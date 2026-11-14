"""The house in 3D, a first pass: walls, roofs, porch, deck, chimney and the openings we know.

Sources:
- the 1991 plat (walls and ties: HOUSE_ST in site_plan.py);
- the county record (2,829 sq ft first floor + 882 sq ft second, "2 story rock/frame");
- the owner's garage and kitchen measurements (Oct 15 2026);
- the yard photos (Oct 13 and Oct 18 2026, private repo).

What the photos settle:
- **The two-story part** runs along the north wall, from just west of the garage out through
  the NW wing (s 85.2-126.2 x t 68.8-90.1 = 873 sq ft, close to the county's 882). Its north
  face has a stone first story with vertical siding above; its back gable and its south face
  over the deck are siding from the ground up (Oct 18). An eave runs along the north, and the
  gable faces the back yard, with a louvered vent at its peak.
- **The north face** (photos 12 and 16, Nov 13 scan): the stone runs level at the garage door's header
  (~7.3 ft) all along, with a cream band board on it, and the cream board-and-batten siding above
  (vertical boards, a batten every 8 in). Three short windows sit in the stone and three more right
  under the eave, over them, and a fourth near the garage (four upstairs, owner, Nov 13). The
  upstairs windows have grey frames (IMG_3470; the owner's photos from inside). Gutters and downspouts are dark charcoal: a downspout at the garage's
  corner and one at the NW corner. The AC condenser stands on a pad by the west gable, near its north
  end (photos 10 and 12).
- **The south face, over the deck** (IMG_3465, 3469, 3470): the second floor overhangs the first by
  about a foot (a soffit at ~8.4 ft). Upstairs, a band of four tall windows starts at the SW corner,
  with one more window round the corner on the gable. Downstairs, from the west: a small window over
  a pet door, a tall window, dark-framed French doors and a tall window by the inside corner.
- **The back of the main block:** the stone south rooms (with the chimney) and, north of
  them, a sided wall with a window and a dark-framed sliding door onto the deck. Its eave runs
  level the whole way, with a gutter (IMG_3465): the roofs are hipped at the back, not gabled. A
  window in the stone, near its north end.
- **The deck** is an L: along the back wall, and on along the two-story's south face nearly to its
  corner, with its steps where the two arms meet. Dark red-brown stain. A cedar-post pergola on four
  posts, with a corrugated metal roof sloping down away from the two-story, covers the inside
  corner (size and heights from the photos, +/-2 ft).
- **One main roof across the front** (owner's street photo, Nov 13 2026): a single eave runs the
  whole front, from the SE bedroom wing (its gablet) across the entry and the porch to the garage
  end, and one slope rises west from it, the porch under it. Its south end is hipped: the hip
  climbs from the front corner by the bedroom wing to the two-story. Over the entry and kitchen a
  back slope comes down to the level back eave. The garage's north wall is the tall sloped face
  over the door.
- **The garage's north face** (owner's photo from the apron, Nov 12 2026; corrected Nov 13 from
  photo 16 and IMG_3473 at full size): stone up to the door's header, the same vertical
  board-and-batten as the rest above it (not lap siding), and a small louvered vent high on the
  sloped face, centered over the door.
- **The south rooms** face the street with a hipped front and a small gable set back on it
  (street photo, Oct 18). The stone back wing with the
  chimney sits south of the deck.

- **The windows:** every one facing US-290, and every one upstairs, is double-pane with a thin air
  gap; the rest are single panes (owner, Nov 14 2026; corrects Nov 13's all single-pane).

Everything else (roof pitches, heights, the middle roof, windows on the walls nobody has
photographed) is a guess, to be tightened with tape and photos.

Survey frame (s, t) in feet: s back from the front line, t from the south line toward US-290.
Heights are feet above the finished floor (FF). house_spec() turns it all into the house's local
frame for the viewer: x = -s (east), y = t (north), z up from FF.
"""

from typing import Callable

