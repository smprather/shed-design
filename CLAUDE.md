# shed-design

Planning for improvements at a house in southwest Austin, in Travis County outside the city
limits:
- a large metal building at "site A" on the north strip along the US-290 fence: a 30 × 30 kit on 14 ft
  legs with a 12 × 12 door for a boat (Oct 25 2026), its doors in the front gable end (Oct 28), on a
  concrete slab dug into its high side, so its doors are at grade (Oct 24 2026; site B was dropped Oct 18);
  drawn turned 22.5° counter-clockwise, its doors facing SSE, so a towed boat can drive out in one move
  (Oct 31, not settled; `A_TURN` in `tools/envelope_plan.py`);
- traffic-noise and visual screening;
- a garage-to-kitchen conversion;
- the drive, redesigned from scratch (Oct 18 2026): loop D, a forecourt with a porte-cochère, the
  service drive and north court, and the shop lane to building A. It comes much later: the building
  and its ramp for the mower come first, and the drive is out of every budget for now, though it stays
  in the renders (owner, Oct 24 2026).

## Start here

- **Read `site/plan.md` first.** It's the whole plan in one place: the four projects, the
  order of work, open decisions and measurements still needed. Update it when a decision
  changes.
- **`site/notes.md` is the running record** behind the plan: measured facts, dated
  decisions, constraints and open questions. Add new facts and decisions there as dated
  sections, and correct earlier text when it's superseded.
- `site/measurements.md` and `site/measurements.csv` hold the field shot list and the tape
  baseline.
- The maps in `site/*.png` are rendered by the scripts in `tools/`. Don't edit the maps by
  hand.
- **The garage-to-kitchen conversion lives in the private repo
  `smprather/kitchen-garage-renovation`**: its measurements, layout and notes. Here, keep only
  what ties it to the site: parking moves out front first, and the septic capacity question.

## Private files: `smprather/shed-design-private`

Everything that can't be public lives in the private repo (Git LFS): the survey plat, closing
and title papers, the neighbors' City plan sets, and the raw site photos and screenshots.
- **Attach it at the start of a session** (add_repo), next to this repo at
  `/home/user/shed-design-private`.
- Its README indexes the folders: `property/`, `photos/<date>/`, `screenshots/`,
  `granada-ridge/` and `reference/`.
- **Save new private material there as soon as it arrives:** photos and PDFs sent in chat,
  and data pulled that carries names. Use its `tools/push_private.sh SOURCE DEST`, which
  dedupes by content and cleans names.
  Floor plans and inside photos of the garage and kitchen go to
  `smprather/kitchen-garage-renovation` instead.
