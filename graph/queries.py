"""The graph paths the investigator follows (Document 2, section 9.4).

Written once on top of the GraphStore interface, so they work on Neo4j and on graph.json.
Only nodes with status verified / from_paper are used as facts; hypotheses are never used.
The equivalent Cypher of each path is in docs/cypher_examples.md.
"""
from __future__ import annotations

import re

from common.config import BBox
from graph.store import GraphStore, parse_json_prop

FACT = ("verified", "from_paper")


def _is_fact(n: dict) -> bool:
    return n.get("status") in FACT


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z\-]+", text.lower()))


# ----------------------------------------------------------------------------- concepts
def concepts(store: GraphStore) -> list[dict]:
    return [c for c in store.nodes("Concept") if _is_fact(c)]


def find_concepts(store: GraphStore, text: str) -> list[dict]:
    """Concepts whose name or a synonym appears in the text (whole words / phrases)."""
    t = " " + " ".join(re.findall(r"[a-z0-9\-]+", text.lower())) + " "
    hits = []
    for c in concepts(store):
        terms = [c["name"]] + [str(s) for s in (parse_json_prop(c.get("synonyms")) or [])]
        matched = [x for x in terms if f" {x.lower()} " in t]
        if matched:
            hits.append({"id": c["id"], "name": c["name"], "matched": matched})
    return hits


# ----------------------------------------------------------------------------- regions
def regions(store: GraphStore) -> list[dict]:
    out = []
    for r in store.nodes("Region"):
        if not _is_fact(r):
            continue
        bb = parse_json_prop(r["bbox"])
        out.append({"id": r["id"], "code_id": r["code_id"], "name": r["name"],
                    "bbox": BBox(*map(float, bb)), "n_land_cells": r.get("n_land_cells"),
                    "parent": next((p["code_id"] for _, p in store.out(r["id"], "PART_OF")), None)})
    return sorted(out, key=lambda x: (x["parent"] is not None, x["name"]))


_GENERIC = {"north", "south", "east", "west", "and", "the", "margin", "peninsula", "delta"}


def find_region(store: GraphStore, text: str) -> dict | None:
    """The most specific region whose name (or a distinctive word of it) appears in the text."""
    words = _words(text)
    t = text.lower()
    best = None
    for r in regions(store):
        names = {r["name"].lower(), r["code_id"].replace("_", " ")}
        tokens = {w for n in names for w in _words(n) if w not in _GENERIC and len(w) > 3}
        if any(n in t for n in names) or tokens & words or \
                any(w.startswith(tok[:6]) for tok in tokens for w in words if len(tok) >= 6):
            if best is None or (r["n_land_cells"] or 1e9) < (best["n_land_cells"] or 1e9):
                best = r
    return best


def larger_region(store: GraphStore, region_code: str, min_cells: int) -> dict | None:
    """The nearest larger region in the graph (Document 2 section 6.3): the smallest region whose
    box contains this one and that has enough land cells - normally its PART_OF parent."""
    regs = regions(store)
    me = next((r for r in regs if r["code_id"] == region_code), None)
    if me is None:
        return None
    candidates = [r for r in regs if r["code_id"] != region_code
                  and (r["n_land_cells"] or 0) >= min_cells and r["bbox"].contains(me["bbox"])]
    return min(candidates, key=lambda r: r["n_land_cells"], default=None)


def sub_regions(store: GraphStore, region_code: str) -> list[dict]:
    rid = f"region:{region_code}"
    return [r for r in regions(store) if r["parent"] == region_code and r["id"] != rid]


# ----------------------------------------------------------------------------- variables
def variables_for_concepts(store: GraphStore, concept_ids: list[str]) -> list[dict]:
    """Concept <-INDICATOR_OF- Variable -IN_DATASET-> Dataset  (+ DRAWN_AS ChartStyle)."""
    seen: dict[str, dict] = {}
    for cid in concept_ids:
        for rel, v in store.inc(cid, "INDICATOR_OF"):
            if not _is_fact(v):
                continue
            why = {"concept": cid, "reason": rel.get("reason")}
            if v["id"] in seen:
                seen[v["id"]]["because"].append(why)
                continue
            seen[v["id"]] = variable_detail(store, v)
            seen[v["id"]]["because"] = [why]
    return list(seen.values())


