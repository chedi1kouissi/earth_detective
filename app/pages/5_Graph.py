"""Graph: the knowledge + evidence graph, the curator's build log, and live checks."""
import json

import common_ui as ui
import pandas as pd
import streamlit as st
from html import escape

from common import config as C

ui.page_header("Knowledge graph", "Layer A (knowledge, built by the AI curator) + Layer B "
               "(evidence, written by code). Dashed = hypothesis.")

from graph.store import parse_json_prop  # noqa: E402
from graph.validate_graph import validate  # noqa: E402

COLORS = {"Mission": "#5B8DEF", "Instrument": "#7FA7F5", "Dataset": "#1F5FA8", "Variable": "#138A7E",
          "Concept": "#E58A2B", "Region": "#8C6D46", "Method": "#6A4FA0", "ChartStyle": "#A08BC9",
          "Paper": "#C8423B", "HypothesisPattern": "#9C5BB5", "Analysis": "#7A7F87",
          "Finding": "#2E3440", "Hypothesis": "#B04FC2", "Investigation": "#D4A72C"}

s = ui.store()
nodes, rels = s.nodes(), s.rels()
counts = s.counts()
st.markdown(" · ".join(f"**{k}** {v}" for k, v in counts.items()))

tab_net, tab_tables, tab_log, tab_check, tab_cypher = st.tabs(
    ["Network", "Tables", "Curator build log", "Checks", "Cypher"])

with tab_net:
    labels = sorted({n["label"] for n in nodes})
    default = [l for l in labels if l not in ("Analysis", "Investigation", "Method", "ChartStyle",
                                              "HypothesisPattern")]
    show = st.multiselect("Show node types", labels, default=default)
    max_findings = st.slider("Max findings shown", 0, 200, 40)
    from pyvis.network import Network
    net = Network(height="640px", width="100%", directed=True, bgcolor="#ffffff",
                  cdn_resources="in_line")
    net.barnes_hut(gravity=-6000, spring_length=140)
    keep, nf = set(), 0
    for n in nodes:
        if n["label"] not in show:
            continue
        if n["label"] == "Finding":
            nf += 1
            if nf > max_findings:
                continue
        keep.add(n["id"])
        title = "\n".join(f"{k}: {escape(str(parse_json_prop(v))[:160])}" for k, v in n.items()
                          if k not in ("abstract",))
        name = n.get("display_name") or n.get("name") or n.get("short_name") or n.get(
            "cluster_label") or n["id"].split(":", 1)[-1]
        net.add_node(n["id"], label=escape(str(name)[:40]), title=title,
                     color=COLORS.get(n["label"], "#999"), shape="dot",
                     size=18 if n["label"] in ("Variable", "Concept", "Dataset") else 11,
                     borderDashes=n.get("status") == "hypothesis")
    for r in rels:
        if r["src"] in keep and r["dst"] in keep:
            net.add_edge(r["src"], r["dst"], label=r["type"], title=r["type"],
                         dashes=r.get("status") == "hypothesis", arrows="to",
                         font={"size": 8}, color="#9AA3AF")
    # graph text (some written by the curator LLM) is HTML-escaped above before embedding
    st.iframe(net.generate_html(), height=660)
    st.caption(" · ".join(f"<span style='color:{c}'>●</span> {l}" for l, c in COLORS.items()),
               unsafe_allow_html=True)

with tab_tables:
    lab = st.selectbox("Node type", sorted({n["label"] for n in nodes}))
    df = pd.DataFrame([{k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                        for k, v in n.items() if k != "abstract"} for n in nodes if n["label"] == lab])
    st.dataframe(df, hide_index=True, width="stretch")

with tab_log:
    if C.BUILD_LOG.exists():
        lines = [json.loads(l) for l in C.BUILD_LOG.read_text(encoding="utf-8").splitlines() if l]
        runs = [i for i, e in enumerate(lines) if e.get("type") == "start"]
        last = lines[runs[-1]:] if runs else lines
        tools = [e for e in last if e.get("type") == "tool"]
        refused = sum(not e["result"].get("ok") for e in tools)
        st.markdown(f"Last curator run: **{len(tools)} tool calls**, **{refused} refused** by the "
                    "checking tools (and retried or skipped).")
        st.dataframe(pd.DataFrame([{
            "time": e["time"], "tool": e["name"], "args": json.dumps(e["args"])[:150],
            "ok": e["result"].get("ok"), "error": e["result"].get("error", "")} for e in tools]),
            hide_index=True, width="stretch")
    else:
        st.caption("No build log yet: the graph was not built by the curator agent "
                   "(`python run.py build_graph`).")

with tab_check:
    if st.button("Run validate_graph"):
        probs = validate(s)
        if probs:
            st.error(f"{len(probs)} problem(s)")
            st.write(probs)
        else:
            st.success("The graph passed all automatic checks.")

with tab_cypher:
    if s.backend != "neo4j":
        st.caption("Cypher needs the live Neo4j graph.")
    else:
        examples = {
            "Concept -> variables -> datasets (the plan)":
                "MATCH (c:Concept)<-[r:INDICATOR_OF]-(v:Variable)-[:IN_DATASET]->(d:Dataset)\n"
                "RETURN c.name AS concept, v.display_name AS variable, d.short_name AS dataset, "
                "r.reason AS reason ORDER BY concept",
            "Method chain": "MATCH p=(m:Method)-[:NEXT*]->(x:Method) WHERE NOT ()-[:NEXT]->(m)\n"
                            "RETURN [n IN nodes(p) | n.name] AS chain ORDER BY length(p) DESC LIMIT 1",
            "Opposite findings": "MATCH (a:Finding)-[:OPPOSITE_OF]->(b:Finding)\n"
                                 "RETURN a.summary AS up, b.summary AS down LIMIT 25",
            "Hypotheses and their evidence":
                "MATCH (f:Finding)-[:SUGGESTS]->(h:Hypothesis)\nRETURN h.text AS hypothesis, "
                "collect(f.summary) AS based_on LIMIT 25",
        }
        pick = st.selectbox("Example query", list(examples))
        q = st.text_area("Read-only Cypher", examples[pick], height=110)
        if st.button("Run query"):
            if any(w in q.upper() for w in ("CREATE", "MERGE", "DELETE", "SET ", "REMOVE", "DROP")):
                st.error("Read-only queries only on this page.")
            else:
                st.dataframe(pd.DataFrame(s.cypher(q)), width="stretch")
