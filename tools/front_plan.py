# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "polars", "rich-click"]
# ///
"""Front-yard study: circle drive and covered parking vs. the building line and the oaks.

The owner's sketch (drawn on the 1991 plat) is transferred to scale. The existing trees come
from the lidar canopy (site/canopy-lidar.json, fetch_canopy.py): crown outlines and treetops.
The lone live oak in the front lawn sits right where a loop would go, so it gets an estimated
trunk and root zone. A revised loop ("C") hugs the house front and leaves the oak in the
island. Options A and B for covered parking stay behind the 45' building line.

Same lot-aligned foot grid as site_plan.py; shapes are given in survey-local (s, t) feet: s
back from the front line, t from the south line toward US-290.

Writes site/front-yard.png and prints the clearances.

Run: uv run tools/front_plan.py
"""

import math

import numpy as np
import polars as pl
import rich_click as click

from front_layout import (
    ASSUMED_DBH_IN, BULGE_OAK, EXISTING_DRIVE, EXISTING_DRIVE_T, FRONT_ELECTRIC, FRONT_WALK, LONE_OAK_BOX,
    LONE_OAK_PHOTO, LOOP_C, LOOP_D, lane_outline,
    NORTH_CARPORT, PORTE_COCHERE,
    SKETCH_BOX, SKETCH_INNER, SKETCH_OUTER, catmull_rom, loop_c_outline,
)
from plan3d import CANOPY, FT, Canopy, Frame
from site_plan import (
    BLUE, BUILDING_LINE, GREEN, MAGENTA, ORANGE, PURPLE, RED, REPO, WHITE, YELLOW,
    Plan, draw_survey, site, st,
)

OUT = REPO / "site" / "front-yard.png"
VIEW = (212, 128, 338, 272)
CYAN = (90, 230, 255)

def st_site(pts):
    return site(st(*q) for q in pts)


