"""Download NOAA CO-OPS data for Mid-Atlantic tide stations.

Hourly water level, every observed high and low tide (high_low), hourly tide
predictions, and hourly weather.

Pulls one calendar year per request (the API's limit for hourly products),
caches each station/product as a CSV in data/raw/, and skips anything already
downloaded, so reruns are cheap.

    python fetch_noaa.py            # 2005-2025
    python fetch_noaa.py 1990 2025  # custom year range
"""
import sys
import time
import concurrent.futures as cf
from pathlib import Path

import pandas as pd
import requests

API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
RAW = Path(__file__).parent / "data" / "raw"

WL_STATIONS = {
    "8531680": "sandy_hook_nj",
    "8534720": "atlantic_city_nj",
    "8536110": "cape_may_nj",
    "8557380": "lewes_de",
    "8570283": "ocean_city_md",
    "8573364": "tolchester_beach_md",
    "8575512": "annapolis_md",
    "8571892": "cambridge_md",
    "8571421": "bishops_head_md",
    "8577330": "solomons_md",
    "8635750": "lewisetta_va",
    "8636580": "windmill_point_va",
    "8637689": "yorktown_va",
    "8631044": "wachapreague_va",
    "8632200": "kiptopeke_va",
    "8638610": "sewells_point_va",
    "8651370": "duck_nc",
}

# Stations with long tracks of weather data and tides
MET_STATIONS = {
    "8557380": "lewes_de",
    "8536110": "cape_may_nj",
    "8573364": "tolchester_beach_md",
    "8571421": "bishops_head_md",
    "8635750": "lewisetta_va",
    "8631044": "wachapreague_va",
    "8651370": "duck_nc",
    "8637689": "yorktown_va",
}
MET_PRODUCTS = ["water_temperature", "air_temperature", "air_pressure", "wind"]


def fetch_year(product, station, year):
    q = dict(product=product, station=station, begin_date=f"{year}0101", end_date=f"{year}1231",
             units="metric", time_zone="lst", format="json", application="tsa_course_project")
    if product in ("hourly_height", "high_low", "predictions"):
        q["datum"] = "MSL"
    if product in MET_PRODUCTS or product == "predictions":
        q["interval"] = "h"
    err = None
    for attempt in range(6):
        try:
            r = requests.get(API, params=q, timeout=120)
            r.raise_for_status()
            js = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            err = e
            time.sleep(3 * 2 ** attempt)
    else:
        print(f"  FAILED {product} {station} {year}: {err!r}")
        return None
    rows = js.get("data") or js.get("predictions") or []
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["t"])
    keep = {"v": "value", "s": "speed", "d": "dir_deg", "g": "gust"}
    if product == "wind":
        keep.pop("v")
    elif product == "hourly_height":
        keep = {"v": "value"}  # 's' is sigma here, not speed
    elif product == "high_low":
        keep = {"v": "value"}
    cols = {k: v for k, v in keep.items() if k in df}
    out = df[["t", *cols]].rename(columns=cols)
    for c in cols.values():
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if product == "high_low":
        # NOAA tags each turning point H/HH (high) or L/LL (low).
        out["type"] = df["ty"].str.strip()
    return out


def fetch(product, station, name, years):
    path = RAW / f"{product}__{name}.csv"
    if path.exists():
        return f"cached  {path.name}"
    parts = [fetch_year(product, station, y) for y in years]
    parts = [p for p in parts if p is not None]
    if not parts:
        return f"EMPTY   {product} {name}"
    df = pd.concat(parts).drop_duplicates("t").sort_values("t")
    df.to_csv(path, index=False)
    return f"wrote   {path.name} ({len(df):,} rows)"


def main():
    y0, y1 = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (2005, 2025)
    years = range(y0, y1 + 1)
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = [("hourly_height", s, n) for s, n in WL_STATIONS.items()]
    jobs += [("high_low", s, n) for s, n in WL_STATIONS.items()]
    jobs += [("predictions", s, n) for s, n in WL_STATIONS.items()]
    jobs += [(p, s, n) for s, n in MET_STATIONS.items() for p in MET_PRODUCTS]
    with cf.ThreadPoolExecutor(3) as ex:
        for msg in ex.map(lambda j: fetch(*j, years), jobs):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
