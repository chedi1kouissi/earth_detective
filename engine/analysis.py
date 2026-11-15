"""On-demand trend analysis for any (variable, area, period) inside our data.

The investigator never computes statistics itself: it calls TrendEngine.run(...), which applies
the guardrails of Document 2 section 6.3, runs engine.stats on every land cell of the area,
applies FDR across those cells, computes the regional trend, and returns Contract 2.
Results are cached on disk, so the same question is instant next time.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from common import config as C
from common.config import BBox
from common.contracts import CellCounts, RegionalTrend, VariableResult
from common.variables import DATASETS, VARIABLES
from engine import stats

log = logging.getLogger(__name__)

METHOD_TEXT = ("monthly anomalies (seasonal cycle removed); Theil-Sen slope with 95% CI; "
               "Mann-Kendall test with Hamed-Rao autocorrelation correction; "
               f"Benjamini-Hochberg FDR q={C.FDR_Q} across the cells of the area; "
               "regional mean weighted by cos(latitude)")


class GuardrailError(ValueError):
    """The request is outside what our data can answer reliably. The message is user-facing."""


@dataclass
class Area:
    id: str
    name: str
    bbox: BBox


def parse_period(period: list[str] | tuple[str, str]) -> tuple[pd.Timestamp, pd.Timestamp]:
    a, b = pd.Timestamp(period[0] + "-01"), pd.Timestamp(period[1] + "-01")
    if a > b:
        raise GuardrailError(f"The period starts after it ends ({period[0]} > {period[1]}).")
    return a, b


@lru_cache(maxsize=2)
def _open(path: str, mtime: float) -> xr.Dataset:
    return xr.load_dataset(path)


def open_series(path: Path = C.SERIES_NC) -> xr.Dataset:
    if not path.exists():
        raise FileNotFoundError("data/processed/series.nc not found. Run `python run.py "
                                "download` then `python run.py preprocess`.")
    return _open(str(path), path.stat().st_mtime)


class TrendEngine:
    def __init__(self, series_path: Path = C.SERIES_NC, cache_dir: Path = C.CACHE):
        self.ds = open_series(series_path)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.synthetic = bool(int(self.ds.attrs.get("synthetic", 0)))
        self.data_version = hashlib.sha1(
            str(self.ds.attrs.get("created", "")).encode()).hexdigest()[:7]
        t = pd.DatetimeIndex(self.ds["time"].values)
        self.first, self.last = t[0], t[-1]

    # ------------------------------------------------------------------ info
    @property
    def variables(self) -> list[str]:
        return [v for v in VARIABLES if v in self.ds.data_vars]

    def land_cells(self, bbox: BBox) -> tuple[np.ndarray, np.ndarray]:
        """Indices (i, j) of land cells whose centre is inside the box."""
        lat, lon = self.ds["lat"].values, self.ds["lon"].values
        li = np.where((lat >= bbox.south) & (lat <= bbox.north))[0]
        lj = np.where((lon >= bbox.west) & (lon <= bbox.east))[0]
        land = self.ds["land_mask"].values.astype(bool)
        I, J = np.meshgrid(li, lj, indexing="ij")
        keep = land[I, J]
        return I[keep], J[keep]

    def n_land_cells(self, bbox: BBox) -> int:
        return int(len(self.land_cells(bbox)[0]))

    # ------------------------------------------------------------------ guardrails
    def check(self, variable: str, area: Area, period) -> list[str]:
        warnings_: list[str] = []
        if variable not in self.variables:
            raise GuardrailError(f"We do not have data for '{variable}'. Available: "
                                 f"{', '.join(self.variables)}.")
        if not area.bbox.is_valid():
            raise GuardrailError(f"The box of '{area.name}' is not valid.")
        a, b = parse_period(period)
        if a < self.first or b > self.last:
            raise GuardrailError(f"Our data covers {self.first:%Y-%m} to {self.last:%Y-%m}.")
        years = (b.year - a.year) + (b.month - a.month + 1) / 12
        if years < C.MIN_YEARS:
            raise GuardrailError(f"{years:.1f} years is too short to measure a trend reliably "
                                 f"(we need at least {C.MIN_YEARS}).")
        if years < C.MIN_YEARS_WARN:
            warnings_.append(f"Trends over short periods ({years:.0f} years) are unreliable: "
                             "natural ups and downs can look like a trend.")
        n = self.n_land_cells(area.bbox)
        if n < C.MIN_CELLS:
            raise GuardrailError(f"'{area.name}' has only {n} land cells in our 1-degree grid "
                                 f"(minimum {C.MIN_CELLS}). Try a larger region.")
        if self.synthetic:
            warnings_.append("SYNTHETIC test data - these are not real NASA results.")
        return warnings_

    # ------------------------------------------------------------------ main entry
    def run(self, variable: str, area: Area, period=(C.PERIOD_START, C.PERIOD_END),
            use_cache: bool = True) -> tuple[pd.DataFrame, VariableResult]:
        period = [str(period[0]), str(period[1])]
        warn = self.check(variable, area, period)
        key = hashlib.sha1(json.dumps([variable, area.id, area.bbox.as_tuple(), period,
                                       self.data_version, C.FDR_Q]).encode()).hexdigest()[:16]
        cpath, jpath = self.cache_dir / f"{key}.parquet", self.cache_dir / f"{key}.json"
        if use_cache and cpath.exists() and jpath.exists():
            return pd.read_parquet(cpath), VariableResult.from_dict(json.loads(jpath.read_text()))

        a, b = parse_period(period)
        sub = self.ds[variable].sel(time=slice(a, b))
        months = pd.DatetimeIndex(sub["time"].values).month.values
        t_years = (np.arange(sub.sizes["time"]) / 12.0)
        I, J = self.land_cells(area.bbox)
        cube = sub.values[:, I, J]                       # (time, cells)
        lats, lons = self.ds["lat"].values[I], self.ds["lon"].values[J]

        rows = []
        for k in range(cube.shape[1]):
            r = stats.trend(cube[:, k], months, t_years)
            base = dict(cell_id=C.cell_id(lats[k], lons[k]), lat=float(lats[k]),
                        lon=float(lons[k]))
            if r is None:
                base.update(slope_dec=np.nan, ci_lo=np.nan, ci_hi=np.nan, p=np.nan, tau=np.nan,
                            n=0, years_needed=np.nan)
            else:
                base.update(r)
            rows.append(base)
        df = stats.add_fdr(pd.DataFrame(rows))
        spec = VARIABLES[variable]
        ds_spec = DATASETS[spec.dataset]
        unit = f"{spec.unit_target} per decade"
        run_id = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}-{self.data_version}"
        df.insert(0, "variable", variable)
        df["unit"] = unit
        df["region"] = area.id
        df["period"] = f"{period[0]}..{period[1]}"
        df["run_id"] = run_id
        df["datasets"] = f"{ds_spec.short_name} v{ds_spec.version}"

        reg = stats.regional_series(cube, lats)
        rt = stats.trend(reg, months, t_years)
        if rt is None:
            regional = RegionalTrend(None, [None, None], None, False)
        else:
            regional = RegionalTrend(
                slope_per_decade=rt["slope_dec"], ci95=[rt["ci_lo"], rt["ci_hi"]], p=rt["p"],
                significant=bool(rt["p"] <= 0.05), tau=rt["tau"], n_months=rt["n"],
                years_needed=None if rt["p"] <= 0.05 else rt["years_needed"])

        tested = df["p"].notna()
        w = stats.area_weights(df["lat"])
        wt = w[tested].sum() or 1.0
        up = (df["direction"] == "up")
        down = (df["direction"] == "down")
        counts = CellCounts(
            n=int(len(df)), n_tested=int(tested.sum()), sig_up=int(up.sum()),
            sig_down=int(down.sum()),
            pct_sig_area=round(100 * float(w[up | down].sum() / wt), 1),
            pct_sig_up_area=round(100 * float(w[up].sum() / wt), 1),
            pct_sig_down_area=round(100 * float(w[down].sum() / wt), 1))
        result = VariableResult(
            variable=variable, display_name=spec.display_name, unit=unit, region=area.id,
            period=period, regional=regional, cells=counts, method=METHOD_TEXT,
            datasets=[f"{ds_spec.short_name} v{ds_spec.version}"], run_id=run_id,
            warnings=warn, synthetic=self.synthetic)
        df.to_parquet(cpath, index=False)
        jpath.write_text(result.to_json())
        return df, result

    # ------------------------------------------------------------------ series for charts
    def regional_timeseries(self, variable: str, area: Area, period=(C.PERIOD_START,
                                                                      C.PERIOD_END)) -> pd.DataFrame:
        a, b = parse_period(period)
        sub = self.ds[variable].sel(time=slice(a, b))
        I, J = self.land_cells(area.bbox)
        cube = sub.values[:, I, J]
        reg = stats.regional_series(cube, self.ds["lat"].values[I])
        return self._series_frame(sub["time"].values, reg)

    def cell_timeseries(self, variable: str, lat: float, lon: float,
                        period=(C.PERIOD_START, C.PERIOD_END)) -> pd.DataFrame:
        a, b = parse_period(period)
        sub = self.ds[variable].sel(time=slice(a, b)).sel(lat=lat, lon=lon, method="nearest")
        return self._series_frame(sub["time"].values, sub.values)

    @staticmethod
    def _series_frame(times, values) -> pd.DataFrame:
        t = pd.DatetimeIndex(times)
        an = stats.anomalies(np.asarray(values, dtype="float64"), t.month.values)
        df = pd.DataFrame({"time": t, "value": values, "anomaly": an})
        ok = np.isfinite(an)
        if ok.sum() > 24:
            ty = np.arange(len(t)) / 12.0
            from scipy.stats import theilslopes
            s, i, lo, hi = theilslopes(an[ok], ty[ok], alpha=0.95)[:4]
            df["trend"] = i + s * ty
            # band from the slope CI, pivoting around the centre of the series
            tc = ty[ok].mean()
            yc = i + s * tc
            df["trend_lo"] = yc + lo * (ty - tc)
            df["trend_hi"] = yc + hi * (ty - tc)
        return df
