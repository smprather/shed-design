# Building A: the groundwork

Nov 2 2026. Two jobs, in this order, before the slab is poured:
1. Move the house's buried power line out from under the building.
2. Build the crushed-rock base the slab sits on. The owner may do this themselves.

The numbers come from `uv run tools/a_groundwork.py`, which also draws the map
`site/a-groundwork.png`. They're from the 2017 lidar (±0.5 ft) and the survey and field shots
(±2 ft). Rerun the script after new measurements, and with `--base` if the engineer calls for a
thicker base.

Prices are rough Central Texas figures, not local quotes.

## Before any of it

- **Settle the building.** The angle is still open: drawn turned 22.5°, or square to the line.
  The size is open too: 30 × 30, or a 24 × 30. The layout, the dig and the base all move with
  them, so don't stake anything until they're decided.
- **Get the slab's design** from the engineer who stamps the kit's drawings:
  - the base's thickness and how compacted it must be;
  - the thickened edges' size;
  - where the anchors go.

  Everything here assumes a 4 in slab on 4 in of base, with thickened edges at the anchors.
- **The permit.** Travis County's accessory-building permit. Ask the permit desk, (512)
  854-4215, whether the electrical work needs anything from them.
- **Locate everything that's buried.**
  - **Call 811** at least two working days before digging. That covers the utilities' own lines.
  - **Hire a private locator** (~$300–600) for your own lines, which 811 doesn't mark:
    - the house's power line, pole to house;
    - the house's sewer, from the house to the septic tank;
    - the well's pipe and pump wire, if the well is still in use;
    - the sprinkler lines (send the sprinkler plan; its lines get capped or moved where the
      dig and the trench go).
  - Mark each with paint and flags, and photograph them with a tape in the picture.

### Worth measuring this afternoon

1. **The ground at the four corners,** with a laser level or a water level, as heights over
   the SW corner. The lidar says:

   | Corner | NW | NE | SE | SW |
   |---|---|---|---|---|
   | Ground over the SW corner (ft, ±0.5) | +0.7 | +2.5 | +0.9 | 0 |

   The dig and the base's thickness hang on these.
2. **The power line's ends.**
   - Photograph where it leaves the meter pole and where it reaches the house.
   - Read the size printed on the cable or conduit, e.g. "4/0 AL".
   - Read the main breaker's rating at the pole.
   - Check whether the pole's panel has spare spaces. Photograph it with its door open, but
     don't take the inner cover off.
3. **What's on the ground along the route.** The aerial is old, and it shows two sheds and a
   round tank or pool on the west side of the route. Note what's still there, plus any deck,
   AC unit or hose bib near the house's NW corner.
4. **The well:** is it in use, or capped? Does any pipe or wire run from it?
5. **The septic tank's lids,** and where the sewer leaves the house (look for a cleanout).

## Part 1: move the house's power line

### Why it has to move

- The meter and the house's disconnect are on the pole at the lot's NW fence corner. The line
  runs underground from there to the house's NW corner.
- Drawn straight between those ends, it's 136 ft long, passes 0.6 ft from the well, and runs
  24 ft under the building. That's 35 ft through the dig, the slab and the aprons.
- The real route bends somewhere, at least round the well, and only the locate will show
  where.
- **No line can stay under the slab.** The dig and the thickened edges would cut it. A fault
  under the slab can't be dug out, and the code allows wiring under a building only in
  conduit.

### The plan: a new run in conduit, round the back and the door side

- **Why a new run, not a patch:** it's simpler and safer than splicing a detour into an old
  cable whose route and condition are unknown.
  - It's one continuous pull from the pole to the house, with no splices.
  - It's in conduit, so the wire can be pulled out and replaced later.
  - It stays clear of everything we're protecting.
