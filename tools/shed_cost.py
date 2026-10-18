# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy"]
# ///
"""Turnkey budget for the steel building at site A: site work, foundation and a tube-frame building, by size.

Tube frame only: the owner ruled out red-iron (Oct 18 2026; see site/notes.md, "Tube frame or red-iron").

The sizes are standard kit sizes (owner, Oct 18 2026): 30 ft wide, the most common shop span, across the
strip from the 5 ft setback line, and 35, 30 or 25 ft long along the line, in the usual 5 ft steps. Every
size keeps site A's east end; the smaller ones give up length at the west end, by the well. The doors are
all in the south wall (owner, Oct 18 2026): two 12 x 12 roll-ups and the walk door between them, behind one
apron 12 ft deep that runs a foot past the outer roll-ups.

The ground falls ~3 ft across the footprint, to the SW, and the doors face the low side, so the pad is cut
and filled: the slab sits CUT ft below the high corner (`--cut`; 0 builds it all up on fill, as first
priced). Quantities come from the 2017 lidar: the cut on the high side, the fill under the rest, the stem
wall where the fill runs deeper than 1.5 ft or the cut deeper than 0.5 ft (it retains the high side there),
and the fill under the apron to bring it up to the slab.

Prices are low/high planning ranges for the Austin area, Oct 2026: published Texas cost guides and
county bid tabulations (sources in site/notes.md, "What the building at site A costs"). None is a
quote. Get three itemized local bids; the building and the slab are most of the money.

The outer range adds every low and every high, which no real job does. The "likely" figure is the sum
of the midpoints, and its band is where 80% of outcomes land if each line's price falls anywhere in its
range independently (uniform; sd = range / sqrt(12) per line). Prices that move together, like a hot
concrete market, would widen it.

Run: uv run tools/shed_cost.py
"""

import math

import polars as pl
import rich_click as click

from drive_layout import APRON_DEEP
from envelope_plan import ALONG, line_rect
from plan3d import FT, TERRAIN, Frame, Terrain

DEPTH = 30.0         # ft, square off the line: the building's width (clear span)
FULL = 35.0          # ft along the line: site A as drawn (30 x 35 = 1,050 sq ft)
X0 = 98.6            # site x of site A's NW corner (envelope_plan.SITE_A)
EAVE = 14.0
DEEP = 1.5           # ft of fill past which an edge gets a stem wall instead of a thickened slab edge
RETAIN = 0.5         # ft of cut past which an edge gets a stem wall to hold the high ground back
CUT = 1.5            # ft: the slab below the footprint's high corner

# (low, high) dollars, and the unit.
PRICES = {
    "prep": ((1500, 3500), "lot", "Site prep: clear, strip the topsoil, lay out"),
    "locate": ((300, 600), "lot", "Locate the buried service line (private locator)"),
    "permits": ((1500, 4000), "lot", "Permits and plans: county permit, septic (OSSF) review, foundation engineer"),
    "cut": ((20, 40), "cu yd", "Cut on the high side, reused as general fill where it suits, the rest hauled"),
    "fill": ((70, 125), "cu yd", "Fill: crushed limestone base, placed and compacted in lifts (slab and apron)"),
    "wall": ((70, 140), "ft", "Stem wall where the fill is deeper than 1.5 ft or the cut deeper than 0.5 ft, with its footing"),
    "drain": ((1500, 3000), "lot", "Swale and French drain along the cut (north and east) sides"),
    "slab": ((9, 15), "sq ft", "Slab: 6 in, rebar, thickened edges, vapor barrier, column piers"),
    "aprons": ((8, 13), "sq ft", "Apron along the south wall, 12 ft deep, with its concrete edge"),
    "tube": ((16, 28), "sq ft", "Building, installed: tube frame, 14 ft eave, two 12 x 12 roll-ups, the kit's walk door"),
    "walk_door": ((1500, 3000), "lot", "Walk door upgrade, net of the kit door: 3070 hollow metal, welded frame, continuous hinge, "
                                      "Grade 1 lever and deadbolt, closer, stop, seals"),
    "insulation": ((1.25, 2.5), "sq ft of wall and roof", "Option: insulation, walls and roof"),
    "power": ((3500, 8000), "lot", "Option: power: trench, conduit, subpanel, lights and outlets"),
}
CONTINGENCY = 0.10
Z80 = 1.2816  # half-width of an 80% band, in standard deviations


def apron_area(length: float) -> float:
    """The south apron (sq ft): two roll-ups and the walk door, a foot past the outer roll-ups, 12 ft deep."""
    return (length - 3) * APRON_DEEP


