from importlib.resources import path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

try:
    import functions as func
except ModuleNotFoundError:
    import importlib.util, tempfile, urllib.request
    from pathlib import Path

    url = "https://github.com/AidanSBrown/midatlantic-tides/blob/main/functions.py" # This is meant to prevent errors if someone runs this file without having the functions.py file in the same directory. It will download it from the GitHub repo and import it.
    urllib.request.urlretrieve(url, path)
    spec = importlib.util.spec_from_file_location("functions", path)
    func = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(func)


dataset = pd.read_csv("https://raw.githubusercontent.com/AidanSBrown/midatlantic-tides/refs/heads/main/data/midatlantic_tides_daily.csv")
dates = pd.date_range(start="2005-01-01", end="2025-12-31")


# Plotting the Mid-Atlantic MSL over time
sns.lineplot(x= dates, y=dataset['msl_midatlantic'], color='blue', label='Mid-Atlantic MSL')
plt.xlabel("Date")
plt.ylabel("MSL Value (m above MSL 1983-2001)")
plt.title("Mid-Atlantic MSL Over Time")
plt.show()

# plot rolling mean and variance of MSL
mean = func.rolling_mean(dataset['msl_midatlantic'], window=30)
variance = func.rolling_var(dataset['msl_midatlantic'], window=30)
plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(dates, mean, color='blue', label='Rolling Mean (30 days)')
plt.title("Rolling Mean of Mid-Atlantic MSL")
plt.xlabel("Date")
plt.ylabel("Mean Value (m above MSL 1983-2001)")
plt.subplot(2, 1, 2)
plt.plot(dates, variance, color='orange', label='Rolling Variance (30 days)')
plt.title("Rolling Variance of Mid-Atlantic MSL")
plt.xlabel("Date")
plt.ylabel("Variance Value")
plt.tight_layout()
plt.show()


func.acfplot(dataset['msl_midatlantic'], lags=365, title="Autocorrelation of Mid-Atlantic MSL")

func.plotma(dataset['msl_midatlantic'], m=365, title="365-Day Moving Average of Mid-Atlantic MSL")

func.ADF_Cal(dataset['msl_midatlantic'])
func.KPSS_Cal(dataset['msl_midatlantic'])

# Strength of trend and seasonality
res = func.trend_season_strength(dataset["msl_midatlantic"], period=31)
res.plot()
plt.show()
