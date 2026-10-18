# The plan: 8400 Candelaria Dr

This is the whole plan in one place. `notes.md` keeps the evidence behind it: measurements,
sources, corrections and dates. This file says what we're doing, in what order, and what's
still undecided. Update it when a decision changes; record the facts behind the change in
`notes.md`.

Last updated: Oct 18 2026 (impervious cover: already over 15%; site A building priced).

## The four projects

| Project | What it is now | Status | Blocked on |
|---|---|---|---|
| **1. The building, at site A** | A standard tube-frame steel kit, 30 ft wide × 35, 30 or 25 ft, on the north strip between the well and the septic pipe. Site B is dropped (owner, Oct 18 2026) | Sized and priced (~$51–67k turnkey, likely); size and use open | The buried service line; the septic layout (the drainfield may be under it) |
| **2. Screening** (noise and views) | US-290 side: the 8 ft fence, building B, maybe a taller wall. Back line: 21 new trees in the gaps | Back-line planting ready to buy; US-290 side needs re-modeling | Fence gaps and ownership; septic layout |
| **3. Garage → kitchen** | Join the 21 × 21 ft attached garage, the hall beside it and the old kitchen into one ~680 sq ft kitchen. Its own repo: `smprather/kitchen-garage-renovation` | Idea stage (~90% likely); layout mocked up | Parking must move first; septic capacity question; structure (see its repo) |
| **4. Circle drive + covered parking** | Loop D through the front lawn and the open path between the oaks, plus a porte-cochère (A) or a carport (B) | Layout proposed | Both front oaks' trunk positions; covered-parking choice; county permits |

## Order of work

The projects share prerequisites. Doing these first unblocks everything, and most of them
are cheap.

### Step 0: find what's buried, and pin the lines (now)

1. **Get the septic permit file** from Travis County's on-site sewage facility (OSSF) office
   for this address. The permit file usually has a drawing of the tank and drainfield.
   - It's the single biggest unknown. Building B's west end, any US-290 wall footing, the
     north end of the back-line trees and the septic truck's route all wait on it.
   - If there's no drawing, have the septic company locate and probe the tank lids and
     trenches next time it pumps.
2. **Locate the buried electric line.** It runs underground from the meter pole at the NW
   fence corner to the house's NW corner (owner, Oct 18 2026). The route between isn't known.
   - **Straight, it would pass over the well,** so it probably bends around it, and maybe
     around the septic tank.
   - **Straight, it would run ~36 ft under site A and clip building B's SW corner** (~4.5 ft
     of run). Whichever way it bends at the well, its last stretch passes B's SW corner on
     the way to the house.
   - **How to find it:**
     - It's private past the meter, so 811 won't mark it. Hire a private utility locator, or
       rent a cable locator (a transmitter on the line and a hand receiver; tool-rental
       shops have them).
     - A metal detector wouldn't do it: they rarely reach a cable 18–24 in down, and they
       don't follow a line.
     - Clues: which way the conduit sweeps into the ground at the pole and at the house, and
       a settled or off-color stripe in the grass.
   - Have the locator give the depth too.
   - **No slab over the line as it is** (see notes, "A slab over the buried line"). Reroute it
     in new conduit around the chosen site. Use the same trench as building B's own power.
   - Call 811 (Texas811) as well before any digging, for the utility-owned lines.
3. **Stake the property lines.** A surveyor sets pins on the US-290 line and the back line.
   - Both fences wander off the surveyed lines. Building B sits on the 5 ft setback with no
     slack, and the back fence is partly on the retail lot.
4. **Arborist visit**, one trip:
   - the twin oak by the garage apron: root-zone protection plan for B's construction, and
     the compacted ground under the parked cars;
   - the big leaning oak propped by the house's west wall;
   - the lone oak in the front lawn: trunk size and root zone for the circle drive;
   - the Ashe junipers at the NW corner: which are male (pollen). That check is best in
     December–January.
5. **Paperwork:**
   - the title commitment's deed restrictions: walls, fences, outbuildings, materials, the
     45 ft building line;
   - Travis County: development permit for building B, a driveway permit for the second
     curb cut, and whether OSSF reviews a new building or a garage conversion on a septic
     lot.

