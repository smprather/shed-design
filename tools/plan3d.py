# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy"]
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

import base64
import bisect
import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import rich_click as click

from site_plan import BUILDING_LINE, HOUSE, PARCEL, REPO, SITE_B, WELL, en_to_site, north_line_y, site, st
from site_b_plan import HOSE, house_north_y
from front_layout import EXISTING_DRIVE, FRONT_WALK, LANE, LOOP_C, PORTE_COCHERE, catmull_rom, offset
from house_layout import FF_FT, house_spec

SPEC = REPO / "property_total_plan.jsonc"
TERRAIN = REPO / "site" / "terrain-lidar.json"
CANOPY = REPO / "site" / "canopy-lidar.json"  # tools/fetch_canopy.py; optional
OUT = REPO / "site" / "plan3d.obj"
VIEWER = REPO / "tools" / "plan3d_viewer.html"  # template; site/plan3d.html is built from it
FT = 0.3048
KEEP_OUT = 10.0  # ft around the septic pipe and the well, until Travis County gives a number
LANE_MIN = 12.0  # ft, septic truck lane
HOSE_MAX = 100.0  # ft of pump-truck hose
B_EAVE = 14.0  # ft; undecided, the noise model's case
B_PITCH = 3 / 12  # building B's gable roof, ridge along the long side; undecided
B_DOORS = (12.0, 12.0)  # ft, width x height: two roll-up doors on the south wall at the quarter points (owner, Oct 18 2026); size undecided
B_MOWER = (43 / 4, 8.0)  # ft from B's SW corner (east, north): the owner's John Deere S130, parked in the west bay for scale
PORTE_COCHERE_CLEAR = 10.0  # ft to the underside of option A's roof (cars and a pickup need ~8)
WALL_FOOTING = 2.0  # ft inside the line for a US-290 wall footing
TREE_ROWS = (10.0, 22.0)  # ft in from the back line: two staggered rows (notes, back-line trees)
TREE_SPACING = 10.0  # ft on center along each row (holly screen 8-10 ft)
TREE_SIDE_INSET = 6.0  # ft in from the side lines
OAK_NO_DIG = 12.0  # ft around the twin oak
GAP_HEIGHT = 4.5  # m (15 ft): a planned spot under standing canopy this tall already has a tree; plant the gaps only
CANOPY_CELL = 3  # existing trees are drawn per 3 x 3 m block of the 1 m canopy grid
# Back row holly; front row alternates yaupon and mountain laurel, offset half a space. No cypress or
# juniper (allergies). Sizes are (height, crown width) in ft when planted (15 gal), at ~8 years with
# drip, and mature.
PLANTS = {
    "holly": {"name": "Nellie R. Stevens holly", "shape": "cone", "sizes": [[6, 3], [15, 8], [22, 12]]},
    "yaupon": {"name": "Yaupon holly, tree form", "shape": "crown", "sizes": [[6, 3], [14, 8], [20, 14]]},
    "laurel": {"name": "Texas mountain laurel", "shape": "crown", "sizes": [[4, 3], [8, 6], [12, 10]]},
}
DRAPE_STEP = 2.0  # m between draped vertices
BACK_WALL_ST = ((100.8, 22.9), (100.8, 68.8))  # the main block's back wall, facing the back lawn (survey s, t)
BACKYARD_EYE = (10.0, 5.0)  # ft out from that wall's midpoint, and ft above the ground there (the owner's camera)
BACKYARD_GAZE = (15.0, 4.0)  # degrees left of straight back (toward the apartments), and below level
POLES = (25.0, 50.0, 100.0)  # ft straight back from the back-yard eye: 6 ft range poles for scale
POLE_INSET = 2.0  # ft inside the back line for one more pole

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

    def to_site(self, q: Pt) -> Pt:
        """Plan frame (m) -> site frame (ft): the inverse of calling the frame."""
        a, b = q[0] / FT, q[1] / FT
        dx, dy = a * self.ex[0] + b * self.ey[0], a * self.ex[1] + b * self.ey[1]
        return self.o[0] + dx, self.o[1] - dy


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

    def ribbon(self, left: list[Pt], right: list[Pt], lift: float = 0.08) -> None:
        """A paved strip on the ground between two matching edge lines, one quad per station."""
        for (a, b), (c, d) in zip(zip(left, left[1:]), zip(right, right[1:])):
            self.face([(x, y, self.ground(x, y) + lift) for x, y in (a, c, d, b)])

    def pad(self, poly: list[Pt], cell: float = 0.5, lift: float = 0.06) -> None:
        """A flat-lying paved area on the ground: the polygon filled with small squares that follow the terrain."""
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        n = len(poly)

        def inside(x: float, y: float) -> bool:
            c = False
            for i in range(n):
                (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
                if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                    c = not c
            return c

        x = min(xs)
        while x < max(xs):
            y = min(ys)
            while y < max(ys):
                if inside(x + cell / 2, y + cell / 2):
                    sq = [(x, y), (x + cell, y), (x + cell, y + cell), (x, y + cell)]
                    self.face([(a, b, self.ground(a, b) + lift) for a, b in sq])
                y += cell
            x += cell

    def prism(self, poly: list[Pt], z0: float, z1: float) -> None:
        """Closed prism over a footprint, flat bottom and top."""
        poly = ccw(poly)
        n = len(poly)
        self.face([(x, y, z0) for x, y in reversed(poly)])
        self.face([(x, y, z1) for x, y in poly])
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            self.face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)])

    def gable(self, sw: Pt, se: Pt, ne: Pt, nw: Pt, z0: float, ze: float, rise: float) -> None:
        """Closed building massing: walls to the eave, gable ends, and a roof with its ridge along sw -> se."""
        ms, me = ((sw[0] + nw[0]) / 2, (sw[1] + nw[1]) / 2), ((se[0] + ne[0]) / 2, (se[1] + ne[1]) / 2)
        zr = ze + rise
        self.face([(*p, z0) for p in (sw, nw, ne, se)])
        self.face([(*sw, z0), (*se, z0), (*se, ze), (*sw, ze)])
        self.face([(*ne, z0), (*nw, z0), (*nw, ze), (*ne, ze)])
        self.face([(*se, z0), (*ne, z0), (*ne, ze), (*me, zr), (*se, ze)])
        self.face([(*nw, z0), (*sw, z0), (*sw, ze), (*ms, zr), (*nw, ze)])
        self.face([(*sw, ze), (*se, ze), (*me, zr), (*ms, zr)])
        self.face([(*ne, ze), (*nw, ze), (*ms, zr), (*me, zr)])

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