FF_FT = 1055.5      # finished floor, ft NAVD88: just under the lidar ground at the garage's NE corner (1055.6); a guess
STONE = 8.0         # Austin stone up to here on the first story; vertical siding above (photos)
STONE_N = 7.3       # the north face's stone: level with the garage door's header, all along (photos 12 and 16)
OVERHANG = 1.2      # the second floor's overhang on the south face, over the deck (IMG_3465, 3470; +/-0.5)
SOFFIT = 8.4        # the overhang's underside, ft above FF (IMG_3465: the doors' heads at 6.8)
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
GABLET = 5.5                         # the south rooms' front gable sits this far back on a hipped front (street photo, Oct 18)
SHED_K = (EAVE2 - PORCH_EAVE) / (TWO[0] - PORCH[0])   # porch + garage plane, rise per ft going west (~4:12)
DECK = (100.8, 110.8, 44.8, 68.8)    # along the back wall (the county's 240 sq ft); position from IMG_3465, +/-2 ft
DECK2 = (110.8, 125.4, 61.4, 68.8)   # its arm along the two-story's south face (IMG_3465, 3470)
PERGOLA = (100.8, 111.6, 54.4, 10.2, 8.6)   # s0, s1, t0 (its low, outer edge), roof at the two-story, at t0 (IMG_3465, 3470)
PERGOLA_POSTS = ((102.6, 110.2), (56.4, 66.0))   # s, t of its four posts
AC = (126.9, 129.7, 81.4, 84.2)      # the AC condenser by the west gable (photos 10 and 12; +/-2 ft)
NORTH_UP = (109.5, 103.0, 96.5, 88.2)   # s of the north face's four upstairs windows, west to east (photos 12, 16; owner, Nov 13)
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

    def wall(a, b, out, top, stone=STONE):
        """A wall from a to b (s, t), outward normal `out` (local x, y), with its top as (u, z) points.

        top: [(u, z), ...] from u = 0 at a to u = |ab| at b, the wall's upper edge. Stone runs up to `stone`
        (feet above FF), siding above it; 0 is a sided wall on a stone foundation.
        """
        ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        bottom = min(ground_rel(*a), ground_rel(*b), ground_rel((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 0.0) - 0.3
        poly = [(0.0, bottom), (ab, bottom)] + [(round(u, 3), round(z - TUCK, 3)) for u, z in reversed(top)]
        walls.append({"a": L(*a), "b": L(*b), "out": out, "thick": WALL,
                      "stone": _clip(poly, stone, True), "siding": _clip(poly, stone, False)})

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
    rise_2 = (TWO[3] - TWO[2]) / 2 * PITCH
    tm_s = (SOUTH[2] + SOUTH[3]) / 2

    # Walls, going round the outside (the plat's outline), then the faces that show above lower roofs.
    wall((56.7, 22.7), (56.7, 50.4), E, flat((56.7, 22.7), (56.7, 50.4), EAVE1))   # front of the south rooms, under the hipped front
    wall((56.7, 50.4), (69.2, 50.4), N, flat((56.7, 50.4), (69.2, 50.4), EAVE1))      # beside the entry
    wall((69.2, 50.4), (69.2, 57.6), E, flat((69.2, 50.4), (69.2, 57.6), EAVE1))      # front door's recess
    wall((69.2, 57.6), (64.2, 57.6), S_, flat((69.2, 57.6), (64.2, 57.6), EAVE1))
    wall((64.2, 57.6), (64.2, 68.8), E, flat((64.2, 57.6), (64.2, 68.8), EAVE1))      # kitchen, under the porch
    wall((64.2, 68.8), (64.2, 90.1), E, flat((64.2, 68.8), (64.2, 90.1), shed_z(64.2)))   # garage, under the porch
    wall((64.2, 90.1), (85.2, 90.1), N, [(0, shed_z(64.2)), (21.0, shed_z(85.2))], stone=STONE_N)   # garage door wall, sloped top: stone to the door's header, siding above (photos)
    wall((85.2, 90.1), (126.2, 90.1), N, flat((85.2, 90.1), (126.2, 90.1), EAVE2), stone=STONE_N)    # two-story, north
    wall((126.2, 90.1), (126.2, 68.8), W_, gable_top((126.2, 90.1), (126.2, 68.8), EAVE2, EAVE2 + rise_2), stone=0.0)   # back gable, sided
    wall((126.2, 68.8), (100.8, 68.8), S_, flat((126.2, 68.8), (100.8, 68.8), SOFFIT), stone=0.0)  # two-story's first floor, over the deck, sided
    wall((100.8, 68.8), (100.8, 50.4), W_, flat((100.8, 68.8), (100.8, 50.4), EAVE1), stone=0.0)   # back wall, sided, under the hip
    wall((100.8, 50.4), (100.8, 22.7), W_, flat((100.8, 50.4), (100.8, 22.7), EAVE1))   # back of the stone south rooms, under the hip
    wall((100.8, 22.7), (56.7, 22.7), S_, flat((100.8, 22.7), (56.7, 22.7), EAVE1))   # south wall
    # The second floor over the deck, out OVERHANG ft past the first (its top under the roof, which keeps its ridge).
    t_up, z_up = TWO[2] - OVERHANG, EAVE2 - OVERHANG * PITCH
    walls.append(_upper((126.2, t_up), (100.8, t_up), S_, SOFFIT, flat((126.2, t_up), (100.8, t_up), z_up), L))
    walls.append(_upper((126.2, TWO[2]), (126.2, t_up), W_, SOFFIT, [(0, EAVE2), (OVERHANG, z_up)], L))   # the gable's overhanging edge
    walls.append(_upper((100.8, t_up), (100.8, TWO[2]), E, SOFFIT, [(0, z_up), (OVERHANG, EAVE2)], L))    # its east end, over the hip
    box(100.8, 126.2, t_up, TWO[2], SOFFIT - 0.15, SOFFIT, "frame")                                       # soffit
    # Faces above the lower roofs.
    walls.append(_upper((100.8, 68.8), (85.2, 68.8), S_, EAVE1, flat((100.8, 68.8), (85.2, 68.8), EAVE2), L))
    walls.append(_upper((85.2, 68.8), (85.2, 90.1), E, 15.0, gable_top((85.2, 68.8), (85.2, 90.1), EAVE2, EAVE2 + rise_2), L))   # down to where the main roof's hip meets it
    ga, gb = (SOUTH[0] + GABLET, SOUTH[2] + GABLET), (SOUTH[0] + GABLET, SOUTH[3] - GABLET)
    walls.append(_upper(ga, gb, E, EAVE1 + GABLET * PITCH, gable_top(ga, gb, EAVE1 + GABLET * PITCH, EAVE1 + rise_s), L))   # front gable

    # Roofs.
    def gable_roof(r, eave, rise, oh_s=(OH, OH), oh_t=(OH, OH)):
        s0, s1, t0, t1 = r
        tm, zr = (t0 + t1) / 2, eave + rise
        k = rise / ((t1 - t0) / 2)
        a, b = s0 - oh_s[0], s1 + oh_s[1]
        quad((a, t0 - oh_t[0], eave - oh_t[0] * k), (b, t0 - oh_t[0], eave - oh_t[0] * k), (b, tm, zr), (a, tm, zr))
        quad((a, t1 + oh_t[1], eave - oh_t[1] * k), (b, t1 + oh_t[1], eave - oh_t[1] * k), (b, tm, zr), (a, tm, zr))
        box(a, b, tm - 0.4, tm + 0.4, zr - 0.05, zr + 0.2, "ridge")   # ridge cap

    # South rooms: hipped front and back (the back's eave runs level, IMG_3465), with the small front gable set back on
    # the front hip.
    f0, f1, g0, g1 = SOUTH
    lo, zb, zr = EAVE1 - OH * PITCH, EAVE1 + GABLET * PITCH, EAVE1 + rise_s
    sw, se, nw, ne = (f1 + OH, g0 - OH, lo), (f0 - OH, g0 - OH, lo), (f1 + OH, g1 + OH, lo), (f0 - OH, g1 + OH, lo)   # eave corners
    rb, rf = (f1 + OH - (tm_s - g0 + OH), tm_s, zr), (f0 + GABLET, tm_s, zr)        # ridge, back to front
    fs, fn = (f0 + GABLET, g0 + GABLET, zb), (f0 + GABLET, g1 - GABLET, zb)          # the front gable's feet
    quad(sw, rb, rf, fs); quad(sw, fs, se, se)        # south slope
    quad(nw, rb, rf, fn); quad(nw, fn, ne, ne)        # north slope
    quad(se, ne, fn, fs)                              # hipped front
    quad(nw, sw, rb, rb)                              # hipped back
    box(f0 + GABLET, rb[0], tm_s - 0.4, tm_s + 0.4, zr - 0.05, zr + 0.2, "ridge")   # ridge cap
    gable_roof(TWO, EAVE2, rise_2, oh_s=(0.6, OH), oh_t=(OH + OVERHANG, OH))
    # The main roof over the entry, kitchen, porch and garage (owner's street photo, Nov 13 2026): one front slope
    # rising west from a single eave along the whole front, from the SE bedroom wing to the garage end, the porch
    # under it. Over the entry and kitchen a back slope comes down to the level back eave (IMG_3465), and the south end
    # is hipped, so the hip climbs from the front corner by the bedroom wing up to the two-story (the street photo's
    # diagonal). Each slope is drawn where it's the lowest of the three, which is how a hipped roof's planes meet.
    p0 = PORCH[0] - 0.5
    m0, m1, n0, n1 = MIDDLE
    front = lambda s_, t_: shed_z(s_)  # noqa: E731
    back = lambda s_, t_: lo + (m1 + OH - s_) * PITCH  # noqa: E731
    hip = lambda s_, t_: shed_z(p0) + (t_ - n0) * PITCH  # noqa: E731
    entry = [(p0, n0), (m1 + OH, n0), (m1 + OH, n1), (p0, n1)]                    # entry and kitchen, with the eaves
    garage = [(p0, n1), (TWO[0], n1), (TWO[0], PORCH[3] + OH), (p0, PORCH[3] + OH)]   # porch and garage, to the two-story
    for zone, planes in ((entry, (front, back, hip)), (garage, (front, hip))):
        for pl in planes:
            poly = zone
            for other in planes:
                if other is not pl:
                    poly = _cut(poly, lambda s_, t_, a=pl, b=other: a(s_, t_) - b(s_, t_))
            if len(poly) >= 3:
                quad(*[(s_, t_, pl(s_, t_)) for s_, t_ in poly])

    # Porch: floor, stone columns and the beam.
    box(PORCH[0], PORCH[1], PORCH[2], PORCH[3], min(ground_rel(PORCH[0], 75), 0) - 0.3, -0.3, "concrete", walk=True)
    for t in (58.4, 69.0, 79.4, 89.4):
        box(PORCH[0] + 0.1, PORCH[0] + 1.6, t - 0.75, t + 0.75, -0.3, PORCH_EAVE - 0.6, "stone")
    box(PORCH[0], PORCH[0] + 0.6, MIDDLE[2], PORCH[3] + 0.5, PORCH_EAVE - 0.6, PORCH_EAVE, "fascia")   # the beam, on to the bedroom wing

    # Deck: an L, low, with no railing; the steps down to the lawn where its arms meet (IMG_3465, 3470).
    for s0, s1, t0, t1 in (DECK, DECK2):
        box(s0, s1, t0, t1, min(ground_rel(s1, (t0 + t1) / 2), 0) - 0.3, -0.45, "deck-skirt")
        box(s0, s1, t0, t1, -0.45, -0.3, "deck", walk=True)
    s0, t0 = DECK[1] + 0.2, DECK2[2]
    g = min(ground_rel(s0 + 2, t0 - 2), -0.6)
    box(s0, s0 + 3.6, t0 - 1.1, t0, (g - 0.3) / 2 - 0.15, (g - 0.3) / 2, "deck", walk=True)
    box(s0, s0 + 3.6, t0 - 1.1, t0, g - 0.2, (g - 0.3) / 2 - 0.15, "deck-skirt")

    # Pergola over the deck's inside corner: four cedar posts, beams along s, and a corrugated metal roof sloping down
    # away from the two-story, its high edge against the overhang's wall.
    p0, p1, q0, zh, zl = PERGOLA
    k = (zh - zl) / (t_up - q0)
    roof_z = lambda t: zl + (t - q0) * k  # noqa: E731
    (sa, sb), (ta, tb) = PERGOLA_POSTS
    for t in (ta, tb):
        zb_ = roof_z(t - 0.25) - 0.05
        for s_ in (sa, sb):
            box(s_ - 0.3, s_ + 0.3, t - 0.3, t + 0.3, -0.3, zb_ - 0.7, "post")
        box(p0 + 0.3, p1 - 0.3, t - 0.25, t + 0.25, zb_ - 0.7, zb_, "post")   # beam
    quad((p0, q0, zl), (p1, q0, zl), (p1, t_up, zh), (p0, t_up, zh), mat="metal-roof")

    # The AC condenser on its pad by the west gable.
    a0, a1, b0, b1 = AC
    g = ground_rel((a0 + a1) / 2, (b0 + b1) / 2)
    box(a0 - 0.3, a1 + 0.3, b0 - 0.3, b1 + 0.3, g - 0.2, g + 0.25, "concrete", walk=True)
    box(a0, a1, b0, b1, g + 0.25, g + 3.1, "ac")
    box(a0 + 0.2, a1 - 0.2, b0 + 0.2, b1 - 0.2, g + 3.1, g + 3.2, "trim")

    # Band board on the north face's stone, and the gutters and downspouts (dark charcoal; photos 12, 16, IMG_3465).
    box(64.2, 126.2, 90.1 - 0.05, 90.1 + 0.15, STONE_N - 0.05, STONE_N + 0.55, "frame")
    z_n, z_s = EAVE2 - OH * PITCH, EAVE2 - (OH + OVERHANG) * PITCH
    box(TWO[0] - 0.6, TWO[1] + OH, TWO[3] + OH - 0.05, TWO[3] + OH + 0.4, z_n - 0.45, z_n + 0.05, "trim")   # two-story, north
    box(TWO[0] - 0.6, TWO[1] + OH, TWO[2] - OH - OVERHANG - 0.4, TWO[2] - OH - OVERHANG + 0.05, z_s - 0.45, z_s + 0.05, "trim")  # south
    box(SOUTH[1] + OH - 0.05, SOUTH[1] + OH + 0.4, SOUTH[2] - OH, MIDDLE[3], lo - 0.45, lo + 0.05, "trim")      # the back's level eave
    box(PORCH[0] - 0.95, PORCH[0] - 0.5, MIDDLE[2], PORCH[3] + OH, shed_z(PORCH[0] - 0.5) - 0.45, shed_z(PORCH[0] - 0.5) + 0.05, "trim")  # the front eave
    for s_, t_, ztop in ((85.6, 90.35, z_n), (125.8, 90.35, z_n), (126.45, t_up + 0.3, z_s), (101.05, 46.6, lo),
                         (PORCH[0] - 0.7, PORCH[3] + 0.3, shed_z(PORCH[0] - 0.5))):
        box(s_ - 0.13, s_ + 0.13, t_ - 0.18, t_ + 0.18, min(ground_rel(s_, t_), 0) - 0.1, ztop - 0.2, "trim")

    # Chimney.
    c = CHIMNEY
    box(c[0], c[1], c[2], c[3], min(ground_rel(c[1], c[2]), 0) - 0.3, c[4], "stone")
    box(c[0] - 0.2, c[1] + 0.2, c[2] - 0.2, c[3] + 0.2, c[4], c[4] + 0.35, "trim")

    # Openings: proud of the wall face by 0.1 ft.
    def opening(face_s=None, face_t=None, out=None, span=(0, 0), z=(0, 0), mat="glass", frame=True, shutters=False, frame_mat="frame"):
        d = 0.1
        if face_s is not None:   # wall at constant s; out is east (+x, smaller s) or west
            sgn = 1 if out == E else -1
            sa, sb = face_s - sgn * d, face_s + sgn * 0.15
            if frame:
                box(sa + sgn * 0.03, sb, span[0] - 0.25, span[1] + 0.25, z[0] - 0.25, z[1] + 0.25, frame_mat)
            box(sa, sb, span[0], span[1], z[0], z[1], mat)
            if shutters:
                for t0_, t1_ in ((span[0] - 1.6, span[0] - 0.35), (span[1] + 0.35, span[1] + 1.6)):
                    box(sa, sb, t0_, t1_, z[0], z[1], "shutter")
        else:                    # wall at constant t; out is north (+y) or south
            sgn = 1 if out == N else -1
            ta, tb = face_t + sgn * d, face_t - sgn * 0.15
            if frame:
                box(span[0] - 0.25, span[1] + 0.25, ta - sgn * 0.03, tb, z[0] - 0.25, z[1] + 0.25, frame_mat)
            box(span[0], span[1], ta, tb, z[0], z[1], mat)

    opening(face_s=56.7, out=E, span=(28.4, 31.9), z=(2.8, 7.4), shutters=True)    # front, two shuttered windows (photo 18)
    opening(face_s=56.7, out=E, span=(41.2, 44.7), z=(2.8, 7.4), shutters=True)
    opening(face_s=SOUTH[0] + GABLET, out=E, span=(tm_s - 0.8, tm_s + 0.8), z=(EAVE1 + rise_s - 2.4, EAVE1 + rise_s - 1.2),
            mat="vent", frame=False)                                               # front gable vent (street photo)
    opening(face_s=69.2, out=E, span=(52.6, 55.6), z=(0, 6.8), mat="door", frame=True)   # front door, in the recess
    opening(face_s=64.2, out=E, span=(60.7, 66.7), z=(3.0, 7.0))                   # kitchen window (floor plan)
    opening(face_s=64.2, out=E, span=(73.8, 79.8), z=(3.0, 7.0))                   # garage window (owner's markup)
    opening(face_t=90.1, out=N, span=(66.7, 82.7), z=(-0.4, 7.0), mat="garage-door", frame=True)   # 16 x 7 (photo 16)
    opening(face_t=90.1, out=N, span=(74.0, 75.5), z=(12.6, 14.1), mat="vent", frame=False)   # louvered vent over the door's middle (photo 16)
    for s in NORTH_UP[:3]:                                                         # two-story north (photo 12): short windows in the stone,
        opening(face_t=90.1, out=N, span=(s - 1.9, s + 1.9), z=(5.0, 6.8))         # and the same right under the eave
        opening(face_t=90.1, out=N, span=(s - 1.9, s + 1.9), z=(15.0, 17.2), frame_mat="frame-grey")
    opening(face_t=90.1, out=N, span=(NORTH_UP[3] - 1.4, NORTH_UP[3] + 1.4), z=(15.0, 17.2), frame_mat="frame-grey")   # photo 16
    for s in (123.9, 120.5, 117.1, 113.7):                                         # over the deck: a band of four from the SW corner (IMG_3470)
        opening(face_t=t_up, out=S_, span=(s - 1.5, s + 1.5), z=(12.3, 16.9), frame_mat="frame-grey")
    opening(face_s=126.2, out=W_, span=(68.7, 71.3), z=(12.3, 16.9), frame_mat="frame-grey")   # back gable, by the south corner (IMG_3470)
    # The two-story's first floor, over the deck, from the west (IMG_3465, 3470): a small window over a pet door, a tall
    # window, French doors and a tall window by the inside corner; the doors' frames are dark.
    opening(face_t=68.8, out=S_, span=(118.4, 120.0), z=(4.1, 6.6))
    opening(face_t=68.8, out=S_, span=(118.9, 119.7), z=(0.6, 2.5), mat="frame", frame=False)   # pet door
    opening(face_t=68.8, out=S_, span=(113.2, 116.4), z=(1.4, 6.7))
    opening(face_t=68.8, out=S_, span=(104.0, 110.0), z=(0, 6.8), frame_mat="trim")
    opening(face_t=68.8, out=S_, span=(101.6, 103.4), z=(1.5, 6.8), frame_mat="trim")
    # The back wall: a window by the inside corner and a sliding door onto the deck (IMG_3465), and a window in the stone.
    opening(face_s=100.8, out=W_, span=(64.3, 66.8), z=(3.0, 6.8))
    opening(face_s=100.8, out=W_, span=(56.5, 62.5), z=(0, 6.8), frame_mat="trim")
    opening(face_s=100.8, out=W_, span=(45.6, 48.6), z=(3.0, 7.3))
    opening(face_s=126.2, out=W_, span=(78.4, 80.5), z=(EAVE2 + 1.0, EAVE2 + 2.6), mat="vent", frame=False)   # gable vent

    return {"ff_ft": FF_FT, "walls": walls, "roofs": roofs, "boxes": boxes,
            "notes": "First pass from the plat, county record, kitchen measurements and photos; most heights, the middle roof and unseen windows are guesses."}


def _cut(poly: list[tuple[float, float]], f: Callable[[float, float], float]) -> list[tuple[float, float]]:
    """Clip an (s, t) polygon to where the linear function f(s, t) <= 0."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = f(*p), f(*q)
        if fp <= 0:
            out.append(p)
        if (fp <= 0) != (fq <= 0):
            k = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k))
    return out


def _upper(a, b, out, z0, top, L) -> dict:
    """A wall face that shows only above a lower roof, from z0 up to its top edge."""
    ab = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    poly = [(0.0, z0), (ab, z0)] + [(round(u, 3), round(z - TUCK, 3)) for u, z in reversed(top)]
    return {"a": L(*a), "b": L(*b), "out": out, "thick": WALL, "stone": [], "siding": poly}


def porte_spec(ground_rel: Callable[[float, float], float]) -> dict:
    """The porte-cochere (drive_layout.py) in the house's frame, for the same viewer code: stone columns like the
    porch's, beams, a beadboard ceiling and a hipped roof at the house's pitch, its outer edge on the 45 ft line.

    It stands clear of the house's eaves: its back eave rides ~2 ft over the porch's and the south rooms' eaves,
    where it would be flashed into them.
    """
    from drive_layout import COLUMN, COVER, COVER_COLUMNS, COVER_EAVE, COVER_PITCH

    L = lambda s, t: [round(-s, 3), round(t, 3)]  # noqa: E731
    boxes, roofs = [], []

    def box(s0, s1, t0, t1, z0, z1, mat):
        boxes.append({"min": [round(-max(s0, s1), 3), round(min(t0, t1), 3), round(z0, 3)],
                      "max": [round(-min(s0, s1), 3), round(max(t0, t1), 3), round(z1, 3)], "mat": mat})

    def quad(*pts):
        roofs.append({"pts": [L(s, t) + [round(z, 3)] for s, t, z in pts], "mat": "roof"})

    s0, s1, t0, t1 = COVER
    base = sum(ground_rel(cs, ct) for cs, ct in COVER_COLUMNS) / len(COVER_COLUMNS)   # the forecourt, about
    beam, eave = base + COVER_EAVE - 0.6, base + COVER_EAVE
    h = COLUMN / 2
    for cs, ct in COVER_COLUMNS:
        box(cs - h - 0.12, cs + h + 0.12, ct - h - 0.12, ct + h + 0.12, ground_rel(cs, ct) - 0.3, ground_rel(cs, ct) + 0.6, "stone")   # plinth
        box(cs - h, cs + h, ct - h, ct + h, ground_rel(cs, ct), beam, "stone")
        box(cs - h - 0.1, cs + h + 0.1, ct - h - 0.1, ct + h + 0.1, beam - 0.25, beam, "fascia")                                # cap
    for a, b, c, d in ((s0, s0 + 0.6, t0, t1), (s1 - 0.6, s1, t0, t1), (s0, s1, t0, t0 + 0.6), (s0, s1, t1 - 0.6, t1)):
        box(a, b, c, d, beam, eave, "fascia")                                                                             # beams, fascia
    box(s0 + 0.6, s1 - 0.6, t0 + 0.6, t1 - 0.6, beam + 0.15, beam + 0.2, "frame")                                         # ceiling
    rise = (s1 - s0) / 2 * COVER_PITCH
    sm, r = (s0 + s1) / 2, eave + rise
    ta, tb = t0 + (s1 - s0) / 2, t1 - (s1 - s0) / 2
    quad((s0, t0, eave), (s0, t1, eave), (sm, tb, r), (sm, ta, r))
    quad((s1, t1, eave), (s1, t0, eave), (sm, ta, r), (sm, tb, r))
    quad((s1, t0, eave), (s0, t0, eave), (sm, ta, r), (sm, ta, r))
    quad((s0, t1, eave), (s1, t1, eave), (sm, tb, r), (sm, tb, r))
    box(sm - 0.3, sm + 0.3, ta, tb, r - 0.05, r + 0.15, "ridge")                                                          # ridge cap
    return {"walls": [], "roofs": roofs, "boxes": boxes}
