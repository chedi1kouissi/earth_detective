"""The AI investigator (Document 2, section 9): one question -> one complete, honest investigation.

Steps (the UI shows them lighting up):
  1 Understand  question -> concepts, region, period        (Gemini, constrained to graph items)
  2 Plan        concepts -> variables/datasets/recipes/methods/charts   (graph walk = Contract 1)
  3 Analyse     statistics + Radar-lite on series.nc          (plain code = Contract 2)
  4 Record      Analysis / Finding / OPPOSITE_OF / CO_OCCURS_WITH       (plain code -> graph)
  5 Why?        literature paths + HypothesisPattern rules -> Hypothesis (unverified)
  6 Check       every number in the answer must come from the tools    (plain code)
  7 Explain     answer for a curious high-school student, every claim labelled (Gemini)
Without Gemini (no key / API down) steps 1 and 7 fall back to rules and templates.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agent import llm
from agent.tools import InvestigatorTools, direction_word, fmt, fmt_p, group_opposites
from common import config as C
from engine.analysis import Area, GuardrailError, TrendEngine
from engine.findings import analyse_area
from graph import queries as Q
from graph.evidence import write_evidence
from graph.store import GraphStore, get_store

log = logging.getLogger(__name__)
STEPS = ["Understand", "Plan", "Analyse", "Record", "Why?", "Check", "Explain"]
# The explanation uses the fast model by default (answers in seconds); set EXPLAIN_MODEL=pro in
# .env to use the reasoning model instead (better prose, much slower).
EXPLAIN_FAST = os.getenv("EXPLAIN_MODEL", "fast").strip().lower() != "pro"

EXPLAIN_SYSTEM = """You are EarthSleuth, an Earth-science investigator explaining results to a
curious high-school student. You receive an EVIDENCE PACK (JSON) produced by real statistics on
NASA data and by a knowledge graph. Write the answer in Markdown with these sections:

## Short answer
## What the data shows  (label each claim [observed])
## Places moving in opposite directions  (only if the pack has opposite trends; [observed])
## What scientists have written  (only items from "literature"; label [literature] and cite title + year)
## Possible explanations  (only items from "hypotheses"; label [hypothesis]; say they are not proven)
## Limits of this investigation

STRICT RULES
- Use ONLY numbers that appear in the evidence pack, written exactly as they appear there.
  Never compute, round, convert or estimate a number. If you need a number that is not there,
  describe it in words instead. Write numbers as plain text (no code formatting / backticks).
- For every trend give: the slope with its unit, the period, the p-value, and whether it is
  significant.
- Correlation is not causation. Never claim a cause as proven.
- Labels go only on claims about this data / literature / hypotheses, never on definitions.
- Short sentences. Define every technical word the first time (trend, significant, anomaly...).
- If "synthetic" is true, start with a bold warning that the data is synthetic test data.
"""

UNDERSTAND_SYSTEM = """You map a student's question about climate and environment onto the
EarthSleuth knowledge graph. Only choose concepts and regions from the lists you are given.
If the question asks about something our data cannot measure (e.g. sea level, air pollution,
a place outside the region), explain it in out_of_scope_reason."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ============================================================================ number check
# A sign only counts when it is not glued to a word or a number before it, so "2001-01" and
# "2001-2024" are dates / ranges (no negative numbers) while "-0.585" and "+0.4" are signed.
_NUM = re.compile(r"(?<![\w.])([-+−]?)(\d+(?:[.,]\d+)*(?:e[-+]?\d+)?)")


def numbers_in(text: str) -> set[str]:
    """Signed numbers in a text: '-0.585', '+0.4' or '0.4' (no sign written)."""
    out = set()
    for sign, digits in _NUM.findall(text):
        sign = {"−": "-", "-": "-", "+": "+"}.get(sign, "")
        out.add(sign + digits.replace(",", ""))
    return out


def number_check(answer: str, evidence_text: str, extra_ok: set[str] | None = None) -> list[str]:
    """Numbers in the answer that do not appear in the evidence (string match, as in the PDF).

    Signs are checked: '-0.585' must appear as a negative number in the evidence and '+0.585' as
    a positive one, so a decrease cannot be reported as an increase. A number written without a
    sign ("decreased by 0.585") only needs its absolute value to appear in the evidence."""
    ev = numbers_in(evidence_text) | (extra_ok or set())
    negative = {n[1:] for n in ev if n.startswith("-")}
    positive = {n.lstrip("+") for n in ev if not n.startswith("-")}
    positive |= {str(i) for i in range(0, 13)}          # counts, months, list numbering
    bad = []
    for n in numbers_in(answer):
        value = n.lstrip("+-")
        if n.startswith("-"):
            ok = value in negative
        elif n.startswith("+"):
            ok = value in positive
        else:
            ok = value in positive or value in negative
        if not ok:
            bad.append(n)
    return sorted(bad)


