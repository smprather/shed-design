# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Field-measurement key map: house reference corners A/B/C and numbered shots.

Same lot-aligned foot grid as site_plan.py. Numbers on the map match the table
in site/measurements.md; positions of the septic system and the large oak are
unknown, so they are only flagged.

Run: uv run tools/measure_plan.py
"""

from site_plan import BLUE, GARAGE, GREEN, MAGENTA, ORANGE, PARCEL, PURPLE, RED, REPO, WHITE, YELLOW, Plan
from PIL import ImageFont

OUT = REPO / "site" / "measure-plan.png"
VIEW = (55, 100, 275, 250)

# Roofline estimates from the aerial (walls sit ~1-2 ft inside these).
A, B, C = (180, 168), (224, 168), (180, 196)
F1, F2, F3 = (180, 127.6), (224, 134.4), (90, 114.7)
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

    # Context: fence, house, old pad, removed sheds.
    plan.poly(PARCEL, PURPLE, width=3, dash=True)
    plan.line([(100, 116.1), (183, 128)], RED, width=4)
    plan.line([(183, 128), (232, 135.6)], RED, width=4, dash=True)
    plan.poly([A, B, (224, 196), C], BLUE, width=3)
    plan.line([(224, 171), (252, 171), (252, 230)], BLUE, width=3)
    plan.poly(GARAGE, BLUE, fill=(120, 190, 255, 70), width=3)
    plan.label(232, 185, "garage", fill=(160, 210, 255), size=18)
    plan.poly(PAD, ORANGE, width=4)
    plan.label(170, 137, "old pad", fill=(255, 190, 110), size=20)
    for outline in REMOVED:
        plan.poly(outline, (200, 200, 200), width=2, dash=True)
    plan.label(84, 145, "removed", fill=(200, 200, 200), size=16)
    plan.label(75, 182, "removed", fill=(200, 200, 200), size=16)

    # 1-2 baseline along the house walls (calibration).
    plan.label(199, 172, "1", fill=BLUE, size=24)
    plan.label(182.5, 179, "2", fill=BLUE, size=24)

    # 3-4 square off the north wall to the fence -> tape marks F1, F2.
    shot(plan, A, F1, "3", at=(181.5, 140))
    shot(plan, B, F2, "4", at=(225.5, 144))
    plan.label(172, 121.5, "F1", fill=(255, 150, 150), size=20)
    plan.label(226, 129, "F2", fill=(255, 150, 150), size=20)

    # 5-6 far-west fence mark F3, tied to A and to F1.
    shot(plan, A, F3, "5", at=(118, 136), dash=True)
    shot(plan, F1, F3, "6", at=(132, 114))
    plan.label(84, 107, "F3", fill=(255, 150, 150), size=20)

    # 7-8 old pad corners from A and B (bucket on each corner).
    shot(plan, A, PAD[3], "7", at=(166, 156), dash=True)
    shot(plan, B, PAD[2], "8", at=(212, 154), dash=True)

    # Unknowns: large oak, septic, east oaks, drive.
    plan.label(118, 172, "9-12  BIG OAK?\ntrunk from A + C,\ngirth, drip line", fill=MAGENTA, size=22)
    plan.label(92, 205, "13-14  SEPTIC?\nbucket on each lid / field corner\nmeasure from A + C", fill=MAGENTA, size=22)
    plan.label(232, 140, "15  east oak trunks\nfrom B (+A), girth", fill=GREEN, size=20)
    plan.label(240, 160, "16  drive: narrowest gap\n17  lowest branches (aim up)", fill=WHITE, size=20)

    marker(plan, A, "A", BLUE)
    marker(plan, B, "B", BLUE)
    marker(plan, C, "C", BLUE)

    plan.label(57, 240, "Lettered = fixed points. Numbered = shots (see site/measurements.md). Grid = 10 ft.", size=18)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
