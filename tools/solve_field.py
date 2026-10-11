# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Turn the laser readings in site/field-data.json into positions on the site grid.

Local frame: origin at A (the house's NW wall corner), u along the north wall toward B,
v square off the wall away from the house (toward US-290). Reference points come from
the shots themselves; targets are located by least squares from their distances, with
trunk shots moved to the trunk center using the measured girth. Results go to
site/field-points.json (local and site-grid coordinates) for the maps to draw.

Run: uv run tools/solve_field.py
"""

import json
import math
import re

from site_plan import HOUSE, REPO

DATA = REPO / "site" / "field-data.json"
OUT = REPO / "site" / "field-points.json"

Pt = tuple[float, float]

# Which worksheet field was shot from which reference point.
FIELD_REF = {"a": "A", "b": "B", "c": "C", "f": "F1"}
# side: "north" keeps v > 0, "west"/"east" pick the sign of u, None reports both mirror images.
TARGETS = {
    "big_oak": {"shot": "s09", "girth": ("s11", "g"), "side": "north"},
    # Owner confirmed the septic access pipe is at the plotted spot: the west one, in the open strip.
    "white_pipe": {"shot": "s13p", "side": "west"},
}
# Tape baseline: from A west along the north wall's line. Station s (ft west of A) and
# offset o (ft toward the fence) map straight to the local frame as (-s, o).
BASELINE_POINTS = {
    "blp": "septic access pipe", "bl1": "tank lid 1", "bl2": "tank lid 2",
    "bld1": "drainfield 1", "bld2": "drainfield 2", "bld3": "drainfield 3", "bld4": "drainfield 4",
    "blw": "well", "blx": "other",
}
FENCE_STATIONS = (0, 25, 50, 75, 100)

# The big oak has twin trunks ~8 ft apart (owner). Shots 9-10 went to the trunk nearer the
# house; the second trunk's offset (u, v) is read off the owner's sketch, so treat it as +/-2 ft.
OAK_SECOND_TRUNK = (4.5, 6.6)


def parse_ft(text: str) -> float | None:
    """'44.6', '44', "44' 7\"", '44 ft 7 in', '-3.5', '+12' -> feet."""
    s = (text or "").strip().lower().replace("’", "'").replace("”", '"').replace("−", "-")
    if not s:
        return None
    if s[0] in "+-":
        v = parse_ft(s[1:])
        return None if v is None else (-v if s[0] == "-" else v)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:'|ft|feet|-|\s)\s*(\d+(?:\.\d+)?)\s*(?:\"|in|inches)?", s)
    if m:
        return float(m[1]) + float(m[2]) / 12
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:'|ft|feet)?", s)
    return float(m[1]) if m else None


def reading(data: dict, shot: str, key: str) -> float | None:
    return parse_ft(data.get(shot, {}).get("fields", {}).get(key, ""))


def two_circle(p: Pt, rp: float, q: Pt, rq: float) -> list[Pt]:
    """Both intersections of two circles (empty if they don't meet)."""
    d = math.dist(p, q)
    a = (rp**2 - rq**2 + d**2) / (2 * d)
    h2 = rp**2 - a**2
    if h2 < 0:
        h2 = 0.0  # tangent within measurement error
    h = math.sqrt(h2)
    ex, ey = (q[0] - p[0]) / d, (q[1] - p[1]) / d
    mx, my = p[0] + a * ex, p[1] + a * ey
    return [(mx - h * ey, my + h * ex), (mx + h * ey, my - h * ex)]


def refine(start: Pt, obs: list[tuple[Pt, float]], iters: int = 20) -> Pt:
    """Gauss-Newton least squares on distance residuals."""
    x, y = start
    for _ in range(iters):
        jtj = [[0.0, 0.0], [0.0, 0.0]]
        jtr = [0.0, 0.0]
        for (px, py), r in obs:
            d = math.hypot(x - px, y - py) or 1e-9
            j = ((x - px) / d, (y - py) / d)
            res = d - r
            for i in range(2):
                jtr[i] += j[i] * res
                for k in range(2):
                    jtj[i][k] += j[i] * j[k]
        det = jtj[0][0] * jtj[1][1] - jtj[0][1] * jtj[1][0]
        if abs(det) < 1e-12:
            break
        dx = (jtj[1][1] * jtr[0] - jtj[0][1] * jtr[1]) / det
        dy = (jtj[0][0] * jtr[1] - jtj[1][0] * jtr[0]) / det
        x, y = x - dx, y - dy
        if math.hypot(dx, dy) < 1e-6:
            break
    return (x, y)


def pick(cands: list[Pt], side: str | None) -> list[Pt]:
    rule = {"north": lambda p: p[1] > 0, "west": lambda p: p[0] < 0, "east": lambda p: p[0] > 0}
    if side is None:
        return cands
    keep = [p for p in cands if rule[side](p)]
    return keep or cands


def to_site(p: Pt) -> Pt:
    a, b = HOUSE[4], HOUSE[5]  # NW corner (A) and NE corner (B) of the north wall
    L = math.dist(a, b)
    e = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (e[1], -e[0])  # away from the house (site y grows southward)
    return (a[0] + p[0] * e[0] + p[1] * n[0], a[1] + p[0] * e[1] + p[1] * n[1])


def main() -> None:
    data = json.loads(DATA.read_text())
    refs: dict[str, Pt] = {"A": (0.0, 0.0)}
    ab = reading(data, "s01", "d")
    if ab:
        refs["B"] = (ab, 0.0)
    if (ac := reading(data, "s02", "d")):
        refs["C"] = (0.0, -ac)
    if (af1 := reading(data, "s03", "d")):
        refs["F1"] = (0.0, af1)
    if ab and (bf2 := reading(data, "s04", "d")):
        refs["F2"] = (ab, bf2)
    if "F1" in refs and (af3 := reading(data, "s05", "d")) and (f1f3 := reading(data, "s06", "d")):
        refs["F3"] = pick(two_circle(refs["A"], af3, refs["F1"], f1f3), "west")[0]

    out: dict[str, dict] = {k: {"local": v, "site": to_site(v)} for k, v in refs.items()}
    for name, spec in TARGETS.items():
        fields = data.get(spec["shot"], {}).get("fields", {})
        add = 0.0
        if "girth" in spec:
            g = reading(data, *spec["girth"])
            add = g / (2 * math.pi) if g else 0.0
        obs = [(refs[FIELD_REF[k]], parse_ft(v) + add) for k, v in fields.items()
               if k in FIELD_REF and FIELD_REF[k] in refs and parse_ft(v)]
        if len(obs) < 2:
            continue
        cands = pick(two_circle(obs[0][0], obs[0][1], obs[1][0], obs[1][1]), spec["side"])
        sols = []
        for c in cands:
            p = refine(c, obs) if len(obs) > 2 else c
            resid = {FIELD_REF[k]: round(math.dist(p, refs[FIELD_REF[k]]) - (parse_ft(v) + add), 2)
                     for k, v in fields.items() if k in FIELD_REF and FIELD_REF[k] in refs and parse_ft(v)}
            sols.append({"local": p, "site": to_site(p), "residuals": resid})
        out[name] = {"solutions": sols, "trunk_radius": add or None, "ambiguous": len(sols) > 1}

    if "big_oak" in out:
        u, v = out["big_oak"]["solutions"][0]["local"]
        p = (u + OAK_SECOND_TRUNK[0], v + OAK_SECOND_TRUNK[1])
        g2 = reading(data, "s11", "g2")
        out["big_oak_2"] = {"solutions": [{"local": p, "site": to_site(p), "residuals": {}}],
                            "trunk_radius": g2 / (2 * math.pi) if g2 else None, "ambiguous": False,
                            "note": "second trunk, offset from the owner's sketch (+/-2 ft)"}

    tape_fence = []
    for st_ft in FENCE_STATIONS:
        o = reading(data, "blf", f"o{st_ft}")
        if o is not None:
            p = (-float(st_ft), o)
            tape_fence.append({"local": p, "site": to_site(p)})
    if tape_fence:
        out["tape_fence"] = tape_fence
    tape_points = {}
    for doc_id, label in BASELINE_POINTS.items():
        s_ft, o = reading(data, doc_id, "s"), reading(data, doc_id, "o")
        if s_ft is not None and o is not None:
            p = (-s_ft, o)
            tape_points[doc_id] = {"label": label, "local": p, "site": to_site(p),
                                   "note": data.get(doc_id, {}).get("note", "")}
    if tape_points:
        out["tape_points"] = tape_points

    def rnd(o):
        if isinstance(o, float):
            return round(o, 2)
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        if isinstance(o, dict):
            return {k: rnd(v) for k, v in o.items()}
        return o

    OUT.write_text(json.dumps(rnd(out), indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}")
    for k, v in out.items():
        if k == "tape_fence":
            print("  tape fence:", ", ".join(f"({p['local'][0]:.0f}, {p['local'][1]:.1f})" for p in v))
            continue
        if k == "tape_points":
            for d in v.values():
                print(f"  tape {d['label']}: {-d['local'][0]:.1f} ft west of A, {d['local'][1]:.1f} ft out")
            continue
        if "solutions" in v:
            for s in v["solutions"]:
                u, w = s["local"]
                print(f"  {k}: {u:6.1f} ft along the wall from A, {w:6.1f} ft out; residuals {rnd(s['residuals'])}")
        else:
            u, w = v["local"]
            print(f"  {k}: {u:6.1f}, {w:6.1f}")


if __name__ == "__main__":
    main()
