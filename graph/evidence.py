"""Layer B writer (Document 2, section 8.2). Plain code: numbers go from the engine straight
into the graph, never through the LLM."""
from __future__ import annotations

from graph.store import GraphStore

WHO = "code"


def variable_node_id(store: GraphStore, code_id: str) -> str | None:
    for v in store.nodes("Variable"):
        if v.get("code_id") == code_id:
            return v["id"]
    return None


def region_node_id(code_id: str) -> str:
    return f"region:{code_id}"


def write_evidence(store: GraphStore, pkg: dict) -> dict:
    """Write Analysis, Finding, OPPOSITE_OF and CO_OCCURS_WITH from an analyse_area() package."""
    a = pkg["analysis"]
    src = f"EarthSleuth engine run {a['run_id']}" + (" (SYNTHETIC data)" if a.get("synthetic") else "")
    store.merge_node("Analysis", a["id"], dict(
        run_id=a["run_id"], region=a["region"], period=list(a["period"]), methods=a["methods"],
        synthetic=bool(a.get("synthetic")), data_version=a.get("data_version")),
        source=src, created_by=WHO)
    if store.get(region_node_id(a["region"])):
        store.merge_rel(a["id"], "IN_REGION", region_node_id(a["region"]), source=src,
                        created_by=WHO)
    for m in store.nodes("Method"):
        store.merge_rel(a["id"], "USED_METHOD", m["id"], source=src, created_by=WHO)

    written, skipped = [], []
    for f in pkg["findings"]:
        props = {k: v for k, v in f.items() if k not in ("id",)}
        props["period"] = list(f["period"])
        store.merge_node("Finding", f["id"], props, source=src, created_by=WHO)
        store.merge_rel(f["id"], "FROM_ANALYSIS", a["id"], source=src, created_by=WHO)
        rid = region_node_id(f["region"])
        if store.get(rid):
            store.merge_rel(f["id"], "IN_REGION", rid, source=src, created_by=WHO)
        else:
            skipped.append(f"{f['id']}: region {rid} not in graph")
        if f["kind"] == "trend":
            vid = variable_node_id(store, f["variable"])
            if vid:
                store.merge_rel(f["id"], "ABOUT", vid, source=src, created_by=WHO)
        elif f["kind"] == "cluster":
            for code in (f.get("directions") or {}):
                vid = variable_node_id(store, code)
                if vid:
                    store.merge_rel(f["id"], "ABOUT", vid,
                                    {"direction": f["directions"][code]}, source=src,
                                    created_by=WHO)
        written.append(f["id"])

    for p in pkg.get("opposite_pairs", []):
        if store.get(p["finding_up"]) and store.get(p["finding_down"]):
            store.merge_rel(p["finding_up"], "OPPOSITE_OF", p["finding_down"],
                            {"variable": p["variable"]}, source=src, created_by=WHO)
    for c in pkg.get("co_occurs", []):
        if store.get(c["finding_a"]) and store.get(c["finding_b"]):
            store.merge_rel(c["finding_a"], "CO_OCCURS_WITH", c["finding_b"],
                            {"shared_cells": c["shared_cells"], "overlap": c["overlap"]},
                            source=src, created_by=WHO)
    return {"analysis": a["id"], "findings": len(written), "skipped": skipped}
