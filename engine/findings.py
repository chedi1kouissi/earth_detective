"""Turn engine results into evidence (Layer B input): findings, opposite pairs, co-occurrences,
clusters. This is plain code - the numbers never pass through the LLM.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from common import config as C
from common.contracts import VariableResult
from engine import radar
from engine.analysis import METHOD_TEXT, Area, GuardrailError, TrendEngine


def finding_id(variable: str, region: str, period: list[str]) -> str:
    return f"finding:{variable}:{region}:{period[0]}_{period[1]}"


def cluster_finding_id(region: str, period: list[str], label: str, c: int) -> str:
    return f"finding:cluster{c}:{region}:{period[0]}_{period[1]}"


def _trend_finding(r: VariableResult) -> dict:
    return dict(
        id=finding_id(r.variable, r.region, r.period), kind="trend", variable=r.variable,
        region=r.region, period=r.period, unit=r.unit,
        slope_per_decade=r.regional.slope_per_decade, ci95=r.regional.ci95, p=r.regional.p,
        significant=r.regional.significant,
        direction="up" if (r.regional.slope_per_decade or 0) > 0 else "down",
        pct_sig_up_area=r.cells.pct_sig_up_area, pct_sig_down_area=r.cells.pct_sig_down_area,
        datasets=r.datasets, run_id=r.run_id, synthetic=r.synthetic,
        summary=(f"{r.display_name} {'increased' if (r.regional.slope_per_decade or 0) > 0 else 'decreased'} "
                 f"by {abs(r.regional.slope_per_decade):.3g} {r.unit} over {r.period[0]}..{r.period[1]} "
                 f"(p = {r.regional.p:.3g})"))


def analyse_area(engine: TrendEngine, area: Area, variables: list[str], period: list[str],
                 subareas: list[Area] | None = None) -> dict:
    """Run every variable on an area (+ optional sub-areas) and build the evidence package."""
    results: dict[str, VariableResult] = {}
    cells: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for v in variables:
        try:
            df, r = engine.run(v, area, period)
            results[v], cells[v] = r, df
        except GuardrailError as e:
            errors[v] = str(e)

    findings = [_trend_finding(r) for r in results.values() if r.regional.significant]
    patterns = [p for p in (radar.opposite_pattern(r) for r in results.values()) if p]

    # sub-area trends -> sub-area findings + opposite pairs between sub-areas
    opposite_pairs: list[dict] = []
    sub_results: dict[str, dict[str, VariableResult]] = {}
    for sa in subareas or []:
        for v in results:
            try:
                _, r = engine.run(v, sa, period)
            except GuardrailError:
                continue
            sub_results.setdefault(v, {})[sa.id] = r
            if r.regional.significant:
                findings.append(_trend_finding(r))
    for v, per_region in sub_results.items():
        for pair in radar.subregion_opposites(per_region):
            opposite_pairs.append(dict(
                variable=v,
                finding_up=finding_id(v, pair["region_up"], period),
                finding_down=finding_id(v, pair["region_down"], period),
                region_up=pair["region_up"], region_down=pair["region_down"],
                slope_up=pair["slope_up"], slope_down=pair["slope_down"]))

    fids = {f["id"] for f in findings}
    co = []
    for c in radar.co_occurrence(cells):
        fa, fb = finding_id(c["var_a"], area.id, period), finding_id(c["var_b"], area.id, period)
        if fa in fids and fb in fids:
            co.append(dict(finding_a=fa, finding_b=fb, **c))

    cl_table, cl_summary = radar.clusters(cells)
    cluster_findings = [dict(
        id=cluster_finding_id(area.id, period, s["label"], s["cluster"]), kind="cluster",
        region=area.id, period=period, cluster_label=s["label"], signature=s["signature"],
        n_cells=s["n_cells"], directions=s["directions"],
        mean_slope_per_decade=s["mean_slope_per_decade"], silhouette=s["silhouette"], k=s["k"],
        summary=f"Cluster '{s['label']}' ({s['n_cells']} cells): {s['signature']}")
        for s in cl_summary]

    run_id = next(iter(results.values())).run_id if results else \
        f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}"
    return dict(
        analysis=dict(id=f"analysis:{run_id}:{area.id}", run_id=run_id, region=area.id,
                      period=period, methods=METHOD_TEXT, synthetic=engine.synthetic,
                      created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      data_version=engine.data_version),
        results={v: r.to_dict() for v, r in results.items()},
        sub_results={v: {k: r.to_dict() for k, r in d.items()} for v, d in sub_results.items()},
        errors=errors, findings=findings + cluster_findings, opposite_patterns=patterns,
        opposite_pairs=opposite_pairs, co_occurs=co,
        _cells=cells, _clusters=cl_table)
