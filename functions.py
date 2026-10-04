import pandas as pd
import numpy as np
from math import sqrt
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.stattools import kpss
from statsmodels.tsa.seasonal import STL


def rolling_mean(data, window=None):
    """rolling mean"""
    values = np.asarray(data, dtype=float)
    out = np.full(len(values), np.nan)
    for t in range(len(values)):
        start = 0 if window is None else t - window + 1
        if start >= 0:
            out[t] = np.mean(values[start : t + 1])
    return out

def rolling_var(data, window=None):
    """rolling variance"""
    values = np.asarray(data, dtype=float)
    out = np.full(len(values), np.nan)
    for t in range(len(values)):
        start = 0 if window is None else t - window + 1
        if start >= 0:
            out[t] = np.var(values[start : t + 1])
    return out

def ADF_Cal(x):
    result = adfuller(x)
    print("ADF Statistic: %f" % result[0])
    print("p-value: %f" % result[1])
    print("Critical Values:")
    for key, value in result[4].items():
        print("\t%s: %.3f" % (key, value))

def KPSS_Cal(x):
    print("Results of KPSS Test:")
    kpsstest = kpss(x, regression="c", nlags="auto")
    kpss_output = pd.Series(kpsstest[0:3],
    index=["Test Statistic", "p-value", "Lags Used"])
    for key, value in kpsstest[3].items():
        kpss_output["Critical Value (%s)" % key] = value
    print(kpss_output)

def acf(y,
        tau):
    """
    Single autocorrelation for a tau
    """
    # r^y(t) = sum(yt - ymean)(yt-T - ymean) / sum((yt - ymean)2)
    T = len(y)
    y_mean = np.mean(y)
    deviations = y - y_mean  # do the deviation calc once across whole array
    denominator = np.sum(deviations ** 2) # compute denominator once

    numerator = 0 # Numerator sum
    for t in range(tau, T): # iterates from tau to T
        numerator += deviations[t] * deviations[t - tau]

    return numerator / denominator

def acf_loop(y, lags):
    """
    Loop over lags and calculate autocorrelation for all
    """
    lags = lags + 1 # Ensure that lag count lines up, lags = 0 returns 1
    acf_array = []
    for lag in range(lags):
        acf_array.append(acf(y, lag)) # Add the calculated lag
    return np.array(acf_array) # returns an array

def acfplot(y, lags,
            title="Autocorrelation Function "
                  "of White Noise",
            show=True): #show bool needed for plotting our 3x3 grid

    # Flip our lags matrix (which goes one dir) and add them so we have our full data
    corrs_matrix = acf_loop(y, lags)
    flipped_corr = corrs_matrix[1:]
    full_corrs = np.concatenate((flipped_corr[::-1], corrs_matrix))

    error = 1.96 / sqrt(len(y))

    x = np.linspace(-lags, lags, len(full_corrs)) # create x between -lags and lags
    y = full_corrs

    markerline, stemlines, baseline = plt.stem(x,y)
    markerline.set_color('r')
    markerline.set_zorder(1) # Had to do all this to put dots under lines like your exact formatting
    plt.title(title)
    plt.xlabel("Lags")
    plt.ylabel("Magnitude")
    plt.fill_between(x, y1 = error, y2=-error, color='blue', alpha=0.2, zorder = 0) # Error shading

    if show:
        plt.show()


def moving_average(m, data, m2=None):
    """ Moving average of a time series """

    if not isinstance(m, (int, np.integer)) or m < 3:
        raise ValueError("m must be an integer >= 3 (1 and 2 are not accepted)")
    if m % 2 == 0:
        if m2 is None:
            raise ValueError("m is even: pass an even m2 to fold it (m2 x m-MA)")
        if not isinstance(m2, (int, np.integer)) or m2 < 2 or m2 % 2 != 0:
            raise ValueError("m2 must be an even integer >= 2")
    else:
        m2 = None

    values = np.asarray(data, dtype=float)
    n = len(values)
    span = m + m2 - 1 if m2 else m  # total number of points each output averages
    if span > n:
        raise ValueError(f"MA window ({span}) is longer than the data ({n})")

    # First MA
    first = np.array([np.mean(values[j : j + m]) for j in range(n - m + 1)])

    if m2:
        # Even x even MA
        smooth = np.array([np.mean(first[i : i + m2]) for i in range(len(first) - m2 + 1)])
    else:
        # Single odd MA already centered on the middle point.
        smooth = first

    trend = np.full(n, np.nan)
    half = (span - 1) // 2
    trend[half : half + len(smooth)] = smooth
    return trend

def plotma(series, m, m2=None, title="Moving Average", show=True):
    """Plot moving average of a time series"""

    ma = moving_average(m, series, m2)
    plt.plot(series, label="original", color="lightgray")
    plt.plot(ma, label=f"{m}-point MA" + (f" + {m2}-point fold" if m2 else ""), color="blue")
    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel("m above MSL 1983-2001")
    plt.legend()
    if show:
        plt.show()

def trend_season_strength(y, period):
    res = STL(y, period=period).fit() # call fit here to return T S R
    T, S, R = res.trend, res.seasonal, res.resid
    F_T = max(0, 1 - np.var(R) / np.var(T + R))
    F_S = max(0, 1 - np.var(R) / np.var(S + R))
    print(f"Strength of trend:       {F_T:.3f}")
    print(f"Strength of seasonality: {F_S:.3f}") # We print these out but then also return the values for later / other use
    return res

# implementation
if __name__ == '__main__':

    # Implementation:
    y = np.array([3,9,27,81,243])
    tau = 3
    print(acf(y,tau))

    # Implementation
    y = np.array([3,9,27,81,243])
    print(acf_loop(y,0))

    data = np.array([1,2,3,4,5,6,7,8,9])
    m = 3
    print(moving_average(m,data))
    plotma(data, m)