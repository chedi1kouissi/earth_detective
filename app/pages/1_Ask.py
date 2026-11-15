"""Ask: the investigator at work, step by step."""
import json

import common_ui as ui
import pandas as pd
import streamlit as st

from common import config as C

ui.page_header("Ask", "The investigator follows the knowledge graph step by step.")
if not ui.data_ready() or not ui.graph_ready():
    st.stop()

from agent.investigator import STEPS, Investigator, list_investigations, load_investigation  # noqa: E402


@st.cache_resource
def investigator():
    return Investigator(store=ui.store(), engine=ui.engine())


with st.form("ask"):
    q = st.text_input("Your question", value=st.session_state.pop("pending_question", ""),
                      placeholder="Is Tunisia getting drier since 2005?")
    c1, c2 = st.columns(2)
    regs = ui.regions()
    opts = ["auto"] + [r["code_id"] for r in regs]
    names = {"auto": "Detect from my question"} | {r["code_id"]: r["name"] for r in regs}
    region = c1.selectbox("Area (optional)", opts, format_func=names.get)
    use_period = c2.checkbox("Choose the period myself")
    period = ui.period_picker("ask_period") if use_period else None
    go = st.form_submit_button("Investigate", type="primary")

if go and q.strip():
    labels = {s: st.empty() for s in STEPS}
    for s in STEPS:
        labels[s].markdown(f"⚪ **{s}**")

    def on_step(step, status, payload):
        if step in labels:
            labels[step].markdown(f"{'🟡' if status == 'running' else '🟢'} **{step}**")

    with st.spinner("Investigating..."):
        report = investigator().run(q, None if region == "auto" else region, period, on_step)
    st.session_state["investigation"] = report

with st.expander("Open a previous investigation"):
    files = list_investigations()[:30]
    if files:
        pick = st.selectbox("Saved investigations", files,
                            format_func=lambda p: json.loads(p.read_text(encoding="utf-8"))["question"]
                            + f"  ({p.stem})")
        if st.button("Open"):
            st.session_state["investigation"] = load_investigation(pick)
    else:
        st.caption("None yet.")

rep = st.session_state.get("investigation")
if not rep:
    st.stop()

st.divider()
st.subheader(f"❓ {rep['question']}")
if rep.get("status") != "done":
    st.markdown(rep["answer"])
    st.stop()

u, plan = rep["steps"]["Understand"], rep["steps"]["Plan"]
tab_ans, tab_plan, tab_res, tab_why, tab_check = st.tabs(
    ["Answer", "1-2 · Understand + Plan", "3-4 · Results + evidence", "5 · Why?", "6 · Check"])

with tab_ans:
    st.markdown(rep["answer"])

with tab_plan:
    st.markdown(f"**Concepts found:** {', '.join(c['name'] + ' (' + ', '.join(c['matched']) + ')' for c in u['concepts'])}  \n"
                f"**Area:** {u['region_name']} · **Period:** {plan['period'][0]} → {plan['period'][1]}"
                f"  \n**How:** {u['method']}")
    st.markdown("**Variables chosen by walking the graph** (Concept ← INDICATOR_OF ← Variable → "
                "IN_DATASET → Dataset):")
    st.dataframe(pd.DataFrame([{
        "variable": v["display_name"], "definition": v["definition"],
        "why": "; ".join(f"{b['concept'].split(':')[1].replace('_', ' ')}: {b['reason']}" for b in v["because"]),
        "dataset": f"{v['dataset']['short_name']} v{v['dataset']['version']}",
        "recipe": f"{v['recipe']['name_in_file']} [{v['recipe']['unit_native']}] → {v['unit']} "
                  f"({v['recipe']['conversion']})",
        "chart": v["chart_style"]["id"]} for v in plan["variable_details"]]),
        hide_index=True, width="stretch")
    st.markdown("**Methods, in the order of the graph's NEXT chain:** " +
                " → ".join(m["name"] for m in rep.get("methods", [])))
    for w in plan["warnings"]:
        st.warning(w)
    with st.expander("Contract 1 (investigation spec, JSON)"):
        st.json({k: plan[k] for k in ("question", "concepts", "variables", "region", "period",
                                      "methods", "outputs")})

