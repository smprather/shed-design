# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Whole-lot overview: the 1991 survey over the aerial, with plat dimensions,
easements, building line, well and electric lines.

Same lot-aligned foot grid as site_plan.py.

Run: uv run tools/lot_plan.py
"""

from site_plan import (
    CYAN, ELECTRIC_1991, MAGENTA, ORANGE, PARCEL, PURPLE, RED, REPO, WELL, YELLOW,
    Plan, draw_survey, en_to_site, site,
)

OUT = REPO / "site" / "lot.png"
VIEW = (45, 85, 340, 285)

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

    for outline in REMOVED:
        plan.poly(outline, (200, 200, 200), width=2, dash=True)
    plan.label(163, 137, "old carport\n(removed)", fill=ORANGE, size=18)
    plan.label(70, 150, "sheds\n(removed)", fill=(220, 220, 220), size=16)

    plan.line(site(ELECTRIC_1991), YELLOW, width=2, dash=True)
    draw_survey(plan)
    plan.line([(100, 116.1), (183, 128)], RED, width=3)
    plan.line([(183, 128), (232, 135.6)], RED, width=3, dash=True)

    plan.label(198, 222, "HOUSE", fill=(160, 210, 255), size=28)
    plan.label(221, 178, "garage", fill=(160, 210, 255), size=18)
    plan.label(292, 186, "driveway", size=16)
    well = en_to_site(WELL)
    plan.label(well[0] + 2.5, well[1] - 1, "well (1991 plat) - still there?", fill=CYAN, size=18)
    plan.label(72, 233, "1991 electric service - current route? (call 811 before digging)", fill=YELLOW, size=16)
    plan.label(48, 186, "7.5' + 10'\nutility\neasement\n(overhead\nline now\nremoved)", fill=PURPLE, size=16)
    plan.label(47, 150, "west:\ncleared for\napartments\n+ retail", fill=(255, 200, 120), size=16)
    plan.label(265, 238, "45' building\nline (plat)", fill=PURPLE, size=16)

    plan.label(80, 200, "back yard:\nseptic + big oak somewhere here\n(to be located)", fill=MAGENTA, size=22)

    plan.label(150, 93, "N50°46'W 253.50' along US-290 (fence ~3-6 ft inside?)", fill=PURPLE, size=22)
    plan.label(311, 196, "N30°05'E\n114.95'\nfrontage", fill=PURPLE, size=20)
    plan.label(150, 264, "N59°52'W 250.05'  (neighbor to the south)", fill=PURPLE, size=22)
    plan.label(47, 108, "N30°00'E\n155.05'\nback", fill=PURPLE, size=18)

    area = shoelace(PARCEL)
    plan.label(
        47, 276,
        f"Lot 176 Granada Hills Amd, from the Apr 1991 survey: {area:,.0f} sq ft by bearings (CAD lists 34,036). "
        "Placed on the aerial by the house, +/-3 ft. Up = NNE, right = ESE.",
        size=16,
    )
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}; survey area {area:,.0f} sq ft")


if __name__ == "__main__":
    main()
