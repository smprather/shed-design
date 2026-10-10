# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Whole-lot overview: the CAD property line over the aerial, with side lengths.

Same lot-aligned foot grid as site_plan.py.

Run: uv run tools/lot_plan.py
"""

import math

from site_plan import BLUE, MAGENTA, ORANGE, PARCEL, PURPLE, RED, REPO, WHITE, Plan

OUT = REPO / "site" / "lot.png"
VIEW = (45, 85, 340, 285)

HOUSE = [(180, 168), (224, 168), (224, 171), (252, 171), (252, 239), (189, 239), (189, 196), (180, 196)]
REMOVED = [
    [(161, 129), (205, 129), (205, 150), (161, 150)],  # teal carport canopies
    [(83, 133), (99, 133), (99, 144), (83, 144)],  # small shed
    [(74, 167), (96, 167), (96, 181), (74, 181)],  # larger shed
]


def shoelace(pts) -> float:
    return 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])))


def main() -> None:
    plan = Plan(view=VIEW)
    plan.grid()

    nw, ne, se, sw, jog = PARCEL
    plan.poly(PARCEL, PURPLE, width=6)

    plan.line([(100, 116.1), (183, 128)], RED, width=4)
    plan.line([(183, 128), (232, 135.6)], RED, width=4, dash=True)

    for outline in REMOVED:
        plan.poly(outline, (200, 200, 200), width=2, dash=True)
    plan.label(163, 137, "old carport\n(removed)", fill=ORANGE, size=18)
    plan.label(70, 150, "sheds\n(removed)", fill=(220, 220, 220), size=16)

    plan.poly(HOUSE, BLUE, width=4)
    plan.label(200, 205, "HOUSE", fill=(160, 210, 255), size=28)
    plan.label(292, 186, "driveway", size=16)

    plan.label(80, 205, "back yard:\nseptic + big oak somewhere here\n(to be located)", fill=MAGENTA, size=22)

    north = math.dist(nw, ne)
    west = math.dist(sw, jog) + math.dist(jog, nw)
    plan.label(150, 96, f"~{north:.0f} ft along US-290 (fence ~ on the line)", fill=PURPLE, size=22)
    plan.label(316, 200, f"~{math.dist(ne, se):.0f} ft\nfrontage", fill=PURPLE, size=22)
    plan.label(160, 268, f"~{math.dist(se, sw):.0f} ft  (neighbor to the south)", fill=PURPLE, size=22)
    plan.label(47, 255, f"~{west:.0f} ft\nwest", fill=PURPLE, size=20)

    area = shoelace(PARCEL)
    plan.label(
        47, 87,
        f"Lot 176 Granada Hills Amd: CAD 34,036 sq ft (outline here {area:,.0f}). "
        "Line from the CAD map, +/-5 ft. Up = NNE, right = ESE.",
        size=16,
    )
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}; outline area {area:,.0f} sq ft")


if __name__ == "__main__":
    main()