- Container files don't survive between sessions.

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
| `front_plan.py` | `site/front-yard.png` (the front of the drive: loop D's legs, the forecourt and the porte-cochère vs. the building line and the lidar trees, prints clearances); old-drive and tree shapes in `front_layout.py` |
| `drive_layout.py` | the drive system's shapes in survey (s, t) feet (lanes, forecourt, porte-cochère, courts, materials); shared by `drive_plan.py`, `front_plan.py`, `impervious_cover.py` and `plan3d.py` |
| `drive_plan.py` | `site/drives.png` (the whole drive over the aerial), plus clearances to trunks and lines, grades, areas and impervious cover (printed tables; no budget while the drive is deferred) |
| `tow_plan.py` | `site/tow-backyard.png` and `site/tow-paths.png`: a pickup towing the 22 ft boat in from the street, the left turn that lines it up on the boat door, the straight back-in, and the way out to the street, as swept areas with a person's margins (printed tables: lengths, hitch angles, clearances to the building, house, trees, well, septic pipe and lot lines, crowns over the boat, lawn crossed). The way out is found by an A* search over the rig's moves, keeping the boat out of the back-lawn oaks' crowns past their outer 6 ft (`--search`, a minute or a few), and kept in `EXITS` by building A's turn. Square to the line (`--turn 0`, writing `site/tow-*-turn+0.png`) there's none; at the plan's 22.5° counter-clockwise turn (`envelope_plan.A_TURN`, the default) one forward move fits; `--truck hd` for a 3/4-ton |
| `house_layout.py` | the house in 3D, a first pass (walls, roofs, porch, deck, chimney, known openings) in survey (s, t) feet; used by `plan3d.py` |
| `envelope_plan.py` | `site/envelope.png` (where a building fits); also building A's placement: `SITE_A_SQUARE`, square to the line, and `SITE_A`, turned `A_TURN` degrees and moved `A_SHIFT` ft off the line |
| `site_b_plan.py` | `site/site-b.png` (the chosen site) |
| `solve_field.py` | `site/field-data.json` → `site/field-points.json` (trilateration, baselines) |
| `import_field.py EXPORT_DIR` | merges exported worksheet shots into `site/field-data.json` |
| `noise_model.py` | traffic-noise comparison of barrier options (printed table) |
| `cmu_cost.py` | DIY block-wall material takeoff (printed table) |
| `shed_cost.py` | turnkey budget for the building at site A, the 30 × 30 × 14 kit on a slab dug into its high side, and the same slab balanced or built up for comparison (printed tables; the dig, rock, fill, graded slope, wall, stem walls and aprons from the lidar, construction access with no drive yet, power from the meter pole and the service line's reroute, closed-cell foam insulation; `--level`, `--soil`) |
| `impervious_cover.py` | impervious cover now, and with the building and the new drive (gravel counted and not), vs. the limit (printed tables) |
| `fetch_terrain.py` | `site/terrain-lidar.json` (USGS 3DEP 1 m lidar resampled onto the 3D plan's 5 m grid); with `--out site/terrain-lidar-shed.json --spacing 1` (its docstring has the box), the 1 m patch round building A, which `plan3d.Terrain` blends in so every tool sees the finer ground there |
| `plan3d.py` | `site/plan3d.obj` and `site/plan3d.html` (a 3D viewer; template `tools/plan3d_viewer.html`) from `property_total_plan.jsonc` on the lidar terrain (`site/terrain-lidar.json`), plus septic conflict checks (printed table). The viewer draws building A on site A in detail (the plan: a 30 × 30 × 14 kit, turned 22.5° counter-clockwise, its ridge running back from a 12 × 12 roll-up for a boat, a 10 × 8 roll-up and a commercial walk door in its front gable end, painted burgundy with black trim and wainscot (`A_COLORS`), on a concrete slab dug into its high side (the terrain is cut, graded back 2:1 and drawn finer there; the dug ground is its own caliche layer, `terrain_excavation`), with concrete aprons at grade in front of its doors, the owner's S130 mower and a 22 ft wake boat on its trailer inside for scale), building B the same way (dropped, hidden at first), the house and the porte-cochère (`house_layout.py`), the drive's surfaces and curbs (`drive_layout.py`; the old drive and walk start hidden), and Candelaria Dr's asphalt. Trees on our lot are drawn in finer detail (lumpy crowns, trunks and limbs; the twin oak on its surveyed trunks). It has orbit, look-around, and Quake-style fly and walk modes (the mouse is captured to look, WASD moves; walking clamps to the surface under you and stops at walls), and remembers the whole view panel (camera, mode, sliders, layers, selection) across reloads in the browser's storage. `--focus` writes `site/shed3d.obj` and `site/shed3d.html` instead: building A close up, cropped to ~30 ft round its walls (`SHED_BOX`), its ground on 0.2 m squares round the cut (`FOCUS_MESH`), with its own views and labels (orbit always turns round the building's middle), published at https://claude.ai/artifact/8JBtwHwc9gbG8wbeGaT5kJ (the whole site is at https://claude.ai/artifact/DnfinmkvF9EfmcC7nLYGRz). Trees standing where the building's cut, slab and aprons go, and 2 m round them, are taken out (cleared to build) |
| `render_view.py` | `site/backyard-bare.jpg` and `site/backyard-8yr.jpg` (static render of the back-yard view, with and without the planned trees; template `tools/render_view.html`; needs a Playwright Chromium: `uv run --with playwright playwright install chromium`, or `--chromium PATH`) |
| `sentinel_view.py` | `site/sentinel.png` (an older and the latest clear Sentinel-2 satellite scene, 10 m, with the lots and the back-yard sight lines; `--series` dates the retail lot's clearing) |
| `render_building_b.py` | `site/building-b-*.jpg` (stills of building B from `tools/building_b.html`, the 3D page with sliders for eave height and door size, also published at https://claude.ai/artifact/HkCoRoNiUNBYoisHaoPWPw; needs a Playwright Chromium) |
| `fetch_canopy.py` | `site/canopy-lidar.json` (tree heights from the 2017 USGS lidar point cloud, 1 m cells, masked to what's still green in the latest Sentinel-2 scene); used by `plan3d.py` and `render_view.py` |

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
