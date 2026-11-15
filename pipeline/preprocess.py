"""Phase 1b - turn NASA files into one clean cube: data/processed/series.nc.

Per granule (one month of one dataset):  read -> cut region -> convert units -> average to 1 deg
-> save a tiny .npz in data/small/<dataset>/<YYYY-MM>.npz.
Then build_series() stacks all months of all variables, applies the land mask and writes series.nc.

Averaging rule (same for every dataset): a 1-degree cell is the mean of all fine cells whose
centre falls inside it; it is kept only if at least BIN_MIN_FRACTION of those fine cells have data.
"""
from __future__ import annotations

import calendar
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from common import config as C
from common.variables import DATASETS, VARIABLE_ORDER, VARIABLES

log = logging.getLogger(__name__)

NLAT, NLON = len(C.LATS), len(C.LONS)


# ----------------------------------------------------------------------------- grid helpers
def bin_to_grid(values: np.ndarray, lats: np.ndarray, lons: np.ndarray,
                min_fraction: float = C.BIN_MIN_FRACTION) -> np.ndarray:
    """Average a fine (lat, lon) field onto our 1-degree grid. Returns (NLAT, NLON) with NaN."""
    values = np.asarray(values, dtype="float64")
    if values.shape != (len(lats), len(lons)):
        raise ValueError(f"shape {values.shape} does not match lat/lon {len(lats)}x{len(lons)}")
    li = np.floor((np.asarray(lats) - C.REGION.south) / C.GRID_RES).astype(int)
    lj = np.floor((np.asarray(lons) - C.REGION.west) / C.GRID_RES).astype(int)
    lat_ok = (li >= 0) & (li < NLAT)
    lon_ok = (lj >= 0) & (lj < NLON)
    sub = values[np.ix_(lat_ok, lon_ok)]
    I, J = np.meshgrid(li[lat_ok], lj[lon_ok], indexing="ij")
    valid = np.isfinite(sub)
    total = np.zeros((NLAT, NLON))
    count = np.zeros((NLAT, NLON))
    acc = np.zeros((NLAT, NLON))
    np.add.at(total, (I, J), 1)
    np.add.at(count, (I[valid], J[valid]), 1)
    np.add.at(acc, (I[valid], J[valid]), sub[valid])
    out = np.full((NLAT, NLON), np.nan)
    keep = (total > 0) & (count >= min_fraction * total)
    out[keep] = acc[keep] / count[keep]
    return out


# ----------------------------------------------------------------------------- month keys
_MONTH_PATTERNS = {
    "merra2": re.compile(r"\.(\d{4})(\d{2})\.nc4"),
    "gldas": re.compile(r"\.A(\d{4})(\d{2})\."),
    "imerg": re.compile(r"3IMERG\.(\d{4})(\d{2})\d{2}"),
}


def month_key(dataset: str, filename: str) -> str:
    """'YYYY-MM' from a NASA file name."""
    name = Path(filename).name
    if dataset == "modis_ndvi":
        m = re.search(r"\.A(\d{4})(\d{3})\.", name)
        if not m:
            raise ValueError(f"cannot read the month from {name}")
        d = datetime.strptime(m.group(1) + m.group(2), "%Y%j")
        return f"{d.year:04d}-{d.month:02d}"
    m = _MONTH_PATTERNS[dataset].search(name)
    if not m:
        raise ValueError(f"cannot read the month from {name}")
    return f"{m.group(1)}-{m.group(2)}"


def days_in_month(key: str) -> int:
    y, m = map(int, key.split("-"))
    return calendar.monthrange(y, m)[1]


# ----------------------------------------------------------------------------- readers
def read_merra2(path: Path) -> dict[str, np.ndarray]:
    with xr.open_dataset(path) as ds:
        t2m = ds["T2M"].isel(time=0).load()
        lats, lons = ds["lat"].values, ds["lon"].values
    return {"t2m": bin_to_grid(t2m.values - 273.15, lats, lons)}


def read_gldas(path: Path) -> dict[str, np.ndarray]:
    with xr.open_dataset(path) as ds:
        sm = ds["SoilMoi0_10cm_inst"].isel(time=0).load().values
        et = ds["Evap_tavg"].isel(time=0).load().values
        lats, lons = ds["lat"].values, ds["lon"].values
    return {"soil_moisture": bin_to_grid(sm, lats, lons),
            "et": bin_to_grid(et * 86400.0, lats, lons)}


def read_imerg(path: Path, key: str) -> dict[str, np.ndarray]:
    import h5py
    with h5py.File(path, "r") as f:
        pr = f["Grid/precipitation"][0]          # (lon, lat) in IMERG files
        lats = f["Grid/lat"][:]
        lons = f["Grid/lon"][:]
    pr = np.asarray(pr, dtype="float64")
    if pr.shape == (len(lons), len(lats)):
        pr = pr.T                                # -> (lat, lon)
    pr[pr < 0] = np.nan                          # fill value is -9999.9
    hours = 24.0 * days_in_month(key)
    return {"precip": bin_to_grid(pr * hours, lats, lons)}


