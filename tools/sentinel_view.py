# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "pyproj", "rasterio", "tifffile"]
# ///
"""Recent satellite view of the lot and the land behind it, from free Sentinel-2 imagery.

Sentinel-2 passes every few days. Its pixels are 10 m (33 ft), so single trees don't show,
but woods vs cleared ground does. This finds clear scenes in Element 84's Earth Search
catalog of the public AWS archive. It crops the area around the lot and draws the property
lines and the back-yard sight lines on top.

Writes site/sentinel.png: a scene from --before next to the latest clear one.
With --series, it also prints the mean color of retail lot 1A over time, which dates the
clearing.

Run: uv run tools/sentinel_view.py [--before 2024-11] [--series]
"""

import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
import rich_click as click
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

from fetch_terrain import plan_to_lonlat
from plan3d import SPEC, Frame, Terrain, TERRAIN, backyard, read_jsonc
from site_plan import HOUSE, PARCEL, REPO

STAC = "https://earth-search.aws.element84.com/v1/search"
TILE = "_14RNU_"  # the Sentinel-2 tile (UTM 14N) that holds the lot
PLAN_BOX = ((-290.0, 80.0), (-190.0, 260.0))  # plan m: x range, y range to show
PX = 1.0  # m per output pixel (the source is 10 m)
OUT = REPO / "site" / "sentinel.png"
to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True)


def utm(p: tuple[float, float]) -> tuple[float, float]:
    """Plan m -> UTM 14N m."""
    return to_utm.transform(*plan_to_lonlat(*p))


def search(start: str, end: str, cloud: float = 3.0) -> list[dict]:
    """Clear Sentinel-2 L2A scenes over the lot, oldest first."""
    body = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": list(plan_to_lonlat(0, 0))},
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z", "limit": 200,
            "query": {"eo:cloud_cover": {"lt": cloud}}}
    req = urllib.request.Request(STAC, json.dumps(body).encode(), {"Content-Type": "application/json"})
    feats = json.load(urllib.request.urlopen(req, timeout=60))["features"]
    return sorted((f for f in feats if TILE in f["id"]), key=lambda f: f["properties"]["datetime"])


def read(scene: dict, bounds: tuple[float, float, float, float]) -> tuple[np.ndarray, object]:
    """The true-color window (bands, rows, cols) and its transform."""
    with rasterio.open("/vsicurl/" + scene["assets"]["visual"]["href"]) as src:
        w = from_bounds(*bounds, src.transform)
        return src.read(window=w, boundless=True).astype(float), src.window_transform(w)


