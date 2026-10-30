# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "polars", "rich-click", "shapely"]
# ///
"""Towing a boat in and out of building A: the ground a pickup and a 22 ft wake boat on its trailer sweep.

The owner's moves (Oct 30 2026):
- In: from Candelaria Dr up the drive and the shop lane into the back yard, a left turn (forward, no jackknife) that
  leaves the rig straight and lined up on the boat door, then straight back into the bay.
- Out: pull out of the bay, a sweeping left turn, and back down the shop lane and the drive to the street.

The rig (assumed; the owner's truck isn't known):
- A half-ton crew-cab pickup with a 5.5 ft bed (an F-150 SuperCrew: 145 in wheelbase, 231.7 in long, 47.8 ft
  curb-to-curb turning circle), the ball 4.6 ft behind its rear axle. `--truck hd` swaps in a 3/4-ton crew cab with
  an 8 ft bed.
- The boat the 3D plan carries: a 22 ft wake boat (8.5 ft beam) on a tandem-axle trailer, 27 ft from the swim
  platform to the coupler, the axles' middle 16.2 ft behind the coupler (plan3d_viewer.html's model).

The driver is reasonably good, not a computer. So:
- turns are planned at R_PLAN (the rear axle's radius), ~3/4 of full lock, and the wheel winds on and off over
  RAMP_FT of travel instead of snapping to lock;
- the driver steers by eye down a path (pure pursuit), so the rig cuts and drifts like a person's;
- every forward sweep carries FORWARD_MARGIN of slop each side, the straight back-in REVERSE_MARGIN outside the door;
- "lined up" (LINED_UP) means the truck within 3 degrees of the door's line and 0.75 ft of it, the trailer within 6
  degrees of the truck: close enough to back in with small corrections. Then the driver pulls PULL_EXTRA further
  before stopping. (A driver who swings the truck a little past the line straightens the boat sooner; the model
  doesn't count on it.);
- the hitch angle stays well short of the angle where the boat's bow or the tongue meets the truck's tailgate;
- the way out (EXITS, search_exit) keeps a margin off the trunks and the lot lines, and the more the better: 1.5 ft
  is a computer's line, 3.5 ft a person's.

What it found (Oct 30 2026): the back-in fits as asked. The way out doesn't, as one left sweep from the door: the
back-lawn oaks stand inside the circle it needs. With building A as planned, the only all-forward way onto the shop
lane is a 330 ft figure-eight with 1.5 ft to spare. Turned 10 degrees clockwise (the doors toward the SW and the open
lawn; --turn -10) and moved 2.5 ft off the line, it's one sweep: a touch right, a long left loop round the lawn and
up past the oaks onto the lane, 196 ft, with 3.5 ft to spare. Turning the doors toward the SE, or a full 45 degrees
either way, makes it worse.

Draws site/tow-paths.png (the whole way from the street) and site/tow-backyard.png (the back yard close up; with
--turn, site/tow-*-turnN.png), and prints the space each move takes and what it comes near: the building, the house,
the trees (trunks, and crowns the boat passes under, from the 2017 lidar), the well, the septic pipe and the lot lines.

Run: uv run tools/tow_plan.py [--turn -10] [--search [--margin 3.5]] [--truck half|hd] [--radius 22]
"""

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
import polars as pl
import rich_click as click
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from drive_layout import ROAD, SERVICE_DRIVE, SHOP_LANE, layout
from envelope_plan import SITE_A
from front_layout import EXISTING_DRIVE, FRONT_WALK, catmull_rom
from front_plan import SurveyFrame, canopy_in_st
from drive_plan import trees
from plan3d import CANOPY, FT, TERRAIN, Canopy, Frame, Terrain, field_features
from site_plan import CYAN, GREEN, ORANGE, PARCEL, RED, REPO, WHITE, Plan, draw_survey, site, st

OUT = REPO / "site" / "tow-paths.png"
OUT_BACK = REPO / "site" / "tow-backyard.png"

R_PLAN = 22.0          # ft: the rear axle's radius on the tightest planned turn (full lock is ~17.2 ft)
RAMP_FT = 8.0          # ft of travel to wind the wheel from straight to R_PLAN
LOOKAHEAD = 10.0       # ft: how far down the path the driver steers for
FORWARD_MARGIN = 2.0   # ft each side of a forward sweep: a person's path, not a computer's
REVERSE_MARGIN = 1.5   # ft each side of the straight back-in, outside the door
LINED_UP = (3.0, 0.75, 6.0)   # degrees off the door's line, ft off it, degrees between truck and trailer: good enough to back
PULL_EXTRA = 5.0       # ft pulled on past "lined up" before stopping to back
STERN_CLEAR = 3.5      # ft: pulling out, the boat's stern clears the door by this much before the wheel turns
BOAT_HEIGHT = 9.5      # ft: a wake boat on its trailer, tower folded (the 3D plan's stands 8.8 ft)
LIMB_CLEAR = 11.0      # ft: the limbs the boat passes under should be at least this high
STEP = 0.25            # ft per simulation step


@dataclass(frozen=True)
class Truck:
    name: str
    wheelbase: float   # ft
    front: float       # ft: front bumper ahead of the front axle
    rear: float        # ft: rear bumper behind the rear axle
    width: float       # ft, body; the mirrors stand ~0.7 ft out past it
    hitch: float       # ft: the ball behind the rear axle
    circle: float      # ft: curb-to-curb turning circle


