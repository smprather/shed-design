# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "playwright"]
# ///
"""Render building B (tools/building_b.html) to still images.

Writes site/building-b-<view>.jpg for the page's views: oblique, from the yard, from the
house corner and from US-290. The page is also published as an Artifact, without its own
<html>/<head>/<body>, so this wraps it in a minimal document first.

Needs a Playwright Chromium: `uv run --with playwright playwright install chromium`, or
pass --chromium PATH.

Run: uv run tools/render_building_b.py
"""

import base64
import json
import tempfile
from pathlib import Path

import rich_click as click
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "tools" / "building_b.html"
VIEWS = {"oblique": False, "yard": False, "house": True, "north": False}  # view -> doors open
SKELETON = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>{}</body></html>')


@click.command()
@click.option("--width", default=1600, show_default=True, help="Image width, px.")
@click.option("--height", default=1000, show_default=True, help="Image height, px.")
@click.option("--chromium", type=click.Path(exists=True, path_type=Path), default=None,
              help="A Chromium executable to use instead of Playwright's own.")
@click.option("--out-dir", type=click.Path(path_type=Path), default=REPO / "site", show_default=True)
def main(width: int, height: int, chromium: Path | None, out_dir: Path) -> None:
    """Write the building B stills."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_path = Path(tmp) / "building_b.html"
        page_path.write_text(SKELETON.format(PAGE.read_text()))
        browser = pw.chromium.launch(
            executable_path=str(chromium) if chromium else None,
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_path.as_uri())
        page.wait_for_function("window.ready === true || window.failed", timeout=180_000)
        if errors or page.evaluate("window.failed || null"):
            raise click.ClickException(f"building B page failed: {errors or page.evaluate('window.failed')}")
        for name, open_doors in VIEWS.items():
            url = page.evaluate(f"window.still({json.dumps(name)}, {width}, {height}, {{open: {json.dumps(open_doors)}}})")
            path = out_dir / f"building-b-{name}.jpg"
            path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
            click.echo(f"wrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
        browser.close()


if __name__ == "__main__":
    main()
