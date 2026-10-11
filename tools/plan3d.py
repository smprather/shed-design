# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow"]
# ///
"""3D model of the owner's property_total_plan.jsonc on the surveyed lot, plus septic checks.

The spec's frame is meters from the center of its rear fence: x along the fence, y away from
the lot, z up from our ground. The rear fence is taken to be the back (west) line, which the
retail lot adjoins. The spec says that fence follows the platted line, so the platted back
line is y = 0 here, and +x runs toward US-290 (that keeps the frame right-handed).

The spec's local sources (a CubiCasa OBJ, the plat PDF, a septic DWG) aren't in the repo. The
plat lines come from site_plan.py, which builds them from the 1991 survey's bearings, and the
septic features from the field measurements. There is no room model, so the house is a
footprint only.

Writes site/plan3d.obj (meters, z up; one object per entity) and prints the checks.

Run: uv run tools/plan3d.py
"""

import json
import math
from pathlib import Path

import polars as pl
import rich_click as click

from site_plan import HOUSE, PARCEL, REPO, SITE_B, WELL, en_to_site, north_line_y
from site_b_plan import HOSE, house_north_y

SPEC = REPO / "property_total_plan.jsonc"
OUT = REPO / "site" / "plan3d.obj"
FT = 0.3048
KEEP_OUT = 10.0  # ft around the septic pipe and the well, until Travis County gives a number
LANE_MIN = 12.0  # ft, septic truck lane
HOSE_MAX = 100.0  # ft of pump-truck hose
B_EAVE = 14.0  # ft; undecided, the noise model's case
WALL_FOOTING = 2.0  # ft inside the line for a US-290 wall footing
TREE_ROWS = (10.0, 22.0)  # ft in from the back line: two staggered rows (notes, back-line trees)

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


class Frame:
    """Site frame (ft; x ESE, y SSW) -> spec frame (m; x toward US-290 along the back line, y west)."""

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
    def __init__(self) -> None:
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

    def polyline(self, pts, closed: bool = True) -> None:
        idx = self._v(pts)
        self.lines.append("l " + " ".join(map(str, idx + idx[:1] if closed else idx)))

    def prism(self, poly: list[Pt], z0: float, z1: float) -> None:
        """Closed prism over a counter-clockwise footprint."""
        n = len(poly)
        self.face([(x, y, z0) for x, y in reversed(poly)])
        self.face([(x, y, z1) for x, y in poly])
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            self.face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)])

    def save(self, path: Path, header: str) -> None:
        path.write_text(header + "\n".join(self.lines) + "\n")


def ccw(poly: list[Pt]) -> list[Pt]:
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else poly[::-1]


def rect(xb, yb) -> list[Pt]:
    return [(xb[0], yb[0]), (xb[1], yb[0]), (xb[1], yb[1]), (xb[0], yb[1])]