TRUCKS = {
    "half": Truck("half-ton crew cab, 5.5 ft bed (F-150 SuperCrew 145 in)", 145 / 12, 3.25, 3.95, 6.66, 4.6, 47.8),
    "hd": Truck("3/4-ton crew cab, 8 ft bed (assumed: 176 in wheelbase)", 176 / 12, 3.4, 4.3, 6.75, 5.0, 54.0),
}


@dataclass(frozen=True)
class Boat:
    coupler_to_axle: float = 16.2   # ft: the coupler to the middle of the tandem axles
    tongue: float = 5.0             # ft: the coupler to the bow
    hull: float = 20.5              # ft
    platform: float = 1.5           # ft: the swim platform past the transom
    beam: float = 8.5               # ft


BOAT = Boat()


def min_radius(tr: Truck) -> float:
    """The rear axle's radius at full lock, from the curb-to-curb circle (the outer front tire's track)."""
    r_tire = tr.circle / 2 - 0.4
    return math.sqrt(r_tire**2 - tr.wheelbase**2) - 2.8   # less half the track


def truck_shape(tr: Truck) -> Polygon:
    """The truck in its own frame: x forward from the rear axle, y to the left; the mirrors stand off the cab."""
    w = tr.width / 2
    body = box(-tr.rear, -w, tr.wheelbase + tr.front, w)
    m = tr.wheelbase - 3.0
    return unary_union([body, box(m - 0.4, -w - 0.7, m + 0.4, w + 0.7)])


def boat_shape(b: Boat = BOAT) -> Polygon:
    """The boat on its trailer in the trailer's frame: x forward from the axles' middle (toward the coupler), y left."""
    transom = b.coupler_to_axle - b.tongue - b.hull
    hw = b.beam / 2
    plan = [(-1, 0), (1, 0), (1, 0.55), (0.82, 0.78), (0.45, 0.93), (0, 1), (-0.45, 0.93), (-0.82, 0.78), (-1, 0.55)]
    hull = Polygon([(transom + v * b.hull, u * hw) for u, v in plan])
    platform = box(transom - b.platform, -hw + 0.2, transom, hw - 0.2)
    tongue = Polygon([(b.coupler_to_axle + 0.5, 0.35), (b.coupler_to_axle + 0.5, -0.35), (transom + b.hull - 2.0, -2.9),
                      (transom + b.hull - 2.0, 2.9)])
    return unary_union([hull, platform, tongue])


# Poses are in a right-handed frame X = -s (toward the street), Y = t (toward US-290), so left turns go
# counter-clockwise. (s, t) in and out.
def to_xy(p):
    return (-p[0], p[1])


def to_st(p):
    return (-p[0], p[1])


@dataclass
class Pose:
    x: float      # the rear axle's middle
    y: float
    th: float     # the truck's heading
    psi: float    # the trailer's heading (from its axles toward the coupler)
    k: float = 0.0
    d: float = 0.0   # distance travelled (ft, signed)

    def hitch(self, tr: Truck):
        return self.x - tr.hitch * math.cos(self.th), self.y - tr.hitch * math.sin(self.th)

    def axle(self, tr: Truck, b: Boat = BOAT):
        hx, hy = self.hitch(tr)
        return hx - b.coupler_to_axle * math.cos(self.psi), hy - b.coupler_to_axle * math.sin(self.psi)


def placed(shape: Polygon, x: float, y: float, th: float) -> Polygon:
    """A shape from its own frame onto the ground, in (s, t)."""
    g = translate(rotate(shape, th, origin=(0, 0), use_radians=True), x, y)
    return Polygon([to_st(q) for q in g.exterior.coords])


def step(p: Pose, tr: Truck, k: float, ds: float) -> Pose:
    """Move the rear axle ds ft (negative backs up) on curvature k; the trailer follows its off-axle hitch."""
    dth = k * ds
    th_mid = p.th + dth / 2
    x, y = p.x + ds * math.cos(th_mid), p.y + ds * math.sin(th_mid)
    phi = p.th - p.psi
    dpsi = ds * (math.sin(phi) - tr.hitch * k * math.cos(phi)) / BOAT.coupler_to_axle
    return Pose(x, y, p.th + dth, p.psi + dpsi, k, p.d + ds)


def jackknife_angle(tr: Truck) -> float:
    """The hitch angle (degrees) at which the boat or its tongue first touches the truck."""
    t = truck_shape(tr)
    for deg in np.arange(0, 120, 0.5):
        phi = math.radians(deg)
        hx, hy = -tr.hitch, 0.0
        ax, ay = hx - BOAT.coupler_to_axle * math.cos(-phi), hy - BOAT.coupler_to_axle * math.sin(-phi)
        g = translate(rotate(boat_shape(), -phi, origin=(0, 0), use_radians=True), ax, ay)
        if g.intersects(t):
            return float(deg)
    return 120.0


def densify(pts_st, n: int = 16) -> np.ndarray:
    """A smooth reference path through (s, t) points, in X, Y, ~0.5 ft apart."""
    c = np.array([to_xy(p) for p in catmull_rom(pts_st, n)] + [to_xy(pts_st[-1])])
    seg = np.hypot(*np.diff(c, axis=0).T)
    keep = np.concatenate([[True], seg > 1e-6])
    c = c[keep]
    cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(c, axis=0).T))])
    ss = np.arange(0, cum[-1], 0.5)
    return np.column_stack([np.interp(ss, cum, c[:, 0]), np.interp(ss, cum, c[:, 1])])