### Step 1: this cool season (Oct–Feb)

- **Plant the back-line trees.** October to February is the planting window; see project 2.
- **Mulch the twin oak**, 3–4 in deep out to the drip line where it isn't paved. Keep cars,
  bins and storage off its root zone.
- **Seal the US-290 fence's gaps** if we own it (project 2). It's the cheapest noise step.
- **Pruning:** any oak pruning for building B's roof or the drive goes July–January only
  (oak wilt). Finish it by the end of January, or wait until July.

### Step 2: the building at site A

After the buried line is traced and the septic layout is known. See project 1.

### Step 3: circle drive and covered parking, then the kitchen

Parking has to exist out front before the garage stops being a garage. Building B's concrete
pump and steel delivery use the north driveway, so build B first; the circle drive's
construction can then follow without working around B's.

## Project 1: The building (site A; site B dropped Oct 18 2026)

**Now at site A** (owner, Oct 18 2026): a standard steel kit, 30 ft wide across the strip,
35, 30 or 25 ft long along the line. The ridge runs along the line, and one 12 × 12 ft roll-up
door is in the south half of the east end wall: a north door's apron would sit on the septic
access pipe. Just north of it is a commercial walk door: hollow metal in a welded frame, a
continuous hinge, Grade 1 hardware and a closer, so it won't sag or stick (owner, Oct 18 2026;
notes, "The walk door"). The 3D plan draws 30 × 35 with the S130 inside.

Tube frame, dealer-installed (owner, Oct 18 2026: red-iron is out).

| Size | Turnkey, likely (80% band) | Per sq ft | + insulation and power |
|---|---|---|---|
| 30 × 35 ft (1,050 sq ft) | $67k ($60–74k) | $64 | $12k ($10–15k) |
| 30 × 30 ft (900 sq ft) | $59k ($53–65k) | $65 | $12k ($9–14k) |
| 30 × 25 ft (750 sq ft) | $51k ($46–56k) | $68 | $11k ($9–13k) |

The commercial walk door and its landing add ~$3k to each (it was $64k, $56k, $48k).

