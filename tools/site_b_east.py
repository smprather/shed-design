# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""A 30 x 30 at site B with its doors in the east wall (owner's question, Nov 1 2026): does it fit, can it be dug
into its high side like site A, and can a towed boat get in?

Site B (the old carport spot, dropped Oct 18 2026) sits between the septic pipe's 10 ft keep-out and the twin oak's
drip line, with the 5 ft setback on the north and the house on the south. The building is placed square to the house,
like B was, its north wall on the setback at its NE corner, in two places:
- P1: its east end on the drip line, where B's was;
- P2: slid APRON ft west, so the door aprons stay outside the drip line.

Each is set three ways: built up (the slab level with the high corner), with the doors' corner at grade, and dug in
the way site A is (SLAB_OVER_LOW over the lowest corner). Quantities and costs come from shed_cost.py's model moved
here; the doors are where site A's are, the 12 x 12 at the south end of the wall. The owner's verdict: too close to
the oaks, in too narrow a gap, on too sloped a part of the yard, with no cheap or easy way out of the slope.

Writes site/site-b-east.png and prints the clearances and the levels (2017 lidar, +/-0.5 ft; field shots +/-2 ft).

Run: uv run tools/site_b_east.py
"""

import json
import math

import polars as pl
import rich_click as click
from shapely.geometry import LineString, Point, Polygon

from drive_layout import SLAB_OVER_LOW
from plan3d import A_DOORS, FT, OAK_NO_DIG, TERRAIN, Canopy, Frame, Terrain, field_features
from shed_cost import APPROACH, estimate, site_quantities
from site_b_plan import DRIP, TRUCK
from site_plan import (FENCE_TRACE, HOUSE, PARCEL, RED, REPO, SITE_B, WHITE, YELLOW, Plan, draw_field, draw_survey,
                       north_line_y)

OUT = REPO / "site" / "site-b-east.png"
VIEW = (118, 96, 262, 188)
SIZE = 30.0       # ft: the 30 x 30 kit
SETBACK = 5.0     # ft from the surveyed line, at the NE corner
APRON = 10.0      # ft: the door aprons' depth, east of the east wall
RIG = 50.0        # ft: a pickup and a 22 ft boat's trailer lined up behind the door
TREE = 3.0        # m: canopy taller than this counts as a standing tree
COLORS = {"P1": (255, 150, 60), "P2": (190, 140, 255)}


def footprint(x_e: float) -> list[tuple[float, float]]:
    """NW, NE, SE, SW (site ft) with the east wall at x_e and the NE corner SETBACK ft off the line."""
    (x0, y0), (x1, y1) = PARCEL[2], PARCEL[1]
    y_n = north_line_y(x_e) + SETBACK / math.cos(math.atan2(y1 - y0, x1 - x0))
    return [(x_e - SIZE, y_n), (x_e, y_n), (x_e, y_n + SIZE), (x_e - SIZE, y_n + SIZE)]


def door_point(c: list[tuple[float, float]]):
    """Site ft of a point in the doors' frame: x ft north along the east wall from its SE corner, y ft west."""
    _, ne, se, sw = c
    ux = ((ne[0] - se[0]) / SIZE, (ne[1] - se[1]) / SIZE)
    uy = ((sw[0] - se[0]) / SIZE, (sw[1] - se[1]) / SIZE)
    return lambda x, y: (se[0] + ux[0] * x + uy[0] * y, se[1] + ux[1] * x + uy[1] * y)


def door_frame(c: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The corners in shed_cost's frame, whose doors are in its SE-SW wall: here the east wall, from its SE corner."""
    nw, ne, se, sw = c
    return [sw, nw, ne, se]


def main_table(rows: list[dict]) -> None:
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=80,
                   tbl_width_chars=200, tbl_rows=-1, tbl_cols=-1):
        click.echo(pl.DataFrame(rows))