def drive(p: Pose, tr: Truck, ref: np.ndarray, k_max: float, stop=None, limit: float = 2000.0) -> list[Pose]:
    """Drive forward down a reference path the way a person does: steer for a point LOOKAHEAD ahead, the wheel
    limited to k_max and wound at a person's pace. Stops at the path's end, or when stop(pose) says so."""
    out, i = [p], 0
    cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(ref, axis=0).T))])
    dk = k_max / RAMP_FT * STEP
    while p.d < limit:
        lo, hi = i, min(i + 60, len(ref))
        i = lo + int(np.argmin(np.hypot(ref[lo:hi, 0] - p.x, ref[lo:hi, 1] - p.y)))
        if cum[-1] - cum[i] < 0.6:
            break
        j = min(int(np.searchsorted(cum, cum[i] + LOOKAHEAD)), len(ref) - 1)
        tx, ty = ref[j]
        alpha = math.atan2(ty - p.y, tx - p.x) - p.th
        ld = max(math.hypot(tx - p.x, ty - p.y), 1.0)
        k = max(-k_max, min(k_max, 2 * math.sin(alpha) / ld))
        k = max(p.k - dk, min(p.k + dk, k))
        p = step(p, tr, k, STEP)
        out.append(p)
        if stop and stop(p):
            break
    return out


def straight(p: Pose, tr: Truck, dist: float) -> list[Pose]:
    """Straight ahead (dist > 0) or straight back (dist < 0), the wheel centered."""
    out, n = [p], int(abs(dist) / STEP)
    for _ in range(n):
        p = step(p, tr, 0.0, math.copysign(STEP, dist))
        out.append(p)
    return out


def sweep(poses: list[Pose], tr: Truck, every: float = 0.5) -> tuple[Polygon, Polygon]:
    """The ground the truck and the boat cover along a run of poses, in (s, t)."""
    ts, bs, last = truck_shape(tr), boat_shape(), None
    tl, bl = [], []
    for p in poses:
        if last is not None and abs(p.d - last) < every and p is not poses[-1]:
            continue
        last = p.d
        tl.append(placed(ts, p.x, p.y, p.th))
        ax, ay = p.axle(tr)
        bl.append(placed(bs, ax, ay, p.psi))
    return unary_union(tl).buffer(0.05).buffer(-0.05), unary_union(bl).buffer(0.05).buffer(-0.05)


def hitch_deg(p: Pose) -> float:
    return abs(math.degrees((p.th - p.psi + math.pi) % (2 * math.pi) - math.pi))


@dataclass
class Phase:
    name: str
    poses: list
    kind: str            # "in", "back", "out", or "blocked" (the sweep that doesn't fit)
    margin: float = FORWARD_MARGIN
    truck: Polygon = None
    boat: Polygon = None

    def swept(self, tr: Truck) -> None:
        self.truck, self.boat = sweep(self.poses, tr)

    @property
    def rig(self) -> Polygon:
        return self.truck.union(self.boat)

    @property
    def slop(self) -> Polygon:
        return self.rig.buffer(self.margin)


# The way out. A left sweep straight from the door can't reach the shop lane: the back-lawn oaks stand inside the
# circle it needs. What fits is the sweep a driver makes by swinging wide: a touch right toward the back fence, one long
# left loop round the open lawn, up past the oaks' west side onto the shop court, and right onto the lane. search_exit()
# finds it: A* over this rig's moves at R_PLAN, forward only, the hitch under 55 degrees, keeping `margin` off the
# trunks and lot lines and 1.5 ft off the building. Found paths are kept here by building A's turn (degrees, rot_study)
# as (margin, program); a program is (direction, ft, wheel) moves, the wheel from -1 (right, at R_PLAN) to +1 (left),
# replayed in REPLAY_STEP steps. --search finds them again (minutes).
EXITS = {
    0.0: (1.5, [(1, 4, 0.5), (1, 8, 1), (1, 4, 0.5), (1, 8, -1), (1, 8, 0), (1, 8, 1), (1, 4, 0.5), (1, 20, 1), (1, 4, 0), (1, 4, 1), (1, 4, 0.5), (1, 8, 1), (1, 4, 0), (1, 40, 1), (1, 4, 0.5), (1, 20, 1), (1, 8, 0.5), (1, 4, 1), (1, 4, 0), (1, 4, 1), (1, 8, -1), (1, 4, -0.5), (1, 56, -1), (1, 4, -0.5), (1, 20, -1), (1, 16, 0), (1, 4, 0.5), (1, 4, 1), (1, 4, 0.5), (1, 4, 1), (1, 4, 0.5), (1, 4, 1), (1, 4, -0.5), (1, 12, -1), (1, 4, -0.5), (1, 4, 0.5)]),
    -10.0: (3.5, [(1, 4, -1), (1, 4, 0), (1, 4, -0.5), (1, 4, 0.5), (1, 12, 1), (1, 4, 0.5), (1, 28, 1), (1, 4, 0.5), (1, 8, 1), (1, 4, 0.5), (1, 4, 1), (1, 4, 0.5), (1, 24, 1), (1, 4, 0.5), (1, 4, 1), (1, 4, -0.5), (1, 12, -1), (1, 4, 0.5), (1, 8, -0.5), (1, 4, 0.5), (1, 4, -0.5), (1, 32, -1), (1, 4, -0.5), (1, 4, 0.5), (1, 4, 1)]),
}
REPLAY_STEP = 1.0       # ft: the search's own step, so its paths replay exactly
SEARCH_GOAL = (148.0, 108.4)   # (s, t): on the shop lane east of the shop court, past the building's SE corner


