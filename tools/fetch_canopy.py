# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "pyproj", "rasterio", "tifffile", "laspy[lazrs]"]
# ///
"""Tree heights from the 2017 USGS lidar point cloud, masked to the trees still standing.

1. Reads the USGS 3DEP point cloud (project TX_Central_B1_2017, Entwine tiles in the
   public AWS archive) over the area around the lot. Points come pre-classified, and the
   vegetation classes (low, medium, high) are the trees and shrubs.
2. Grids the points in the plan frame at 1 m. Canopy height is the highest vegetation
   return in each cell minus the ground from site/terrain-lidar.json (the same survey's
   bare-earth model).
3. Keeps the cells that are still green in the latest clear Sentinel-2 scene (NDVI). That
   drops the trees cleared for the retail and apartment sites since 2017. Sentinel pixels
   are 10 m, so the edge of a clearing is only good to about that.

Writes site/canopy-lidar.json.

Run: uv run tools/fetch_canopy.py
"""

import base64
import io
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import laspy
import numpy as np
import rasterio
import rich_click as click
from pyproj import Transformer
from rasterio.windows import from_bounds

from fetch_terrain import lonlat_to_plan, plan_to_lonlat
from plan3d import FT, TERRAIN, Terrain
from sentinel_view import search
from site_plan import REPO

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_TX_Central_B1_2017_LAS_2019/"
VEGETATION = (3, 4, 5)  # ASPRS classes: low, medium and high vegetation
MIN_HEIGHT = 2.0  # m; lower vegetation is shrubs and grass
SPIKE = 4.0  # m; a cell this far above its 3x3 median is a stray return (bird, wire) and is clipped to it
NDVI_STANDING = 0.35  # woods read ~0.7 here in October 2026; cleared ground ~0.1
H_STEP = 0.2  # m per stored unit (uint8, so up to 51 m)
OUT = REPO / "site" / "canopy-lidar.json"


def fetch(path: str) -> bytes:
    for k in range(5):
        try:
            return urllib.request.urlopen(EPT + path, timeout=120).read()
        except OSError:
            if k == 4:
                raise
            time.sleep(2 ** k)
    raise AssertionError


def lidar_points(box: tuple[float, float, float, float]) -> np.ndarray:
    """Points (x, y, z NAVD88 m, class) inside a Web Mercator box, from every EPT node over it."""
    meta = json.loads(fetch("ept.json"))
    b = meta["bounds"]
    size0 = b[3] - b[0]
    hier: dict[str, int] = json.loads(fetch("ept-hierarchy/0-0-0-0.json"))
    keys: list[str] = []

    def walk(d: int, x: int, y: int, z: int) -> None:
        key = f"{d}-{x}-{y}-{z}"
        if key not in hier:
            return
        if hier[key] == -1:  # this subtree's counts live in their own file
            hier.update(json.loads(fetch(f"ept-hierarchy/{key}.json")))
        if hier[key] <= 0:
            return
        s = size0 / 2 ** d
        x0, y0 = b[0] + x * s, b[1] + y * s
        if x0 > box[2] or x0 + s < box[0] or y0 > box[3] or y0 + s < box[1]:
            return
        keys.append(key)
        for i in range(8):
            walk(d + 1, 2 * x + (i & 1), 2 * y + (i >> 1 & 1), 2 * z + (i >> 2))

    walk(0, 0, 0, 0)

    def read(key: str) -> np.ndarray:
        las = laspy.read(io.BytesIO(fetch(f"ept-data/{key}.laz")))
        x, y = np.asarray(las.x), np.asarray(las.y)
        m = (x >= box[0]) & (x <= box[2]) & (y >= box[1]) & (y <= box[3])
        return np.c_[x[m], y[m], np.asarray(las.z)[m], np.asarray(las.classification)[m]]

    with ThreadPoolExecutor(8) as ex:
        return np.vstack(list(ex.map(read, keys)))


