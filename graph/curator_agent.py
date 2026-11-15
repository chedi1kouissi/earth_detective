"""Phase 2 - the curator agent builds Layer A of the graph (Document 2, section 8.6).

It is an LLM (Gemini) that can ONLY use the checking tools in curator_tools.py.
Every tool call and answer is written to data/graph/curator_build_log.jsonl (the build log).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from agent import llm
from common import config as C
from graph.curator_tools import TOOL_SCHEMAS, CuratorTools
from graph.store import GraphStore

log = logging.getLogger(__name__)

SYSTEM = """You are the CURATOR of the EarthSleuth knowledge graph (a Neo4j graph about NASA
Earth-science data for the Mediterranean and North Africa, used by students).

Your job: build Layer A of the graph so that it contains everything an investigation needs.
You decide WHAT to add; the tools decide whether it is TRUE and refuse anything wrong.

Rules:
1. You can only change the graph through the tools. There is no free Cypher.
2. Never type a number from memory (units, dates, scale factors, ids). The tools fetch them
   from NASA CMR, the real data files or Crossref.
3. Call find_node before adding something, to avoid duplicates.
4. When a tool refuses, read the error, fix the call and try again (max 2 retries), or skip.
5. Definitions are for a curious 15-year-old: one clear sentence, no jargon.
6. Each synonym may belong to ONE concept only. Synonyms are everyday words students type
   ("hotter", "drier", "plants"...).
7. Link every variable to the concepts it indicates (INDICATOR_OF) with a one-sentence reason,
   and give every variable a chart style.
8. Literature: only add papers that the tools accept (a team member must have read them), and
   only add INFLUENCES links whose quote you copy WORD FOR WORD from the abstract the tool
   returns. If no sentence of the abstract clearly supports a link, do not add it.
9. Work in this order: get_schema -> datasets -> variables -> concepts + links -> regions
   (the main region first, then sub-regions with parent_code_id) -> methods -> chart styles
   (+ assign) -> hypothesis patterns -> papers + influences -> get_progress -> validate_graph.
10. When get_progress says nothing is missing and validate_graph passes, write a short summary
    of what you built and stop calling tools.
"""

KICKOFF = """Build the graph now. Start with get_schema to see the schema and the target.
Our main region code_id is '{region_id}' ({region_name}), box {bbox}.
Suggested sub-regions (boxes as west, south, east, north - you may adjust them, the tool checks
them): {subregions}.
Call several tools per turn when they are independent."""


def build_graph(store: GraphStore, max_turns: int = 80, echo=print) -> dict:
    from common.variables import SUBREGIONS
    tools = CuratorTools(store)
    C.BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stats = {"calls": 0, "refused": 0}

    with C.BUILD_LOG.open("a", encoding="utf-8") as logf:
        logf.write(json.dumps({"type": "start", "time": started, "store": store.backend}) + "\n")

        def call(name: str, args: dict) -> dict:
            res = tools.call(name, args)
            stats["calls"] += 1
            if not res.get("ok"):
                stats["refused"] += 1
            return res

        def on_event(e: dict):
            e = {**e, "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            logf.write(json.dumps(e, default=str, ensure_ascii=False) + "\n")
            logf.flush()
            if e["type"] == "tool":
                status = "ok " if e["result"].get("ok") else "REFUSED"
                short = json.dumps(e["args"], ensure_ascii=False)[:110]
                echo(f"  [{status}] {e['name']}({short})" +
                     ("" if e["result"].get("ok") else f"  <- {e['result'].get('error', '')[:150]}"))
            elif e["type"] == "text":
                echo(f"  curator: {e['text'][:300]}")

        kickoff = KICKOFF.format(region_id=C.REGION_ID, region_name=C.REGION_NAME,
                                 bbox=C.REGION.as_tuple(),
                                 subregions={k: v for k, v in SUBREGIONS.items()})
        final = llm.run_tools(SYSTEM, kickoff, TOOL_SCHEMAS, call, max_turns=max_turns,
                              on_event=on_event)
        logf.write(json.dumps({"type": "end", "final": final, **stats}) + "\n")

    progress = tools.get_progress()
    validation = tools.validate_graph()
    return {"final_message": final, **stats, "missing": progress["missing"],
            "problems": validation["problems"], "counts": store.counts()}
