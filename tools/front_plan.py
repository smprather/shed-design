# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Front-yard study: circle drive and covered parking vs. the plat's 45' building line.

The owner's sketch (drawn on the 1991 plat) is transferred to scale. Two options that stay
behind the building line are drawn for comparison. Same lot-aligned foot grid as
site_plan.py; shapes are given in survey-local (s, t) feet: s back from the front line,
t from the south line toward US-290.

Run: uv run tools/front_plan.py
"""

from site_plan import (
    BLUE, BUILDING_LINE, GREEN, ORANGE, PURPLE, RED, REPO, WHITE, YELLOW,
    Plan, draw_survey, site, st,
)

OUT = REPO / "site" / "front-yard.png"
VIEW = (212, 128, 338, 272)

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


def st_site(pts):
    return site(st(*q) for q in pts)


def main() -> None:
    plan = Plan(view=VIEW)
    plan.grid()
    draw_survey(plan)
    plan.line(st_site(FRONT_ELECTRIC), YELLOW, width=2, dash=True)

    # Owner's sketch.
    plan.line(st_site(catmull_rom(SKETCH_OUTER)), RED, width=4)
    plan.line(st_site(catmull_rom(SKETCH_INNER)), RED, width=4)
    plan.poly(st_site(SKETCH_BOX), ORANGE, fill=(255, 150, 40, 60), width=4)

    # Options behind the line.
    plan.poly(st_site(PORTE_COCHERE), GREEN, fill=(80, 220, 120, 70), width=4, dash=True)
    plan.poly(st_site(NORTH_CARPORT), GREEN, fill=(80, 220, 120, 70), width=4, dash=True)

    bl = site(BUILDING_LINE)
    plan.line(bl, PURPLE, width=4)
    plan.label(bl[1][0] - 8, 131, "45' building line (plat)", fill=PURPLE, size=20)

    plan.label(222.5, 179, "garage ->\nkitchen?", fill=(160, 210, 255), size=16)
    plan.label(216, 222, "HOUSE", fill=(160, 210, 255), size=24)
    plan.label(271, 214, "your sketch:\n~26 x 33 ft cover,\n~17 ft past the line", fill=(255, 190, 110), size=18)
    plan.label(230, 236, "A: porte-cochere\nbehind the line\n~12 x 44 ft,\n2 cars nose-to-tail", fill=(150, 255, 170), size=18)
    plan.label(228, 132, "B: carport on the old\ngarage apron ~23 x 24 ft\n(live oaks here)", fill=(150, 255, 170), size=18)
    plan.label(300, 255, "1991 electric\n(call 811)", fill=YELLOW, size=16)
    plan.label(311, 200, "Candelaria\nDr", fill=WHITE, size=16)
    plan.label(214, 266, "Red = your circle drive (approx.). Grid = 10 ft. Up = NNE.", size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
