"""Load the hand-written backup seed.yaml (offline, no CMR, no LLM). Same schema as the curator."""
from __future__ import annotations

from pathlib import Path

import yaml

from common import config as C
from common.config import BBox
from common.variables import DATASETS, VARIABLES
from graph.curator_tools import dataset_node_id, slug, strategy
from graph.store import GraphStore

SEED = Path(__file__).with_name("seed.yaml")
WHO = "human"


def _land_cells(bbox: BBox) -> int:
    try:
        from engine.analysis import TrendEngine
        return TrendEngine().n_land_cells(bbox)
    except FileNotFoundError:
        return 0


def load_seed(store: GraphStore, path: Path = SEED) -> dict:
    seed = yaml.safe_load(path.read_text(encoding="utf-8"))
    src = "seed.yaml (hand-written, checked against CMR)"

    for d in seed["datasets"]:
        ref = next(x for x in DATASETS.values() if x.short_name == d["short_name"])
        did = dataset_node_id(d["short_name"], str(d["version"]))
        store.merge_node("Dataset", did, dict(
            short_name=d["short_name"], version=str(d["version"]), title=d["title"],
            cmr_concept_id=d["cmr_concept_id"], doi=d.get("doi"), provider=d["provider"],
            time_start=str(d["time_start"]), local_key=d["local_key"],
            file_format=ref.file_format, native_resolution=ref.native_res),
            source=src, created_by=WHO)
        for m in d.get("missions", []):
            mid = f"mission:{slug(m['name'])}"
            store.merge_node("Mission", mid, {"name": m["name"]}, source=src, created_by=WHO)
            if not m.get("instruments"):
                store.merge_rel(mid, "PROVIDES", did, source=src, created_by=WHO)
            for ins in m.get("instruments", []):
                iid = f"instrument:{slug(ins)}"
                store.merge_node("Instrument", iid, {"name": ins}, source=src, created_by=WHO)
                store.merge_rel(mid, "CARRIES", iid, source=src, created_by=WHO)
                store.merge_rel(iid, "PROVIDES", did, source=src, created_by=WHO)

    for name, syns in seed["concepts"].items():
        store.merge_node("Concept", f"concept:{slug(name)}", {"name": name, "synonyms": syns},
                         source=src, created_by=WHO)

    st = strategy()
    for m in st["methods"]:
        store.merge_node("Method", f"method:{m['id']}", dict(
            name=m["name"], order=m["order"], stage=m["stage"], description=m["description"],
            applies_to_kind=m["applies_to_kind"], parameters=m["parameters"]),
            source="graph/strategy.yaml", created_by=WHO)
    ms = sorted(st["methods"], key=lambda x: x["order"])
    for a, b in zip(ms, ms[1:]):
        store.merge_rel(f"method:{a['id']}", "NEXT", f"method:{b['id']}",
                        source="graph/strategy.yaml", created_by=WHO)
    for s in st["chart_styles"]:
        store.merge_node("ChartStyle", f"chart:{s['id']}", dict(
            chart_type=s["chart_type"], colormap=s["colormap"], label_template=s["label_template"]),
            source="graph/strategy.yaml", created_by=WHO)
    for p in st["hypothesis_patterns"]:
        store.merge_node("HypothesisPattern", f"pattern:{p['id']}", dict(
            name=p["name"], description=p["description"].strip(), cypher=p["cypher"].strip()),
            source="graph/strategy.yaml", created_by=WHO)

    for v in seed["variables"]:
        spec = next(x for x in VARIABLES.values()
                    if DATASETS[x.dataset].short_name == v["dataset"]
                    and x.name_in_file == v["name_in_file"])
        ds = DATASETS[spec.dataset]
        did = dataset_node_id(ds.short_name, ds.version)
        vid = f"var:{ds.short_name}/{spec.name_in_file}"
        store.merge_node("Variable", vid, dict(
            code_id=spec.id, display_name=spec.display_name,
            definition_for_students=spec.definition_for_students, name_in_file=spec.name_in_file,
            group=spec.group, unit_native=v["unit_native"], unit_target=spec.unit_target,
            conversion=spec.conversion, scale_factor=v.get("scale_factor"),
            add_offset=v.get("add_offset"), fill_value=v.get("fill_value"),
            cf_standard_name=spec.cf_standard_name, kind=v["kind"], recipe_source=src),
            source=src, created_by=WHO)
        store.merge_rel(vid, "IN_DATASET", did, source=src, created_by=WHO)
        store.merge_rel(did, "HAS_VARIABLE", vid, source=src, created_by=WHO)
        store.merge_rel(vid, "DRAWN_AS", f"chart:{v['chart']}", source=src, created_by=WHO)
        for concept, reason in v["concepts"].items():
            store.merge_rel(vid, "INDICATOR_OF", f"concept:{slug(concept)}", {"reason": reason},
                            source=src, created_by=WHO)

    for r in seed["regions"]:
        bbox = BBox(*map(float, r["bbox"]))
        rid = f"region:{r['code_id']}"
        store.merge_node("Region", rid, dict(
            code_id=r["code_id"], name=r["name"], bbox=list(bbox.as_tuple()),
            n_land_cells=_land_cells(bbox)), source=src, created_by=WHO)
    for r in seed["regions"]:
        if r.get("parent"):
            store.merge_rel(f"region:{r['code_id']}", "PART_OF", f"region:{r['parent']}",
                            source=src, created_by=WHO)
    return store.counts()
