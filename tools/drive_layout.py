"""The drive system, redesigned from scratch (owner, Oct 18 2026): the shapes the drive study and the 3D plan share.

The owner's brief: no tree removal; keep loop D (the circle through the open path between the lawn oaks); a
covered porte-cochere on the house front, out to the 45 ft building line, with a lane outside it so a car can
pass a parked one; building A's doors on its south side; and an estate-style drive: gravel
held in a stabilizer grid, bounded by concrete curbs so it never ruts, sinks or spreads into the lawn or the
house. The old drive and the front walk come out.

How it's laid out:
- Two entrances. The south one is new, in the open south lawn (loop D's). The north one stays where the old drive
  meets the street, so the street end doesn't move under the oaks there.
- The forecourt in front of the house: the porte-cochere's covered lane (two cars nose to tail, pavers on a
  concrete base) and the gravel lane outside it. Loop D's legs join it at each end.
- The service drive leaves the north entrance along the old drive's curl around the bulge oak (rebuilt in place,
  no deeper than the old one: those roots have lived beside it for 35 years) to the north court, the old garage
  apron. The court is the septic truck's stop, a turnaround and two guest spaces.
- The shop lane runs west from the court, between the house and the twin oak (outside its 12 ft no-dig), along
  the strip to the concrete ramp up to building A's doors (since Oct 24, when A went on a pier-and-beam floor; it
  replaced a 12 ft apron and a raised gravel court).

Survey-local (s, t) feet: s back from the front line, t from the south line toward US-290 (site_plan.st).
No heavy imports, so drive_plan.py and plan3d.py can both use it.
"""

import math

from front_layout import catmull_rom, offset

# Candelaria Dr: the plat's 50 ft right-of-way runs from our front line out to s = -50. The asphalt, measured off the
# aerial (its white edge lines at s ~ -20 and -38, +/-1.5 ft), is ~19 ft wide and sits off-center in it. So the
# county's strip between our line and the pavement is ~19.5 ft deep, and every drive crosses it (the old one did).
ROAD = (-38.5, -19.5)          # s range of the pavement
ROAD_LINES = (-20.0, -38.0)    # its white edge lines
ROAD_T = (-640.0, 175.0)       # t range drawn: past the Candelaria lots to the south, as far as the aerial shows it north
STREET_S = ROAD[1]             # the asphalt's near edge: the drive aprons run out to it
LANE = 12.0        # ft: loop D's legs
SERVICE = 10.0     # ft: the service drive and the shop lane, which carry a pickup, a trailer and a septic truck now and then
CURB = 0.67        # ft: concrete ribbon curb, 8 in wide (and ~12 in deep, with rebar)
APRON_TO = 10.0    # ft: the street aprons are concrete from the asphalt to this far inside the front line
# Building A's approach (Oct 24 2026): it stands on a pier-and-beam floor, so its south door sills are 3.6-4.4 ft above
# the ground there. A concrete ramp on compacted fill, between concrete side walls, runs from the sills down to the
# ground APPROACH_FOOT ft out (~1:5.4), a foot past the doors at the west end; the shop lane joins its east side.
APPROACH_FOOT = 25.0   # ft out from the south wall to the ramp's foot


# Building A's cut (owner, Oct 24 2026): the high NE side is dug down so the floor and the door sills sit ~2 ft lower,
# inside a low segmental-block retaining wall CUT_OFFSET ft off the north, east and west walls. The cut falls
# CUT_FALL toward the south, so water runs out the low side; the south side is already below the cut.
CUT_OFFSET = 2.0       # ft from the building to the retaining wall
CUT_FALL = 0.02        # the cut's fall toward the south


def cut_zone_a(L: float, W: float) -> list[tuple[float, float]]:
    """The dug-down area inside building A's retaining wall, in its own frame (ft): the footprint plus CUT_OFFSET on
    the north, east and west, open to the south."""
    return [(-CUT_OFFSET, -1.0), (L + CUT_OFFSET, -1.0), (L + CUT_OFFSET, W + CUT_OFFSET), (-CUT_OFFSET, W + CUT_OFFSET)]


# Building A's south side (owner, Oct 24 2026). The 25 ft concrete ramp serves only the west roll-up: no trailers now,
# but boat storage stays possible for a later owner, who'd back a boat trailer up it. The walk door and the east roll-up
# open onto a pressure-treated pier-and-beam landing at floor level, LANDING_DEEP out, with steps down in front of the
# east roll-up. The rest of the old approach is a gravel court at grade, where the shop lane arrives.
RAMP_TO = 13.0          # ft east of the SW corner: the ramp's east edge (the west roll-up is 2-12 ft)
LANDING_DEEP = 10.0     # ft out from the south wall
STEPS = (18.0, 28.0)    # ft along the wall: the steps, as wide as the east roll-up
STEPS_DEEP = 3.5        # ft: four treads


