# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""Groundwork for building A (owner, Nov 2 2026): the house's buried power line moved round it, then the crushed-rock
base for its slab, laid out from the surveyed line. The owner may do the base themselves; site/building-a-groundwork.md
is the step-by-step and the parts list, and this script makes its numbers.

- **Layout:** each corner's distance along the surveyed US-290 line from the lot's NW corner and square in from it,
  the diagonals, and the well and the septic pipe as checks.
- **The power line:** the owner's buried line runs from the meter pole at the NW fence corner to the house's NW corner;
  drawn straight it passes over the well and ~24 ft under the building. ROUTE is a new run in conduit round the
  building's back and door sides (found by a least-cost search on a 1 ft grid that keeps 3 ft off the dig, the slab
  and the aprons, 10 ft off the septic pipe and 12 ft off the twin oak, 2 ft inside the lot lines, and avoids the
  well's ring, the planned back-line trees and standing canopy where it can; then straightened into trenchable legs).
  The building's own feeder and a data conduit share its first leg (FEEDER). The real route waits on the locate and
  the sprinkler plan.
- **The base:** STRIP of topsoil off the pad, the high side dug down to the base's bottom, and crushed limestone
  base built up to BASE under the slab's bottom (thicker where the ground is low), PAD_OVER past the slab's edges;
  the same under the door aprons, which fall to the lawn. Plus the swale's French drain to daylight.

All from the 2017 lidar (+/-0.5 ft) and the survey and field shots (+/-2 ft). Writes site/a-groundwork.png.

Run: uv run tools/a_groundwork.py
"""

import math
from itertools import pairwise

import numpy as np
import polars as pl
import rich_click as click
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from drive_layout import CUT_SLOPE, SLAB_OVER_LOW, SWALE, SWALE_DROP, aprons_a
from drive_plan import trees
from envelope_plan import FN, RN, SITE_A
from front_plan import SurveyFrame
from plan3d import CANOPY, FT, KEEP_OUT, TERRAIN, Canopy, Frame, Terrain, field_features, planting
from shed_cost import APPROACH, POLE_M, SOIL
from site_plan import (CYAN, GREEN, MAGENTA, ORANGE, RED, REPO, WHITE, YELLOW, Plan, draw_field, draw_survey,
                       site, st)

OUT = REPO / "site" / "a-groundwork.png"
VIEW = (40, 88, 200, 212)
SIZE = 30.0          # ft: the 30 x 30 kit
SLAB = 4 / 12        # ft: the slab
BASE = 4 / 12        # ft: crushed base under the slab at its thinnest (drive_layout.SLAB_SECTION = SLAB + BASE)
STRIP = 4 / 12       # ft of topsoil and roots stripped off everything the base goes on
PAD_OVER = 1.0       # ft: the base runs this far past the slab's edges, for the forms' stakes
APRON_SLAB = 4 / 12  # ft: the aprons' concrete
TONS_PER_YD = 1.9    # tons of crushed limestone base per compacted cu yd, at its working moisture
WASTE = 1.10         # order this much more
DRAIN_DEEP = 1.0     # ft: the French drain's trench under the swale's floor, 1 ft wide
STONE_TONS = 1.4     # tons of washed 3/4 in stone per cu yd
CELL = 0.5           # ft

# The power line, site ft. The meter pole (shed_cost.POLE_M) to the house's NW corner (field point A), round the back
# strip and the door side. PULL_BOX splits it so neither pull has more than 360 degrees of bends (NEC 352.26).
ROUTE = [(61.8, 105.5), (62.5, 152.0), (78.0, 158.5), (116.0, 197.0), (172.0, 199.0), (178.0, 191.0),
         (178.0, 172.0), (181.5, 169.5)]
PULL_BOX = 3          # index in ROUTE
FEEDER_BRANCH = (62.4, 140.0)   # where the building's feeder and data conduits leave the shared trench
PANEL_AT = (0.0, 20.0)          # the panel's stub-up in building A's frame (ft): x along the door wall, y in from it


def a_frame():
    """Building A's frame: x along the door (SW-SE) wall from its SW corner, y in from it (ft) -> site ft."""
    nw, _, se, sw = SITE_A
    ux = ((se[0] - sw[0]) / SIZE, (se[1] - sw[1]) / SIZE)
    uy = ((nw[0] - sw[0]) / SIZE, (nw[1] - sw[1]) / SIZE)
    return lambda x, y: (sw[0] + ux[0] * x + uy[0] * y, sw[1] + ux[1] * x + uy[1] * y)


