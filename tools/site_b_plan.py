# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Site B close-up: the chosen 20 x 40 metal building and its clearances.

Shows the footprint (24 x 40 dashed), the solid highway-side wall, where doors go, the
sound shadow toward the house, the septic truck's parking spot and hose run, and the
distances that set the footprint. Same lot-aligned foot grid as site_plan.py.

Run: uv run tools/site_b_plan.py
"""

import json
import math

from site_plan import (
    BLUE, CYAN, GREEN, HOUSE, MAGENTA, PARCEL, RED, REPO, WHITE, YELLOW,
    Plan, draw_field, draw_survey,
)

OUT = REPO / "site" / "site-b.png"
VIEW = (118, 98, 258, 184)

B = [(152, 131.5), (192, 131.5), (192, 151.5), (152, 151.5)]
B_DEEP = [(152, 131.5), (192, 131.5), (192, 155.5), (152, 155.5)]
TRUCK = [(186, 156.5), (212, 156.5), (212, 164.5), (186, 164.5)]  # pump truck in the lane
HOSE = [(186, 160.5), (150, 157), (143, 138), (141.7, 127.5)]
WALL_RED = (200, 60, 50)


def north_line_y(x: float) -> float:
    (x0, y0), (x1, y1) = PARCEL[2], PARCEL[1]
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def main() -> None:
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    pipe = tuple(fp["white_pipe"]["solutions"][0]["site"])
    oak = tuple(fp["big_oak"]["solutions"][0]["site"])

    plan = Plan(view=VIEW)
    plan.grid()

    # Sound shadow: the quieter area behind the building, toward the house.
    plan.d.polygon([plan.p(150, 151.5), plan.p(194, 151.5), plan.p(198, 169.5), plan.p(146, 169.5)],
                   fill=(120, 190, 255, 45))
    draw_survey(plan)
    draw_field(plan)

    # 5 ft setback from the surveyed line.
    plan.line([(120, north_line_y(120) + 5.08), (256, north_line_y(256) + 5.08)], RED, width=2, dash=True)

    plan.poly(B_DEEP, YELLOW, width=2, dash=True)
    plan.poly(B, YELLOW, fill=(255, 220, 60, 95), width=4)
    for x_end in (195, 197):  # east end stretched 3 or 5 ft toward the oak
        plan.line([(192, 131.5), (x_end, 131.5), (x_end, 151.5), (192, 151.5)], YELLOW, width=2, dash=True)
    plan.line([B[0], B[1]], WALL_RED, width=12)  # solid highway-side wall
    for x0 in (158, 174):  # suggested roll-up doors on the south side
        plan.line([(x0, 151.5), (x0 + 12, 151.5)], WHITE, width=10)

    # 10 ft keep-out around the septic access pipe.
    x0, y0 = plan.p(pipe[0] - 10, pipe[1] - 10)
    x1, y1 = plan.p(pipe[0] + 10, pipe[1] + 10)
    plan.d.ellipse([x0, y0, x1, y1], outline=MAGENTA, width=3)

    plan.poly(TRUCK, (230, 230, 230), fill=(230, 230, 230, 120), width=2)
    plan.line(HOSE, CYAN, width=3, dash=True)

    # Distances that set the footprint.
    plan.dim((190, 131.5), (190, north_line_y(190)), "5.3 ft to\nsurveyed line", at=(176, 119.5))
    plan.dim((152, 131.5), pipe, "12 ft", at=(145.5, 131))
    plan.dim((192, 144.1), (oak[0], oak[1]), "25.5 ft to trunk\n(drip line 25.1)", at=(196, 145.5))
    plan.dim((172, 151.5), (172, 169.5), "18 ft", at=(166, 159))

    plan.label(160, 139, "B  20 x 40 ft\nmetal building, slab", fill=(255, 235, 140), size=26)
    plan.label(153, 125.4, "solid wall to US-290: insulated, no openings", fill=(255, 150, 140), size=18)
    plan.label(156, 148.2, "roll-up doors on this side", fill=WHITE, size=16)
    plan.label(152.5, 156.7, "dashed: 24 x 40 if the trees allow", fill=(255, 235, 140), size=15)
    plan.label(193.5, 152.3, "+3 / +5 ft", fill=(255, 235, 140), size=15)
    plan.label(186.5, 165.5, "septic truck parks here", fill=(230, 230, 230), size=15)
    plan.label(121, 146, "hose ~65-70 ft\naround the west end", fill=CYAN, size=15)
    plan.label(146, 171, "quietest: the yard right behind\nthe building (~7 dB)", fill=BLUE, size=16)
    plan.label(120, 100, "Site B, decided Oct 11 2026. Grid = 10 ft. Up = NNE (toward US-290).", size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")
    hose = sum(math.dist(a, b) for a, b in zip(HOSE, HOSE[1:]))
    print(f"  hose run {hose:.0f} ft; pipe to B {math.dist(pipe, (152, 131.5)):.1f} ft")


if __name__ == "__main__":
    main()