# ============================================================================ investigator
class Investigator:
    def __init__(self, store: GraphStore | None = None, engine: TrendEngine | None = None,
                 use_llm: bool = True):
        self.store = store or get_store()
        self.engine = engine or TrendEngine()
        self.tools = InvestigatorTools(self.store, self.engine)
        self.use_llm = use_llm and bool(C.GEMINI_API_KEY)

    # ------------------------------------------------------------------ public
    def run(self, question: str, region_code: str | None = None,
            period: list[str] | None = None,
            on_step: Callable[[str, str, dict], None] | None = None) -> dict:
        user_emit = on_step or (lambda *a: None)
        inv_id = "investigation:" + hashlib.sha1(f"{question}|{_now()}".encode()).hexdigest()[:12]
        report: dict = {"id": inv_id, "question": question, "created": _now(),
                        "synthetic": self.engine.synthetic, "steps": {}, "llm_used": self.use_llm,
                        "store": self.store.backend, "timings_s": {}}
        started: dict[str, float] = {}

        def emit(step: str, status: str, payload: dict):
            if status == "running":
                started[step] = time.perf_counter()
            elif step in started:
                report["timings_s"][step] = round(time.perf_counter() - started[step], 2)
            user_emit(step, status, payload)

        # 1 ---------------------------------------------------------- Understand
        emit("Understand", "running", {})
        u = self.understand(question, region_code, period)
        report["steps"]["Understand"] = u
        emit("Understand", "done", u)
        if not u["concepts"]:
            msg = self.out_of_scope_message(u)
            report.update(status="out_of_scope", answer=msg)
            emit("Explain", "done", {"answer": msg})
            return self._save(report)

        # 2 ---------------------------------------------------------- Plan
        emit("Plan", "running", {})
        spec = self.tools.plan_from_graph(question, [c["id"] for c in u["concepts"]],
                                          u["region"], u["period"])
        report["steps"]["Plan"] = spec.to_dict()
        report["methods"] = Q.method_chain(self.store)
        emit("Plan", "done", spec.to_dict())
        if not spec.variables:
            msg = ("I found the concepts in your question, but none of our variables can be analysed "
                   "for this region and period:\n\n" + "\n".join(f"- {w}" for w in spec.warnings))
            report.update(status="refused", answer=msg)
            emit("Explain", "done", {"answer": msg})
            return self._save(report)

        # 3 ---------------------------------------------------------- Analyse
        emit("Analyse", "running", {})
        area = self.tools.area(spec.region)
        subs = [Area(s["code_id"], s["name"], s["bbox"]) for s in Q.sub_regions(self.store, area.id)]
        pkg = analyse_area(self.engine, area, spec.variables, spec.period, subs)
        pkg.pop("_cells")
        clusters_df = pkg.pop("_clusters")
        report["steps"]["Analyse"] = {k: pkg[k] for k in ("results", "errors", "opposite_patterns",
                                                          "opposite_pairs", "co_occurs")}
        report["clusters"] = [f for f in pkg["findings"] if f["kind"] == "cluster"]
        report["cluster_cells"] = (clusters_df[["cell_id", "lat", "lon", "cluster",
                                                "cluster_label"]].to_dict("records")
                                   if not clusters_df.empty else [])
        report["sub_results"] = pkg["sub_results"]
        emit("Analyse", "done", report["steps"]["Analyse"])

        # 4 ---------------------------------------------------------- Record
        emit("Record", "running", {})
        rec = write_evidence(self.store, pkg)
        self._record_investigation(inv_id, question, spec, pkg)
        report["steps"]["Record"] = {**rec, "findings": [f["id"] for f in pkg["findings"]]}
        report["findings"] = pkg["findings"]
        emit("Record", "done", report["steps"]["Record"])

        # 5 ---------------------------------------------------------- Why?
        emit("Why?", "running", {})
        literature = []
        for v in spec.variables:
            literature += self.tools.get_mechanisms(v)
        literature = list({(m["source_variable"], m["target_variable"], m["paper_id"]): m
                           for m in literature}.values())
        hyps = []
        for h in self.tools.propose_hypotheses(pkg):
            rec_h = self.tools.record_hypothesis(h["text"], h["based_on"], h["pattern"],
                                                 h.get("about"), inv_id)
            hyps.append({**h, **rec_h})
        report["steps"]["Why?"] = {"literature": literature, "hypotheses": hyps}
        emit("Why?", "done", report["steps"]["Why?"])

        # 6 + 7 ----------------------------------------------------- Check + Explain
        evidence = self.evidence_pack(question, spec, pkg, literature, hyps)
        report["evidence_pack"] = evidence
        emit("Check", "running", {})
        answer, check = self.explain(evidence)
        report["steps"]["Check"] = check
        emit("Check", "done", check)
        emit("Explain", "running", {})
        report.update(status="done", answer=answer)
        emit("Explain", "done", {"answer": answer})
        return self._save(report)

    # ------------------------------------------------------------------ 1 understand
    def understand(self, question: str, region_code: str | None, period: list[str] | None) -> dict:
        concepts = {c["id"]: c for c in Q.find_concepts(self.store, question)}
        rule_region = Q.find_region(self.store, question)
        region = rule_region
        method = "rules (graph synonyms)"
        out_of_scope = ""
        p = self._period_from_text(question)
        if self.use_llm:
            try:
                all_c = Q.concepts(self.store)
                regs = Q.regions(self.store)
                schema = {"type": "object", "properties": {
                    "concepts": {"type": "array", "items": {"type": "string",
                                                            "enum": [c["name"] for c in all_c]}},
                    "region_code": {"type": "string",
                                    "enum": [r["code_id"] for r in regs] + ["none"]},
                    "start_year": {"type": "integer"}, "end_year": {"type": "integer"},
                    "out_of_scope_reason": {"type": "string"},
                    "interpretation": {"type": "string"}},
                    "required": ["concepts", "region_code", "out_of_scope_reason",
                                 "interpretation"]}
                prompt = (f"Question: {question}\n\nConcepts available: "
                          + json.dumps({c['name']: c.get('synonyms') for c in all_c})
                          + "\nRegions available: "
                          + json.dumps({r['code_id']: r['name'] for r in regs})
                          + f"\nOur data covers {C.PERIOD_START[:4]}-{C.PERIOD_END[:4]}. Give "
                          "start_year/end_year only if the question names years. region_code "
                          "'none' if no region is named.")
                ans = llm.generate_json(prompt, schema, UNDERSTAND_SYSTEM, fast=True)
                for name in ans.get("concepts", []):
                    c = next((x for x in all_c if x["name"] == name), None)
                    if c:
                        concepts.setdefault(c["id"], {"id": c["id"], "name": c["name"],
                                                      "matched": ["(Gemini)"]})
                # A region whose name is written in the question (found in the graph) always
                # wins; Gemini's region is only used when the question names no known region.
                if rule_region is None and ans.get("region_code") not in (None, "", "none"):
                    region = next((r for r in regs if r["code_id"] == ans["region_code"]), region)
                if ans.get("start_year") or ans.get("end_year"):
                    p = [f"{ans.get('start_year') or C.PERIOD_START[:4]}-01" if ans.get("start_year")
                         else C.PERIOD_START,
                         f"{ans['end_year']}-12" if ans.get("end_year") else C.PERIOD_END]
                out_of_scope = ans.get("out_of_scope_reason", "")
                method = "Gemini (constrained to graph concepts) + graph synonyms"
            except llm.LLMUnavailable as e:
                log.warning("understand without LLM: %s", e)
        if region_code:
            region = next((r for r in Q.regions(self.store) if r["code_id"] == region_code), region)
        region_code = region["code_id"] if region else C.REGION_ID
        if period:
            p = list(period)
        # No silent clamping: a period outside our data is refused by the engine's guardrail
        # ("Our data covers 2001-01 to 2024-12."), as Document 2 section 6.3 requires.
        return {"concepts": list(concepts.values()), "region": region_code,
                "region_name": next((r["name"] for r in Q.regions(self.store)
                                     if r["code_id"] == region_code), region_code),
                "period": p, "method": method, "out_of_scope_reason": out_of_scope}

    @staticmethod
    def _period_from_text(q: str) -> list[str]:
        years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", q)]
        start, end = C.PERIOD_START, C.PERIOD_END
        if years:
            if re.search(r"\b(since|from|after)\b", q.lower()) or len(years) == 1:
                start = f"{years[0]}-01"
            if len(years) >= 2:
                start, end = f"{min(years)}-01", f"{max(years)}-12"
        return [start, end]

    def out_of_scope_message(self, u: dict) -> str:
        names = ", ".join(c["name"] for c in Q.concepts(self.store))
        vars_ = ", ".join(v["display_name"] for v in Q.all_variables(self.store))
        reason = f"\n\n{u['out_of_scope_reason']}" if u.get("out_of_scope_reason") else ""
        return (f"**Our data can't answer this question.**{reason}\n\nEarthSleuth knows about: "
                f"{names}. It can measure: {vars_}, over the Mediterranean and North Africa, "
                f"{C.PERIOD_START[:4]}-{C.PERIOD_END[:4]}.\n\nTry for example: *Is it getting hotter "
                "and drier around the Mediterranean?* or *Are plants in Tunisia getting greener?*")

    # ------------------------------------------------------------------ 4 record
    def _record_investigation(self, inv_id: str, question: str, spec, pkg: dict):
        s = self.store
        s.merge_node("Investigation", inv_id, {"question": question, "region": spec.region,
                                               "period": spec.period,
                                               "variables": spec.variables},
                     source="user question", created_by="investigator")
        for c in spec.concepts:
            if s.get(c):
                s.merge_rel(inv_id, "ASKED_ABOUT", c, source="investigator",
                            created_by="investigator")
        if s.get(f"region:{spec.region}"):
            s.merge_rel(inv_id, "IN_REGION", f"region:{spec.region}", source="investigator",
                        created_by="investigator")
        for f in pkg["findings"]:
            if s.get(f["id"]):
                s.merge_rel(inv_id, "PRODUCED", f["id"], source="investigator",
                            created_by="investigator")
        for m in spec.methods:
            if s.get(m):
                s.merge_rel(inv_id, "USED_METHOD", m, source="investigator",
                            created_by="investigator")

    # ------------------------------------------------------------------ evidence for the LLM
    def evidence_pack(self, question, spec, pkg, literature, hyps) -> dict:
        regions = {r["code_id"]: r["name"] for r in Q.regions(self.store)}
        trends = []
        for v, r in pkg["results"].items():
            reg = r["regional"]
            trends.append(dict(
                variable=r["display_name"],
                definition=next((d["definition"] for d in spec.variable_details
                                 if d["code_id"] == v), ""),
                dataset=", ".join(r["datasets"]),
                slope_per_decade=fmt(reg["slope_per_decade"]), unit=r["unit"],
                ci95=[fmt(x) for x in reg["ci95"]], p_value=fmt_p(reg["p"]),
                significant=reg["significant"], direction=direction_word(reg["slope_per_decade"]),
                percent_area_significant_increase=fmt(r["cells"]["pct_sig_up_area"]),
                percent_area_significant_decrease=fmt(r["cells"]["pct_sig_down_area"]),
                cells_tested=r["cells"]["n_tested"],
                years_needed_if_not_significant=fmt(reg.get("years_needed"))))
        units = {v: r["unit"] for v, r in pkg["results"].items()}
        opposite = [dict(variable=next((r["display_name"] for k, r in pkg["results"].items()
                                        if k == var), var), unit=units.get(var, ""),
                         increases_in={regions.get(k, k): fmt(s) for k, s in g["up"].items()},
                         decreases_in={regions.get(k, k): fmt(s) for k, s in g["down"].items()})
                    for var, g in group_opposites(pkg["opposite_pairs"]).items()]
        patterns = [dict(variable=p["variable"], percent_area_up=fmt(p["pct_up"]),
                         percent_area_down=fmt(p["pct_down"])) for p in pkg["opposite_patterns"]]
        return dict(
            question=question, region=regions.get(spec.region, spec.region),
            period=f"{spec.period[0]} to {spec.period[1]}", synthetic=self.engine.synthetic,
            method=("seasons removed (monthly anomalies); Theil-Sen slope per decade with 95% "
                    "confidence interval; Mann-Kendall test with Hamed-Rao correction; false "
                    "discovery rate correction (q = 0.10) across grid cells; regional average "
                    "weighted by cos(latitude); significance of the regional trend at p <= 0.05"),
            trends=trends, opposite_trends_between_subregions=opposite,
            opposite_patterns_inside_region=patterns,
            clusters=[dict(label=f["cluster_label"], cells=f["n_cells"], signature=f["signature"])
                      for f in pkg["findings"] if f["kind"] == "cluster"],
            literature=[dict(statement=f"{m['source_variable'].split('/')[-1]} influences "
                             f"{m['target_variable'].split('/')[-1]} (sign {m['sign']})",
                             quote=m["quote"], title=m["paper_title"], year=m["paper_year"])
                        for m in literature],
            hypotheses=[h["text"] for h in hyps],
            warnings=sorted(set(spec.warnings + [w for r in pkg["results"].values()
                                                 for w in r["warnings"]])),
            errors=pkg["errors"])

    # ------------------------------------------------------------------ 6 + 7 explain + check
    def explain(self, evidence: dict) -> tuple[str, dict]:
        ev_text = json.dumps(evidence, ensure_ascii=False)
        extra = numbers_in(evidence["period"]) | numbers_in(evidence["question"])
        check = {"attempts": [], "passed": False, "mode": "template"}
        if self.use_llm:
            feedback = ""
            for attempt in range(3):
                t0 = time.perf_counter()
                try:
                    text = llm.generate_text(
                        "EVIDENCE PACK:\n" + json.dumps(evidence, indent=1, ensure_ascii=False)
                        + feedback, EXPLAIN_SYSTEM, fast=EXPLAIN_FAST)
                except llm.LLMUnavailable as e:
                    check["attempts"].append({"error": str(e)})
                    break
                bad = number_check(text, ev_text, extra)
                check["attempts"].append({"attempt": attempt + 1, "unknown_numbers": bad,
                                          "seconds": round(time.perf_counter() - t0, 1)})
                if not bad:
                    check.update(passed=True, mode="gemini")
                    return text, check
                feedback = ("\n\nYOUR PREVIOUS ANSWER USED NUMBERS THAT ARE NOT IN THE EVIDENCE "
                            f"PACK: {bad}. Rewrite it using only numbers from the pack.")
        text = template_answer(evidence)
        bad = number_check(text, ev_text, extra)
        check.update(passed=not bad, mode="template", unknown_numbers=bad)
        return text, check

    # ------------------------------------------------------------------ save
    def _save(self, report: dict) -> dict:
        path = C.INVESTIGATIONS / (report["id"].split(":")[1] + ".json")
        path.write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False),
                        encoding="utf-8")
        report["saved_to"] = str(path)
        return report


