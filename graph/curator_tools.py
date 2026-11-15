"""The checking tools of the curator agent (Document 2, section 8.6).

The agent decides WHAT to add; these tools decide whether the fact is TRUE.
- Facts with numbers (units, fill values, dates, ids, DOIs) come from CMR, the real file or
  Crossref - never from the LLM.
- Every write goes through GraphStore, which enforces the schema (Contract 0) and uses MERGE.
- A refused call returns {"ok": false, "error": "..."} explaining why, so the agent can retry.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import yaml

from common import config as C
from common.config import BBox
from common.variables import DATASETS, VARIABLES
from graph import sources
from graph.store import GraphStore, SchemaError

STRATEGY_PATH = Path(__file__).with_name("strategy.yaml")
CREATOR = "curator"


@lru_cache(maxsize=1)
def strategy() -> dict:
    return yaml.safe_load(STRATEGY_PATH.read_text(encoding="utf-8"))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def dataset_node_id(short_name: str, version: str) -> str:
    return f"dataset:{short_name}_v{version}"


def ok(**kw) -> dict:
    return {"ok": True, **kw}


def fail(msg: str) -> dict:
    return {"ok": False, "error": msg}


def _land_cells(bbox: BBox) -> int | None:
    try:
        from engine.analysis import TrendEngine
        return TrendEngine().n_land_cells(bbox)
    except FileNotFoundError:
        return None


class CuratorTools:
    def __init__(self, store: GraphStore):
        self.store = store

    # ================================================================== read-only
    def get_schema(self) -> dict:
        """Allowed node labels, relationship types and the build target."""
        from graph.store import load_schema
        sch = load_schema()
        return ok(nodes={k: v["required"] for k, v in sch["nodes"].items()},
                  relationships={k: f"{v['from']} -> {v['to']}" for k, v in
                                 sch["relationships"].items()},
                  target=self.target())

    @staticmethod
    def target() -> dict:
        """What the finished Layer A must contain (Document 2, section 8.1)."""
        st = strategy()
        return dict(
            datasets=[f"{d.short_name} v{d.version}" for d in DATASETS.values()],
            variables={k: f"{v.name_in_file} in {DATASETS[v.dataset].short_name}"
                       for k, v in VARIABLES.items()},
            concepts=["surface heating", "water availability", "drought", "vegetation health",
                      "evaporative demand", "water cycle"],
            regions=[C.REGION_NAME, "and sub-regions such as Iberia, Maghreb, Tunisia, Nile "
                     "Delta, Levant, Sahara margin, Italy and the Balkans, Anatolia"],
            methods=[m["id"] for m in st["methods"]],
            chart_styles=[c["id"] for c in st["chart_styles"]],
            hypothesis_patterns=[p["id"] for p in st["hypothesis_patterns"]],
            papers=[f"{d} (read_by: {p.get('read_by') or 'NOBODY YET'})"
                    for d, p in sources.papers_catalog().items()])

    def get_progress(self) -> dict:
        """What already exists and what is still missing compared with the target."""
        have = self.store.counts()
        missing = []
        for d in DATASETS.values():
            if not self.store.get(dataset_node_id(d.short_name, d.version)):
                missing.append(f"Dataset {d.short_name} v{d.version}")
        vnodes = {n["code_id"]: n for n in self.store.nodes("Variable")}
        for k, v in VARIABLES.items():
            if k not in vnodes:
                missing.append(f"Variable {v.name_in_file} ({k})")
                continue
            vid = vnodes[k]["id"]
            if not self.store.out(vid, "INDICATOR_OF"):
                missing.append(f"INDICATOR_OF link for {vid}")
            if not self.store.out(vid, "DRAWN_AS"):
                missing.append(f"chart style for {vid}")
        for c in self.target()["concepts"]:
            if not self.store.get(f"concept:{slug(c)}"):
                missing.append(f"Concept {c}")
        if not self.store.get(f"region:{C.REGION_ID}"):
            missing.append(f"Region {C.REGION_NAME}")
        if len(self.store.nodes("Region")) < 5:
            missing.append("sub-regions (at least 4)")
        for kind, items in (("Method", strategy()["methods"]),
                            ("ChartStyle", strategy()["chart_styles"]),
                            ("HypothesisPattern", strategy()["hypothesis_patterns"])):
            prefix = {"Method": "method:", "ChartStyle": "chart:",
                      "HypothesisPattern": "pattern:"}[kind]
            for it in items:
                if not self.store.get(prefix + it["id"]):
                    missing.append(f"{kind} {it['id']}")
        readable = [d for d, p in sources.papers_catalog().items() if p.get("read_by")]
        for d in readable:
            if not self.store.get(f"paper:{d}"):
                missing.append(f"Paper {d}")
        return ok(counts=have, missing=missing, done=not missing)

    def find_node(self, label: str, text: str) -> dict:
        """Search existing nodes (by id, name, synonyms...). Call before every add_ tool."""
        label = label or None
        hits = self.store.search(label, text, limit=15)
        return ok(matches=[{k: n.get(k) for k in ("id", "label", "name", "display_name",
                                                  "code_id", "synonyms", "status")
                            if n.get(k) is not None} for n in hits])

    # ================================================================== datasets
    def add_dataset(self, short_name: str, version: str) -> dict:
        """Look the dataset up in NASA CMR and copy the official metadata. Also creates the
        Mission / Instrument nodes listed by CMR and the PROVIDES / CARRIES links."""
        ref = next((d for d in DATASETS.values()
                    if d.short_name == short_name and d.version == version), None)
        if ref is None:
            return fail(f"{short_name} v{version} is not one of the datasets we downloaded "
                        f"({', '.join(f'{d.short_name} v{d.version}' for d in DATASETS.values())}).")
        try:
            col = sources.cmr_collection(short_name, version)
        except sources.SourceError as e:
            return fail(f"CMR lookup failed: {e}")
        nid = dataset_node_id(short_name, version)
        node = self.store.merge_node("Dataset", nid, dict(
            short_name=col["short_name"], version=col["version"], title=col["title"],
            cmr_concept_id=col["cmr_concept_id"], doi=col["doi"], provider=col["provider"],
            time_start=col["time_start"], time_end=col["time_end"],
            processing_level=col["processing_level"], local_key=ref.key,
            file_format=ref.file_format, native_resolution=ref.native_res),
            source=f"NASA CMR {col['cmr_concept_id']}", created_by=CREATOR)
        created = [nid]
        for p in col["platforms"]:
            if not p["name"]:
                continue
            mid = f"mission:{slug(p['name'])}"
            self.store.merge_node("Mission", mid, {"name": p["name"]},
                                  source=f"NASA CMR {col['cmr_concept_id']} Platforms",
                                  created_by=CREATOR)
            created.append(mid)
            if not p["instruments"]:
                self.store.merge_rel(mid, "PROVIDES", nid, source="NASA CMR", created_by=CREATOR)
            for ins in p["instruments"]:
                iid = f"instrument:{slug(ins)}"
                self.store.merge_node("Instrument", iid, {"name": ins},
                                      source=f"NASA CMR {col['cmr_concept_id']} Instruments",
                                      created_by=CREATOR)
                self.store.merge_rel(mid, "CARRIES", iid, source="NASA CMR", created_by=CREATOR)
                self.store.merge_rel(iid, "PROVIDES", nid, source="NASA CMR", created_by=CREATOR)
                created.append(iid)
        return ok(node=node, created_or_updated=created)

    # ================================================================== variables
    def add_variable(self, dataset_short_name: str, name_in_file: str,
                     definition_for_students: str, kind: str) -> dict:
        """Create a Variable with its recipe. Units, fill value and scale come from the real file
        header (or CMR UMM-Var if no file is downloaded yet); the target unit and conversion come
        from the team's reference table. The agent only writes the student definition and kind."""
        spec = next((v for v in VARIABLES.values()
                     if DATASETS[v.dataset].short_name == dataset_short_name
                     and v.name_in_file == name_in_file), None)
        if spec is None:
            return fail(f"'{name_in_file}' in {dataset_short_name} is not a variable of our "
                        "series.nc. Our variables: " + ", ".join(
                            f"{v.name_in_file} ({DATASETS[v.dataset].short_name})"
                            for v in VARIABLES.values()))
        ds = DATASETS[spec.dataset]
        did = dataset_node_id(ds.short_name, ds.version)
        if not self.store.get(did):
            return fail(f"Create the dataset first: add_dataset('{ds.short_name}', '{ds.version}').")
        if kind not in ("state", "flux", "index"):
            return fail("kind must be 'state', 'flux' or 'index'.")
        if len(definition_for_students.split()) < 6:
            return fail("Write a real one-sentence definition for a high-school student.")
        meta, source = None, None
        try:
            meta = sources.file_header(ds.key, name_in_file, spec.group)
            source = f"file header {meta['file']}" if meta else None
        except Exception:  # noqa: BLE001 - unreadable sample file -> fall back to CMR
            meta, source = None, None
        if meta is None:
            try:
                col = sources.cmr_collection(ds.short_name, ds.version)
                meta = sources.cmr_variable(col, name_in_file)
                source = f"NASA CMR UMM-Var {meta['concept_id']}" if meta else None
            except sources.SourceError as e:
                return fail(f"No file header and CMR failed: {e}")
        if meta is None:
            meta, source = {}, "team reference table (no file header, no CMR UMM-Var)"
        unit_native = meta.get("units") or spec.unit_native
        vid = f"var:{ds.short_name}/{name_in_file}"
        node = self.store.merge_node("Variable", vid, dict(
            code_id=spec.id, display_name=spec.display_name,
            definition_for_students=definition_for_students.strip(),
            name_in_file=name_in_file, group=spec.group, unit_native=unit_native,
            unit_target=spec.unit_target, conversion=spec.conversion,
            scale_factor=meta.get("scale_factor"), add_offset=meta.get("add_offset"),
            fill_value=meta.get("fill_value"), long_name=meta.get("long_name"),
            cf_standard_name=spec.cf_standard_name, kind=kind,
            recipe_source=source), source=source, created_by=CREATOR)
        self.store.merge_rel(vid, "IN_DATASET", did, source=source, created_by=CREATOR)
        self.store.merge_rel(did, "HAS_VARIABLE", vid, source=source, created_by=CREATOR)
        warn = None
        if kind != spec.kind:
            warn = f"Note: the team's reference table says kind='{spec.kind}'."
        return ok(node=node, recipe_source=source, warning=warn)

    # ================================================================== concepts
    def add_concept(self, name: str, synonyms: list[str]) -> dict:
        """Create a concept a student might ask about, with everyday synonyms."""
        name = name.strip().lower()
        if not name or len(name) > 40:
            return fail("Give a short concept name (a few words).")
        cid = f"concept:{slug(name)}"
        syns = sorted({s.strip().lower() for s in synonyms if s and s.strip()} - {name})
        if not syns:
            return fail("Give at least one synonym students might use.")
        for other in self.store.nodes("Concept"):
            if other["id"] == cid:
                continue
            taken = {str(s).lower() for s in other.get("synonyms", [])} | {other["name"]}
            if name in taken:
                return fail(f"'{name}' is already used by {other['id']}.")
            clash = sorted(set(syns) & taken)
            if clash:
                return fail(f"Synonyms {clash} already belong to {other['id']}: a synonym can "
                            "belong to one concept only. Remove them and retry.")
        node = self.store.merge_node("Concept", cid, {"name": name, "synonyms": syns},
                                     source="curator (concept vocabulary)", created_by=CREATOR,
                                     confidence=0.9)
        return ok(node=node)

    def link_variable_to_concept(self, variable_id: str, concept_name: str, reason: str) -> dict:
        """INDICATOR_OF: this variable measures / indicates this concept. A reason is required."""
        cid = f"concept:{slug(concept_name)}"
        if not self.store.get(variable_id):
            return fail(f"Variable '{variable_id}' does not exist. Use find_node first.")
        if not self.store.get(cid):
            return fail(f"Concept '{concept_name}' does not exist. Create it with add_concept.")
        if len(reason.split()) < 5:
            return fail("Explain the link in one sentence (reason).")
        self.store.merge_rel(variable_id, "INDICATOR_OF", cid, {"reason": reason.strip()},
                             source="curator", created_by=CREATOR, confidence=0.9)
        return ok(linked=f"{variable_id} -INDICATOR_OF-> {cid}")

    # ================================================================== regions
    def add_region(self, code_id: str, name: str, west: float, south: float, east: float,
                   north: float, parent_code_id: str = "") -> dict:
        """A box of 1-degree cells inside our data. The tool counts its land cells."""
        code_id = slug(code_id)
        bbox = BBox(float(west), float(south), float(east), float(north))
        if not bbox.is_valid():
            return fail("west must be < east and south must be < north.")
        if not C.REGION.contains(bbox):
            return fail(f"The box must be inside our data {C.REGION.as_tuple()}.")
        n = _land_cells(bbox)
        if n is None:
            return fail("series.nc is missing: run the data pipeline before adding regions.")
        if code_id != C.REGION_ID and n < C.MIN_CELLS:
            return fail(f"Only {n} land cells - a sub-region needs at least {C.MIN_CELLS}.")
        rid = f"region:{code_id}"
        node = self.store.merge_node("Region", rid, dict(
            code_id=code_id, name=name.strip(), bbox=list(bbox.as_tuple()), n_land_cells=n),
            source="curator box + land cells counted from series.nc", created_by=CREATOR)
        if parent_code_id:
            pid = f"region:{slug(parent_code_id)}"
            if not self.store.get(pid):
                return fail(f"Parent region '{pid}' does not exist (created {rid} without parent).")
            self.store.merge_rel(rid, "PART_OF", pid, source="curator", created_by=CREATOR)
        return ok(node=node)

    # ================================================================== papers
    def add_paper(self, doi: str) -> dict:
        """Add a paper from papers.yaml. Title/year/abstract come from Crossref (or the abstract
        pasted by the team). Refused if no team member has read it."""
        doi = doi.lower().strip().removeprefix("https://doi.org/")
        cat = sources.papers_catalog().get(doi)
        if cat is None:
            return fail("Only papers listed in graph/papers.yaml can be added.")
        if not (cat.get("read_by") or "").strip():
            return fail(f"No team member has read {doi} yet (read_by is empty in papers.yaml).")
        try:
            meta = sources.paper_metadata(doi)
        except sources.SourceError as e:
            return fail(f"Crossref lookup failed: {e}")
        if not meta["abstract"]:
            return fail(f"No abstract available for {doi}: paste it in papers.yaml.")
        node = self.store.merge_node("Paper", f"paper:{doi}", dict(
            doi=doi, title=meta["title"], year=meta["year"], journal=meta["journal"],
            abstract=meta["abstract"], abstract_source=meta["abstract_source"],
            read_by=cat["read_by"]), source=f"Crossref DOI {doi}", created_by=CREATOR,
            status="from_paper")
        return ok(node={k: node[k] for k in ("id", "title", "year")},
                  abstract=meta["abstract"])

    def add_influence(self, from_variable_id: str, to_variable_id: str, sign: str,
                      paper_doi: str, quote: str) -> dict:
        """INFLUENCES (literature): from_variable affects to_variable. The quote must appear
        word for word in the paper's abstract."""
        if sign not in ("+", "-"):
            return fail("sign must be '+' (more A -> more B) or '-' (more A -> less B).")
        pid = f"paper:{paper_doi.lower().strip()}"
        paper = self.store.get(pid)
        if paper is None:
            return fail(f"Paper {pid} is not in the graph. Use add_paper first.")
        for v in (from_variable_id, to_variable_id):
            if not self.store.get(v):
                return fail(f"Variable '{v}' does not exist.")
        if from_variable_id == to_variable_id:
            return fail("A variable cannot influence itself.")
        if not sources.quote_in_text(quote, paper.get("abstract", "")):
            return fail("The quote does not appear word for word in the paper's abstract "
                        "(minimum 20 characters). Copy an exact sentence from the abstract.")
        self.store.merge_rel(from_variable_id, "INFLUENCES", to_variable_id,
                             {"sign": sign, "paper_id": pid, "quote": quote.strip()},
                             source=f"DOI {paper['doi']}", created_by=CREATOR,
                             status="from_paper", confidence=0.8)
        self.store.merge_rel(from_variable_id, "SUPPORTED_BY", pid,
                             {"about": f"INFLUENCES {to_variable_id}"},
                             source=f"DOI {paper['doi']}", created_by=CREATOR,
                             status="from_paper")
        return ok(linked=f"{from_variable_id} -INFLUENCES({sign})-> {to_variable_id}")

    # ================================================================== strategy
    def add_method(self, method_id: str) -> dict:
        """Create a Method from strategy.yaml; NEXT links are added to its neighbours in order."""
        m = next((x for x in strategy()["methods"] if x["id"] == method_id), None)
        if m is None:
            return fail("Unknown method. Allowed: " + ", ".join(x["id"] for x in strategy()["methods"]))
        node = self.store.merge_node("Method", f"method:{m['id']}", dict(
            name=m["name"], order=m["order"], stage=m["stage"], description=m["description"],
            applies_to_kind=m["applies_to_kind"], parameters=m["parameters"]),
            source="graph/strategy.yaml (team)", created_by=CREATOR)
        methods = sorted(strategy()["methods"], key=lambda x: x["order"])
        for a, b in zip(methods, methods[1:]):
            if self.store.get(f"method:{a['id']}") and self.store.get(f"method:{b['id']}"):
                self.store.merge_rel(f"method:{a['id']}", "NEXT", f"method:{b['id']}",
                                     source="graph/strategy.yaml", created_by=CREATOR)
        return ok(node={"id": node["id"], "order": node["order"]})

    def add_chart_style(self, style_id: str) -> dict:
        """Create a ChartStyle from strategy.yaml."""
        s = next((x for x in strategy()["chart_styles"] if x["id"] == style_id), None)
        if s is None:
            return fail("Unknown chart style. Allowed: " +
                        ", ".join(x["id"] for x in strategy()["chart_styles"]))
        node = self.store.merge_node("ChartStyle", f"chart:{s['id']}", dict(
            chart_type=s["chart_type"], colormap=s["colormap"],
            label_template=s["label_template"]),
            source="graph/strategy.yaml (team)", created_by=CREATOR)
        return ok(node={"id": node["id"]})

    def assign_chart_style(self, variable_id: str, style_id: str) -> dict:
        """DRAWN_AS: how this variable's results are drawn."""
        cid = f"chart:{style_id}"
        if not self.store.get(variable_id):
            return fail(f"Variable '{variable_id}' does not exist.")
        if not self.store.get(cid):
            return fail(f"Chart style '{cid}' does not exist. Use add_chart_style first.")
        self.store.merge_rel(variable_id, "DRAWN_AS", cid, source="curator", created_by=CREATOR)
        return ok(linked=f"{variable_id} -DRAWN_AS-> {cid}")

    def add_hypothesis_pattern(self, pattern_id: str) -> dict:
        """Create a HypothesisPattern from strategy.yaml."""
        p = next((x for x in strategy()["hypothesis_patterns"] if x["id"] == pattern_id), None)
        if p is None:
            return fail("Unknown pattern. Allowed: " +
                        ", ".join(x["id"] for x in strategy()["hypothesis_patterns"]))
        node = self.store.merge_node("HypothesisPattern", f"pattern:{p['id']}", dict(
            name=p["name"], description=p["description"].strip(), cypher=p["cypher"].strip()),
            source="graph/strategy.yaml (team)", created_by=CREATOR)
        return ok(node={"id": node["id"]})

    # ================================================================== checks
    def validate_graph(self) -> dict:
        """Run all automatic checks (Document 2, section 8.7)."""
        from graph.validate_graph import validate
        problems = validate(self.store)
        return ok(problems=problems, passed=not problems)

    # ================================================================== registry
    def registry(self) -> dict[str, Callable[..., dict]]:
        return {name: getattr(self, name) for name in TOOL_SCHEMAS}

    def call(self, name: str, args: dict[str, Any]) -> dict:
        fn = self.registry().get(name)
        if fn is None:
            return fail(f"Unknown tool {name}.")
        try:
            return fn(**args)
        except SchemaError as e:
            return fail(f"Schema refused the write: {e}")
        except TypeError as e:
            return fail(f"Bad arguments for {name}: {e}")
        except sources.SourceError as e:
            return fail(f"Source error: {e}")