- **The route** (white on the map; site x, y in ft):

  | Leg | From | To | Length | Where |
  |---|---|---|---|---|
  | 1 | the pole (62, 106) | 62, 152 | 46.5 ft | down the back strip, ~4 ft inside the back fence, outside the back-line tree row |
  | 2 | 62, 152 | 78, 159 | 16.8 ft | angling off the fence |
  | 3 | 78, 159 | the pull box (116, 197) | 54.1 ft | diagonally across, past the building's SW corner |
  | 4 | the pull box | 172, 199 | 56.0 ft | along the back lawn |
  | 5–7 | 172, 199 | the house's NW corner (182, 170) | 33.3 ft | up along the house's west wall, ~3 ft off it |

  It's 207 ft of trench and ~219 ft of conduit, counting the risers. A straight run would be
  136 ft.
- **What it stays clear of:**
  - the dig, the slab and the aprons: 10 ft;
  - the well: 24 ft;
  - the septic pipe: 59 ft;
  - the twin oak: 44 ft.

  About 50 ft of it is under tree canopy. Dig there with the trencher's teeth cutting the roots
  cleanly. Hand-dig past any root over 2 in.
- **One yaupon spot** on the back-line planting plan ends up 3 ft from the trench. Plant it a
  few feet further along its row.
- **A pull box at the leg 3/4 corner.**
  - A pull can take only 360° of bends (NEC 352.26).
  - This route has 179° from the pole to the box and 237° from the box to the house, counting
    a 90° bend at each end where the conduit rises.
- **The building's feeder and a data conduit** share leg 1's trench for 35 ft. Then they branch
  32 ft east to the building's panel inside its west wall (orange on the map).
  - Lay them only to the edge of the dig, capped and staked.
  - After the dig, extend them under the pad to the panel's stub-up.
- **Depth:** 24 in of cover over the conduit, so a trench ~27–30 in deep. The code minimum
  for PVC is 18 in (NEC Table 300.5), but this route crosses the lawn the boat's truck uses,
  and a future drive.
- **The old line:** once the new one is live, it's dead. Cut it back and cap it at both ends,
  and pull it out where the dig uncovers it.

### Who does what

- **Texas lets you do electrical work on a home you own and live in** without a license (TDLR:
  Occupations Code 1305.003(a)(6)). Local rules can still require permits.
- **The split we'd suggest:**
  - **You:** the locate, the trench, the conduit, the pull box, the bedding, the warning tape
    and the backfill. That's most of the labor.
  - **A licensed electrician:** the conduit and wire sizes, the pull, the terminations at
    both ends, and the cutover. That means a few hours with the house's power off at the
    pole's disconnect.
    - Aluminum lugs need torque specs and anti-oxidant paste.
    - The run to the house is a feeder, which must be 4-wire. If the old one is 3-wire, the
      house panel's neutral and ground get separated.
    - The electrician also adds the building's 100 A breaker at the pole.
- **Pedernales Electric** isn't needed for the cutover, since the disconnect at the pole kills
  the run. Call them only if the pole's panel has to be swapped for one with spare spaces:
  they pull and reset the meter.

### Parts list: the trench and conduit (your part)

Conduit sizes are typical for a 200 A house in aluminum wire and a 100 A building. The
electrician confirms them once the house's wire size is known.