def circle(c: Pt, r: float, n: int = 36) -> list[Pt]:
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def seg_dist(p: Pt, a: Pt, b: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def poly_dist(p: Pt, poly: list[Pt]) -> float:
    return min(seg_dist(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def slope_h(ratio: str) -> float:
    """Horizontal run per unit of drop for an 'H:V' side slope (civil convention)."""
    h, v = (float(x) for x in ratio.split(":"))
    return h / v


@click.command()
@click.option("--spec", type=click.Path(exists=True, path_type=Path), default=SPEC, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=OUT, show_default=True)
def main(spec: Path, out: Path) -> None:
    """Coregister the spec with the surveyed lot, extrude its meshes, and run the septic checks."""
    plan = read_jsonc(spec)
    ents = {e["entity_id"]: e for e in plan["spatial_entities"]}
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    pipe = tuple(fp["white_pipe"]["solutions"][0]["site"])
    oak = tuple(fp["big_oak"]["solutions"][0]["site"])
    well = en_to_site(WELL)
    to_m = Frame()
    obj = Obj()
    checks: list[dict] = []

    def check(item: str, value: str, limit: str, status: str, note: str = "") -> None:
        checks.append({"check": item, "value": value, "limit": limit, "status": status, "note": note})

    for path in plan.get("local_source_registry", {}).values():
        if not (spec.parent / path).exists():
            check(f"source {path}", "missing", "file", "MISSING", "not in the repo")

    # --- Our side, from the survey and the field data (z = 0 is our ground) ---
    obj.obj("our_parcel_1991_survey")
    obj.polyline([(*to_m(p), 0.0) for p in PARCEL])
    obj.obj("house_footprint_survey")
    obj.polyline([(*to_m(p), 0.0) for p in HOUSE])
    obj.obj(f"building_B_23x43_eave_{B_EAVE:g}ft_assumed")
    obj.prism(ccw([to_m(p) for p in SITE_B]), 0.0, B_EAVE * FT)
    for name, c, r in (("septic_pipe_keepout_10ft", pipe, KEEP_OUT), ("well_keepout_10ft", well, KEEP_OUT),
                       ("oak_drip_line", oak, 25.1), ("oak_no_dig_12ft", oak, 12.0)):
        obj.obj(name)
        obj.polyline([(*to_m(p), 0.0) for p in circle(c, r)])

    # --- The spec's entities, in its own frame ---
    fence = ents.get("rear_fence_line")
    if fence:
        (x0, y0, _), (x1, y1, _) = fence["coordinates_relative_meters"]["start"], fence["coordinates_relative_meters"]["end"]
        g = fence["geometry"]
        ux, uy = (x1 - x0) / math.dist((x0, y0), (x1, y1)), (y1 - y0) / math.dist((x0, y0), (x1, y1))
        nx, ny = -uy * g["thickness"] / 2, ux * g["thickness"] / 2
        obj.obj("spec_rear_fence")
        obj.prism(ccw([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)]), 0.0, g["height"])
        line_m = math.dist(PARCEL[2], PARCEL[3]) * FT
        check("spec fence vs platted back line", f"{math.dist((x0, y0), (x1, y1)):.1f} m", f"{line_m:.1f} m",
              "MISMATCH" if abs(math.dist((x0, y0), (x1, y1)) - line_m) > 1 else "OK", "the fence stops short of both corners")

    basin = ents.get("scenic_brook_retention_basin")
    if basin:
        c, g = basin["coordinates_relative_meters"], basin["geometry"]
        (xa, xb), (ya, yb) = c["x_bounds"], c["y_bounds"]
        run = slope_h(g["slope_ratio"])
        depth = g["surface_z"] - g["floor_z"]
        max_depth = min(xb - xa, yb - ya) / 2 / run
        floor_z = g["floor_z"]
        if depth > max_depth:
            floor_z = g["surface_z"] - max_depth
            check("basin depth at its side slope", f"{depth:.2f} m asked", f"{max_depth:.2f} m fits",
                  "INCONSISTENT", f"{g['slope_ratio']} slopes from a {yb - ya:.0f} m width meet at z = {floor_z:.2f}; modeled as a trough")
        inset = (g["surface_z"] - floor_z) * run
        top = rect((xa, xb), (ya, yb))
        bot = rect((xa + inset, xb - inset), (ya + inset, yb - inset))
        obj.obj("spec_retention_basin")
        obj.face([(x, y, floor_z) for x, y in bot])
        for i in range(4):
            j = (i + 1) % 4
            obj.face([(*top[i], g["surface_z"]), (*top[j], g["surface_z"]), (*bot[j], floor_z), (*bot[i], floor_z)])

    wall = ents.get("plaza_retaining_wall")
    if wall:
        c = wall["coordinates_relative_meters"]
        (xa, xb), y, dz = c["x_bounds"], c["y_fixed"], wall["geometry"]["vertical_drop_delta_z"]
        obj.obj("spec_plaza_retaining_wall_face")
        obj.face([(xa, y, 0.0), (xb, y, 0.0), (xb, y, dz), (xa, y, dz)])

    bldg = ents.get("scenic_brook_plaza_bldg_c")
    if bldg:
        c, g = bldg["coordinates_relative_meters"], bldg["geometry"]
        z0 = g["foundation_z"]
        z1 = z0 + g["roof_height_from_pad"]
        obj.obj("spec_plaza_bldg_c")
        obj.prism(ccw(rect(c["x_bounds"], c["y_bounds"])), z0, z1)
        stated = g.get("effective_visual_z_above_yard")
        if stated is not None and abs(stated - z1) > 0.05:
            check("bldg_c height above our yard", f"{z1:.2f} m from the pad", f"{stated} m stated", "MISMATCH")

    park = ents.get("scenic_brook_pocket_park")
    if park:
        c = park["coordinates_relative_meters"]
        obj.obj("spec_pocket_park_footprint")
        obj.polyline([(x, y, 0.0) for x, y in rect(c["x_bounds"], c["y_bounds"])])

    # Nothing in the spec sits on our side of the back line, so none of it can touch our septic.
    spec_min_y = min(
        [v for e in ents.values() for k, v in e.get("coordinates_relative_meters", {}).items() if k == "y_fixed"]
        + [e["coordinates_relative_meters"]["y_bounds"][0] for e in ents.values()
           if "y_bounds" in e.get("coordinates_relative_meters", {})]
    )
    septic_max_y = max(y for _, y in [to_m(p) for p in circle(pipe, KEEP_OUT) + circle(well, KEEP_OUT)])
    check("spec entities vs septic keep-outs", f"spec y >= {spec_min_y:.1f} m", f"septic y <= {septic_max_y:.1f} m",
          "OK" if spec_min_y > septic_max_y else "CONFLICT", "all the spec's neighbor geometry is past the back line")

    # --- Our planned additions vs the septic system (site frame, ft) ---
    d = poly_dist(pipe, SITE_B)
    check("building B vs septic pipe", f"{d:.1f} ft", f"{KEEP_OUT:g} ft",
          "AT LIMIT" if d < KEEP_OUT + 1 else "OK", "no margin; the pipe is from long laser shots (+/-2 ft)")
    check("building B vs well", f"{poly_dist(well, SITE_B):.1f} ft", f"{KEEP_OUT:g} ft", "OK")
    lane = house_north_y(185) - SITE_B[2][1]
    check("truck lane, B to house", f"{lane:.1f} ft", f"{LANE_MIN:g} ft", "OK" if lane >= LANE_MIN else "CONFLICT")
    hose = sum(math.dist(a, b) for a, b in zip(HOSE + [pipe], HOSE[1:] + [pipe]))
    check("hose run to the pipe", f"{hose:.0f} ft", f"{HOSE_MAX:g} ft", "OK" if hose <= HOSE_MAX else "CONFLICT")

    (lx0, ly0), (lx1, ly1) = PARCEL[2], PARCEL[1]
    cos_line = (lx1 - lx0) / math.dist((lx0, ly0), (lx1, ly1))
    for name, p in (("septic pipe", pipe), ("well", well)):
        to_line = (p[1] - north_line_y(p[0])) * cos_line
        gap = to_line - WALL_FOOTING
        check(f"US-290 wall footing vs {name}", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft",
              "CONFLICT" if gap < KEEP_OUT - 0.05 else "AT LIMIT" if gap < KEEP_OUT + 1 else "OK",
              f"{name} is {to_line:.1f} ft from the surveyed line; footing assumed {WALL_FOOTING:g} ft wide")

    rn, rs = PARCEL[2], PARCEL[3]
    well_in = seg_dist(well, rn, rs)
    gap = min(abs(well_in - r) for r in TREE_ROWS)
    check("back-line tree rows vs well", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft",
          "CONFLICT" if gap < KEEP_OUT else "OK", f"well is {well_in:.0f} ft in; rows at {TREE_ROWS[0]:g} and {TREE_ROWS[1]:g} ft")
    check("anything vs tank and drainfield", "not located", "-", "UNKNOWN",
          "every check against them waits on finding the lids and trenches")

    out.parent.mkdir(parents=True, exist_ok=True)
    obj.save(out, f"# {out.name}: written by tools/plan3d.py from {spec.name}. Meters, z up.\n"
                  "# Origin: center of the platted back line; +x toward US-290 along it, +y away from the lot.\n")
    click.echo(f"wrote {out.relative_to(REPO)} ({obj.nv} vertices)")
    with pl.Config(tbl_rows=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True,
                   tbl_width_chars=220, fmt_str_lengths=90):
        click.echo(pl.DataFrame(checks))


if __name__ == "__main__":
    main()
