"""The tools of the investigator (Document 2, section 9.1).

Each tool reads the graph or runs the engine and returns plain JSON-able data.
The investigator controller calls them in the order the graph gives; the follow-up chat lets
the LLM call the read-only ones itself.
"""
from __future__ import annotations

import hashlib
from typing import Any

from common import config as C
from common.contracts import InvestigationSpec, VariableResult
from engine.analysis import Area, GuardrailError, TrendEngine
from graph import queries as Q
from graph.store import GraphStore, parse_json_prop


def fmt(x: float | None, sig: int = 3) -> str:
    """The ONE way numbers are written for the LLM and the report (so the number check works)."""
    if x is None:
        return "n/a"
    if x == 0:
        return "0"
    s = f"{x:.{sig}g}"
    return s if "e" not in s else f"{x:.{sig}e}"


def fmt_p(p: float | None) -> str:
    if p is None:
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.2g}"


def group_opposites(pairs: list[dict]) -> dict[str, dict]:
    """Opposite pairs grouped per variable: which sub-regions go up, which go down."""
    out: dict[str, dict] = {}
    for p in pairs:
        g = out.setdefault(p["variable"], {"up": {}, "down": {}, "findings": []})
        g["up"][p["region_up"]] = p["slope_up"]
        g["down"][p["region_down"]] = p["slope_down"]
        for f in (p["finding_up"], p["finding_down"]):
            if f not in g["findings"]:
                g["findings"].append(f)
    return out


def direction_word(slope: float | None) -> str:
    return "no clear change" if not slope else ("increase" if slope > 0 else "decrease")


