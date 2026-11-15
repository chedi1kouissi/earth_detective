"""Precompute the whole region (the cache the app opens with): trends.parquet, regional.json,
clusters.parquet, clusters.json, findings.json."""
from __future__ import annotations

import json
import logging

import pandas as pd

from common import config as C
from common.config import BBox
from common.variables import SUBREGIONS, VARIABLE_ORDER
from engine.analysis import Area, TrendEngine
from engine.findings import analyse_area

log = logging.getLogger(__name__)


def main_area() -> Area:
    return Area(C.REGION_ID, C.REGION_NAME, C.REGION)


def default_subareas() -> list[Area]:
    return [Area(k, name, BBox(*bb)) for k, (name, bb) in SUBREGIONS.items()]


def precompute(period=(C.PERIOD_START, C.PERIOD_END)) -> dict:
    engine = TrendEngine()
    variables = [v for v in VARIABLE_ORDER if v in engine.variables]
    pkg = analyse_area(engine, main_area(), variables, list(period), default_subareas())
    cells: dict[str, pd.DataFrame] = pkg.pop("_cells")
    clusters: pd.DataFrame = pkg.pop("_clusters")
    pd.concat(cells.values(), ignore_index=True).to_parquet(C.TRENDS_PARQUET, index=False)
    C.REGIONAL_JSON.write_text(json.dumps({"results": pkg["results"],
                                           "sub_results": pkg["sub_results"]}, indent=2))
    if not clusters.empty:
        clusters.to_parquet(C.CLUSTERS_PARQUET, index=False)
    C.CLUSTERS_JSON.write_text(json.dumps(
        [f for f in pkg["findings"] if f["kind"] == "cluster"], indent=2))
    C.FINDINGS_JSON.write_text(json.dumps(pkg, indent=2, default=str))
    log.info("precompute done: %d findings, %d opposite pairs, %d co-occurrences",
             len(pkg["findings"]), len(pkg["opposite_pairs"]), len(pkg["co_occurs"]))
    return pkg
