"""Turn the cached NOAA pulls into a uniformly sampled multivariate table.

Steps
  1. Hourly -> daily (or weekly) means on a complete, gap-free calendar index.
     A day only counts if >= 18 of its 24 hourly readings exist. Observed
     high/low tides give each day's MHHW, MHW, MLW and MLLW.
  2. Drop any column with < MIN_COVERAGE of days present.
  3. Fill short gaps (<= MAX_GAP steps) by time interpolation; longer gaps
     stay NaN so they're visible and not interpolated.
  4. Write data/midatlantic_tides_<freq>.csv plus a coverage report.

    python build_dataset.py          # daily
    python build_dataset.py W        # weekly (W-SUN)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_noaa import MET_STATIONS, WL_STATIONS

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
START, END = "2005-01-01", "2025-12-31"
MIN_HOURS_PER_DAY = 18
MIN_COVERAGE = 0.85
MAX_GAP = {"D": 7, "W": 2}


def load(product, name):
    path = RAW / f"{product}__{name}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["t"]).set_index("t")
    return df[~df.index.duplicated()]


def daily(series):
    """Daily mean, NaN where too few hourly readings."""
    g = series.resample("D")
    out = g.mean()
    out[g.count() < MIN_HOURS_PER_DAY] = np.nan
    return out


def daily_tides(hl):
    """Daily analogues of NOAA's tidal datums from observed high/low tides.

    Grouped by calendar day, so a day can hold 1-2 highs and 1-2 lows (the tidal
    day is ~24.8 h). With a single high, MHW = MHHW; with a single low, MLW = MLLW.
    A day needs at least one high and one low to count.
    """
    v = hl["value"]
    is_high = hl["type"].str.startswith("H")
    highs, lows = v[is_high].resample("D"), v[~is_high].resample("D")
    ok = (highs.count() > 0) & (lows.count() > 0)
    return {
        "mhhw": highs.max().where(ok),
        "mhw": highs.mean().where(ok),
        "mlw": lows.mean().where(ok),
        "mllw": lows.min().where(ok),
    }


def build_daily():
    cols = {}
    for name in WL_STATIONS.values():
        obs, pred = load("hourly_height", name), load("predictions", name)
        if obs is None:
            continue
        wl = obs["value"]
        cols[f"msl_{name}"] = daily(wl)                      # mean of the day's hourly levels
        hl = load("high_low", name)
        if hl is not None:
            cols.update({f"{k}_{name}": v for k, v in daily_tides(hl).items()})
        if pred is not None:
            # Non-tidal residual ("surge"): observed minus astronomical prediction.
            cols[f"surge_{name}"] = daily(wl - pred["value"].reindex(wl.index))

    for name in MET_STATIONS.values():
        for product, short in [("water_temperature", "wtemp"), ("air_temperature", "atemp"),
                               ("air_pressure", "pres")]:
            df = load(product, name)
            if df is not None:
                cols[f"{short}_{name}"] = daily(df["value"])
        w = load("wind", name)
        if w is not None:
            # Direction is where wind blows FROM; u>0 = toward east, v>0 = toward north.
            rad = np.deg2rad(w["dir_deg"])
            cols[f"wspd_{name}"] = daily(w["speed"])
            cols[f"wind_u_{name}"] = daily(-w["speed"] * np.sin(rad))
            cols[f"wind_v_{name}"] = daily(-w["speed"] * np.cos(rad))

    idx = pd.date_range(START, END, freq="D", name="date")
    return pd.DataFrame({k: v.reindex(idx) for k, v in cols.items()})


def main():
    freq = sys.argv[1].upper() if len(sys.argv) > 1 else "D"
    df = build_daily()
    if freq == "W":
        counts = df.resample("W-SUN").count()
        df = df.resample("W-SUN").mean().where(counts >= 5)  # >=5 good days per week
        df.index.name = "week_ending"

    coverage = df.notna().mean().sort_values()
    kept = coverage[coverage >= MIN_COVERAGE].index
    dropped = coverage[coverage < MIN_COVERAGE]
    df = df[[c for c in df.columns if c in kept]]

    filled = df.interpolate(method="time", limit=MAX_GAP[freq], limit_area="inside")
    n_filled = int((filled.notna() & df.isna()).sum().sum())
    tag = {"D": "daily", "W": "weekly"}[freq]
    out = ROOT / "data" / f"midatlantic_tides_{tag}.csv"
    filled.round(4).to_csv(out)

    complete = filled.dropna()
    report = [
        f"{tag}: {len(filled):,} rows x {filled.shape[1]} features  ({filled.index[0].date()} .. {filled.index[-1].date()})",
        f"uniform spacing: {filled.index.to_series().diff().dropna().nunique() == 1}",
        f"values interpolated across short gaps: {n_filled:,}",
        f"rows with every column present: {len(complete):,}",
        f"dropped (<{MIN_COVERAGE:.0%} coverage): " + (", ".join(f"{c} {v:.0%}" for c, v in dropped.items()) or "none"),
        "", "remaining NaN per column after fill:",
        filled.isna().sum().loc[lambda s: s > 0].to_string() or "  none",
    ]
    (ROOT / "data" / f"coverage_{tag}.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
