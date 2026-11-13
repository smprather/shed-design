# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "pillow", "numpy", "shapely", "contourpy"]
# ///
"""Is a 10 ft sealed wall on the north line worth it? Traffic noise and sight lines from US-290 (owner, Nov 13 2026).

The highway is the rebuilt section in us290_layout.py: the eastbound frontage road by our fence, the main lanes down in
a cut behind its barrier, and the westbound frontage road up the far bank. Each lane is a row of incoherent point
sources (tires at 2 ft, engines and truck stacks at 12 ft) along the road, which runs parallel to our north line west
of the drawn stretch. Each path from a source to a receiver is cut by the barriers it crosses: the highway's barrier
at the cut, the median barrier, the westbound guardrail, our fences. Over the top, ISO 9613-2's barrier term in octave
bands (one edge, or the two that matter most); through a fence, its transmission loss (mass law, derated 5 dB and
capped at 40, with its gaps letting sound straight through). The bands are weighted by the standard A-weighted
traffic spectrum (EN 1793-3). Ground effect, trees, wind and reflections are left out, so read the results as
comparisons between options; a barrier also takes away some of the soft ground's attenuation, so real gains at the
ground floor run ~1-3 dB under these.

Indoors, each fence option is combined with window options: the north wall's sound insulation is the windows' and the
wall's, by area, so a window upgrade and a fence add up in dB, band by band. Today's windows are single panes of
ordinary glass in old sashes (owner), which leak some air. Absolute levels are pinned to TxDOT's
Oak Hill Parkway noise study, which predicted 64 dB(A) (2040 peak hour) at this house (receiver R234), with no fence.

Sight lines: the share of each road, within each window's view (60 degrees either side of straight out, out to 800
ft), where a car's roof (5 ft) or a truck's top (13 ft) shows over everything in between.

Run: uv run tools/fence_noise.py [--gaps 0.03] [--main-db 11] [--window-leak 0.003]
"""

import math

import numpy as np
import polars as pl
import rich_click as click

from house_layout import FF_FT
from plan3d import FT, TERRAIN, Frame, Terrain
from site_plan import BUILDING_LINE, FENCE_TRACE, PARCEL, site, st
from us290_layout import HWY_BARRIER, HWY_STATIONS, HWY_Z, hwy_frame, hwy_offsets

BANDS = np.array([125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0])
TRAFFIC_A = np.array([-14.5, -10.1, -7.2, -3.9, -6.4, -11.4])   # EN 1793-3 traffic spectrum, A-weighted, octaves
LAMBDA = 1125.0 / BANDS                                           # ft
SUBSOURCES = ((2.0, 0.8), (12.0, 0.2))                            # height over the road (ft), share of the energy
STATIONS = np.arange(-2500.0, 2501.0, 20.0)                       # ft along the road
TXDOT_DBA = 64.0                                                  # R234, 2040 peak hour, no fence (TxDOT 2018)

# Panels: surface mass (kg/m2) and open fraction. 3/4 in cedar ~7 kg/m2; 1 lb/sq ft MLV ~4.9 kg/m2.
PICKETS = 7.0
MLV = 4.9

# Windows and walls, sound transmission loss by octave (dB), typical published values. Today's windows are single
# panes of ordinary glass (owner, Nov 13 2026), in old sashes that leak some air (--window-leak); the upgrades are taken
# as sealed. The north rooms' windows are small (the high bands upstairs, the short windows in the stone): ~12% of the
# exposed wall.
TODAY_GLAZING = "today's single pane"
GLAZING = {
    TODAY_GLAZING: np.array([17, 20, 25, 29, 32, 27]),                        # 1/8 in glass, OITC ~23 sealed
    "standard double-pane": np.array([21, 19, 26, 35, 38, 33]),               # 1/8-1/2 air-1/8, OITC ~22-24
    "laminated double-pane": np.array([24, 27, 33, 39, 41, 45]),              # 1/4 lam-1/2-1/8, OITC ~30
    "insert over the single pane": np.array([27, 35, 44, 50, 52, 53]),        # a sealed second pane 3-4 in inside, OITC ~38-40
}
WALL = np.array([33, 38, 45, 50, 52, 53])                                    # sided frame wall, insulated
WINDOW_SHARE = 0.12


def a_level(band_energy: np.ndarray) -> float:
    return 10 * math.log10(float(np.sum(band_energy)))


def panel_tl(mass: float, open_frac: float) -> np.ndarray:
    """A fence panel's transmission loss by band: mass law, derated, capped; its gaps pass sound straight through."""
    tl = np.clip(20 * np.log10(mass * BANDS) - 47 - 5, 0, 40)
    return -10 * np.log10((1 - open_frac) * 10 ** (-tl / 10) + open_frac)


