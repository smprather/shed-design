# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""Turnkey budget for the steel building at site A: site work, foundation and a tube-frame building.

Tube frame only: the owner ruled out red-iron (Oct 18 2026; see site/notes.md, "Tube frame or red-iron").

The building is a common 30 x 30 x 11 kit (owner, Oct 24 2026): 30 ft wide, the most common shop span, across
the strip from the 5 ft setback line, 30 ft along it, on 11 ft legs. It keeps site A's east end and gives up
5 ft by the well. Its doors are all in the south wall (owner, Oct 18 2026): two 10 x 9 roll-ups and the walk
door between them. `--lengths` prices other standard lengths (35, 25) the same way.

Two foundations, priced side by side:
- piers (the plan, owner Oct 24 2026): a pressure-treated pier-and-beam floor, low at the high NE corner (plan3d.py
  has the framing). The ground falls ~3 ft to the SW, where the doors are, so the floor stands 3.8-4.2 ft over the
  ground at the sills, and a concrete ramp on fill runs down from them to the ground 25 ft out, between concrete
  side walls (drive_layout.approach_a).
- slab (for comparison, as priced Oct 18): a slab cut and filled CUT ft below the high corner (`--cut`), with a
  12 ft concrete apron along the doors near grade.
Quantities come from the 2017 lidar.

Prices are low/high planning ranges for the Austin area, Oct 2026: published Texas cost guides and county bid
tabulations (sources in site/notes.md, "What the building at site A costs" and "Building A on pier and beam").
None is a quote. Get three itemized local bids; the building and the foundation are most of the money.

The outer range adds every low and every high, which no real job does. The "likely" figure is the sum of the
midpoints, and its band is where 80% of outcomes land if each line's price falls anywhere in its range
independently (uniform; sd = range / sqrt(12) per line). Prices that move together, like a hot concrete market,
would widen it.