class Canopy:
    """Standing tree canopy (m above ground, 1 m plan cells) from site/canopy-lidar.json: 2017 lidar heights,
    zeroed where the latest Sentinel-2 scene shows the ground cleared."""

    def __init__(self, path: Path = CANOPY) -> None:
        d = json.loads(path.read_text())
        self.x0, self.y0, self.nx, self.ny = d["x0"], d["y0"], d["nx"], d["ny"]
        grid = lambda key: np.frombuffer(base64.b64decode(d[key]), np.uint8).reshape(self.ny, self.nx)
        self.h = np.where(grid("standing") > 0, grid("h") * d["h_step_m"], 0.0)
        self.source = f"{d['lidar']}; standing per Sentinel-2 {d['sentinel_scene']} (NDVI >= {d['ndvi_standing']})"

    def at(self, x: float, y: float, r: float = 1.0) -> float:
        """Tallest standing canopy within r m of a plan point; 0 off the grid."""
        c0, c1 = max(int(x - r - self.x0), 0), int(x + r - self.x0) + 1
        r0, r1 = max(int(y - r - self.y0), 0), int(y + r - self.y0) + 1
        w = self.h[r0:r1, c0:c1]
        return float(w.max()) if w.size else 0.0

    def for_viewer(self, ground: "Terrain", k: int = CANOPY_CELL) -> dict:
        """Blocks of k m (ground and canopy height packed as bytes) and treetops, for the viewers."""
        ny, nx = self.ny // k, self.nx // k
        blocks = self.h[:ny * k, :nx * k].reshape(ny, k, nx, k)
        # A block is tree only where about half its cells are canopy, so crown edges don't spread.
        h = np.where((blocks > 0).mean(axis=(1, 3)) >= 0.45, blocks.max(axis=(1, 3)), 0.0)
        xs, ys = self.x0 + k / 2 + k * np.arange(nx), self.y0 + k / 2 + k * np.arange(ny)
        zg = np.array([[ground(x, y) for x in xs] for y in ys])
        zmin, step = float(zg.min()), 0.2
        win = np.lib.stride_tricks.sliding_window_view(np.pad(self.h, 3), (7, 7)).max(axis=(2, 3))
        tops = []  # local maxima at least 4 m tall, tallest first, none within 3 m of a taller one
        for r, c in sorted(np.argwhere((self.h == win) & (self.h >= 4.0)), key=lambda rc: -self.h[rc[0], rc[1]]):
            x, y = self.x0 + c + 0.5, self.y0 + r + 0.5
            if all((x - t[0]) ** 2 + (y - t[1]) ** 2 > 9 for t in tops):
                tops.append([round(x, 1), round(y, 1), round(ground(x, y), 2), round(float(self.h[r, c]), 1)])
        pack = lambda a: base64.b64encode(np.clip(np.round(a), 0, 255).astype(np.uint8).tobytes()).decode()
        return {"x0": self.x0, "y0": self.y0, "cell": k, "nx": nx, "ny": ny, "zmin": round(zmin, 2), "step": step,
                "zg": pack((zg - zmin) / step), "h": pack(h / step), "tops": tops, "source": self.source}


