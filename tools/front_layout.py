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

# Loop C (proposal): a new curb cut in the open south lawn, a 12 ft lane that sweeps to the
# house and runs along the porch front (drop-off at the porch), then joins the existing drive
# where it flares to the porch's north end. Centerline, (s, t) ft.
LOOP_C = [(-1, 33), (12, 34), (26, 36.5), (37, 41), (44, 48), (48, 57), (48, 68), (49, 78), (52, 86)]
LANE = 12.0  # ft
EXISTING_DRIVE_T = 86.0  # ft: middle of the existing curb cut (aerial, +/-4 ft)
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