def facade_tl(glazing: np.ndarray, leak: float = 0.0) -> np.ndarray:
    """The north wall's transmission loss: the windows (with `leak` of their area open) and the wall, by area."""
    window = -10 * np.log10((1 - leak) * 10 ** (-glazing / 10) + leak)
    return -10 * np.log10(WINDOW_SHARE * 10 ** (-window / 10) + (1 - WINDOW_SHARE) * 10 ** (-WALL / 10))


def iso_dz(z: np.ndarray, lam: float, e: np.ndarray | None = None) -> np.ndarray:
    """ISO 9613-2 barrier attenuation for path difference z (ft): one edge, or two edges e ft apart."""
    c3 = 1.0 if e is None else (1 + (5 * lam / np.maximum(e, 1e-6)) ** 2) / (1 / 3 + (5 * lam / np.maximum(e, 1e-6)) ** 2)
    arg = 3 + 20 * c3 * z / lam
    d = 10 * np.log10(np.maximum(arg, 1.0))
    return np.where(z > -0.1 * lam, np.minimum(d, 20.0 if e is None else 25.0), 0.0)


class Site:
    """The highway's lanes and edges, our fences and the ground under them, in site ft and ft NAVD88."""

    def __init__(self) -> None:
        self.at, _ = hwy_frame()
        rn, fn = PARCEL[2], PARCEL[1]
        n = math.dist(rn, fn)
        self.line_dir = ((fn[0] - rn[0]) / n, (fn[1] - rn[1]) / n)
        ground, to_m = Terrain(TERRAIN), Frame()
        self.g = lambda p: ground.natural(*to_m(p)) / FT + ground.z0  # noqa: E731
        self.k = hwy_offsets()

    def road(self, s_: float, o: float) -> tuple[float, float]:
        """A point on the highway: the drawn stretch, then parallel to our north line west of it (it must curve)."""
        s0 = HWY_STATIONS[0]
        if s_ >= s0:
            return self.at(s_, o)
        x, y = self.at(s0, o)
        return (x + self.line_dir[0] * (s_ - s0), y + self.line_dir[1] * (s_ - s0))

    def lanes(self) -> list[tuple[str, float, float]]:
        zr, zm, zw = HWY_Z
        k = self.k
        eb = [("eastbound frontage road", o, zr) for o in (8.0, 20.0, 32.0)]
        main = [("main lanes", k["cut"] + o, zm) for o in (16.0, 28.0, 40.0, 60.0, 72.0, 84.0)]
        wb = [("westbound frontage road", k["wb"] + o, zw) for o in (8.0, 20.0, 32.0)]
        return eb + main + wb

    def edges(self) -> list[dict]:
        """The highway's own barriers as polylines (x, y, top z)."""
        zr, zm, zw = HWY_Z
        k = self.k
        out = []
        for o, top in ((HWY_BARRIER[0] + 1.0, zr + HWY_BARRIER[2]), ((k["cut"] + k["wall"]) / 2, zm + 2.7), (k["wb"] + 0.5, zw + 2.3)):
            out.append({"pts": [(*self.road(s_, o), top) for s_ in np.arange(-2600.0, 2601.0, 100.0)], "tl": None})
        return out

    def fence(self, pts: list[tuple[float, float]], height: float, tl: np.ndarray, step: float = 10.0) -> dict:
        """A fence along a site polyline, its top `height` ft over the lidar ground, cut into ~step ft pieces."""
        dense = []
        for a, b in zip(pts, pts[1:]):
            n = max(1, math.ceil(math.dist(a, b) / step))
            dense += [(a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n) for j in range(n)]
        dense.append(pts[-1])
        return {"pts": [(x, y, self.g((x, y)) + height) for x, y in dense], "tl": tl}


def crossings(S: np.ndarray, R: np.ndarray, poly: list[tuple[float, float, float]]):
    """Where the paths S -> R cross a polyline in plan: (crossed, t along the path, the top's height there)."""
    best_ok = np.zeros(len(S), bool)
    best_t = np.zeros(len(S))
    best_top = np.full(len(S), -1e9)
    best_gap = np.full(len(S), -1e9)
    d1 = R[None, :2] - S[:, :2]
    for a, b in zip(poly, poly[1:]):
        d2 = (b[0] - a[0], b[1] - a[1])
        den = d1[:, 0] * d2[1] - d1[:, 1] * d2[0]
        ax, ay = a[0] - S[:, 0], a[1] - S[:, 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ax * d2[1] - ay * d2[0]) / den
            w = (ax * d1[:, 1] - ay * d1[:, 0]) / den
        ok = (np.abs(den) > 1e-9) & (t > 0) & (t < 1) & (w >= 0) & (w <= 1)
        top = a[2] + w * (b[2] - a[2])
        gap = top - (S[:, 2] + t * (R[2] - S[:, 2]))
        take = ok & (gap > best_gap)
        best_ok |= ok
        best_t = np.where(take, t, best_t)
        best_top = np.where(take, top, best_top)
        best_gap = np.where(take, gap, best_gap)
    return best_ok, best_t, best_top


