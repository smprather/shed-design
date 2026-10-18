"""The house in 3D, a first pass: walls, roofs, porch, deck, chimney and the openings we know.

Sources:
- the 1991 plat (walls and ties: HOUSE_ST in site_plan.py);
- the county record (2,829 sq ft first floor + 882 sq ft second, "2 story rock/frame");
- the owner's garage and kitchen measurements (Oct 15 2026);
- the yard photos (Oct 13 2026, private repo).

What the photos settle:
- **The two-story part** runs along the north wall, from just west of the garage out through
  the NW wing (s 85.2-126.2 x t 68.8-90.1 = 873 sq ft, close to the county's 882). It has a
  stone first story, vertical siding above, an eave along the north and a gable facing the
  back yard.
- **The porch and the garage share one roof plane** that rises west from the porch eave to the
  two-story's eave. The garage's north wall is the tall sloped face over the door.
- **The south rooms** have the front gable on the street side. The stone back wing with the
  chimney sits south of the deck.

Everything else (roof pitches, heights, the middle roof, windows on the walls nobody has
photographed) is a guess, to be tightened with tape and photos.

Survey frame (s, t) in feet: s back from the front line, t from the south line toward US-290.
Heights are feet above the finished floor (FF). house_spec() turns it all into the house's local
frame for the viewer: x = -s (east), y = t (north), z up from FF.
"""

from typing import Callable

FF_FT = 1055.5      # finished floor, ft NAVD88: just under the lidar ground at the garage's NE corner (1055.6); a guess
STONE = 8.0         # Austin stone up to here on the first story; vertical siding above (photos)
PITCH = 5 / 12      # main gables (guess)
EAVE1 = 8.5         # first-story eave
EAVE2 = 18.0        # two-story eave (photo scale)
OH = 1.5            # eave and rake overhang
WALL = 0.5          # wall thickness
TUCK = 0.06         # wall tops sit just under the roof planes, so the two don't flicker

SOUTH = (56.7, 100.8, 22.7, 50.4)    # south rooms: s0, s1, t0, t1; front gable, ridge along s
MIDDLE = (64.2, 100.8, 50.4, 68.8)   # entry, kitchen and the rooms behind: gable, ridge along s (guess)
GARAGE = (64.2, 85.2, 68.8, 90.1)
TWO = (85.2, 126.2, 68.8, 90.1)      # two-story part, including the NW wing
PORCH = (54.5, 64.2, 57.6, 90.1)
PORCH_EAVE = 7.6                     # porch roof at its front edge (photo scale)
SHED_K = (EAVE2 - PORCH_EAVE) / (TWO[0] - PORCH[0])   # porch + garage plane, rise per ft going west (~4:12)
DECK = (100.8, 110.8, 44.8, 68.8)    # 240 sq ft (county), off the middle of the back wall; position a guess
CHIMNEY = (99.3, 102.3, 38.0, 43.0, 17.5)   # stone; on the back of the south rooms (photo 02); size a guess


def shed_z(s: float) -> float:
    return PORCH_EAVE + (s - PORCH[0]) * SHED_K


def _clip(poly: list[tuple[float, float]], z: float, keep_below: bool) -> list[tuple[float, float]]:
    """Clip a (u, z) polygon to one side of a level line."""
    out = []
    inside = (lambda p: p[1] <= z) if keep_below else (lambda p: p[1] >= z)
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        if inside(p):
            out.append(p)
        if inside(p) != inside(q):
            k = (z - p[1]) / (q[1] - p[1])
            out.append((p[0] + (q[0] - p[0]) * k, z))
    return out


