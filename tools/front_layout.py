"""Front-yard layout: the shapes the front-yard study and the 3D plan share.

Survey-local (s, t) feet: s back from the front line along the south line, t from the south
line toward US-290 (see site_plan.st). No heavy imports, so both front_plan.py and plan3d.py
can use it.
"""

import math

# Owner's sketch, read off the plat (+/-3 ft).
SKETCH_BOX = [(28, 39), (61, 39), (61, 66), (28, 66)]
SKETCH_OUTER = [(0, 9), (36, 21), (48.5, 36.7), (51, 55), (45.6, 78), (34, 91), (0, 96)]
SKETCH_INNER = [(0, 30), (25, 38), (27.6, 55), (23, 76), (8, 91)]

# Option A: porte-cochere between the 45' line and the house/porch front, two cars nose-to-tail.
PORTE_COCHERE = [(45, 32), (57, 32), (57, 76), (45, 76)]
# Option B: carport on the old garage apron (north side), reached from the existing driveway,
# with the existing covered porch as the covered walk to the front door.
NORTH_CARPORT = [(62, 91), (86, 91), (86, 114), (62, 114)]
# 1991 plat: electric line from the front-south pin to the house's SE corner.
FRONT_ELECTRIC = [(0, 0), (59.3, 22.7)]

# The existing concrete drive and the front walk, traced from the 1991 survey plat (private repo,
# property/CUR-Survey-8400-Candelaria.pdf; the plat gives no drive dimensions). The scan was fitted
# with an affine transform to five points: both front pins, the porch's front-north corner, and the
# house's NW and front-south corners (residuals 0.8-2.3 ft), so the outline is good to about +/-3 ft.
# Negative s is the approach in the street right-of-way, out to the asphalt.
# Drive: up the south edge from the street, around the lawn bulge in front of the porch to the
# porch's front-north corner, along the house's north side to the apron's back edge (in line with
# the garage's back wall), then down the north edge to the street.
EXISTING_DRIVE = [
    (-16.0, 85.0), (-8.0, 88.0), (5.5, 89.5), (17.0, 90.0), (29.5, 91.0), (31.5, 96.5), (38.0, 101.0),
    (45.5, 103.5), (51.5, 103.0), (56.5, 99.5), (59.0, 94.0), (59.0, 90.0), (64.0, 90.0), (81.5, 90.0),
    (84.0, 93.5), (85.0, 93.5), (84.0, 121.5), (78.5, 124.0), (71.5, 119.5), (57.5, 117.5), (42.5, 113.5),
    (30.0, 110.0), (16.5, 104.0), (3.5, 102.5), (-9.0, 102.5), (-16.5, 106.5),
]
# Walk: ~3 ft wide, from the front door's recess (house front at t 50.4-57.6) to the street, flared at both ends.
FRONT_WALK = [
    (56.0, 50.0), (53.0, 51.5), (41.0, 51.5), (20.0, 51.0), (-1.0, 51.0), (-9.5, 51.0), (-15.0, 49.0),
    (-15.0, 56.0), (-11.5, 54.0), (-1.0, 54.0), (20.0, 54.0), (41.0, 54.5), (53.0, 54.5), (55.5, 56.5),
]
EXISTING_DRIVE_T = 95.5  # ft: middle of the existing drive's straight run at the front line (plat)

# Loop C (proposal): a new curb cut in the open south lawn, a 12 ft lane that sweeps to the
# house and runs along the porch front (drop-off at the porch), then crosses the plat's lawn
# bulge in front of the porch's north end to join the existing drive. Centerline, (s, t) ft.
LOOP_C = [(-1, 33), (12, 34), (26, 36.5), (37, 41), (44, 48), (48, 57), (48, 68), (49, 78), (50, 89),
          (49, 99), (47, 108)]
LANE = 12.0  # ft
LONE_OAK_BOX = ((-5.0, 30.0), (44.0, 86.0))  # (s range, t range) holding the lone lawn oak's crown
ASSUMED_DBH_IN = 20.0  # in; not measured. Root zone = 1 ft radius per inch.


def catmull_rom(pts, n: int = 12):
    """Smooth polyline through the given points."""
    out = []
    ext = [pts[0], *pts, pts[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            u = k / n
            out.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u**2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u**3)
                for j in range(2)
            ))
    out.append(pts[-1])
    return out


def offset(pts, d: float):
    """Polyline shifted d ft to its left (in s, t)."""
    out = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        out.append((p[0] - dy / L * d, p[1] + dx / L * d))
    return out



def loop_c_outline() -> list[tuple[float, float]]:
    """Loop C as a closed outline (s, t): the lane's left edge out, the right edge back."""
    center = catmull_rom(LOOP_C)
    return offset(center, LANE / 2) + offset(center, -LANE / 2)[::-1]