| Item | Quantity | Rough cost |
|---|---|---|
| 2½ in Schedule 40 PVC conduit, 10 ft sticks (the house) | 23 | ~$650 |
| 1½ in Schedule 40 PVC (the building's feeder) | 8 | ~$100 |
| 1 in Schedule 40 PVC (data) | 8 | ~$60 |
| Long-radius sweeps, 2½ in: 45° and 22½° (cut to suit the bends) | ~6 and ~4 | ~$150 |
| Sweeps for the 1½ and 1 in: two 45° and one 90° each | | ~$40 |
| 2½ in Schedule 80 PVC (the risers out of the ground, at the pole and the house), 90° Sch 80 sweeps, straps | 2 sticks, 2 sweeps | ~$150 |
| PVC expansion fittings, 2½ in, on the risers | 2 | ~$80 |
| PVC primer and cement, heavy-bodied | 1 each | ~$30 |
| Pull string or mule tape, 250 ft | 3 | ~$45 |
| In-grade pull box, ~13 × 24 in, with a Tier 15 lid (for occasional vehicles) | 1 | ~$150–300 |
| Washed gravel under the pull box | 2–3 bags | ~$20 |
| Red "buried electric line" warning tape, 6 in wide | 300 ft | ~$25 |
| Sand or screened fines for bedding, if the trench is rocky | 1–3 cu yd | ~$50–150 |
| Walk-behind trencher with a rock chain, 36 in boom | 1 day | ~$200–300 |

The shared leg is three conduits side by side, 12 in wide. Dig it with the loader's or a mini
excavator's bucket when they're on site for the dig.

Your part comes to ~$1.7–2.1k. The electrician's work and the new wire are another ~$2–4k,
depending on the wire size. The budget now carries $3.5–6k for the whole new run. It was
$1–2.5k for a spliced detour, which raises the turnkey total from $82k to $85k.

### Steps

1. **Locate, mark and photograph** everything buried (above). Set out the route with paint.
   Check it against the marks and against the sprinkler plan.
2. **Trench** 27–30 in deep and flat-bottomed.
   - Hand-dig within 2 ft of any marked line.
   - Pick out rocks bigger than a fist.
   - In rock, lay 2 in of sand in the bottom.
3. **Lay the conduit.**
   - Dry-fit first.
   - Prime and cement every joint, bells facing the pull.
   - Use the long sweeps at the bends, not tight elbows.
   - Run a pull string through each conduit as you go, and tie both ends off.
4. **Set the pull box** on 4–6 in of gravel, its lid flush with the grade.
5. **The risers:**
   - Schedule 80 out of the ground at the pole and at the house, with an expansion fitting,
     strapped every 3 ft.
   - Cap the tops until the electrician comes.
6. **Bed and backfill.**
   - 4–6 in of sand or fine soil over the conduit, tamped by foot.
   - The warning tape 12 in below the grade.
   - Then the rest of the soil, tamped in 6–8 in layers.
   - Leave the shared leg's branch to the building capped and staked at the dig's edge.
7. **The electrician pulls and cuts over.**
   - Open the house's disconnect at the pole.
   - Take off the old run.
   - Land the new conductors and test them.
   - Turn the power back on.
   - Cap and label the old run at both ends: DEAD.
8. **Record the as-built.** Measure the route from the building's corners and from the house,
   and photograph the open trench with a tape in the picture. Note it in `site/notes.md`.

## Part 2: the rock base for the slab

### The design

- **The slab's top** sits 0.8 ft (9½ in) over the SW corner's natural ground. That corner is
  the lowest, and the doors stay at grade.
  - **The base's top** is 4 in under that: 0.47 ft (5½ in) over the SW corner's ground.
  - **The base's bottom** is at least 4 in under its top.
- **Strip** 4 in of topsoil and roots off everything the base goes on, plus 1 ft past the
  slab's edges.
- **The high side is dug down** to the base's bottom. It's deepest at the NE corner, about
  2.5 ft.
  - The soil there is Brackett: 10–20 in over soft limestone. Expect to dig into weathered
    rock in the NE corner, about 0.8 cu yd of it.
  - A loader's bucket rips weathered rock. A hard ledge needs a mini excavator with a rock
    bucket.
- **The low side is built up with base.** The base is 4 in thick at the NE side and ~10 in at
  the SW corner, where the stripped ground is lowest.
- **The base runs 1 ft past the slab's edges,** for the forms' stakes: 32 × 32 ft.
- **The aprons** at the doors get the same 4 in of base under 4 in of concrete. They fall to
  the lawn: 10% from the 12 × 12 door, 4% from the 10 × 8.
- **The swale** round the north, east and west is 2 ft wide, its floor 0.5 ft under the
  slab's top. The graded slope runs back from it at 2:1 (3:1 also fits, for mowing).
  - A French drain runs under the swale to daylight past the SW corner.
- **The material:**
  - **Use:** crushed limestone base ("flex base", "road base"; TxDOT Item 247, Type A, Grade
    1–2). It's angular and locks together when it's wet and compacted. Crushed recycled
    concrete also works.
  - **Don't use:** pea gravel, river rock or decomposed granite. They roll and never lock.
  - **Avoid** pit caliche of unknown quality.

### The quantities (from `a_groundwork.py`)

| | Dig (cu yd, in place) | Base (cu yd, compacted) | Base to order |
|---|---|---|---|
| Under the slab (32 × 32 ft) | 28.4 | 14.8 | 31 tons |
| Under the aprons (267 sq ft) | 5.3 | 3.6 | 7 tons |
| The swale and its 2:1 slope | 10.2 | | |
| **In all** | **44** (spread on the lot) | **18.4** | **38 tons** (~3 truckloads) |

- **Ordering:** 1.9 tons per compacted cu yd, plus 10%.
- **Where the spoil goes:** spread it on the lot, but not on the drainfield, in the septic
  strip, or under the oaks' crowns. Keep the topsoil apart, for dressing the slopes.

### Parts list: the base

| Item | Quantity | Rough cost |
|---|---|---|
| Crushed limestone base, delivered | 38 tons | ~$1.1–1.7k ($30–45/ton) |
| Washed ¾ in crushed stone (#57), for the drain | ~4 tons | ~$150–250 |
| 4 in drain pipe: perforated (SDR 35 PVC, or corrugated with a sock) and solid, with two or three 45° bends, a cleanout and a pop-up outlet | 64 ft perforated, 77 ft solid | ~$250–450 |
| Non-woven filter fabric, 4 ft wide | 100 ft roll | ~$60–100 |
| Batter boards and stakes: twelve 2 × 4 × 8, two dozen 1 × 4 or rebar stakes, screws, 500 ft of mason's line, marking paint, flagging | | ~$120–180 |
| Compact track loader, ~70 hp, with a smooth bucket (rent), and delivery | 3 days | ~$1.3–1.8k |
| Reversible plate compactor, ~5,000+ lbf (rent) | 2 days | ~$300–400 |
| Rotating laser level, receiver and grade rod (rent, or buy one for ~$300–500) | 3 days | ~$150–300 |
| Garden hose and fan nozzle (~700 gal of water, wetting the base) | | |
| Hand tools: square and round shovels, landscape rake, asphalt (lute) rake, wheelbarrow, 100 ft and 25 ft tapes, 4 ft level, a straight 12 ft 2 × 4 or screed, sledge | | |
| Safety: gloves, glasses, hearing protection, boots, N95 masks for the dust | | |
| **For the pour** (often the concrete crew's): 15 mil Class A vapor barrier, one 14 × 140 ft roll, and seam tape | | ~$350–500 |

That's ~$3.5–5k out of pocket for the base and the drain, without the vapor barrier. The
budget's matching lines are site prep, the dig, the slope and the drain: ~$4–8k for a
contractor, plus whatever the concrete crew charges for the base.

### Steps

**Lay out**

1. **Stake the surveyed line first.** Find the NW lot-corner pin and the next pin along
   US-290, and pull a string between them. The fence wanders up to 7 ft off the line, so
   don't measure from it.
2. **Mark the corners.**
   - Measure along the string from the NW pin, then square in from it (3-4-5).
   - Check the diagonals: 42.43 ft each, to within ¼ in.
   - Check the distances to the well and the septic pipe. Those two are only ±2 ft, so
     they catch blunders, nothing finer.

   | Corner | Along the line from the NW pin | Square in from the line | To the well | To the septic pipe |
   |---|---|---|---|---|
   | NW | 38.0 ft | 21.6 ft | 12.4 ft | 49.8 ft |
   | NE | 65.8 | 10.2 | 35.5 | 20.3 |
   | SE (door side) | 77.2 | 37.9 | 53.6 | 31.1 |
   | SW (door side, low corner) | 49.5 | 49.3 | 42.0 | 55.1 |

3. **Set batter boards** 4 ft outside each corner, and string the slab's edges from them. They
   bring the corners back after the dig takes the stakes out.
4. **Set a benchmark** outside the work, a rebar pin or a nail in a post, and read the SW
   corner's natural ground on it with the laser. Everything after is a rod reading from that
   one shot:

   | Target | Over the SW corner's natural ground |
   |---|---|
   | The slab's top | +0.80 ft (9½ in) |
   | The base's top | +0.47 ft (5½ in) |
   | The base's bottom (the dig's floor) | +0.13 ft (1½ in), or lower where stripping goes deeper |
   | The swale's floor | +0.30 ft |

**Dig**

5. **Clear and strip** 4 in of topsoil and roots over the pad, 1 ft past it, and the aprons.
   Stockpile the topsoil.
6. **Dig the high side** to the base's bottom, checking with the laser every few feet.
   - Cut the swale and lay the slope back, 2:1 (or 3:1).
   - Don't over-dig: fill a hole with base, never with loose soil.
7. **Proof-roll** the dug ground. Drive the loaded track loader over it in lanes.
   - Mark anything that pumps or ruts more than ½ in.
   - Dig those spots out 6–12 in, and refill with base.
   - Then run the plate over the bare ground, wetting it if it's dusty.
8. **The building's conduits.** Extend the feeder (1½ in) and data (1 in) conduits from the dig's
   edge to the panel's spot.
   - The panel goes inside the west wall, ~20 ft from the SW corner. The electrician picks
     the exact spot.
   - Lay them in a shallow groove in the dug ground, so the base covers them.
   - Turn them up with Schedule 80 sweeps, 4–6 in inside the wall line so they come up
     inside the kit's base rail.
   - Cap them and tie them to a stake. Tamp round them by hand.

**Build the base**

9. **Place the base in layers about 5 in deep, loose,** which compacts to about 4 in.
   - The SW (low) side takes two layers before the whole pad gets its last one.
   - Dump in piles, and spread with the loader.
10. **Wet each layer** until it's damp right through, like sand for a sandcastle: it holds a
    squeeze without dripping. Don't leave puddles.
11. **Compact each layer** with the reversible plate.
    - 3–4 passes each way, overlapping by half a plate.
    - Do the edges and corners first.
    - It's done when the plate rides instead of sinking, and your boot leaves no print.
12. **Finish the top.**
    - Spread the last layer a little high, compact it, and read it with the laser on a 5 ft
      grid.
    - It should be within ±½ in of the base's top.
    - Shave the highs with the lute rake, fill the lows with fines, wet, and compact again.
    - Check it with the straight 12 ft board for ridges.
13. **Check it all again from the batter boards:**
    - the slab's edges, 1 ft inside the base's edge all round;
    - the diagonals;
    - the conduit stub where the panel goes.

**After**

14. **Keep it.** No traffic on it.
    - If rain softens it, let it dry, then compact again.
    - In heat, mist it until the forms go on.
15. **For the pour** (the concrete crew, or you with them):
    - forms;
    - the thickened-edge trenches cut down through the base at the engineer's size, their
      spoil cleared out;
    - the vapor barrier, lapped 6 in, taped, and run down into the edge trenches;
    - the rebar on chairs;
    - the kit's anchors per the dealer's anchor plan;
    - a boot on the conduit stub;
    - then the inspection, then the pour.
16. **The aprons' base** goes in after the building is up, the same way, following each apron's
    fall.
17. **The French drain** goes in after the slab, so equipment doesn't crush it.
    - A trench 12 in wide and 1 ft under the swale's floor, falling at least 1% (⅛ in per
      ft) to the outlet. Check it with the laser.
    - Fabric in the trench, 2 in of stone, the pipe with its holes down, stone to 2 in over
      it, then fold the fabric over.
    - Perforated pipe along the east side's cut and the north side; solid pipe down the west
      side and ~45 ft out past the SW corner.
    - A pop-up outlet on a rock splash pad, inside our lot.
    - A cleanout at the high (east) end.

**How to tell it's right**

- A screwdriver pushed by hand goes in no more than ¼ in.
- A loaded wheelbarrow leaves no rut.
- The top is within ±½ in of the laser, and flat under the straightedge.
- The corners are within ¼ in of the strings, and the diagonals are equal.
- For proof on paper, a testing lab can check the compaction (~$300–600). The engineer may
  ask for it.
