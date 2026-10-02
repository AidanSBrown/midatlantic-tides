"""Map of the NOAA tide gauges used in midatlantic_tides_daily.csv.

Basemap is the US Census 1:500k state boundary file (data/geo/), drawn with
plain matplotlib, so no GIS libraries are needed.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon, Rectangle

from fetch_noaa import MET_STATIONS, WL_STATIONS

ROOT = Path(__file__).parent
GEO = ROOT / "data" / "geo"

SURFACE, WATER, LAND, BORDER = "#fcfcfb", "#e8eef4", "#f1f0ec", "#b9b7ae"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a887f"
WL_ONLY, WITH_MET = "#2a78d6", "#eb6834"   # categorical slots 1 and 2

EXTENT = (-77.3, -73.45, 35.85, 40.85)    # lon0, lon1, lat0, lat1

# Label offsets (points) and alignment, hand-placed to avoid collisions.
LABELS = {
    "sandy_hook_nj":    (8, 0, "left"),
    "atlantic_city_nj": (8, 0, "left"),
    "cape_may_nj":      (8, -3, "left"),
    "lewes_de":         (8, -3, "left"),
    "ocean_city_md":    (8, 0, "left"),
    "tolchester_beach_md": (-8, 2, "right"),
    "annapolis_md":     (8, 4, "left"),
    "cambridge_md":     (8, 2, "left"),
    "bishops_head_md":  (8, -2, "left"),
    "solomons_md":      (-8, 0, "right"),
    "lewisetta_va":     (-8, 0, "right"),
    "windmill_point_va": (-8, 0, "right"),
    "yorktown_va":      (-8, 2, "right"),
    "wachapreague_va":  (8, 0, "left"),
    "kiptopeke_va":     (8, -2, "left"),
    "sewells_point_va": (-8, -4, "right"),
    "duck_nc":          (8, 0, "left"),
}
# Shorter map labels where NOAA's station name is long.
SHORT_NAMES = {"yorktown_va": "Yorktown"}
STATE_LABELS = {"PA": (-75.75, 40.65), "NJ": (-74.6, 40.05), "DE": (-75.47, 38.98),
                "MD": (-76.95, 39.45), "VA": (-76.95, 36.68), "NY": (-73.75, 40.75),
                "NC": (-76.95, 36.32)}


def station_table():
    """Station names and coordinates from NOAA's metadata API, cached to disk."""
    path = GEO / "stations.json"
    cached = json.loads(path.read_text()) if path.exists() else {}
    if set(cached) != set(WL_STATIONS):
        cached = {}
        for sid, key in WL_STATIONS.items():
            url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{sid}.json"
            st = requests.get(url, timeout=60).json()["stations"][0]
            cached[sid] = dict(key=key, name=st["name"], state=st["state"], lat=st["lat"], lon=st["lng"])
        path.write_text(json.dumps(cached, indent=1))
    return cached


def rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        yield np.asarray(poly[0])  # exterior ring only; holes are lakes, not coast


def draw_states(ax, features, lw=0.6):
    for f in features:
        for ring in rings(f["geometry"]):
            ax.add_patch(Polygon(ring, closed=True, fc=LAND, ec=BORDER, lw=lw))


def main():
    states = json.loads((GEO / "us_states_500k.json").read_text(encoding="latin-1"))["features"]
    stations = station_table()
    met_keys = set(MET_STATIONS.values())

    fig, ax = plt.subplots(figsize=(6.8, 9.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(WATER)
    draw_states(ax, states)
    lon0, lon1, lat0, lat1 = EXTENT
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.deg2rad((lat0 + lat1) / 2)))  # equirectangular, true at mid-lat

    for st, (x, y) in STATE_LABELS.items():
        ax.text(x, y, st, color=MUTED, fontsize=11, ha="center", va="center", weight="bold", alpha=0.8)
    for txt, x, y, rot in [("Atlantic Ocean", -74.0, 37.6, 0), ("Chesapeake\nBay", -76.12, 37.4, 0),
                           ("Delaware\nBay", -75.18, 39.17, 0)]:
        ax.text(x, y, txt, color="#6f8aa6", fontsize=8.5, style="italic", ha="center", va="center", rotation=rot)

    for s in stations.values():
        met = s["key"] in met_keys
        ax.scatter(s["lon"], s["lat"], s=70 if met else 46, marker="D" if met else "o",
                   c=WITH_MET if met else WL_ONLY, edgecolors=SURFACE, linewidths=1.6, zorder=5)
        dx, dy, ha = LABELS[s["key"]]
        ax.annotate(SHORT_NAMES.get(s["key"], s["name"]), (s["lon"], s["lat"]), xytext=(dx, dy), textcoords="offset points",
                    ha=ha, va="center", fontsize=8.5, color=INK, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.75))

    # Scale bar: 50 km at mid-latitude.
    km_per_deg = 111.32 * np.cos(np.deg2rad((lat0 + lat1) / 2))
    x0, y0 = lon0 + 0.2, lat0 + 0.2
    ax.plot([x0, x0 + 50 / km_per_deg], [y0, y0], color=INK2, lw=2, solid_capstyle="butt")
    ax.text(x0 + 25 / km_per_deg, y0 + 0.06, "50 km", ha="center", va="bottom", fontsize=8, color=INK2)

    for side in ax.spines.values():
        side.set_color(BORDER)
    ax.tick_params(colors=MUTED, labelsize=8, length=3)
    ax.set_xticks(np.arange(-77, lon1, 1.0))
    ax.set_yticks(np.arange(36, lat1, 1.0))
    ax.xaxis.set_major_formatter(lambda v, _: f"{abs(v):.0f}°W")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}°N")

    handles = [
        Line2D([], [], marker="o", ls="", ms=7, mfc=WL_ONLY, mec=SURFACE, mew=1.2,
               label=f"Water level ({len(stations) - len(met_keys)})"),
        Line2D([], [], marker="D", ls="", ms=7.5, mfc=WITH_MET, mec=SURFACE, mew=1.2,
               label=f"Water level + weather ({len(met_keys)})"),
    ]
    leg = ax.legend(handles=handles, loc="lower right", fontsize=8.5, frameon=True,
                    facecolor=SURFACE, edgecolor=BORDER, title="NOAA CO-OPS gauges", title_fontsize=8.5)
    leg.get_title().set_color(INK2)

    # Locator inset: eastern US with the study box.
    ins = ax.inset_axes([0.015, 0.765, 0.26, 0.22])
    ins.set_facecolor(WATER)
    draw_states(ins, states, lw=0.3)
    ins.set_xlim(-90, -66.5)
    ins.set_ylim(24.5, 47.5)
    ins.set_aspect(1 / np.cos(np.deg2rad(36)))
    ins.add_patch(Rectangle((lon0, lat0), lon1 - lon0, lat1 - lat0, fill=False, ec=WITH_MET, lw=1.4))
    ins.set_xticks([])
    ins.set_yticks([])
    for side in ins.spines.values():
        side.set_color(BORDER)

    ax.set_title("Mid-Atlantic coastal tide gauges used in the dataset", loc="left", fontsize=12, color=INK, pad=10)
    fig.text(0.125, 0.045, "Daily series 2005–2025 from NOAA Tides & Currents. "
             "Weather = water & air temperature, pressure, wind.\nBasemap: US Census 1:500k state boundaries.",
             fontsize=7.5, color=INK2, va="top")

    out = ROOT / "figures" / "station_map.png"
    fig.savefig(out, bbox_inches="tight", facecolor=SURFACE)
    print("wrote", out)


if __name__ == "__main__":
    main()
