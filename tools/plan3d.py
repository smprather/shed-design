# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow"]
# ///
"""3D model of property_total_plan.jsonc on the surveyed lot and the lidar terrain, plus septic checks.

The plan's frame is meters from the midpoint of the platted back (west) line: x along it
toward US-290, y away from our lot, z up from the ground at the origin. Terrain comes from
site/terrain-lidar.json (USGS lidar, 2017). Entities marked "z": "terrain" are draped on it.
Our side comes from the repo: the parcel and house walls from the 1991 survey bearings in
site_plan.py, building B, and the septic pipe, well and oak from the field data. There is no
room model yet, so the house is a footprint only.

Writes site/plan3d.obj (meters, z up; one object per entity) and site/plan3d.html (an
interactive viewer: open it in a browser), and prints the checks.

Run: uv run tools/plan3d.py
"""

import bisect
import json
import math
from pathlib import Path

import polars as pl
import rich_click as click

from site_plan import HOUSE, PARCEL, REPO, SITE_B, WELL, en_to_site, north_line_y, site, st
from site_b_plan import HOSE, house_north_y

SPEC = REPO / "property_total_plan.jsonc"
TERRAIN = REPO / "site" / "terrain-lidar.json"
OUT = REPO / "site" / "plan3d.obj"
VIEWER = REPO / "tools" / "plan3d_viewer.html"  # template; site/plan3d.html is built from it
FT = 0.3048
KEEP_OUT = 10.0  # ft around the septic pipe and the well, until Travis County gives a number
LANE_MIN = 12.0  # ft, septic truck lane
HOSE_MAX = 100.0  # ft of pump-truck hose
B_EAVE = 14.0  # ft; undecided, the noise model's case
WALL_FOOTING = 2.0  # ft inside the line for a US-290 wall footing
TREE_ROWS = (10.0, 22.0)  # ft in from the back line: two staggered rows (notes, back-line trees)
DRAPE_STEP = 2.0  # m between draped vertices
BACK_WALL_ST = ((100.8, 22.9), (100.8, 68.8))  # the main block's back wall, facing the back lawn (survey s, t)
BACKYARD_EYE = (10.0, 6.0)  # ft out from that wall's midpoint, and ft above the ground there
BACKYARD_GAZE = (15.0, 4.0)  # degrees left of straight back (toward the apartments), and below level

Pt = tuple[float, float]