def replay(p: Pose, tr: Truck, k_max: float, program) -> list[Pose]:
    """Drive a program of (direction, ft, wheel) moves."""
    out = [p]
    for direction, length, wheel in program:
        for _ in range(round(length / REPLAY_STEP)):
            p = step(p, tr, wheel * k_max, direction * REPLAY_STEP)
            out.append(p)
    return out


def outline_pts(poly: Polygon, every: float = 1.0) -> np.ndarray:
    ring = poly.exterior
    return np.array([ring.interpolate(d).coords[0] for d in np.arange(0, ring.length, every)])


def search_exit(start: Pose, tr: Truck, k_max: float, walls, trunks, lot: Polygon, margin: float, cap: int = 300000):
    """The shortest forward way from start onto the shop lane at SEARCH_GOAL, as a program, or None."""
    import heapq

    import shapely
    s0, t0, res = 110.0, -5.0, 0.5
    ns, nt = int((262.0 - s0) / res), int((165.0 - t0) / res)
    ss, tt = np.meshgrid(s0 + (np.arange(ns) + 0.5) * res, t0 + (np.arange(nt) + 0.5) * res)
    others = unary_union([Point(q).buffer(2.0) for q in trunks]).buffer(margin)
    grid = (shapely.contains_xy(walls.buffer(0.3 + 1.5), ss.ravel(), tt.ravel()) | shapely.contains_xy(others, ss.ravel(), tt.ravel())
            | ~shapely.contains_xy(lot.buffer(-margin), ss.ravel(), tt.ravel())).reshape(nt, ns)
    tp_, bp_ = outline_pts(truck_shape(tr)), outline_pts(boat_shape())

    def hits(p: Pose) -> bool:
        c, sn = math.cos(p.th), math.sin(p.th)
        ax, ay = p.axle(tr)
        c2, s2 = math.cos(p.psi), math.sin(p.psi)
        X = np.concatenate([p.x + tp_[:, 0] * c - tp_[:, 1] * sn, ax + bp_[:, 0] * c2 - bp_[:, 1] * s2])
        Y = np.concatenate([p.y + tp_[:, 0] * sn + tp_[:, 1] * c, ay + bp_[:, 0] * s2 + bp_[:, 1] * c2])
        i, j = ((Y - t0) / res).astype(int), ((-X - s0) / res).astype(int)
        if (i < 0).any() or (j < 0).any() or (i >= nt).any() or (j >= ns).any():
            return True
        return bool(grid[i, j].any())

    wrap = lambda a: (a + math.pi) % (2 * math.pi) - math.pi   # noqa: E731
    gx, gy = to_xy(SEARCH_GOAL)
    g_head = math.atan2(SHOP_LANE[5][1] - SHOP_LANE[6][1], -(SHOP_LANE[5][0] - SHOP_LANE[6][0]))
    key = lambda p: (round(p.x / 1.5), round(p.y / 1.5), round(wrap(p.th) / math.radians(10)), round(wrap(p.th - p.psi) / math.radians(10)))  # noqa: E731
    h = lambda p: math.hypot(p.x - gx, p.y - gy) + 8.0 * abs(wrap(p.th - g_head))  # noqa: E731
    if hits(start):
        return None
    nodes, best, openq, n_exp = {0: (start, None, None)}, {key(start): 0.0}, [(h(start), 0.0, 0)], 0
    while openq and n_exp < cap:
        _, g, i = heapq.heappop(openq)
        p = nodes[i][0]
        n_exp += 1
        if math.hypot(p.x - gx, p.y - gy) < 3.0 and abs(wrap(p.th - g_head)) < math.radians(12) and hitch_deg(p) < 12:
            prog, j = [], i
            while nodes[j][1] is not None:
                q, parent, wheel = nodes[j]
                if prog and prog[-1][2] == wheel:
                    prog[-1][1] += 4.0
                else:
                    prog.append([1, 4.0, wheel])
                j = parent
            return [tuple(m) for m in prog[::-1]]
        for wheel in (-1.0, -0.5, 0.0, 0.5, 1.0):
            q, ok = p, True
            for _ in range(4):
                q = step(q, tr, wheel * k_max, REPLAY_STEP)
                if abs(wrap(q.th - q.psi)) > math.radians(55) or hits(q):
                    ok = False
                    break
            if not ok or best.get(key(q), 1e18) <= g + 4.0:
                continue
            best[key(q)] = g + 4.0
            nodes[len(nodes)] = (q, i, wheel)
            heapq.heappush(openq, (g + 4.0 + 1.6 * h(q), g + 4.0, len(nodes) - 1))
    return None