def site_quantities(length: float, ground: Terrain, to_m: Frame, cut: float = CUT) -> dict:
    """Cut and fill (cu yd) and stem-wall length (ft) for a footprint `length` ft along the line, from the lidar."""
    poly = line_rect(X0 + (FULL - length) * ALONG[0], length, DEPTH)
    gft = lambda p: ground(*to_m(p)) / FT + ground.z0  # noqa: E731
    lerp = lambda a, b, u: (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)  # noqa: E731
    high = max(gft(p) for p in poly)
    top = high - cut
    nw, ne, se, sw = poly
    n, m = int(length * 2), int(DEPTH * 2)
    cells = [top - gft(lerp(lerp(nw, ne, (i + .5) / n), lerp(sw, se, (i + .5) / n), (j + .5) / m)) for i in range(n) for j in range(m)]
    fill = sum(max(d, 0) for d in cells) / (n * m) * length * DEPTH / 27
    dug = sum(max(-d, 0) for d in cells) / (n * m) * length * DEPTH / 27
    wall = 0.0
    for a, b in ((nw, ne), (ne, se), (se, sw), (sw, nw)):
        k = int(math.dist(a, b))
        wall += sum(math.dist(a, b) / k for i in range(k) if not -RETAIN <= top - gft(lerp(a, b, (i + .5) / k)) <= DEEP)
    # The apron's fill: from the ground up to the apron (which falls 1.5% from the slab), under its 12 ft out from the south wall.
    out = ((sw[0] - nw[0]) / DEPTH, (sw[1] - nw[1]) / DEPTH)
    k = 40
    apron = sum(max(top - 0.015 * (j + .5) / 4 - gft((lerp(sw, se, (i + .5) / k)[0] + out[0] * (j + .5) / 4,
                                                      lerp(sw, se, (i + .5) / k)[1] + out[1] * (j + .5) / 4)), 0)
                for i in range(k) for j in range(int(APRON_DEEP * 4))) / (k * APRON_DEEP * 4) * apron_area(length) / 27
    return {"fill": fill + apron, "cut": dug, "wall": wall, "fall": high - min(gft(p) for p in poly), "low": top - min(gft(p) for p in poly)}


def estimate(length: float, q: dict) -> tuple[list[dict], dict]:
    area = length * DEPTH
    surface = 2 * (length + DEPTH) * EAVE + area / math.cos(math.atan(3 / 12))
    qty = {"prep": 1, "locate": 1, "permits": 1, "cut": q["cut"], "fill": q["fill"], "wall": q["wall"], "drain": 1 if q["cut"] > 0.5 else 0,
           "slab": area, "aprons": apron_area(length), "walk_door": 1, "tube": area, "insulation": surface, "power": 1}
    rows, sums = [], {}
    for key, ((lo, hi), unit, label) in PRICES.items():
        rows.append({"item": label, "qty": f"{qty[key]:,.0f} {unit}", "low": int(round(lo * qty[key], -2)), "high": int(round(hi * qty[key], -2))})
        sums[key] = (lo * qty[key], hi * qty[key])
    base = [sums[k] for k in ("prep", "locate", "permits", "cut", "fill", "wall", "drain", "slab", "aprons", "walk_door")]
    items = base + [sums["tube"]]
    lo = sum(b[0] for b in items) * (1 + CONTINGENCY)
    hi = sum(b[1] for b in items) * (1 + CONTINGENCY)
    mid = sum((a + b) / 2 for a, b in items) * (1 + CONTINGENCY)
    sd = math.sqrt(sum((b - a) ** 2 / 12 for a, b in items)) * (1 + CONTINGENCY)
    options = [sums["insulation"], sums["power"]]
    opt_mid = sum((a + b) / 2 for a, b in options) * (1 + CONTINGENCY)
    opt_sd = math.sqrt(sum((b - a) ** 2 / 12 for a, b in options)) * (1 + CONTINGENCY)
    totals = {"range": (lo, hi), "likely": (mid, mid - Z80 * sd, mid + Z80 * sd),
              "options": (opt_mid, opt_mid - Z80 * opt_sd, opt_mid + Z80 * opt_sd)}
    return rows, totals


@click.command()
@click.option("--lengths", default="35,30,25", show_default=True, help="Lengths along the line to price (ft), comma-separated.")
@click.option("--detail/--no-detail", default=True, show_default=True, help="Print the line items for each size.")
@click.option("--cut", default=CUT, show_default=True, help="Ft the slab sits below the footprint's high corner (0: all fill).")
def main(lengths: str, detail: bool, cut: float) -> None:
    """Price the building at site A, slab and building, turnkey."""
    ground, to_m = Terrain(TERRAIN), Frame()
    summary = []
    for length in (float(v) for v in lengths.split(",")):
        q = site_quantities(length, ground, to_m, cut)
        rows, totals = estimate(length, q)
        area = length * DEPTH
        if detail:
            click.echo(f"\n{DEPTH:g} x {length:g} ft = {area:,.0f} sq ft: the ground falls {q['fall']:.1f} ft; slab {cut:g} ft below the high corner: "
                       f"cut {q['cut']:.0f} cu yd, fill {q['fill']:.0f} cu yd (slab and apron, {q['low']:.1f} ft deep at most), stem wall {q['wall']:.0f} ft")
            with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=90, tbl_width_chars=150,
                           tbl_rows=-1, thousands_separator=","):
                click.echo(pl.DataFrame(rows))
        k = lambda v: f"${v / 1000:,.0f}k"  # noqa: E731
        likely = lambda t: f"{k(t[0])} ({k(t[1])}-{k(t[2])})"  # noqa: E731
        summary.append({"size": f"{DEPTH:g} x {length:g} ({area:,.0f} sq ft)",
                        "turnkey, likely (80% band)": likely(totals["likely"]),
                        "per sq ft": f"${totals['likely'][0] / area:,.0f}",
                        "all lows to all highs": f"{k(totals['range'][0])}-{k(totals['range'][1])}",
                        "+ insulation and power, likely": likely(totals["options"])})
    click.echo(f"\nTurnkey totals, with {CONTINGENCY:.0%} contingency (site work, cut and fill, stem wall, slab, apron, the building, the walk door), "
               f"slab {cut:g} ft below the high corner:")
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=40, tbl_width_chars=160):
        click.echo(pl.DataFrame(summary))


if __name__ == "__main__":
    main()
