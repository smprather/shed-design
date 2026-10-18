# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""Impervious cover on our lot: what's there now, and with the building at site A and loop D.

Areas are on the lot only (the drive's apron in the street right-of-way doesn't count), in plan,
with overlaps counted once. Sources and accuracy:
- the lot, the house walls and the porch: the 1991 plat (good to ~1 ft);
- the deck: the county record's 240 sq ft, placed by photo (a wood deck over soil may not count;
  the pergola's metal roof over part of it does);
- the existing drive and walk: traced from the plat, +/-3 ft on every edge;
- the building at site A: the standard kit sizes in tools/shed_cost.py, plus its 14 x 10 ft door
  apron and the walk door's 4.5 x 4 ft landing (gravel counts too under most rules, so it's counted either way);
- loop D: tools/front_layout.py, the part that isn't already the existing drive or walk.

Not counted: the A/C pads, the septic lids, stepping stones and anything not yet mapped.

Run: uv run tools/impervious_cover.py [--limit 15]
"""

import polars as pl
import rich_click as click
from shapely.geometry import Polygon
from shapely.ops import unary_union

from envelope_plan import ALONG, line_rect
from front_layout import EXISTING_DRIVE, FRONT_WALK, LOOP_D, lane_outline
from front_plan import SurveyFrame
from house_layout import DECK
from site_plan import HOUSE_ST, PARCEL, PORCH_ST
from shed_cost import APRON, DEPTH, FULL, STOOP, X0

SIZES = (35.0, 30.0, 25.0)   # building A's length along the line (ft); 30 ft wide


def rect(s0: float, s1: float, t0: float, t1: float) -> Polygon:
    return Polygon([(s0, t0), (s1, t0), (s1, t1), (s0, t1)])


@click.command()
@click.option("--limit", default=15.0, show_default=True, help="Impervious-cover limit, % of the lot.")
def main(limit: float) -> None:
    """Tally impervious cover now, and with the building and loop D."""
    sf = SurveyFrame()
    lot = Polygon([sf.from_site(p) for p in PARCEL])
    on_lot = lambda g: g.intersection(lot)  # noqa: E731
    existing = {
        "House (plat walls, garage included)": on_lot(Polygon(HOUSE_ST)),
        "Covered front porch": on_lot(Polygon(PORCH_ST)),
        "Back deck and pergola (wood deck; may not count)": on_lot(rect(*DECK)),
        "Existing drive and garage apron (plat, +/-3 ft)": on_lot(Polygon(EXISTING_DRIVE)),
        "Front walk (plat)": on_lot(Polygon(FRONT_WALK)),
    }
    now = unary_union(list(existing.values()))
    loop_d = on_lot(Polygon(lane_outline(LOOP_D))).difference(now)
    area_lot = lot.area
    pct = lambda a: 100 * a / area_lot  # noqa: E731
    allowed = area_lot * limit / 100

    rows = [{"item": k, "sq ft": round(g.area), "% of lot": round(pct(g.area), 1)} for k, g in existing.items()]
    rows.append({"item": "Now (overlaps counted once)", "sq ft": round(now.area), "% of lot": round(pct(now.area), 1)})
    rows.append({"item": "Loop D, new paving on the lot", "sq ft": round(loop_d.area), "% of lot": round(pct(loop_d.area), 1)})
    click.echo(f"Lot: {area_lot:,.0f} sq ft ({area_lot / 43560:.2f} ac); {limit:g}% allows {allowed:,.0f} sq ft.")
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=60, tbl_rows=-1,
                   thousands_separator=","):
        click.echo(pl.DataFrame(rows))

    out = []
    for length in SIZES:
        bldg = on_lot(Polygon([sf.from_site(p) for p in line_rect(X0 + max(FULL - length, 0) * ALONG[0], length, DEPTH)]))
        b = bldg.area + APRON + STOOP
        for label, extra in (("+ building", 0.0), ("+ building + loop D", loop_d.area)):
            total = now.area + b + extra
            out.append({"case": f"{label} {DEPTH:g} x {length:g} (+ apron)", "sq ft": round(total),
                        "% of lot": round(pct(total), 1), f"vs {limit:g}% (sq ft)": round(allowed - total)})
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=60, tbl_rows=-1,
                   thousands_separator=","):
        click.echo(pl.DataFrame(out))


if __name__ == "__main__":
    main()
