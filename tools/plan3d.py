# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
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
import copy
import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import rich_click as click

from site_plan import BUILDING_LINE, HOUSE, PARCEL, REPO, SITE_B, WELL, en_to_site, north_line_y, site, st
from site_b_plan import HOSE, house_north_y
from drive_layout import (
    CURB, CUT_SLOPE, ROAD, ROAD_LINES, ROAD_T, SLAB_OVER_LOW, SLAB_SECTION, SWALE, SWALE_DROP, aprons_a,
    layout as drive_layout,
)
from front_layout import EXISTING_DRIVE, FRONT_WALK, offset
from house_layout import FF_FT, house_spec, porte_spec
from envelope_plan import SITE_A

SPEC = REPO / "property_total_plan.jsonc"
TERRAIN = REPO / "site" / "terrain-lidar.json"
TERRAIN_FINE = REPO / "site" / "terrain-lidar-shed.json"   # fetch_terrain.py: the 1 m DEM round building A; optional
FEATHER = 3.0  # m: the fine patch blends into the 5 m grid over this much of its edge, so the two meet without a seam
DUG = 0.03     # m: ground cut deeper than this below the lidar's is drawn as the excavation
FOCUS_MESH = 0.2   # m: the close-up's ground squares round the cut (the whole site's are 0.5 m)
SHED_OUT = REPO / "site" / "shed3d.obj"   # --focus: building A close up
# --focus: the box drawn round building A, in its frame (ft): 30 ft out from the west, south and east walls (40 on the
# west, to take in the meter pole), and 15 ft north, 5 ft past the surveyed line; cut off 0.5 m past the back line.
SHED_BOX = (-40.0, -30.0, 30.0, 15.0)   # ft past the west wall, south wall, east wall, north wall
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
MOWER_IN = 8.0  # ft in from the door wall to the rear axle: the owner's John Deere S130, parked in building A, for scale
# Building A: a common 30 x 30 kit (owner, Oct 24 2026) on 14 ft legs, for boat storage (owner, Oct 25: a 12 ft door
# clears most wake boats with the tower folded and pontoons with the bimini down, and a roll-up wants ~2 ft over it).
# Its doors are all in its south wall, now a gable end (owner, Oct 28: the front face in the dealer's configurator), so
# the ridge runs north-south, square to the line: a 12 x 12 roll-up for a boat at the west end, a 10 x 8 at the east
# end, and the walk door between them, ~1'1" from each. Feet east of the SW corner (the wall is 30 ft wide).
A_EAVE = 14.0           # ft: the kit's leg height
A_DOORS = ((7.5, 12.0, 12.0), (23.75, 10.0, 8.0))   # roll-ups: center, width, height; 1'6" and 1'3" of wall at the corners
WALK_AT = 16.125        # the walk door's center
# Its paint, from the owner's configurator (Oct 28 2026): burgundy walls, black trim and a black wainscot ~2.5 ft high,
# light doors. The roof's color isn't shown there: charcoal, assumed.
A_COLORS = {"wall": "#5b2226", "roof": "#3a3c40", "trim": "#1d1d1f", "wainscot": "#1d1d1f", "wainscot_ft": 2.5, "door": "#d9d6c1"}
# It stands on a concrete slab dug into its high side (owner, Oct 24 2026): drive_layout has the levels and the cut.
A_CUT_RUN = SWALE + CUT_SLOPE * 3.5   # ft out from the walls that the graded cut can reach (the NE corner is cut ~3 ft)
WALL_FOOTING = 2.0  # ft inside the line for a US-290 wall footing
TREE_ROWS = (10.0, 22.0)  # ft in from the back line: two staggered rows (notes, back-line trees)
TREE_SPACING = 10.0  # ft on center along each row (holly screen 8-10 ft)
TREE_SIDE_INSET = 6.0  # ft in from the side lines
OAK_NO_DIG = 12.0  # ft around the twin oak
GAP_HEIGHT = 4.5  # m (15 ft): a planned spot under standing canopy this tall already has a tree; plant the gaps only
CANOPY_CELL = 3  # existing trees are drawn per 3 x 3 m block of the 1 m canopy grid
DETAIL_MARGIN = 8.0  # ...but in more detail on our lot and this far (m) past its lines, so crowns over the line stay whole
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
    """Bilinear ground height (m above the origin's ground) from the lidar grid; clamped at its edges. Where the finer
    patch covers it (TERRAIN_FINE: 1 m round building A), the patch, blended in over FEATHER m from its edges."""

    def __init__(self, path: Path, fine: Path | None = TERRAIN_FINE) -> None:
        d = json.loads(path.read_text())
        self.xs, self.ys, self.z0 = d["x_m"], d["y_m"], d["z0_ft"]
        self.z = [[(v - self.z0) * FT for v in row] for row in d["z_ft"]]
        self.fine = None
        if fine is not None and fine.exists():
            f = json.loads(fine.read_text())
            self.fine = (f["x_m"], f["y_m"], [[(v - self.z0) * FT for v in row] for row in f["z_ft"]])
        self.cuts: list[tuple[list[Pt], tuple[float, float, float, float], object]] = []   # graded areas: see cut()

    @staticmethod
    def _cell(axis: list[float], v: float) -> tuple[int, float]:
        v = min(max(v, axis[0]), axis[-1])
        i = min(max(bisect.bisect_right(axis, v) - 1, 0), len(axis) - 2)
        return i, (v - axis[i]) / (axis[i + 1] - axis[i])

    def __call__(self, x: float, y: float) -> float:
        z = self.natural(x, y)
        for poly, (x0, y0, x1, y1), level in self.cuts:
            if x0 <= x <= x1 and y0 <= y <= y1 and inside((x, y), poly):
                z = min(z, level(x, y))
        return z

    def cut(self, poly: list[Pt], level) -> None:
        """Dig the ground down to level(x, y) (m) inside poly (plan m). Everything that asks for the ground sees it, and
        the terrain mesh is drawn finer around it."""
        self.cuts.append((poly, (min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)), level))

    @classmethod
    def _bilinear(cls, xs: list[float], ys: list[float], z: list[list[float]], x: float, y: float) -> float:
        i, tx = cls._cell(xs, x)
        j, ty = cls._cell(ys, y)
        return ((1 - tx) * (1 - ty) * z[j][i] + tx * (1 - ty) * z[j][i + 1]
                + (1 - tx) * ty * z[j + 1][i] + tx * ty * z[j + 1][i + 1])

    def natural(self, x: float, y: float) -> float:
        """The lidar ground, before any cut."""
        z = self._bilinear(self.xs, self.ys, self.z, x, y)
        if self.fine:
            fx, fy, fz = self.fine
            edge = min(x - fx[0], fx[-1] - x, y - fy[0], fy[-1] - y)
            if edge > 0:
                z += min(edge / FEATHER, 1.0) * (self._bilinear(fx, fy, fz, x, y) - z)
        return z

    def fine_box(self) -> tuple[float, float, float, float] | None:
        """The fine patch's extent (x0, y0, x1, y1, plan m), if there is one."""
        return (self.fine[0][0], self.fine[1][0], self.fine[0][-1], self.fine[1][-1]) if self.fine else None



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
        self.clip: list[Pt] | None = None   # --focus: only what falls inside this plan polygon is written

    def obj(self, name: str) -> None:
        self.lines.append(f"o {name}")

    def _v(self, pts) -> list[int]:
        for x, y, z in pts:
            self.lines.append(f"v {x:.3f} {y:.3f} {z:.3f}")
        self.nv += len(pts)
        return list(range(self.nv - len(pts) + 1, self.nv + 1))

    def face(self, pts) -> None:
        if self.clip and not inside((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)), self.clip):
            return
        self.lines.append("f " + " ".join(map(str, self._v(pts))))

    def polyline(self, pts, closed: bool = False) -> None:
        if self.clip:
            ring = list(pts) + list(pts[:1]) if closed else list(pts)
            run: list = []
            for p in ring + [None]:   # the runs of points inside the clip, each its own polyline
                if p is not None and inside(p[:2], self.clip):
                    run.append(p)
                    continue
                if len(run) > 1:
                    idx = self._v(run)
                    self.lines.append("l " + " ".join(map(str, idx)))
                run = []
            return
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

    def area(self, geom, cell: float = 0.4, z=None, lift: float = 0.06) -> None:
        """A paved area of any shape (a shapely geometry in plan m, holes and all) in small squares, on the ground or at z(x, y)."""
        from shapely.geometry import box
        from shapely.prepared import prep
        shape = prep(geom)
        zf = z or (lambda x, y: self.ground(x, y) + lift)
        x0, y0, x1, y1 = geom.bounds
        for i in range(int((x1 - x0) / cell) + 1):
            for j in range(int((y1 - y0) / cell) + 1):
                sq = box(x0 + i * cell, y0 + j * cell, x0 + (i + 1) * cell, y0 + (j + 1) * cell)
                if shape.contains(sq):
                    pieces = [sq]
                elif shape.intersects(sq):   # an edge cell: clipped to the outline, so the edges stay clean
                    cut = geom.intersection(sq)
                    pieces = [g for g in getattr(cut, "geoms", [cut]) if g.geom_type == "Polygon" and g.area > 1e-4]
                else:
                    continue
                for g in pieces:
                    self.face([(a, b, zf(a, b)) for a, b in list(g.exterior.coords)[:-1]])

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

    def terrain(self, fine: float = 0.5) -> None:
        """The ground: one quad per lidar cell. In the cells a cut or the fine patch touches, ~`fine` m squares, clipped
        at the cut's outline so the ground steps down there cleanly (a retaining wall stands on that line); and with a
        clip, cut off at its outline. The dug ground (more than DUG m below the lidar's) goes in its own object after it,
        terrain_excavation, so the viewer can show the cut."""
        from shapely.geometry import Polygon as SPolygon, box as sbox
        g = self.ground
        cuts = [(SPolygon(poly), level, (x0 - 1, y0 - 1, x1 + 1, y1 + 1)) for poly, (x0, y0, x1, y1), level in g.cuts]
        fb, clip = g.fine_box(), SPolygon(self.clip) if self.clip else None
        dug = []
        for j in range(len(g.ys) - 1):
            for i in range(len(g.xs) - 1):
                x0, x1, y0, y1 = g.xs[i], g.xs[i + 1], g.ys[j], g.ys[j + 1]
                if clip is not None and not clip.intersects(sbox(x0, y0, x1, y1)):
                    continue
                near = [c for c in cuts if c[2][0] < x1 and c[2][2] > x0 and c[2][1] < y1 and c[2][3] > y0]
                in_fine = fb is not None and fb[0] < x1 and fb[2] > x0 and fb[1] < y1 and fb[3] > y0
                edge = clip is not None and not clip.contains(sbox(x0, y0, x1, y1))
                if not (near or in_fine or edge):
                    self.face([(x0, y0, g.z[j][i]), (x1, y0, g.z[j][i + 1]), (x1, y1, g.z[j + 1][i + 1]), (x0, y1, g.z[j + 1][i])])
                    continue
                nx, ny = math.ceil((x1 - x0) / fine), math.ceil((y1 - y0) / fine)
                for b in range(ny):
                    for a in range(nx):
                        sq = sbox(x0 + (x1 - x0) * a / nx, y0 + (y1 - y0) * b / ny, x0 + (x1 - x0) * (a + 1) / nx, y0 + (y1 - y0) * (b + 1) / ny)
                        if clip is not None:
                            sq = sq.intersection(clip)
                            if sq.is_empty:
                                continue
                        rest = sq
                        for poly, level, _ in near:
                            part = sq.intersection(poly)
                            for piece in getattr(part, "geoms", [part]):
                                if piece.geom_type == "Polygon" and piece.area > 1e-6:
                                    # split along the line where the cut meets the ground (depth DUG), so the excavation's
                                    # edge follows it rather than the squares
                                    xy = list(piece.exterior.coords)[:-1]
                                    d = [g.natural(x, y) - level(x, y) - DUG for x, y in xy]
                                    for keep, sink in ((lambda v: v > 0, dug.append), (lambda v: v <= 0, self.face)):
                                        ring = []
                                        for k, (pa, da) in enumerate(zip(xy, d)):
                                            pb, db = xy[(k + 1) % len(xy)], d[(k + 1) % len(xy)]
                                            if keep(da):
                                                ring.append(pa)
                                            if (da > 0) != (db > 0):
                                                f = da / (da - db)
                                                ring.append((pa[0] + f * (pb[0] - pa[0]), pa[1] + f * (pb[1] - pa[1])))
                                        if len(ring) >= 3:
                                            sink([(x, y, min(g.natural(x, y), level(x, y))) for x, y in ring])
                            rest = rest.difference(poly)
                        for piece in getattr(rest, "geoms", [rest]):
                            if piece.geom_type == "Polygon" and piece.area > 1e-6:
                                self.face([(x, y, g.natural(x, y)) for x, y in list(piece.exterior.coords)[:-1]])
        if dug:
            self.obj("terrain_excavation")
            for pts in dug:
                self.face(pts)

    def save(self, path: Path, header: str) -> None:
        """Write the OBJ, leaving out objects with nothing in them (a clip can empty them)."""
        out, pending = [], None
        for line in self.lines:
            if line.startswith("o "):
                pending = line
                continue
            if pending and line[0] in "fl":
                out.append(pending)
                pending = None
            out.append(line)
        path.write_text(header + "\n".join(out) + "\n")


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

    def crop(self, x0: float, y0: float, x1: float, y1: float) -> "Canopy":
        """The canopy inside a plan box (m), whole 1 m cells."""
        c0, c1 = max(int(math.floor(x0 - self.x0)), 0), min(int(math.ceil(x1 - self.x0)), self.nx)
        r0, r1 = max(int(math.floor(y0 - self.y0)), 0), min(int(math.ceil(y1 - self.y0)), self.ny)
        out = copy.copy(self)
        out.x0, out.y0, out.nx, out.ny, out.h = self.x0 + c0, self.y0 + r0, c1 - c0, r1 - r0, self.h[r0:r1, c0:c1]
        return out

    def clear(self, poly: list[Pt], outside: bool = False) -> None:
        """Take out the trees inside a plan polygon (cleared to build), or with `outside`, everywhere but inside it."""
        import shapely
        xx, yy = np.meshgrid(self.x0 + 0.5 + np.arange(self.nx), self.y0 + 0.5 + np.arange(self.ny))
        hit = shapely.contains_xy(shapely.Polygon(poly), xx, yy)
        self.h = np.where(hit != outside, 0.0, self.h)

    def at(self, x: float, y: float, r: float = 1.0) -> float:
        """Tallest standing canopy within r m of a plan point; 0 off the grid."""
        c0, c1 = max(int(x - r - self.x0), 0), int(x + r - self.x0) + 1
        r0, r1 = max(int(y - r - self.y0), 0), int(y + r - self.y0) + 1
        w = self.h[r0:r1, c0:c1]
        return float(w.max()) if w.size else 0.0

    def for_viewer(self, ground: "Terrain", k: int = CANOPY_CELL, lot: list[Pt] | None = None,
                   trunks: list[tuple[float, float, float]] = ()) -> dict:
        """Blocks of k m (ground and canopy height packed as bytes) and treetops, for the viewers.

        With `lot` (a plan polygon), also the 1 m cells around it, so the viewer can draw the trees on our lot (and
        DETAIL_MARGIN past its lines) in more detail; `trunks` are surveyed trunks there (plan x, y and diameter, m),
        drawn instead of nearby treetops.
        """
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
        out = {"x0": self.x0, "y0": self.y0, "cell": k, "nx": nx, "ny": ny, "zmin": round(zmin, 2), "step": step,
               "zg": pack((zg - zmin) / step), "h": pack(h / step), "tops": tops, "source": self.source}
        if lot:
            # The 1 m cells over the lot's box, the margin and a block beyond, so every block drawn in detail is covered.
            pad = int(math.ceil(DETAIL_MARGIN)) + k
            c0 = max(int(math.floor(min(p[0] for p in lot) - self.x0)) - pad, 0)
            c1 = min(int(math.ceil(max(p[0] for p in lot) - self.x0)) + pad, self.nx)
            r0 = max(int(math.floor(min(p[1] for p in lot) - self.y0)) - pad, 0)
            r1 = min(int(math.ceil(max(p[1] for p in lot) - self.y0)) + pad, self.ny)
            zl = np.array([[ground(self.x0 + c + 0.5, self.y0 + r + 0.5) for c in range(c0, c1)] for r in range(r0, r1)])
            zlmin = float(zl.min())
            out["lot"] = {"x0": self.x0 + c0, "y0": self.y0 + r0, "nx": c1 - c0, "ny": r1 - r0, "zmin": round(zlmin, 2),
                          "zg": pack((zl - zlmin) / step), "h": pack(self.h[r0:r1, c0:c1] / step),
                          "poly": [[round(c, 2) for c in p] for p in lot], "margin": DETAIL_MARGIN,
                          "trunks": [[round(x, 2), round(y, 2), round(float(ground(x, y)), 2), round(d, 2)] for x, y, d in trunks]}
        return out


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
                 poles: list[dict], trees: dict, canopy: dict | None, z0_ft: float, building_b: dict | None,
                 house: dict | None, building_a: dict, focus: dict | None = None) -> None:
    """Fill the viewer template with the model, the plan's entity notes, the checks, the back-yard view, the poles,
    the trees, buildings B's and A's placement and the house (the viewer draws them in detail). `focus` makes it the
    close-up page: its title, views, labels and stored-view key."""
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
            .replace("/*BUILDING_A*/", json.dumps(building_a))
            .replace("/*HOUSE*/", json.dumps(house))
            .replace("/*FOCUS*/", json.dumps(focus)))
    if focus:
        head = head.replace("<title>Candelaria 3D Plan</title>", f"<title>{focus['title']}</title>")
        body = body.replace("<h1>Candelaria 3D Plan</h1>", f"<h1>{focus['title']}</h1>").replace(
            '<p class="sub">8400 Candelaria Dr, building B, and the retail and apartment lots behind it.</p>',
            f'<p class="sub">{focus["sub"]}</p>')
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
@click.option("--out", type=click.Path(path_type=Path), default=None, help=f"[default: {OUT.relative_to(REPO)}, or {SHED_OUT.relative_to(REPO)} with --focus]")
@click.option("--focus", is_flag=True, help="Building A close up: it and the ground ~30 ft round it, on its own page.")
def main(spec: Path, out: Path | None, focus: bool) -> None:
    """Build the 3D plan on the lidar terrain and run the septic checks."""
    out = out or (SHED_OUT if focus else OUT)
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

    # Building A's cut (owner, Oct 24 2026): its slab's top SLAB_OVER_LOW over the SW corner's ground, so the high NE side
    # is dug down. Round the north, east and west walls the ground is dug to a SWALE ft swale SWALE_DROP under the slab,
    # then graded back at CUT_SLOPE:1 up to the natural ground; within 10 ft of the septic pipe it stops at a block wall
    # instead. It's registered before the ground is drawn, so the terrain and walking see it.
    a_m = [to_m(p) for p in SITE_A]
    anw, ane, ase, asw = a_m
    a_len, a_wid = math.dist(asw, ase) / FT, math.dist(asw, anw) / FT
    a_ux = ((ase[0] - asw[0]) / (a_len * FT), (ase[1] - asw[1]) / (a_len * FT))
    a_uy = ((anw[0] - asw[0]) / (a_wid * FT), (anw[1] - asw[1]) / (a_wid * FT))
    a_pt = lambda x, y: (asw[0] + (a_ux[0] * x + a_uy[0] * y) * FT, asw[1] + (a_ux[1] * x + a_uy[1] * y) * FT)  # noqa: E731
    a_yft = lambda x, y: ((x - asw[0]) * a_uy[0] + (y - asw[1]) * a_uy[1]) / FT  # noqa: E731   # ft north of the south wall
    a_xft = lambda x, y: ((x - asw[0]) * a_ux[0] + (y - asw[1]) * a_ux[1]) / FT  # noqa: E731   # ft east of the SW corner
    a_top = ground(*asw) + SLAB_OVER_LOW * FT   # the slab's top (m)

    def cut_level(x: float, y: float) -> float:
        u, v = a_xft(x, y), a_yft(x, y)
        d = math.hypot(max(-u, 0.0, u - a_len), max(-v, 0.0, v - a_wid))   # ft out from the walls
        if d == 0:
            return a_top - SLAB_SECTION * FT
        return a_top - SWALE_DROP * FT + max(d - SWALE, 0.0) / CUT_SLOPE * FT

    from shapely.geometry import Point as SPoint, Polygon as SPolygon
    from shapely.ops import unary_union
    R = A_CUT_RUN
    zone = SPolygon([(-R, -2.0), (0.0, -2.0), (0.0, 0.0), (a_len, 0.0), (a_len, -2.0), (a_len + R, -2.0),
                     (a_len + R, a_wid + R), (-R, a_wid + R)])   # open in front of the doors, where the aprons are
    pipe_a = (a_xft(*to_m(pipe)), a_yft(*to_m(pipe)))
    zone = zone.difference(SPoint(pipe_a).buffer(KEEP_OUT, 48))
    cut_poly = [a_pt(x, y) for x, y in list(zone.exterior.coords)[:-1]]
    ground.cut(cut_poly, cut_level)
    # What's cleared to build it: the cut and its slopes, the slab and the aprons. The trees standing there come out.
    cleared = zone.union(unary_union([SPolygon(q) for q in aprons_a(a_len)])).buffer(0.5)
    cleared = [a_pt(x, y) for x, y in list(cleared.exterior.coords)[:-1]]
    # --focus: everything from here on is cut off at the box round building A (SHED_BOX), and 0.5 m past the back line.
    bw, bs, be, bn = SHED_BOX
    crop = SPolygon([a_pt(x, y) for x, y in ((bw, bs), (a_len + be, bs), (a_len + be, a_wid + bn), (bw, a_wid + bn))])
    crop = list(crop.intersection(SPolygon([(-1e4, -1e4), (1e4, -1e4), (1e4, 0.5), (-1e4, 0.5)])).exterior.coords)[:-1]
    if focus:
        obj.clip = crop
    obj.obj("terrain_lidar_2017")
    obj.terrain(FOCUS_MESH if focus else 0.5)

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
                  "mower": None}   # site B is out (owner, Oct 18 2026): the mower moved to building A
    # Site A (envelope_plan.py): the building's site since site B was dropped (owner, Oct 18 2026). 30 x 35 ft, a
    # standard kit size, between the well and the septic pipe, 5 ft inside the line.
    a_m = [to_m(p) for p in SITE_A]
    anw, ane, ase, asw = a_m
    a_len, a_wid = math.dist(asw, ase) / FT, math.dist(asw, anw) / FT   # along the line; across the strip (the span)
    a_dims = f"{a_wid:.0f}x{a_len:.0f}"
    obj.obj(f"site_A_footprint_{a_dims}")
    obj.pad(a_m, cell=0.5, lift=0.07)
    obj.drape(a_m, closed=True, lift=0.12)
    # Building A on it, laid out like a standard kit: 30 x 30, its doors in the south gable end (owner, Oct 28 2026), so
    # its ridge runs north-south, square to the line. It stands on a slab dug into the high side (owner, Oct 24): the
    # ground rises ~3 ft to the NE corner, but the door side is nearly level.
    a_ground = [ground.natural(*p) for p in a_m]
    a_slab = a_top - 0.5 * FT   # the viewer draws a slab's top 0.5 ft over this
    a_id = f"building_A_{a_dims}_eave_{A_EAVE:g}ft_assumed"
    obj.obj(a_id)
    obj.gable(anw, asw, ase, ane, a_top, a_top + A_EAVE * FT, a_len / 2 * B_PITCH * FT)   # the ridge north-south
    # The viewer's frame for it: x south from the north wall (along the ridge), y east from the west wall; the doors are
    # in the end wall at x = length.
    building_a = {"id": a_id, "origin": [round(c, 3) for c in anw],
                  "ux": [round((asw[i] - anw[i]) / (a_wid * FT), 6) for i in (0, 1)],
                  "uy": [round((ane[i] - anw[i]) / (a_len * FT), 6) for i in (0, 1)],
                  "slab_m": round(a_slab, 3), "drop_ft": round((a_slab - min(a_ground)) / FT, 2),
                  "length_ft": round(a_wid, 2), "width_ft": round(a_len, 2), "eave_ft": A_EAVE, "pitch": B_PITCH,
                  "door_wall": "end", "colors": A_COLORS,
                  # Two roll-ups and a commercial walk door between them, all in the south gable end (owner, Oct 28
                  # 2026), feet east of the west wall. Away from the septic access pipe, off the east wall's north half.
                  "doors": [{"center_ft": c, "width_ft": w, "height_ft": h} for c, w, h in A_DOORS],
                  # The walk door: 3070 hollow metal in a welded frame, outswing, hinged on its west edge so the latch
                  # is on the side you come from (the drive arrives from the east).
                  "walk_doors": [{"center_ft": WALK_AT, "width_ft": 3.0, "height_ft": 7.0, "hinge": "west"}],
                  "own_aprons": True,   # drawn below, from drive_layout.aprons_a
                  "mower": {"x_ft": a_wid - MOWER_IN, "y_ft": A_DOORS[1][0]},   # east bay, nose to the door: the west bay is the boat's
                  # For scale: a 22 ft wake boat on its trailer, backed into the west bay (owner, Oct 25 2026: boat storage).
                  "boat": {"x_ft": A_DOORS[0][0], "transom_y_ft": 27.5, "hull_ft": 20.5, "platform_ft": 1.5, "beam_ft": 8.5,
                           "tongue_ft": 5.0}}
    # Existing drive and front walk, traced from the 1991 plat (front_layout.py, +/-3 ft).
    obj.obj("existing_driveway_1991_plat")
    obj.pad([to_m(p) for p in site(st(*q) for q in EXISTING_DRIVE)], lift=0.05)
    obj.obj("front_walk_1991_plat")
    obj.pad([to_m(p) for p in site(st(*q) for q in FRONT_WALK)], cell=0.25, lift=0.05)
    # The drive system, from scratch (drive_layout.py, owner's brief Oct 18 2026): gravel in a stabilizer grid with
    # concrete curbs, pavers under the porte-cochere and concrete street aprons. Building A's doors open onto concrete
    # aprons at grade, with the shop court's gravel round them.
    from shapely.ops import transform
    o_, e_s, e_t = site([st(0, 0)])[0], site([st(1, 0)])[0], site([st(0, 1)])[0]
    to_st = lambda p: tuple(sum((p[k] - o_[k]) * (e[k] - o_[k]) for k in (0, 1)) for e in (e_s, e_t))  # noqa: E731
    sv = lambda s, t: to_m(site([st(s, t)])[0])  # noqa: E731
    plan_m = lambda g: transform(lambda xs, ys, zs=None: tuple(map(list, zip(*[sv(x, y) for x, y in zip(xs, ys)]))), g)  # noqa: E731
    dl = drive_layout([to_st(p) for p in SITE_A])
    # Building A's aprons: planes falling from just under the slab's edge to the lawn at their outer edge, 1% at least.
    sill = a_top - 0.04 * FT
    aprons = []
    for q in aprons_a(a_len):
        (x0, _), (x1, _), (_, y1), _ = q
        foot = ground(*a_pt((x0 + x1) / 2, y1))
        k = max((sill - foot) / (-y1 * FT), 0.01)   # m per m
        aprons.append((SPolygon([a_pt(x, y) for x, y in q]), k))
    obj.obj("proposed_drive_gravel")
    obj.area(plan_m(dl["gravel"]), lift=0.06)
    obj.obj("proposed_drive_pavers")
    obj.area(plan_m(dl["paved"]), lift=0.08)
    obj.obj("proposed_drive_concrete_aprons")
    obj.area(plan_m(dl["concrete"]), lift=0.07)
    obj.obj("proposed_drive_curbs")
    for line in getattr(dl["curbs"], "geoms", [dl["curbs"]]):
        pts = list(line.coords)
        if len(pts) < 2:
            continue
        left, right = ([sv(*q) for q in offset(pts, side * CURB / 2)] for side in (1, -1))
        for (l0, l1), (r0, r1) in zip(zip(left, left[1:]), zip(right, right[1:])):
            obj.face([(x, y, ground(x, y) + 0.11) for x, y in (l0, r0, r1, l1)])
    obj.obj("building_A_aprons")
    for poly, k in aprons:
        obj.area(poly, z=lambda x, y, k=k: max(sill + k * min(a_yft(x, y), 0) * FT, ground(x, y) + 0.03))
    # Building A's retaining wall: segmental block, 12 in deep, just outside the cut's edge wherever the ground there
    # stands more than ~3 in over the cut (by the septic pipe, where the graded slope can't go); its cap course 3 in
    # proud, a buried course below the cut.
    obj.obj("proposed_retaining_wall")
    wall_len, wall_max, wall_pts = 0.0, 0.0, []
    ring = cut_poly + cut_poly[:1]
    for e0, e1 in zip(ring, ring[1:]):
        if max(a_yft(*e0), a_yft(*e1)) <= 0.01:   # the open south side
            continue
        seg = math.dist(e0, e1)
        ex, ey = (e1[0] - e0[0]) / seg, (e1[1] - e0[1]) / seg
        nx, ny = ey, -ex
        mid = ((e0[0] + e1[0]) / 2 + nx * 0.5, (e0[1] + e1[1]) / 2 + ny * 0.5)
        if inside(mid, cut_poly):   # make (nx, ny) point out of the cut
            nx, ny = -nx, -ny
        n = max(1, int(seg / 0.3))
        for k in range(n):
            p0 = (e0[0] + ex * seg * k / n, e0[1] + ey * seg * k / n)
            p1 = (e0[0] + ex * seg * (k + 1) / n, e0[1] + ey * seg * (k + 1) / n)
            q = ((p0[0] + p1[0]) / 2 + nx * 0.1, (p0[1] + p1[1]) / 2 + ny * 0.1)
            h = ground.natural(*q) - cut_level(*q)
            if h < 0.08:
                continue
            wall_len += seg / n / FT
            wall_max = max(wall_max, h / FT)
            wall_pts.append(q)
            obj.prism([p0, p1, (p1[0] + nx * 0.3, p1[1] + ny * 0.3), (p0[0] + nx * 0.3, p0[1] + ny * 0.3)],
                      cut_level(*q) - 0.15, ground.natural(*q) + 0.08)   # 12 in deep units
    # Candelaria Dr (drive_layout.ROAD): very dark asphalt and its white edge lines, drawn straight along the front line
    # (the aerial shows only our frontage; the lots south of us line up with it).
    ts = [ROAD_T[0] + (ROAD_T[1] - ROAD_T[0]) * k / 200 for k in range(201)]   # ~4 ft stations
    obj.obj("candelaria_dr")
    edges = [ROAD[1] + (ROAD[0] - ROAD[1]) * k / 6 for k in range(7)]          # six strips across, so it follows the ground
    for a_s, b_s in zip(edges, edges[1:]):
        obj.ribbon([sv(a_s, t) for t in ts], [sv(b_s, t) for t in ts], lift=0.1)
    obj.obj("candelaria_dr_edge_lines")
    for s_line in ROAD_LINES:
        obj.ribbon([sv(s_line + 0.2, t) for t in ts], [sv(s_line - 0.2, t) for t in ts], lift=0.13)
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
            if gap < 0 and e["type"] not in ("property_line", "easement", "parcels", "utility"):
                check(f"{e['entity_id']} vs {name}", f"{gap + r:.1f} ft", f"{r:g} ft", "CONFLICT")

    # --- Our planned additions vs the septic system (site frame, ft) ---
    fall = (slab - min(ground(*p) for p in b)) / FT
    # Building A: its slab against the natural ground, the door sills, the aprons' falls, the cut's wall vs. the pipe.
    over = {name: (a_top - ground.natural(*q)) / FT for name, q in zip(("NW", "NE", "SE", "SW"), a_m)}
    check("building A's slab over the natural ground, corners", ", ".join(f"{k} {v:+.1f}" for k, v in over.items()) + " ft", "-", "NOTE",
          f"a slab dug into the high side: its top {SLAB_OVER_LOW:g} ft over the SW corner, the NE corner cut {-over['NE']:.1f} ft "
          f"(plus the slab and its base)")
    sills = [(a_top - ground.natural(*a_pt(c, 0.0))) / FT for c in (*(d[0] for d in A_DOORS), WALK_AT)]
    check("building A's door sills over the ground", f"{min(sills):.1f}-{max(sills):.1f} ft", "-", "NOTE",
          "the doors are at grade: the aprons fall " + " and ".join(f"{100 * k:.0f}%" for _, k in aprons) + " to the lawn")
    gap = min(poly_dist(pipe, [to_m.to_site(q) for q in list(poly.exterior.coords)[:-1]]) for poly, _ in aprons)
    check("building A's aprons vs septic pipe", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft", "OK" if gap >= KEEP_OUT else "CONFLICT")
    wall_pipe = min(math.dist(to_m.to_site(q), pipe) for q in wall_pts) if wall_pts else float("inf")
    check("building A's cut", f"wall {wall_len:.0f} ft, up to {wall_max:.1f} ft", "-", "NOTE",
          f"graded back {CUT_SLOPE:g}:1 from a {SWALE:g} ft swale on the north, east and west; a block wall only where the slope "
          "would come within 10 ft of the septic pipe")
    if wall_pts:
        check("building A's retaining wall vs septic pipe", f"{wall_pipe:.1f} ft", f"{KEEP_OUT:g} ft",
              "OK" if wall_pipe >= KEEP_OUT - 0.5 else "CHECK", "it stands on the keep-out's edge: find the tank before digging its footing")
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
    if canopy:   # ...and 2 m more, for the crowns that would hang into the building
        canopy.clear(list(SPolygon(cleared).buffer(2.0).exterior.coords)[:-1])
    trees, dropped = planting(canopy)
    well_in = seg_dist(well, PARCEL[2], PARCEL[3])
    gap = min(math.dist(tr["site"], well) for tr in trees)
    check("back-line trees vs well", f"{gap:.1f} ft", f"{KEEP_OUT:g} ft", "CONFLICT" if gap < KEEP_OUT else "OK",
          f"well is {well_in:.0f} ft in; rows at {TREE_ROWS[0]:g} and {TREE_ROWS[1]:g} ft; "
          f"{dropped['keep_out']} spot(s) left out by the well, {dropped['existing']} already under existing trees")
    check("digging vs buried electric service", "not located", "-", "UNKNOWN",
          "it runs underground from the NW-corner meter pole to the house's NW corner (owner); the route between "
          "isn't known: locate it before digging the planting, B's or A's footings or a US-290 wall")
    # The owner's endpoints, drawn straight (buried_service_line_assumed): what it would cross if it were.
    line = [to_m.to_site(tuple(q)) for q in next(e for e in plan["spatial_entities"]
                                                 if e["entity_id"] == "buried_service_line_assumed")["geometry"]["points_m"]]
    def run_under(poly: list[Pt]) -> float:
        n = 1000
        return sum(inside((line[0][0] + (line[1][0] - line[0][0]) * (k + 0.5) / n,
                           line[0][1] + (line[1][1] - line[0][1]) * (k + 0.5) / n), poly) for k in range(n)) / n * math.dist(*line)
    check("straight service line vs well", f"{seg_dist(well, *line):.1f} ft", "-", "NOTE",
          "the straight pole-to-house line passes over the well, so the real run probably bends around it")
    for label, poly in (("site A", SITE_A), ("building B", SITE_B)):
        u = run_under(poly)
        check(f"straight service line vs {label}", f"{u:.1f} ft under", "0", "CONFLICT" if u > 0 else "OK",
              "if it runs straight: reroute it in conduit, or sleeve it under the slab; locate it first")
    check("site A vs well", f"{poly_dist(well, SITE_A):.1f} ft", f"{KEEP_OUT:g} ft",
          "OK" if poly_dist(well, SITE_A) >= KEEP_OUT else "CONFLICT", f"{a_wid:.0f} x {a_len:.0f} ft, 10 ft inside the line")
    check("site A vs septic pipe", f"{poly_dist(pipe, SITE_A):.1f} ft", f"{KEEP_OUT:g} ft",
          "OK" if poly_dist(pipe, SITE_A) >= KEEP_OUT else "CONFLICT", "the drainfield may run under site A: find it first")
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    trunks = [tuple(fp[k]["solutions"][0]["site"]) for k in ("big_oak", "big_oak_2") if fp.get(k, {}).get("solutions")]
    north = (site([BUILDING_LINE[1]])[0], PARCEL[2])   # the fence: back corner to the 45 ft building line
    d_oak = min(seg_dist(tr, *north) for tr in trunks)
    in_zone = sum(2 * math.sqrt(OAK_NO_DIG ** 2 - seg_dist(tr, *north) ** 2) for tr in trunks if seg_dist(tr, *north) < OAK_NO_DIG)
    check("north-line fence posts vs twin oak no-dig", f"{d_oak:.1f} ft", f"{OAK_NO_DIG:g} ft", "CONFLICT" if d_oak < OAK_NO_DIG else "OK",
          f"~{in_zone:.0f} ft of the line is inside a trunk's no-dig zone: hand-dig or air-spade those posts, or bridge it")
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
                 "trees": [{"xy": [round(c, 2) for c in to_m(tr["site"])], "plant": tr["plant"]} for tr in trees
                           if not focus or inside(to_m(tr["site"]), crop)]}
    # The twin oak's trunks (field data): the near one is 24 in across (6.3 ft around); the second isn't measured yet.
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    oak_trunks = [(*to_m(tuple(fp[key]["solutions"][0]["site"])), 0.61)
                  for key in ("big_oak", "big_oak_2") if fp.get(key, {}).get("solutions")]
    if focus and canopy:
        cx, cy = [p[0] for p in crop], [p[1] for p in crop]
        canopy = canopy.crop(min(cx) - 3, min(cy) - 3, max(cx) + 3, max(cy) + 3)
        canopy.clear(crop, outside=True)
        existing = canopy.for_viewer(ground, lot=crop, trunks=[t for t in oak_trunks if inside(t[:2], crop)])
    else:
        existing = canopy.for_viewer(ground, lot=[to_m(p) for p in PARCEL], trunks=oak_trunks) if canopy else None
    # The house, a first pass (house_layout.py), in its own frame: x = -s (east), y = t (north), z up from the floor.
    sv = lambda s, t: to_m(site([st(s, t)])[0])  # noqa: E731
    o, e, n = sv(0, 0), sv(-1, 0), sv(0, 1)
    house = house_spec(lambda s, t: (ground(*sv(s, t)) / FT + ground.z0) - FF_FT)
    house["porte"] = porte_spec(lambda s, t: (ground(*sv(s, t)) / FT + ground.z0) - FF_FT)
    house.update({"origin": [round(c, 4) for c in o], "ex": [round((e[i] - o[i]) / FT, 6) for i in (0, 1)],
                  "ey": [round((n[i] - o[i]) / FT, 6) for i in (0, 1)], "ff_m": round((FF_FT - ground.z0) * FT, 3)})
    shed = None
    if focus:
        # The close-up page's views (plan m, from points in building A's frame, ft) and labels; the house, building B
        # and the back-yard poles are outside the box.
        at = lambda x, y, h: [round(c, 2) for c in (*a_pt(x, y), ground(*a_pt(x, y)) + h * FT)]  # noqa: E731
        mid = at(a_len / 2, a_wid / 2, 0)
        # Orbiting always turns round the middle of the building, halfway up its walls (owner, Oct 30 2026).
        center = [round(c, 2) for c in (*a_pt(a_len / 2, a_wid / 2), a_top + A_EAVE / 2 * FT)]
        tag = lambda p, h=7.0: [round(c, 2) for c in (*p, ground(*p) + h * FT)]  # noqa: E731
        shed = {"title": "Building A close up",
                "sub": "The shed at site A on its dug-in slab, and the ground ~30 ft round it (2017 lidar, 1 m).",
                "key": "candelaria-shed-3d:view:v1", "fly_m_s": 4.0, "center": center,
                "views": [
                    {"id": "top", "label": "Overhead", "eye": [mid[0] - 0.05, mid[1], mid[2] + 130 * FT], "at": mid, "exag": 1, "mode": "fly"},
                    {"id": "oblique", "label": "From the SE", "eye": at(a_len + 40, -45, 60), "at": center, "mode": "orbit"},
                    {"id": "doors", "label": "At the doors", "eye": at(a_len / 2, -28, 5.5), "at": at(a_len / 2, a_wid, 5.5), "exag": 1, "mode": "look"},
                    {"id": "cut", "label": "The cut, from the east", "eye": at(a_len + 36, a_wid + 14, 24), "at": center, "mode": "orbit"},
                    {"id": "north", "label": "Along the north cut", "eye": at(-10, a_wid + 7, 9), "at": at(a_len + 2, a_wid + 2, 0), "exag": 1, "mode": "look"},
                    {"id": "west", "label": "From the SW", "eye": at(-16, -14, 15), "at": center, "mode": "orbit"},
                ],
                "tags": [["Meter pole: the power", tag((22.6, -1.0), 22.0)],   # electric_meter_pole in the spec
                         ["Well", tag(to_m(well))], ["Septic access pipe (tank?)", tag(to_m(pipe))],
                         ["US-290 →", tag(a_pt(a_len / 2, a_wid + 13), 12.0)]]}
        house = building_b = None
        poles = []
    write_viewer(html, out.read_text(), plan, checks, view, poles, tree_view, existing, ground.z0, building_b, house, building_a, shed)
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
