# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "numpy", "polars", "rich-click", "shapely"]
# ///
"""Drive study: the drive system redesigned from scratch (drive_layout.py) against the trees, septic and lines.

Draws site/drives.png over the aerial and prints:
- clearances from every known trunk and lidar treetop near the drive to its nearest edge;
- grades along each lane (2017 lidar);
- areas by surface, and impervious cover now and with the plan (gravel counted, and not);
- a planning budget, with the same "likely" figure and 80% band as shed_cost.py.

Trees: the twin oak's trunks are laser-placed (field data); the lone lawn oak and the bulge oak are placed from
photos (+/-8 ft); everything else is a lidar treetop (a crown's high point, which can sit several feet off the
trunk on a leaning live oak). Tape the trunks within ~15 ft of a curb before staking anything.

Run: uv run tools/drive_plan.py
"""

import json
import math

import numpy as np
from PIL import Image, ImageDraw
import polars as pl
import rich_click as click
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from drive_layout import (
    APRON_DEEP, COLUMN, COVER_COLUMNS, CURB, NORTH_LEG, PARK, SERVICE_DRIVE, SHOP_COURT_FALL, SHOP_LANE, SOUTH_LEG,
    layout,
)
from envelope_plan import SITE_A
from front_layout import BULGE_OAK, EXISTING_DRIVE, FRONT_ELECTRIC, FRONT_WALK, LONE_OAK_PHOTO, catmull_rom
from front_plan import SurveyFrame, canopy_in_st
from house_layout import DECK
from plan3d import CANOPY, FT, TERRAIN, Canopy, Frame, Terrain, field_features
from site_plan import (
    CYAN, GREEN, ORANGE, PARCEL, RED, REPO, WHITE, YELLOW, Plan, draw_survey, site, st,
)

OUT = REPO / "site" / "drives.png"
NO_DIG = 12.0       # ft around the twin oak's trunks
TREE_FLAG = 10.0    # ft: a drive edge closer than this to a trunk or treetop gets flagged
CONTINGENCY, Z80 = 0.10, 1.2816

# (low, high) dollars per unit, Austin area, Oct 2026: planning ranges, not quotes (sources in site/notes.md).
PRICES = {
    "demo": ((2, 5), "sq ft", "Take out the old drive and front walk, haul off"),
    "concrete": ((10, 16), "sq ft", "Concrete street aprons (to 10 ft inside the line), flared"),
    "permit": ((1000, 4000), "lot", "Travis County driveway permits, two entrances (a culvert if the ditch needs one)"),
    "gravel": ((8, 14), "sq ft", "Gravel drive: compacted base, geotextile, stabilizer grid, 3/8 in angular gravel"),
    "curb": ((15, 35), "ft", "Concrete ribbon curb, 8 x 12 in with rebar, along every gravel edge"),
    "pavers": ((25, 45), "sq ft", "Pavers on a concrete base: under the cover and into the door's recess"),
    "cover": ((90, 180), "sq ft", "Porte-cochere: stone columns, beams, hipped roof tied into the house, gutters, lights"),
    "fill": ((70, 125), "cu yd", "Fill under the shop court, crushed limestone, compacted"),
    "wall": ((60, 120), "ft", "Shop court's retaining edge where it stands above the ground"),
    "arborist": ((500, 1500), "lot", "Arborist: root-zone plan, and on site for digging near the oaks"),
}


