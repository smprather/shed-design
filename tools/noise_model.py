# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow"]
# ///
"""Rough traffic-noise model: how much each barrier option quiets the house and yard.

US-290 is modeled as straight lanes parallel to the surveyed north line, each a row of
incoherent point sources (tires at 2 ft, truck stacks at 12 ft), running far past both ends of
the lot. The road sits `--drop` ft below the lot, and the slope's crest is at the line. Each
source-to-receiver path is cut by the highest barrier edge it crosses (Maekawa /
Kurze-Anderson at 550 Hz, 20 dB cap). Ground effect, trees, wind and reflections are left out,
so read the results as comparisons between options, not as predictions.

What it shows is that a barrier only quiets the stretch of highway it hides. Sound from the
traffic beyond its ends still arrives, which limits a 40 ft building and the east end of a
wall that stops at Candelaria.

Run: uv run tools/noise_model.py
"""

import math

import polars as pl
import rich_click as click

from site_plan import HOUSE, PARCEL

FS, FN, RN = PARCEL[0], PARCEL[1], PARCEL[2]
THETA = math.atan2(FN[1] - RN[1], FN[0] - RN[0])
ALONG = (math.cos(THETA), math.sin(THETA))
INWARD = (-math.sin(THETA), math.cos(THETA))  # into the lot (site y grows southward)
LAMBDA = 1125 / 550  # ft, the usual effective frequency for traffic noise
SOURCES = ((2.0, 0.7), (12.0, 0.3))  # (height above the road ft, share of the energy)
FAR = 1e5

B_EAVE_WALLS = [((152, 131.5), (192, 131.5)), ((192, 131.5), (192, 151.5)),
                ((192, 151.5), (152, 151.5)), ((152, 151.5), (152, 131.5))]


def uv(p) -> tuple[float, float]:
    """Site point -> (along the north line from its west end, distance inside the line)."""
    dx, dy = p[0] - RN[0], p[1] - RN[1]
    return (dx * ALONG[0] + dy * ALONG[1], dx * INWARD[0] + dy * INWARD[1])


LINE_LEN = math.dist(RN, FN)
FRONT_DIR = ((FS[0] - FN[0]) / math.dist(FN, FS), (FS[1] - FN[1]) / math.dist(FN, FS))


def il_edge(delta: float) -> float:
    """Insertion loss (dB) of one thin edge for a signed path difference (ft)."""
    n = 2 * delta / LAMBDA
    x = math.sqrt(2 * math.pi * abs(n))
    if x < 1e-6:
        return 5.0
    if n > 0:
        return min(20.0, 5 + 20 * math.log10(x / math.tanh(x)))
    if n > -0.2:
        return max(0.0, 5 + 20 * math.log10(x / math.tan(x)))
    return 0.0


def cross(s, r, a, b):
    """Parameter t along s->r where it crosses segment a-b in plan, or None."""
    d1 = (r[0] - s[0], r[1] - s[1])
    d2 = (b[0] - a[0], b[1] - a[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - s[0]) * d2[1] - (a[1] - s[1]) * d2[0]) / den
    w = ((a[0] - s[0]) * d1[1] - (a[1] - s[1]) * d1[0]) / den
    return t if 0 < t < 1 and 0 <= w <= 1 else None


def path_il(s, r, barriers) -> float:
    """IL of the dominant edge on the path s -> r. s, r = (u, v, z); barriers = [(a, b, ztop)]."""
    best = 0.0
    sr = math.dist(s, r)
    for a, b, ztop in barriers:
        t = cross(s, r, a, b)
        if t is None:
            continue
        c = (s[0] + t * (r[0] - s[0]), s[1] + t * (r[1] - s[1]))
        zline = s[2] + t * (r[2] - s[2])
        top = (c[0], c[1], ztop)
        delta = math.dist(s, top) + math.dist(top, r) - sr
        best = max(best, il_edge(delta if ztop > zline else -delta))
    return best


def level(r, barriers, lanes, drop, step) -> float:
    """Relative level (dB) at receiver r from all lanes."""
    e = 0.0
    u0 = -3000.0
    while u0 <= LINE_LEN + 3000:
        for d in lanes:
            for h, w in SOURCES:
                s = (u0, -d, -drop + h)
                e += w * step / math.dist(s, r) ** 2 * 10 ** (-path_il(s, r, barriers) / 10)
        u0 += step
    return 10 * math.log10(e)


@click.command()
@click.option("--drop", default=17.5, show_default=True, help="Road below the lot at the line (ft).")
@click.option("--lanes", default="60,73,87,100", show_default=True, help="Lane distances north of the line (ft).")
@click.option("--step", default=4.0, show_default=True, help="Source spacing along the road (ft).")
def main(drop: float, lanes: str, step: float) -> None:
    """Insertion loss vs today (hill + see-through picket fence) for barrier options."""
    lane_d = [float(x) for x in lanes.split(",")]
    crest = [((-FAR, 0.0), (FAR, 0.0), 0.0)]

    def wall(height: float, ret: float = 0.0):
        segs = [((0.0, 0.5), (LINE_LEN, 0.5), height)]
        if ret:
            end = (FN[0] + ret * FRONT_DIR[0], FN[1] + ret * FRONT_DIR[1])
            segs.append((uv(FN), uv(end), height))
        return segs

    def building(eave: float):
        return [(uv(a), uv(b), eave) for a, b in B_EAVE_WALLS]

    a, ne = HOUSE[4], HOUSE[5]
    mid = ((a[0] + ne[0]) / 2, (a[1] + ne[1]) / 2)
    receivers = {}
    for name, p in (("west end (A)", a), ("middle", mid), ("east end (kitchen)", ne)):
        u, v = uv(p)
        receivers[f"House {name}, ground floor"] = (u, v - 1, 5.0)
        receivers[f"House {name}, 2nd floor"] = (u, v - 1, 15.0)
    for name, p in (("Yard right behind B", (172, 158)), ("Yard east of B", (215, 158))):
        u, v = uv(p)
        receivers[name] = (u, v, 5.0)

    scenarios = {
        "B 14 ft eave": building(14),
        "B 18 ft eave": building(18),
        "8 ft wall": wall(8),
        "12 ft wall": wall(12),
        "8 ft wall + B 14": wall(8) + building(14),
        "8 ft wall + 60 ft return": wall(8, 60),
        "12 ft wall + 60 ft return": wall(12, 60),
    }
    rows = []
    for rname, r in receivers.items():
        base = level(r, crest, lane_d, drop, step)
        row = {"receiver": rname, "hill vs flat": round(level(r, [], lane_d, drop, step) - base, 1)}
        for sname, bars in scenarios.items():
            row[sname] = round(base - level(r, crest + bars, lane_d, drop, step), 1)
        rows.append(row)
    df = pl.DataFrame(rows)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_hide_dataframe_shape=True,
                   tbl_hide_column_data_types=True, tbl_width_chars=200, fmt_str_lengths=40):
        click.echo(f"dB quieter than today (road {drop:g} ft below the lot, lanes {lanes} ft out); "
                   "'hill vs flat' = what the slope already does")
        click.echo(df)


if __name__ == "__main__":
    main()