with tab_res:
    res = rep["steps"]["Analyse"]["results"]
    cols = st.columns(max(1, len(res)))
    for col, (v, r) in zip(cols, res.items()):
        reg = r["regional"]
        col.metric(r["display_name"], f"{reg['slope_per_decade']:+.3g}" if reg["slope_per_decade"] is not None else "n/a",
                   help=f"{r['unit']}; p = {ui.fmt_p(reg['p'])}")
        col.caption(f"{r['unit']} · p {ui.fmt_p(reg['p'])} · "
                    f"{'**significant**' if reg['significant'] else 'not significant'}  \n"
                    f"area ↑ {r['cells']['pct_sig_up_area']}% · ↓ {r['cells']['pct_sig_down_area']}%")
    st.info("Open **Trend map** and **Time series** in the sidebar to explore each variable "
            "(they use the same engine and the same period).")
    opp = rep["steps"]["Analyse"]["opposite_pairs"]
    if opp:
        st.markdown("**Opposite trends between sub-regions** (the regional average hides these):")
        st.dataframe(pd.DataFrame(opp)[["variable", "region_up", "slope_up", "region_down",
                                        "slope_down"]], hide_index=True)
    if rep.get("clusters"):
        st.markdown("**Trend-signature clusters** (clusters suggest, statistics decide):")
        st.dataframe(pd.DataFrame(rep["clusters"])[["cluster_label", "n_cells", "signature"]],
                     hide_index=True)
    st.markdown(f"**Written to the graph (Layer B):** {len(rep['findings'])} findings, "
                f"analysis `{rep['steps']['Record']['analysis']}`")
    with st.expander("Contract 2 results (JSON)"):
        st.json(res)

with tab_why:
    why = rep["steps"]["Why?"]
    st.markdown("**Literature paths in the graph** (Variable -INFLUENCES-> Variable, with the quote):")
    if why["literature"]:
        for m in why["literature"]:
            st.markdown(f"- {m['source_variable']} → {m['target_variable']} ({m['sign']}): "
                        f"*\"{m['quote']}\"* — {m['paper_title']} ({m['paper_year']})")
    else:
        st.caption("No literature link for these variables yet (a team member must read a paper "
                   "and list it in graph/papers.yaml, then rebuild the graph).")
    st.markdown("**Hypotheses** (from the graph's HypothesisPattern rules, saved as *unverified*):")
    for h in why["hypotheses"]:
        st.markdown(f"- 🟣 {h['text']}  \n  <small>pattern `{h['pattern']}` · based on "
                    f"{', '.join(h['based_on'])}</small>", unsafe_allow_html=True)
    if not why["hypotheses"]:
        st.caption("No hypothesis pattern matched.")

with tab_check:
    chk = rep["steps"]["Check"]
    st.markdown(f"**Mode:** {chk['mode']} · **Number check passed:** {chk['passed']}")
    st.json(chk)
    with st.expander("Evidence pack given to the explainer"):
        st.json(rep.get("evidence_pack", {}))

# ------------------------------------------------------------------ follow-up chat with tools
st.divider()
st.subheader("Follow-up question")
st.caption("The AI can call read-only tools (graph + statistics engine) to answer.")
fq = st.text_input("Ask a follow-up", key="followup")
if st.button("Ask") and fq.strip():
    from agent import llm
    from agent.tools import CHAT_TOOL_SCHEMAS, InvestigatorTools
    tools = InvestigatorTools(ui.store(), ui.engine())
    calls = []

    def call(name, args):
        try:
            out = getattr(tools, name)(**args)
            return {"ok": True, "result": out}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    system = ("You answer follow-up questions about an EarthSleuth investigation for a high-school "
              "student. Use the tools for every number; never compute or guess one. Region codes: "
              + ", ".join(r["code_id"] for r in ui.regions()) + ". Variable codes: "
              + ", ".join(v["code_id"] for v in ui.variables())
              + f". Data period {C.PERIOD_START}..{C.PERIOD_END}. Label claims [observed], "
              "[literature] or [hypothesis].")
    ctx = json.dumps(rep.get("evidence_pack", {}))[:6000]
    with st.spinner("Thinking with tools..."):
        try:
            ans = llm.run_tools(system, f"Context of the investigation: {ctx}\n\nFollow-up: {fq}",
                                CHAT_TOOL_SCHEMAS, call, max_turns=8,
                                on_event=lambda e: calls.append(e) if e["type"] == "tool" else None)
            st.markdown(ans)
            if calls:
                with st.expander(f"{len(calls)} tool call(s)"):
                    for c in calls:
                        st.code(f"{c['name']}({json.dumps(c['args'])})")
        except llm.LLMUnavailable as e:
            st.error(f"Gemini is unavailable: {e}")