def band_attenuation(S: np.ndarray, R: np.ndarray, barriers: list[dict]) -> np.ndarray:
    """(N, bands) energy factor for each path: over the barriers (one or two edges) plus through any fence."""
    n = len(S)
    dh = np.hypot(R[0] - S[:, 0], R[1] - S[:, 1])
    direct = np.sqrt(dh ** 2 + (R[2] - S[:, 2]) ** 2)
    cr = [crossings(S, R, b["pts"]) for b in barriers]
    k = len(cr)
    if not k:
        return np.ones((n, len(BANDS)))
    ok = np.array([c[0] for c in cr])                       # (k, n)
    xs = np.array([c[1] for c in cr]) * dh                 # horizontal distance from the source to each edge
    tops = np.array([c[2] for c in cr])
    # Single-edge path differences (signed: negative when the straight line clears the top).
    zline = S[None, :, 2] + (xs / np.maximum(dh, 1e-9)) * (R[2] - S[None, :, 2])
    over = np.sqrt(xs ** 2 + (tops - S[None, :, 2]) ** 2) + np.sqrt((dh - xs) ** 2 + (R[2] - tops) ** 2) - direct
    z1 = np.where(ok, np.where(tops > zline, over, -over), -1e9)
    out = np.empty((n, len(BANDS)))
    for bi, lam in enumerate(LAMBDA):
        single = np.where(ok, iso_dz(z1, lam), 0.0)        # (k, n)
        best = single.max(axis=0)
        # The best pair of edges, where both stand above the line between their neighbors.
        for i in range(k):
            for j in range(k):
                if i == j:
                    continue
                first = ok[i] & ok[j] & (xs[i] < xs[j]) & (z1[i] > 0) & (z1[j] > 0)
                if not first.any():
                    continue
                x1, x2, h1, h2 = xs[i], xs[j], tops[i], tops[j]
                above1 = h1 > S[:, 2] + (h2 - S[:, 2]) * x1 / np.maximum(x2, 1e-9)
                above2 = h2 > h1 + (R[2] - h1) * (x2 - x1) / np.maximum(dh - x1, 1e-9)
                e = np.hypot(x2 - x1, h2 - h1)
                z2 = np.hypot(x1, h1 - S[:, 2]) + e + np.hypot(dh - x2, R[2] - h2) - direct
                both = first & above1 & above2
                best = np.where(both, np.maximum(best, iso_dz(z2, lam, e)), best)
        energy = 10 ** (-best / 10)
        # Through each fence the straight path pierces: its transmission, times what the other edges still take off.
        for f, b in enumerate(barriers):
            if b["tl"] is None:
                continue
            pierced = ok[f] & (z1[f] > 0)
            others = np.where(np.arange(k)[:, None] != f, single, 0.0).max(axis=0)
            energy = energy + np.where(pierced, 10 ** (-(b["tl"][bi] + others) / 10), 0.0)
        out[:, bi] = energy
    return out


def sources(site_: Site, main_db: float):
    pts, weights, groups = [], [], []
    lanes = site_.lanes()
    per_group = {"eastbound frontage road": 1.0, "main lanes": 10 ** (main_db / 10), "westbound frontage road": 1.0}
    counts = {g: sum(1 for name, _, _ in lanes if name == g) for g in per_group}
    for name, o, z in lanes:
        for s_ in STATIONS:
            x, y = site_.road(s_, o)
            for h, share in SUBSOURCES:
                pts.append((x, y, z + h))
                weights.append(per_group[name] / counts[name] * share)
                groups.append(name)
    return np.array(pts), np.array(weights), np.array(groups)


def receiver_bands(S, W, R, barriers) -> np.ndarray:
    """(n sources, bands) energy at R, before the traffic spectrum."""
    d2 = (S[:, 0] - R[0]) ** 2 + (S[:, 1] - R[1]) ** 2 + (S[:, 2] - R[2]) ** 2
    return (W / d2)[:, None] * band_attenuation(S, R, barriers)