def ramp_a(L: float) -> list[tuple[float, float]]:
    """The west roll-up's ramp, in building A's frame (ft)."""
    return [(-1.0, 0.0), (RAMP_TO, 0.0), (RAMP_TO, -APPROACH_FOOT), (-1.0, -APPROACH_FOOT)]


def landing_a(L: float) -> list[tuple[float, float]]:
    """The landing in front of the walk door and the east roll-up, in building A's frame (ft)."""
    return [(RAMP_TO, 0.0), (L, 0.0), (L, -LANDING_DEEP), (RAMP_TO, -LANDING_DEEP)]


def steps_a() -> list[tuple[float, float]]:
    """The landing's steps down to the court, in building A's frame (ft)."""
    return [(STEPS[0], -LANDING_DEEP), (STEPS[1], -LANDING_DEEP), (STEPS[1], -LANDING_DEEP - STEPS_DEEP), (STEPS[0], -LANDING_DEEP - STEPS_DEEP)]


def approach_a(L: float) -> list[tuple[float, float]]:
    """The whole area in front of building A's doors, in its own frame (x east from its SW corner, y north, ft), for a
    building L ft long: the ramp, the landing and its steps, and the gravel court around them.

    Its SE corner is cut back on a diagonal for an oak, and a stub on its east side takes the shop lane.
    """
    return [(-1.0, 0.0), (L + 1.0, 0.0), (L + 5.0, -14.0), (L + 5.0, -16.0), (L - 4.0, -APPROACH_FOOT), (-1.0, -APPROACH_FOOT)]

# Loop D's legs, centerlines. The south leg comes in from the new curb cut and runs west into the forecourt's south
# end; the north leg leaves the forecourt's north end through the open path between the lone lawn oak and the bulge
# oak (owner's photos, Oct 18) and meets the street at the old drive's curb cut.
SOUTH_LEG = [(STREET_S, 33.0), (-1, 33.0), (12, 32.5), (24, 31.0), (38, 29.5)]
NORTH_LEG = [(39.25, 64.0), (36, 71.5), (30, 77.0), (23, 82.0), (15, 87.0), (7, 91.5), (-2, 95.0), (STREET_S, 95.5)]
# The forecourt: from 33.5 ft back (11.5 ft outside the 45 ft line) to the house, the porch and the front-door recess.
FORECOURT = [(33.5, 23.0), (56.7, 23.0), (56.7, 50.4), (54.5, 50.4), (54.5, 79.0), (33.5, 79.0)]   # stops 12 ft short of the bulge oak
# The porte-cochere: its roof from the 45 ft building line to the house, over the covered lane. Its back eave
# rides just above the porch's and the south rooms' eaves; stone columns like the porch's.
COVER = (45.0, 56.0, 29.5, 78.5)            # s0, s1, t0, t1 of the roof (ft)
COVER_EAVE = 9.6                            # ft above the forecourt: 9 ft clear under the beams
COVER_PITCH = 5 / 12                        # the house's pitch
COVER_COLUMNS = [(45.8, 30.5), (45.8, 54.0), (45.8, 77.5),           # front: centered on the front door
                 (55.3, 30.5), (55.3, 49.5), (55.3, 58.5), (55.3, 77.5)]   # back: framing the door's recess
COLUMN = 1.33                               # ft square, stone
# Pavers on a concrete base: under the cover, and the walk into the front door's recess.
PAVED = [(45.0, 23.0), (56.7, 23.0), (56.7, 50.4), (69.2, 50.4), (69.2, 57.6), (54.5, 57.6), (54.5, 79.0), (45.0, 79.0)]
PARK = [(t, t + 17.0) for t in (31.0, 59.0)]  # the two covered spaces (t ranges), either side of the front door

# The service drive: the north entrance to the north court, around the bulge oak on the old drive's curl.
SERVICE_DRIVE = [(9, 93.0), (20, 97.0), (31, 101.5), (39, 105.5), (47, 108.0), (54, 106.0), (60, 101.5), (66, 99.0)]
# The north court, on the old garage apron: it stops 12 ft from the twin oak's trunks, and 4 ft off the kitchen's
# north wall (the old garage door, which becomes a glass slider), leaving a planted strip under the glass.
NORTH_COURT = [(58.5, 94.5), (80.0, 94.5), (80.0, 106.0), (76.0, 110.0), (58.5, 110.0)]
# The shop lane: the north court to building A's approach ramp, past the house's north wall (4-7 ft off it) and the twin
# oak (12 ft off its trunks), then along the strip north of the back-lawn oaks.
SHOP_LANE = [(78, 98.5), (91, 99.0), (101, 100.0), (113, 102.0), (126, 104.5), (140, 107.0), (153, 109.0), (163, 108.0),
             (171, 104.0), (178, 98.0), (185, 93.0)]   # ends in the shop court, in front of the landing