def variable_detail(store: GraphStore, v: dict) -> dict:
    ds = next((d for _, d in store.out(v["id"], "IN_DATASET")), {})
    chart = next((c for _, c in store.out(v["id"], "DRAWN_AS")), {})
    return dict(
        id=v["id"], code_id=v["code_id"], display_name=v["display_name"],
        definition=v.get("definition_for_students"), unit=v.get("unit_target"),
        recipe=dict(name_in_file=v.get("name_in_file"), group=v.get("group"),
                    unit_native=v.get("unit_native"), conversion=v.get("conversion"),
                    fill_value=v.get("fill_value"), scale_factor=v.get("scale_factor"),
                    source=v.get("recipe_source")),
        dataset=dict(id=ds.get("id"), short_name=ds.get("short_name"),
                     version=ds.get("version"), title=ds.get("title"), doi=ds.get("doi"),
                     cmr_concept_id=ds.get("cmr_concept_id")),
        chart_style=dict(id=chart.get("id"), chart_type=chart.get("chart_type"),
                         colormap=chart.get("colormap"),
                         label_template=chart.get("label_template")),
        kind=v.get("kind"))


def all_variables(store: GraphStore) -> list[dict]:
    return [variable_detail(store, v) for v in store.nodes("Variable") if _is_fact(v)]


# ----------------------------------------------------------------------------- strategy
def method_chain(store: GraphStore, stage: str | None = None) -> list[dict]:
    """Follow NEXT from the method with no predecessor."""
    methods = {m["id"]: m for m in store.nodes("Method") if _is_fact(m)}
    starts = [m for m in methods.values() if not store.inc(m["id"], "NEXT")]
    chain, cur, guard = [], (starts[0] if starts else None), 0
    while cur is not None and guard < 50:
        chain.append(cur)
        nxt = [n for _, n in store.out(cur["id"], "NEXT") if n["id"] in methods]
        cur, guard = (nxt[0] if nxt else None), guard + 1
    if stage:
        chain = [m for m in chain if m.get("stage") == stage]
    return [dict(id=m["id"], name=m["name"], stage=m.get("stage"), order=m.get("order"),
                 description=m.get("description"),
                 parameters=parse_json_prop(m.get("parameters"))) for m in chain]


def hypothesis_patterns(store: GraphStore) -> list[dict]:
    return [dict(id=p["id"], name=p["name"], description=p["description"], cypher=p["cypher"])
            for p in store.nodes("HypothesisPattern")]


# ----------------------------------------------------------------------------- literature
def mechanisms(store: GraphStore, variable_id: str) -> list[dict]:
    """INFLUENCES edges into and out of a variable, with their paper and quote."""
    out = []
    for direction, pairs in (("out", store.out(variable_id, "INFLUENCES")),
                             ("in", store.inc(variable_id, "INFLUENCES"))):
        for rel, other in pairs:
            paper = store.get(rel.get("paper_id", "")) or {}
            src, dst = (variable_id, other["id"]) if direction == "out" else (other["id"], variable_id)
            out.append(dict(source_variable=src, target_variable=dst, sign=rel.get("sign"),
                            quote=rel.get("quote"), paper_id=rel.get("paper_id"),
                            paper_title=paper.get("title"), paper_year=paper.get("year"),
                            doi=paper.get("doi"), status=rel.get("status")))
    return out


def findings_in(store: GraphStore, region_code: str, period: list[str]) -> list[dict]:
    return [f for f in store.nodes("Finding")
            if f.get("region") == region_code and parse_json_prop(f.get("period")) == list(period)]