- For comparison, ~800 sq ft of portable wood sheds on blocks is ~$25–41k (notes, "For
  comparison: ~800 sq ft of portable sheds").

- Planning ranges from `tools/shed_cost.py`, not quotes. Notes, "What the building at site A
  costs", has the breakdown, the sources and the owner work that cuts the cost.
- The slope adds ~$11–21k: fill and a stem wall on the low SW side.
- **Impervious cover: confirm the limit applies before anything else.**
  - Against 15%, the lot is already at ~16% (5,502 sq ft of 5,065 allowed). The building
    makes it ~19–20%, and loop D ~23–24%.
  - But 15% is the City's SOS number, and the 1992 ordinance exempted single-family
    development on lots that existed by Nov 1, 1991. This one did (recorded plat Vol. 55
    Pg. 69; the April 1991 survey shows the house).
  - Ask Travis County TNR whether any limit applies to an accessory building here.
  - See notes, "Does the 15% even apply?".
- **Before anything:** trace the buried service line (it likely runs under the site) and
  find the drainfield and the tank's outline. The door's apron is 12.5 ft from the septic
  access pipe; nothing gets poured or driven over the tank.
- **Decisions for you:** the size; insulation; power.

The rest of this section is building B's study at site B, kept for the record.

**Footprint:** 23 × 43 ft (989 sq ft), square to the house, at the old carport spot
(`site-b.png`).

| Edge | Clearance | Limit |
|---|---|---|
| North wall (US-290) | 5.1 ft from the surveyed line at the NE corner | 5 ft setback |
| West end | 10.0 ft from the septic access pipe | 10 ft keep-out (until the county gives a number) |
| East end | 25.0 ft from the twin oak's near trunk | the oak's drip line (25.1 ft) |
| South side | ~15 ft to the house's north wall | ~12 ft septic truck lane |

**It fits with no slack on three sides.** Stake the line and pin down the septic pipe before
the slab is laid out.

**Issues to settle:**
- **The cross fence.** The ~4.5 ft fence and chain-link gate between the US-290 fence and the
  house sit about where B's east wall goes (from the photo, ±5 ft). Either the fence and gate
  move a few feet east, or B's east end stops short. Measure where the fence meets the house
  and the US-290 fence.
- **The gate** is the only way in for the septic truck and for B's construction. Pump and
  concrete trucks are ~8.5 ft wide, so a 12 ft opening is better than ~10.
- **The ground falls ~3.8 ft across the slab**, high at the NE corner by the oak. Level it
  with fill or a stem wall on the west side, never a cut toward the oak.
- **Overhead lines** run just outside the US-290 fence. Keep cranes, lifts and steel at least
  10 ft from them while erecting, and have the utility confirm the north eave's clearance.

**Construction access:**
- A concrete pump parks on the driveway, with a line or boom to the slab. No loaded trucks
  under the twin oak.
- The steel delivery's crane or forklift works from the paved drive. Lay plywood over mulch
  for anything wheeled beyond it.

**Look (Oct 18 2026):** dark grey on every surface, with two roll-up doors on the south long
wall. See `building-b-*.jpg` and the 3D page (`tools/building_b.html`), which has sliders
for the eave height and door size. Drawn with 12 × 12 ft doors at the quarter points and a
3:12 gable; both are placeholders.
- **The east door faces the house's NW corner, ~15 ft away.** That's tight for driving a
  vehicle in. The west door has the open yard in front of it.
- **If both doors take vehicles,** shift them west, or put the second door in the east end.

**For noise:** solid north wall with no doors, windows or vents; roll-up doors on the south or
east side; insulated wall panels. It's a yard shield: ~7 dB right behind it, ~3.5 dB at the
house's west end, ~1 dB or less elsewhere.

**Decisions for you:**
- **Eave height.** 12–14 ft shields more of the yard. Check the overhead-line clearance.
- **Use:** vehicles, trailer or RV/boat, shop. That sets the doors, slab thickness, power
  and water.
- **Doors:** sizes and which walls.
- **Power:** from the house side or the west. Never trench through the oak's root zone, and
  route around the buried service line once it's located.
- **Foundation:** build up the low (SW) side with compacted crushed-limestone base, not extra
  concrete.
  - About 66 cu yd at B, the cheapest way by ~$4k.
  - Slope the fill's edges where there's room. Put a block stem wall only where a slope
    can't go: the truck lane, root zones.
  - See notes, "Building up the low side".
- **For comparison, site A** (Oct 18 2026): 30 × 34 ft (1,020 sq ft) between the well and the
  septic pipe. It was 27 ft deep; the owner had the far (SSW) wall pushed out past 1,000 sq ft.
  - The 3D plan draws a shed there like B ("building A"). Its doors face east toward B: the
    only way in, along the strip past B.
  - **Better than B:** the ground falls 3.1 ft (B's falls 3.8), and it's ~90 ft from the oak.
  - **Worse than B:** the drainfield may be under it, the buried service line likely runs
    under it, and it's farther for trucks.
  - It also screens less of the house from US-290: it sits at the far west end.

## Project 2: Screening (noise and views)

### US-290 side (traffic noise and view)

- **The fence is already 8 ft** (horizontal boards; correction Oct 13 2026). The earlier
  noise estimates assumed no fence, so part of what they credit to new walls already
  exists.
- **Next:**
  1. Find out who owns the fence: it stands up to ~7 ft beyond the surveyed line.
  2. If it's ours, seal the gaps between boards: battens over the joints, or a second layer
     of boards on our side.
  3. Re-run the noise model with the fence as the baseline, then decide whether a taller
     wall or a return along Candelaria is still worth it.
- **An 8 ft fence on the surveyed north line** (owner, Oct 18 2026) is drawn in the 3D
  model.
  - **Length:** from the back corner to the 45 ft building line, 207.9 ft. It was pulled back
    from the front corner the same day.
  - **The front 45.6 ft** could follow if the deed restrictions allow a variance, since that
    side faces US-290.
  - **What it buys (`noise_model.py` geometry, airtight 8 ft fence vs. none):**
    - ~4 dB at the house's west end and middle, ~2.5–3 dB at the kitchen end;
    - running it to the front corner adds ~2 dB at the kitchen end.
  - **Sealing the gaps** (two layers of boards, offset half a board) is worth ~0.5 dB at 5%
    open area in this model. That's because the fence's effect is modest here: the road sits
    17.5 ft below.
  - **A kickboard** closes the gap at the bottom of the fence.
  - **Height, and how far the fence runs,** matter more than sealing the gaps.
  - **The twin oak:** its second trunk is 5.8 ft from the line, so ~21 ft of fence falls
    inside the 12 ft no-dig zone. Hand-dig or air-spade those posts, or bridge that stretch,
    and do any cutting July–January.
  - **Building B:** its north wall is 5.1 ft from the line (~4 ft clear under the eave).
  - **Front yard:** the deed restrictions may limit fence height in front of the 45 ft
    building line.
- **Wall constraints, if we go further:**
  - The footing must be fully on our side of the line.
  - It conflicts with the septic pipe (6 ft from a footing at the line); the wall would jog
    in or stop there.
  - Piers, not a trench, inside oak drip lines.
  - A gate of ~12 ft for the septic truck if the wall returns along Candelaria.
- **Inside the house:** north- and west-facing windows are often the cheapest big gain.
  Laminated glass with unequal panes (compare by OITC), or interior acoustic inserts; seal
  the frames.

### Back line (the retail and apartments)

- **Planting** (21 new trees in the gaps of the existing tree line, `plan3d.py`):
  - 13 Nellie R. Stevens hollies, 10 ft in from the line (outside the utility easement),
    ~10 ft apart;
  - 4 yaupon (berried females) and 4 Texas mountain laurel, 22 ft in, between the hollies;
  - 6 planned spots are already under existing trees, and 2 are in the well's keep-out.
- **No cypress or juniper** (household allergies). The species list is in `notes.md`.
- **Buy:** 15-gal hollies (5–6 ft) reach ~15 ft in about 8 years with drip irrigation, and
  20–25 ft mature.
- **Install:** drip irrigation for 2–3 summers; deer cages on the yaupon and laurel; hand-dig
  under existing oaks.
- **What it screens:** the retail buildings, which sit behind our back line. The apartments
  are off to the south-west, beyond the line's reach, and the woods on the retail lot's south
  arm already hide them. Those woods are approved to stay as stormwater irrigation ground.
- **Behind the fence:** the retail's stormwater ponds run the length of our back line, a
  mowed grass basin with a pump. The developer plans no screening.

### Not drawn yet

- Trees along our south side line, if the arm's woods ever come down.
- A pergola or evergreens by the deck, which screen the most per foot of height where we
  sit.

## Project 3: Garage → kitchen

**Moved to its own private repo, `smprather/kitchen-garage-renovation` (Oct 16 2026).** It
holds the measurements, the layout mockup, the structure and the renovation's own list of
measurements. What ties it to the rest of this plan:

- **Parking first:** the circle drive and covered parking (project 4) must be in use before
  the garage stops holding cars.
- **Septic:** ask Travis County OSSF whether ~440 sq ft of added living area changes the
  required capacity. The same question goes for building B.
- **The apron stays a drive lane.** The old garage door becomes glass onto the apron. The
  apron is still the way to the north gate, for the septic truck and building B's
  construction.

## Project 4: Circle drive and covered parking

See `front-yard.png` and the 3D viewer's "Front yard" view.

- **Loop D (proposed, Oct 18; replaces loop C):**
  - **Route:** a 12 ft lane from a new curb cut in the open south lawn, sweeping to the
    house, along the porch front (drop-off at the porch).
    - Then it turns back toward the street through the open path the owner showed in the
      photos: between the lone lawn oak and the leaning oak in the lawn bulge.
    - It joins the existing drive ~10–20 ft in from the street.
  - **Why not loop C:** C crossed the lawn bulge to reach the drive, and the bulge holds a
    big leaning live oak, ~1 ft from C's paving.
  - **Paving:** ~1,370 sq ft new, about 60% of the original sketch.
  - **Clearances, paving edge to trunk:**
    - ~13 ft to each oak. The trunks were placed from photos, ±8 ft.
    - That's inside both root zones (assumed 20 ft), so build the connector no-dig:
      permeable pavers or gravel over geogrid, on the existing grade.
    - Keep ~13.5 ft of clear height under the limbs for a truck.
  - **The front walk:** the lane crosses it about 40 ft back from the street.
  - **Under the porch-front oaks:** build that stretch no-dig too.
  - **Tape both trunks before finalizing** (see the measurement list).
  - **Hedge and myrtle:** the hedge's street end and the crape myrtle may need to move.
- **Covered parking, one of:**

  | Option | What | For | Against |
  |---|---|---|---|
  | **A: porte-cochère** | ~12 × 44 ft roof over the porch-front lane, behind the 45 ft building line; 2 cars nose to tail, ~10 ft clear | Fits loop D; dry walk to the door | Tandem parking; under porch-front oaks |
  | **B: carport on the garage apron** | ~23 × 24 ft off the existing drive | Uses existing paving; covered porch walk | Sits on the septic truck's route (needs a drive-through with ~14 ft clear); under the twin oak |
  | Original sketch | ~26 × 33 ft cover in front of the house | Most room | Crosses the 45 ft building line: needs relief from the plat or deed restrictions |

- **Permits:** a Travis County driveway permit for the second curb cut (maybe a culvert).
  Check impervious-cover limits, since the lots next door are in the Barton Springs Zone.
- **Utilities:** a pole at the street's south side lines up with the plat's 1991 electric
  line to the house. Loop D's south leg (same as C's) stays ~19 ft from that line; locate it
  anyway.

**Decision for you:** A, B, or pursuing the larger cover.

## Measurements still needed

The kitchen's measurements are listed in its own repo.

| What | Why | How |
|---|---|---|
| Cross fence: both ends, from the house's NW corner (A) | Building B's east end | Tape |
| Chain-link gate's clear opening | Truck access to B and the septic | Tape |
| The rusty casing by the burn barrel: is it the well? Its distance to both fences | Keep-outs for the trees and any wall | Look and tape |
| Lone front-lawn oak: trunk position and girth. Two tapes from house corners pin it: from the south rooms' front corners (south and north ends) | Loop D | Tape |
| Bulge oak, between the drive and the porch's north end (and the stump beside it): trunk position and girth, the same way from the porch's front corners | Loop D's connector | Tape |
| Along the street: from the walk's center to the drive's south edge | Whether the drive was widened since 1991 (plat ~36 ft, aerial ~28 ft) | Tape |
| Twin oak's second trunk girth (worksheet 11) | Root-zone size | Tape around at 4.5 ft up |
| Branches over B's east end (17a) | Roof and erection clearance | Laser or pole |
| Eave height wanted for B | Noise, overhead lines | Decision |
| **House model:** photos taken square-on to each wall, with the 6 ft range pole (or a tape) standing against it: south wall, back walls, the two-story's south face, the front | Windows, doors, eave and gable heights on walls not yet seen | Photos |
| **House model:** ground to the gutter at the front porch, the garage's NE corner, the two-story's north eave and the back wall; the roof pitch on one gable (a phone level on the rake) | Heights and pitches (now guessed) | Laser or tape |
| **House model:** along the back wall from the SW corner: the deck's ends, the chimney, the back door; the deck's height above the lawn | Deck, chimney and door positions | Tape |
| **House model:** the step from the walk up to the porch, and from the deck down to the lawn | The floor level | Tape |
| **House model:** the pergola: its posts from the back wall and the two-story's south face, and the roof's height at both edges | Pergola (now guessed) | Tape |

## Sources

- `notes.md`: the running record behind every number here.
- Maps: `site-b.png`, `envelope.png`, `front-yard.png`, `lot.png`, `north-yard.png`.
- 3D: `plan3d.html` (the viewer); the back-yard renders `backyard-bare.jpg` and
  `backyard-8yr.jpg`.
- **The private repo** (`smprather/shed-design-private`) holds:
  - the neighbors' plans, SP-2019-0411D (retail) and SP-2018-0138D (apartments);
  - the site photos;
  - our property papers (`property/`: the 1991 plat; closing, title and septic papers
    still to add);
