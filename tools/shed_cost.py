# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy"]
# ///
"""Turnkey budget for the steel building at site A: site work, foundation and the building, by size.

The sizes are standard kit sizes (owner, Oct 18 2026): 30 ft wide, the most common shop span, across the
strip from the 5 ft setback line, and 35, 30 or 25 ft long along the line, in the usual 5 ft steps. Every
size keeps site A's east end, where the doors are; the smaller ones give up length at the west end, by the
well. Quantities come from the site: the fill
needed to bring the ground up level with the footprint's high corner (2017 lidar), the stem wall along
the sides where that fill runs deeper than 1.5 ft, and two 14 x 10 ft door aprons.

Prices are low/high planning ranges for the Austin area, Oct 2026: published Texas cost guides and
county bid tabulations (sources in site/notes.md, "What the building at site A costs"). None is a
quote. Get three itemized local bids; the building and the slab are most of the money.

Run: uv run tools/shed_cost.py
"""

import math

import polars as pl
import rich_click as click

from envelope_plan import ALONG, line_rect
from plan3d import FT, TERRAIN, Frame, Terrain

DEPTH = 30.0         # ft, square off the line: the building's width (clear span)
FULL = 35.0          # ft along the line: site A as drawn (30 x 35 = 1,050 sq ft)
X0 = 98.6            # site x of site A's NW corner (envelope_plan.SITE_A)
EAVE = 14.0
APRON = 2 * 14 * 10  # sq ft: two door aprons
DEEP = 1.5           # ft of fill past which an edge gets a stem wall instead of a thickened slab edge

# (low, high) dollars, and the unit.
PRICES = {
    "prep": ((1500, 3500), "lot", "Site prep: clear, strip the topsoil, lay out"),
    "locate": ((300, 600), "lot", "Locate the buried service line (private locator)"),
    "permits": ((1500, 4000), "lot", "Permits and plans: county permit, septic (OSSF) review, foundation engineer"),
    "fill": ((70, 125), "cu yd", "Fill: crushed limestone base, placed and compacted in lifts"),
    "wall": ((70, 140), "ft", "Stem wall where the fill is deeper than 1.5 ft, with its footing"),
    "slab": ((9, 15), "sq ft", "Slab: 6 in, rebar, thickened edges, vapor barrier, column piers"),
    "aprons": ((7, 11), "sq ft", "Door aprons, two 14 x 10 ft"),
    "red_iron": ((25, 45), "sq ft", "Building, erected: red-iron frame, 14 ft eave, two 12 x 12 roll-ups, walk door"),
    "tube": ((16, 28), "sq ft", "Building, installed: tube frame, same size and doors"),
    "insulation": ((1.25, 2.5), "sq ft of wall and roof", "Option: insulation, walls and roof"),
    "power": ((3500, 8000), "lot", "Option: power: trench, conduit, subpanel, lights and outlets"),
}
CONTINGENCY = 0.10


def site_quantities(length: float, ground: Terrain, to_m: Frame) -> dict:
    """Fill (cu yd) and stem-wall length (ft) for a footprint `length` ft along the line, from the lidar."""
    poly = line_rect(X0 + (FULL - length) * ALONG[0], length, DEPTH)
    gft = lambda p: ground(*to_m(p)) / FT + ground.z0  # noqa: E731
    lerp = lambda a, b, u: (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)  # noqa: E731
    top = max(gft(p) for p in poly)
    nw, ne, se, sw = poly
    n, m = int(length * 2), int(DEPTH * 2)
    fill = sum(max(top - gft(lerp(lerp(nw, ne, (i + .5) / n), lerp(sw, se, (i + .5) / n), (j + .5) / m)), 0)
               for i in range(n) for j in range(m)) / (n * m) * length * DEPTH / 27
    wall = 0.0
    for a, b in ((nw, ne), (ne, se), (se, sw), (sw, nw)):
        k = int(math.dist(a, b))
        wall += sum(math.dist(a, b) / k for i in range(k) if top - gft(lerp(a, b, (i + .5) / k)) > DEEP)
    return {"fill": fill, "wall": wall, "fall": top - min(gft(p) for p in poly)}


def estimate(length: float, q: dict) -> tuple[list[dict], dict]:
    area = length * DEPTH
    surface = 2 * (length + DEPTH) * EAVE + area / math.cos(math.atan(3 / 12))
    qty = {"prep": 1, "locate": 1, "permits": 1, "fill": q["fill"], "wall": q["wall"], "slab": area, "aprons": APRON,
           "red_iron": area, "tube": area, "insulation": surface, "power": 1}
    rows, sums = [], {}
    for key, ((lo, hi), unit, label) in PRICES.items():
        rows.append({"item": label, "qty": f"{qty[key]:,.0f} {unit}", "low": int(round(lo * qty[key], -2)), "high": int(round(hi * qty[key], -2))})
        sums[key] = (lo * qty[key], hi * qty[key])
    base = [sums[k] for k in ("prep", "locate", "permits", "fill", "wall", "slab", "aprons")]
    totals = {}
    for frame in ("red_iron", "tube"):
        lo = (sum(b[0] for b in base) + sums[frame][0]) * (1 + CONTINGENCY)
        hi = (sum(b[1] for b in base) + sums[frame][1]) * (1 + CONTINGENCY)
        opt = ((sums["insulation"][0] + sums["power"][0]) * (1 + CONTINGENCY), (sums["insulation"][1] + sums["power"][1]) * (1 + CONTINGENCY))
        totals[frame] = (lo, hi, opt)
    return rows, totals


@click.command()
@click.option("--lengths", default="35,30,25", show_default=True, help="Lengths along the line to price (ft), comma-separated.")
@click.option("--detail/--no-detail", default=True, show_default=True, help="Print the line items for each size.")
def main(lengths: str, detail: bool) -> None:
    """Price the building at site A, slab and building, turnkey."""
    ground, to_m = Terrain(TERRAIN), Frame()
    summary = []
    for length in (float(v) for v in lengths.split(",")):
        q = site_quantities(length, ground, to_m)
        rows, totals = estimate(length, q)
        area = length * DEPTH
        if detail:
            click.echo(f"\n{DEPTH:g} x {length:g} ft = {area:,.0f} sq ft: fill {q['fill']:.0f} cu yd (the ground falls {q['fall']:.1f} ft), "
                       f"stem wall {q['wall']:.0f} ft")
            with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=90, tbl_width_chars=150,
                           tbl_rows=-1, thousands_separator=","):
                click.echo(pl.DataFrame(rows))
        fmt = lambda a, b: f"${a / 1000:,.0f}k-{b / 1000:,.0f}k"  # noqa: E731
        summary.append({"size": f"{DEPTH:g} x {length:g} ({area:,.0f} sq ft)",
                        "red-iron, turnkey": fmt(*totals["red_iron"][:2]), "tube frame, turnkey": fmt(*totals["tube"][:2]),
                        "+ insulation and power": fmt(*totals["red_iron"][2]),
                        "red-iron $/sq ft": f"{totals['red_iron'][0] / area:.0f}-{totals['red_iron'][1] / area:.0f}"})
    click.echo(f"\nTurnkey totals, with {CONTINGENCY:.0%} contingency (site work, fill, stem wall, slab, aprons, the building):")
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=40):
        click.echo(pl.DataFrame(summary))


if __name__ == "__main__":
    main()
