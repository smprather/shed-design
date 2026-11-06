# /// script
# requires-python = ">=3.11"
# dependencies = ["rich-click", "polars", "numpy", "pillow"]
# ///
"""The sprinkler system from the house's 2017 irrigation plan, in site feet: site/irrigation-2017.json.

The plan (Feb 8 2017, 1" = 20', drawn and sealed by a licensed irrigator) is a photo of the paper in the private repo,
`property/irrigation-plan-2017.webp`; it names the owner of the time and carries a signature, so only the lines live
here. Its legend: Hunter PGP rotors and Pro-S pop-ups with MP3 rotary nozzles, 1" PGV valves with flow control, a
master valve and an isolation valve, a 3/4" double check with a Y-strainer at the meter, a 1-1/4" mainline, a rain
sensor, the valve wire laid in the trench under the pipe (splices only in the valve boxes). Its own note 5: the plan is
schematic; the actual piping could be different.

The photo's pixels map onto the site frame by a projective fit on the four lot corners and six house corners
(residuals 1-6 ft). Only what bears on building A, its dig and the trenches is digitized: the four back-yard rotor
zones, the mainline up the south side, their valves, the controller and the rain sensor. The front and south-side
zones (Pro-S with MP3 nozzles) are left out. Read positions as +/-5-10 ft until the lines are located.

Run: uv run tools/irrigation_plan.py
"""

import json
from itertools import pairwise

import numpy as np
import polars as pl
import rich_click as click

from site_plan import HOUSE, PARCEL, REPO

OUT = REPO / "site" / "irrigation-2017.json"

# Photo pixels (1387 x 1035) -> site ft: the lot's corners and the house's.
CTRL = [((115, 45), PARCEL[3]), ((560, 35), PARCEL[2]), ((92, 815), PARCEL[0]), ((432, 812), PARCEL[1]),
        ((374, 385), HOUSE[4]), ((310, 385), HOUSE[3]), ((310, 460), HOUSE[2]), ((175, 460), HOUSE[1]),
        ((375, 590), HOUSE[5]), ((175, 590), HOUSE[0])]

# Photo pixels. The zone numbers and flows are read off the plan's margin (zone, valve, GPM).
ZONES = [
    {"zone": 7, "gpm": 12, "what": "back-lawn rotors, the row nearest the back line", "valve": (157.5, 246),
     "pipes": [[(157.5, 246), (157.5, 155)], [(117.5, 155), (209, 151), (300, 144), (391.5, 138.5)]],
     "heads": [(117.5, 155), (209, 151), (300, 144), (391.5, 138.5)]},
    {"zone": 6, "gpm": 12, "what": "back-lawn rotors, the middle row", "valve": (157.5, 265),
     "pipes": [[(117.5, 265), (207.5, 260), (299, 255), (386, 251)]],
     "heads": [(117.5, 265), (207.5, 260), (299, 255), (386, 251)]},
    {"zone": 5, "gpm": 12, "what": "rotors behind the house and along its north side to the north line", "valve": (157.5, 350),
     "pipes": [[(157.5, 350), (272.5, 350), (300, 365), (382.5, 364), (380, 447.5), (490, 445)]],
     "heads": [(300, 365), (382.5, 364), (380, 447.5), (490, 445)]},
    {"zone": 4, "gpm": 14, "what": "rotors by the back deck and the south side", "valve": (157.5, 365),
     "pipes": [[(117.5, 455), (117.5, 365), (157.5, 365), (232.5, 364), (232.5, 450)], [(240, 392.5), (255, 387.5)]],
     "heads": [(117.5, 365), (117.5, 455), (232.5, 364), (232.5, 450), (255, 387.5)]},
]
MAINLINE = [(92.5, 815), (147.5, 810), (147.5, 750), (152.5, 607), (157.5, 430), (157.5, 246)]
POINTS = {"controller": (368.5, 376), "rain sensor": (490, 430), "master and isolation valves": (180, 625),
          "water meter": (92.5, 815)}


def homography() -> np.ndarray:
    rows = []
    for (u, v), (x, y) in CTRL:
        rows.append([u, v, 1, 0, 0, 0, -x * u, -x * v, -x])
        rows.append([0, 0, 0, u, v, 1, -y * u, -y * v, -y])
    _, _, vt = np.linalg.svd(np.array(rows, float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


@click.command()
def main() -> None:
    """Write the digitized sprinkler lines and print the fit and the zones."""
    h = homography()

    def site_ft(p):
        q = h @ np.array([p[0], p[1], 1.0])
        return [round(float(q[0] / q[2]), 1), round(float(q[1] / q[2]), 1)]

    err = [float(np.hypot(*(np.array(site_ft(px)) - np.array(xy)))) for px, xy in CTRL]
    zones = [{"zone": z["zone"], "gpm": z["gpm"], "what": z["what"], "valve": site_ft(z["valve"]),
              "pipes": [[site_ft(p) for p in line] for line in z["pipes"]], "heads": [site_ft(p) for p in z["heads"]]}
             for z in ZONES]
    out = {"source": "the house's 2017 irrigation plan (private repo, property/irrigation-plan-2017.webp), digitized "
                     "Nov 6 2026 by tools/irrigation_plan.py; site frame, ft. Schematic (the plan's note 5); "
                     f"fit residuals {min(err):.0f}-{max(err):.0f} ft. Read as +/-5-10 ft until located.",
           "zones": zones, "mainline": [site_ft(p) for p in MAINLINE],
           "points": {k: site_ft(p) for k, p in POINTS.items()}}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    click.echo(f"Fit on {len(CTRL)} lot and house corners: residuals {min(err):.1f}-{max(err):.1f} ft "
               f"(mean {np.mean(err):.1f}).")
    rows = []
    for z in zones:
        length = sum(float(np.hypot(b[0] - a[0], b[1] - a[1])) for line in z["pipes"] for a, b in pairwise(line))
        rows.append({"zone": z["zone"], "GPM": z["gpm"], "what": z["what"], "heads": len(z["heads"]),
                     "pipe (ft)": f"{length:.0f}", "valve (site x, y)": f"{z['valve'][0]:.0f}, {z['valve'][1]:.0f}"})
    with pl.Config(tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True, fmt_str_lengths=80, tbl_width_chars=180):
        click.echo(pl.DataFrame(rows))
    click.echo(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
