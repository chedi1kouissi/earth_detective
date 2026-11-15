"""EarthSleuth - Home page. Start with: python run.py app"""
import json

import common_ui as ui
import streamlit as st

from common import config as C

ui.page_header("EarthSleuth 🛰️", "Turn questions about our changing planet into honest, "
               "data-backed investigations with NASA data.")

st.markdown("""
**EarthSleuth** helps students and curious citizens become *Earth-science data detectives*.
Ask a question in plain words; an AI investigator **follows a knowledge graph** to choose the right
NASA variables, runs **real statistics** on 24 years of monthly data over the Mediterranean and
North Africa, and explains what it found - separating what is **observed**, what the
**literature** says, and what is only a **hypothesis**.
""")

c1, c2, c3 = st.columns(3)
c1.markdown("#### 🔎 Discover\nRadar-lite ranks what changes the most, finds places that move in "
            "**opposite directions**, and groups similar places.")
c2.markdown("#### 🧠 Connect\nA Neo4j knowledge graph **built by an AI curator** (every fact checked "
            "by tools) stores datasets, recipes, concepts, methods and evidence.")
c3.markdown("#### 🧪 Investigate\nThe investigator walks the graph: plan → statistics → evidence → "
            "hypotheses → number check → explanation.")

st.divider()
if not ui.data_ready() or not ui.graph_ready():
    st.stop()

st.subheader("Ask a question")
q = st.text_input("Your question", placeholder="Is it getting hotter and drier around the "
                  "Mediterranean?", key="home_q")
cols = st.columns(3)
if cols[0].button("Investigate", type="primary", disabled=not q):
    st.session_state["pending_question"] = q
    st.switch_page("pages/1_Ask.py")
demos = ["Is it getting hotter and drier around the Mediterranean?",
         "Are plants in Tunisia getting greener or browner?"]
for i, d in enumerate(demos):
    if cols[i + 1].button(f"Demo: {d}", key=f"demo{i}"):
        st.session_state["pending_question"] = d
        st.switch_page("pages/1_Ask.py")

st.divider()
st.subheader("Two words you need")
a, b = st.columns(2)
a.info("**Trend**: the long-term direction of a series after removing the seasons "
       "(summer is always hotter than winter - that is not a trend).")
b.info("**Significant**: unlikely to be random luck. We test hundreds of places at once, so we use "
       "a correction (FDR) - otherwise some places would look significant by pure chance.")

if C.FINDINGS_JSON.exists():
    pkg = json.loads(C.FINDINGS_JSON.read_text())
    st.subheader("What is changing the most (whole region)")
    rows = sorted(pkg["results"].values(), key=lambda r: -r["cells"]["pct_sig_area"])
    for r in rows:
        st.markdown(f"- **{r['display_name']}**: {r['cells']['pct_sig_down_area']}% of the land area "
                    f"with a significant decrease, {r['cells']['pct_sig_up_area']}% with a "
                    f"significant increase.")