def template_answer(ev: dict) -> str:
    """Deterministic answer used when Gemini is unavailable (or keeps inventing numbers)."""
    L = []
    if ev["synthetic"]:
        L.append("**Warning: these results come from SYNTHETIC test data, not real NASA data.**\n")
    sig = [t for t in ev["trends"] if t["significant"]]
    L.append("## Short answer")
    if sig:
        L.append("Over " + ev["region"] + " (" + ev["period"] + "), the data shows a significant "
                 + "; ".join(f"{t['direction']} in {t['variable'].lower()}" for t in sig) + ".")
    else:
        L.append(f"No variable shows a significant regional trend over {ev['region']} "
                 f"({ev['period']}).")
    L.append("\n## What the data shows")
    for t in ev["trends"]:
        L.append(f"- [observed] **{t['variable']}** ({t['dataset']}): {t['slope_per_decade']} "
                 f"{t['unit']} (95% interval {t['ci95'][0]} to {t['ci95'][1]}), "
                 f"p {t['p_value'] if t['p_value'].startswith('<') else '= ' + t['p_value']}"
                 f" - {'significant' if t['significant'] else 'not significant'}. Significant "
                 f"increase over {t['percent_area_significant_increase']}% of the area, decrease "
                 f"over {t['percent_area_significant_decrease']}%.")
    if ev["opposite_trends_between_subregions"]:
        L.append("\n## Places moving in opposite directions")
        for o in ev["opposite_trends_between_subregions"]:
            ups = ", ".join(f"{k} ({v})" for k, v in o["increases_in"].items())
            downs = ", ".join(f"{k} ({v})" for k, v in o["decreases_in"].items())
            L.append(f"- [observed] {o['variable']} ({o['unit']}): up in {ups}; down in {downs}.")
    if ev["literature"]:
        L.append("\n## What scientists have written")
        for m in ev["literature"]:
            L.append(f"- [literature] \"{m['quote']}\" ({m['title']}, {m['year']})")
    if ev["hypotheses"]:
        L.append("\n## Possible explanations (not proven)")
        for h in ev["hypotheses"]:
            L.append(f"- [hypothesis] {h}")
    L.append("\n## Limits of this investigation")
    L.append("- A trend is the long-term direction after removing the seasons; 'significant' "
             "means it is unlikely to be random luck. It does not tell us the cause.")
    for w in ev["warnings"]:
        L.append(f"- {w}")
    return "\n".join(L)


def load_investigation(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_investigations() -> list[Path]:
    return sorted(C.INVESTIGATIONS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