def a_frame(sw, se, nw):
    """Building A's frame -> (s, t), given its SW, SE and NW corners in (s, t)."""
    L, W = math.dist(sw, se), math.dist(sw, nw)
    ux = ((se[0] - sw[0]) / L, (se[1] - sw[1]) / L)
    uy = ((nw[0] - sw[0]) / W, (nw[1] - sw[1]) / W)
    return lambda x, y: (sw[0] + ux[0] * x + uy[0] * y, sw[1] + ux[1] * x + uy[1] * y)


def lane(points, width: float) -> list[tuple[float, float]]:
    """A lane along a centerline, as a closed outline (s, t)."""
    center = catmull_rom(points)
    return offset(center, width / 2) + offset(center, -width / 2)[::-1]


def street_flares(points, width: float, flare: float = 3.0) -> list[tuple[float, float]]:
    """The curb-cut flares at the asphalt: a lane `flare` ft wider each side at the street, tapering in over 12 ft."""
    (s0, t0), (s1, t1) = points[0], points[1]
    n = math.hypot(s1 - s0, t1 - t0)
    u, v = ((s1 - s0) / n, (t1 - t0) / n), (-(t1 - t0) / n, (s1 - s0) / n)
    h, k = width / 2 + flare, 12.0
    return [(s0 + v[0] * h, t0 + v[1] * h), (s0 + u[0] * k + v[0] * width / 2, t0 + u[1] * k + v[1] * width / 2),
            (s0 + u[0] * k - v[0] * width / 2, t0 + u[1] * k - v[1] * width / 2), (s0 - v[0] * h, t0 - v[1] * h)]


def layout(a_corners) -> dict:
    """Every surface as a shapely shape in (s, t) ft. a_corners: building A's NW, NE, SE and SW corners in (s, t)."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    from site_plan import HOUSE_ST, PORCH_ST
    nw, ne, se, sw = a_corners
    A = a_frame(sw, se, nw)
    building = Polygon([sw, se, ne, nw])
    a_len = math.dist(sw, se)
    ramp = Polygon([A(x, y) for x, y in ramp_a(a_len)])
    landing = Polygon([A(x, y) for x, y in landing_a(a_len)]).union(Polygon([A(x, y) for x, y in steps_a()]))
    approach = ramp.union(landing)   # building A's own front, priced with it
    court = Polygon([A(x, y) for x, y in approach_a(a_len)]).difference(approach)
    house = Polygon(HOUSE_ST).union(Polygon(PORCH_ST))
    parts = {
        "south leg": Polygon(lane(SOUTH_LEG, LANE)).union(Polygon(street_flares(SOUTH_LEG, LANE))),
        "north leg": Polygon(lane(NORTH_LEG, LANE)).union(Polygon(street_flares(NORTH_LEG[::-1][:2], LANE))),
        "forecourt": Polygon(FORECOURT),
        "service drive": Polygon(lane(SERVICE_DRIVE, SERVICE)),
        "north court": Polygon(NORTH_COURT),
        "shop lane": Polygon(lane(SHOP_LANE, SERVICE)),
        "shop court": court,
    }
    parts = {k: g.buffer(0).difference(house).difference(approach).difference(building) for k, g in parts.items()}
    drive = unary_union(list(parts.values())).buffer(0.01).buffer(-0.01)
    concrete = drive.intersection(box(STREET_S - 10, -100, APRON_TO, 400))
    paved = Polygon(PAVED).buffer(0).difference(house).intersection(drive.union(Polygon(PAVED))).difference(concrete)
    gravel = drive.difference(concrete).difference(paved)
    edge_free = unary_union([house.buffer(0.7), approach.buffer(0.7), building.buffer(0.7), concrete.buffer(0.3)])
    curbs = gravel.boundary.difference(edge_free)
    return {"parts": parts, "drive": drive.union(paved), "concrete": concrete, "paved": paved, "gravel": gravel,
            "curbs": curbs, "approach": approach, "ramp": ramp, "landing": landing, "building": building, "house": house,
            "A": A, "a_len": a_len,
            "cover": box(COVER[0], COVER[2], COVER[1], COVER[3])}
