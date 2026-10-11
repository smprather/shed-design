# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Site B close-up: the chosen 23 x 43 metal building and its clearances.

Shows the footprint (the earlier 20 x 40 dashed), the north wall that stays free of openings,
where doors go, the sound shadow toward the house, the septic truck's parking spot and hose run, and the
distances that set the footprint. Same lot-aligned foot grid as site_plan.py.

Run: uv run tools/site_b_plan.py
"""

import json
import math

from site_plan import (
    BLUE, CYAN, GREEN, HOUSE, MAGENTA, PARCEL, RED, REPO, SITE_B, WHITE, YELLOW,
    Plan, draw_field, draw_survey,
)

OUT = REPO / "site" / "site-b.png"
VIEW = (118, 98, 258, 184)

B = SITE_B
(BX0, BY0), (BX1, BY1) = B[0], B[2]
B_OLD = [(152, 131.5), (192, 131.5), (192, 151.5), (152, 151.5)]  # 20 x 40, superseded Oct 11 2026
TRUCK = [(186, 158), (212, 158), (212, 166), (186, 166)]  # pump truck, centered in the lane
HOSE = [(186, 162), (147, 158), (144, 140)]  # then to the septic pipe
WALL_RED = (200, 60, 50)
DRIP = 25.1  # oak drip line from the near trunk (site_plan.draw_field)


def north_line_y(x: float) -> float:
    (x0, y0), (x1, y1) = PARCEL[2], PARCEL[1]
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def house_north_y(x: float) -> float:
    (x0, y0), (x1, y1) = HOUSE[4], HOUSE[5]
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def main() -> None:
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    pipe = tuple(fp["white_pipe"]["solutions"][0]["site"])
    oak = tuple(fp["big_oak"]["solutions"][0]["site"])

    (lx0, ly0), (lx1, ly1) = PARCEL[2], PARCEL[1]
    cos_line = (lx1 - lx0) / math.dist((lx0, ly0), (lx1, ly1))
    to_line = (BY0 - north_line_y(BX1)) * cos_line  # NE corner, square to the line
    to_pipe = math.dist(pipe, B[0])
    to_trunk = oak[0] - BX1
    to_house = house_north_y(185) - BY1

    plan = Plan(view=VIEW)
    plan.grid()

    # Sound shadow: the quieter area behind the building, toward the house.
    plan.d.polygon([plan.p(BX0 - 2, BY1), plan.p(BX1 + 2, BY1), plan.p(BX1 + 6, 169.5), plan.p(BX0 - 6, 169.5)],
                   fill=(120, 190, 255, 45))
    draw_survey(plan)
    draw_field(plan)

    # 5 ft setback from the surveyed line.
    plan.line([(120, north_line_y(120) + 5 / cos_line), (256, north_line_y(256) + 5 / cos_line)],
              RED, width=2, dash=True)

    plan.poly(B_OLD, YELLOW, width=2, dash=True)
    plan.poly(B, YELLOW, fill=(255, 220, 60, 95), width=4)
    plan.line([B[0], B[1]], WALL_RED, width=8)  # north wall of the building itself: no openings (noise)
    for x0 in (156, 174):  # suggested roll-up doors on the south side
        plan.line([(x0, BY1), (x0 + 12, BY1)], WHITE, width=10)

    # 10 ft keep-out around the septic access pipe.
    x0, y0 = plan.p(pipe[0] - 10, pipe[1] - 10)
    x1, y1 = plan.p(pipe[0] + 10, pipe[1] + 10)
    plan.d.ellipse([x0, y0, x1, y1], outline=MAGENTA, width=3)

    hose = HOSE + [pipe]
    plan.poly(TRUCK, (230, 230, 230), fill=(230, 230, 230, 120), width=2)
    plan.line(hose, CYAN, width=3, dash=True)

    # Distances that set the footprint.
    plan.dim((BX1, BY0), (BX1, north_line_y(BX1)), f"{to_line:.1f} ft to\nsurveyed line", at=(178.5, 119.5))
    plan.dim(B[0], pipe, f"{to_pipe:.0f} ft", at=(143.5, 131))
    plan.dim((BX1, oak[1]), oak, f"{to_trunk:.1f} ft to trunk\n(drip line {DRIP})", at=(196, 145.5))
    plan.dim((185, BY1), (185, house_north_y(185)), f"{to_house:.0f} ft", at=(179, 160))

    plan.label(158, 139.5, "B  23 x 43 ft\nmetal building, slab", fill=(255, 235, 140), size=26)
    plan.label(152, 125.4, "north wall: no doors, windows or vents", fill=(255, 150, 140), size=18)
    plan.label(156, 151.2, "roll-up doors on this side", fill=WHITE, size=16)
    plan.label(193.5, 152.3, "dashed: earlier 20 x 40", fill=(255, 235, 140), size=15)
    plan.label(186.5, 167, "septic truck parks here", fill=(230, 230, 230), size=15)
    hose_ft = sum(math.dist(a, b) for a, b in zip(hose, hose[1:]))
    plan.label(121, 146, f"hose ~{5 * round(hose_ft / 5):.0f} ft\naround the west end", fill=CYAN, size=15)
    plan.label(146, 171, "quietest: the yard right behind\nthe building (~7 dB)", fill=BLUE, size=16)
    plan.label(120, 100, "Site B, 23 x 43 ft (Oct 11 2026). Grid = 10 ft. Up = NNE (toward US-290).", size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")
    print(f"  NE corner to the line {to_line:.1f} ft; pipe to B {to_pipe:.1f} ft; east wall to trunk "
          f"{to_trunk:.1f} ft (drip line {DRIP}); B to house {to_house:.1f} ft; hose run {hose_ft:.0f} ft")


if __name__ == "__main__":
    main()
