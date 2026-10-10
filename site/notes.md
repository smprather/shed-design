# Site notes: 8400 Candelaria Dr (78737)

This is the running record of what we know about the site. Measured facts go here
as they come in.

## Status

- The house was purchased in May 2026.
- The aerial (`8400_candelaria_78737.png`) **predates the sale**. Before selling,
  the previous owners removed **all the sheds** and the **teal-roofed carport
  canopies**, so nothing in the north and west yards shown on the aerial is still
  standing.

## Property record (Travis CAD, 2026)

| Field | Value |
|---|---|
| Property ID / Geo ID | 315319 / 0410480106 |
| Legal description | **Lot 176, Granada Hills Amended** (GIS map: J.P. Johannesen Survey, Abstract 3454) |
| Land | **0.7814 ac = 34,035.73 sq ft** |
| Taxing units | Austin ISD, Travis County, Travis Co. ESD No. 3, Travis Co. Healthcare District, ACC, TCAD. **No City of Austin**, so the lot is outside city limits. |
| House | Built 1972, slab foundation, gable roof with composition shingles, L-shaped. Main area 3,711 sq ft (2,829 on the 1st floor + 882 on the 2nd). |
| Other improvements listed | Attached garage, 441 sq ft (1st floor); open porch, 315 sq ft; enclosed finished porch, 78 sq ft; uncovered deck, 240 sq ft; concrete spa; fireplace |
| Not listed | No sheds, carport or other outbuildings were ever appraised. |

From listings (not on the CAD record): septic with public water is typical for
Granada Hills, and the HOA is voluntary. Deed restrictions may still apply.

## Lot shape (CAD parcel map over the aerial; see `lot.png`)

- The lot is a rough rectangle, longer east-to-west, and widens toward the back:
  - **~116 ft** of frontage on Candelaria Dr
  - **~255 ft** along the US-290 side
  - **~249 ft** along the neighbor to the south
  - **~158 ft** across the back (west) side, with a small jog
- The **fence on the US-290 side is within ~3 ft of the CAD property line** along its
  whole visible length. The CAD map is only good to about ±5 ft, so the survey is the
  real answer.
- The house sits about 55–60 ft back from the front line and about 25 ft from the
  south line.
- The north strip runs from the back line (x ≈ 64) to the east end of the old
  carport (x ≈ 205), **~140 ft** in all. It's 25–40 ft deep between the fence and the
  trees and house.
- The big open lawn in the zoomed-out aerial, south-west of the house, is mostly
  the **neighbor's** lot. Our back yard is the smaller lawn west of the house.
- The lot behind ours to the west is the Broadstone Scenic Brook subdivision.

## Goal

- Build a shed first, possibly combined with a 2-car covered parking structure.
- Put it about where the old canopies stood (tape-measured at **20 × 40 ft**), but larger.

## Known constraints

| Constraint | Status |
|---|---|
| **Septic system** in the back yard | Location unknown: shots 13–14, or the septic report from closing |
| **Large oak** in the back yard | Trunk, size and drip line unknown: shots 9–12 |
| **Live oaks** east of the old canopy site | Avoid root zones; trunks not located yet (shot 15) |
| **Fence**, US-290 side | ≈ the north property line; runs ~9° to the house and gets closer going east |
| **House** north wall | ~18 ft south of the old canopy footprint (aerial); probably the pull-in aisle |
| **Drive** from Candelaria Dr | Route and clearance into the site to be confirmed (shots 16–17) |
| **Jurisdiction** | Outside Austin city limits (probably the ETJ): permits go through Travis County, not the City. City tree rules shouldn't apply, but the oaks' roots still need protecting. |

## Map frame

- The aerial is rotated 29° so the house and Candelaria Dr sit square to the frame.
  Coordinates are in feet: **+x runs ESE toward Candelaria Dr, +y runs SSW away from US-290**,
  and up on the maps is NNE.
- The scale comes from the map's 20 ft bar (4.8 px/ft). It agrees with the 20 × 40
  tape measurement to within about 10%, and the zoomed-out view gives the same
  house size (~44 × 28 ft roof).
- The roof edges on the aerial sit about 1–2 ft outside the walls.
- The property line in `tools/site_plan.py` (`PARCEL`) was read by eye from the CAD
  map screenshot. Its scale is set so it encloses the CAD land area, and it's
  positioned using the house and the two removed sheds, which appear on both maps.

## Open questions

- Where are the septic tank and field, and what type of system is it (conventional or aerobic)?
- Which oak is "the large oak", and how big is it?
- What should "larger" hold: 2 cars plus a shed of what size, and anything else?
- The CAD record lists a 441 sq ft attached garage. Is it still a garage, and do you
  want the new covered parking in addition to it?
- Does Travis County's septic (OSSF) office need to review a new structure on a lot
  with a septic system? Ask before designing the foundation.
- Paperwork to dig out:
  - the **survey** from closing (exact lines and easements)
  - the **Granada Hills Amended plat** (building lines and utility easements), from the Travis County Clerk
  - the **septic inspection report or permit**
  - the **title commitment** (deed restrictions)