def moves(tr: Truck, k_max: float, A, exit_program) -> list[Phase]:
    """Every move, in from the street and out again, as runs of poses."""
    on_line = lambda y: A(7.5, y)                              # noqa: E731   the boat bay's middle line, A's y
    (ls0, lt0), (ls1, lt1) = on_line(0.0), on_line(-1.0)
    u = (ls1 - ls0, lt1 - lt0)                                 # down the line, away from the door, in (s, t)
    head_out = math.atan2(u[1], -u[0])                         # heading straight out of the door, in X, Y
    off_line = lambda s_, t_: (s_ - ls0) * u[1] - (t_ - lt0) * u[0]   # noqa: E731

    # In: Candelaria southbound, right into the north entrance, the service drive's curl, a wide line across the north
    # court, the shop lane to its end, on across the shop court in the same line, and a left onto the door's line.
    # A driver with a trailer swings wide into a turn so the trailer doesn't cut the corner: out across the centerline
    # before turning in, and out to the far lane before turning north.
    road = [(-24.3, 178.0), (-24.3, 140.0), (-29.0, 118.0), (-25.0, 103.0), (-14.0, 97.0), (-3.0, 95.5), (9.0, 94.0)]
    court = [(55.0, 106.5), (63.0, 104.0), (71.0, 101.5), (80.0, 99.5)]
    (s1, t1), (s2, t2) = SHOP_LANE[-2], SHOP_LANE[-1]
    n = math.hypot(s2 - s1, t2 - t1)
    lane_dir = ((s2 - s1) / n, (t2 - t1) / n)
    h0 = math.atan2(lane_dir[1], -lane_dir[0])
    h1 = head_out + 2 * math.pi * (head_out < h0)
    R = R_PLAN + 2.0                                           # the driver aims a little wider than the planned lock

    def arc_from(d):
        """The left turn's centre and end, after d ft more in the lane's line."""
        x, y = to_xy((s2 + lane_dir[0] * d, t2 + lane_dir[1] * d))
        c = (x + R * math.cos(h0 + math.pi / 2), y + R * math.sin(h0 + math.pi / 2))
        return c, to_st((c[0] + R * math.cos(h1 - math.pi / 2), c[1] + R * math.sin(h1 - math.pi / 2)))

    lo, hi = -20.0, 80.0                                       # how far on before turning, so the turn ends on the line
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if off_line(*arc_from(mid)[1]) * off_line(*arc_from(lo)[1]) <= 0 else (mid, hi)
    c, end = arc_from(lo)
    arc = [to_st((c[0] + R * math.cos(a), c[1] + R * math.sin(a))) for a in np.linspace(h0 - math.pi / 2, h1 - math.pi / 2, 16)]
    line = [(end[0] + u[0] * k, end[1] + u[1] * k) for k in (15.0, 40.0, 80.0, 120.0)]
    ref = densify(road + SERVICE_DRIVE[1:5] + court + SHOP_LANE[1:] + arc + line, 8)

    def lined_up(p: Pose) -> bool:
        s_, t_ = to_st((p.x, p.y))
        return (t_ < end[1] - 2.0 and abs(math.degrees((p.th - head_out + math.pi) % (2 * math.pi) - math.pi)) < LINED_UP[0]
                and abs(off_line(s_, t_)) < LINED_UP[1] and hitch_deg(p) < LINED_UP[2])

    run = drive(Pose(*to_xy(road[0]), th=-math.pi / 2, psi=-math.pi / 2), tr, ref, k_max, stop=lined_up)
    i = next(k for k, p in enumerate(run) if to_st((p.x, p.y))[0] > SHOP_LANE[-1][0] - 3.0)
    lanes_in, turn = run[:i + 1], run[i:]
    turn = turn + straight(turn[-1], tr, PULL_EXTRA)[1:]

    # Back straight in until the coupler is 2 ft inside the door (the 3D plan's boat: 1 ft off the back wall). Backing,
    # a trailer runs off its line unless the driver keeps catching it, so this leg is the rig square on the line and
    # REVERSE_MARGIN stands for the corrections.
    p = turn[-1]
    park = to_xy(on_line(2.0))
    y0 = 2.0 - math.hypot(p.x - park[0], p.y - park[1])
    start, length = to_xy(on_line(y0)), (2.0 - tr.hitch) - y0
    ox, oy = math.cos(head_out), math.sin(head_out)
    back = [Pose(start[0] - ox * d, start[1] - oy * d, head_out, head_out, 0.0, p.d - d) for d in np.arange(0, length + 1e-6, STEP)]

    # Out: straight out until the stern clears the door, the sweep onto the shop lane, then the lane and the drive to
    # the street, and left onto Candelaria northbound.
    pull = straight(back[-1], tr, BOAT.tongue + BOAT.hull + BOAT.platform + STERN_CLEAR)
    way = replay(pull[-1], tr, k_max, exit_program or [])
    q = way[-1]
    q = Pose(q.x, q.y, q.th, q.psi, 0.0, q.d)   # coming onto the lane, the driver already has the wheel straight
    lead = [to_st((q.x + k * math.cos(q.th), q.y + k * math.sin(q.th))) for k in (0.0, 6.0)]
    lane_out = ([p for p in SHOP_LANE[::-1][:-1] if p[0] < lead[-1][0] - 8.0] + court[::-1] + SERVICE_DRIVE[4:0:-1]
                + [(9.0, 94.0), (-3.0, 95.5), (-17.0, 96.5), (-29.0, 101.0), (-33.8, 114.0), (-33.8, 178.0)])
    lanes_out = drive(q, tr, densify(lead + lane_out, 8), k_max)
    return [Phase("in: the street to the shop court", lanes_in, "in"),
            Phase("in: the left turn, lined up on the door", turn, "in"),
            Phase("in: straight back into the bay", back, "back", REVERSE_MARGIN),
            Phase("out: straight out, the stern clears the door", pull, "out"),
            Phase("out: the sweep onto the shop lane", way, "out"),
            Phase("out: the shop lane to the street", lanes_out, "out")]


def tag_ring(p, r: float, n: int = 36):
    return [(p[0] + r * math.cos(k / n * 2 * math.pi), p[1] + r * math.sin(k / n * 2 * math.pi)) for k in range(n + 1)]


