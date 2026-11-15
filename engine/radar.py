"""Radar-lite (Document 2, section 7): ranking, opposite trends, trend-signature clusters.

Golden rule: clusters only say "these places changed in a similar way". Whether each trend is
real is decided by the significance test, not by the clustering.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from common.contracts import VariableResult
from common.variables import VARIABLES

OPPOSITE_MIN_AREA = 10.0     # % of area that must go up AND down to call it an opposite pattern
MIN_CELLS_FOR_CLUSTERS = 60  # k-means on fewer cells mostly finds noise


def ranking(results: list[VariableResult]) -> pd.DataFrame:
    rows = [dict(variable=r.variable, display_name=r.display_name,
                 pct_sig_area=r.cells.pct_sig_area, pct_up=r.cells.pct_sig_up_area,
                 pct_down=r.cells.pct_sig_down_area,
                 regional_slope=r.regional.slope_per_decade, unit=r.unit,
                 regional_significant=r.regional.significant, regional_p=r.regional.p)
            for r in results]
    return pd.DataFrame(rows).sort_values("pct_sig_area", ascending=False).reset_index(drop=True)


def opposite_pattern(result: VariableResult) -> dict | None:
    """Both directions cover a large share of the area -> the regional mean hides the story."""
    up, down = result.cells.pct_sig_up_area, result.cells.pct_sig_down_area
    if up >= OPPOSITE_MIN_AREA and down >= OPPOSITE_MIN_AREA:
        return dict(variable=result.variable, pct_up=up, pct_down=down,
                    regional_slope=result.regional.slope_per_decade,
                    regional_significant=result.regional.significant)
    return None


def subregion_opposites(sub_results: dict[str, VariableResult]) -> list[dict]:
    """Pairs of sub-regions whose REGIONAL trends are significant in opposite directions."""
    sig = {rid: r for rid, r in sub_results.items()
           if r.regional.significant and r.regional.slope_per_decade}
    pairs = []
    ids = sorted(sig)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            sa, sb = sig[a].regional.slope_per_decade, sig[b].regional.slope_per_decade
            if sa * sb < 0:
                up, down = (a, b) if sa > 0 else (b, a)
                pairs.append(dict(variable=sig[a].variable, region_up=up, region_down=down,
                                  slope_up=max(sa, sb), slope_down=min(sa, sb)))
    return pairs


def co_occurrence(cells: dict[str, pd.DataFrame], min_overlap: float = 0.5) -> list[dict]:
    """Two variables with significant trends in mostly the same cells (overlap of the smaller set)."""
    sets = {v: set(df.loc[df["significant"], "cell_id"]) for v, df in cells.items()}
    out = []
    vs = sorted(sets)
    for i, a in enumerate(vs):
        for b in vs[i + 1:]:
            A, B = sets[a], sets[b]
            if not A or not B:
                continue
            inter = len(A & B)
            frac = inter / min(len(A), len(B))
            if frac >= min_overlap and inter >= 5:
                out.append(dict(var_a=a, var_b=b, shared_cells=inter, overlap=round(frac, 2)))
    return out


SIG_SHARE = 0.4   # a variable describes a cluster if >= 40% of its cells are significant that way


def _directions(cluster_cells: list[str], cells: dict[str, pd.DataFrame]) -> dict[str, str]:
    """For each variable: 'up' / 'down' if enough cells of the cluster have a SIGNIFICANT trend
    in that direction (real slopes + FDR, not the standardised values used for clustering)."""
    out = {}
    for v, df in cells.items():
        d = df.set_index("cell_id").loc[cluster_cells, "direction"]
        up, down = (d == "up").mean(), (d == "down").mean()
        if up >= SIG_SHARE and up > down:
            out[v] = "up"
        elif down >= SIG_SHARE and down > up:
            out[v] = "down"
    return out


def _signature_name(dirs: dict[str, str]) -> str:
    parts = [f"{VARIABLES[v].display_name.split(' (')[0]} {'↑' if d == 'up' else '↓'}"
             for v, d in dirs.items()]
    return ", ".join(parts) if parts else "no common significant change"


def _label(dirs: dict[str, str]) -> str:
    warm = dirs.get("t2m") == "up"
    dry = "down" in (dirs.get("precip"), dirs.get("soil_moisture"))
    wet = "up" in (dirs.get("precip"), dirs.get("soil_moisture"))
    green = dirs.get("ndvi") == "up"
    brown = dirs.get("ndvi") == "down"
    words = []
    if warm:
        words.append("warming")
    if dry:
        words.append("drying")
    if wet:
        words.append("wetting")
    if brown:
        words.append("browning")
    if green:
        words.append("greening")
    return " + ".join(words) if words else "mixed / weak change"


def clusters(cells: dict[str, pd.DataFrame], k_range=range(3, 7), seed: int = 0
             ) -> tuple[pd.DataFrame, list[dict]]:
    """k-means on standardised slopes (one row per cell, one column per variable)."""
    wide = pd.concat({v: df.set_index("cell_id")["slope_dec"] for v, df in cells.items()},
                     axis=1).dropna()
    if len(wide) < MIN_CELLS_FOR_CLUSTERS or wide.shape[1] < 2:
        return pd.DataFrame(), []      # too few cells or variables: clusters would be meaningless
    coords = next(iter(cells.values())).set_index("cell_id")[["lat", "lon"]]
    X = StandardScaler().fit_transform(wide.values)
    scores = {}
    for k in k_range:
        if k >= len(wide):
            break
        lab = KMeans(k, n_init=10, random_state=seed).fit_predict(X)
        scores[k] = silhouette_score(X, lab)
    best = max(scores, key=scores.get)
    labels = KMeans(best, n_init=10, random_state=seed).fit_predict(X)
    z = pd.DataFrame(X, index=wide.index, columns=wide.columns)
    z["cluster"] = labels
    summary = []
    for c in sorted(set(labels)):
        members = list(z.index[z["cluster"] == c])
        raw = wide.loc[members].mean()
        dirs = _directions(members, cells)
        summary.append(dict(cluster=int(c), n_cells=len(members),
                            label=_label(dirs), signature=_signature_name(dirs),
                            directions=dirs,
                            mean_slope_per_decade={k: round(float(v), 4) for k, v in raw.items()}))
    out = wide.copy()
    out["cluster"] = labels
    out = out.join(coords).reset_index().rename(columns={"index": "cell_id"})
    names = {s["cluster"]: s["label"] for s in summary}
    out["cluster_label"] = out["cluster"].map(names)
    for s in summary:
        s["silhouette"] = round(float(scores[best]), 3)
        s["k"] = int(best)
    return out, summary