def read_modis_ndvi(path: Path) -> dict[str, np.ndarray]:
    from pyhdf.SD import SD, SDC
    res = 0.05
    r0, r1 = int(round((90 - C.REGION.north) / res)), int(round((90 - C.REGION.south) / res))
    c0, c1 = int(round((C.REGION.west + 180) / res)), int(round((C.REGION.east + 180) / res))
    sd = SD(str(path), SDC.READ)
    try:
        sds = sd.select(VARIABLES["ndvi"].name_in_file)
        raw = sds[r0:r1, c0:c1].astype("float64")
        attrs = sds.attributes()
        sds.endaccess()
    finally:
        sd.end()
    fill = attrs.get("_FillValue", -3000)
    vmin, vmax = attrs.get("valid_range", (-2000, 10000))
    raw[(raw == fill) | (raw < vmin) | (raw > vmax)] = np.nan
    scale = float(attrs.get("scale_factor", 10000.0))
    ndvi = raw / scale if scale > 1 else raw * scale       # MODIS convention: value / 10000
    lats = 90 - (np.arange(r0, r1) + 0.5) * res
    lons = -180 + (np.arange(c0, c1) + 0.5) * res
    return {"ndvi": bin_to_grid(ndvi, lats, lons)}


def process_granule(dataset: str, path: Path) -> Path:
    """Read one NASA file and save the 1-degree result. Returns the small file path."""
    key = month_key(dataset, path.name)
    if dataset == "merra2":
        fields = read_merra2(path)
    elif dataset == "gldas":
        fields = read_gldas(path)
    elif dataset == "imerg":
        fields = read_imerg(path, key)
    elif dataset == "modis_ndvi":
        fields = read_modis_ndvi(path)
    else:
        raise ValueError(f"unknown dataset {dataset}")
    out = C.SMALL / dataset / f"{key}.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, source=np.array(path.name), **fields)
    return out


# ----------------------------------------------------------------------------- series.nc
def month_range(start: str = C.PERIOD_START, end: str = C.PERIOD_END) -> pd.DatetimeIndex:
    return pd.date_range(start + "-01", end + "-01", freq="MS")


def build_series(start: str = C.PERIOD_START, end: str = C.PERIOD_END,
                 out: Path = C.SERIES_NC) -> Path:
    """Stack the small monthly files into series.nc (time, lat, lon) with a land mask."""
    times = month_range(start, end)
    data: dict[str, np.ndarray] = {}
    missing: dict[str, list[str]] = {}
    sources: dict[str, int] = {}
    for vid in VARIABLE_ORDER:
        spec = VARIABLES[vid]
        folder = C.SMALL / spec.dataset
        cube = np.full((len(times), NLAT, NLON), np.nan, dtype="float32")
        miss = []
        n_files = 0
        for t, ts in enumerate(times):
            f = folder / f"{ts:%Y-%m}.npz"
            if not f.exists():
                miss.append(f"{ts:%Y-%m}")
                continue
            with np.load(f) as z:
                if vid in z:
                    cube[t] = z[vid]
                    n_files += 1
                else:
                    miss.append(f"{ts:%Y-%m}")
        if n_files == 0:
            log.warning("no data at all for %s (%s) - variable skipped", vid, spec.dataset)
            continue
        data[vid] = cube
        missing[vid] = miss
        sources[vid] = n_files
        log.info("%s: %d/%d months", vid, n_files, len(times))
    if not data:
        raise RuntimeError("No processed months found in data/small. Run `python run.py download` "
                           "first.")
    land = land_mask_from(data)
    ds = make_dataset(data, times, land, synthetic=False,
                      extra_attrs={"months_missing": json.dumps(missing),
                                   "months_present": json.dumps(sources)})
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)
    return out


def land_mask_from(data: dict[str, np.ndarray]) -> np.ndarray:
    """Land = cells where GLDAS soil moisture exists in >= 80% of months (GLDAS has no ocean).
    Falls back to an offline coastline mask if GLDAS is not available."""
    if "soil_moisture" in data:
        frac = np.isfinite(data["soil_moisture"]).mean(axis=0)
        return frac >= 0.8
    log.warning("GLDAS missing: using the offline land mask instead")
    return offline_land_mask()


def offline_land_mask() -> np.ndarray:
    from global_land_mask import globe
    fine = np.arange(0.05, 1.0, 0.1)
    mask = np.zeros((NLAT, NLON), dtype=bool)
    for i, lat in enumerate(C.LATS):
        for j, lon in enumerate(C.LONS):
            la, lo = np.meshgrid(lat - 0.5 + fine, lon - 0.5 + fine, indexing="ij")
            mask[i, j] = globe.is_land(la, lo).mean() >= 0.5
    return mask


def make_dataset(data: dict[str, np.ndarray], times: pd.DatetimeIndex, land: np.ndarray,
                 synthetic: bool, extra_attrs: dict | None = None) -> xr.Dataset:
    coords = {"time": times, "lat": C.LATS, "lon": C.LONS}
    dvars = {}
    for vid, cube in data.items():
        spec = VARIABLES[vid]
        ds_spec = DATASETS[spec.dataset]
        arr = np.where(land[None, :, :], cube, np.nan).astype("float32")
        dvars[vid] = (("time", "lat", "lon"), arr, {
            "long_name": spec.display_name, "units": spec.unit_target,
            "dataset": ds_spec.short_name, "version": ds_spec.version,
            "name_in_file": spec.name_in_file, "conversion": spec.conversion})
    dvars["land_mask"] = (("lat", "lon"), land.astype("int8"), {"long_name": "1 = land"})
    attrs = {
        "title": "EarthSleuth monthly series, 1 degree",
        "region": C.REGION_ID, "bbox": json.dumps(C.REGION.as_tuple()),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "synthetic": int(synthetic),
    }
    attrs.update(extra_attrs or {})
    return xr.Dataset(dvars, coords=coords, attrs=attrs)
