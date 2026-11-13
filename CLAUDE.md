# shed-design

Planning for improvements at a house in southwest Austin, in Travis County outside the city
limits:
- a large metal building at "site A" on the north strip along the US-290 fence: a 30 × 30 kit on 14 ft
  legs with a 12 × 12 door for a boat (Oct 25 2026), its doors in the front gable end (Oct 28), on a
  concrete slab dug into its high side, so its doors are at grade (Oct 24 2026; site B was dropped Oct 18);
  drawn turned 22.5° counter-clockwise, its doors facing SSE, so a towed boat can drive out in one move
  (Oct 31, not settled; `A_TURN` in `tools/envelope_plan.py`). The 1971 deed restrictions (Granada
  Hills Amended; notes, "The deed restrictions") allow only one dwelling with an attached garage or
  carport, so a detached building needs an attorney's read first;
- traffic-noise and visual screening (no fence past the 45 ft front building line: deed restrictions, sec. 3);
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
- `site/building-a-groundwork.md` is building A's groundwork, step by step: the house's power line
  moved round it, and the slab's rock base (parts lists, for the owner to do themselves).
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
| `site_b_plan.py` | `site/site-b.png` (site B, 23 × 43, dropped Oct 18) |
| `site_b_east.py` | `site/site-b-east.png`: a 30 × 30 at site B with its doors east (Nov 1 2026), placed on the oak's drip line and 10 ft west of it, each built up, at grade and dug in like site A (printed tables: clearances, sills, dig and fill, uphill approaches, cost via `shed_cost.site_quantities(corners=...)`). The answer: no |
| `solve_field.py` | `site/field-data.json` → `site/field-points.json` (trilateration, baselines) |
| `import_field.py EXPORT_DIR` | merges exported worksheet shots into `site/field-data.json` |
| `noise_model.py` | traffic-noise comparison of barrier options (printed table) |
| `cmu_cost.py` | DIY block-wall material takeoff (printed table) |
| `a_groundwork.py` | `site/a-groundwork.png` and the numbers in `site/building-a-groundwork.md`: building A's corners tied to the surveyed line, the house's power line in a new run round it (`ROUTE`, a pull box, the building's feeder sharing its first leg; clearances, bends), the slab's crushed-rock base (strip, dig, base tons, aprons; `--base`, `--strip`, `--soil`), the swale's French drain to daylight, and the sprinklers from `site/irrigation-2017.json` against all of it (heads in the dig, crossings) |
| `irrigation_plan.py` | `site/irrigation-2017.json`: the sprinklers from the house's 2017 irrigation plan (the photo is private: `shed-design-private/property/irrigation-plan-2017.webp`), digitized by a projective fit on the lot's and house's corners: the back yard's rotor zones, the mainline, the valves, the controller and the rain sensor, in site ft (±5–10 ft; the plan is schematic) |
| `shed_cost.py` | turnkey budget for the building at site A, the 30 × 30 × 14 kit on a slab dug into its high side, and the same slab balanced or built up for comparison (printed tables; the dig, rock, fill, graded slope, wall, stem walls and aprons from the lidar, construction access with no drive yet, power from the meter pole and the service line's reroute, closed-cell foam insulation; `--level`, `--soil`) |
| `impervious_cover.py` | impervious cover now, and with the building and the new drive (gravel counted and not), vs. the limit (printed tables) |
| `fetch_terrain.py` | `site/terrain-lidar.json` (USGS 3DEP 1 m lidar resampled onto the 3D plan's 5 m grid); with `--out site/terrain-lidar-shed.json --spacing 1` (its docstring has the box), the 1 m patch round building A, which `plan3d.Terrain` blends in so every tool sees the finer ground there |
| `plan3d.py` | `site/plan3d.obj` and `site/plan3d.html` (a 3D viewer; template `tools/plan3d_viewer.html`) from `property_total_plan.jsonc` on the lidar terrain (`site/terrain-lidar.json`), plus septic conflict checks (printed table). The viewer draws building A on site A in detail (the plan: a 30 × 30 × 14 kit, turned 22.5° counter-clockwise, its ridge running back from a 12 × 12 roll-up for a boat, a 10 × 8 roll-up and a commercial walk door in its front gable end, painted burgundy with black trim and wainscot (`A_COLORS`), on a concrete slab dug into its high side (the terrain is cut, graded back 2:1 and drawn on 0.2 m squares there, `FOCUS_MESH`; the dug ground is its own caliche layer, `terrain_excavation`), with concrete aprons at grade in front of its doors, the owner's S130 mower and a 22 ft wake boat on its trailer inside for scale), building B the same way (dropped, hidden at first), the house and the porte-cochère (`house_layout.py`), the drive's surfaces and curbs (`drive_layout.py`; the old drive and walk start hidden), Candelaria Dr's asphalt, the septic access pipe (a white riser), the back yard's sprinklers from `site/irrigation-2017.json` (pipes as bands on the ground, heads, valve boxes, the controller) and the house's new power run with building A's feeder, the pull box and the risers (from `a_groundwork.py`; layer group "Utilities"), the 45 ft front building line (a purple band, labeled), the US-290 fence as it stands (`FENCE_TRACE`, weathered grey, under Your lot) beside the proposed one on the line (under Proposed), with 1 ft contours over our lot and ~20 ft past its lines (`CONTOUR_PAD`), and "Building A", "The garage" and two upstairs views (from the north face's windows 1 and 3, as in the owner's photos), and a Labels group in the layer list (building labels and the rest, each on its own box). The house's colors follow the owner's photo of the garage end (Nov 12 2026), and its details the yard photos (Nov 13: board-and-batten, the north face's stone line and band, gutters, the AC, the south overhang, hipped back roofs, the L deck and pergola). The models are true to scale (no exaggeration slider) and there are no range poles. Trees on our lot are drawn in finer detail (lumpy crowns, trunks and limbs; the twin oak on its surveyed trunks). It has orbit, look-around, and Quake-style fly and walk modes (the mouse is captured to look, WASD moves; walking clamps to the surface under you and stops at walls), a slider for the north-line fence's height (6–10 ft; it's built at the spec's 8 ft and the viewer moves its top), and remembers the whole view panel (camera, mode, sliders, layers, selection) across reloads in the browser's storage. `--focus` writes `site/shed3d.obj` and `site/shed3d.html` instead: building A close up, cropped square to the back line from ~40 ft round its walls out past the lot's NW corner (`FOCUS_BOX`), its ground on 0.2 m squares round the cut and 0.5 m elsewhere, with a 2 ft grid (heavier every 10 ft), 1 ft contours of the cut ground (`ground_contours_1ft`, every 5 ft in `ground_contours_5ft`), and its own views and labels (orbit always turns round the building's middle; "The NW corner" looks along both fences), published at https://claude.ai/artifact/8JBtwHwc9gbG8wbeGaT5kJ (the whole site is at https://claude.ai/artifact/DnfinmkvF9EfmcC7nLYGRz). Trees standing where the building's cut, slab and aprons go, and 2 m round them, are taken out (cleared to build) |
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
- **Keep the house model accurate (owner, Nov 12 2026):** whenever a photo, measurement or
  document shows something about the house (shape, openings, materials, colors), update
  `tools/house_layout.py` and the house's colors in `tools/plan3d_viewer.html` to match, without
  waiting to be asked, and republish the 3D page.
