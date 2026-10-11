# shed-design

Planning for improvements at a house in southwest Austin, in Travis County outside the city
limits:
- a large metal building on a slab at "site B" along the US-290 fence;
- traffic-noise and visual screening;
- a garage-to-kitchen conversion;
- a front circle drive.

## Start here

- **Read `site/notes.md` first.** It's the running record: measured facts, dated decisions,
  constraints and open questions. Add new facts and decisions there as dated sections, and
  correct earlier text when it's superseded.
- `site/measurements.md` and `site/measurements.csv` hold the field shot list and the tape
  baseline.
- The maps in `site/*.png` are rendered by the scripts in `tools/`. Don't edit the maps by
  hand.

## Privacy: this repo is public

- Never commit the survey PDF, closing papers, or anything showing owners' or neighbors'
  names, signatures, lender details, tax values, exemptions or sale prices.
- Don't add screenshots that show neighbors' prices (e.g. Zillow).
- Keep model identifiers out of commits and files.

## Tools

Each script carries its dependencies inline (PEP 723). Run them from the repo root with
`uv run tools/<script>.py`.

| Script | Output |
|---|---|
| `site_plan.py` | `site/north-yard.png`; also the shared module (frames, survey, field features) |
| `measure_plan.py` | `site/measure-plan.png` (shot key for the worksheet) |
| `lot_plan.py` | `site/lot.png` (whole-lot overview) |
| `front_plan.py` | `site/front-yard.png` (circle drive) |
| `envelope_plan.py` | `site/envelope.png` (where a building fits) |
| `site_b_plan.py` | `site/site-b.png` (the chosen site) |
| `solve_field.py` | `site/field-data.json` → `site/field-points.json` (trilateration, baselines) |
| `import_field.py EXPORT_DIR` | merges exported worksheet shots into `site/field-data.json` |
| `noise_model.py` | traffic-noise comparison of barrier options (printed table) |
| `cmu_cost.py` | DIY block-wall material takeoff (printed table) |
| `plan3d.py` | `site/plan3d.obj` from `property_total_plan.jsonc` on the lidar terrain (`site/terrain-lidar.json`), plus septic conflict checks (printed table) |

**After new field measurements:**
1. Export the worksheet.
2. Run `import_field.py`.
3. Run `solve_field.py`.
4. Re-render `site_plan`, `envelope_plan` and `site_b_plan`. Re-render `measure_plan` and
   `lot_plan` too if the geometry moved.

## Field worksheet

The owner records measurements in a private Artifact:
https://claude.ai/artifact/H53VoemG3UgKtCruAP9Mz3 (database collection `shots`). To pull
the data:
1. Use the ArtifactData tool to list collection `shots` with an `out_dir`.
2. Run `uv run tools/import_field.py <that dir>`.

## Coordinate frames

- **Site frame** (`site_plan.py`): the aerial rotated 29° counter-clockwise, in feet.
  - +x is ESE toward Candelaria (the front).
  - +y is SSW, away from US-290.
  - Up on the maps is NNE.
- **Survey frame `st(s, t)`:** s runs back from the front line along the south line; t runs
  toward US-290. Bearings from the 1991 survey enter through `en_to_site`.
- **Measurement frame** (`solve_field.py`):
  - origin is A, the house's NW wall corner;
  - u runs along the north wall toward B (the NE corner);
  - v runs square off the wall toward the fence.

## Conventions

- Python with pathlib, rich-click for CLIs, polars for tables, uv for running scripts.
- Units are feet. Say whether a number was measured or read off the aerial, and give ±.
- Design to the surveyed line, not the fence. The US-290 fence wanders off the line.
- Twin oak north of the house:
  - no digging within 12 ft of either trunk;
  - stay outside the drip line where possible;
  - prune only July–January (oak wilt).
- Keep the septic tank, drainfield and pump-truck lane clear. The septic system is in the
  strip along US-290.
