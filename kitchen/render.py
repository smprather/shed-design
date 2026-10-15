# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "playwright"]
# ///
"""Render the kitchen mockup's plan and 3D views to images.

Opens kitchen/mockup.html in headless Chromium and writes kitchen/plan.png and
kitchen/view-<name>.jpg. The page is published as an Artifact without its own
<html>/<head>/<body>, so this wraps it in a minimal document first.

Needs a Playwright Chromium: `uv run --with playwright playwright install chromium`,
or pass --chromium PATH.

Run: uv run kitchen/render.py
"""

import base64
import tempfile
from pathlib import Path

import rich_click as click
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PAGE = HERE / "mockup.html"
VIEWS = ("overview", "door", "dining", "stair")
SKELETON = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>{}</body></html>')


@click.command()
@click.option("--width", default=1600, show_default=True, help="3D image width, px.")
@click.option("--height", default=1000, show_default=True, help="3D image height, px.")
@click.option("--chromium", type=click.Path(exists=True, path_type=Path), default=None,
              help="A Chromium executable to use instead of Playwright's own.")
@click.option("--out-dir", type=click.Path(path_type=Path), default=HERE, show_default=True)
def main(width: int, height: int, chromium: Path | None, out_dir: Path) -> None:
    """Write the plan and the 3D views of the kitchen mockup."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_path = Path(tmp) / "mockup.html"
        page_path.write_text(SKELETON.format(PAGE.read_text()))
        browser = pw.chromium.launch(
            executable_path=str(chromium) if chromium else None,
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_path.as_uri())
        page.wait_for_function("window.ready === true || window.failed", timeout=180_000)
        if errors or page.evaluate("window.failed || null"):
            raise click.ClickException(f"mockup page failed: {errors or page.evaluate('window.failed')}")
        page.locator("#plan").screenshot(path=str(out_dir / "plan.png"))
        click.echo(f"wrote {out_dir / 'plan.png'}")
        for name in VIEWS:
            url = page.evaluate(f"window.still({name!r}, {width}, {height})")
            path = out_dir / f"view-{name}.jpg"
            path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
            click.echo(f"wrote {path}")
        browser.close()


if __name__ == "__main__":
    main()