# JSON-schema descriptions for the LLM (kept next to the code they describe)
_S, _N, _A = {"type": "string"}, {"type": "number"}, {"type": "array", "items": {"type": "string"}}
TOOL_SCHEMAS: dict[str, dict] = {
    "get_schema": {"description": CuratorTools.get_schema.__doc__, "properties": {}},
    "get_progress": {"description": CuratorTools.get_progress.__doc__, "properties": {}},
    "find_node": {"description": CuratorTools.find_node.__doc__,
                  "properties": {"label": {**_S, "description": "node label or empty string"},
                                 "text": _S}, "required": ["label", "text"]},
    "add_dataset": {"description": CuratorTools.add_dataset.__doc__,
                    "properties": {"short_name": _S, "version": _S},
                    "required": ["short_name", "version"]},
    "add_variable": {"description": CuratorTools.add_variable.__doc__,
                     "properties": {"dataset_short_name": _S, "name_in_file": _S,
                                    "definition_for_students": _S,
                                    "kind": {**_S, "enum": ["state", "flux", "index"]}},
                     "required": ["dataset_short_name", "name_in_file",
                                  "definition_for_students", "kind"]},
    "add_concept": {"description": CuratorTools.add_concept.__doc__,
                    "properties": {"name": _S, "synonyms": _A}, "required": ["name", "synonyms"]},
    "link_variable_to_concept": {"description": CuratorTools.link_variable_to_concept.__doc__,
                                 "properties": {"variable_id": _S, "concept_name": _S,
                                                "reason": _S},
                                 "required": ["variable_id", "concept_name", "reason"]},
    "add_region": {"description": CuratorTools.add_region.__doc__,
                   "properties": {"code_id": _S, "name": _S, "west": _N, "south": _N,
                                  "east": _N, "north": _N, "parent_code_id": _S},
                   "required": ["code_id", "name", "west", "south", "east", "north"]},
    "add_paper": {"description": CuratorTools.add_paper.__doc__,
                  "properties": {"doi": _S}, "required": ["doi"]},
    "add_influence": {"description": CuratorTools.add_influence.__doc__,
                      "properties": {"from_variable_id": _S, "to_variable_id": _S,
                                     "sign": {**_S, "enum": ["+", "-"]}, "paper_doi": _S,
                                     "quote": _S},
                      "required": ["from_variable_id", "to_variable_id", "sign", "paper_doi",
                                   "quote"]},
    "add_method": {"description": CuratorTools.add_method.__doc__,
                   "properties": {"method_id": _S}, "required": ["method_id"]},
    "add_chart_style": {"description": CuratorTools.add_chart_style.__doc__,
                        "properties": {"style_id": _S}, "required": ["style_id"]},
    "assign_chart_style": {"description": CuratorTools.assign_chart_style.__doc__,
                           "properties": {"variable_id": _S, "style_id": _S},
                           "required": ["variable_id", "style_id"]},
    "add_hypothesis_pattern": {"description": CuratorTools.add_hypothesis_pattern.__doc__,
                               "properties": {"pattern_id": _S}, "required": ["pattern_id"]},
    "validate_graph": {"description": CuratorTools.validate_graph.__doc__, "properties": {}},
}