def back_line_trees(keep_outs: list[tuple[Pt, float]]) -> tuple[list[dict], int]:
    """The proposed back-line planting (site ft), less any tree inside a keep-out. Returns the trees and how many were dropped."""
    rs, rn = PARCEL[3], PARCEL[2]
    length = math.dist(rs, rn)
    u = ((rn[0] - rs[0]) / length, (rn[1] - rs[1]) / length)
    cx, cy = sum(p[0] for p in PARCEL) / 4, sum(p[1] for p in PARCEL) / 4
    n = (-u[1], u[0])
    if (cx - rs[0]) * n[0] + (cy - rs[1]) * n[1] < 0:
        n = (-n[0], -n[1])

    def at(a: float, d: float) -> Pt:  # a ft along the back line from its south end, d ft in from it
        return rs[0] + u[0] * a + n[0] * d, rs[1] + u[1] * a + n[1] * d

    def inside(p: Pt) -> bool:
        return min(seg_dist(p, PARCEL[1], PARCEL[2]), seg_dist(p, PARCEL[0], PARCEL[3])) >= TREE_SIDE_INSET

    back, front = TREE_ROWS
    span = [a / 2 for a in range(int(2 * length) + 1) if inside(at(a / 2, back))]
    k = round((span[-1] - span[0]) / TREE_SPACING)
    step = (span[-1] - span[0]) / k
    rows = [(at(span[0] + i * step, back), "holly") for i in range(k + 1)]
    rows += [(at(span[0] + (i + 0.5) * step, front), ("yaupon", "laurel")[i % 2]) for i in range(k)]
    rows = [(p, kind) for p, kind in rows if inside(p)]
    kept = [(p, kind) for p, kind in rows if all(math.dist(p, c) >= r for c, r in keep_outs)]
    return [{"site": p, "plant": kind} for p, kind in kept], len(rows) - len(kept)


def field_features() -> tuple[Pt, Pt, Pt]:
    """The septic pipe and the oak's main trunk (field data), and the well (survey); site ft."""
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    return (tuple(fp["white_pipe"]["solutions"][0]["site"]), tuple(fp["big_oak"]["solutions"][0]["site"]),
            en_to_site(WELL))


def planting(canopy: Canopy | None = None) -> tuple[list[dict], dict[str, int]]:
    """The back-line trees, clear of the well, the septic pipe and the oak (see back_line_trees), and with a
    canopy, only in the gaps of the existing trees. Returns the trees and how many spots each rule left out."""
    pipe, oak, well = field_features()
    trees, kept_out = back_line_trees([(well, KEEP_OUT), (pipe, KEEP_OUT), (oak, OAK_NO_DIG)])
    if canopy is None:
        return trees, {"keep_out": kept_out, "existing": 0}
    to_m = Frame()
    gaps = [t for t in trees if canopy.at(*to_m(t["site"])) < GAP_HEIGHT]
    return gaps, {"keep_out": kept_out, "existing": len(trees) - len(gaps)}


