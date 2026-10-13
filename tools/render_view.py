# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "playwright", "numpy"]
# ///
"""Static render of the back-yard view, with and without the planned back-line trees.

Builds a three.js scene from the same data as plan3d.py: the lidar ground, the plan's rear
fence and buildings, building B, the existing trees (the 2017 lidar canopy where it still
stands, from site/canopy-lidar.json), the back-line planting and the back-yard eye.
Then it renders the scene in headless Chromium with grass, sky, sun and shadows. Writes
site/backyard-bare.jpg (no new trees) and site/backyard-<stage>.jpg.

The first run needs a browser for Playwright:
    uv run --with playwright playwright install chromium
or pass --chromium PATH to use one that's already installed.

Run: uv run tools/render_view.py [--stage 8yr]
"""

import json
import math
import tempfile
from pathlib import Path

import rich_click as click
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from plan3d import (B_EAVE, BACKYARD_EYE, BACKYARD_GAZE, CANOPY, FT, PLANTS, SPEC, TERRAIN, Canopy, Frame, Terrain,
                    backyard, planting, read_jsonc)
from site_plan import REPO, SITE_B

TEMPLATE = REPO / "tools" / "render_view.html"
STAGES = {"planted": 0, "8yr": 1, "mature": 2}
STAGE_TEXT = {"planted": "at planting", "8yr": "at ~8 years", "mature": "mature"}
SUN = (140.0, 42.0)  # azimuth and altitude, degrees: late morning in mid-October, behind the viewer
VFOV = 45.0  # degrees, vertical; about a phone camera's main lens held sideways
CANOPY_BLOCK = 2  # m; existing trees are drawn per 2 x 2 m block (finer than the viewer's)
FENCE_POST = 8.0  # ft between posts
SHED_PITCH = 3 / 12  # building B's roof; undecided


def plan_bearing(azimuth: float) -> float:
    """Compass azimuth (degrees) -> angle CCW from plan +x (radians). Plan +x runs N30E."""
    return math.radians(30.0 - azimuth)


def scene(stage: str) -> dict:
    """Everything the render page draws, in plan meters (x along the back line, y away from the lot, z up)."""
    plan = read_jsonc(SPEC)
    ground = Terrain(TERRAIN)
    to_m = Frame()
    view, _ = backyard(ground, to_m)
    canopy = Canopy() if CANOPY.exists() else None
    trees, _ = planting(canopy)
    ents = {e["entity_id"]: e for e in plan["spatial_entities"]}

    buildings = []
    for eid, e in ents.items():
        kind = ("retail" if eid.startswith("scenic_brook_plaza")
                else "apartment" if eid.startswith("granada_ridge_buildings") else None)
        if kind is None:
            continue
        g = e["geometry"]
        for it in g["items"] if g["kind"] == "prisms" else [g]:
            pts = it["points_m"]
            # The 2017 ground predates the grading, so draw the pad down to it where it's lower.
            edge = [(a[0] + (b[0] - a[0]) * s / 8, a[1] + (b[1] - a[1]) * s / 8)
                    for a, b in zip(pts, pts[1:] + pts[:1]) for s in range(8)]
            buildings.append({"kind": kind, "points": pts, "z0": it["z_bottom_m"], "z1": it["z_top_m"],
                              "pad": round(min(ground(*q) for q in edge), 2)})
    b = [to_m(p) for p in SITE_B]
    slab = max(ground(*p) for p in b)  # as in plan3d.py: slab at the high corner
    buildings.append({"kind": "shed", "points": [[round(c, 2) for c in p] for p in b], "z0": round(slab, 2),
                      "z1": round(slab + B_EAVE * FT, 2), "rise": round(23 / 2 * SHED_PITCH * FT, 2)})

    fence = ents["rear_fence"]["geometry"]
    (ax, ay), (bx, by) = fence["points_m"][0], fence["points_m"][-1]
    n = max(1, round(math.dist((ax, ay), (bx, by)) / (FENCE_POST * FT)))
    posts = [[ax + (bx - ax) * i / n, ay + (by - ay) * i / n] for i in range(n + 1)]
    posts = [[round(x, 2), round(y, 2), round(ground(x, y), 3)] for x, y in posts]

    k = STAGES[stage]
    th = plan_bearing(SUN[0])
    alt = math.radians(SUN[1])
    return {
        "terrain": {"x": ground.xs, "y": ground.ys, "z": [[round(v, 3) for v in row] for row in ground.z]},
        "eye": view["eye"], "at": view["at"], "vfov": VFOV,
        "sun": [math.cos(alt) * math.cos(th), math.cos(alt) * math.sin(th), math.sin(alt)],
        "fence": {"posts": posts, "height": fence["height_m"]},
        "buildings": buildings,
        "trees": [{"xy": [round(c, 2) for c in to_m(t["site"])], "z": round(ground(*to_m(t["site"])), 3),
                   "plant": t["plant"], "h": PLANTS[t["plant"]]["sizes"][k][0] * FT,
                   "w": PLANTS[t["plant"]]["sizes"][k][1] * FT} for t in trees],
        "canopy": canopy.for_viewer(ground, CANOPY_BLOCK) if canopy else None,
    }