Run: uv run tools/shed_cost.py
"""

import math

import polars as pl
import rich_click as click
from shapely.geometry import Point, Polygon

from drive_layout import APPROACH_FOOT, approach_a
from envelope_plan import ALONG, line_rect
from plan3d import FT, PB_BEAMS_Y, PB_FLOOR, PB_PIERS_X, TERRAIN, Frame, Terrain

DEPTH = 30.0         # ft, square off the line: the building's width (clear span)
FULL = 35.0          # ft along the line: the site A it was cut from (x 98.6 is that site's NW corner)
X0 = 98.6
LENGTH = 30.0        # ft along the line: the 30 x 30 kit (owner, Oct 24 2026)
EAVE = 11.0
DEEP = 1.5           # ft of fill past which a slab edge gets a stem wall instead of a thickened edge
RETAIN = 0.5         # ft of cut past which a slab edge gets a stem wall to hold the high ground back
CUT = 1.5            # ft: the slab below the footprint's high corner (slab option)
SLAB_APRON = 12.0    # ft: the slab option's apron, out from the south wall
WALL_FROM = 0.75     # ft: the ramp gets a side wall where it stands higher than this over the ground

# (low, high) dollars, and the unit.
PRICES = {
    "prep": ((1500, 3500), "lot", "Site prep: clear, strip the topsoil, lay out"),
    "locate": ((300, 600), "lot", "Locate the buried service line (private locator)"),
    "permits": ((1500, 4000), "lot", "Permits and plans: county permit, septic (OSSF) review, foundation engineer"),
    # pier and beam
    "piers": ((250, 600), "piers", "Concrete piers, 12 in, on footings to rock, formed above the ground, galvanized beam seats"),
    "framing": ((8, 14), "sq ft", "PT floor: triple 2x12 beams, 2x12 joists at 16 in on hangers, 1-1/8 in T&G floor, labor"),
    "anchors": ((500, 1500), "lot", "Uplift ties: the kit's base rail to the beams, the beams to the piers"),
    "skirting": ((6, 12), "sq ft", "Skirting round the crawl space: PT frame, metal panels, hardware cloth behind"),
    "ramp": ((10, 16), "sq ft", "Concrete ramp up to the doors, broom finish, on compacted fill"),
    "ramp_fill": ((70, 125), "cu yd", "Fill under the ramp: crushed limestone, compacted in lifts"),
    "ramp_walls": ((80, 160), "ft", "The ramp's concrete side walls, up to ~4.4 ft, with footings"),
    # slab
    "cut": ((20, 40), "cu yd", "Cut on the high side, reused as general fill where it suits, the rest hauled"),
    "fill": ((70, 125), "cu yd", "Fill: crushed limestone base, placed and compacted in lifts (slab and apron)"),
    "wall": ((70, 140), "ft", "Stem wall where the fill is deeper than 1.5 ft or the cut deeper than 0.5 ft, with its footing"),
    "drain": ((1500, 3000), "lot", "Swale and French drain along the cut (north and east) sides"),
    "slab": ((9, 15), "sq ft", "Slab: 6 in, rebar, thickened edges, vapor barrier, column piers"),
    "aprons": ((8, 13), "sq ft", "Apron along the south wall, 12 ft deep, with its concrete edge"),
    # both
    "tube": ((15, 26), "sq ft", "Building, installed: tube frame, 11 ft legs, two 10 x 9 roll-ups, the kit's walk door"),
    "walk_door": ((1500, 3000), "lot", "Walk door upgrade, net of the kit door: 3070 hollow metal, welded frame, continuous hinge, "
                                      "Grade 1 lever and deadbolt, closer, stop, seals"),
    "insulation": ((1.25, 2.5), "sq ft of wall and roof", "Option: insulation, walls and roof"),
    "power": ((3500, 8000), "lot", "Option: power: trench, conduit, subpanel, lights and outlets"),
}
BASE = {"piers": ("prep", "locate", "permits", "piers", "framing", "anchors", "skirting", "ramp", "ramp_fill", "ramp_walls"),
        "slab": ("prep", "locate", "permits", "cut", "fill", "wall", "drain", "slab", "aprons")}
CONTINGENCY = 0.10
Z80 = 1.2816  # half-width of an 80% band, in standard deviations


def footprint(length: float):
    return line_rect(X0 + (FULL - length) * ALONG[0], length, DEPTH)


def site_quantities(length: float, ground: Terrain, to_m: Frame, cut: float = CUT) -> dict:
    """Quantities for both foundations, for a footprint `length` ft along the line, from the lidar."""
    poly = footprint(length)
    gft = lambda p: ground(*to_m(p)) / FT + ground.z0  # noqa: E731
    lerp = lambda a, b, u: (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)  # noqa: E731
    nw, ne, se, sw = poly
    ux = ((se[0] - sw[0]) / length, (se[1] - sw[1]) / length)
    uy = ((nw[0] - sw[0]) / DEPTH, (nw[1] - sw[1]) / DEPTH)
    at = lambda x, y: (sw[0] + ux[0] * x + uy[0] * y, sw[1] + ux[1] * x + uy[1] * y)  # noqa: E731   # A's frame -> site
    high = max(gft(p) for p in poly)
    q = {"fall": high - min(gft(p) for p in poly)}

    # Pier and beam: the floor PB_FLOOR over the high corner; the ramp from the sills to the ground APPROACH_FOOT out.
    floor = high + PB_FLOOR
    q["piers"] = len(PB_BEAMS_Y) * len(PB_PIERS_X)
    q["under"] = {k: floor - gft(p) for k, p in zip(("NW", "NE", "SE", "SW"), poly)}
    q["skirting"] = sum(math.dist(a, b) * (floor - (gft(a) + gft(b)) / 2) for a, b in zip(poly, poly[1:] + poly[:1]))
    sill = floor - 0.04
    k = (sill - gft(at(length / 2, -APPROACH_FOOT))) / APPROACH_FOOT
    ramp = Polygon(approach_a(length))
    z = lambda x, y: sill + k * min(y, 0.0)  # noqa: E731
    x0, y0, x1, y1 = ramp.bounds
    cells = [(x0 + i * 0.5 + 0.25, y0 + j * 0.5 + 0.25) for i in range(int((x1 - x0) / 0.5)) for j in range(int((y1 - y0) / 0.5))]
    cells = [c for c in cells if ramp.contains(Point(c))]
    q["ramp"] = ramp.area
    q["ramp_fill"] = sum(max(z(*c) - gft(at(*c)), 0) for c in cells) * 0.25 / 27
    ring = list(ramp.exterior.coords)
    q["ramp_walls"] = 0.0
    for a, b in zip(ring, ring[1:]):
        if min(a[1], b[1]) > -0.5:   # the edge along the building
            continue
        n = max(1, int(math.dist(a, b)))
        q["ramp_walls"] += sum(math.dist(a, b) / n for i in range(n)
                               if z(*lerp(a, b, (i + .5) / n)) - gft(at(*lerp(a, b, (i + .5) / n))) > WALL_FROM)
    q["sills"] = [floor - gft(at(c, 0)) for c in (7.0, 15.0, 23.0)] if length == LENGTH else []
    q["grade"] = k

    # Slab: cut and filled `cut` ft below the high corner; the apron near grade.
    top = high - cut
    n, m = int(length * 2), int(DEPTH * 2)
    d = [top - gft(lerp(lerp(nw, ne, (i + .5) / n), lerp(sw, se, (i + .5) / n), (j + .5) / m)) for i in range(n) for j in range(m)]
    fill = sum(max(v, 0) for v in d) / (n * m) * length * DEPTH / 27
    q["cut"] = sum(max(-v, 0) for v in d) / (n * m) * length * DEPTH / 27
    q["wall"] = 0.0
    for a, b in ((nw, ne), (ne, se), (se, sw), (sw, nw)):
        kk = int(math.dist(a, b))
        q["wall"] += sum(math.dist(a, b) / kk for i in range(kk) if not -RETAIN <= top - gft(lerp(a, b, (i + .5) / kk)) <= DEEP)
    apron = sum(max(top - 0.015 * (j + .5) / 4 - gft(at(1.5 + (length - 3) * (i + .5) / 40, -(j + .5) / 4)), 0)
                for i in range(40) for j in range(int(SLAB_APRON * 4))) / (40 * SLAB_APRON * 4) * (length - 3) * SLAB_APRON / 27
    q["fill"] = fill + apron
    q["aprons"] = (length - 3) * SLAB_APRON
    return q


def estimate(length: float, q: dict, kind: str) -> tuple[list[dict], dict]:
    area = length * DEPTH
    surface = 2 * (length + DEPTH) * EAVE + area / math.cos(math.atan(3 / 12))
    qty = {"prep": 1, "locate": 1, "permits": 1, "piers": q["piers"], "framing": area, "anchors": 1, "skirting": q["skirting"],
           "ramp": q["ramp"], "ramp_fill": q["ramp_fill"], "ramp_walls": q["ramp_walls"], "cut": q["cut"], "fill": q["fill"],
           "wall": q["wall"], "drain": 1 if q["cut"] > 0.5 else 0, "slab": area, "aprons": q["aprons"], "tube": area,
           "walk_door": 1, "insulation": surface, "power": 1}
    keys = [*BASE[kind], "tube", "walk_door", "insulation", "power"]
    rows, sums = [], {}
    for key in keys:
        (lo, hi), unit, label = PRICES[key]
        rows.append({"item": label, "qty": f"{qty[key]:,.0f} {unit}", "low": int(round(lo * qty[key], -2)), "high": int(round(hi * qty[key], -2))})
        sums[key] = (lo * qty[key], hi * qty[key])
    items = [sums[k] for k in (*BASE[kind], "tube", "walk_door")]
    found = [sums[k] for k in BASE[kind] if k not in ("prep", "locate", "permits")]

    def likely(its):
        mid = sum((a + b) / 2 for a, b in its) * (1 + CONTINGENCY)
        sd = math.sqrt(sum((b - a) ** 2 / 12 for a, b in its)) * (1 + CONTINGENCY)
        return mid, mid - Z80 * sd, mid + Z80 * sd

    totals = {"range": tuple(sum(b[i] for b in items) * (1 + CONTINGENCY) for i in (0, 1)), "likely": likely(items),
              "foundation": likely(found), "options": likely([sums["insulation"], sums["power"]])}
    return rows, totals


@click.command()
@click.option("--lengths", default="30", show_default=True, help="Lengths along the line to price (ft), comma-separated.")
@click.option("--detail/--no-detail", default=True, show_default=True, help="Print the line items.")
@click.option("--cut", default=CUT, show_default=True, help="Slab option: ft the slab sits below the footprint's high corner (0: all fill).")
def main(lengths: str, detail: bool, cut: float) -> None:
    """Price the building at site A, turnkey, on pier and beam and, for comparison, on a slab."""
    ground, to_m = Terrain(TERRAIN), Frame()
    k = lambda v: f"${v / 1000:,.0f}k"  # noqa: E731
    fmt = lambda t: f"{k(t[0])} ({k(t[1])}-{k(t[2])})"  # noqa: E731
    cfg = dict(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=95, tbl_width_chars=160,
               tbl_rows=-1, thousands_separator=",")
    summary = []
    for length in (float(v) for v in lengths.split(",")):
        q = site_quantities(length, ground, to_m, cut)
        area = length * DEPTH
        if detail:
            under = ", ".join(f"{c} {v:.1f}" for c, v in q["under"].items())
            sills = f"; the door sills {min(q['sills']):.1f}-{max(q['sills']):.1f} ft" if q["sills"] else ""
            click.echo(f"\n{DEPTH:g} x {length:g} x {EAVE:g} ft = {area:,.0f} sq ft; the ground falls {q['fall']:.1f} ft to the SW.")
            click.echo(f"Pier and beam: the floor over the ground at the corners {under} ft{sills}. Ramp {q['ramp']:,.0f} sq ft at "
                       f"{100 * q['grade']:.0f}% (1:{1 / q['grade']:.1f}), {q['ramp_fill']:.0f} cu yd of fill, side walls {q['ramp_walls']:.0f} ft.")
        for kind in ("piers", "slab"):
            rows, totals = estimate(length, q, kind)
            if detail:
                head = ("on pier and beam (the plan)" if kind == "piers" else
                        f"on a slab {cut:g} ft below the high corner (for comparison): cut {q['cut']:.0f} cu yd, fill {q['fill']:.0f}, "
                        f"stem wall {q['wall']:.0f} ft")
                click.echo(f"\n{DEPTH:g} x {length:g}, {head}")
                with pl.Config(**cfg):
                    click.echo(pl.DataFrame(rows))
            summary.append({"size": f"{DEPTH:g} x {length:g} x {EAVE:g}", "foundation": "pier and beam" if kind == "piers" else "slab",
                            "turnkey, likely (80% band)": fmt(totals["likely"]), "per sq ft": f"${totals['likely'][0] / area:,.0f}",
                            "of which the foundation and ramp/apron": fmt(totals["foundation"]),
                            "all lows to all highs": f"{k(totals['range'][0])}-{k(totals['range'][1])}",
                            "+ insulation and power": fmt(totals["options"])})
    click.echo(f"\nTurnkey totals, with {CONTINGENCY:.0%} contingency (site work, foundation, ramp or apron, the building, the walk door):")
    with pl.Config(**{**cfg, "fmt_str_lengths": 40}):
        click.echo(pl.DataFrame(summary))


if __name__ == "__main__":
    main()
