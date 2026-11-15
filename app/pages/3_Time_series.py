"""Time series: monthly values, anomalies, Theil-Sen line and its uncertainty."""
import common_ui as ui
import streamlit as st

ui.page_header("Time series", "The regional average of a variable, month by month. Anomalies = "
               "values minus the normal for that month, so the seasons disappear.")
if not ui.data_ready() or not ui.graph_ready():
    st.stop()

from engine.analysis import GuardrailError  # noqa: E402

c1, c2, c3 = st.columns([1.2, 1.2, 1])
with c1:
    v = ui.variable_picker("ts_var")
with c2:
    region = ui.region_picker("ts_region")
with c3:
    period = ui.period_picker("ts_period")

try:
    _, res = ui.engine().run(v["code_id"], ui.area_for(region), period)
except GuardrailError as e:
    st.error(str(e))
    st.stop()
area = ui.area_for(region)
ts = ui.engine().regional_timeseries(v["code_id"], area, period)
st.plotly_chart(ui.series_chart(ts, f"{v['display_name']} - {area.name} (cos-latitude weighted)",
                                v["unit"]), width="stretch")
reg = res.regional
st.markdown(
    f"**Trend:** {reg.slope_per_decade:+.3g} {res.unit} (95% CI {reg.ci95[0]:+.3g} to "
    f"{reg.ci95[1]:+.3g}) · **p** = {ui.fmt_p(reg.p)} · "
    f"**{'significant' if reg.significant else 'not significant'}**"
    + (f" · about **{reg.years_needed:.0f} years** of data would be needed to detect a trend this "
       "size (Weatherhead et al. 1998)" if (not reg.significant and reg.years_needed) else ""))
st.caption("The red band shows the 95% range of possible slopes. It does not account for "
           "autocorrelation, so it can be a bit too narrow - we say so honestly.")
with st.expander("Monthly values (before removing the seasons)"):
    st.plotly_chart(ui.raw_chart(ts, v["unit"]), width="stretch")
for w in res.warnings:
    st.warning(w)