def caption(img: Image.Image, lines: list[str]) -> Image.Image:
    """Add a strip of plain text under the image."""
    font = ImageFont.load_default(size=max(14, img.width // 85))
    pad, gap = font.size, font.size // 3
    h = pad * 2 + len(lines) * font.size + (len(lines) - 1) * gap
    out = Image.new("RGB", (img.width, img.height + h), (24, 30, 27))
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    for i, line in enumerate(lines):
        d.text((pad, img.height + pad + i * (font.size + gap)), line, font=font,
               fill=(232, 236, 233) if i == 0 else (165, 178, 170))
    return out


@click.command()
@click.option("--stage", type=click.Choice(list(STAGES)), default="8yr", show_default=True,
              help="Tree size for the planted render.")
@click.option("--width", default=1600, show_default=True, help="Image width, px.")
@click.option("--height", default=1000, show_default=True, help="Image height, px (before the caption).")
@click.option("--chromium", type=click.Path(exists=True, path_type=Path), default=None,
              help="A Chromium executable to use instead of Playwright's own.")
@click.option("--out-dir", type=click.Path(path_type=Path), default=REPO / "site", show_default=True)
def main(stage: str, width: int, height: int, chromium: Path | None, out_dir: Path) -> None:
    """Render the back-yard view with and without the planned back-line trees."""
    data = scene(stage)
    sizes = ", ".join(f"{PLANTS[p]['name'].split(',')[0]} ~{PLANTS[p]['sizes'][STAGES[stage]][0]} ft"
                      for p in ("holly", "yaupon", "laurel"))
    common = ("Ground and existing trees from the 2017 lidar (trees kept where still green in Oct 2026 satellite imagery); "
              "rear fence 8 ft. Retail and apartments as planned (apartments as 3 stories, ~40 ft).")
    head = (f"From the back yard: eye {BACKYARD_EYE[1]:g} ft up, {BACKYARD_EYE[0]:g} ft out from the middle of the back wall, "
            f"looking {BACKYARD_GAZE[0]:g}° left of straight back.")
    renders = {"bare": (False, [head, "Without the new trees.", common]),
               stage: (True, [head, f"New back-line trees {STAGE_TEXT[stage]}, in the gaps between existing trees: {sizes}.",
                              common])}
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_path = Path(tmp) / "render.html"
        page_path.write_text(TEMPLATE.read_text().replace("/*SCENE*/", json.dumps(data)))
        browser = pw.chromium.launch(
            executable_path=str(chromium) if chromium else None,
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_path.as_uri())
        page.wait_for_function("window.ready === true || window.failed", timeout=180_000)
        if errors or page.evaluate("window.failed || null"):
            raise click.ClickException(f"render page failed: {errors or page.evaluate('window.failed')}")
        for name, (show, lines) in renders.items():
            page.evaluate(f"window.draw({json.dumps(show)})")
            shot = Path(tmp) / f"{name}.png"
            page.locator("canvas").screenshot(path=str(shot))
            img = Image.open(shot).convert("RGB").resize((width, height), Image.LANCZOS)  # 2x supersampled
            path = out_dir / f"backyard-{name}.jpg"
            caption(img, lines).save(path, quality=88, optimize=True)
            click.echo(f"wrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
        browser.close()


if __name__ == "__main__":
    main()