@click.command()
@click.option("--before", default="2024-11", show_default=True, help="Month (YYYY-MM) for the left panel.")
@click.option("--series", is_flag=True, help="Also print retail lot 1A's mean color per month since 2023.")
@click.option("--out", type=click.Path(path_type=Path), default=OUT, show_default=True)
def main(before: str, series: bool, out: Path) -> None:
    """Draw the lot on an older and the latest clear Sentinel-2 scene."""
    plan = read_jsonc(SPEC)
    ents = {e["entity_id"]: e for e in plan["spatial_entities"]}
    to_m = Frame()
    view, _ = backyard(Terrain(TERRAIN), to_m)
    (x0, x1), (y0, y1) = PLAN_BOX
    corners = [utm((x, y)) for x in (x0, x1) for y in (y0, y1)]
    e0, e1 = min(c[0] for c in corners), max(c[0] for c in corners)
    n0, n1 = min(c[1] for c in corners), max(c[1] for c in corners)
    bounds = (e0, n0, e1, n1)

    if series:
        lot = [utm(p) for p in ents["retail_lot_1a"]["geometry"]["points_m"]]
        months: dict[str, dict] = {}
        for f in search("2023-01-01", "2100-01-01"):
            months.setdefault(f["properties"]["datetime"][:7], f)
        for m, f in months.items():
            a, tr = read(f, bounds)
            mask = ~geometry_mask([{"type": "Polygon", "coordinates": [lot + lot[:1]]}], out_shape=a.shape[1:], transform=tr)
            click.echo(f"{f['properties']['datetime'][:10]}  lot 1A mean RGB {a[:, mask].mean(1).round(0)}")

    y, m = map(int, before.split("-"))
    first = search(f"{before}-01", f"{y + m // 12}-{m % 12 + 1:02d}-01")
    latest = search("2025-01-01", "2100-01-01")
    if not first or not latest:
        raise click.ClickException("no clear scene found")
    scenes = [first[0], latest[-1]]
    imgs = [read(s, bounds) for s in scenes]
    tr = imgs[0][1]
    top = max(np.percentile(a, 99.5) for a, _ in imgs)  # one stretch for both panels, so they compare
    w_px, h_px = round((e1 - e0) / PX), round((n1 - n0) / PX)

    def to_px(p: tuple[float, float]) -> tuple[float, float]:
        e, n = utm(p)
        return (e - e0) / PX, (n1 - n) / PX

    font = ImageFont.load_default(size=15)
    small = ImageFont.load_default(size=13)
    lot = [to_px(to_m(p)) for p in PARCEL]
    house = [to_px(to_m(p)) for p in HOUSE]
    eye = view["eye"][:2]
    panels = []
    for scene, (a, _) in zip(scenes, imgs):
        rgb = np.clip((a / top) ** 0.85 * 255, 0, 255).astype(np.uint8).transpose(1, 2, 0)
        im = Image.fromarray(rgb).resize((w_px, h_px), Image.BICUBIC)
        d = ImageDraw.Draw(im, "RGBA")
        for eid, color in (("retail_lot_1a", (255, 150, 60, 255)), ("apartment_lot_2a", (255, 220, 90, 255))):
            pts = [to_px(tuple(p)) for p in ents[eid]["geometry"]["points_m"]]
            d.line(pts + pts[:1], fill=color, width=2)
        for eid in ("granada_ridge_buildings_7_8", "granada_ridge_buildings_1_6", "scenic_brook_plaza_building_3",
                    "scenic_brook_plaza_buildings_1_2"):
            g = ents[eid]["geometry"]
            for it in g["items"] if g["kind"] == "prisms" else [g]:
                pts = [to_px(tuple(p)) for p in it["points_m"]]
                d.polygon(pts, outline=(140, 200, 255, 255), fill=(140, 200, 255, 70))
        # Sight lines from the back-yard eye: the back line's ends bound what trees on it can hide.
        ex, ey = to_px(eye)
        for end in ((-23.63, 0.0), (23.63, 0.0)):
            far = (eye[0] + (end[0] - eye[0]) * 9, eye[1] + (end[1] - eye[1]) * 9)
            d.line([(ex, ey), to_px(far)], fill=(80, 230, 255, 230), width=2)
        apt = ents["granada_ridge_buildings_7_8"]["geometry"]["items"][0]["points_m"]
        c = (sum(p[0] for p in apt) / len(apt), sum(p[1] for p in apt) / len(apt))
        d.line([(ex, ey), to_px(c)], fill=(255, 90, 200, 230), width=2)
        d.line(lot + lot[:1], fill=(255, 255, 255, 255), width=3)
        d.polygon(house, fill=(255, 255, 255, 150))
        d.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(80, 230, 255, 255))
        date = scene["properties"]["datetime"][:10]
        d.rectangle([0, 0, w_px, 24], fill=(0, 0, 0, 150))
        d.text((8, 4), f"Sentinel-2, {date}", font=font, fill=(255, 255, 255))
        d.text((w_px - 30, 30), "N", font=font, fill=(255, 255, 255))
        d.line([(w_px - 25, 70), (w_px - 25, 50)], fill=(255, 255, 255), width=2)
        d.polygon([(w_px - 25, 46), (w_px - 30, 56), (w_px - 20, 56)], fill=(255, 255, 255))
        panels.append(im)

    legend = [
        ((255, 255, 255), "Our lot and house"),
        ((80, 230, 255), "From the back-yard eye through the ends of our back line: trees on the line hide only what's between"),
        ((255, 90, 200), "From the back-yard eye to Apartments 7/8"),
        ((255, 150, 60), "Retail lot 1A"),
        ((255, 220, 90), "Apartment lot 2A"),
        ((140, 200, 255), "Planned buildings"),
    ]
    note = ("Dark green is tree canopy. Pixels are 10 m (33 ft), so single trees don't show. "
            "Contains modified Copernicus Sentinel data.")
    gap, pad, line_h = 8, 10, 19
    W = w_px * 2 + gap
    H = h_px + pad * 2 + line_h * (len(legend) + 1)
    sheet = Image.new("RGB", (W, H), (24, 30, 27))
    sheet.paste(panels[0], (0, 0))
    sheet.paste(panels[1], (w_px + gap, 0))
    d = ImageDraw.Draw(sheet)
    yy = h_px + pad
    for color, text in legend:
        d.rectangle([pad, yy + 5, pad + 18, yy + 9], fill=color)
        d.text((pad + 26, yy), text, font=small, fill=(225, 230, 226))
        yy += line_h
    d.text((pad, yy), note, font=small, fill=(165, 178, 170))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    click.echo(f"wrote {out.relative_to(REPO) if out.is_relative_to(REPO) else out}: "
               f"{scenes[0]['properties']['datetime'][:10]} and {scenes[1]['properties']['datetime'][:10]}")


if __name__ == "__main__":
    main()
