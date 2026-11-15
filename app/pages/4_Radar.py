"""Radar-lite: what is changing the most, opposite trends, trend-signature clusters."""
import common_ui as ui
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ui.page_header("Radar", "The app does not wait for questions: it shows what changes the most.")
if not ui.data_ready() or not ui.graph_ready():
    st.stop()

from engine import radar  # noqa: E402
from engine.analysis import GuardrailError  # noqa: E402
from graph import queries as Q  # noqa: E402

c1, c2 = st.columns(2)
with c1:
    region = ui.region_picker("rd_region")
with c2:
    period = ui.period_picker("rd_period")
area = ui.area_for(region)

results, cells = [], {}
with st.spinner("Running the statistics engine on every variable..."):
    for v in ui.variables():
        try:
            df, r = ui.engine().run(v["code_id"], area, period)
            results.append(r)
            cells[v["code_id"]] = df
        except GuardrailError as e:
            st.warning(f"{v['display_name']}: {e}")
if not results:
    st.stop()

st.subheader("1 · Ranking: share of the land area with a significant trend")
rank = radar.ranking(results)
fig = go.Figure()
fig.add_trace(go.Bar(y=rank["display_name"], x=rank["pct_up"], orientation="h", name="increase",
                     marker_color=ui.RED))
fig.add_trace(go.Bar(y=rank["display_name"], x=rank["pct_down"], orientation="h", name="decrease",
                     marker_color=ui.BLUE))
fig.update_layout(barmode="stack", height=300, xaxis_title="% of land area (cos-latitude weighted)",
                  margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, width="stretch")

st.subheader("2 · Opposite trends")
pats = [p for p in (radar.opposite_pattern(r) for r in results) if p]
for p in pats:
    st.info(f"**{p['variable']}**: {p['pct_up']}% of the area increases while {p['pct_down']}% "
            "decreases - the regional average hides two stories.")
per_var = {}
for sub in Q.sub_regions(ui.store(), region):
    for r in results:
        try:
            _, rs = ui.engine().run(r.variable, ui.area_for(sub["code_id"]), period)
            per_var.setdefault(r.variable, {})[sub["code_id"]] = rs
        except GuardrailError:
            pass
pairs = [p for d in per_var.values() for p in radar.subregion_opposites(d)]
if pairs:
    st.dataframe(pd.DataFrame(pairs)[["variable", "region_up", "slope_up", "region_down",
                                      "slope_down"]], hide_index=True, width="stretch")
elif not pats:
    st.caption("No opposite pattern found for this area and period.")

st.subheader("3 · Trend-signature clusters")
table, summary = radar.clusters(cells)
if table.empty:
    st.caption(f"Clusters need at least {radar.MIN_CELLS_FOR_CLUSTERS} land cells and 2 variables.")
else:
    st.plotly_chart(ui.cluster_map(table), width="stretch")
    st.dataframe(pd.DataFrame(summary)[["cluster", "label", "n_cells", "signature", "k",
                                        "silhouette"]], hide_index=True, width="stretch")
    st.error("Golden rule: clusters only say *these places changed in a similar way*. Whether "
             "each trend is real is decided by the significance test, not by the clustering.",
             icon="⚖️")
