"""US-290 beyond our north line, rough (owner, Nov 13 2026): the rebuilt highway's cross-section in site feet, shared
by plan3d.py (the 3D page) and fence_noise.py (traffic noise and sight lines).

The 2017 lidar predates the rebuilt highway, so it's drawn
from what we have: the eastbound frontage road's near edge off the base aerial (8400_candelaria_78737.png, +/-5 ft);
the owner's description (the main lanes drop below the eastbound frontage road, and the ground rises sharply to the
westbound one); and the upstairs photos, scaled by the 8 ft fence and the cars, which line up with this section: the
eastbound frontage road about level with our fence line, its barrier, the light strip of the far wall over it, the
grass bank above and the westbound frontage road's guardrail at about eye level from upstairs. The main lanes are
hidden from the house, so their depth is a guess. Straight and level along its length; +/-10 ft across, +/-4 ft in
height (the main lanes +/-6 ft).
"""

import math

HWY_EDGE = ((173.2, 52.7), (287.8, 36.0))   # site ft: two points on the eastbound frontage road's near edge, off the aerial
HWY_STATIONS = (-180.0, 480.0)             # ft along it from the first point (it closes on our line going west, so it must curve)
HWY_ROAD = 42.0                            # ft of each frontage road (three lanes and shoulders)
HWY_BARRIER = (42.0, 44.0, 2.7)            # the eastbound frontage road's barrier: from, to (ft out), height (ft)
HWY_CUT = 62.0                             # ft out: the foot of the slope down from the barrier, where the main lanes start
HWY_MAIN = 100.0                           # ft of main lanes, in the cut
HWY_WALL = 12.0                            # ft: the concrete wall at the far side of the main lanes
HWY_BANK = 33.0                            # ft: the grass bank's run from the wall's top up to the westbound frontage road
HWY_Z = (1058.0, 1046.0, 1074.5)           # ft NAVD88: the eastbound frontage road, the main lanes, the westbound one
HWY_POLES = (-54.0, (-180.0, -30.0, 43.8, 194.0, 344.0, 494.0))   # wood poles: ft out, stations (one on the aerial at
                                                                    # 43.8, one by the NW in the photos at ~-30; ~150 ft apart)


def hwy_frame():
    """(site point of (station, offset)), (station, offset of a site point): the highway's frame, offsets away from our lot."""
    (ax, ay), (bx, by) = HWY_EDGE
    n = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / n, (by - ay) / n
    mx, my = uy, -ux
    return (lambda s_, o: (ax + ux * s_ + mx * o, ay + uy * s_ + my * o),
            lambda p: ((p[0] - ax) * ux + (p[1] - ay) * uy, (p[0] - ax) * mx + (p[1] - ay) * my))


def hwy_offsets() -> dict:
    """The cross-section's breaks, ft out from the eastbound frontage road's near edge."""
    main1 = HWY_CUT + HWY_MAIN
    return {"barrier": HWY_BARRIER[1], "cut": HWY_CUT, "wall": main1, "wb": main1 + HWY_BANK, "wb_end": main1 + HWY_BANK + HWY_ROAD}


def hwy_profile(o: float) -> float:
    """The rebuilt cross-section's ground (ft NAVD88) at o ft out from the eastbound frontage road's near edge."""
    zr, zm, zw = HWY_Z
    k = hwy_offsets()
    if o <= k["barrier"]:
        return zr
    if o <= k["cut"]:
        return zr + (o - k["barrier"]) / (k["cut"] - k["barrier"]) * (zm - zr)
    if o <= k["wall"]:
        return zm
    if o <= k["wb"]:
        return zm + HWY_WALL + (o - k["wall"]) / HWY_BANK * (zw - zm - HWY_WALL)
    return zw