def trees(sf: SurveyFrame, to_m: Frame) -> list[dict]:
    """Known trunks and lidar treetops, in (s, t) ft, tallest first."""
    fp = json.loads((REPO / "site" / "field-points.json").read_text())
    out = [{"name": f"twin oak, trunk {i + 1} (laser)", "st": sf.from_site(tuple(fp[k]["solutions"][0]["site"])), "known": True}
           for i, k in enumerate(("big_oak", "big_oak_2")) if fp.get(k, {}).get("solutions")]
    out += [{"name": "lone lawn oak (photo)", "st": LONE_OAK_PHOTO, "known": True},
            {"name": "bulge oak (photos)", "st": BULGE_OAK, "known": True}]
    can = Canopy(CANOPY)
    h = can.h
    win = np.lib.stride_tricks.sliding_window_view(np.pad(h, 3), (7, 7)).max(axis=(2, 3))
    tops = []
    for r, c in sorted(np.argwhere((h == win) & (h >= 4.0)), key=lambda rc: -h[rc[0], rc[1]]):
        x, y = can.x0 + c + 0.5, can.y0 + r + 0.5
        if all((x - q[0]) ** 2 + (y - q[1]) ** 2 > 9 for q in tops):
            tops.append((x, y, float(h[r, c])))
    for x, y, hh in tops:
        out.append({"name": f"lidar treetop, {hh / FT:.0f} ft", "st": sf.from_site(to_m.to_site((x, y))), "known": False})
    return out


def likely(items: list[tuple[float, float]]) -> tuple[float, float, float]:
    mid = sum((a + b) / 2 for a, b in items) * (1 + CONTINGENCY)
    sd = math.sqrt(sum((b - a) ** 2 / 12 for a, b in items)) * (1 + CONTINGENCY)
    return mid, mid - Z80 * sd, mid + Z80 * sd