def backyard(ground: Terrain, to_m: Frame) -> tuple[dict, list[dict]]:
    """The back-yard view (eye and gaze target, plan m) and the range poles straight back from the eye."""
    (s0, t0), (s1, t1) = BACK_WALL_ST
    s_eye, t_eye = (s0 + s1) / 2 + BACKYARD_EYE[0], (t0 + t1) / 2
    eye_xy = to_m(site([st(s_eye, t_eye)])[0])

    def back(d: float) -> Pt:  # d ft straight back from the eye (square off the back wall)
        return to_m(site([st(s_eye + d, t_eye)])[0])

    y0, y1 = back(0.0)[1], back(1.0)[1]  # the back line is plan y = 0
    pole_ft = [*POLES, (-POLE_INSET * FT - y0) / (y1 - y0)]
    poles = [{"xy": [round(c, 2) for c in back(d)], "ft": round(d),
              "drop_ft": round((ground(*eye_xy) - ground(*back(d))) / FT, 1)} for d in pole_ft]
    eye = [round(eye_xy[0], 2), round(eye_xy[1], 2), round(ground(*eye_xy) + BACKYARD_EYE[1] * FT, 2)]
    left, down, reach = math.radians(BACKYARD_GAZE[0]), math.radians(BACKYARD_GAZE[1]), 200.0  # ft
    at_xy = to_m(site([st(s_eye + reach * math.cos(left), t_eye - reach * math.sin(left))])[0])
    at = [round(at_xy[0], 2), round(at_xy[1], 2), round(eye[2] - reach * FT * math.tan(down), 2)]
    spot = {"along_ft": round((t1 - t0) / 2, 1), "out_ft": BACKYARD_EYE[0], "eye_ft": BACKYARD_EYE[1], "gaze_deg": BACKYARD_GAZE[0]}
    return {"eye": eye, "at": at, "spot": spot}, poles


