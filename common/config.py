"""Project-wide settings: region, grid, period, paths, thresholds, secrets.

Everything that the team agreed on in the kick-off (Document 2, section 5.1) lives here,
so there is exactly one place to change it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is in requirements
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(ROOT / ".env", override=False)

# ----------------------------------------------------------------------------- region
@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)

    def contains(self, other: "BBox") -> bool:
        return (self.west <= other.west and self.east >= other.east
                and self.south <= other.south and self.north >= other.north)

    def is_valid(self) -> bool:
        return self.west < self.east and self.south < self.north


REGION_ID = "mediterranean_north_africa"
REGION_NAME = "Mediterranean + North Africa"
REGION = BBox(west=-10.0, south=25.0, east=40.0, north=47.0)

# ----------------------------------------------------------------------------- grid
GRID_RES = 1.0
LATS = np.arange(REGION.south + GRID_RES / 2, REGION.north, GRID_RES)   # 25.5 .. 46.5 (22)
LONS = np.arange(REGION.west + GRID_RES / 2, REGION.east, GRID_RES)     # -9.5 .. 39.5 (50)


def cell_id(lat: float, lon: float) -> str:
    """Stable, human-readable id of a 1-degree cell, e.g. 'lat36.5_lon10.5'."""
    return f"lat{lat:.1f}_lon{lon:.1f}"


# ----------------------------------------------------------------------------- period
PERIOD_START = "2001-01"
PERIOD_END = "2024-12"

# ----------------------------------------------------------------------------- statistics
FDR_Q = 0.10              # Benjamini-Hochberg, Wilks (2016)
MIN_VALID_FRACTION = 0.8  # a cell needs >= 80% of its months to get a trend
MIN_YEARS_WARN = 15       # shorter periods get a warning
MIN_YEARS = 10            # shorter periods are refused
MIN_CELLS = 10            # smaller sub-regions are refused
BIN_MIN_FRACTION = 0.5    # when averaging to 1 deg, keep a cell if >= 50% of fine cells have data

# ----------------------------------------------------------------------------- paths
DATA = ROOT / "data"
RAW = DATA / "raw"            # downloaded NASA files (deleted after processing, one kept)
SMALL = DATA / "small"        # one small 1-degree file per dataset per month
PROCESSED = DATA / "processed"
CACHE = DATA / "cache"        # on-demand results
GRAPH_DIR = DATA / "graph"

SERIES_NC = PROCESSED / "series.nc"
TRENDS_PARQUET = PROCESSED / "trends.parquet"
REGIONAL_JSON = PROCESSED / "regional.json"
CLUSTERS_PARQUET = PROCESSED / "clusters.parquet"
CLUSTERS_JSON = PROCESSED / "clusters.json"
FINDINGS_JSON = PROCESSED / "findings.json"
GRAPH_JSON = GRAPH_DIR / "graph.json"
BUILD_LOG = GRAPH_DIR / "curator_build_log.jsonl"
INVESTIGATIONS = DATA / "investigations"

for _d in (RAW, SMALL, PROCESSED, CACHE, GRAPH_DIR, INVESTIGATIONS):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------- secrets / services
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE") or None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()

EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME", "")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD", "")

CMR_URL = "https://cmr.earthdata.nasa.gov/search"
HTTP_TIMEOUT = 30