def read_jsonc(path: Path) -> dict:
    """Parse JSON with // comments (outside strings)."""
    s, out, i, in_str = path.read_text(), [], 0, False
    while i < len(s):
        c = s[i]
        if in_str:
            out.append(c)
            if c == "\\":
                out.append(s[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif s.startswith("//", i):
            while i < len(s) and s[i] != "\n":
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return json.loads("".join(out))


class Terrain:
    """Bilinear ground height (m above the origin's ground) from the lidar grid; clamped at its edges."""

    def __init__(self, path: Path) -> None:
        d = json.loads(path.read_text())
        self.xs, self.ys, self.z0 = d["x_m"], d["y_m"], d["z0_ft"]
        self.z = [[(v - self.z0) * FT for v in row] for row in d["z_ft"]]

    @staticmethod
    def _cell(axis: list[float], v: float) -> tuple[int, float]:
        v = min(max(v, axis[0]), axis[-1])
        i = min(max(bisect.bisect_right(axis, v) - 1, 0), len(axis) - 2)
        return i, (v - axis[i]) / (axis[i + 1] - axis[i])

    def __call__(self, x: float, y: float) -> float:
        i, tx = self._cell(self.xs, x)
        j, ty = self._cell(self.ys, y)
        z = self.z
        return ((1 - tx) * (1 - ty) * z[j][i] + tx * (1 - ty) * z[j][i + 1]
                + (1 - tx) * ty * z[j + 1][i] + tx * ty * z[j + 1][i + 1])


class Frame:
    """Site frame (ft; x ESE, y SSW) -> plan frame (m; x toward US-290 along the back line, y west)."""

    def __init__(self) -> None:
        rn, rs = PARCEL[2], PARCEL[3]
        self.o = ((rn[0] + rs[0]) / 2, (rn[1] + rs[1]) / 2)
        n = math.dist(rn, rs)
        ex = ((rn[0] - rs[0]) / n, -(rn[1] - rs[1]) / n)  # in map axes (X ESE, Y NNE)
        self.ex, self.ey = ex, (-ex[1], ex[0])  # ey = ex turned 90 deg CCW
        cx = sum(p[0] for p in PARCEL) / 4 - self.o[0]
        cy = -(sum(p[1] for p in PARCEL) / 4 - self.o[1])
        assert cx * self.ey[0] + cy * self.ey[1] < 0, "+y should point away from the lot"

    def __call__(self, p: Pt) -> Pt:
        dx, dy = p[0] - self.o[0], -(p[1] - self.o[1])
        return ((dx * self.ex[0] + dy * self.ex[1]) * FT, (dx * self.ey[0] + dy * self.ey[1]) * FT)


class Obj:
    def __init__(self, ground: Terrain) -> None:
        self.ground = ground
        self.lines: list[str] = []
        self.nv = 0

    def obj(self, name: str) -> None:
        self.lines.append(f"o {name}")

    def _v(self, pts) -> list[int]:
        for x, y, z in pts:
            self.lines.append(f"v {x:.3f} {y:.3f} {z:.3f}")
        self.nv += len(pts)
        return list(range(self.nv - len(pts) + 1, self.nv + 1))

    def face(self, pts) -> None:
        self.lines.append("f " + " ".join(map(str, self._v(pts))))

    def polyline(self, pts, closed: bool = False) -> None:
        idx = self._v(pts)
        self.lines.append("l " + " ".join(map(str, idx + idx[:1] if closed else idx)))

    def drape(self, pts: list[Pt], closed: bool, lift: float = 0.05) -> None:
        """Polyline on the ground, subdivided so it follows the terrain."""
        ring = pts + pts[:1] if closed else pts
        out = []
        for a, b in zip(ring, ring[1:]):
            n = max(1, math.ceil(math.dist(a, b) / DRAPE_STEP))
            out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
        out.append(ring[-1])
        self.polyline([(x, y, self.ground(x, y) + lift) for x, y in out])

    def prism(self, poly: list[Pt], z0: float, z1: float) -> None:
        """Closed prism over a footprint, flat bottom and top."""
        poly = ccw(poly)
        n = len(poly)
        self.face([(x, y, z0) for x, y in reversed(poly)])
        self.face([(x, y, z1) for x, y in poly])
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            self.face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)])

    def wall(self, a: Pt, b: Pt, height: float, thickness: float) -> None:
        """Wall standing on the terrain between a and b, one panel per drape step."""
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -uy * thickness / 2, ux * thickness / 2
        n = max(1, math.ceil(L / DRAPE_STEP))
        for k in range(n):
            p = (a[0] + ux * L * k / n, a[1] + uy * L * k / n)
            q = (a[0] + ux * L * (k + 1) / n, a[1] + uy * L * (k + 1) / n)
            z = (self.ground(*p) + self.ground(*q)) / 2
            self.prism([(p[0] - nx, p[1] - ny), (q[0] - nx, q[1] - ny), (q[0] + nx, q[1] + ny), (p[0] + nx, p[1] + ny)],
                       z, z + height)

    def terrain(self) -> None:
        g = self.ground
        for j in range(len(g.ys) - 1):
            for i in range(len(g.xs) - 1):
                c = [(g.xs[i], g.ys[j], g.z[j][i]), (g.xs[i + 1], g.ys[j], g.z[j][i + 1]),
                     (g.xs[i + 1], g.ys[j + 1], g.z[j + 1][i + 1]), (g.xs[i], g.ys[j + 1], g.z[j + 1][i])]
                self.face(c)

    def save(self, path: Path, header: str) -> None:
        path.write_text(header + "\n".join(self.lines) + "\n")


def ccw(poly: list[Pt]) -> list[Pt]:
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else poly[::-1]


