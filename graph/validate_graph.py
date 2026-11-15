"""Automatic checks after every graph build (Document 2, section 8.7).

Returns a list of human-readable problems; an empty list means the graph passed.
"""
from __future__ import annotations

import re

from common.variables import DATASETS, VARIABLES
from graph.store import GraphStore, load_schema

# equivalent spellings of the native units we expect (file / CMR / reference)
_UNIT_ALIASES = {
    "k": "K", "kelvin": "K",
    "mm/hr": "mm/h", "mmhr-1": "mm/h", "mm/h": "mm/h", "mmh-1": "mm/h",
    "kgm-2": "kg/m2", "kg/m2": "kg/m2", "kg/m^2": "kg/m2",
    "kgm-2s-1": "kg/m2/s", "kg/m2/s": "kg/m2/s", "kg/m^2/s": "kg/m2/s",
}


def norm_unit(u) -> str:
    s = re.sub(r"[\s*^]", "", str(u or "")).lower()
    return _UNIT_ALIASES.get(s, s)


def validate(store: GraphStore) -> list[str]:
    problems: list[str] = []
    schema = load_schema()
    nodes = store.nodes()
    rels = store.rels()

    # 1. no node or edge type outside the schema
    for n in nodes:
        if n["label"] not in schema["nodes"]:
            problems.append(f"{n['id']}: label {n['label']} is not in the schema")
    for r in rels:
        if r["type"] not in schema["relationships"]:
            problems.append(f"{r['src']}-{r['type']}->{r['dst']}: type not in the schema")

    # 2. no duplicates: two nodes with the same name or synonym (same label)
    seen: dict[tuple[str, str], str] = {}
    for n in nodes:
        names = [n.get("name"), n.get("display_name"), n.get("code_id")]
        syn = n.get("synonyms") or []
        names += list(syn) if isinstance(syn, list) else [syn]
        for nm in {str(x).strip().lower() for x in names if x}:
            key = (n["label"], nm)
            if key in seen and seen[key] != n["id"]:
                problems.append(f"duplicate {n['label']} name '{nm}': {seen[key]} and {n['id']}")
            seen.setdefault(key, n["id"])

    # 3. every Variable is usable: dataset, complete recipe, chart style, >= 1 concept
    recipe = ["name_in_file", "unit_native", "unit_target", "conversion", "kind"]
    for v in store.nodes("Variable"):
        vid = v["id"]
        if not store.out(vid, "IN_DATASET"):
            problems.append(f"{vid}: no IN_DATASET link")
        miss = [k for k in recipe if not v.get(k)]
        if miss:
            problems.append(f"{vid}: incomplete recipe {miss}")
        if not store.out(vid, "DRAWN_AS"):
            problems.append(f"{vid}: no chart style (DRAWN_AS)")
        if not store.out(vid, "INDICATOR_OF"):
            problems.append(f"{vid}: not linked to any Concept (INDICATOR_OF)")
        # 5. recipes match the team's reference table (catches hallucinated units)
        ref = VARIABLES.get(v.get("code_id", ""))
        if ref is None:
            problems.append(f"{vid}: code_id '{v.get('code_id')}' is not one of our variables")
            continue
        if v.get("name_in_file") != ref.name_in_file:
            problems.append(f"{vid}: name_in_file {v.get('name_in_file')} != reference "
                            f"{ref.name_in_file}")
        if ref.dataset != "modis_ndvi" and norm_unit(v.get("unit_native")) != norm_unit(ref.unit_native):
            problems.append(f"{vid}: native unit '{v.get('unit_native')}' does not match the "
                            f"reference '{ref.unit_native}' - check the conversion")
        if v.get("unit_target") != ref.unit_target or v.get("conversion") != ref.conversion:
            problems.append(f"{vid}: target unit / conversion differ from the reference")
        if v.get("kind") != ref.kind:
            problems.append(f"{vid}: kind '{v.get('kind')}' != reference '{ref.kind}'")

    # every dataset we use is in the graph
    for d in DATASETS.values():
        if not store.get(f"dataset:{d.short_name}_v{d.version}"):
            problems.append(f"Dataset {d.short_name} v{d.version} is missing")

    # 4. every INFLUENCES edge has a Paper and a quote
    for r in store.rels("INFLUENCES"):
        if not r.get("quote") or not r.get("paper_id"):
            problems.append(f"{r['src']}-INFLUENCES->{r['dst']}: no paper or quote")
        elif store.get(r["paper_id"]) is None:
            problems.append(f"{r['src']}-INFLUENCES->{r['dst']}: paper {r['paper_id']} missing")

    # papers must have a reader
    for p in store.nodes("Paper"):
        if not p.get("read_by"):
            problems.append(f"{p['id']}: nobody is listed in read_by")

    # hypotheses are never verified facts
    for h in store.nodes("Hypothesis"):
        if h.get("status") != "hypothesis":
            problems.append(f"{h['id']}: hypothesis with status {h.get('status')}")

    # concepts must have synonyms; the method chain must be a single line
    for c in store.nodes("Concept"):
        if not c.get("synonyms"):
            problems.append(f"{c['id']}: no synonyms")
    methods = store.nodes("Method")
    if methods:
        starts = [m for m in methods if not store.inc(m["id"], "NEXT")]
        if len(starts) != 1:
            problems.append(f"the Method chain should have exactly one start, found "
                            f"{[m['id'] for m in starts]}")
    return problems
