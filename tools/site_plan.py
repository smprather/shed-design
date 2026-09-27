# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Annotated site plan of the north yard, drawn over the Google Maps aerial.

Coordinates are in feet on a lot-aligned grid: the aerial is rotated 29 deg CCW
so the house and Candelaria Dr are square to the frame. +x runs toward
Candelaria Dr, +y runs away from US-290. Scale comes from the map's 20 ft bar
(96.5 px), which agrees with the tape-measured 20x40 canopy footprint to ~10%.

Run: uv run tools/site_plan.py
"""

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


class Plan:
    def __init__(self) -> None:
        raw = Image.open(SRC).convert("RGB").rotate(
            ROTATE_DEG, expand=True, resample=Image.BICUBIC, fillcolor=(40, 40, 40)
        )
        self.box = tuple(round(v * PX_PER_FT) for v in VIEW)
        w, h = self.box[2] - self.box[0], self.box[3] - self.box[1]
        self.img = raw.crop(self.box).resize((w * UPSCALE, h * UPSCALE), Image.LANCZOS)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x * PX_PER_FT - self.box[0]) * UPSCALE,
            (y * PX_PER_FT - self.box[1]) * UPSCALE,
        )

    def grid(self, step: int = 10) -> None:
        x0, y0, x1, y1 = VIEW
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
        x1, y1 = VIEW[2], VIEW[3]
        a, b = self.p(x1 - feet - 8, y1 - 6), self.p(x1 - 8, y1 - 6)
        self.d.rectangle([a[0] - 8, a[1] - 30, b[0] + 8, a[1] + 12], fill=(0, 0, 0, 175))
        self.d.line([a, b], fill=WHITE, width=4)
        self.d.text((a[0], a[1] - 26), f"{feet} ft", fill=WHITE, font=ImageFont.load_default(size=18))


def main() -> None:
    plan = Plan()
    plan.grid()

    # Fence along the US-290 side: solid where visible, dashed where hidden by shadow.
    plan.line([(105, 116.8), (183, 128)], RED, width=5)
    plan.line([(183, 128), (215, 133)], RED, width=5, dash=True)
    plan.label(118, 101, "Fence, US-290 side (approx.): angles ~9 deg toward the house going east", fill=(255, 150, 150))

    # Open ground west of the old canopies: only usable once septic + oak are located.
    zone = [(100, 117.5), (161, 126.5), (161, 149), (100, 149)]
    plan.poly(zone, GREEN, fill=(80, 220, 120, 50), width=3, dash=True)
    plan.label(103, 128.5, "Open ground west of old canopies\n~60 ft run x ~25-30 ft deep\nCHECK: septic + large oak?", fill=(170, 255, 190))

    # Unknowns to confirm with the owner.
    plan.label(123, 140, "light circle:\nfire pit? septic lid?", fill=MAGENTA, size=18)
    plan.label(118, 170, "large tree canopy -\nthe oak? (trunk + drip\nline to be located)", fill=MAGENTA, size=18)

    # Old canopy footprint (removed).
    plan.poly([(161, 129), (205, 129), (205, 150), (161, 150)], ORANGE, width=5)
    plan.label(163, 151.5, "Old canopies (gone)\ntape: 20 x 40\naerial: ~21 x 44", fill=(255, 190, 110))

    # House: north wall plus the east wing.
    plan.poly([(180, 168), (224, 168), (224, 196), (180, 196)], BLUE)
    plan.line([(224, 171), (252, 171), (252, 235)], BLUE)
    plan.label(196, 179, "HOUSE", fill=(160, 210, 255), size=26)

    plan.dim((208, 131.5), (208, 168), "~40 ft fence\nto house", at=(209.5, 150))
    plan.dim((186, 150), (186, 168), "~18 ft", at=(187.5, 157))

    plan.label(222, 138, "Live oaks\n(avoid root zones)", fill=(200, 255, 170))
    plan.label(62, 124, "Existing\nshed\n~15x11", fill=(230, 230, 230), size=18)
    plan.label(62, 163, "Existing shed ~20x12", fill=(230, 230, 230), size=18)

    # Drive approach from Candelaria Dr (route under the oaks unconfirmed).
    plan.line([(283, 170), (259, 162)], WHITE, width=5)
    plan.d.polygon([plan.p(256, 161), plan.p(261, 159.3), plan.p(260, 164.6)], fill=WHITE)
    plan.label(252, 172, "Drive from\nCandelaria Dr\n(route?)", size=18)

    plan.label(229, 217, "Up = toward US-290 (NNW)\nRight = toward Candelaria (ENE)", size=16)
    plan.scale_bar()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plan.img.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")


if __name__ == "__main__":
    main()