class InvestigatorTools:
    def __init__(self, store: GraphStore, engine: TrendEngine | None = None):
        self.store = store
        self.engine = engine or TrendEngine()

    # ------------------------------------------------------------------ graph reads
    def find_concepts(self, question_words: str) -> list[dict]:
        """Concepts in the graph matching the words or synonyms (empty = out of scope)."""
        return Q.find_concepts(self.store, question_words)

    def find_variables(self, concepts: list[str]) -> list[dict]:
        """Variables linked to the concepts, with definitions and datasets."""
        ids = [c if c.startswith("concept:") else f"concept:{c.replace(' ', '_')}" for c in concepts]
        return Q.variables_for_concepts(self.store, ids)

    def area(self, region_code: str) -> Area:
        r = next((x for x in Q.regions(self.store) if x["code_id"] == region_code), None)
        if r is None:
            raise GuardrailError(f"Region '{region_code}' is not in the graph.")
        return Area(r["code_id"], r["name"], r["bbox"])

    def plan_from_graph(self, question: str, concepts: list[str], region_code: str,
                        period: list[str]) -> InvestigationSpec:
        """Contract 1, entirely read from the graph: variables + definitions, datasets, recipes,
        ordered methods, chart styles."""
        variables = self.find_variables(concepts)
        methods = Q.method_chain(self.store)
        area = self.area(region_code)
        warnings, usable = [], []
        for v in variables:
            try:
                warnings += self.engine.check(v["code_id"], area, period)
                usable.append(v)
            except GuardrailError as e:
                warnings.append(f"{v['display_name']}: {self._with_suggestion(e, region_code)}")
        spec = InvestigationSpec(
            question=question, concepts=concepts, variables=[v["code_id"] for v in usable],
            region=area.id, period=list(period), methods=[m["id"] for m in methods],
            variable_details=usable, warnings=sorted(set(warnings)))
        return spec

    # ------------------------------------------------------------------ engine
    def get_trend(self, variable: str, region: str, period: list[str]) -> dict:
        """Contract-2 JSON for the regional trend + cell counts (cache or computed on demand)."""
        try:
            _, r = self.engine.run(variable, self.area(region), period)
        except GuardrailError as e:
            raise GuardrailError(self._with_suggestion(e, region)) from e
        return r.to_dict()

    def _with_suggestion(self, err: GuardrailError, region_code: str) -> str:
        """Too few land cells -> name the nearest larger region of the graph (section 6.3)."""
        msg = str(err)
        if "land cells" in msg:
            big = Q.larger_region(self.store, region_code, C.MIN_CELLS)
            if big:
                msg = msg.replace(" Try a larger region.", "") + \
                    f" Try '{big['name']}' ({big['n_land_cells']} land cells) instead."
        return msg

    def get_opposite_trends(self, variable: str, region: str, period: list[str]) -> list[dict]:
        """Sub-regions with opposite significant directions."""
        from engine import radar
        per = {}
        for sub in Q.sub_regions(self.store, region):
            try:
                _, r = self.engine.run(variable, Area(sub["code_id"], sub["name"], sub["bbox"]),
                                       period)
                per[sub["code_id"]] = r
            except GuardrailError:
                continue
        return radar.subregion_opposites(per)

    def get_clusters(self, region: str, period: list[str]) -> list[dict]:
        """Cluster signatures, sizes (from the graph's Finding nodes of kind 'cluster')."""
        return [dict(id=f["id"], label=f.get("cluster_label"), signature=f.get("signature"),
                     n_cells=f.get("n_cells"))
                for f in Q.findings_in(self.store, region, period) if f.get("kind") == "cluster"]

    def get_mechanisms(self, variable: str) -> list[dict]:
        """INFLUENCES paths from the graph, with their paper sources."""
        vid = next((v["id"] for v in self.store.nodes("Variable") if v.get("code_id") == variable),
                   None)
        return Q.mechanisms(self.store, vid) if vid else []

    def get_chart(self, variable: str, kind: str = "map") -> dict:
        """Chart spec (type, colours, labels) from ChartStyle."""
        v = next((x for x in Q.all_variables(self.store) if x["code_id"] == variable), None)
        if v is None:
            return {}
        cs = dict(v["chart_style"])
        cs["axis_label"] = (cs.get("label_template") or "{unit}").format(
            unit=v["unit"], display_name=v["display_name"])
        return cs

    # ------------------------------------------------------------------ hypotheses
    def propose_hypotheses(self, pkg: dict) -> list[dict]:
        """Candidate hypotheses from the HypothesisPattern rules (co-trends + literature paths,
        opposite sub-regions, compound clusters). Always 'unverified'."""
        patterns = {p["id"]: p for p in Q.hypothesis_patterns(self.store)}
        names = {v["code_id"]: v["display_name"] for v in Q.all_variables(self.store)}
        regions = {r["code_id"]: r["name"] for r in Q.regions(self.store)}
        trend = [f for f in pkg["findings"] if f["kind"] == "trend"]
        out: list[dict] = []

        if "pattern:co_trend_literature" in patterns:
            by_var = {}
            for f in trend:
                by_var.setdefault((f["variable"], f["region"]), f)
            for f in trend:
                for m in self.get_mechanisms(f["variable"]):
                    if m["source_variable"] != self._var_id(f["variable"]):
                        continue
                    tgt = self._code(m["target_variable"])
                    g = by_var.get((tgt, f["region"]))
                    if not g:
                        continue
                    same = f["direction"] == g["direction"]
                    if (m["sign"] == "+") != same:
                        continue
                    out.append(dict(
                        pattern="pattern:co_trend_literature", based_on=[f["id"], g["id"]],
                        about=[f["variable"], tgt], paper=m.get("doi"),
                        text=(f"The {direction_word(1 if f['direction'] == 'up' else -1)} in "
                              f"{names.get(f['variable'], f['variable']).lower()} may be contributing "
                              f"to the {direction_word(1 if g['direction'] == 'up' else -1)} in "
                              f"{names.get(tgt, tgt).lower()} in {regions.get(f['region'], f['region'])}, "
                              f"as described in the literature ({m.get('paper_title')}, "
                              f"{m.get('paper_year')}). Not tested here.")))

        if "pattern:opposite_regions" in patterns:
            for var, g in group_opposites(pkg.get("opposite_pairs", [])).items():
                ups = ", ".join(regions.get(r, r) for r in g["up"])
                downs = ", ".join(regions.get(r, r) for r in g["down"])
                out.append(dict(
                    pattern="pattern:opposite_regions", based_on=g["findings"], about=[var],
                    text=(f"{names.get(var, var)} increases in {ups} but decreases in {downs}: "
                          "different processes may dominate in each place, and a single regional "
                          "average hides this.")))

        if "pattern:compound_cluster" in patterns:
            groups: dict[str, list[dict]] = {}
            for f in pkg["findings"]:
                lab = f.get("cluster_label", "")
                if f["kind"] == "cluster" and "warming" in lab and "drying" in lab:
                    groups.setdefault(lab, []).append(f)
            for lab, fs in groups.items():
                about = sorted({v for f in fs for v in (f.get("directions") or {})})
                out.append(dict(
                    pattern="pattern:compound_cluster", based_on=[f["id"] for f in fs],
                    about=about,
                    text=(f"The places in the '{lab}' group(s) could be compound "
                          "heat-and-drought hot spots worth watching; the clustering only shows "
                          "that these places changed in a similar way.")))
        return out

    def record_hypothesis(self, text: str, based_on: list[str], pattern: str,
                          about: list[str] | None = None, investigation_id: str | None = None
                          ) -> dict:
        """Saves a hypothesis node labelled 'unverified'."""
        hid = "hypothesis:" + hashlib.sha1((text + "|".join(based_on)).encode()).hexdigest()[:12]
        self.store.merge_node("Hypothesis", hid, {"text": text, "pattern": pattern,
                                                  "verification": "unverified"},
                              source="investigator (pattern rule)", created_by="investigator",
                              status="hypothesis", confidence=0.3)
        for fid in based_on:
            if self.store.get(fid):
                self.store.merge_rel(fid, "SUGGESTS", hid, source="investigator",
                                     created_by="investigator", status="hypothesis")
        if self.store.get(pattern):
            self.store.merge_rel(hid, "VIA_PATTERN", pattern, source="investigator",
                                 created_by="investigator", status="hypothesis")
        for code in about or []:
            vid = self._var_id(code)
            if vid:
                self.store.merge_rel(hid, "ABOUT", vid, source="investigator",
                                     created_by="investigator", status="hypothesis")
        if investigation_id and self.store.get(investigation_id):
            self.store.merge_rel(investigation_id, "PROPOSED", hid, source="investigator",
                                 created_by="investigator", status="hypothesis")
        return {"id": hid, "text": text, "status": "unverified"}

    # ------------------------------------------------------------------ helpers
    def _var_id(self, code: str) -> str | None:
        return next((v["id"] for v in self.store.nodes("Variable") if v.get("code_id") == code),
                    None)

    def _code(self, var_id: str) -> str | None:
        v = self.store.get(var_id)
        return v.get("code_id") if v else None


# JSON schemas of the read-only tools offered to the follow-up chat
_S = {"type": "string"}
_P = {"type": "array", "items": {"type": "string"}, "description": "[start YYYY-MM, end YYYY-MM]"}
CHAT_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "find_concepts": {"description": InvestigatorTools.find_concepts.__doc__,
                      "properties": {"question_words": _S}, "required": ["question_words"]},
    "find_variables": {"description": InvestigatorTools.find_variables.__doc__,
                       "properties": {"concepts": {"type": "array", "items": _S}},
                       "required": ["concepts"]},
    "get_trend": {"description": InvestigatorTools.get_trend.__doc__,
                  "properties": {"variable": _S, "region": _S, "period": _P},
                  "required": ["variable", "region", "period"]},
    "get_opposite_trends": {"description": InvestigatorTools.get_opposite_trends.__doc__,
                            "properties": {"variable": _S, "region": _S, "period": _P},
                            "required": ["variable", "region", "period"]},
    "get_mechanisms": {"description": InvestigatorTools.get_mechanisms.__doc__,
                       "properties": {"variable": _S}, "required": ["variable"]},
}
