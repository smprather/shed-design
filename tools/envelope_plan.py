# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Where a large building could go, as of the current measurements.

Draws the limits we know (surveyed line minus a 5 ft setback, the back-line easement, the
well, the twin oak's drip line, a 10 ft keep-out around the septic access pipe in case it
marks the tank) plus the edges of the other trees as seen on the aerial (not measured),
and tests sample footprints against them. Same lot-aligned foot grid as site_plan.py.

Run: uv run tools/envelope_plan.py
"""

import json
import math

from site_plan import (
    CYAN, GREEN, MAGENTA, PARCEL, RED, REPO, SITE_B, WELL, WHITE, YELLOW,
    Plan, draw_field, draw_survey, en_to_site,
)

OUT = REPO / "site" / "envelope.png"
VIEW = (55, 95, 262, 262)
SETBACK = 5.0  # ft inside the surveyed US-290 line
KEEP_OUT = 10.0  # ft around the well and the septic access pipe

RN, FN = PARCEL[2], PARCEL[1]
THETA = math.atan2(FN[1] - RN[1], FN[0] - RN[0])
ALONG = (math.cos(THETA), math.sin(THETA))
INWARD = (-math.sin(THETA), math.cos(THETA))  # into the lot (site y grows southward)

# Edges of the other trees, read off the aerial (not measured, +/-5 ft).
STRIP_TREE_EDGE_Y = 148.0
BACK_LAWN_OPEN = [(80, 195), (165, 195), (165, 232), (80, 232)]


def setback_point(x: float) -> tuple[float, float]:
    """Point on the line SETBACK ft inside the surveyed line, at site x."""
    t = (x - RN[0]) / ALONG[0]
    return (RN[0] + t * ALONG[0] + SETBACK * INWARD[0], RN[1] + t * ALONG[1] + SETBACK * INWARD[1])


def line_rect(x0: float, length: float, depth: float):
    """Footprint along the setback line: NW corner on it at x0, length along it, depth inward."""
    nw = setback_point(x0)
    ne = (nw[0] + length * ALONG[0], nw[1] + length * ALONG[1])
    return [nw, ne, (ne[0] + depth * INWARD[0], ne[1] + depth * INWARD[1]),
            (nw[0] + depth * INWARD[0], nw[1] + depth * INWARD[1])]


# Site A (Oct 11 2026): the strip west of the septic pipe, between the well and the pipe, square to the line.
# 30 ft deep since Oct 18 (owner: past 1,000 sq ft; was 27). 30 ft along the line since Oct 24, for a common
# 30 x 30 x 11 kit (owner). It keeps the east end, 10.3 ft from the septic pipe, and gives up 5 ft at the west end:
# the well is now 15 ft off. The 35 ft site it was cut from starts at x 98.6.
SITE_A = line_rect(98.6 + 5 * ALONG[0], 30, 30)


def circle(plan: Plan, c, r, **kw):
    x0, y0 = plan.p(c[0] - r, c[1] - r)
    x1, y1 = plan.p(c[0] + r, c[1] + r)
    plan.d.ellipse([x0, y0, x1, y1], **kw)


def main() -> None:
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    pipe = tuple(fp["white_pipe"]["solutions"][0]["site"])
    well = en_to_site(WELL)

    plan = Plan(view=VIEW)
    plan.grid()
    draw_survey(plan)
    draw_field(plan)

    plan.line([setback_point(60), setback_point(258)], RED, width=3, dash=True)
    circle(plan, well, KEEP_OUT, outline=CYAN, width=3)
    circle(plan, pipe, KEEP_OUT, outline=MAGENTA, width=3)
    plan.line([(95, STRIP_TREE_EDGE_Y), (150, STRIP_TREE_EDGE_Y)], WHITE, width=2, dash=True)
    plan.poly(BACK_LAWN_OPEN, WHITE, width=2, dash=True)

    candidates = {
        "A  30 x 30": SITE_A,
        "B  23 x 43": SITE_B,
        "C  30 x 60": [(90, 197), (150, 197), (150, 227), (90, 227)],
    }
    for name, poly in candidates.items():
        plan.poly(poly, YELLOW, fill=(255, 220, 60, 90), width=4)
        cx = sum(p[0] for p in poly) / 4
        cy = sum(p[1] for p in poly) / 4
        plan.label(cx - 7, cy - 2, name, fill=(255, 235, 140), size=22)

    plan.label(64, 97, "Red dashed = 5 ft inside the surveyed line.  Rings: well and septic pipe keep-outs (10 ft), "
                       "oak drip line (green).  White dashed = edges of other trees from the aerial, not measured.", size=16)
    plan.label(96, 150, "strip west of B: ~25-40 ft deep\nbetween the setback and the trees", fill=WHITE, size=16)
    plan.label(150, 156.5, "SW corner: needs the tree edge (T11)", fill=(255, 235, 140), size=16)
    plan.label(147, 113, "septic pipe: tank here? keep 10 ft", fill=MAGENTA, size=16)
    plan.label(84, 236, "back lawn: open ~85 x 37 ft on the aerial (septic and trees here still unknown)", fill=WHITE, size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")
    for name, poly in candidates.items():
        print(f"  {name}: corners {[tuple(round(v, 1) for v in p) for p in poly]}")


if __name__ == "__main__":
    main()