def circle(c: Pt, r: float, n: int = 36) -> list[Pt]:
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def seg_dist(p: Pt, a: Pt, b: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def inside(p: Pt, poly: list[Pt]) -> bool:
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            c = not c
    return c


def poly_dist(p: Pt, poly: list[Pt], closed: bool = True) -> float:
    if closed and len(poly) > 2 and inside(p, poly):
        return 0.0
    segs = zip(poly, poly[1:] + poly[:1]) if closed else zip(poly, poly[1:])
    return min(seg_dist(p, a, b) for a, b in segs) if len(poly) > 1 else math.dist(p, poly[0])


def write_viewer(path: Path, obj_text: str, plan: dict, checks: list[dict], backyard: dict,
                 z0_ft: float) -> None:
    """Fill the viewer template with the model, the plan's entity notes, the checks and the back-yard view."""
    spec = {"entities": [{k: e.get(k) for k in ("entity_id", "status", "source", "notes", "facade_toward_us")}
                         for e in plan["spatial_entities"]],
            "removed": plan.get("removed_claims", [])}
    head, body = VIEWER.read_text().split("<!--BODY-->\n")
    body = (body.replace("/*OBJ*/", obj_text)
            .replace("/*SPEC*/", json.dumps(spec).replace("</", "<\\/"))
            .replace("/*CHECKS*/", json.dumps(checks).replace("</", "<\\/"))
            .replace("/*BACKYARD*/", json.dumps(backyard)[1:-1])
            .replace("/*Z0_FT*/", json.dumps(z0_ft)))
    path.write_text('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                    f"{head}</head>\n<body>\n{body}</body>\n</html>\n")


def footprints(geom: dict) -> list[tuple[list[Pt], bool]]:
    """2D shapes of an entity (plan m), each with whether it is closed."""
    if geom["kind"] == "point":
        return [([tuple(geom["point_m"])], False)]
    if geom["kind"] in ("prisms", "polygons"):
        return [([tuple(p) for p in it["points_m"]], True) for it in geom["items"]]
    return [([tuple(p) for p in geom["points_m"]], geom["kind"] in ("polygon", "prism"))]


@click.command()
@click.option("--spec", type=click.Path(exists=True, path_type=Path), default=SPEC, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=OUT, show_default=True)
def main(spec: Path, out: Path) -> None:
    """Build the 3D plan on the lidar terrain and run the septic checks."""
    plan = read_jsonc(spec)
    ground = Terrain(TERRAIN)
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    pipe = tuple(fp["white_pipe"]["solutions"][0]["site"])
    oak = tuple(fp["big_oak"]["solutions"][0]["site"])
    well = en_to_site(WELL)
    to_m = Frame()
    obj = Obj(ground)
    checks: list[dict] = []

    def check(item: str, value: str, limit: str, status: str, note: str = "") -> None:
        checks.append({"check": item, "value": value, "limit": limit, "status": status, "note": note})

    for key, path in plan.get("local_source_registry", {}).items():
        if isinstance(path, str) and path.startswith("site/") and not (REPO / path).exists():
            check(f"source {key}", path, "file", "MISSING")

    obj.obj("terrain_lidar_2017")
    obj.terrain()

    # --- Our side, from the survey and the field data ---
    obj.obj("our_parcel_1991_survey")
    obj.drape([to_m(p) for p in PARCEL], closed=True)
    obj.obj("house_footprint_survey")
    obj.drape([to_m(p) for p in HOUSE], closed=True)
    b = [to_m(p) for p in SITE_B]
    slab = max(ground(*p) for p in b)  # slab at the high corner; the low side gets fill or a stem wall
    obj.obj(f"building_B_23x43_eave_{B_EAVE:g}ft_assumed")
    obj.prism(b, slab, slab + B_EAVE * FT)
    keep_outs = {"septic_pipe_keepout_10ft": (pipe, KEEP_OUT), "well_keepout_10ft": (well, KEEP_OUT)}
    for name, (c, r) in {**keep_outs, "oak_drip_line": (oak, 25.1), "oak_no_dig_12ft": (oak, 12.0)}.items():
        obj.obj(name)
        obj.drape([to_m(p) for p in circle(c, r)], closed=True)

    # --- The plan's entities ---
    for e in plan["spatial_entities"]:
        g = e["geometry"]
        obj.obj(e["entity_id"])
        if g["kind"] == "wall":
            for a, c in zip(g["points_m"], g["points_m"][1:]):
                obj.wall(tuple(a), tuple(c), g["height_m"], g["thickness_m"])
        elif g["kind"] == "prism":
            obj.prism([tuple(p) for p in g["points_m"]], g["z_bottom_m"], g["z_top_m"])
        elif g["kind"] == "prisms":
            for it in g["items"]:
                obj.prism([tuple(p) for p in it["points_m"]], it["z_bottom_m"], it["z_top_m"])
        elif g["kind"] == "point":
            x, y = g["point_m"]
            obj.polyline([(x, y, ground(x, y)), (x, y, ground(x, y) + 3.0)])
        else:
            for pts, closed in footprints(g):
                obj.drape(pts, closed=closed)

        for name, (c, r) in keep_outs.items():
            gap = min(poly_dist(to_m(c), pts, closed) for pts, closed in footprints(g)) / FT - r
            if gap < 0 and e["type"] not in ("property_line", "easement", "parcels"):
                check(f"{e['entity_id']} vs {name}", f"{gap + r:.1f} ft", f"{r:g} ft", "CONFLICT")

    # --- Our planned additions vs the septic system (site frame, ft) ---
    fall = (slab - min(ground(*p) for p in b)) / FT
    check("building B ground fall across the slab", f"{fall:.1f} ft", "-", "NOTE",
          "2017 lidar; high at the NE corner by the oak, so level it with fill on the west side, not a cut toward the oak")
    d = poly_dist(pipe, SITE_B)
    check("building B vs septic pipe", f"{d:.1f} ft", f"{KEEP_OUT:g} ft",
          "AT LIMIT" if d < KEEP_OUT + 1 else "OK", "no margin; the pipe is from long laser shots (+/-2 ft)")
    check("building B vs well", f"{poly_dist(well, SITE_B):.1f} ft", f"{KEEP_OUT:g} ft", "OK")
    lane = house_north_y(185) - SITE_B[2][1]
    check("truck lane, B to house", f"{lane:.1f} ft", f"{LANE_MIN:g} ft", "OK" if lane >= LANE_MIN else "CONFLICT")
    hose = sum(math.dist(a, c) for a, c in zip(HOSE + [pipe], HOSE[1:] + [pipe]))
    check("hose run to the pipe", f"{hose:.0f} ft", f"{HOSE_MAX:g} ft", "OK" if hose <= HOSE_MAX else "CONFLICT")

    (lx0, ly0), (lx1, ly1) = PARCEL[2], PARCEL[1]
    cos_line = (lx1 - lx0) / math.dist((lx0, ly0), (lx1, ly1))
    for name, p in (("septic pipe", pipe), ("well", well)):
        to_line = (p[1] - north_line_y(p[0])) * cos_line
        gap = to_line - WALL_FOOTING
        check(f"US-290 wall footing vs {name}", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft",
              "CONFLICT" if gap < KEEP_OUT - 0.05 else "AT LIMIT" if gap < KEEP_OUT + 1 else "OK",
              f"{name} is {to_line:.1f} ft from the surveyed line; footing assumed {WALL_FOOTING:g} ft wide")

    well_in = seg_dist(well, PARCEL[2], PARCEL[3])
    gap = min(abs(well_in - r) for r in TREE_ROWS)
    check("back-line tree rows vs well", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft",
          "CONFLICT" if gap < KEEP_OUT else "OK", f"well is {well_in:.0f} ft in; rows at {TREE_ROWS[0]:g} and {TREE_ROWS[1]:g} ft")
    check("anything vs tank and drainfield", "not located", "-", "UNKNOWN",
          "every check against them waits on finding the lids and trenches")

    out.parent.mkdir(parents=True, exist_ok=True)
    obj.save(out, f"# {out.name}: written by tools/plan3d.py from {spec.name} and {TERRAIN.name}. Meters, z up.\n"
                  f"# Origin: midpoint of the platted back line, z = 0 at {ground.z0} ft NAVD88; "
                  "+x toward US-290 along the line, +y away from the lot.\n")
    html = out.with_suffix(".html")
    (s0, t0), (s1, t1) = BACK_WALL_ST
    s_eye, t_eye = (s0 + s1) / 2 + BACKYARD_EYE[0], (t0 + t1) / 2
    eye_xy = to_m(site([st(s_eye, t_eye)])[0])
    eye = [round(eye_xy[0], 2), round(eye_xy[1], 2), round(ground(*eye_xy) + BACKYARD_EYE[1] * FT, 2)]
    left, down, reach = math.radians(BACKYARD_GAZE[0]), math.radians(BACKYARD_GAZE[1]), 200.0  # ft
    at_xy = to_m(site([st(s_eye + reach * math.cos(left), t_eye - reach * math.sin(left))])[0])
    at = [round(at_xy[0], 2), round(at_xy[1], 2), round(eye[2] - reach * FT * math.tan(down), 2)]
    write_viewer(html, out.read_text(), plan, checks, {"eye": eye, "at": at}, ground.z0)
    click.echo(f"wrote {out.relative_to(REPO)} ({obj.nv} vertices) and {html.relative_to(REPO)}; "
               f"building B slab at z = {slab:.2f} m")
    with pl.Config(tbl_rows=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True,
                   tbl_width_chars=220, fmt_str_lengths=90):
        click.echo(pl.DataFrame([{"entity": e["entity_id"], "status": e.get("status", "")}
                                 for e in plan["spatial_entities"]]))
        click.echo(pl.DataFrame(checks))
    if plan.get("removed_claims"):
        click.echo(f"{len(plan['removed_claims'])} claims removed from the plan; see removed_claims in {spec.name}")


if __name__ == "__main__":
    main()