def draw_panel(view_st, L, phases, tr, sf, to_m, tr_list, pipe, well, title: str, show) -> Plan:
    """One map: the aerial, the canopy, the drive as planned, and the chosen moves' sweeps, in (s, t) view bounds."""
    s0, t0, s1, t1 = view_st
    corners = [site([st(a, b)])[0] for a, b in ((s0, t0), (s0, t1), (s1, t1), (s1, t0))]
    xs, ys = [q[0] for q in corners], [q[1] for q in corners]
    plan = Plan(view=(int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1))
    plan.grid()
    S = lambda pts: site(st(*q) for q in pts)  # noqa: E731
    can = Canopy(CANOPY)
    for s_, t_, hh, r, c in canopy_in_st(can, to_m, sf):
        if s0 - 5 < s_ < s1 + 5 and t0 - 5 < t_ < t1 + 5:
            x, y = can.x0 + c, can.y0 + r
            q = [to_m.to_site(pt) for pt in ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))]
            plan.d.polygon([plan.p(*pt) for pt in q], fill=(255, 225, 60, 30))
    draw_survey(plan)

    def area(g, outline, fill, width=2, dash=False):
        layer = Image.new("RGBA", plan.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        polys = [g_ for g_ in getattr(g, "geoms", [g]) if not g_.is_empty and g_.geom_type == "Polygon"]
        for g_ in polys:
            if fill:
                d.polygon([plan.p(*q) for q in S(list(g_.exterior.coords)[:-1])], fill=fill)
                for hole in g_.interiors:
                    d.polygon([plan.p(*q) for q in S(list(hole.coords)[:-1])], fill=(0, 0, 0, 0))
        plan.img = Image.alpha_composite(plan.img.convert("RGBA"), layer).convert("RGB")
        plan.d = ImageDraw.Draw(plan.img, "RGBA")
        for g_ in polys:
            plan.line(S(list(g_.exterior.coords)), outline, width=width, dash=dash)

    area(L["drive"], (214, 190, 140), (222, 200, 150, 70), width=1)
    area(L["approach"], (200, 200, 195), (200, 200, 195, 150), width=1)
    area(L["building"], (90, 95, 100), (60, 65, 70, 220), width=3)
    A = L["A"]
    plan.line(S([A(1.5, 0), A(13.5, 0)]), ORANGE, width=6)
    for p, r, col in ((pipe, 10.0, RED), (well, 10.0, CYAN)):
        plan.line(S(tag_ring(p, r)), col, width=2, dash=True)
    colors = {"in": (110, 170, 255), "back": (90, 230, 255), "out": (255, 170, 60), "blocked": (255, 80, 80)}
    for ph in phases:
        if ph.name not in show:
            continue
        col = colors[ph.kind]
        if ph.kind == "blocked":
            area(ph.rig, col, (*col, 45), width=3, dash=True)
            continue
        area(ph.slop, col, (*col, 35), width=1, dash=True)
        area(ph.boat, col, (*col, 70), width=2)
        area(ph.truck, col, (*col, 50), width=2)
        plan.line(S([to_st((q.x, q.y)) for q in ph.poses[::4]]), WHITE, width=2)
    for t in tr_list:
        s_, t_ = t["st"]
        if not (s0 < s_ < s1 and t0 < t_ < t1):
            continue
        cx, cy = plan.p(*site([st(s_, t_)])[0])
        r = 8 if t["known"] else 6
        plan.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN if t["known"] else (60, 170, 60), outline=WHITE, width=2)
    plan.label(*site([st(s1 - 2, t1 - 3)])[0], title, size=20)
    return plan


KEEP = 10.0   # ft: building A stays this far off the surveyed north line, the well and the septic pipe


def place_a(sf: SurveyFrame, turn: float, pipe, well):
    """Building A's corners (NW, NE, SE, SW in (s, t)) turned `turn` degrees about its middle (positive turns it
    counter-clockwise seen from above, the doors toward the SE and the oaks; negative, toward the SW and the open
    lawn), then moved straight off the surveyed north line until KEEP clear of it, the well and the septic pipe.
    Returns the corners and how far it moved (ft)."""
    corners = [sf.from_site(p) for p in SITE_A]
    if turn == 0:
        return corners, 0.0
    lot = [sf.from_site(p) for p in PARCEL]
    north = LineString([lot[1], lot[2]])
    cs, ct = np.mean([c[0] for c in corners]), np.mean([c[1] for c in corners])
    a = math.radians(turn)
    turned = []
    for s_, t_ in corners:
        x, y = -(s_ - cs), t_ - ct
        turned.append((cs - (x * math.cos(a) - y * math.sin(a)), ct + x * math.sin(a) + y * math.cos(a)))
    d = np.array(lot[2]) - np.array(lot[1])
    off = np.array([d[1], -d[0]]) / np.linalg.norm(d)            # square off the line, into the lot
    for move in np.arange(0.0, 30.01, 0.25):
        c = [(q[0] + off[0] * move, q[1] + off[1] * move) for q in turned]
        g = Polygon(c)
        if g.distance(north) >= KEEP and g.distance(Point(well)) >= KEEP and g.distance(Point(pipe)) >= KEEP:
            return c, float(move)
    raise click.ClickException(f"building A turned {turn:g} degrees doesn't fit")


@click.command()
@click.option("--truck", type=click.Choice(sorted(TRUCKS)), default="half", show_default=True, help="The tow vehicle.")
@click.option("--radius", type=float, default=R_PLAN, show_default=True, help="The rear axle's radius on the tightest planned turn (ft).")
@click.option("--turn", type=float, default=0.0, show_default=True,
              help="Turn building A this many degrees about its middle (negative: the doors toward the SW), moved off the line as needed.")
