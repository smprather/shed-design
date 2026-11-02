# Field measurements

Key map: [`measure-plan.png`](measure-plan.png) (regenerate with `uv run tools/measure_plan.py`).

Reply with the numbers in chat, or fill in the **Measured** column here. I'll
use them to place everything on a to-scale plan.

## Fixed points

| Point | Where |
|---|---|
| **A** | NW corner of the house: the west end of the north wall, the outside corner nearest the old carport. Use the wall corner at the ground, not the roof eave. |
| **B** | East end of the north wall: the garage's front corner, where the front porch starts. |
| **C** | Where the house's west wall steps back east, about 21 ft south of A. |
| **F1, F2** | Tape marks you put on the fence during shots 3 and 4. |
| **F3** | A tape mark on the fence at the far west end of the open grass strip along it. |

## How to shoot

- The laser measures from its back edge (check the setting). Rest the back edge on the point.
- **Square off a wall:** lay the laser's back flat against the wall and the beam shoots straight out from it.
- The beam needs something to hit. Walls, trunks and the fence all work.
  For a spot on open ground (septic lid, field corner), set a bucket
  or box on it. Shoot its near side and add half its width.
- For trunk shots, just hit the near face of the trunk. I'll add the radius from the girth (shot 11).
- To locate a spot, shoot it from two lettered points that are far apart and not in line
  with it; a third is a free check. If a line is blocked, use another point and say which.
- The nearest inch is plenty.
- Shots 1–2 are checked against the 1991 survey. The other estimates come from the
  aerial, which shows rooflines rather than walls, so a foot or two of difference is normal. If you're 5+ ft off an estimate, a point
  is probably mixed up, so it's worth a second look.

## Shots

| # | From → To | How | Aerial est. | Measured |
|---|---|---|---|---|
| 1 | A → B | along the north wall | 59.4 ft (survey) | |
| 2 | A → C | along the west wall | 21.3 ft (survey) | |
| 3 | A → fence | square off the north wall; tape the spot = **F1**. The surveyed line is 44.6 ft out. | ~42 ft | |
| 4 | B → fence | square off the north wall; tape the spot = **F2**. The surveyed line is 35.2 ft out. | ~34 ft | |
| 5 | A → F3 | aim the dot at the tape mark | ~107 ft | |
| 6 | F1 → F3 | along the fence; bucket or helper at the far end | ~92 ft | |
| 9 | A → big oak trunk | hit the trunk face | ? | |
| 10 | B → big oak trunk | hit the trunk face (C has no line of sight). A third shot from F1 is a free check. | ? | |
| 11 | Big oak girth | tape around the trunk at 4.5 ft off the ground | ? | |
| 12 | Big oak drip line | trunk → outer edge of the branches, on the side facing the build site | ? | |
| 13 | Septic tank lid(s) | bucket on each lid; shoot from two or three of A, B, F1 (C for anything west of the house) | ? | |
| 14 | Drain field corners or spray heads | bucket on each; shoot from two or three of A, B, F1 (C for anything west of the house) | ? | |
| 15 | East oak trunks | trunks in the strip between the garage's north wall and the fence: from B and A, plus girth | ? | |
| 16 | Drive, narrowest gap | trunk-to-trunk (or other obstacle) at the tightest spot on the way in | ? | |
| 17 | Lowest branches | aim straight up: a few spots over the build strip and over the drive | ? | |
| 18 | Slope (optional) | which way the build strip drops, and roughly how much | ? | |
| 19 | Well | the 1991 plat shows a well near the NW corner, ~28 ft in from the back line and ~12 ft from the US-290 line. Is it still there (casing, cap or pump)? If so: from A and from F1. | ~108 ft from A | |

## Tape baseline west of A (100 ft tape)

The laser gets unreliable past ~50 ft in daylight and through brush, so for the strip use a
baseline and offsets:

1. Stretch the tape from **A** straight west along the line of the north wall (sight down
   the wall). Stake it at 25, 50, 75 and 100 ft.
2. For each item, write its **station** (the tape reading where the item is square off the
   tape) and its **offset** (distance from the tape: + toward the fence, − toward the back
   yard). Short offsets can be eyeballed square.

