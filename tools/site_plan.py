# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Annotated site plan of the north yard, drawn over the Google Maps aerial.

Coordinates are in feet on a lot-aligned grid: the aerial is rotated 29 deg CCW
so the house and Candelaria Dr are square to the frame. +x runs ESE toward
Candelaria Dr, +y runs SSW away from US-290. Scale comes from the map's 20 ft bar
(96.5 px), which agrees with the tape-measured 20x40 canopy footprint to ~10%.

The property line comes from the Travis CAD parcel map (see PARCEL below).

Run: uv run tools/site_plan.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "8400_candelaria_78737.png"
OUT = REPO / "site" / "north-yard.png"

PX_PER_FT = 96.5 / 20
ROTATE_DEG = 29
UPSCALE = 2
VIEW = (60, 95, 285, 235)  # x0, y0, x1, y1 in feet

WHITE = (255, 255, 255)
YELLOW = (255, 255, 120)
ORANGE = (255, 150, 40)
RED = (255, 70, 70)
GREEN = (80, 220, 120)
BLUE = (120, 190, 255)
MAGENTA = (255, 110, 230)
PURPLE = (200, 140, 255)
CYAN = (90, 230, 255)

# Survey plat: Samford & Associates, Apr 16 1991 (rev Apr 18 1991), Lot 176,
# Granada Hills Amended (Vol. 55 Pg. 69, Plat Records of Travis County).
# Bearings as true azimuths (degrees), distances in feet. The back line,
# N30°00'E 155.05', closes to 0.01 ft.
SV_FRONT = (30 + 5 / 60, 114.95)  # N30°05'E along Candelaria Dr, south pin -> north pin
SV_NORTH = (360 - (50 + 46 / 60), 253.50)  # N50°46'W, US-290 side, front -> back
SV_SOUTH = (360 - (59 + 52 / 60), 250.05)  # N59°52'W, south neighbor side, front -> back

Pt = tuple[float, float]


def _dir(az: float) -> Pt:
    r = math.radians(az)
    return (math.sin(r), math.cos(r))


def _step(p: Pt, az: float, dist: float) -> Pt:
    u = _dir(az)
    return (p[0] + dist * u[0], p[1] + dist * u[1])


# Corners in east/north feet from the front-south pin.
_FS = (0.0, 0.0)
_FN = _step(_FS, *SV_FRONT)
_RN = _step(_FN, *SV_NORTH)
_RS = _step(_FS, *SV_SOUTH)


def st(s: float, t: float) -> Pt:
    """Survey-local point: s ft back from the front line along the south line, t ft toward US-290."""
    return _step(_step(_FS, SV_SOUTH[0], s), SV_SOUTH[0] + 90, t)