def seg_dist(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def poly_dist(p, pts) -> float:
    return min(seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


def area(poly) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


class SurveyFrame:
    """Site ft <-> survey (s, t) ft: st() is an orthonormal frame, so this is a rigid transform."""

    def __init__(self) -> None:
        self.o = np.array(site([st(0, 0)])[0])
        self.es = np.array(site([st(1, 0)])[0]) - self.o
        self.et = np.array(site([st(0, 1)])[0]) - self.o

    def from_site(self, p) -> tuple[float, float]:
        d = np.asarray(p) - self.o
        return float(d @ self.es), float(d @ self.et)


def canopy_in_st(canopy: Canopy, to_m: Frame, sf: SurveyFrame):
    """Each standing canopy cell's center and height, in (s, t) ft."""
    rows, cols = np.nonzero(canopy.h > 0)
    out = []
    for r, c in zip(rows, cols):
        x, y = canopy.x0 + c + 0.5, canopy.y0 + r + 0.5
        out.append((*sf.from_site(to_m.to_site((x, y))), float(canopy.h[r, c]) / FT, r, c))
    return out


@click.command()
def main() -> None:
    """Draw the front-yard study and print the clearances."""
    plan = Plan(view=VIEW)
    plan.grid()
    to_m, sf = Frame(), SurveyFrame()
    canopy = Canopy() if CANOPY.exists() else None

    # Existing canopy (lidar): outline of standing canopy cells, and treetops.
    lone_oak = None
    if canopy is not None:
        h = canopy.h
        for r, c in zip(*np.nonzero(h > 0)):
            x, y = canopy.x0 + c, canopy.y0 + r
            corners = [to_m.to_site(q) for q in ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))]
            if VIEW[0] <= corners[0][0] <= VIEW[2] and VIEW[1] <= corners[0][1] <= VIEW[3]:
                plan.d.polygon([plan.p(*q) for q in corners], fill=(255, 225, 60, 38))
            for (dr, dc), edge in (((-1, 0), ((x, y), (x + 1, y))), ((1, 0), ((x, y + 1), (x + 1, y + 1))),
                                   ((0, -1), ((x, y), (x, y + 1))), ((0, 1), ((x + 1, y), (x + 1, y + 1)))):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h.shape[0] and 0 <= cc < h.shape[1] and h[rr, cc] > 0:
                    continue
                a, b = to_m.to_site(edge[0]), to_m.to_site(edge[1])
                if VIEW[0] <= a[0] <= VIEW[2] and VIEW[1] <= a[1] <= VIEW[3]:
                    plan.d.line([plan.p(*a), plan.p(*b)], fill=(255, 225, 60, 200), width=2)
        cells = canopy_in_st(canopy, to_m, sf)
        (s0, s1), (t0, t1) = LONE_OAK_BOX
        crown = [(s, t, hh) for s, t, hh, _, _ in cells if s0 <= s <= s1 and t0 <= t <= t1]
        w = np.array([hh for _, _, hh in crown])
        lone_oak = {
            "trunk": (float(np.average([s for s, _, _ in crown], weights=w)),
                      float(np.average([t for _, t, _ in crown], weights=w))),
            "height": float(w.max()), "crown_r": math.sqrt(len(crown) / FT**2 / math.pi),
        }

    draw_survey(plan)
    plan.line(st_site(FRONT_ELECTRIC), YELLOW, width=2, dash=True)

    # Existing drive and walk (1991 plat, +/-3 ft).
    plan.poly(st_site(EXISTING_DRIVE), (235, 235, 225), fill=(235, 235, 225, 70), width=3)
    plan.poly(st_site(FRONT_WALK), (235, 235, 225), fill=(235, 235, 225, 70), width=2)

    # Owner's sketch.
    outer, inner = catmull_rom(SKETCH_OUTER), catmull_rom(SKETCH_INNER)
    plan.line(st_site(outer), RED, width=3)
    plan.line(st_site(inner), RED, width=3)
    plan.poly(st_site(SKETCH_BOX), ORANGE, fill=(255, 150, 40, 45), width=3)

    # Options behind the line.
    plan.poly(st_site(PORTE_COCHERE), GREEN, fill=(80, 220, 120, 60), width=3, dash=True)
    plan.poly(st_site(NORTH_CARPORT), GREEN, fill=(80, 220, 120, 60), width=3, dash=True)

    # Loop C, and loop D through the open path (owner's photos, Oct 18).
    loop_c = loop_c_outline()
    plan.poly(st_site(loop_c), CYAN, fill=(90, 230, 255, 70), width=4)
    loop_d = lane_outline(LOOP_D)
    plan.poly(st_site(loop_d), MAGENTA, fill=(255, 90, 230, 60), width=4)

    # Trunks placed from the photos (+/-8 ft), with the assumed root zone.
    for (ts, tt), name, (ls, lt) in ((BULGE_OAK, "bulge oak (photos)", (-4, 9)), (LONE_OAK_PHOTO, "lone oak (street photo)", (2, -6))):
        ring = [(ts + ASSUMED_DBH_IN * math.cos(a / 36 * 2 * math.pi), tt + ASSUMED_DBH_IN * math.sin(a / 36 * 2 * math.pi))
                for a in range(37)]
        plan.line(st_site(ring), MAGENTA, width=2, dash=True)
        cx, cy = plan.p(*site([st(ts, tt)])[0])
        plan.d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=MAGENTA, outline=WHITE, width=2)
        lx, ly = site([st(ts + ls, tt + lt)])[0]
        plan.label(lx, ly, name, fill=(255, 170, 240), size=14)

    # The lone lawn oak: estimated trunk (crown's center) and its root zone at an assumed size.
    if lone_oak:
        ts, tt = lone_oak["trunk"]
        cz = ASSUMED_DBH_IN  # ft radius
        ring = [(ts + cz * math.cos(a / 36 * 2 * math.pi), tt + cz * math.sin(a / 36 * 2 * math.pi)) for a in range(37)]
        plan.line(st_site(ring), (255, 120, 60), width=3, dash=True)
        cx, cy = plan.p(*site([st(ts, tt)])[0])
        plan.d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(255, 120, 60), outline=WHITE, width=2)
        lx, ly = site([st(ts - 3, tt + 22)])[0]
        plan.label(lx, ly, f"lone lawn oak, ~{lone_oak['height']:.0f} ft\ntrunk estimated (tape it)\n"
                           f"root zone ~{cz:.0f} ft (assumed {ASSUMED_DBH_IN:.0f} in trunk)",
                   fill=(255, 170, 120), size=15)

    bl = site(BUILDING_LINE)
    plan.line(bl, PURPLE, width=4)
    plan.label(bl[1][0] - 8, 131, "45' building line (plat)", fill=PURPLE, size=18)

    plan.label(222.5, 179, "garage ->\nkitchen?", fill=(160, 210, 255), size=16)
    plan.label(216, 222, "HOUSE", fill=(160, 210, 255), size=24)
    plan.label(279, 236, "your sketch (red)", fill=(255, 160, 140), size=16)
    plan.label(222, 248, "A: porte-cochere behind the line\n~12 x 44 ft, 2 cars nose-to-tail", fill=(150, 255, 170), size=15)
    plan.label(226, 133, "B: carport on the old garage\napron ~23 x 24 ft (live oaks)", fill=(150, 255, 170), size=15)
    cx, cy = site([st(14, 26)])[0]
    plan.label(cx, cy, "C: new curb cut in the open\nsouth lawn; lane hugs the porch,\njoins the existing drive", fill=CYAN, size=15)
    dx, dy = site([st(37, 66)])[0]
    plan.label(dx, dy, "D: C's south leg, then the\nopen path between the oaks\nto the existing drive", fill=(255, 170, 240), size=14)
    plan.label(300, 262, "1991 electric\n(locate)", fill=YELLOW, size=15)
    dx, dy = site([st(20, 104)])[0]
    plan.label(dx, dy, "existing drive\n(1991 plat, +/-3 ft)", fill=(235, 235, 225), size=15)
    wx, wy = site([st(8, 47)])[0]
    plan.label(wx, wy, "walk", fill=(235, 235, 225), size=14)
    plan.label(311, 200, "Candelaria\nDr", fill=WHITE, size=16)
    plan.label(214, 266, "Yellow = tree canopy (2017 lidar, still standing). Grid = 10 ft. Up = NNE.", size=15)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    click.echo(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")

    if lone_oak:
        ts, tt = lone_oak["trunk"]
        click.echo(f"lone lawn oak: crown ~{lone_oak['height']:.0f} ft tall, ~{lone_oak['crown_r']:.0f} ft radius; "
                   f"trunk estimated at s {ts:.0f} ft, t {tt:.0f} ft (crown center, +/-6 ft: tape it)")
        rows = [
            {"layout": "your sketch", "paving to the oak's trunk (ft)": round(poly_dist((ts, tt), inner), 1),
             "new curb cut, middle (t ft)": round((SKETCH_INNER[0][1] + SKETCH_OUTER[0][1]) / 2, 1),
             "new paving (sq ft)": round(area(outer + inner[::-1]))},
            {"layout": "C", "paving to the oak's trunk (ft)": round(poly_dist((ts, tt), loop_c + loop_c[:1]), 1),
             "new curb cut, middle (t ft)": LOOP_C[0][1], "new paving (sq ft)": round(area(loop_c))},
        ]
        for row, lines in zip(rows, ((inner, outer), (loop_c + loop_c[:1],))):
            row["to the lone oak, photo (ft)"] = round(min(poly_dist(LONE_OAK_PHOTO, ln) for ln in lines), 1)
            row["to the bulge oak, photos (ft)"] = round(min(poly_dist(BULGE_OAK, ln) for ln in lines), 1)
        rows.append({"layout": "D", "paving to the oak's trunk (ft)": round(poly_dist((ts, tt), loop_d + loop_d[:1]), 1),
                     "new curb cut, middle (t ft)": LOOP_D[0][1], "new paving (sq ft)": round(area(loop_d)),
                     "to the lone oak, photo (ft)": round(poly_dist(LONE_OAK_PHOTO, loop_d + loop_d[:1]), 1),
                     "to the bulge oak, photos (ft)": round(poly_dist(BULGE_OAK, loop_d + loop_d[:1]), 1)})
        with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True):
            click.echo(pl.DataFrame(rows))
        click.echo(f"root zone assumed {ASSUMED_DBH_IN:.0f} ft; curb cuts {EXISTING_DRIVE_T - LOOP_C[0][1]:.0f} ft apart "
                   f"(C); C to the 1991 electric line {min(seg_dist(q, *FRONT_ELECTRIC) for q in loop_c):.0f} ft")


if __name__ == "__main__":
    main()
