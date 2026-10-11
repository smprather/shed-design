# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars"]
# ///
"""DIY material cost for the interior CMU (cinder block) sound wall on the US-290 side.

Quantities follow standard 8x8x16 block takeoffs; prices are low/high ranges for Central
Texas retail (Oct 2026, unverified locally). Labor is the owner's, so it isn't priced. The
footing, rebar layout and grouting are for the building's engineer to set; this is a
budget, not a design.

Run: uv run tools/cmu_cost.py --length 40 --height 10
"""

import math

import polars as pl
import rich_click as click

BLOCKS_PER_SQFT = 1.125  # 8x8x16 nominal: 16 x 8 in face = 0.889 sq ft
WASTE = 0.05
GROUT_CUFT_PER_SQFT = 0.25  # fully grouted 8 in CMU
BLOCKS_PER_MORTAR_BAG = 13  # 80 lb premixed mortar mix
BAG_GROUT_CUFT = 0.6  # 80 lb bag of concrete/grout mix
SAND_LB_PER_CUFT = 100

# (low, high) prices in dollars.
PRICE = {
    "block": (2.00, 3.00),
    "bond_beam_block": (3.00, 4.25),
    "mortar_bag": (7.0, 9.0),
    "grout_bag": (6.0, 7.5),
    "rebar_20ft_no5": (16.0, 22.0),
    "ladder_wire_10ft": (4.0, 6.0),
    "sand_ton_delivered": (45.0, 70.0),
    "anchors_ties": (100.0, 200.0),
    "sealant": (60.0, 120.0),
    "rentals_tools": (400.0, 900.0),  # mixer, scaffold, masonry blade, hand tools
    "footing_cuyd": (150.0, 200.0),
}


@click.command()
@click.option("--length", default=40.0, show_default=True, help="Wall length along the US-290 side (ft).")
@click.option("--height", default=10.0, show_default=True, help="Wall height (ft).")
@click.option("--wrap", default=0.0, show_default=True, help="Extra wall around each end corner (ft per end).")
@click.option("--fill", type=click.Choice(["full", "partial"]), default="full", show_default=True,
              help="full = every core grouted; partial = rebar cells and bond beams grouted, other cores sand-filled.")
@click.option("--rebar-spacing", default=32.0, show_default=True, help="Vertical rebar spacing (in).")
def main(length: float, height: float, wrap: float, fill: str, rebar_spacing: float) -> None:
    """Estimate material for a DIY CMU sound wall."""
    run = length + 2 * wrap
    area = run * height
    courses = math.ceil(height / (8 / 12))
    bond_courses = 2  # top and mid-height
    bond_blocks = math.ceil(run / (16 / 12)) * bond_courses
    blocks = math.ceil(area * BLOCKS_PER_SQFT * (1 + WASTE)) - bond_blocks
    mortar_bags = math.ceil((blocks + bond_blocks) / BLOCKS_PER_MORTAR_BAG)

    void_cuft = area * GROUT_CUFT_PER_SQFT
    grout_frac = 1.0 if fill == "full" else min(1.0, (8 / rebar_spacing) + bond_courses / courses)
    grout_cuft = void_cuft * grout_frac * 1.10
    grout_bags = math.ceil(grout_cuft / BAG_GROUT_CUFT)
    sand_tons = 0.0 if fill == "full" else void_cuft * (1 - grout_frac) * SAND_LB_PER_CUFT / 2000

    verticals = math.ceil(run / (rebar_spacing / 12)) + 1
    vert_ft = verticals * (height + 2)  # + dowel/lap into the footing
    horiz_ft = 2 * bond_courses * run * 1.1
    rebar_bars = math.ceil((vert_ft + horiz_ft) / 20)
    ladder_pieces = math.ceil(math.ceil(courses / 2) * run / 10)
    footing_cuyd = run * 2 * 1.5 / 27  # extra 2 ft wide x 1.5 ft deep under the wall, poured with the slab

    rows = [
        ("Block 8x8x16", f"{blocks}", blocks, "block"),
        ("Bond-beam block (top + mid courses)", f"{bond_blocks}", bond_blocks, "bond_beam_block"),
        ("Mortar mix, 80 lb bags", f"{mortar_bags}", mortar_bags, "mortar_bag"),
        (f"Grout, 80 lb bags ({grout_cuft / 27:.1f} cu yd)", f"{grout_bags}", grout_bags, "grout_bag"),
        ("Sand for unreinforced cores (tons)", f"{sand_tons:.1f}", sand_tons, "sand_ton_delivered"),
        ("#5 rebar, 20 ft bars", f"{rebar_bars}", rebar_bars, "rebar_20ft_no5"),
        ("Ladder joint wire, 10 ft", f"{ladder_pieces}", ladder_pieces, "ladder_wire_10ft"),
        ("Anchors / ties to the frame", "lot", 1, "anchors_ties"),
        ("Acoustic sealant + backer rod", "lot", 1, "sealant"),
        ("Rentals + tools (mixer, scaffold, blade)", "lot", 1, "rentals_tools"),
        ("Wall subtotal", "", None, None),
        ("Extra footing under the wall (cu yd)", f"{footing_cuyd:.1f}", footing_cuyd, "footing_cuyd"),
    ]
    data = []
    for item, qty, n, key in rows:
        if key is None:
            lo = sum(r["low"] for r in data)
            hi = sum(r["high"] for r in data)
        else:
            lo, hi = (round(n * p) for p in PRICE[key])
        data.append({"item": item, "qty": qty, "low": lo, "high": hi})
    df = pl.DataFrame(data)
    lo_all = df.filter(pl.col("item") != "Wall subtotal")["low"].sum()
    hi_all = df.filter(pl.col("item") != "Wall subtotal")["high"].sum()
    weight_tons = area * (80 if fill == "full" else 70) / 2000

    with pl.Config(tbl_rows=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, tbl_width_chars=100):
        click.echo(f"{run:.0f} ft x {height:.0f} ft = {area:.0f} sq ft, {fill} fill, ~{weight_tons:.0f} tons of wall")
        click.echo(df)
    click.echo(f"All in (wall + extra footing): ${lo_all:,.0f} - ${hi_all:,.0f}")


if __name__ == "__main__":
    main()