def ndvi_at(scene: dict, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Sentinel-2 NDVI at plan points (nearest 10 m pixel)."""
    lon, lat = plan_to_lonlat(X, Y)
    E, N = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True).transform(lon, lat)
    out = {}
    for band in ("red", "nir"):
        with rasterio.open("/vsicurl/" + scene["assets"][band]["href"]) as src:
            w = from_bounds(E.min() - 20, N.min() - 20, E.max() + 20, N.max() + 20, src.transform)
            a = src.read(1, window=w).astype(float)
            tr = src.window_transform(w)
        out[band] = a[((N - tr.f) / tr.e).astype(int), ((E - tr.c) / tr.a).astype(int)]
    return (out["nir"] - out["red"]) / (out["nir"] + out["red"] + 1e-9)


def pack(a: np.ndarray) -> str:
    return base64.b64encode(a.astype(np.uint8).tobytes()).decode()


@click.command()
@click.option("--x", "xr", nargs=2, type=float, default=(-300.0, 80.0), show_default=True, help="Plan x range (m).")
@click.option("--y", "yr", nargs=2, type=float, default=(-110.0, 330.0), show_default=True, help="Plan y range (m).")
@click.option("--out", type=click.Path(path_type=Path), default=OUT, show_default=True)
def main(xr: tuple[float, float], yr: tuple[float, float], out: Path) -> None:
    """Grid the lidar canopy and mask it to what's still green now."""
    to3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    corners = [to3857.transform(*plan_to_lonlat(x, y)) for x in xr for y in yr]
    box = (min(c[0] for c in corners), min(c[1] for c in corners), max(c[0] for c in corners), max(c[1] for c in corners))
    pts = lidar_points(box)
    lon, lat = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform(pts[:, 0], pts[:, 1])
    px, py = lonlat_to_plan(lon, lat)
    ground = Terrain(TERRAIN)
    z0 = ground.z0 * FT

    nx, ny = int(xr[1] - xr[0]), int(yr[1] - yr[0])
    col = np.floor(px - xr[0]).astype(int)
    row = np.floor(py - yr[0]).astype(int)
    veg = np.isin(pts[:, 3], VEGETATION) & (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
    top = np.full(ny * nx, -np.inf)
    np.maximum.at(top, row[veg] * nx + col[veg], pts[veg, 2] - z0)
    xs, ys = xr[0] + 0.5 + np.arange(nx), yr[0] + 0.5 + np.arange(ny)
    X, Y = np.meshgrid(xs, ys)
    gz = np.array([ground(x, y) for x, y in zip(X.ravel(), Y.ravel())])
    h = np.where(np.isfinite(top), top - gz, 0.0)
    h = np.where(h >= MIN_HEIGHT, h, 0.0).reshape(ny, nx)
    med = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(h, 1, mode="edge"), (3, 3)), axis=(2, 3))
    h = np.minimum(h, med + SPIKE)

    scene = search("2025-01-01", "2100-01-01")[-1]
    ndvi = ndvi_at(scene, X, Y)
    standing = ndvi >= NDVI_STANDING
    cover17, cover_now = (h > 0).mean(), ((h > 0) & standing).mean()
    data = {
        "description": "Tree canopy height above ground, 1 m cells in the plan frame, from the 2017 USGS lidar; "
                       "standing marks cells still green in the Sentinel-2 scene named below.",
        "lidar": "USGS 3DEP TX_Central_B1_2017 point cloud (vegetation classes 3-5), via Entwine tiles on AWS",
        "sentinel_scene": scene["id"], "ndvi_standing": NDVI_STANDING, "min_height_m": MIN_HEIGHT,
        "x0": xr[0], "y0": yr[0], "cell": 1.0, "nx": nx, "ny": ny, "h_step_m": H_STEP,
        "h": pack(np.clip(np.round(h / H_STEP), 0, 255)), "standing": pack(standing),
        "note": "Rows run from y0 upward, columns from x0. Heights are 2017; live oaks have grown a little since.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data))
    click.echo(f"{len(pts):,} lidar points; canopy over {cover17:.0%} of the box in 2017, {cover_now:.0%} still standing "
               f"({scene['properties']['datetime'][:10]}); tallest {h.max() / FT:.0f} ft")
    click.echo(f"wrote {out.relative_to(REPO) if out.is_relative_to(REPO) else out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