def table(rows: list[dict], title: str) -> None:
    click.echo(f"\n{title}")
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True,
                   tbl_width_chars=230, fmt_str_lengths=60):
        click.echo(pl.DataFrame(rows))


@click.command()
@click.option("--gaps", default=0.03, show_default=True, help="Open fraction of today's fence (and the rear fence).")
@click.option("--main-db", default=11.0, show_default=True, help="Main lanes (both ways) louder than one frontage road, dB.")
@click.option("--window-leak", default=0.003, show_default=True, help="Open fraction of today's old single-pane windows (air leaks).")
def main(gaps: float, main_db: float, window_leak: float) -> None:
    """Fence options vs today's fence: outdoor and indoor dB, window upgrades, and what each hides of the highway."""
    site_ = Site()
    S, W, G = sources(site_, main_db)
    edges = site_.edges()
    rear = site_.fence([PARCEL[2], PARCEL[3]], 8.0, panel_tl(PICKETS, gaps))
    line = [site([BUILDING_LINE[1]])[0], PARCEL[2]]                     # the north line, building line to back corner
    options = {
        "no fence": [],
        "today: 8 ft, leaky": [site_.fence(FENCE_TRACE, 8.0, panel_tl(PICKETS, gaps))],
        "today's, gaps sealed": [site_.fence(FENCE_TRACE, 8.0, panel_tl(2 * PICKETS, 0.0))],
        "8 ft line, picket-MLV-picket": [site_.fence(line, 8.0, panel_tl(2 * PICKETS + MLV, 0.0))],
        "10 ft line, leaky pickets": [site_.fence(line, 10.0, panel_tl(PICKETS, gaps))],
        "10 ft line, board-on-board": [site_.fence(line, 10.0, panel_tl(2 * PICKETS, 0.0))],
        "10 ft line, picket-MLV-picket": [site_.fence(line, 10.0, panel_tl(2 * PICKETS + MLV, 0.0))],
    }
    north = 91.1                                                        # 1 ft out from the north wall (t 90.1)
    yard = site([st(100.0, 105.0)])[0]
    receivers = {
        "west end, ground floor": (site([st(115.0, north)])[0], FF_FT + 5.0),
        "west end, upstairs": (site([st(115.0, north)])[0], FF_FT + 16.0),
        "middle, ground floor": (site([st(98.0, north)])[0], FF_FT + 5.0),
        "middle, upstairs": (site([st(98.0, north)])[0], FF_FT + 16.0),
        "garage/kitchen end, ground floor": (site([st(75.0, north)])[0], FF_FT + 5.0),
        "north yard, 15 ft off the wall": (yard, site_.g(yard) + 5.0),
    }
    spec = 10 ** (TRAFFIC_A / 10)
    out_levels: dict[tuple[str, str], np.ndarray] = {}
    shares = []
    for rname, (p, z) in receivers.items():
        R = np.array([p[0], p[1], z])
        for oname, fences in options.items():
            e = receiver_bands(S, W, R, edges + [rear] + fences) * spec[None, :]
            out_levels[(rname, oname)] = e.sum(axis=0)
            if oname in ("today: 8 ft, leaky", "10 ft line, picket-MLV-picket"):
                tot = e.sum()
                shares.append({"receiver": rname, "fence": oname,
                               **{g: f"{100 * e[G == g].sum() / tot:.0f}%" for g in ("eastbound frontage road", "main lanes", "westbound frontage road")}})
    # Pin the yard with no fence to TxDOT's figure.
    cal = TXDOT_DBA - a_level(out_levels[("north yard, 15 ft off the wall", "no fence")])
    rows = []
    for rname in receivers:
        today = a_level(out_levels[(rname, "today: 8 ft, leaky")])
        row = {"receiver (outdoors)": rname, "today, dB(A)": round(today + cal, 1)}
        for oname in options:
            if oname != "today: 8 ft, leaky":
                row[oname] = round(today - a_level(out_levels[(rname, oname)]), 1)
        rows.append(row)
    click.echo(f"Traffic noise from US-290 (today's fence {gaps:.0%} open; main lanes {main_db:g} dB over one frontage road). "
               "Comparisons, not predictions: no ground effect, trees or wind.")
    table(rows, "Outdoors at the north wall: today's level (pinned to TxDOT's 64 dB(A) in the yard with no fence), "
                "and dB quieter than today for each option (negative = louder)")
    table(shares, "Where today's sound comes from, and with the 10 ft sealed wall (share of the energy)")
    fband = []
    for rname in ("middle, ground floor", "middle, upstairs"):
        today = out_levels[(rname, "today: 8 ft, leaky")]
        plan_ = out_levels[(rname, "10 ft line, picket-MLV-picket")]
        fband.append({"receiver": rname, **{f"{int(f)} Hz": round(float(10 * np.log10(today[i] / plan_[i])), 1) for i, f in enumerate(BANDS)}})
    table(fband, "The 10 ft sealed wall vs today's fence, by octave band (dB quieter)")
    # Indoors: today's fence and windows vs each combination.
    spectrum_out = out_levels[("middle, ground floor", "today: 8 ft, leaky")]
    trows = []
    for gname, glz in GLAZING.items():
        leak = window_leak if gname == TODAY_GLAZING else 0.0
        trows.append({"windows": gname + (f" ({leak:.1%} open)" if leak else ", sealed"),
                      "traffic noise through the north wall, dB(A)": round(a_level(spectrum_out) - a_level(spectrum_out * 10 ** (-facade_tl(glz, leak) / 10)), 1),
                      **{f"{int(f)} Hz": int(round(float(v))) for f, v in zip(BANDS, -10 * np.log10((1 - leak) * 10 ** (-glz / 10) + leak))}})
    table(trows, "The windows alone (sound transmission loss by octave, dB), and the whole north wall's drop for traffic noise")
    irows = []
    base_tl = facade_tl(GLAZING[TODAY_GLAZING], window_leak)
    for rname in [r for r in receivers if "yard" not in r]:
        today_in = a_level(out_levels[(rname, "today: 8 ft, leaky")] * 10 ** (-base_tl / 10))
        row = {"room (indoors, north wall)": rname, "today, dB(A)": round(today_in + cal, 1),
               "10 ft wall alone": round(today_in - a_level(out_levels[(rname, "10 ft line, board-on-board")] * 10 ** (-base_tl / 10)), 1)}
        for gname, glz in list(GLAZING.items())[1:]:
            ftl = facade_tl(glz)
            for oname, tag in (("today: 8 ft, leaky", ""), ("10 ft line, board-on-board", " + 10 ft wall")):
                row[gname + tag] = round(today_in - a_level(out_levels[(rname, oname)] * 10 ** (-ftl / 10)), 1)
        irows.append(row)
    table(irows, f"Indoors, windows shut: today's level (single panes {window_leak:.1%} open), and dB quieter for each window "
                 f"upgrade, alone and with the 10 ft wall (windows {WINDOW_SHARE:.0%} of the wall; the rest an insulated "
                 "sided wall)")
    # Sight lines.
    vrows = []
    for rname, (p, z) in receivers.items():
        if "garage" in rname:
            continue
        eye = np.array([p[0], p[1], z])
        out_dir = np.array(site([st(100.0, 200.0)])[0]) - np.array(site([st(100.0, 100.0)])[0])
        out_dir = out_dir / np.linalg.norm(out_dir)
        for oname in ("no fence", "today: 8 ft, leaky", "10 ft line, picket-MLV-picket"):
            bars = edges + [rear] + options[oname]
            row = {"view from": rname, "fence": oname}
            for gname, roof in (("eastbound frontage road", 5.0), ("main lanes", 5.0), ("westbound frontage road", 5.0),
                                ("eastbound frontage road", 13.0), ("main lanes", 13.0), ("westbound frontage road", 13.0)):
                lanes = [(o, zz) for name, o, zz in site_.lanes() if name == gname]
                pts = np.array([(*site_.road(s_, o), zz + roof) for o, zz in lanes for s_ in np.arange(-800.0, 800.1, 5.0)])
                v = pts[:, :2] - eye[None, :2]
                dist = np.hypot(v[:, 0], v[:, 1])
                ang = np.degrees(np.arccos(np.clip((v @ out_dir) / dist, -1, 1)))
                inview = (ang <= 60) & (dist <= 800)
                hidden = np.zeros(len(pts), bool)
                for b in bars:
                    okb, _, top = crossings(pts, eye, b["pts"])
                    tb = crossings(pts, eye, b["pts"])[1]
                    hidden |= okb & (top > pts[:, 2] + tb * (eye[2] - pts[:, 2]))
                frac = (inview & ~hidden).sum() / max(inview.sum(), 1)
                row[f"{'cars' if roof < 10 else 'trucks'}: {gname.split(' ')[0]}"] = f"{frac:.0%}"
            vrows.append(row)
    table(vrows, "How much of each road shows (in view: 60 deg either side of straight out, to 800 ft); cars' roofs at 5 ft, "
                 "truck tops at 13 ft")


if __name__ == "__main__":
    main()
