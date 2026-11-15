"""The statistics engine (Document 2, section 6). Plain Python, no AI.

anomalies -> Theil-Sen slope (+95% CI) -> Mann-Kendall with Hamed-Rao correction
-> Benjamini-Hochberg FDR across cells -> cos-latitude weighted regional series.
Plus the Weatherhead et al. (1998) "years needed" estimate for non-significant trends.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes
from statsmodels.stats.multitest import multipletests

from common import config as C


def anomalies(values: np.ndarray, months: np.ndarray) -> np.ndarray:
    """Subtract the mean of each calendar month (removes summer/winter)."""
    values = np.asarray(values, dtype="float64")
    out = np.full_like(values, np.nan)
    for m in range(1, 13):
        sel = months == m
        if not sel.any():
            continue
        clim = np.nanmean(values[sel]) if np.isfinite(values[sel]).any() else np.nan
        out[sel] = values[sel] - clim
    return out


def lag1_autocorr(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if len(x) < 3 or np.nanstd(x) == 0:
        return 0.0
    x = x - x.mean()
    return float(np.dot(x[:-1], x[1:]) / np.dot(x, x))


def years_needed(slope_per_year: float, residual_sd: float, phi: float) -> float | None:
    """Weatherhead et al. (1998): years of monthly data needed to detect this trend."""
    if not slope_per_year or not np.isfinite(slope_per_year) or residual_sd <= 0:
        return None
    phi = min(max(phi, -0.95), 0.95)
    n = ((3.3 * residual_sd / abs(slope_per_year)) * math.sqrt((1 + phi) / (1 - phi))) ** (2 / 3)
    return float(n)


def trend(values: np.ndarray, months: np.ndarray, t_years: np.ndarray,
          min_valid: float = C.MIN_VALID_FRACTION) -> dict | None:
    """Trend of one monthly series. Returns None when too many months are missing."""
    a = anomalies(values, months)
    ok = np.isfinite(a)
    if ok.sum() < max(24, min_valid * len(a)):
        return None
    y, t = a[ok], t_years[ok]
    if np.nanstd(y) == 0:
        return dict(slope_dec=0.0, ci_lo=0.0, ci_hi=0.0, p=1.0, tau=0.0, n=int(ok.sum()),
                    years_needed=None)
    res = theilslopes(y, t, alpha=0.95)
    slope, intercept, lo, hi = res[0], res[1], res[2], res[3]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            test = mk.hamed_rao_modification_test(y)
            p, tau = float(test.p), float(test.Tau)
        except Exception:                      # rare numerical failure -> plain MK
            test = mk.original_test(y)
            p, tau = float(test.p), float(test.Tau)
    resid = y - (intercept + slope * t)
    return dict(slope_dec=float(slope * 10), ci_lo=float(lo * 10), ci_hi=float(hi * 10),
                p=p, tau=tau, n=int(ok.sum()),
                years_needed=years_needed(slope, float(np.std(resid)), lag1_autocorr(resid)))


def add_fdr(df: pd.DataFrame, q: float = C.FDR_Q) -> pd.DataFrame:
    """Benjamini-Hochberg across all cells of ONE variable and ONE area."""
    df = df.copy()
    df["q"] = np.nan
    df["significant"] = False
    ok = df["p"].notna()
    if ok.any():
        reject, qvals, _, _ = multipletests(df.loc[ok, "p"].values, alpha=q, method="fdr_bh")
        df.loc[ok, "q"] = qvals
        df.loc[ok, "significant"] = reject
    df["direction"] = np.where(~df["significant"], "none",
                               np.where(df["slope_dec"] > 0, "up", "down"))
    return df


def regional_series(cube: np.ndarray, lats: np.ndarray, min_cell_fraction: float = 0.5
                    ) -> np.ndarray:
    """cos(latitude)-weighted mean over cells for each month. cube: (time, cells), lats: (cells,).
    A month is kept only if at least half of the cells have data."""
    w = np.cos(np.deg2rad(lats))[None, :] * np.ones_like(cube)
    valid = np.isfinite(cube)
    w = np.where(valid, w, 0.0)
    num = np.nansum(np.where(valid, cube, 0.0) * w, axis=1)
    den = w.sum(axis=1)
    out = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    frac = valid.mean(axis=1)
    out[frac < min_cell_fraction] = np.nan
    return out


def area_weights(lats: np.ndarray) -> np.ndarray:
    return np.cos(np.deg2rad(np.asarray(lats, dtype="float64")))