def offset_line(a: Pt, b: Pt, dist: float, toward: Pt) -> tuple[Pt, Pt]:
    """Line a-b shifted `dist` ft toward the side containing `toward`."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = (-dy / math.hypot(dx, dy), dx / math.hypot(dx, dy))
    if (toward[0] - a[0]) * n[0] + (toward[1] - a[1]) * n[1] < 0:
        n = (-n[0], -n[1])
    return (a[0] + dist * n[0], a[1] + dist * n[1]), (b[0] + dist * n[0], b[1] + dist * n[1])


def intersect(l1: tuple[Pt, Pt], l2: tuple[Pt, Pt]) -> Pt:
    (x1, y1), (x2, y2) = l1
    (x3, y3), (x4, y4) = l2
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    a, b = x1 * y2 - y1 * x2, x3 * y4 - y3 * x4
    return ((a * (x3 - x4) - (x1 - x2) * b) / den, (a * (y3 - y4) - (y1 - y2) * b) / den)


# House walls rebuilt from the plat's dimensions and ties (44.6 / 35.2 ft to the US-290
# line, 22.9 / 22.7 ft to the south line). The north wall is 62.0 ft as laser-measured
# (owner, Oct 2026: A->B), which matches the plat drawing; the NE tie then checks to ~0.6 ft.
HOUSE_ST = [
    (56.7, 22.7), (100.8, 22.9), (100.8, 68.8), (126.2, 68.8), (126.2, 90.1),
    (64.2, 90.1), (64.2, 57.6), (69.2, 57.6), (69.2, 50.4), (56.7, 50.4),
]
PORCH_ST = [(54.5, 57.6), (64.2, 57.6), (64.2, 90.1), (54.5, 90.1)]  # CAD open porch 315 sq ft
# CAD attached garage 441 sq ft = 21 x 21, at the house's NE corner behind the porch
# (owner marked it on the plat). The door faces north, onto the concrete driveway.
# Inside 19'-6" x 20'-2" (laser, Oct 15 2026), which fits.
GARAGE_ST = [(64.2, 69.1), (85.2, 69.1), (85.2, 90.1), (64.2, 90.1)]
GARAGE_DOOR = (st(74.7, 90.1), st(74.7, 98))  # arrow out of the north wall
HOUSE_NW = st(126.2, 90.1)  # point A on the measurement plan

_CENTER = ((_FS[0] + _RN[0]) / 2, (_FS[1] + _RN[1]) / 2)
BUILDING_LINE = (
    intersect(offset_line(_FS, _FN, 45, _CENTER), (_FS, _RS)),
    intersect(offset_line(_FS, _FN, 45, _CENTER), (_FN, _RN)),
)  # 45' B.L. (plat), measured from the front line
PUE = [
    (intersect(offset_line(_RS, _RN, w, _CENTER), (_FS, _RS)), intersect(offset_line(_RS, _RN, w, _CENTER), (_FN, _RN)))
    for w in (7.5, 10)
]  # 7.5' and 10' P.U.E. (plat) along the back line
# Plat shows "Well" ~28 ft in from the back line and ~12 ft from the US-290 line (read off
# the sketch, +/-3 ft).
WELL = intersect(offset_line(_RS, _RN, 28, _CENTER), offset_line(_FN, _RN, 12, _CENTER))
# 1991 electric service: from the overhead line on the back line to the house's back wall,
# ~30 ft north of the south line. The overhead line on the back line has since been removed
# (owner, Oct 2026, with the redevelopment next door), so the house's current feed is unknown.
ELECTRIC_1991 = (intersect((st(0, 30), st(1, 30)), (_RS, _RN)), st(100.8, 30))

# Register to the aerial frame: the house's NW wall corner sits ~1.5 ft inside the
# roof corner seen at (180, 168).
ANCHOR_SITE = (181.5, 169.5)


def en_to_site(p: Pt) -> Pt:
    r = _dir(ROTATE_DEG + 90), _dir(ROTATE_DEG)
    x = p[0] * r[0][0] + p[1] * r[0][1]
    y = -(p[0] * r[1][0] + p[1] * r[1][1])
    ax = HOUSE_NW[0] * r[0][0] + HOUSE_NW[1] * r[0][1]
    ay = -(HOUSE_NW[0] * r[1][0] + HOUSE_NW[1] * r[1][1])
    return (x - ax + ANCHOR_SITE[0], y - ay + ANCHOR_SITE[1])


def site(pts) -> list[Pt]:
    return [en_to_site(p) for p in pts]


# Front-south, front-north (US-290), back-north, back-south.
PARCEL = site([_FS, _FN, _RN, _RS])
HOUSE = site(st(*q) for q in HOUSE_ST)
PORCH = site(st(*q) for q in PORCH_ST)
GARAGE = site(st(*q) for q in GARAGE_ST)


class Plan:
    def __init__(self, view: tuple[int, int, int, int] = VIEW) -> None:
        self.view = view
        raw = Image.open(SRC).convert("RGB").rotate(
            ROTATE_DEG, expand=True, resample=Image.BICUBIC, fillcolor=(40, 40, 40)
        )
        self.box = tuple(round(v * PX_PER_FT) for v in view)
        w, h = self.box[2] - self.box[0], self.box[3] - self.box[1]
        self.img = raw.crop(self.box).resize((w * UPSCALE, h * UPSCALE), Image.LANCZOS)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x * PX_PER_FT - self.box[0]) * UPSCALE,
            (y * PX_PER_FT - self.box[1]) * UPSCALE,
        )

    def grid(self, step: int = 10) -> None:
        x0, y0, x1, y1 = self.view
        for ft in range(x0, x1 + 1, step):
            self.d.line([self.p(ft, y0), self.p(ft, y1)], fill=(255, 255, 255, 40))
        for ft in range(y0, y1 + 1, step):
            self.d.line([self.p(x0, ft), self.p(x1, ft)], fill=(255, 255, 255, 40))

    def line(self, pts, fill, width=4, dash: bool = False) -> None:
        for a, b in zip(pts, pts[1:]):
            if not dash:
                self.d.line([self.p(*a), self.p(*b)], fill=fill, width=width)
                continue
            (xa, ya), (xb, yb) = self.p(*a), self.p(*b)
            length = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
            on, off, t = 14, 10, 0.0
            while t < length:
                s, e = t / length, min(t + on, length) / length
                self.d.line(
                    [(xa + (xb - xa) * s, ya + (yb - ya) * s), (xa + (xb - xa) * e, ya + (yb - ya) * e)],
                    fill=fill,
                    width=width,
                )
                t += on + off

    def poly(self, pts, outline, fill=None, width=4, dash: bool = False) -> None:
        if fill:
            self.d.polygon([self.p(*q) for q in pts], fill=fill)
        self.line([*pts, pts[0]], outline, width, dash)

    def label(self, x: float, y: float, text: str, fill=WHITE, size: int = 20) -> None:
        font = ImageFont.load_default(size=size)
        l, t, r, b = self.d.multiline_textbbox(self.p(x, y), text, font=font)
        self.d.rectangle([l - 6, t - 4, r + 6, b + 4], fill=(0, 0, 0, 175))
        self.d.multiline_text(self.p(x, y), text, fill=fill, font=font)

    def dim(self, a, b, text: str, at: tuple[float, float], fill=YELLOW) -> None:
        self.line([a, b], fill, width=3)
        for q in (a, b):
            cx, cy = self.p(*q)
            self.d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=fill)
        self.label(*at, text, fill=fill)

    def scale_bar(self, feet: int = 20) -> None:
        x1, y1 = self.view[2], self.view[3]
        a, b = self.p(x1 - feet - 8, y1 - 6), self.p(x1 - 8, y1 - 6)
        self.d.rectangle([a[0] - 8, a[1] - 30, b[0] + 8, a[1] + 12], fill=(0, 0, 0, 175))
        self.d.line([a, b], fill=WHITE, width=4)
        self.d.text((a[0], a[1] - 26), f"{feet} ft", fill=WHITE, font=ImageFont.load_default(size=18))


def draw_survey(plan: Plan) -> None:
    """Property line, plat easements and building line, well, and the house as surveyed."""
    for a, b in PUE:
        plan.line(site([a, b]), PURPLE, width=2, dash=True)
    plan.line(site(BUILDING_LINE), PURPLE, width=2, dash=True)
    plan.poly(PARCEL, PURPLE, width=4)
    plan.poly(HOUSE, BLUE, width=4)
    plan.poly(PORCH, BLUE, width=2, dash=True)
    plan.poly(GARAGE, BLUE, fill=(120, 190, 255, 70), width=3)
    tail, tip = site(GARAGE_DOOR)
    plan.line([tail, tip], WHITE, width=5)
    (tx, ty), (bx, by) = plan.p(*tip), plan.p(*tail)
    ux, uy = (tx - bx) / math.hypot(tx - bx, ty - by), (ty - by) / math.hypot(tx - bx, ty - by)
    plan.d.polygon([(tx + 10 * ux, ty + 10 * uy), (tx - 10 * uy, ty + 10 * ux), (tx + 10 * uy, ty - 10 * ux)], fill=WHITE)
    cx, cy = plan.p(*en_to_site(WELL))
    plan.d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], outline=CYAN, width=4)


def north_line_y(x: float) -> float:
    """y of the surveyed US-290 line at a given x (site frame)."""
    (x0, y0), (x1, y1) = PARCEL[2], PARCEL[1]
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


FIELD_POINTS = REPO / "site" / "field-points.json"
# The US-290 fence (owner, Oct 2026). West of the gap between the old canopies it follows
# the owner's trace on a newer aerial (mapped with a similarity fit on the house roof and
# canopy corners, residuals <= 2 ft). At that gap it bends and runs along the highway side
# of the house-side canopy, roughly parallel to the house; laser shot 4 (B -> fence 42.0 ft)
# fits that line. Shot 3 hit near the bend and read long. To be checked with a tape.
FENCE_TRACE = [(62.9, 102.7), (183.0, 128.0), (205.0, 128.3), (243.5, 128.7)]

# Building B (owner, Oct 11 2026): 23 x 43 ft, square to the house. The north wall stays
# where the 20 x 40 had it (5 ft inside the surveyed line at the NE corner); the west end
# sits 10 ft from the septic pipe and the east end at the oak's drip line. NW, NE, SE, SW.
SITE_B = [(149.5, 131.5), (192.5, 131.5), (192.5, 154.5), (149.5, 154.5)]


def draw_field(plan: Plan) -> dict:
    """Laser-measured fence, big oak (trunk, drip line, no-dig core) and septic pipe."""
    import json

    if not FIELD_POINTS.exists():
        return {}
    fp = json.loads(FIELD_POINTS.read_text())
    plan.line(FENCE_TRACE, ORANGE, width=5)
    trunks = [(tuple(fp[k]["solutions"][0]["site"]), fp[k].get("trunk_radius") or 1.0)
              for k in ("big_oak", "big_oak_2") if fp.get(k, {}).get("solutions")]

    def circle(c, radius, **kw):
        x0, y0 = plan.p(c[0] - radius, c[1] - radius)
        x1, y1 = plan.p(c[0] + radius, c[1] + radius)
        plan.d.ellipse([x0, y0, x1, y1], **kw)

    # Twin-trunk oak: drip line ~25 ft (measured from the near trunk) and a 12 ft no-dig core around each trunk.
    for c, _ in trunks:
        circle(c, 25.1, outline=GREEN, width=3, fill=(80, 220, 120, 18))
    for c, _ in trunks:
        circle(c, 12.0, outline=(255, 200, 80), width=3)
    for c, r in trunks:
        circle(c, r, fill=(120, 80, 40), outline=WHITE, width=2)
    tape_fence = [tuple(p["site"]) for p in fp.get("tape_fence", [])]
    if len(tape_fence) > 1:
        plan.line(tape_fence, YELLOW, width=4)
    tree_edge = [tuple(p["site"]) for p in fp.get("tape_tree_edge", [])]
    if len(tree_edge) > 1:
        plan.line(tree_edge, GREEN, width=4)
    for d in fp.get("tape_points", {}).values():
        cx, cy = plan.p(*d["site"])
        plan.d.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=YELLOW, outline=(0, 0, 0), width=2)
        plan.label(d["site"][0] + 1.5, d["site"][1] + 1, d["label"], fill=YELLOW, size=15)
    for sol in fp.get("white_pipe", {}).get("solutions", []):
        cx, cy = plan.p(*sol["site"])
        plan.d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=WHITE, outline=(0, 0, 0), width=2)
    return fp


def main() -> None:
    plan = Plan()
    plan.grid()

    draw_survey(plan)
    fp = draw_field(plan)
    plan.label(100, 96.5, "Purple = property line (1991 survey). Orange = fence (owner): bends at the old canopy gap.", fill=(255, 190, 110), size=18)

    well = en_to_site(WELL)
    plan.label(well[0] + 2.5, well[1] + 1.5, "well (confirmed at\nthe 1991 plat spot)", fill=CYAN, size=16)
    plan.label(62, 186, "10' utility\neasement\n(back line)", fill=PURPLE, size=16)

    plan.poly([(161, 129), (205, 129), (205, 150), (161, 150)], ORANGE, width=2, dash=True)
    plan.label(162.5, 151, "old canopies (gone)", fill=(255, 190, 110), size=16)

    if "big_oak" in fp:
        c = fp["big_oak"]["solutions"][0]["site"]
        plan.label(c[0] + 7, c[1] + 0.5, "BIG OAK (twin trunks)\nnear trunk 24 in", fill=WHITE, size=18)
        plan.label(c[0] - 33, c[1] - 22, "drip line ~25 ft (green)\nno digging inside 12 ft (yellow)", fill=(170, 255, 190), size=16)
    pipes = fp.get("white_pipe", {}).get("solutions", [])
    for i, sol in enumerate(pipes):
        x, y = sol["site"]
        plan.label(x - 12, y + 2.5, "white pipe?" if len(pipes) > 1 else "septic access pipe", fill=WHITE, size=16)
    if len(pipes) > 1:
        plan.label(97, 137, "the white pipe is one of these two\n(A and F1 can't tell east from west)", fill=WHITE, size=16)

    plan.label(97, 160, "west of the oak: the open strip -\nwhere the drainfield likely is", fill=MAGENTA, size=18)

    plan.label(186, 213, "HOUSE (surveyed walls)", fill=(160, 210, 255), size=22)
    plan.label(222, 177, "garage", fill=(160, 210, 255), size=18)
    plan.label(242, 188, "porch", fill=(160, 210, 255), size=14)

    a = HOUSE[4]
    plan.dim(a, (a[0], north_line_y(a[0])), "44.6 ft\n(survey)", at=(171, 158))

    plan.label(62, 225, "Aerial predates the sale: only the house, fences\nand driveway remain.", fill=ORANGE, size=20)

    # Drive approach from Candelaria Dr toward the garage's north side.
    plan.line([(283, 170), (259, 162)], WHITE, width=5)
    plan.d.polygon([plan.p(256, 161), plan.p(261, 159.3), plan.p(260, 164.6)], fill=WHITE)
    plan.label(256, 166, "drive", size=18)
    plan.label(256, 145, "45' building\nline (plat)", fill=PURPLE, size=16)

    plan.label(229, 217, "Up = NNE (toward US-290)\nRight = ESE (toward Candelaria)", size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