def house_spec(ground_rel: Callable[[float, float], float]) -> dict:
    """The house for the viewer, in its local frame (x = -s, y = t, z up from FF, feet).

    ground_rel(s, t) is the 2017 lidar ground minus FF, in feet; it sets how far the stone
    foundation shows below the floor.
    """
    L = lambda s, t: [round(-s, 3), round(t, 3)]  # noqa: E731
    walls, boxes, roofs = [], [], []

    def wall(a, b, out, top, extra=()):
        """A wall from a to b (s, t), outward normal `out` (local x, y), with its top as (u, z) points.

        top: [(u, z), ...] from u = 0 at a to u = |ab| at b, the wall's upper edge.
        """
        ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        bottom = min(ground_rel(*a), ground_rel(*b), ground_rel((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 0.0) - 0.3
        poly = [(0.0, bottom), (ab, bottom)] + [(round(u, 3), round(z - TUCK, 3)) for u, z in reversed(top)]
        walls.append({"a": L(*a), "b": L(*b), "out": out, "thick": WALL,
                      "stone": _clip(poly, STONE, True), "siding": _clip(poly, STONE, False)})

    def flat(a, b, h):
        ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        return [(0.0, h), (ab, h)]

    def gable_top(a, b, h, peak):
        ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        return [(0.0, h), (ab / 2, peak), (ab, h)]

    def box(s0, s1, t0, t1, z0, z1, mat, walk=False):
        boxes.append({"min": [round(-max(s0, s1), 3), round(min(t0, t1), 3), round(z0, 3)],
                      "max": [round(-min(s0, s1), 3), round(max(t0, t1), 3), round(z1, 3)], "mat": mat, **({"walk": True} if walk else {})})

    def quad(*pts, mat="roof"):
        roofs.append({"pts": [L(s, t) + [round(z, 3)] for s, t, z in pts], "mat": mat})

    E, N, W_, S_ = [1, 0], [0, 1], [-1, 0], [0, -1]   # outward normals in local (x east, y north)
    rise_s = (SOUTH[3] - SOUTH[2]) / 2 * PITCH
    rise_m = (MIDDLE[3] - MIDDLE[2]) / 2 * PITCH
    rise_2 = (TWO[3] - TWO[2]) / 2 * PITCH
    tm_s, tm_m, tm_2 = (SOUTH[2] + SOUTH[3]) / 2, (MIDDLE[2] + MIDDLE[3]) / 2, (TWO[2] + TWO[3]) / 2

    # Walls, going round the outside (the plat's outline), then the faces that show above lower roofs.
    wall((56.7, 22.7), (56.7, 50.4), E, gable_top((56.7, 22.7), (56.7, 50.4), EAVE1, EAVE1 + rise_s))   # front gable
    wall((56.7, 50.4), (69.2, 50.4), N, flat((56.7, 50.4), (69.2, 50.4), EAVE1))      # beside the entry
    wall((69.2, 50.4), (69.2, 57.6), E, flat((69.2, 50.4), (69.2, 57.6), EAVE1))      # front door's recess
    wall((69.2, 57.6), (64.2, 57.6), S_, flat((69.2, 57.6), (64.2, 57.6), EAVE1))
    wall((64.2, 57.6), (64.2, 68.8), E, flat((64.2, 57.6), (64.2, 68.8), EAVE1))      # kitchen, under the porch
    wall((64.2, 68.8), (64.2, 90.1), E, flat((64.2, 68.8), (64.2, 90.1), shed_z(64.2)))   # garage, under the porch
    wall((64.2, 90.1), (85.2, 90.1), N, [(0, shed_z(64.2)), (21.0, shed_z(85.2))])   # garage door wall, sloped top
    wall((85.2, 90.1), (126.2, 90.1), N, flat((85.2, 90.1), (126.2, 90.1), EAVE2))    # two-story, north
    wall((126.2, 90.1), (126.2, 68.8), W_, gable_top((126.2, 90.1), (126.2, 68.8), EAVE2, EAVE2 + rise_2))   # back gable
    wall((126.2, 68.8), (100.8, 68.8), S_, flat((126.2, 68.8), (100.8, 68.8), EAVE2))  # two-story, over the deck
    back = 68.8 - 22.7
    wall((100.8, 68.8), (100.8, 22.7), W_, [(0, EAVE1), ((68.8 - tm_m), EAVE1 + rise_m), (68.8 - 50.4, EAVE1),
                                           ((68.8 - tm_s), EAVE1 + rise_s), (back, EAVE1)])   # back wall, two gable ends
    wall((100.8, 22.7), (56.7, 22.7), S_, flat((100.8, 22.7), (56.7, 22.7), EAVE1))   # south wall
    # Faces above the lower roofs.
    walls.append(_upper((100.8, 68.8), (85.2, 68.8), S_, EAVE1, flat((100.8, 68.8), (85.2, 68.8), EAVE2), L))
    walls.append(_upper((85.2, 68.8), (64.2, 68.8), S_, EAVE1, [(0, shed_z(85.2)), (21.0, shed_z(64.2))], L))
    walls.append(_upper((85.2, 68.8), (85.2, 90.1), E, EAVE2 - 0.6, gable_top((85.2, 68.8), (85.2, 90.1), EAVE2, EAVE2 + rise_2), L))
    walls.append(_upper((64.2, 50.4), (64.2, 68.8), E, EAVE1, gable_top((64.2, 50.4), (64.2, 68.8), EAVE1, EAVE1 + rise_m), L))

    # Roofs.
    def gable_roof(r, eave, rise, oh_s=(OH, OH), oh_t=(OH, OH)):
        s0, s1, t0, t1 = r
        tm, zr = (t0 + t1) / 2, eave + rise
        k = rise / ((t1 - t0) / 2)
        a, b = s0 - oh_s[0], s1 + oh_s[1]
        quad((a, t0 - oh_t[0], eave - oh_t[0] * k), (b, t0 - oh_t[0], eave - oh_t[0] * k), (b, tm, zr), (a, tm, zr))
        quad((a, t1 + oh_t[1], eave - oh_t[1] * k), (b, t1 + oh_t[1], eave - oh_t[1] * k), (b, tm, zr), (a, tm, zr))
        box(a, b, tm - 0.4, tm + 0.4, zr - 0.05, zr + 0.2, "trim")   # ridge cap

    gable_roof(SOUTH, EAVE1, rise_s, oh_t=(OH, 0.0))
    gable_roof(MIDDLE, EAVE1, rise_m, oh_s=(0.0, OH), oh_t=(0.0, 0.0))
    gable_roof(TWO, EAVE2, rise_2, oh_s=(0.6, OH))
    # Porch + garage: one plane rising west to the two-story's eave.
    p0 = PORCH[0] - 0.5
    quad((p0, PORCH[2] - OH, shed_z(p0)), (p0, PORCH[3] + OH, shed_z(p0)),
         (GARAGE[0], PORCH[3] + OH, shed_z(GARAGE[0])), (GARAGE[0], PORCH[2] - OH, shed_z(GARAGE[0])))
    quad((GARAGE[0], GARAGE[2], shed_z(GARAGE[0])), (GARAGE[0], GARAGE[3] + OH, shed_z(GARAGE[0])),
         (GARAGE[1], GARAGE[3] + OH, shed_z(GARAGE[1])), (GARAGE[1], GARAGE[2], shed_z(GARAGE[1])))

    # Porch: floor, stone columns and the beam.
    box(PORCH[0], PORCH[1], PORCH[2], PORCH[3], min(ground_rel(PORCH[0], 75), 0) - 0.3, -0.3, "concrete", walk=True)
    for t in (58.4, 69.0, 79.4, 89.4):
        box(PORCH[0] + 0.1, PORCH[0] + 1.6, t - 0.75, t + 0.75, -0.3, PORCH_EAVE - 0.6, "stone")
    box(PORCH[0], PORCH[0] + 0.6, PORCH[2] - 0.5, PORCH[3] + 0.5, PORCH_EAVE - 0.6, PORCH_EAVE, "trim")

    # Deck (240 sq ft), with a railing on its two open sides.
    s0, s1, t0, t1 = DECK
    box(s0, s1, t0, t1, min(ground_rel(s1, (t0 + t1) / 2), 0) - 0.3, -0.45, "deck-skirt")
    box(s0, s1, t0, t1, -0.45, -0.3, "deck", walk=True)
    for t in [t0 + 0.2 + k * 6 for k in range(5)]:
        box(s1 - 0.35, s1 - 0.05, t - 0.15, t + 0.15, -0.3, 3.0, "deck")
    for s in [s0 + 2 + k * 4.4 for k in range(3)]:
        box(s - 0.15, s + 0.15, t0 + 0.05, t0 + 0.35, -0.3, 3.0, "deck")
    box(s1 - 0.4, s1, t0, t1, 2.8, 3.0, "deck")
    box(s0, s1, t0, t0 + 0.4, 2.8, 3.0, "deck")

    # Chimney.
    c = CHIMNEY
    box(c[0], c[1], c[2], c[3], min(ground_rel(c[1], c[2]), 0) - 0.3, c[4], "stone")
    box(c[0] - 0.2, c[1] + 0.2, c[2] - 0.2, c[3] + 0.2, c[4], c[4] + 0.35, "trim")

    # Openings: proud of the wall face by 0.1 ft.
    def opening(face_s=None, face_t=None, out=None, span=(0, 0), z=(0, 0), mat="glass", frame=True, shutters=False):
        d = 0.1
        if face_s is not None:   # wall at constant s; out is east (+x, smaller s) or west
            sgn = 1 if out == E else -1
            sa, sb = face_s - sgn * d, face_s + sgn * 0.15
            if frame:
                box(sa + sgn * 0.03, sb, span[0] - 0.25, span[1] + 0.25, z[0] - 0.25, z[1] + 0.25, "frame")
            box(sa, sb, span[0], span[1], z[0], z[1], mat)
            if shutters:
                for t0_, t1_ in ((span[0] - 1.6, span[0] - 0.35), (span[1] + 0.35, span[1] + 1.6)):
                    box(sa, sb, t0_, t1_, z[0], z[1], "shutter")
        else:                    # wall at constant t; out is north (+y) or south
            sgn = 1 if out == N else -1
            ta, tb = face_t + sgn * d, face_t - sgn * 0.15
            if frame:
                box(span[0] - 0.25, span[1] + 0.25, ta - sgn * 0.03, tb, z[0] - 0.25, z[1] + 0.25, "frame")
            box(span[0], span[1], ta, tb, z[0], z[1], mat)

    opening(face_s=56.7, out=E, span=(28.4, 31.9), z=(2.8, 7.4), shutters=True)    # front, two shuttered windows (photo 18)
    opening(face_s=56.7, out=E, span=(41.2, 44.7), z=(2.8, 7.4), shutters=True)
    opening(face_s=69.2, out=E, span=(52.6, 55.6), z=(0, 6.8), mat="door", frame=True)   # front door, in the recess
    opening(face_s=64.2, out=E, span=(60.7, 66.7), z=(3.0, 7.0))                   # kitchen window (floor plan)
    opening(face_s=64.2, out=E, span=(73.8, 79.8), z=(3.0, 7.0))                   # garage window (owner's markup)
    opening(face_t=90.1, out=N, span=(66.7, 82.7), z=(-0.4, 7.0), mat="garage-door", frame=True)   # 16 x 7 (photo 16)
    for s in (96.5, 103.0, 109.5):                                                 # two-story north (photo 12)
        opening(face_t=90.1, out=N, span=(s - 1.9, s + 1.9), z=(5.2, 7.3))
        opening(face_t=90.1, out=N, span=(s - 1.9, s + 1.9), z=(14.8, 16.8))
    opening(face_t=90.1, out=N, span=(86.8, 89.6), z=(14.8, 16.8))                # photo 16, upper right
    for s in (106.0, 116.0):                                                       # two-story, over the deck (photo 02)
        opening(face_t=68.8, out=S_, span=(s - 1.9, s + 1.9), z=(14.8, 16.8))
    opening(face_s=100.8, out=W_, span=(55.5, 61.5), z=(0, 6.8))                   # door to the deck (guess)
    opening(face_s=126.2, out=W_, span=(78.4, 80.5), z=(EAVE2 + 1.0, EAVE2 + 2.6), mat="trim", frame=False)   # gable vent

    return {"ff_ft": FF_FT, "walls": walls, "roofs": roofs, "boxes": boxes,
            "notes": "First pass from the plat, county record, kitchen measurements and photos; most heights, the middle roof and unseen windows are guesses."}


def _upper(a, b, out, z0, top, L) -> dict:
    """A wall face that shows only above a lower roof, from z0 up to its top edge."""
    ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    poly = [(0.0, z0), (ab, z0)] + [(round(u, 3), round(z - TUCK, 3)) for u, z in reversed(top)]
    return {"a": L(*a), "b": L(*b), "out": out, "thick": WALL, "stone": [], "siding": poly}
