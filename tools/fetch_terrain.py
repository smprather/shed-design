# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "numpy", "pyproj", "tifffile"]
# ///
"""Fetch USGS 3DEP lidar ground heights and resample them onto the 3D plan's grid.

The plan's frame (property_total_plan.jsonc) is meters from the midpoint of our platted back
line: x along it toward US-290, y away from our lot. Its origin and x direction are fixed
below by two lon/lat points, placed from the Travis CAD parcel map. One exportImage request
to the 3DEP ImageServer returns the 1 m bare-earth DEM for the area in UTM 14N; this samples
it bilinearly at every grid node and writes site/terrain-lidar.json (feet, NAVD88).

The DEM here is from Feb 2017, before the retail and apartment sites were graded.

Run: uv run tools/fetch_terrain.py
"""

import io
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rich_click as click
import tifffile
from pyproj import Transformer

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "site" / "terrain-lidar.json"
SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
ORIGIN_LONLAT = (-97.8987352, 30.2303111)  # midpoint of the platted back line (parcel map)
X_AXIS_LONLAT = (-97.8986859, 30.2303906)  # 10 m along the back line toward US-290
Z0_FT = 1048.7  # ground at the origin (2017 lidar); z = 0 in the plan
M_TO_FT = 1 / 0.3048

# Same lon/lat <-> local-feet conversion the rest of the plan used when it was placed.
LAT0 = 30.2300
KX = 364000 * math.cos(math.radians(LAT0))
KY = 364000.0


def _ft(lonlat):
    return ((lonlat[0] + 97.8975) * KX, (lonlat[1] - LAT0) * KY)


_O = _ft(ORIGIN_LONLAT)
_A = _ft(X_AXIS_LONLAT)
_L = math.dist(_O, _A)
_EX = ((_A[0] - _O[0]) / _L, (_A[1] - _O[1]) / _L)
_EY = (-_EX[1], _EX[0])  # x turned 90 deg CCW: away from our lot


def plan_to_lonlat(x: float, y: float) -> tuple[float, float]:
    xf, yf = x * M_TO_FT, y * M_TO_FT
    e = _O[0] + xf * _EX[0] + yf * _EY[0]
    n = _O[1] + xf * _EX[1] + yf * _EY[1]
    return (e / KX - 97.8975, n / KY + LAT0)


def lonlat_to_plan(lon, lat):
    """Inverse of plan_to_lonlat; also works elementwise on numpy arrays."""
    dx, dy = (lon + 97.8975) * KX - _O[0], (lat - LAT0) * KY - _O[1]
    return ((dx * _EX[0] + dy * _EX[1]) / M_TO_FT, (dx * _EY[0] + dy * _EY[1]) / M_TO_FT)


@click.command()
@click.option("--x", "xr", nargs=2, type=float, default=(-590.0, 70.0), show_default=True, help="x range (m).")
@click.option("--y", "yr", nargs=2, type=float, default=(-110.0, 370.0), show_default=True, help="y range (m).")
@click.option("--spacing", default=5.0, show_default=True, help="Grid spacing (m).")
def main(xr: tuple[float, float], yr: tuple[float, float], spacing: float) -> None:
    """Download the DEM and write the plan-frame terrain grid."""
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32614", always_xy=True)
    corners = [to_utm.transform(*plan_to_lonlat(x, y)) for x in xr for y in yr]
    e0, e1 = min(c[0] for c in corners) - 10, max(c[0] for c in corners) + 10
    n0, n1 = min(c[1] for c in corners) - 10, max(c[1] for c in corners) + 10
    w, h = math.ceil(e1 - e0), math.ceil(n1 - n0)  # 1 m pixels
    q = {"bbox": f"{e0},{n0},{e0 + w},{n0 + h}", "bboxSR": 32614, "imageSR": 32614, "size": f"{w},{h}",
         "format": "tiff", "pixelType": "F32", "noData": -9999,
         "interpolation": "RSP_BilinearInterpolation", "f": "image"}
    click.echo(f"requesting {w} x {h} m of 1 m DEM")
    with urllib.request.urlopen(SERVICE + "?" + urllib.parse.urlencode(q), timeout=300) as r:
        dem = tifffile.imread(io.BytesIO(r.read())).astype(float)
    if dem.shape != (h, w):
        raise click.ClickException(f"unexpected DEM shape {dem.shape}, wanted {(h, w)}")
    if (dem < -1000).any():
        raise click.ClickException("the DEM has holes (no-data pixels) in this area")

    def sample(e: float, n: float) -> float:
        # pixel centers: column c at e0 + c + 0.5, row r at n1 - r - 0.5
        fc, fr = e - e0 - 0.5, (n0 + h) - n - 0.5
        c, r = int(math.floor(fc)), int(math.floor(fr))
        tc, tr = fc - c, fr - r
        z = dem[r:r + 2, c:c + 2]
        return float((1 - tr) * ((1 - tc) * z[0, 0] + tc * z[0, 1]) + tr * ((1 - tc) * z[1, 0] + tc * z[1, 1]))

    xs = [round(xr[0] + i * spacing, 3) for i in range(int(round((xr[1] - xr[0]) / spacing)) + 1)]
    ys = [round(yr[0] + j * spacing, 3) for j in range(int(round((yr[1] - yr[0]) / spacing)) + 1)]
    grid = [[round(sample(*to_utm.transform(*plan_to_lonlat(x, y))) * M_TO_FT, 1) for x in xs] for y in ys]

    meta = {
        "description": "Bare-earth ground elevations in the frame of property_total_plan.jsonc.",
        "source": "USGS 3DEP 1 m DEM (lidar acquired Feb 2017) from the 3DEPElevation ImageServer, "
                  "resampled bilinearly by tools/fetch_terrain.py",
        "frame": "x m along our platted back line toward US-290, y m square to it away from our lot; "
                 "origin at the back line's midpoint as placed by the Travis CAD parcel map",
        "origin_lonlat": list(ORIGIN_LONLAT),
        "x_axis_point_lonlat_10m": list(X_AXIS_LONLAT),
        "z_datum": "ft NAVD88",
        "z0_ft": Z0_FT,
        "accuracy": "+/-2 ft, mostly from where the parcel map puts the lot",
        "caveat": "Pre-construction: beyond the back line (y > 0) the retail and apartment sites have since been graded.",
    }
    lines = ["{"] + [f"  {json.dumps(k)}: {json.dumps(v)}," for k, v in meta.items()]
    lines += [f'  "x_m": {json.dumps(xs)},', f'  "y_m": {json.dumps(ys)},', '  "z_ft": [']
    lines.append(",\n".join(f"    {json.dumps(row)}" for row in grid))
    lines += ["  ]", "}"]
    OUT.write_text("\n".join(lines) + "\n")
    click.echo(f"wrote {OUT.relative_to(REPO)}: {len(xs)} x {len(ys)} nodes at {spacing:g} m; "
               f"ground {min(map(min, grid)):.0f}-{max(map(max, grid)):.0f} ft")


if __name__ == "__main__":
    main()