def bends(pts: list[tuple[float, float]]) -> float:
    """Degrees of bend along a polyline."""
    out = 0.0
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        h1, h2 = math.atan2(b[1] - a[1], b[0] - a[0]), math.atan2(c[1] - b[1], c[0] - b[0])
        out += abs(math.degrees((h2 - h1 + math.pi) % (2 * math.pi) - math.pi))
    return out


def table(rows: list[dict]) -> None:
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=90,
                   tbl_width_chars=200, tbl_rows=-1, tbl_cols=-1):
        click.echo(pl.DataFrame(rows))


@click.command()
@click.option("--base", "base_in", default=BASE * 12, show_default=True, help="Crushed base under the slab at its thinnest (in).")
@click.option("--strip", "strip_in", default=STRIP * 12, show_default=True, help="Topsoil stripped off (in).")
@click.option("--soil", default=SOIL, show_default=True, help="Ft of soil over the soft limestone (Brackett: 10-20 in).")
def main(base_in: float, strip_in: float, soil: float) -> None:
    """Print the layout ties, the power route and the base's quantities, and draw the map."""
    global BASE, STRIP
    BASE, STRIP = base_in / 12, strip_in / 12
    ground, to_m, sf = Terrain(TERRAIN), Frame(), SurveyFrame()
    gft = lambda p: ground.natural(*to_m(p)) / FT  # noqa: E731   # lidar ground, ft over the datum
    at = a_frame()
    nw, ne, se, sw = SITE_A
    pipe, oak, well = field_features()
    pole = to_m.to_site(POLE_M)
    bldg = Polygon(SITE_A)
    top = gft(sw) + SLAB_OVER_LOW   # the slab's top
    click.echo(f"Building A, 30 x 30, its slab's top {SLAB_OVER_LOW:g} ft over the SW corner's ground "
               f"({top + ground.z0:.1f} ft NAVD88, 2017 lidar +/-0.5 ft).")

    # --- Layout: from the lot's NW corner along the surveyed north line, and square in from it ---
    u = np.subtract(FN, RN) / np.linalg.norm(np.subtract(FN, RN))
    n = np.array([-u[1], u[0]])
    if np.dot(np.subtract(np.mean(SITE_A, axis=0), RN), n) < 0:
        n = -n
    rows = []
    for name, c in zip(("NW", "NE", "SE", "SW"), SITE_A):
        d = np.subtract(c, RN)
        rows.append({"corner": name, "along the line from the NW lot corner": f"{d @ u:.1f}",
                     "square in from the line": f"{d @ n:.1f}", "to the well": f"{math.dist(c, well):.1f}",
                     "to the septic pipe": f"{math.dist(c, pipe):.1f}", "to the meter pole": f"{math.dist(c, pole):.1f}",
                     "ground over the SW corner's": f"{gft(c) - gft(sw):+.1f}"})
    click.echo("\nLayout (ft; the line and its NW corner from the 1991 survey, staked first; the well and pipe +/-2 ft). "
               f"Diagonals {math.dist(nw, se):.2f} and {math.dist(ne, sw):.2f} ft:")
    table(rows)

    # --- What's dug: the cut and its 2:1 slopes, the slab and the aprons ---
    quads = []
    for (x, y), (nx, ny), (tx, ty) in ([((k, SIZE), (0, 1), (1, 0)) for k in range(int(SIZE))]
                                        + [((SIZE, k), (1, 0), (0, 1)) for k in range(int(SIZE))]
                                        + [((0, k), (-1, 0), (0, 1)) for k in range(int(SIZE))]):
        h = gft(at(x + tx / 2 + nx * SWALE, y + ty / 2 + ny * SWALE)) - (top - SWALE_DROP)
        r = SWALE + CUT_SLOPE * max(h, 0.0)
        quads.append(Polygon([at(x, y), at(x + tx, y + ty), at(x + tx + nx * r, y + ty + ny * r), at(x + nx * r, y + ny * r)]))
    aprons = [Polygon([at(*q) for q in a]) for a in aprons_a(SIZE)]
    work = unary_union([bldg, *quads, *aprons]).buffer(0.3).buffer(-0.3)

    # --- The power line ---
    straight = LineString([pole, ROUTE[-1]])
    route = LineString(ROUTE)
    feeder = [*ROUTE[:1], FEEDER_BRANCH, at(*PANEL_AT)]
    sft = [sf.from_site(p) for p in ROUTE]
    tr = [{**t, "site": site([st(*t["st"])])[0]} for t in trees(sf, to_m)]
    near = min(tr, key=lambda t: route.distance(Point(t["site"])))
    can = Canopy(CANOPY)
    steps = np.arange(0.5, route.length, 1.0)
    under = sum(can.at(*to_m(route.interpolate(d).coords[0]), 0.5) > 4.0 for d in steps)
    back = [t["site"] for t in planting()[0]]
    click.echo(f"\nThe house's power line. Drawn straight (the owner's endpoints) it's {straight.length:.0f} ft, passing "
               f"{straight.distance(Point(well)):.1f} ft from the well and {straight.intersection(bldg).length:.0f} ft under the "
               f"building ({straight.intersection(work).length:.0f} ft through the dig, slab and aprons).")
    legs = [{"leg": f"{k + 1}", "from (x, y)": f"{a[0]:.0f}, {a[1]:.0f}", "to": f"{b[0]:.0f}, {b[1]:.0f}",
             "ft": f"{math.dist(a, b):.1f}"} for k, (a, b) in enumerate(pairwise(ROUTE))]
    table(legs)
    first, second = ROUTE[:PULL_BOX + 1], ROUTE[PULL_BOX:]
    click.echo(f"New run: {route.length:.0f} ft of trench, ~{route.length + 12:.0f} ft of conduit with the risers. Bends: "
               f"{bends(first) + 90:.0f} degrees pole to the pull box, {bends(second) + 90:.0f} box to the house (with a 90 at "
               f"each riser; NEC limit 360 between pull points).")
    click.echo(f"Clear of: the dig, slab and aprons by {route.distance(work):.1f} ft; the well {route.distance(Point(well)):.1f}; "
               f"the septic pipe {route.distance(Point(pipe)):.1f}; the twin oak's main trunk {route.distance(Point(oak)):.1f}; the "
               f"back-line tree spots {min(route.distance(Point(p)) for p in back):.1f}; the nearest tree "
               f"({near['name']}) {route.distance(Point(near['site'])):.1f}. Under standing canopy (lidar, > 4 m): {under} ft.")
    click.echo(f"The building's feeder and data conduits share the first {math.dist(ROUTE[0], FEEDER_BRANCH):.0f} ft, then "
               f"branch {math.dist(FEEDER_BRANCH, feeder[-1]):.0f} ft to the panel's stub-up inside the west wall: "
               f"{math.dist(ROUTE[0], FEEDER_BRANCH) + math.dist(FEEDER_BRANCH, feeder[-1]):.0f} ft in all. "
               f"(Survey (s, t) of the route's ends: {sft[0][0]:.0f}, {sft[0][1]:.0f} and {sft[-1][0]:.0f}, {sft[-1][1]:.0f}.)")

    # --- The base: 0.5 ft cells over the slab and PAD_OVER past it ---
    slab_bottom = top - SLAB
    base_bottom = slab_bottom - BASE
    cells = np.arange(-PAD_OVER + CELL / 2, SIZE + PAD_OVER, CELL)
    dig = base = rock = deepest = 0.0
    thick = []
    for x in cells:
        for y in cells:
            g = gft(at(x, y))
            e = max(g - base_bottom, STRIP)          # dig to the base's bottom, or at least strip the topsoil
            t = slab_bottom - (g - e)                # base from the dug ground up to the slab's bottom
            dig += e * CELL * CELL
            base += t * CELL * CELL
            rock += max(e - soil, 0.0) * CELL * CELL
            deepest = max(deepest, e)
            if 0 <= x <= SIZE and 0 <= y <= SIZE:
                thick.append(t)
    a_dig = a_base = a_area = 0.0
    falls = []
    for a in aprons_a(SIZE):
        (x0, _), (x1, _), (_, y1), _ = a
        fall = min(max((top - gft(at((x0 + x1) / 2, y1))) / -y1, 0.01), APPROACH)   # from the sill down to the lawn
        falls.append(fall)
        for x in np.arange(x0 + CELL / 2, x1, CELL):
            for y in np.arange(y1 + CELL / 2, 0, CELL):
                g = gft(at(x, y))
                atop = top - fall * -y
                b_bot = atop - APRON_SLAB - BASE
                e = max(g - b_bot, STRIP)
                a_dig += e * CELL * CELL
                a_base += (atop - APRON_SLAB - (g - e)) * CELL * CELL
                a_area += CELL * CELL
    yd = lambda v: v / 27  # noqa: E731
    tons = lambda v: yd(v) * TONS_PER_YD * WASTE  # noqa: E731
    pad = (SIZE + 2 * PAD_OVER) ** 2
    click.echo(f"\nThe base: {pad:,.0f} sq ft under the slab ({SIZE:g} x {SIZE:g} and {PAD_OVER:g} ft past it), "
               f"{a_area:,.0f} sq ft under the aprons. Topsoil stripped {STRIP * 12:.0f} in; base at least "
               f"{BASE * 12:.0f} in, compacted; under the slab it's {min(thick) * 12:.0f}-{max(thick) * 12:.0f} in thick "
               f"(thickest at the SW corner, where the ground is low). The aprons fall "
               + " and ".join(f"{100 * f:.0f}%" for f in falls) + " from the sills (west, east).")
    q = [{"": "under the slab", "dig (cu yd, in place)": f"{yd(dig):.1f}", "base (cu yd, compacted)": f"{yd(base):.1f}",
          "base to order (tons)": f"{tons(base):.0f}"},
         {"": "under the aprons", "dig (cu yd, in place)": f"{yd(a_dig):.1f}", "base (cu yd, compacted)": f"{yd(a_base):.1f}",
          "base to order (tons)": f"{tons(a_base):.0f}"},
         {"": "in all", "dig (cu yd, in place)": f"{yd(dig + a_dig):.1f}", "base (cu yd, compacted)": f"{yd(base + a_base):.1f}",
          "base to order (tons)": f"{tons(base + a_base):.0f}"}]
    table(q)
    click.echo(f"The deepest dig is {deepest:.1f} ft, at the NE corner; with {soil:g} ft of soil, ~{yd(rock):.1f} cu yd of it is the soft "
               "limestone under it (a loader's bucket rips weathered rock; a hard ledge wants a mini-excavator's rock bucket).")

    # --- The dig round the cut sides, and the swale's French drain ---
    swale = slope = 0.0
    east_from = SIZE
    for (x, y), (nx, ny) in ([((k + .5, SIZE), (0, 1)) for k in range(int(SIZE))] + [((SIZE, k + .5), (1, 0)) for k in range(int(SIZE))]
                             + [((0, k + .5), (-1, 0)) for k in range(int(SIZE))]):
        h = gft(at(x + nx * SWALE, y + ny * SWALE)) - (top - SWALE_DROP)
        if h > 0.25:
            swale += SWALE * h
            slope += CUT_SLOPE * h * h / 2
            if nx == 1:
                east_from = min(east_from, y - 0.5)
    click.echo(f"Round the cut sides: the swale {yd(swale):.1f} cu yd and its 2:1 slope {yd(slope):.1f} cu yd more dig; with the "
               f"pad, {yd(dig + a_dig + swale + slope):.0f} cu yd to spread on the lot (not on the drainfield or the oaks' roots).")
    # The drain: perforated pipe under the swale from where the east side's cut starts, round the NE, NW and SW corners
    # (solid along the west side, where there's little cut), then out to daylight at 1% or more.
    run_in = (SIZE - east_from) + SIZE + SIZE + 3 * SWALE
    start = at(-SWALE / 2, -SWALE / 2)
    invert = top - SWALE_DROP - DRAIN_DEEP - 0.01 * run_in
    best = None
    for ang in range(180, 271, 5):   # away from the building on its low side, between straight out west and straight out front
        for d in np.arange(1.0, 80.0, 1.0):
            q = at(-SWALE / 2 + d * math.cos(math.radians(ang)), -SWALE / 2 + d * math.sin(math.radians(ang)))
            if gft(q) <= invert - 0.01 * d:
                if best is None or d < best[0]:
                    best = (d, ang, q)
                break
    outlet, _, out_pt = best if best else (40.0, 225, at(-30, -30))
    perf = (SIZE - east_from) + SIZE + 2 * SWALE
    stone = perf * 1.0 * DRAIN_DEEP / 27
    click.echo(f"\nThe drain: 4 in perforated pipe in washed stone, {DRAIN_DEEP:g} ft under the swale's floor, falling 1% or more: "
               f"{perf:.0f} ft perforated (the east side's cut and the north side), {SIZE + SWALE:.0f} ft solid down the west side "
               f"and {outlet:.0f} ft solid out to daylight past the SW corner: ~{perf + SIZE + SWALE + outlet:.0f} ft of pipe, "
               f"~{stone:.1f} cu yd ({stone * STONE_TONS * WASTE:.1f} tons) of stone.")

    # --- Map ---
    plan = Plan(view=VIEW)
    plan.grid()
    draw_survey(plan)
    draw_field(plan)
    for c, r, col in ((well, KEEP_OUT, CYAN), (pipe, KEEP_OUT, MAGENTA)):
        x0, y0 = plan.p(c[0] - r, c[1] - r)
        x1, y1 = plan.p(c[0] + r, c[1] + r)
        plan.d.ellipse([x0, y0, x1, y1], outline=col, width=3)
    plan.poly(list(work.exterior.coords)[:-1], ORANGE, fill=(255, 160, 60, 55), width=2)
    pad_c = [at(-PAD_OVER, -PAD_OVER), at(SIZE + PAD_OVER, -PAD_OVER), at(SIZE + PAD_OVER, SIZE + PAD_OVER), at(-PAD_OVER, SIZE + PAD_OVER)]
    plan.poly(pad_c, (200, 200, 200), fill=(220, 220, 220, 70), width=2, dash=True)
    plan.poly(SITE_A, YELLOW, fill=(255, 220, 60, 90), width=4)
    for p in back:
        px, py = plan.p(*p)
        plan.d.ellipse([px - 5, py - 5, px + 5, py + 5], outline=GREEN, width=2)
    plan.line([pole, ROUTE[-1]], RED, width=3, dash=True)
    plan.line(feeder, (255, 120, 40), width=5)
    plan.line([at(-SWALE / 2, east_from), at(SIZE + SWALE / 2, east_from)][1:] + [at(SIZE + SWALE / 2, SIZE + SWALE / 2),
              at(-SWALE / 2, SIZE + SWALE / 2), start, out_pt], CYAN, width=3, dash=True)
    plan.line(ROUTE, WHITE, width=6)
    bx, by = plan.p(*ROUTE[PULL_BOX])
    plan.d.rectangle([bx - 9, by - 9, bx + 9, by + 9], outline=(20, 20, 20), fill=WHITE, width=2)
    px, py = plan.p(*pole)
    plan.d.rectangle([px - 8, py - 8, px + 8, py + 8], fill=WHITE)
    ux, uy = u
    for name, c in zip(("NW", "NE", "SE", "SW"), SITE_A):
        d = np.subtract(c, RN)
        foot = (RN[0] + ux * (d @ u), RN[1] + uy * (d @ u))
        plan.line([foot, c], YELLOW, width=2, dash=True)
        plan.label(c[0] + 1, c[1] - 1.5, name, fill=YELLOW, size=16)
    plan.label(64, 96, "meter pole and the house's disconnect", fill=WHITE, size=16)
    plan.label(83, 104.5, "the line, if straight (owner's ends)", fill=(255, 140, 140), size=15)
    plan.label(66, 120, "shared trench:\nhouse + building + data", fill=WHITE, size=15)
    plan.label(83, 141, "building feeder\nto the panel", fill=(255, 150, 80), size=15)
    plan.label(119, 199.5, "pull box", fill=WHITE, size=15)
    plan.label(130, 192, "new run in conduit to the house's NW corner", fill=WHITE, size=16)
    plan.label(99, 131, "A 30 x 30", fill=(255, 235, 140), size=20)
    plan.label(out_pt[0] - 12, out_pt[1] + 1, "drain to daylight", fill=CYAN, size=15)
    plan.label(42, 201.5, "Building A's groundwork (Nov 2 2026). White: the house's new power run (the box: a pull box). Orange line: "
                          "the building's feeder. Red dashed: the old line if straight.", size=15)
    plan.label(42, 205.5, "Orange area: the dig, slab and aprons. Grey dashed: the base, 1 ft past the slab. Cyan dashed: the drain. "
                          "Yellow dashed: corner ties square to the line. Grid 10 ft; up NNE.", size=15)
    plan.scale_bar()
    plan.img.save(OUT)
    click.echo(f"\nwrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
