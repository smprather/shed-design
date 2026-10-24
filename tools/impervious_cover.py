# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely"]
# ///
"""Impervious cover on our lot: what's there now, and with the building at site A and the new drive system.

Areas are on the lot only (the drive's apron in the street right-of-way doesn't count), in plan,
with overlaps counted once. Sources and accuracy:
- the lot, the house walls and the porch: the 1991 plat (good to ~1 ft);
- the deck: the county record's 240 sq ft, placed by photo (a wood deck over soil may not count;
  the pergola's metal roof over part of it does);
- the existing drive and walk: traced from the plat, +/-3 ft on every edge;
- the building at site A: the 30 x 30 kit on a slab (owner, Oct 24 2026), plus its concrete aprons at grade
  (drive_layout.aprons_a);
- the drive system (tools/drive_layout.py, Oct 18 2026): the old drive and walk come out; the porte-cochere's
  roof, the pavers, the concrete street aprons and the curbs count; its gravel is shown both ways, since rules
  differ on gravel (Travis County's answer decides it).

Not counted: the A/C pads, the septic lids, stepping stones and anything not yet mapped.

Run: uv run tools/impervious_cover.py [--limit 15]
"""

import polars as pl
import rich_click as click
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from envelope_plan import SITE_A
from drive_layout import COVER, CURB, layout
from front_layout import EXISTING_DRIVE, FRONT_WALK
from front_plan import SurveyFrame
from house_layout import DECK
from site_plan import HOUSE_ST, PARCEL, PORCH_ST
from shed_cost import DEPTH, LENGTH



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
    house_only = unary_union([existing[k] for k in list(existing)[:3]])
    dl = layout([sf.from_site(p) for p in SITE_A])
    hard = unary_union([on_lot(dl["paved"]), on_lot(dl["concrete"]), on_lot(box(COVER[0], COVER[2], COVER[1], COVER[3]))])
    curbs = on_lot(dl["curbs"]).length * CURB
    gravel = on_lot(dl["gravel"]).difference(house_only).difference(hard)
    area_lot = lot.area
    pct = lambda a: 100 * a / area_lot  # noqa: E731
    allowed = area_lot * limit / 100

    rows = [{"item": k, "sq ft": round(g.area), "% of lot": round(pct(g.area), 1)} for k, g in existing.items()]
    rows.append({"item": "Now (overlaps counted once)", "sq ft": round(now.area), "% of lot": round(pct(now.area), 1)})
    rows.append({"item": "New drive: cover, pavers, concrete aprons, curbs", "sq ft": round(hard.difference(house_only).area + curbs),
                 "% of lot": round(pct(hard.difference(house_only).area + curbs), 1)})
    rows.append({"item": "New drive: gravel", "sq ft": round(gravel.area), "% of lot": round(pct(gravel.area), 1)})
    click.echo(f"Lot: {area_lot:,.0f} sq ft ({area_lot / 43560:.2f} ac); {limit:g}% allows {allowed:,.0f} sq ft.")
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=72, tbl_rows=-1,
                   thousands_separator=","):
        click.echo(pl.DataFrame(rows))

    out = []
    for length in (LENGTH,):
        b = unary_union([on_lot(dl["building"]), on_lot(dl["approach"])]).area
        drive_hard = unary_union([house_only, hard]).area + curbs
        for label, base, extra in (("now + building", now.area, 0.0), ("new drive (gravel not counted) + building", drive_hard, 0.0),
                                   ("new drive (gravel counted) + building", drive_hard, gravel.area)):
            total = base + b + extra
            out.append({"case": f"{label} {DEPTH:g} x {length:g} and its aprons", "sq ft": round(total),
                        "% of lot": round(pct(total), 1), f"vs {limit:g}% (sq ft)": round(allowed - total)})
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=72, tbl_rows=-1,
                   thousands_separator=","):
        click.echo(pl.DataFrame(out))


if __name__ == "__main__":
    main()
