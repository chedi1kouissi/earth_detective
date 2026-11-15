"""Trend map: where each variable changes, how much, and where it is significant."""
import common_ui as ui
import streamlit as st

from common import config as C

ui.page_header("Trend map", "Slope per decade in every 1° land cell. Grey = not significant "
               "after the FDR correction. Click a cell to see its time series.")
if not ui.data_ready() or not ui.graph_ready():
    st.stop()

from engine.analysis import GuardrailError  # noqa: E402

c1, c2, c3 = st.columns([1.2, 1.2, 1])
with c1:
    v = ui.variable_picker("tm_var")
with c2:
    region = ui.region_picker("tm_region")
with c3:
    period = ui.period_picker("tm_period")
mode = st.radio("Colour by", ["slope", "direction"], horizontal=True,
                format_func={"slope": "Slope per decade",
                             "direction": "Opposite-trend view (red ↑ / blue ↓)"}.get)

try:
    df, res = ui.engine().run(v["code_id"], ui.area_for(region), period)
except GuardrailError as e:
    st.error(str(e))
    st.stop()

for w in res.warnings:
    st.warning(w)
reg = res.regional
m1, m2, m3, m4 = st.columns(4)
m1.metric("Regional trend", f"{reg.slope_per_decade:+.3g}" if reg.slope_per_decade is not None
          else "n/a", help=res.unit)
m2.metric("p-value (regional)", ui.fmt_p(reg.p), "significant" if reg.significant else
          "not significant", delta_color="off")
m3.metric("Area ↑ significant", f"{res.cells.pct_sig_up_area}%")
m4.metric("Area ↓ significant", f"{res.cells.pct_sig_down_area}%")
st.caption(f"Unit: {res.unit} · {res.cells.n_tested} cells tested · method: {res.method}")

if res.cells.pct_sig_up_area >= 10 and res.cells.pct_sig_down_area >= 10:
    st.info("**Opposite trends:** large areas go up while others go down. The regional average "
            f"({reg.slope_per_decade:+.3g} {res.unit}) hides two different stories.")

event = st.plotly_chart(ui.trend_map(df, res.unit, mode), width="stretch",
                        on_select="rerun", selection_mode="points", key="tm_map")
cell = ui.selected_cell(event)
if cell is None:
    cell = st.selectbox("...or pick a cell", df["cell_id"], index=None,
                        placeholder="Click the map or choose a cell")
if cell:
    row = df[df["cell_id"] == cell].iloc[0]
    ts = ui.engine().cell_timeseries(v["code_id"], row["lat"], row["lon"], period)
    st.plotly_chart(ui.series_chart(ts, f"{v['display_name']} at {cell}", v["unit"]),
                    width="stretch")
    st.caption(f"slope {row['slope_dec']:+.3g} {res.unit} (95% CI {row['ci_lo']:+.3g} to "
               f"{row['ci_hi']:+.3g}) · p = {ui.fmt_p(row['p'])} · q = {ui.fmt_p(row['q'])} · "
               f"{'significant' if row['significant'] else 'not significant'}")

with st.expander("Data table / download"):
    st.dataframe(df, hide_index=True, width="stretch")
    st.download_button("Download CSV", df.to_csv(index=False), f"trends_{v['code_id']}_{region}.csv")
