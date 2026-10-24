# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""Turnkey budget for the steel building at site A: site work, a concrete slab and a tube-frame building.

Tube frame only: the owner ruled out red-iron (Oct 18 2026; see site/notes.md, "Tube frame or red-iron").

The building is a common 30 x 30 x 11 kit (owner, Oct 24 2026): 30 ft wide, the most common shop span, across
the strip, 30 ft along it, on 11 ft legs. Its doors are all in the south wall (owner, Oct 18 2026): two 10 x 9
roll-ups and the walk door between them.

It stands on a concrete slab dug into its high side (owner, Oct 24 2026: back to concrete, the costs down; it was
on pier and beam that morning, at ~$85k). The ground under it rises ~2.7 ft to the NE corner, but its door (south)
side is nearly level, so the slab's top sits SLAB_OVER_LOW over the SW corner's ground (`--level`) and the doors are
at grade: short concrete aprons, no ramp. The high side is cut and graded back at 2:1 from a swale, with a block
wall only where the slope would come within 10 ft of the septic pipe (drive_layout.py has the levels and shapes).

The other way, building the low side up, is priced alongside: the slab level with the high corner, the fill under it
held by stem walls, and ramps from the doors down to the lawn at 10%. And the balanced slab of Oct 18, between.

The soil is Brackett (USDA soil survey, map unit BlD: Brackett-Rock outcrop complex): 10-20 in of soil over soft,
weathered limestone, with rock at the surface in places. Cut below `--soil` ft is priced as rock.

Power and insulation are in the total (owner, Oct 24 2026):
- power: the meter and the house's disconnect are on a pole at the NW fence corner, ~40 ft from the building, so it
  gets its own 100 A breaker there and a short feeder, in the same trench as the house's buried line where that has
  to be rerouted round the building (priced too, since a straight run passes under it); a 100 A panel inside, and a
  woodshop's wiring;
- insulation, the high-grade kind for a steel shop: closed-cell spray foam on the walls and under the roof, with a
  thermal barrier over it. Dealer-installed fiberglass blanket is the cheaper way, printed for comparison.

The building comes first and the drive much later (owner, Oct 24 2026), so nothing here is the drive's: the aprons
come down to the lawn, and with no shop lane to drive on, the concrete is pumped in from the old drive and the lawn
and the twin oak's root zone are matted for the crews.