@click.command()
def main() -> None:
    """Draw the drive study and print its clearances, grades, areas and budget."""
    sf, to_m, ground = SurveyFrame(), Frame(), Terrain(TERRAIN)
    gz = lambda s, t: ground(*to_m(site([st(s, t)])[0])) / FT + ground.z0  # noqa: E731
    L = layout([sf.from_site(p) for p in SITE_A])
    pipe, _, well = field_features()
    pipe, well = sf.from_site(pipe), sf.from_site(well)
    tr = trees(sf, to_m)
    old = Polygon(EXISTING_DRIVE).union(Polygon(FRONT_WALK))

    # --- Map ---
    corners = [site([st(s, t)])[0] for s, t in ((-25, -12), (-25, 168), (232, 168), (232, -12))]
    xs, ys = [p[0] for p in corners], [p[1] for p in corners]
    plan = Plan(view=(int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1))
    plan.grid()
    can = Canopy(CANOPY)
    for s_, t_, hh, r, c in canopy_in_st(can, to_m, sf):
        x, y = can.x0 + c, can.y0 + r
        q = [to_m.to_site(p) for p in ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))]
        plan.d.polygon([plan.p(*p) for p in q], fill=(255, 225, 60, 28))
    draw_survey(plan)
    S = lambda pts: site(st(*q) for q in pts)  # noqa: E731

    def shape(g, outline, fill, width=2):
        """A shapely area: filled on its own layer, so holes (loop D's island) stay clear, then outlined."""
        layer = Image.new("RGBA", plan.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        polys = [poly for poly in getattr(g, "geoms", [g]) if not poly.is_empty]
        for poly in polys:
            d.polygon([plan.p(*q) for q in S(list(poly.exterior.coords)[:-1])], fill=fill)
            for hole in poly.interiors:
                d.polygon([plan.p(*q) for q in S(list(hole.coords)[:-1])], fill=(0, 0, 0, 0))
        plan.img = Image.alpha_composite(plan.img.convert("RGBA"), layer).convert("RGB")
        plan.d = ImageDraw.Draw(plan.img, "RGBA")
        for poly in polys:
            plan.poly(S(list(poly.exterior.coords)[:-1]), outline, width=width)
            for hole in poly.interiors:
                plan.poly(S(list(hole.coords)[:-1]), outline, width=width)

    plan.poly(S(EXISTING_DRIVE), (235, 235, 225), width=2, dash=True)
    plan.poly(S(FRONT_WALK), (235, 235, 225), width=2, dash=True)
    shape(L["gravel"], (214, 190, 140), (222, 200, 150, 205))
    shape(L["paved"], (196, 160, 130), (196, 160, 130, 190))
    shape(L["concrete"], (200, 200, 195), (200, 200, 195, 210))
    for ln in getattr(L["curbs"], "geoms", [L["curbs"]]):
        plan.line(S(list(ln.coords)), (240, 240, 235), width=3)
    shape(L["apron"], (200, 200, 195), (200, 200, 195, 210))
    shape(L["building"], (90, 95, 100), (60, 65, 70, 220), width=3)
    shape(L["cover"], (120, 80, 60), (150, 100, 70, 90), width=3)
    for s_, t_ in COVER_COLUMNS:
        h = COLUMN / 2
        plan.poly(S([(s_ - h, t_ - h), (s_ + h, t_ - h), (s_ + h, t_ + h), (s_ - h, t_ + h)]), WHITE, fill=(225, 215, 195, 255), width=1)
    for t0, t1 in PARK:
        plan.poly(S([(46.0, t0), (52.5, t0), (52.5, t1), (46.0, t1)]), WHITE, width=1, dash=True)
    # A's doors, on its south wall
    A = L["A"]
    for x0, x1 in ((2.5, 14.5), (16.0, 19.0), (20.5, 32.5)):
        plan.line(S([A(x0, 0), A(x1, 0)]), ORANGE, width=6)
    # trees: known trunks with their keep-outs, treetops as dots
    for t in tr:
        s_, t_ = t["st"]
        if not (-25 < s_ < 232 and -12 < t_ < 168):
            continue
        cx, cy = plan.p(*site([st(s_, t_)])[0])
        if t["known"]:
            r = NO_DIG if "twin" in t["name"] else 12.0
            ring = [(s_ + r * math.cos(k / 36 * 2 * math.pi), t_ + r * math.sin(k / 36 * 2 * math.pi)) for k in range(37)]
            plan.line(S(ring), GREEN, width=3, dash=True)
            plan.d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=GREEN, outline=WHITE, width=2)
        else:
            plan.d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(60, 170, 60), outline=WHITE, width=1)
    for p, r, col in ((pipe, 10.0, RED), (well, 10.0, CYAN)):
        ring = [(p[0] + r * math.cos(k / 36 * 2 * math.pi), p[1] + r * math.sin(k / 36 * 2 * math.pi)) for k in range(37)]
        plan.line(S(ring), col, width=3, dash=True)
    plan.line(S(FRONT_ELECTRIC), YELLOW, width=2, dash=True)
    meter = sf.from_site(to_m.to_site((22.6, -1.0)))
    plan.line(S([meter, (126.2, 90.1)]), YELLOW, width=2, dash=True)
    for (s_, t_), text, col, size in (
        ((2, 18), "south entrance\n(new)", WHITE, 16), ((2, 116), "north entrance\n(the old curb cut)", WHITE, 16),
        ((36, 58), "forecourt", (240, 220, 170), 16), ((47, 35), "porte-cochere\n2 cars nose to tail\n9 ft clear", (255, 210, 180), 15),
        ((14, 62), "loop D's island\n(lawn, lone oak)", (180, 240, 180), 15), ((24, 112), "service drive\n(old curl, rebuilt in place)", (240, 220, 170), 15),
        ((60, 120), "north court\nseptic truck stop,\n2 guest spaces", (240, 220, 170), 15), ((118, 118), "shop lane", (240, 220, 170), 16),
        ((186, 72), "shop court\n(raised, walled)", (240, 220, 170), 15), ((196, 128), "BUILDING A\ndoors face south", WHITE, 16),
        ((150, 140), "septic pipe\n10 ft keep-out", RED, 15), ((86, 132), "twin oak\n12 ft no-dig", GREEN, 15),
        ((210, 150), "well", CYAN, 15), ((-3, 2), "1991 electric (locate)", YELLOW, 14), ((150, 120), "service line (locate)", YELLOW, 14),
    ):
        x, y = site([st(s_, t_)])[0]
        plan.label(x, y, text, fill=col, size=size)
    plan.label(*site([st(225, -10)])[0], "Tan: gravel in a stabilizer grid, concrete-curbed (white).  Brown: pavers under the porte-cochere.  "
               "Grey: concrete.  Dashed white: the old drive and walk, coming out.  Green: trunks; yellow: canopy (2017 lidar).  Grid 10 ft.", size=15)
    plan.scale_bar()
    plan.img.save(OUT)
    click.echo(f"wrote {OUT.relative_to(REPO)} {plan.img.size}")
    cfg = dict(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, tbl_rows=-1, fmt_str_lengths=80, tbl_width_chars=170,
               thousands_separator=",")

    # --- Clearances ---
    rows = []
    for t in tr:
        p = Point(t["st"])
        d = L["drive"].distance(p)
        if d > 20 or not (-20 < t["st"][0] < 240 and -20 < t["st"][1] < 170):
            continue
        part = min(L["parts"], key=lambda k: L["parts"][k].distance(p))
        if "twin" in t["name"]:
            status = "OK" if d >= NO_DIG else "CONFLICT"
        elif L["house"].contains(p):
            status = "a crown over the roof (the trunk is off the house)"
        elif d == 0 and old.contains(p):
            status = "a crown over the old drive (the trunk can't be there)"
        elif d < TREE_FLAG and old.distance(p) <= d + 0.5:
            status = "no closer than the old drive was"
        elif d == 0:
            status = "CHECK: on the drive"
        else:
            status = "check: tape the trunk" if d < TREE_FLAG else "OK"
        rows.append({"tree": t["name"], "s, t (ft)": f"{t['st'][0]:.0f}, {t['st'][1]:.0f}", "nearest": part,
                     "to the edge (ft)": round(d, 1), "status": status})
    rows.sort(key=lambda r: r["to the edge (ft)"])
    click.echo("\nTrees near the drive (edge of paving to the trunk or treetop):")
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(rows))
    other = [{"thing": "septic access pipe", "to the edge (ft)": round(L["drive"].distance(Point(pipe)), 1), "keep": "10 ft"},
             {"thing": "well", "to the edge (ft)": round(L["drive"].distance(Point(well)), 1), "keep": "10 ft"},
             {"thing": "1991 electric line (front)", "to the edge (ft)": round(L["drive"].distance(LineString(FRONT_ELECTRIC)), 1), "keep": "locate"},
             {"thing": "buried service line (if straight)", "to the edge (ft)": round(L["drive"].distance(LineString([meter, (126.2, 90.1)])), 1),
              "keep": "locate; the shop lane runs along it"},
             {"thing": "house's north wall (shop lane)", "to the edge (ft)": round(L["parts"]["shop lane"].distance(LineString([(64.2, 90.1), (126.2, 90.1)])), 1),
              "keep": "AC unit, eave drip"}]
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(other))

    # --- Grades along the lanes (2017 lidar; finished grades will smooth these) ---
    grades = []
    for name, pts in (("south leg", SOUTH_LEG), ("north leg", NORTH_LEG), ("service drive", SERVICE_DRIVE), ("shop lane", SHOP_LANE)):
        c = catmull_rom(pts, 24)
        dist = np.concatenate([[0], np.cumsum([math.dist(a, b) for a, b in zip(c, c[1:])])])
        z = np.array([gz(*q) for q in c])
        k = [i for i in range(len(c)) if dist[i] >= 5]
        steep = max(abs(z[i] - z[np.searchsorted(dist, dist[i] - 10)]) / (dist[i] - dist[np.searchsorted(dist, dist[i] - 10)]) for i in k)
        grades.append({"lane": name, "length (ft)": round(dist[-1]), "rise end to end (ft)": round(z[-1] - z[0], 1),
                       "steepest 10 ft": f"{100 * steep:.1f}%"})
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(grades))

    # --- Areas, impervious cover ---
    lot = Polygon([sf.from_site(p) for p in PARCEL])
    on = lambda g: g.intersection(lot)  # noqa: E731
    cover = L["cover"]
    deck = box(DECK[0], DECK[2], DECK[1], DECK[3])
    curb_len = L["curbs"].length
    curb_area = curb_len * CURB
    areas = {"gravel": on(L["gravel"]).area, "pavers": on(L["paved"]).area, "concrete": on(L["concrete"]).area,
             "concrete (street right-of-way)": L["concrete"].area - on(L["concrete"]).area}
    click.echo(f"\nSurfaces: gravel {areas['gravel']:,.0f} sq ft, pavers {areas['pavers']:,.0f}, concrete aprons {areas['concrete']:,.0f} "
               f"on the lot (+{areas['concrete (street right-of-way)']:,.0f} in the right-of-way), curbs {curb_len:,.0f} ft "
               f"({curb_area:,.0f} sq ft); the cover's roof {cover.area:,.0f} sq ft.")
    house_now = unary_union([on(L["house"]), on(deck)])
    now = unary_union([house_now, on(old)])
    a_bldg = unary_union([on(L["building"]), on(L["apron"])])
    hard = unary_union([on(L["paved"]), on(L["concrete"]), on(cover)]).difference(house_now)
    court_and_gravel = on(L["gravel"]).difference(house_now)
    plan_hard = unary_union([house_now, a_bldg, hard])
    plan_all = unary_union([plan_hard, court_and_gravel])
    area_lot = lot.area
    imp = [{"case": "now (house, porch, deck, old drive and walk)", "sq ft": round(now.area)},
           {"case": "plan, gravel not counted (house, building A and apron, cover, pavers, concrete, curbs)", "sq ft": round(plan_hard.area + curb_area)},
           {"case": "plan, gravel counted too", "sq ft": round(plan_all.area + curb_area)}]
    for r in imp:
        r["% of lot"] = round(100 * r["sq ft"] / area_lot, 1)
        r["vs 15%"] = round(0.15 * area_lot - r["sq ft"])
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(imp))

    # --- Budget ---
    court = L["court"]
    lo_court = court.exterior
    gft = lambda q: gz(*q)  # noqa: E731
    a_slab = max(gz(*sf.from_site(p)) for p in SITE_A) - 1.5   # shed_cost.CUT
    top = a_slab - 0.015 * APRON_DEEP
    xs_, ys_ = court.bounds[0::2], court.bounds[1::2]
    cells = [(s_, t_) for s_ in np.arange(xs_[0], xs_[1], 1.0) for t_ in np.arange(ys_[0], ys_[1], 1.0) if court.contains(Point(s_, t_))]
    fill = sum(max(top - SHOP_COURT_FALL * L["apron"].distance(Point(c)) - gft(c), 0) for c in cells) / 27
    wall = sum(1.0 for k in range(int(lo_court.length)) if (lambda q: top - gft(q) > 0.75 and L["apron"].distance(Point(q)) > 1)(
        lo_court.interpolate(k + 0.5).coords[0]))
    qty = {"demo": Polygon(EXISTING_DRIVE).area + Polygon(FRONT_WALK).area, "concrete": L["concrete"].area, "permit": 1,
           "gravel": L["gravel"].area, "curb": curb_len, "pavers": L["paved"].area, "cover": cover.area, "fill": fill, "wall": wall,
           "arborist": 1}
    rows, sums = [], {}
    for key, ((lo, hi), unit, label) in PRICES.items():
        q = qty[key]
        rows.append({"item": label, "qty": f"{q:,.0f} {unit}", "low": int(round(lo * q, -2)), "high": int(round(hi * q, -2))})
        sums[key] = (lo * q, hi * q)
    with pl.Config(**cfg):
        click.echo(pl.DataFrame(rows))
    k = lambda v: f"${v / 1000:,.0f}k"  # noqa: E731
    drive_items = [sums[x] for x in PRICES if x != "cover"]
    for label, items in (("The drive (everything but the cover)", drive_items), ("The porte-cochere", [sums["cover"]]),
                         ("All of it", list(sums.values()))):
        m, a, b = likely(items)
        click.echo(f"{label}, likely with {CONTINGENCY:.0%} contingency: {k(m)} ({k(a)}-{k(b)} 80% band)")


if __name__ == "__main__":
    main()
