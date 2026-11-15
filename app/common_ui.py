"""Shared helpers for the Streamlit pages: cached graph/engine, maps, charts, banners."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from common import config as C  # noqa: E402

RED, BLUE, GREY = "#C8423B", "#1F5FA8", "#B9BEC7"


# ----------------------------------------------------------------------------- resources
@st.cache_resource(show_spinner="Connecting to the knowledge graph...")
def store():
    from graph.store import get_store
    return get_store()


@st.cache_resource(show_spinner="Opening series.nc...")
def engine():
    from engine.analysis import TrendEngine
    return TrendEngine()


def data_ready() -> bool:
    if not C.SERIES_NC.exists():
        st.error("No data yet. Run `python run.py synthetic` (test data) or `python run.py download`"
                 " then `python run.py preprocess` (real NASA data).")
        return False
    return True


def graph_ready() -> bool:
    missing = [lab for lab in ("Variable", "Concept", "Region", "Method") if not store().nodes(lab)]
    if missing:
        st.error(f"The knowledge graph is not complete (no {', '.join(missing)} nodes). Run "
                 "`python run.py build_graph` (curator agent) or `python run.py load_seed` (backup).")
        return False
    return True


def page_header(title: str, subtitle: str = ""):
    st.set_page_config(page_title=f"EarthSleuth · {title}", page_icon="🛰️", layout="wide")
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    if C.SERIES_NC.exists() and engine().synthetic:
        st.warning("**SYNTHETIC test data** - the numbers on this page are not real NASA results.",
                   icon="⚠️")
    sidebar_status()


def sidebar_status():
    with st.sidebar:
        s = store()
        st.markdown(f"**Graph:** {'Neo4j (live)' if s.backend == 'neo4j' else 'graph.json snapshot'}")
        st.markdown(f"**Gemini:** {'ready' if C.GEMINI_API_KEY else 'no key - template answers'}")
        st.markdown(f"**Region:** {C.REGION_NAME}  \n**Period:** {C.PERIOD_START} → {C.PERIOD_END}")
        st.divider()
        st.caption("AI use: an AI curator agent built the knowledge graph (checked by tools and by "
                   "the team); an AI investigator writes the explanations (numbers are checked "
                   "against the statistics). AI also helped write the code. Data: NASA MERRA-2, "
                   "GPM IMERG, GLDAS, MODIS. No NASA logos are used.")


# ----------------------------------------------------------------------------- regions / variables
def regions() -> list[dict]:
    from graph import queries as Q
    return Q.regions(store())


def variables() -> list[dict]:
    from graph import queries as Q
    have = set(engine().variables)
    return [v for v in Q.all_variables(store()) if v["code_id"] in have]


def area_for(code_id: str):
    from engine.analysis import Area
    r = next(r for r in regions() if r["code_id"] == code_id)
    return Area(r["code_id"], r["name"], r["bbox"])


def region_picker(key: str, default: str = C.REGION_ID, label: str = "Area") -> str:
    regs = regions()
    if not regs:
        st.error("No regions in the graph yet.")
        st.stop()
    codes = [r["code_id"] for r in regs]
    names = {r["code_id"]: f"{r['name']} ({r['n_land_cells']} land cells)" for r in regs}
    idx = codes.index(default) if default in codes else 0
    return st.selectbox(label, codes, index=idx, format_func=names.get, key=key)


def variable_picker(key: str, default: str | None = None) -> dict:
    vs = variables()
    codes = [v["code_id"] for v in vs]
    idx = codes.index(default) if default in codes else 0
    code = st.selectbox("Variable", codes, index=idx, key=key,
                        format_func=lambda c: next(v["display_name"] for v in vs if v["code_id"] == c),
                        help="Definitions come from the knowledge graph.")
    v = next(v for v in vs if v["code_id"] == code)
    st.caption(f"ℹ️ {v['definition']}  \nDataset: {v['dataset']['short_name']} "
               f"v{v['dataset']['version']} · unit: {v['unit']}")
    return v


def period_picker(key: str, default=(2001, 2024)) -> list[str]:
    a, b = st.slider("Period", 2001, 2024, default, key=key)
    return [f"{a}-01", f"{b}-12"]


# ----------------------------------------------------------------------------- maps
def _cell_geojson(df: pd.DataFrame) -> dict:
    h = C.GRID_RES / 2
    feats = []
    for cid, lat, lon in df[["cell_id", "lat", "lon"]].itertuples(index=False):
        feats.append({"type": "Feature", "id": cid, "properties": {},
                      "geometry": {"type": "Polygon", "coordinates": [[
                          [lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h],
                          [lon - h, lat + h], [lon - h, lat - h]]]}})
    return {"type": "FeatureCollection", "features": feats}


def _base_layout(fig: go.Figure, height: int = 520) -> go.Figure:
    fig.update_layout(map=dict(style="carto-positron", zoom=3.0,
                               center=dict(lat=(C.REGION.south + C.REGION.north) / 2,
                                           lon=(C.REGION.west + C.REGION.east) / 2)),
                      margin=dict(l=0, r=0, t=30, b=0), height=height)
    return fig


def trend_map(df: pd.DataFrame, unit: str, mode: str = "slope") -> go.Figure:
    """mode='slope': colour = slope per decade (significant cells), grey = not significant.
    mode='direction': red = significant increase, blue = significant decrease, grey = none."""
    fig = go.Figure()
    nons = df[df["direction"] == "none"]
    sig = df[df["direction"] != "none"]
    hover = ("%{customdata[0]}<br>slope %{customdata[1]:.3g} " + unit +
             "<br>p=%{customdata[2]:.2g}, q=%{customdata[3]:.2g}<extra></extra>")
    if len(nons):
        fig.add_trace(go.Choroplethmap(
            geojson=_cell_geojson(nons), locations=nons["cell_id"], z=np.zeros(len(nons)),
            colorscale=[[0, GREY], [1, GREY]], showscale=False, marker_opacity=0.55,
            marker_line_width=0.3, name="not significant",
            customdata=nons[["cell_id", "slope_dec", "p", "q"]].values, hovertemplate=hover))
    if len(sig):
        if mode == "direction":
            z = np.where(sig["direction"] == "up", 1, -1)
            fig.add_trace(go.Choroplethmap(
                geojson=_cell_geojson(sig), locations=sig["cell_id"], z=z,
                colorscale=[[0, BLUE], [1, RED]], zmin=-1, zmax=1, showscale=False,
                marker_opacity=0.8, marker_line_width=0.3, name="significant",
                customdata=sig[["cell_id", "slope_dec", "p", "q"]].values, hovertemplate=hover))
        else:
            lim = float(np.nanmax(np.abs(sig["slope_dec"]))) or 1.0
            fig.add_trace(go.Choroplethmap(
                geojson=_cell_geojson(sig), locations=sig["cell_id"], z=sig["slope_dec"],
                colorscale="RdBu_r", zmin=-lim, zmax=lim, marker_opacity=0.85,
                marker_line_width=0.3, name="significant",
                colorbar=dict(title=dict(text=unit, side="right")),
                customdata=sig[["cell_id", "slope_dec", "p", "q"]].values, hovertemplate=hover))
    return _base_layout(fig)


def cluster_map(df: pd.DataFrame) -> go.Figure:
    import plotly.express as px
    palette = px.colors.qualitative.Set2
    fig = go.Figure()
    for i, (lab, g) in enumerate(df.groupby(["cluster", "cluster_label"])):
        color = palette[i % len(palette)]
        fig.add_trace(go.Choroplethmap(
            geojson=_cell_geojson(g), locations=g["cell_id"], z=np.ones(len(g)),
            colorscale=[[0, color], [1, color]], showscale=False, marker_opacity=0.8,
            marker_line_width=0.3, name=f"{lab[0]}: {lab[1]}", showlegend=True,
            hovertemplate=f"cluster {lab[0]}: {lab[1]}<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.05))
    return _base_layout(fig)


def selected_cell(event) -> str | None:
    try:
        pts = event.selection.points if hasattr(event, "selection") else event["selection"]["points"]
        if pts:
            return pts[0].get("location")
    except Exception:  # noqa: BLE001
        return None
    return None


# ----------------------------------------------------------------------------- time series
def series_chart(df: pd.DataFrame, title: str, unit: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time"], y=df["anomaly"], mode="lines", name="monthly anomaly",
                             line=dict(color="#8A94A6", width=1)))
    if "trend" in df:
        fig.add_trace(go.Scatter(x=df["time"], y=df["trend_hi"], line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=df["time"], y=df["trend_lo"], line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(200,66,59,0.15)",
                                 name="slope uncertainty (95%)", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=df["time"], y=df["trend"], name="Theil-Sen trend",
                                 line=dict(color=RED, width=2.5)))
    fig.update_layout(title=title, yaxis_title=f"anomaly ({unit})", height=380,
                      margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


def raw_chart(df: pd.DataFrame, unit: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df["time"], y=df["value"], mode="lines",
                               line=dict(color=BLUE, width=1), name="monthly value"))
    fig.update_layout(yaxis_title=unit, height=260, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def fmt_p(p) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.2g}"
