# Kitchen mockup

The garage-to-kitchen conversion: the garage, the 3'-2½" hall beside it and the old kitchen
become one ~680 sq ft kitchen. This folder will move to its own repo. Until then it stays
separate from the site model (`tools/`, `site/`).

- `mockup.html`: the mockup page (scaled plan + 3D, three.js), also published as a private
  Artifact: https://claude.ai/artifact/JjgRa7we9Wgoi6JLc19b9y
  - It's written for the Artifact host, so it has no `<html>`/`<head>`/`<body>` of its own.
  - The layout data (walls, cabinets, furniture, in feet) is at the top of its script.
- `render.py`: writes `plan.png` and `view-*.jpg` from the page. Run
  `uv run kitchen/render.py` (or add `--chromium PATH`).

## Inputs

- **Laser shots (Oct 15 2026):**
  - garage 19'-6" × 20'-2" inside;
  - kitchen 21'-5" × 10'-3", 8'-0" ceiling;
  - hall 3'-2½" wide;
  - walls taken as 4¾".
  - The floor plans are in the private repo, under `house/`.
- **Frame:** x east from the hall's west wall, y north from the kitchen's south wall, feet.
  - The garage is the house's NE corner, behind the porch's north half.
  - Its 16 ft door, in the north wall, opens onto the driveway apron.

## Layout (Oct 15 2026)

- **A, cook wall** (south wall, west of the pocket door): 36 in range, plaster hood, stone
  slab to the ceiling.
- **B, tall wall** (the hall's west wall): fridge, freezer, wall ovens, two pantries.
- **C, island:** 12'-0" × 4'-6", waterfall; prep sink and dishwasher; 4 stools.
- **D, dining for 8:** at the old garage door, which becomes a 16 ft glass slider.
- **E, coffee bar** by the foyer door, and a banquette under the old kitchen's porch window.
- **F, sideboard** under the old garage's porch window.
- **G, stair** (existing) at the hall's north end.

## Assumed

- The old kitchen's west wall is drawn square. The floor plan's slant is unconfirmed: laser
  the north wall and both diagonals.
- The garage floor is raised to the house floor, with an 8 ft ceiling throughout.
- The plumbing, power and the hood's duct are placed freely.
- The garage's west wall is replaced by an attic beam. An engineer sizes it and picks its
  south support.
- Window positions are approximate.