@click.command()
def main() -> None:
    """Fit the 30 x 30 at site B, doors east; print the clearances and the levels and draw the map."""
    ground, to_m = Terrain(TERRAIN), Frame()
    gft = lambda p: ground.natural(*to_m(p)) / FT  # noqa: E731   # ft over the datum, from the lidar
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    oak1 = tuple(fp["big_oak"]["solutions"][0]["site"])
    pipe, _, _ = field_features()
    fence, house, truck = LineString(FENCE_TRACE), Polygon(HOUSE), Polygon(TRUCK)
    canopy = Canopy()
    k = lambda v: f"${v / 1000:,.0f}k"  # noqa: E731
    fmt = lambda t: f"{k(t[0])} ({k(t[1])}-{k(t[2])})"  # noqa: E731

    east = oak1[0] - DRIP   # the east wall on the drip line
    places = {"P1": east, "P2": east - APRON}
    fits, levels = [], []
    for name, x_e in places.items():
        c = footprint(x_e)
        nw, ne, se, sw = c
        poly = Polygon(c)
        cells = [(nw[0] + i + 0.5, nw[1] + j + 0.5) for i in range(int(SIZE)) for j in range(int(SIZE))]
        trees = sum(canopy.at(*to_m(p), 0.5) > TREE for p in cells) / len(cells)
        fence_off = [fence.distance(Point(x, nw[1])) for x in range(math.ceil(nw[0]), math.floor(ne[0]) + 1)]
        yc = se[1] - A_DOORS[0][0]   # the 12 x 12's middle, A_DOORS[0][0] ft north of the SE corner
        rig = LineString([(x_e, yc), (x_e + RIG, yc)])
        fall = {n: gft(p) for n, p in zip(("NW", "NE", "SE", "SW"), c)}
        lo = min(fall.values())
        fits.append({"": name, "walls (x, y ft)": f"{nw[0]:.0f}-{ne[0]:.0f}, {nw[1]:.0f}-{sw[1]:.0f}",
                     "to the house": f"{poly.distance(house):.1f}", "on the truck spot (sq ft)": f"{poly.intersection(truck).area:.0f}",
                     "to the pipe": f"{poly.distance(Point(pipe)):.1f}", "east wall to the trunk": f"{poly.distance(Point(oak1)):.1f}",
                     "fence off the north wall": f"{min(fence_off):.1f}-{max(fence_off):.1f}",
                     "ground over the low corner (NW NE SE SW)": " ".join(f"{v - lo:+.1f}" for v in fall.values()),
                     "under canopy": f"{trees:.0%}", "boat's line-up to the trunk": f"{rig.distance(Point(oak1)):.1f}"})

        frame, at = door_frame(c), door_point(c)
        for how, level in (("built up: 0.2 ft over the high corner", max(fall.values()) - fall["SE"] + 0.2),
                           ("the doors' corner at grade", 0.2),
                           ("dug in like site A", lo - fall["SE"] + SLAB_OVER_LOW)):
            q = site_quantities(ground, to_m, level, corners=frame)
            _, t = estimate(q)
            ups = []
            for xc, _, _ in A_DOORS:   # an uphill approach from each sill, at APPROACH, until it meets the ground
                run = 0.0
                while run < 60 and level + APPROACH * run < gft(at(xc, -run)) - fall["SE"] - 0.05:
                    run += 0.5
                ups.append(f"{run:.0f} ft, ends {math.dist(at(xc, -run), oak1):.0f}" if run else "-")
            levels.append({"": name, "slab": how, "sills over the ground (ft)": ", ".join(f"{s:+.1f}" for s in q["sills"]),
                           "dig / fill (cu yd)": f"{q['soil'] + q['rock']:.0f} / {q['fill']:.0f}",
                           "wall / stem (ft)": f"{q['wall_len']:.0f} / {q['stem']:.0f}",
                           "uphill approaches (ft from the trunk)": "; ".join(ups),
                           "the building on its slab": fmt(t["shell"]), "turnkey, likely": fmt(t["likely"])})

    click.echo(f"A 30 x 30 at site B, doors east. P1: the east wall on the oak's drip line ({DRIP} ft from the trunk); "
               f"P2: {APRON:g} ft west of that. Feet; 2017 lidar +/-0.5 ft, field shots +/-2 ft. The oak's no-dig ring is "
               f"{OAK_NO_DIG:g} ft.")
    main_table(fits)
    click.echo("\nThe slab three ways (shed_cost.py's model; tree removal and the oak's protection not in it). "
               "Site A, for comparison: $82k likely, $49k the building on its slab.")
    main_table(levels)

    plan = Plan(view=VIEW)
    plan.grid()
    draw_survey(plan)
    draw_field(plan)
    (x0, y0), (x1, y1) = PARCEL[2], PARCEL[1]
    off = SETBACK / math.cos(math.atan2(y1 - y0, x1 - x0))
    plan.line([(VIEW[0], north_line_y(VIEW[0]) + off), (VIEW[2], north_line_y(VIEW[2]) + off)], RED, width=2, dash=True)
    plan.poly(SITE_B, YELLOW, width=2, dash=True)
    plan.poly(TRUCK, (230, 230, 230), fill=(230, 230, 230, 90), width=2)
    for name, x_e in places.items():
        nw, ne, se, sw = footprint(x_e)
        col = COLORS[name]
        plan.poly([nw, ne, se, sw], col, fill=(*col, 50), width=4)
        for xc, w, _ in A_DOORS:
            plan.line([(x_e, se[1] - xc - w / 2), (x_e, se[1] - xc + w / 2)], WHITE, width=9 if w > 10 else 7)
        yc = se[1] - A_DOORS[0][0]
        plan.line([(x_e, yc), (x_e + RIG, yc)], col, width=2, dash=True)
        plan.label(nw[0] + 2, nw[1] + 3 if name == "P2" else sw[1] - 9, f"{name}: 30 x 30, doors east", fill=col, size=20)
    p1 = footprint(places["P1"])
    gap = Polygon(p1).distance(house)
    plan.dim((p1[2][0] - 6, p1[2][1]), (p1[2][0] - 6, p1[2][1] + gap), f"{gap:.0f} ft to\nthe house", at=(p1[2][0] - 15, p1[2][1] + 3.5))
    plan.label(194.5, 161, "septic truck spot", fill=(230, 230, 230), size=15)
    plan.label(150, 101, "dashed yellow: B, 23 x 43 (dropped Oct 18)   dashed red: 5 ft setback", fill=YELLOW, size=15)
    plan.label(212, 160.5, "a rig backing into the 12 x 12\nlines up on the dashed line:\nthrough the oak's no-dig ring",
               fill=WHITE, size=14)
    plan.label(120, 182, "30 x 30 at site B, doors east (study, Nov 1 2026). Grid = 10 ft. Up = NNE (toward US-290).", size=16)
    plan.scale_bar()
    plan.img.save(OUT)
    click.echo(f"\nwrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