def write_viewer(path: Path, obj_text: str, plan: dict, checks: list[dict], backyard: dict,
                 poles: list[dict], trees: dict, canopy: dict | None, z0_ft: float, building_b: dict,
                 house: dict) -> None:
    """Fill the viewer template with the model, the plan's entity notes, the checks, the back-yard view, the poles,
    the trees, building B's placement and the house (the viewer draws both in detail)."""
    spec = {"entities": [{k: e.get(k) for k in ("entity_id", "status", "source", "notes", "facade_toward_us")}
                         for e in plan["spatial_entities"]],
            "removed": plan.get("removed_claims", [])}
    head, body = VIEWER.read_text().split("<!--BODY-->\n")
    body = (body.replace("/*OBJ*/", obj_text)
            .replace("/*SPEC*/", json.dumps(spec).replace("</", "<\\/"))
            .replace("/*CHECKS*/", json.dumps(checks).replace("</", "<\\/"))
            .replace("/*BACKYARD*/", json.dumps(backyard)[1:-1])
            .replace("/*POLES*/", json.dumps(poles))
            .replace("/*TREES*/", json.dumps(trees))
            .replace("/*CANOPY*/", json.dumps(canopy))
            .replace("/*Z0_FT*/", json.dumps(z0_ft))
            .replace("/*BUILDING_B*/", json.dumps(building_b))
            .replace("/*HOUSE*/", json.dumps(house)))
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
    pipe, oak, well = field_features()
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
    nw, ne, se, sw = b
    b_ground = [ground(*p) for p in b]
    slab = max(b_ground)  # slab at the high corner; the low side gets fill or a stem wall
    b_id = f"building_B_23x43_eave_{B_EAVE:g}ft_assumed"
    b_len, b_wid = math.dist(sw, se) / FT, math.dist(sw, nw) / FT
    obj.obj(b_id)
    obj.gable(sw, se, ne, nw, slab, slab + B_EAVE * FT, b_wid / 2 * B_PITCH * FT)
    # The viewer draws B in detail from this: its frame (x east from the SW corner, y north, feet), doors and the mower.
    building_b = {"id": b_id, "origin": [round(c, 3) for c in sw],
                  "ux": [round((se[i] - sw[i]) / (b_len * FT), 6) for i in (0, 1)],
                  "uy": [round((nw[i] - sw[i]) / (b_wid * FT), 6) for i in (0, 1)],
                  "slab_m": round(slab, 3), "drop_ft": round((slab - min(b_ground)) / FT, 2),
                  "length_ft": round(b_len, 2), "width_ft": round(b_wid, 2), "eave_ft": B_EAVE, "pitch": B_PITCH,
                  "doors": [{"center_ft": round(c, 2), "width_ft": B_DOORS[0], "height_ft": B_DOORS[1]}
                            for c in (b_len / 4, 3 * b_len / 4)],
                  "mower": {"x_ft": B_MOWER[0], "y_ft": B_MOWER[1]}}
    # Existing drive and front walk, traced from the 1991 plat (front_layout.py, +/-3 ft).
    obj.obj("existing_driveway_1991_plat")
    obj.pad([to_m(p) for p in site(st(*q) for q in EXISTING_DRIVE)], lift=0.05)
    obj.obj("front_walk_1991_plat")
    obj.pad([to_m(p) for p in site(st(*q) for q in FRONT_WALK)], cell=0.25, lift=0.05)
    # Proposed front yard (front_layout.py): loop C, and option A's roof at ~10 ft over the porch-front lane.
    obj.obj("proposed_circle_drive_loop_c")
    center = catmull_rom(LOOP_C)
    obj.ribbon(*([to_m(p) for p in site(st(*q) for q in offset(center, side * LANE / 2))] for side in (1, -1)))
    obj.obj("proposed_porte_cochere_option_a")
    pc = [to_m(p) for p in site(st(*q) for q in PORTE_COCHERE)]
    roof = max(ground(*p) for p in pc) + PORTE_COCHERE_CLEAR * FT
    obj.prism(pc, roof, roof + 1.0 * FT)
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

    canopy = Canopy() if CANOPY.exists() else None
    trees, dropped = planting(canopy)
    well_in = seg_dist(well, PARCEL[2], PARCEL[3])
    gap = min(math.dist(tr["site"], well) for tr in trees)
    check("back-line trees vs well", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft", "CONFLICT" if gap < KEEP_OUT else "OK",
          f"well is {well_in:.0f} ft in; rows at {TREE_ROWS[0]:g} and {TREE_ROWS[1]:g} ft; "
          f"{dropped['keep_out']} spot(s) left out by the well, {dropped['existing']} already under existing trees")
    check("digging vs buried electric service", "not located", "-", "UNKNOWN",
          "meter pole at the NW corner; the line runs underground to the house; locate it before digging "
          "the north end of the planting, B's footings or a US-290 wall")
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    trunks = [tuple(fp[k]["solutions"][0]["site"]) for k in ("big_oak", "big_oak_2") if fp.get(k, {}).get("solutions")]
    north = (site([BUILDING_LINE[1]])[0], PARCEL[2])   # the fence: back corner to the 45 ft building line
    d_oak = min(seg_dist(tr, *north) for tr in trunks)
    inside = sum(2 * math.sqrt(OAK_NO_DIG ** 2 - seg_dist(tr, *north) ** 2) for tr in trunks if seg_dist(tr, *north) < OAK_NO_DIG)
    check("north-line fence posts vs twin oak no-dig", f"{d_oak:.1f} ft", f"{OAK_NO_DIG:g} ft", "CONFLICT" if d_oak < OAK_NO_DIG else "OK",
          f"~{inside:.0f} ft of the line is inside a trunk's no-dig zone: hand-dig or air-spade those posts, or bridge it")
    check("anything vs tank and drainfield", "not located", "-", "UNKNOWN",
          "every check against them waits on finding the lids and trenches")

    out.parent.mkdir(parents=True, exist_ok=True)
    obj.save(out, f"# {out.name}: written by tools/plan3d.py from {spec.name} and {TERRAIN.name}. Meters, z up.\n"
                  f"# Origin: midpoint of the platted back line, z = 0 at {ground.z0} ft NAVD88; "
                  "+x toward US-290 along the line, +y away from the lot.\n")
    html = out.with_suffix(".html")
    view, poles = backyard(ground, to_m)
    # Front-yard view: from above the street, looking back at the house over loop C.
    fx, fy = to_m(site([st(25, 57)])[0])   # middle of the front lawn
    sx, sy = to_m(site([st(-75, 57)])[0])  # 75 ft out past the front line
    view["front"] = {"eye": [round(sx, 1), round(sy, 1), round(ground(fx, fy) + 28.0, 1)],
                     "at": [round(fx, 1), round(fy, 1), round(ground(fx, fy), 1)]}
    tree_view = {"plants": PLANTS, "stages": ["Planted", "~8 years", "Mature"], "dropped": dropped,
                 "rows_ft": TREE_ROWS, "spacing_ft": TREE_SPACING,
                 "trees": [{"xy": [round(c, 2) for c in to_m(tr["site"])], "plant": tr["plant"]} for tr in trees]}
    existing = canopy.for_viewer(ground) if canopy else None
    # The house, a first pass (house_layout.py), in its own frame: x = -s (east), y = t (north), z up from the floor.
    sv = lambda s, t: to_m(site([st(s, t)])[0])  # noqa: E731
    o, e, n = sv(0, 0), sv(-1, 0), sv(0, 1)
    house = house_spec(lambda s, t: (ground(*sv(s, t)) / FT + ground.z0) - FF_FT)
    house.update({"origin": [round(c, 4) for c in o], "ex": [round((e[i] - o[i]) / FT, 6) for i in (0, 1)],
                  "ey": [round((n[i] - o[i]) / FT, 6) for i in (0, 1)], "ff_m": round((FF_FT - ground.z0) * FT, 3)})
    write_viewer(html, out.read_text(), plan, checks, view, poles, tree_view, existing, ground.z0, building_b, house)
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