Prices are low/high planning ranges for the Austin area, Oct 2026: published Texas cost guides and county bid
tabulations (sources in site/notes.md, "What the building at site A costs", "Back to a slab" and "Power and
insulation in the budget"). None is a quote.
Get three itemized local bids; the building and the slab are most of the money.

The outer range adds every low and every high, which no real job does. The "likely" figure is the sum of the
midpoints, and its band is where 80% of outcomes land if each line's price falls anywhere in its range
independently (uniform; sd = range / sqrt(12) per line). Prices that move together, like a hot concrete market,
would widen it.

Run: uv run tools/shed_cost.py [--level 0.8] [--soil 1.5]
"""

import math

import polars as pl
import rich_click as click
from shapely.geometry import LineString, Point, Polygon

from drive_layout import CUT_SLOPE, SLAB_OVER_LOW, SLAB_SECTION, SWALE, SWALE_DROP, aprons_a
from envelope_plan import FN, RN, SITE_A
from plan3d import FT, KEEP_OUT, TERRAIN, Frame, Terrain, field_features

LENGTH = DEPTH = 30.0   # ft: the 30 x 30 kit
EAVE = 11.0
SOIL = 1.5              # ft of soil over soft rock (Brackett: 10-20 in)
APPROACH = 0.10         # the steepest fall from a door down to the lawn, for the mower and a boat trailer
STEM_FROM = 1.0         # ft of fill at a slab edge past which it takes a stem wall, not a thickened edge
PITCH = 3 / 12          # the kit's roof
DOORS = 2 * 10 * 9 + 3 * 7   # sq ft of wall the two roll-ups and the walk door take
POLE_M = (22.6, -1.0)   # plan m: the meter pole at the NW fence corner (electric_meter_pole in property_total_plan.jsonc)

# (low, high) dollars, and the unit.
PRICES = {
    "prep": ((1500, 3500), "lot", "Site prep: clear, strip the topsoil, lay out"),
    "locate": ((300, 600), "lot", "Locate the buried service line (private locator)"),
    "permits": ((1500, 4000), "lot", "Permits and plans: county permit, septic (OSSF) review, the slab's engineer"),
    "access": ((1500, 4000), "lot", "Access, no drive yet: a line pump on the old drive for each pour, mats over lawn and oak roots"),
    "soil": ((20, 40), "cu yd", "Dig: soil, spread on the lot (not on the drainfield or the oak roots)"),
    "rock": ((40, 90), "cu yd", "Dig: soft limestone under the soil, ripped with the excavator, hauled off"),
    "fill": ((70, 125), "cu yd", "Fill: crushed limestone, compacted in lifts (under the slab's low side and the aprons)"),
    "slope": ((3, 6), "ft", "Grade the cut back 2:1, erosion blanket and seed"),
    "wall": ((20, 40), "sq ft of face", "Segmental-block wall where the slope can't go (by the septic pipe), base course and cap"),
    "stem": ((70, 140), "ft", "Stem walls where the fill is deep: the slab's edges, the ramps' sides"),
    "drain": ((1500, 3000), "lot", "Swale round the cut sides, a French drain to daylight on the low side, gutters piped away"),
    "slab": ((6, 10), "sq ft", "Slab: 4 in, rebar, thickened edges at the kit's anchors, vapor barrier"),
    "apron": ((8, 13), "sq ft", "Concrete aprons and ramps at the doors, on base, falling to the lawn"),
    "tube": ((15, 26), "sq ft", "Building, installed: tube frame, 11 ft legs, two 10 x 9 roll-ups, the kit's walk door"),
    "walk_door": ((1500, 3000), "lot", "Walk door upgrade, net of the kit door: 3070 hollow metal, welded frame, continuous hinge, "
                                      "Grade 1 lever and deadbolt, closer, stop, seals"),
    # insulation, the high-grade kind
    "foam_walls": ((2.75, 5.0), "sq ft of wall", "Insulation: closed-cell spray foam, 2 in (~R-13), on the walls and gable ends"),
    "foam_roof": ((4.0, 7.0), "sq ft of roof", "Insulation: closed-cell spray foam, 3 in (~R-20), under the roof"),
    "barrier": ((1.25, 2.25), "sq ft", "Thermal barrier over the foam: intumescent coating (IRC R316.4; it's a woodshop)"),
    # power
    "reroute": ((2500, 7000), "lot", "Reroute the house's buried line round the building, if it runs under it: conduit, wire, splices"),
    "pole": ((500, 3000), "lot", "At the meter pole: a 100 A breaker for the building (or a meter-main with spaces; PEC pulls the meter)"),
    "feeder": ((20, 40), "ft", "100 A feeder in PVC, and a spare conduit for data, in the trench shared with the house's line"),
    "panel": ((1200, 2500), "lot", "100 A main-breaker panel in the building, two ground rods"),
    "wiring": ((5000, 9000), "lot", "Wiring in EMT on the frame: LED shop lights, GFCI outlets every ~6 ft, three 240 V circuits, outside lights"),
    # options, and the cheaper insulation
    "doors_insulated": ((3000, 6000), "lot", "Option: insulated sectional doors in place of the roll-ups (then the walls' weak spot)"),
    "minisplit": ((4000, 7500), "lot", "Option: a ductless mini-split, 1.5-2 tons, on one of the 240 V circuits"),
    "fiberglass": ((1.25, 2.5), "sq ft of wall and roof", "Instead of the foam and its barrier: dealer-installed fiberglass blanket, R-13 walls, R-19 roof"),
}
SITE = ("prep", "locate", "permits", "access")
FOUNDATION = ("soil", "rock", "fill", "slope", "wall", "stem", "drain", "slab", "apron")
BUILDING = ("tube", "walk_door")
INSULATION = ("foam_walls", "foam_roof", "barrier")
POWER = ("pole", "feeder", "panel", "wiring")
REROUTE = ("reroute",)
OPTIONS = ("doors_insulated", "minisplit")
CONTINGENCY = 0.10
Z80 = 1.2816  # half-width of an 80% band, in standard deviations


def site_quantities(ground: Terrain, to_m: Frame, level: float, soil: float = SOIL) -> dict:
    """Quantities for the slab at site A with its top `level` ft over the SW corner's ground, from the lidar."""
    gft = lambda p: ground.natural(*to_m(p)) / FT  # noqa: E731
    nw, ne, se, sw = SITE_A
    ux = ((se[0] - sw[0]) / LENGTH, (se[1] - sw[1]) / LENGTH)
    uy = ((nw[0] - sw[0]) / DEPTH, (nw[1] - sw[1]) / DEPTH)
    at = lambda x, y: (sw[0] + ux[0] * x + uy[0] * y, sw[1] + ux[1] * x + uy[1] * y)  # noqa: E731   # A's frame -> site
    base = gft(sw)
    g = lambda x, y: gft(at(x, y)) - base  # noqa: E731   # ground over the SW corner's
    pipe, _, well = field_features()
    line = LineString([RN, FN])
    top, sub = level, level - SLAB_SECTION
    q = {k: 0.0 for k in FOUNDATION}
    q["corners"] = {k: g(*c) for k, c in (("NW", (0, DEPTH)), ("NE", (LENGTH, DEPTH)), ("SE", (LENGTH, 0)), ("SW", (0, 0)))}

    # Under the slab, 0.5 ft cells: dig to the base's bottom, or fill up to it.
    for i in range(int(LENGTH * 2)):
        for j in range(int(DEPTH * 2)):
            d = g((i + .5) / 2, (j + .5) / 2) - sub
            if d > 0:
                q["soil"] += min(d, soil) * 0.25 / 27
                q["rock"] += max(d - soil, 0) * 0.25 / 27
            else:
                q["fill"] -= d * 0.25 / 27
    q["slab"] = LENGTH * DEPTH

    # The cut sides (north, east, west): the swale SWALE_DROP under the slab, then a 2:1 slope up to the ground, or a
    # wall where the slope would come within 10 ft of the septic pipe or the well, or 1 ft of the surveyed line.
    q["wall_len"] = q["wall_max"] = q["h_max"] = 0.0
    edges = ([((x + .5, DEPTH), (0, 1)) for x in range(int(LENGTH))] + [((LENGTH, y + .5), (1, 0)) for y in range(int(DEPTH))]
             + [((0, y + .5), (-1, 0)) for y in range(int(DEPTH))])
    for (x, y), (nx, ny) in edges:
        h = g(x + nx * SWALE, y + ny * SWALE) - (top - SWALE_DROP)
        if h <= 0.25:
            continue
        q["soil"] += SWALE * h / 27
        q["h_max"] = max(q["h_max"], h)
        far = at(x + nx * (SWALE + CUT_SLOPE * h), y + ny * (SWALE + CUT_SLOPE * h))
        if Point(far).distance(line) >= 1.0 and math.dist(far, pipe) >= KEEP_OUT and math.dist(far, well) >= KEEP_OUT:
            q["soil"] += CUT_SLOPE * h * h / 2 / 27
            q["slope"] += 1
        else:
            q["wall"] += h + 0.75   # its face, with a buried course and the cap
            q["wall_len"] += 1
            q["wall_max"] = max(q["wall_max"], h)
    q["drain"] = 1 if q["h_max"] > 0.25 else 0

    # The low sides: where the fill at the slab's edge is deeper than STEM_FROM, a stem wall.
    for (x, y) in ([(k + .5, 0) for k in range(int(LENGTH))] + [(0, k + .5) for k in range(int(DEPTH))]
                   + [(LENGTH, k + .5) for k in range(int(DEPTH))]):
        if sub - g(x, y) > STEM_FROM:
            q["stem"] += 1

    # The aprons (drive_layout.aprons_a), lengthened into ramps where the doors stand high: each falls from the sill to
    # the lawn at APPROACH at most; the base under them is filled up from the ground, and a ramp's sides take stem walls
    # where it stands more than STEM_FROM over the ground.
    q["sills"], q["runs"], q["falls"] = [], [], []
    for (x0, _), (x1, _), (_, y1), _ in aprons_a(LENGTH):
        xc = (x0 + x1) / 2
        run = -y1
        while run < 60 and top - APPROACH * run > g(xc, -run) + 0.05:
            run += 0.5
        fall = max((top - g(xc, -run)) / run, 0.01)
        q["sills"].append(top - g(xc, 0))
        q["runs"].append(run)
        q["falls"].append(fall)
        q["apron"] += (x1 - x0) * run
        for k in range(int(run * 2)):
            r = (k + .5) / 2
            dz = (top - fall * r - SLAB_SECTION) - g(xc, -r)
            q["fill"] += max(dz, 0) * 0.5 * (x1 - x0) / 27
            if dz + SLAB_SECTION > STEM_FROM:
                q["stem"] += 2 * 0.5
    q["pipe"] = Polygon(SITE_A).distance(Point(pipe))
    q["well"] = Polygon(SITE_A).distance(Point(well))
    # The feeder: from the meter pole to the panel inside the building's west wall, a fifth longer than straight for the
    # trench's bends (round the well), plus the rise at each end.
    q["pole"] = Polygon(SITE_A).distance(Point(to_m.to_site(POLE_M)))
    q["feeder"] = round(1.2 * q["pole"] + 6)
    return q


def estimate(q: dict) -> tuple[list[dict], dict]:
    area = LENGTH * DEPTH
    walls = 2 * (LENGTH + DEPTH) * EAVE + DEPTH * DEPTH / 2 * PITCH - DOORS   # the gable ends' triangles; less the doors
    roof = area / math.cos(math.atan(PITCH))
    qty = {**{k: q[k] for k in FOUNDATION}, "prep": 1, "locate": 1, "permits": 1, "access": 1, "tube": area, "walk_door": 1,
           "foam_walls": walls, "foam_roof": roof, "barrier": walls + roof, "reroute": 1, "pole": 1, "feeder": q["feeder"],
           "panel": 1, "wiring": 1, "doors_insulated": 1, "minisplit": 1, "fiberglass": walls + roof}
    rows, sums = [], {}
    for key in (*SITE, *FOUNDATION, *BUILDING, *REROUTE, *POWER, *INSULATION, *OPTIONS, "fiberglass"):
        (lo, hi), unit, label = PRICES[key]
        if round(hi * qty[key], -2) == 0:
            continue
        rows.append({"item": label, "qty": f"{qty[key]:,.0f} {unit}", "low": int(round(lo * qty[key], -2)), "high": int(round(hi * qty[key], -2))})
        sums[key] = (lo * qty[key], hi * qty[key])

    def likely(keys):
        its = [sums[k] for k in keys if k in sums]
        mid = sum((a + b) / 2 for a, b in its) * (1 + CONTINGENCY)
        sd = math.sqrt(sum((b - a) ** 2 / 12 for a, b in its)) * (1 + CONTINGENCY)
        return mid, mid - Z80 * sd, mid + Z80 * sd

    base = (*SITE, *FOUNDATION, *BUILDING, *REROUTE, *POWER, *INSULATION)
    totals = {"range": tuple(sum(sums[k][i] for k in base if k in sums) * (1 + CONTINGENCY) for i in (0, 1)),
              "likely": likely(base), "shell": likely((*SITE, *FOUNDATION, *BUILDING)), "foundation": likely(FOUNDATION),
              "insulation": likely(INSULATION), "power": likely(POWER), "reroute": likely(REROUTE), "options": likely(OPTIONS),
              "fiberglass": likely(("fiberglass",))}
    return rows, totals


@click.command()
@click.option("--level", default=SLAB_OVER_LOW, show_default=True, help="The slab's top over the SW corner's ground (ft).")
@click.option("--soil", default=SOIL, show_default=True, help="Ft of soil over the soft rock; deeper cut is priced as rock.")
@click.option("--detail/--no-detail", default=True, show_default=True, help="Print the line items.")
def main(level: float, soil: float, detail: bool) -> None:
    """Price the building at site A, turnkey, on a slab dug into its high side, and the other ways to set the slab."""
    ground, to_m = Terrain(TERRAIN), Frame()
    k = lambda v: f"${v / 1000:,.0f}k"  # noqa: E731
    fmt = lambda t: f"{k(t[0])} ({k(t[1])}-{k(t[2])})"  # noqa: E731
    cfg = dict(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=95, tbl_width_chars=170,
               tbl_rows=-1, thousands_separator=",")
    q = site_quantities(ground, to_m, level, soil)
    rows, totals = estimate(q)
    if detail:
        c = q["corners"]
        click.echo(f"{DEPTH:g} x {LENGTH:g} x {EAVE:g} ft = {LENGTH * DEPTH:,.0f} sq ft. The ground over the SW corner's: "
                   + ", ".join(f"{n} {v:+.1f}" for n, v in c.items()) + " ft (2017 lidar).")
        click.echo(f"The slab's top {level:g} ft over the SW corner: the NE corner cut {c['NE'] - level:.1f} ft "
                   f"({c['NE'] - level + SLAB_SECTION:.1f} to the base's bottom); door sills "
                   + ", ".join(f"{s:.1f}" for s in q["sills"]) + " ft (west apron, east apron).")
        click.echo(f"Dig {q['soil']:.0f} cu yd of soil and {q['rock']:.0f} of rock (soil {soil:g} ft deep); fill {q['fill']:.0f} cu yd; "
                   f"slope {q['slope']:.0f} ft; wall {q['wall_len']:.0f} ft, up to {q['wall_max']:.1f} ft; stem walls {q['stem']:.0f} ft; "
                   f"aprons {', '.join(f'{r:g}' for r in q['runs'])} ft out, falling {', '.join(f'{100 * f:.0f}%' for f in q['falls'])}.")
        click.echo(f"{q['pipe']:.1f} ft from the septic pipe, {q['well']:.1f} ft from the well, {q['pole']:.0f} ft from the meter pole "
                   f"(a {q['feeder']:.0f} ft feeder).")
        click.echo(f"\nOn a slab dug into the high side, {level:g} ft over the SW corner (the plan)")
        with pl.Config(**cfg):
            click.echo(pl.DataFrame(rows))
    click.echo(f"\nTurnkey, with {CONTINGENCY:.0%} contingency: {fmt(totals['likely'])}, ${totals['likely'][0] / (LENGTH * DEPTH):,.0f}/sq ft; "
               f"all lows to all highs {k(totals['range'][0])}-{k(totals['range'][1])}. Of it:")
    for label, key in (("the building on its slab: site work and access, the slab, cut, aprons, the kit, the walk door", "shell"),
                       ("the house's buried line rerouted round it, if it runs under it", "reroute"),
                       ("power: the breaker at the pole, the feeder, the panel, the wiring", "power"),
                       ("insulation: closed-cell foam and its thermal barrier", "insulation")):
        click.echo(f"  {label}: {fmt(totals[key])}")
    click.echo(f"Fiberglass blanket instead of the foam and barrier: {fmt(totals['fiberglass'])}, saving ~{k(totals['insulation'][0] - totals['fiberglass'][0])}. "
               f"Options, not in the total: insulated doors and a mini-split, {fmt(totals['options'])}.")

    # Dig in, or build up? The same building with its slab at other levels.
    corners = q["corners"]
    cases = [("dig into the high side (the plan)", level), ("balanced cut and fill (the Oct 18 slab)", 1.5),
             ("build the low side up: level with the high corner", round(max(corners.values()) + 0.33, 2))]
    out = []
    for name, lev in cases:
        qq = site_quantities(ground, to_m, lev, soil)
        _, t = estimate(qq)
        out.append({"slab": name, "top over SW (ft)": lev, "dig (cu yd)": f"{qq['soil'] + qq['rock']:.0f}", "fill (cu yd)": f"{qq['fill']:.0f}",
                    "wall / stem (ft)": f"{qq['wall_len']:.0f} / {qq['stem']:.0f}",
                    "door aprons or ramps (ft out)": ", ".join(f"{r:g}" for r in qq["runs"]),
                    "site work and slab": fmt(t["foundation"]), "turnkey, likely": fmt(t["likely"])})
    click.echo("\nDig in, or build up? The same building, its slab at three levels:")
    with pl.Config(**{**cfg, "fmt_str_lengths": 50}):
        click.echo(pl.DataFrame(out))


if __name__ == "__main__":
    main()