@click.option("--search/--no-search", default=False, help="Search for the way out again instead of using the stored one (minutes).")
@click.option("--margin", type=float, default=None, help="With --search: ft kept off the trunks and the lot lines (default: the stored one's, or 2.5).")
def main(truck: str, radius: float, turn: float, search: bool, margin: float | None) -> None:
    """Map the ground a truck and a 22 ft boat sweep backing into building A and driving out again."""
    sf, to_m, ground = SurveyFrame(), Frame(), Terrain(TERRAIN)
    tr = TRUCKS[truck]
    pipe, _, well = field_features()
    pipe, well = sf.from_site(pipe), sf.from_site(well)
    corners, moved = place_a(sf, turn, pipe, well)
    L = layout(corners)
    A = L["A"]
    k_max = 1 / radius
    walls = unary_union([LineString([A(0, 0), A(1.5, 0)]), LineString([A(13.5, 0), A(30, 0), A(30, 30), A(0, 30), A(0, 0)])])
    house = L["house"]
    lot = Polygon([sf.from_site(p) for p in PARCEL])
    paved = unary_union([L["drive"], L["approach"], L["building"], box(ROAD[0], -100, 0.0, 400)])
    # Trees: the known trunks, and the lidar treetops that could be trunks. A treetop over the old drive, the street
    # or the roof is a crown reaching over it (its trunk stands off), so it counts overhead, not underfoot.
    old = unary_union([Polygon(EXISTING_DRIVE), Polygon(FRONT_WALK), box(ROAD[0] - 15, -100, ROAD[1], 400), house])
    tr_list = [t for t in trees(sf, to_m) if t["known"] or not old.contains(Point(t["st"]))]
    for t in tr_list:
        if not t["known"]:
            t["name"] = t["name"].replace("lidar treetop", "treetop") + " (trunk?)"
    stored = EXITS.get(turn) if truck == "half" and radius == R_PLAN else None
    if search or stored is None:
        margin = margin if margin is not None else (stored[0] if stored else 2.5)
        click.echo(f"Searching for the way out, {margin:g} ft off the trees and lot lines (a few minutes)...")
        probe = moves(tr, k_max, A, [])
        back_trunks = [t["st"] for t in tr_list if 100 < t["st"][0] < 260 and -10 < t["st"][1] < 165]
        program = search_exit(probe[3].poses[-1], tr, k_max, walls, back_trunks, lot, margin)
        if program:
            click.echo("found: " + repr([(d, round(ft), w) for d, ft, w in program]))
    else:
        margin, program = stored
    phases = moves(tr, k_max, A, program)
    for ph in phases:
        ph.swept(tr)
    can = Canopy(CANOPY)
    cells = [(Point(s_, t_), h) for s_, t_, h, r, c in canopy_in_st(can, to_m, sf) if -45 < s_ < 260 and -10 < t_ < 170]
    gz = lambda s_, t_: ground.natural(*to_m(site([st(s_, t_)])[0])) / FT  # noqa: E731
    cfg = dict(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, tbl_rows=-1, fmt_str_lengths=60, tbl_width_chars=230)

    click.echo(f"The rig: {tr.name}, {tr.wheelbase + tr.front + tr.rear:.1f} ft long; a 22 ft wake boat on a tandem trailer, "
               f"{BOAT.tongue + BOAT.hull + BOAT.platform:.0f} ft coupler to swim platform, {BOAT.beam} ft beam: "
               f"{tr.wheelbase + tr.front + tr.hitch + BOAT.tongue + BOAT.hull + BOAT.platform:.0f} ft bumper to stern.")
    click.echo(f"Full lock: the rear axle's radius ~{min_radius(tr):.1f} ft; planned at {radius:.0f} ft. The boat's bow meets the "
               f"tailgate at ~{jackknife_angle(tr):.0f} degrees between truck and trailer.")
    g = Polygon(corners)
    north = LineString([sf.from_site(PARCEL[1]), sf.from_site(PARCEL[2])])
    click.echo(f"Building A turned {turn:+g} degrees, moved {moved:.1f} ft off the line: {g.distance(north):.1f} ft from the line, "
               f"{g.distance(Point(well)):.1f} from the well, {g.distance(Point(pipe)):.1f} from the septic pipe.")

    rows, near_rows, room_rows = [], [], []
    for ph in phases:
        ks = [abs(q.k) for q in ph.poses]
        rows.append({"move": ph.name, "ft": round(sum(abs(b.d - a.d) for a, b in zip(ph.poses, ph.poses[1:]))),
                     "tightest R (ft)": round(1 / max(ks)) if max(ks) > 1e-6 else None,
                     "hitch max (deg)": round(max(hitch_deg(q) for q in ph.poses))})
        near = min((ph.rig.distance(Point(t["st"])), t["name"]) for t in tr_list)
        near_rows.append({"move": ph.name, "building": round(ph.rig.distance(walls), 1), "house": round(ph.rig.distance(house), 1),
                          "nearest tree (ft)": f"{near[0]:.1f}: {near[1]}", "septic pipe": round(ph.rig.distance(Point(pipe)), 1),
                          "well": round(ph.rig.distance(Point(well)), 1),
                          "lot line": round(ph.rig.distance(lot.exterior), 1) if lot.contains(ph.rig) else "the street"})
        crowns = [h for pt, h in cells if ph.boat.contains(pt)]
        room_rows.append({"move": ph.name,
                          "crowns over the boat": f"{len(crowns) * 10.76:.0f} sq ft, tops {min(crowns):.0f}-{max(crowns):.0f} ft" if crowns else "none",
                          "rig off the planned paving (sq ft)": round(ph.rig.difference(paved).intersection(lot).area),
                          "with the margin (sq ft)": round(ph.slop.difference(paved).intersection(lot).area)})
    click.echo("\nThe moves:")
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(rows))
    click.echo("\nClearances from the rig itself, ft (trees: known trunks, or lidar treetops, which are crowns' high points):")
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(near_rows))
    click.echo(f"\nOverhead and underfoot (the crowns are 2017 lidar tops; the limbs over the boat want {LIMB_CLEAR:.0f} ft or more; "
               f"the boat stands ~{BOAT_HEIGHT} ft):")
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(room_rows))
    spill = []
    for ph in (phases[0], phases[-1]):
        for g_ in getattr(ph.rig.difference(paved), "geoms", [ph.rig.difference(paved)]):
            if g_.area >= 15:
                c = g_.centroid
                spill.append({"move": ph.name, "where (s, t)": f"{c.x:.0f}, {c.y:.0f}", "sq ft": round(g_.area)})
    if spill:
        click.echo("\nWhere the rig runs off the drive as drawn (patches over 15 sq ft):")
        with pl.Config(**cfg):
            click.echo(pl.DataFrame(spill))

    # The numbers that matter.
    turn_in, back, way = phases[1], phases[2], phases[4]
    stop = turn_in.poses[-1]
    bumper = (stop.x + (tr.wheelbase + tr.front) * math.cos(stop.th), stop.y + (tr.wheelbase + tr.front) * math.sin(stop.th))
    out_ft = math.dist(to_st(bumper), A(7.5, 0.0))
    rig_len = tr.wheelbase + tr.front + tr.hitch + BOAT.tongue + BOAT.hull + BOAT.platform
    click.echo(f"\nIn: the rig is lined up and stopped with the truck's bumper {out_ft:.0f} ft out from the boat door "
               f"(the stern {out_ft - rig_len:.0f} ft out), then backs {abs(back.poses[-1].d - back.poses[0].d):.0f} ft straight in. "
               f"The 12 ft door leaves {(12 - BOAT.beam) / 2:.2f} ft each side of the boat.")
    if program:
        lane_line = LineString(catmull_rom(SHOP_LANE))
        q = way.poses[-1]
        click.echo(f"Out: the sweep is {sum(ft for _, ft, _ in program):.0f} ft, forward all the way, found keeping {margin:g} ft off the "
                   f"trunks and lot lines; it ends {lane_line.distance(Point(to_st((q.x, q.y)))):.1f} ft off the shop lane's middle.")
    else:
        click.echo("Out: no forward sweep onto the shop lane found at that margin.")
    lawn_in = unary_union([phases[1].slop, phases[2].slop]).difference(paved).intersection(lot)
    lawn_out = way.slop.difference(paved).intersection(lot)
    click.echo(f"The lawn the moves cross, margins included: {lawn_in.area:,.0f} sq ft in, {lawn_out.area:,.0f} sq ft out, "
               f"{lawn_in.union(lawn_out).area:,.0f} sq ft in all.")
    for name, ph in (("in", phases[1]), ("out", way)):
        pts = [to_st((q.x, q.y)) for q in ph.poses[::4]]
        z = [gz(*q) for q in pts]
        steep = max((abs(z[i] - z[i - 3]) / max(math.dist(pts[i], pts[i - 3]), 1e-6) for i in range(3, len(pts))), default=0)
        click.echo(f"Ground under the truck's rear axle, {name}: {z[-1] - z[0]:+.1f} ft end to end, {max(z) - min(z):.1f} ft high to low, "
                   f"steepest ~{100 * steep:.0f}% (2017 lidar).")

    # --- Maps ---
    tag = "" if turn == 0 else f"-turn{turn:+g}"
    out_back, out_all = OUT_BACK.with_name(f"tow-backyard{tag}.png"), OUT.with_name(f"tow-paths{tag}.png")
    back_view = (110.0, -8.0, 258.0, 160.0)
    names_in = [p.name for p in phases if p.kind in ("in", "back") and "street" not in p.name]
    names_out = [p.name for p in phases if p.kind == "out" and "street" not in p.name]
    head = f"building A turned {turn:+g} deg" if turn else "building A as planned"
    a = draw_panel(back_view, L, phases, tr, sf, to_m, tr_list, pipe, well, f"IN ({head}): left turn, line up, back straight in", names_in)
    out_title = (f"OUT: forward to the shop lane, {sum(ft for _, ft, _ in program):.0f} ft, {margin:g} ft off trees and lot lines"
                 if program else "OUT: no forward way to the shop lane found")
    b = draw_panel(back_view, L, phases, tr, sf, to_m, tr_list, pipe, well, out_title, names_out)
    img = Image.new("RGB", (a.img.width + b.img.width + 20, a.img.height), (30, 30, 30))
    img.paste(a.img, (0, 0))
    img.paste(b.img, (a.img.width + 20, 0))
    img.save(out_back)
    whole = draw_panel((-45.0, -8.0, 258.0, 175.0), L, phases, tr, sf, to_m, tr_list, pipe, well,
                       f"Towing a 22 ft boat to building A and out again ({head})", [p.name for p in phases])
    whole.scale_bar()
    whole.img.save(out_all)
    click.echo(f"\nwrote {out_back.relative_to(REPO)} {img.size} and {out_all.relative_to(REPO)} {whole.img.size}")


if __name__ == "__main__":
    main()
