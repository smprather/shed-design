# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Field-measurement key map: house reference corners A/B/C and numbered shots.

Same lot-aligned foot grid as site_plan.py. Numbers on the map match the table
in site/measurements.md. A, B and C are wall corners from the 1991 survey; the
septic system and the large oak are unknown, so they are only flagged.

Run: uv run tools/measure_plan.py
"""

import math

from PIL import ImageFont
from site_plan import (
    BLUE, CYAN, GREEN, HOUSE, MAGENTA, ORANGE, RED, REPO, WELL, YELLOW,
    Plan, draw_survey, en_to_site, north_line_y,
)

OUT = REPO / "site" / "measure-plan.png"
VIEW = (55, 100, 275, 250)

A, B, C = HOUSE[4], HOUSE[5], HOUSE[3]  # NW corner, NE corner (garage), wing's SW corner


def fence_y(x: float) -> float:
    """Fence as traced on the aerial."""
    return 116.8 + (x - 105) * (11.2 / 78) if x <= 183 else 128 + (x - 183) * (5 / 32)


F1, F2, F3 = (A[0], fence_y(A[0])), (B[0], fence_y(B[0])), (90, fence_y(90))
PAD = [(161, 129), (205, 129), (205, 150), (161, 150)]
# Removed since the aerial was taken; outlined so the photo still makes sense.
REMOVED = [
    [(83, 133), (99, 133), (99, 144), (83, 144)],
    [(74, 167), (96, 167), (96, 181), (74, 181)],
]


def marker(plan: Plan, pt, text: str, fill, r: int = 16) -> None:
    x, y = plan.p(*pt)
    plan.d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=(0, 0, 0), width=2)
    font = ImageFont.load_default(size=24)
    plan.d.text((x, y), text, fill=(0, 0, 0), font=font, anchor="mm")


def shot(plan: Plan, a, b, num: str, at, fill=YELLOW, dash: bool = False) -> None:
    plan.line([a, b], fill, width=4, dash=dash)
    x, y = plan.p(*b)
    plan.d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=fill)
    plan.label(*at, num, fill=fill, size=24)


def main() -> None:
    plan = Plan(view=VIEW)
    plan.grid()

    draw_survey(plan)
    plan.line([(100, 116.1), (183, 128)], RED, width=4)
    plan.line([(183, 128), (232, 135.6)], RED, width=4, dash=True)
    plan.poly(PAD, ORANGE, width=4)
    plan.label(170, 137, "old pad", fill=(255, 190, 110), size=20)
    for outline in REMOVED:
        plan.poly(outline, (200, 200, 200), width=2, dash=True)
    plan.label(84, 145, "removed", fill=(200, 200, 200), size=16)
    plan.label(75, 182, "removed", fill=(200, 200, 200), size=16)
    plan.label(222, 180, "garage", fill=(160, 210, 255), size=18)

    # 1-2 baseline along the house walls (calibration against the survey).
    plan.label(208, 172, "1", fill=BLUE, size=24)
    plan.label(183, 178, "2", fill=BLUE, size=24)

    # 3-4 square off the north wall to the fence -> tape marks F1, F2.
    shot(plan, A, F1, "3", at=(183, 140))
    shot(plan, B, F2, "4", at=(242.5, 150))
    plan.label(172, 120.5, "F1", fill=(255, 150, 150), size=20)
    plan.label(242, 128, "F2", fill=(255, 150, 150), size=20)

    # 5-6 far-west fence mark F3, tied to A and to F1.
    shot(plan, A, F3, "5", at=(118, 136), dash=True)
    shot(plan, F1, F3, "6", at=(132, 113.5))
    plan.label(84, 105, "F3", fill=(255, 150, 150), size=20)

    # 7-8 old pad corners from A and B (bucket on each corner).
    shot(plan, A, PAD[3], "7", at=(166, 156), dash=True)
    shot(plan, B, PAD[2], "8", at=(213, 156), dash=True)

    # 19 the well on the 1991 plat, if it is still there.
    well = en_to_site(WELL)
    plan.label(well[0] + 2.5, well[1] + 1.5, "19 well?", fill=CYAN, size=20)

    # Unknowns: large oak, septic, east oaks, drive.
    plan.label(118, 172, "9-12  BIG OAK?\ntrunk from A + C,\ngirth, drip line", fill=MAGENTA, size=22)
    plan.label(92, 205, "13-14  SEPTIC?\nbucket on each lid / field corner\nmeasure from A + C", fill=MAGENTA, size=22)
    plan.label(250, 128, "15  east oak\ntrunks", fill=GREEN, size=20)
    plan.label(252, 160, "16 drive gap\n17 branches", size=20)

    marker(plan, A, "A", BLUE)
    marker(plan, B, "B", BLUE)
    marker(plan, C, "C", BLUE)

    plan.label(57, 240, "Lettered = fixed points (surveyed wall corners). Numbered = shots (site/measurements.md). Grid = 10 ft.", size=18)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")
    est = {
        "1 A-B": math.dist(A, B), "2 A-C": math.dist(A, C),
        "3 A-fence (aerial)": A[1] - F1[1], "3 A-line (survey, vertical)": A[1] - north_line_y(A[0]),
        "4 B-fence (aerial)": B[1] - F2[1], "5 A-F3": math.dist(A, F3), "6 F1-F3": math.dist(F1, F3),
        "7 A-pad SW": math.dist(A, PAD[3]), "8 B-pad SE": math.dist(B, PAD[2]),
        "19 A-well": math.dist(A, well), "19 F1-well": math.dist(F1, well),
    }
    for k, v in est.items():
        print(f"  {k}: {v:.1f}")


if __name__ == "__main__":
    main()