| # | Item | Station | Offset | Estimate |
|---|---|---|---|---|
| T1 | Fence offset at 0 / 25 / 50 / 75 / 100 | — | | ~42 ft at 0 |
| T2 | Septic access pipe | | | ~41 / +43 |
| T3–T4 | Tank lids 1–2 | | | |
| T5–T8 | Drainfield points (trench ends, ports, green stripes) | | | |
| T9 | Well | | | ~95 / +50 |
| T10 | Anything else (oak branch edge, wire crossing, roots…) | | | |
| T11 | North edge of the tree belt (strip side), offset at 25 / 50 / 75 / 100 | — | | ~+21 at 25 |
| T12–T15 | Back lawn open area corners (NE, NW, SW, SE) at the branch edges | | | ~17 & ~100 / −25 & −62 |

## Heights with a laser level (Nov 2 2026)

For building A's dig and base (`site/building-a-groundwork.md`).

**The mark, z = 0:** the top of the house's foundation at **A**, the NW corner.
- Paint a small mark on the exact spot and photograph it. Use the slab's edge, not a brick
  ledge or the siding.
- Every height is measured from the mark; below it is negative.
- The model's house floor height is a guess (1055.5 ft, `house_layout.FF_FT`). H1 pins it to
  the lidar.

**How** (a line laser on a tripod, a helper, and a tape or a marked 2 × 4 held plumb as the
rod):
1. **Set up** within the line's visible range of the mark: ~20–30 ft in daylight. It reaches
   farther at dusk, or with a detector if the laser has a pulse mode.
2. **Read the mark:** the tape from the mark up to the line (the backsight).
3. **Read each point:** the tape from the ground up to the line. The point's height is the
   backsight minus that reading.
4. **To go farther,** set a turning point: a stake driven flush, or a brick. Read it, move the
   laser, read it again from the new setup, and carry on.
5. **Close the loop:** end by reading the mark again, back through the same turning points.
   It should close within ½ in; if not, redo the hop that's off.

**Find the points** with the tape baseline above:
- the **station** is the distance west along the north wall's line from A;
- the **offset** is the distance square off it toward the fence.

±1–2 ft is close enough for heights. The corners are building A turned 22.5° (the plan); if
the angle changes, they move.

| # | Point | Station | Offset | Estimate (ft from the mark) |
|---|---|---|---|---|
| H1 | Ground at A, at the foot of the foundation | 0 | 0 | −1.9 |
| H2 | Building A's NW corner | 90 | +38 | −4.7 |
| H3 | NE corner (the high one) | 61 | +45 | −3.0 |
| H4 | SE corner (door side) | 54 | +15 | −4.5 |
| H5 | SW corner (door side, the low one) | 83 | +8 | −5.5 |
| H6 | West side, middle | 87 | +23 | −5.2 |
| H7 | Back (north) side, middle | 75 | +41 | −4.3 |
| H8 | East side, middle | 57 | +30 | −3.8 |
| H9 | Door side, middle | 69 | +12 | −5.1 |
| H10 | 5 ft out behind the back wall's middle | 77 | +46 | −4.1 |
| H11 | 5 ft out behind the NE corner | 62 | +49 | −2.7 |
| H12 | The drain's outlet, ~45 ft past the SW corner | 107 | −31 | −7.5 |
| H13 | Top of the septic access pipe (and the ground beside it) | 41 | +43 | ground −1.8 |
| H14 | Top of the well casing (and the ground beside it) | 96 | +48 | ground −4.7 |

The estimates are the 2017 lidar and the floor guess, ±1 ft. The slab's top is drawn ~4.65 ft
under the floor: 0.8 ft over the SW corner's ground.

## Also note

- Check your closing papers first, since they may answer some of these outright.
  A **survey** shows the property lines and easements. A **septic inspection report**
  or permit often has a sketch of where the tank and field are.
- Septic: conventional gravity system, 1,200-gal concrete tank, standard drainfield (owner). Find the
  tank from the sewer cleanout where the main drain leaves the house; probe for the lids.
- The 1991 survey puts the US-290 property line 44.6 ft from A and 35.2 ft from B.
  The aerial suggests the fence is ~3–6 ft inside that line, and shots 3–4 will settle it.
