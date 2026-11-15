"""PDF 2 - the version of EarthSleuth we build during the hackathon, plus future work.

Version 2: local only, AI-curated knowledge graph, graph-guided investigation.
"""
import sys

from common import *  # noqa: F401,F403
from shared import (challenge_section, diagram_stats_pipeline, glossary_section,
                    problem_section)


def diagram_hack_arch():
    W, H = 495, 340
    g = [dict(x=0, y=0, w=232, h=338, title="PHASES 1-2 — OFFLINE, done once by us",
              fill=SKY, stroke=BLUE, tc=BLUE),
         dict(x=258, y=0, w=237, h=338, title="PHASE 3 — the local app, for each question",
              fill=LILAC, stroke=PURPLE, tc=PURPLE)]
    b = {
        "ed": bx(10, 282, 212, 36, "<b>1 · Download</b> (earthaccess)<br/>MERRA-2 · GPM IMERG · "
                 "GLDAS · MODIS", fill=colors.white, stroke=BLUE),
        "pre": bx(10, 226, 212, 40, "<b>1 · Preprocess</b><br/>region · units · 1° grid · "
                  "land mask → <b>series.nc</b>", stroke=BLUE),
        "src": bx(10, 164, 212, 44, "<b>2 · Trusted sources</b><br/>NASA CMR metadata · file "
                  "headers · 5–10 papers we read · our fixed schema", stroke=ORANGE),
        "cur": bx(10, 100, 212, 46, "<b>2 · Curator agent</b> (LLM)<br/>builds the graph using "
                  "checking tools only (no free Cypher)", fill=PURPLE, stroke=PURPLE,
                  tc=colors.white),
        "rev": bx(10, 14, 212, 68, "<b>2 · Team review + backup</b><br/>validate_graph · "
                  "30-minute human check<br/>Neo4j dump + graph.json snapshot<br/>"
                  "(seed.yaml = hand-written fallback)", fill=CREAM, stroke=ORANGE),
        "user": bx(268, 290, 217, 30, "<b>Student / judge</b> asks a question → gets the "
                   "full investigation", fill=CREAM, stroke=ORANGE),
        "app": bx(268, 234, 217, 40, "<b>Streamlit app</b> (runs on our laptop)<br/>Ask · Trend "
                  "map · Time series · Radar · Graph · Report", fill=NAVY, stroke=NAVY,
                  tc=colors.white),
        "inv": bx(268, 168, 217, 50, "<b>3 · Investigator agent</b> (LLM)<br/>plan from the graph "
                  "→ call tools → check → explain", fill=PURPLE, stroke=PURPLE,
                  tc=colors.white),
        "eng": bx(268, 106, 217, 44, "<b>Stats engine + Radar-lite</b> (plain code)<br/>on "
                  "demand: whole region · sub-region · period", stroke=TEAL),
        "kg": bx(268, 14, 217, 72, "<b>Neo4j knowledge + evidence graph</b><br/>datasets · "
                 "variables + recipes · concepts · regions · methods · chart styles · papers · "
                 "findings · hypotheses", stroke=ORANGE),
    }
    a = [
        dict(pts=[("ed", "bottom"), ("pre", "top")], color=BLUE),
        dict(pts=[("pre", "bottom"), ("src", "top")], color=BLUE),
        dict(pts=[("src", "bottom"), ("cur", "top")], color=ORANGE),
        dict(pts=[("cur", "bottom"), ("rev", "top")], color=PURPLE),
        dict(pts=[("cur", "right"), (240, 123), (240, 50), ("kg", "left")], color=PURPLE,
             label="writes"),
        dict(pts=[("pre", "right"), (252, 246), (252, 128), ("eng", "left")], color=BLUE,
             label="series.nc"),
        dict(pts=[("user", "bottom"), ("app", "top")], color=NAVY, both=True),
        dict(pts=[("app", "bottom"), ("inv", "top")], color=PURPLE, both=True),
        dict(pts=[("inv", "bottom"), ("eng", "top")], color=TEAL, both=True),
        dict(pts=[("eng", "bottom"), ("kg", "top")], color=TEAL),
        dict(pts=[("inv", "right"), (491, 193), (491, 50), ("kg", "right")], color=PURPLE,
             both=True),
    ]
    return centered(Diagram(W, H, b, a, groups=g))


def diagram_guided():
    """Investigation steps (left) and the graph paths each step uses (right)."""
    W, H = 495, 352
    steps = [
        ("1 · Understand", "question → concepts",
         "reads <b>Concept</b> nodes (names + synonyms). No match → "
         "“our data can't answer this”, and suggest what it can."),
        ("2 · Plan", "→ investigation spec (Contract 1)",
         "reads Concept →INDICATED_BY→ Variable →IN_DATASET→ Dataset (+ recipe) · "
         "Region box · Method chain · ChartStyle"),
        ("3 · Analyse", "stats engine + Radar-lite (code)",
         "reads method settings (q = 0.10, minimum years) and the recipe; the numbers "
         "come from series.nc, never from the graph or the LLM"),
        ("4 · Record evidence", "written by code",
         "writes <b>Analysis</b> + <b>Finding</b> nodes, OPPOSITE_OF and "
         "CO_OCCURS_WITH edges (Layer B)"),
        ("5 · Why?", "propose hypotheses",
         "reads Finding → Variable →INFLUENCES (paper)→ Variable ← Finding; a matching "
         "HypothesisPattern → new <b>Hypothesis</b> (unverified)"),
        ("6 · Check", "audit (code)",
         "every number in the answer must appear in tool outputs; every claim has a label "
         "(observed / literature / hypothesis)"),
        ("7 · Explain", "charts + report → user",
         "reads <b>ChartStyle</b> → Plotly charts; report with provenance; the whole "
         "investigation stays in the graph"),
    ]
    b, a = {}, []
    for i, (t1, t2, right) in enumerate(steps):
        y = 296 - 47 * i
        b[f"s{i}"] = bx(0, y, 200, 38, f"<b>{t1}</b><br/>{t2}", fill=colors.white,
                        stroke=PURPLE, fs=8.2)
        b[f"g{i}"] = bx(250, y, 245, 38, right, fill=CREAM, stroke=ORANGE, fs=7.4)
        a.append(dict(pts=[(f"s{i}", "right"), (f"g{i}", "left")], color=ORANGE,
                      dashed=True, both=True))
        if i:
            a.append(dict(pts=[(f"s{i-1}", "bottom", 0.5), (f"s{i}", "top", 0.5)],
                          color=PURPLE))
    t = [dict(x=100, y=342, text="INVESTIGATOR STEPS", fs=8, color=PURPLE, bold=True,
              anchor="center"),
         dict(x=372, y=342, text="WHAT IT READS / WRITES IN THE GRAPH", fs=8, color=ORANGE,
              bold=True, anchor="center")]
    return centered(Diagram(W, H, b, a, texts=t))


EXTRA_GLOSSARY = [
    ("Curator agent", "Our AI agent that builds and maintains the knowledge graph. It can only use "
     "checking tools; it decides what to add, but the facts come from trusted sources."),
    ("Investigator agent", "Our AI agent that answers a user's question by following the graph: "
     "plan, call tools, check, explain."),
    ("Schema (ontology)", "The fixed list of allowed node types, relationship types and required "
     "properties in our graph. The agents fill it but cannot change it."),
    ("Recipe (in our graph)", "The properties that say how to use a variable: file, name inside "
     "the file, unit, scale factor, fill value, conversion."),
    ("MERGE (Cypher)", "“Create this node only if it does not already exist.” Prevents "
     "duplicates."),
    ("Snapshot / dump", "A saved copy of the whole graph we can reload if something breaks."),
    ("Tool (for an AI agent)", "A Python function the LLM is allowed to call. The tool does the "
     "real work and returns the result."),
    ("Sub-region", "A smaller area inside our region (e.g. Tunisia, Iberia), stored in the "
     "graph as a box of grid cells."),
]


def build(path):
    doc = Doc(path, "The hackathon build\nWhat we ship this weekend, and what comes next",
              "Real NASA data, real statistics, a knowledge graph built by AI.\n"
              "Document 2 of 2, v2 — deadline: Sunday, November 15, 11:59 p.m. (local time).",
              "Document 2 · Hackathon build")
    st = []
    st.append(NextPageTemplate("normal"))
    st.append(Spacer(1, 300))
    st.append(P("<b>What this document is.</b> Document 1 describes the complete EarthSleuth "
                "system. This document describes the <b>smaller version we will really build and "
                "submit</b> before the deadline, with exact datasets, exact methods, file formats, "
                "who does what and when, the demo plan, and finally the <b>future work</b>: "
                "everything from Document 1 that we leave for later."))
    st.append(P("<b>The one-sentence plan.</b> We download 5 NASA variables for the Mediterranean "
                "and North Africa (2001–2024, monthly, 1° grid); an <b>AI curator agent</b> builds "
                "a Neo4j knowledge graph that holds everything an investigation needs; then an "
                "<b>AI investigator agent</b> answers a user's question by following that graph "
                "— it plans, runs real statistics and machine learning (plain code), proposes "
                "hypotheses along graph paths, and returns a complete, honest investigation. "
                "Everything runs on our own laptops."))
    st.append(box("note", [
        "<b>Local only.</b> Nothing is deployed. The app runs on our laptops; we submit a public "
        "GitHub repository plus a video or slides.",
        "<b>The graph is built by AI.</b> A curator agent fills and maintains Neo4j with checking "
        "tools and a fixed schema. The hand-written seed.yaml is now only the backup.",
        "<b>The graph guides the investigation.</b> It stores the recipes (how to read each "
        "variable), the methods, the chart styles and the hypothesis patterns, so the plan is a "
        "walk through the graph.",
        "<b>Statistics on demand.</b> Users can ask about a sub-region (e.g. Tunisia) or a "
        "sub-period inside our data; the engine runs in seconds.",
        "<b>No real-time downloading yet.</b> We, the developers, choose and download the data "
        "beforehand. Live retrieval for any region is future work.",
    ], title="What changed in version 2 (after our team discussion)"))
    st.append(P("Coloured boxes: <font color='#E58A2B'><b>orange</b></font> = simple explanation, "
                "<font color='#C8423B'><b>red</b></font> = rule or risk, "
                "<font color='#138A7E'><b>green</b></font> = example, "
                "<font color='#1F5FA8'><b>blue</b></font> = good to know, "
                "<font color='#6A4FA0'><b>purple</b></font> = owner / future work."))
    st.append(PageBreak())
    st.append(P("Contents", "H1x"))
    st.append(toc())
    st.append(PageBreak())

    problem_section(st)
    st.append(PageBreak())
    challenge_section(st)
    st.append(PageBreak())

    # -------------------------------------------------------------- 3 what we build
    st.append(H1("3. What we build this weekend"))
    st.append(P("We keep the <b>three superpowers</b> of the full system, each in a small but real "
                "form:"))
    st.append(table([
        ["Superpower", "Full system (Document 1)", "Hackathon version (this document)"],
        ["DISCOVER", "Earth Signal Radar over any region, dozens of variables, clustering, change "
         "points, GNN.", "Radar-lite: 5 variables, one big region (and its sub-regions), ranking by "
         "significant area, opposite-trend maps, k-means clusters of trend signatures."],
        ["CONNECT", "Self-growing Neo4j graph harvested from CMR, literature GraphRAG, two layers.",
         "A Neo4j graph <b>built by an AI curator agent</b> from NASA metadata, our files and a few "
         "papers, with checking tools and a fixed schema. It also stores recipes, methods and chart "
         "styles. Same two layers, same three kinds of truth."],
        ["INVESTIGATE", "Six agents orchestrated with LangGraph, live data acquisition, auditor, "
         "hypothesis engine.", "One investigator agent <b>guided by the graph</b>: it plans from "
         "graph paths, calls tools that run the real statistics, proposes hypotheses along "
         "graph paths, and labels every explanation by evidence type."],
    ], [1.1, 2.9, 3.0]))
    st.append(box("rule", [
        "<b>We keep every golden rule from Document 1</b>, even in the small version: the AI never "
        "computes numbers; every finding has provenance; hypotheses are always labelled; ML suggests, "
        "statistics decides. These rules are what make the project scientifically valid (the "
        "<b>Validity</b> criterion).",
        "<b>New rule for the AI-built graph: the AI decides what goes in, but it never makes up the "
        "facts.</b> Facts come from trusted sources (NASA's catalogue, the files themselves, papers "
        "we read) through tools that check them before writing."], title="Non-negotiable"))
    st.append(H2("3.1 In scope / out of scope"))
    st.append(table([
        ["Part", "In scope (we build it)", "Out of scope (future work)"],
        ["Region", "Chosen by us: Mediterranean + North Africa. Users can ask about sub-regions "
         "inside it (Tunisia, Iberia, Nile Delta...)", "Any region in the world, user-drawn shapes"],
        ["Variables", "5: air temperature, precipitation, soil moisture, evapotranspiration, NDVI",
         "Dozens: LST, AIRS profiles, OMI NO<sub>2</sub>, GRACE, ocean variables"],
        ["Data access", "Downloaded and processed once by us, before the demo", "Real-time "
         "retrieval for any region, variables and period the user picks"],
        ["Grid / period", "1° grid, monthly, 2001–2024 (users may pick a shorter period)",
         "0.25° or finer, daily, longer records"],
        ["Statistics", "Anomalies, Theil–Sen, Mann–Kendall (Hamed–Rao), 95% CI, "
         "BH-FDR, regional average; on demand for any sub-region / sub-period",
         "Seasonal MK option, block bootstrap, field significance tests"],
        ["Discovery", "Ranking, opposite-trend map, k-means", "HDBSCAN, change points, anomalies, GNN"],
        ["Graph", "Built by the curator agent (checking tools, fixed schema), reviewed by us; "
         "findings added by code; seed.yaml as backup", "Continuous curation of all of CMR, "
         "literature at scale, a review screen for humans"],
        ["AI", "2 agents: curator (offline) + investigator (online), both with tools",
         "6 agents + Orchestrator in LangGraph"],
        ["App", "Streamlit, running locally on our laptops", "Hosted public web app, React + "
         "MapLibre, accounts, sharing"],
        ["Submission", "Public GitHub repo (README, screenshots) + video or slides", "—"],
    ], [1.1, 3.0, 2.9]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 4 architecture
    st.append(H1("4. The whole flow (architecture)"))
    st.append(P("The system works in <b>four phases</b>. Phases 1 and 2 happen once, before the "
                "demo, on our laptops. Phase 3 happens every time someone asks a question, and "
                "phase 4 is the answer they get back."))
    st.append(diagram_hack_arch())
    st.append(caption("Figure 2. Left: what we prepare once (data + graph). Right: what happens "
                      "for each question."))
    st.append(box("kid", [
        "Think of a restaurant. <b>Phase 1:</b> we buy and wash the ingredients (download and "
        "clean the data). <b>Phase 2:</b> a librarian robot writes the cookbook — what each "
        "ingredient is, where it is stored, how to prepare it, which recipes go together "
        "(the curator agent builds the graph). <b>Phase 3:</b> a customer orders, and the chef "
        "robot follows the cookbook step by step to cook the dish (the investigator follows the "
        "graph). <b>Phase 4:</b> the dish arrives, with a card saying exactly what is in it "
        "(the report with provenance)."]))
    st.append(H2("4.1 The four phases in plain words"))
    st.append(table([
        ["Phase", "What happens", "Input", "Output"],
        ["1 · Data (once)", "We download the 5 datasets for our region and period, convert units, "
         "put everything on the same 1° grid, keep land only.", "NASA Earthdata (4 datasets)",
         "<b>series.nc</b>: 5 variables × 288 months × ~600 land cells"],
        ["2 · Graph (once)", "The curator agent reads trusted sources and fills Neo4j through "
         "checking tools. We review it, then save a backup.", "NASA CMR metadata, our files' "
         "headers, 5–10 papers, the schema", "A checked Neo4j graph + dump + graph.json"],
        ["3 · Investigation (each question)", "The investigator agent turns the question into a "
         "plan by walking the graph, calls tools that run the statistics and ML on series.nc, "
         "writes findings back to the graph, proposes hypotheses along graph paths, checks "
         "itself.", "The question (+ optional sub-region / period)", "Findings, hypotheses, "
         "charts, an explanation"],
        ["4 · Result", "The user sees the answer, the maps, the time series, the graph of "
         "evidence and a downloadable report. The investigation stays in the graph.",
         "Everything from phase 3", "Report with numbers, labels, sources, limits"],
    ], [1.25, 3.1, 1.45, 1.6]))
    st.append(H2("4.2 Repository layout"))
    st.append(code("""
earthsleuth/
  run.py               # one command per phase: download | preprocess | build_graph | app
  .env.example         # names of the secrets (Earthdata, LLM key) - the real .env is NOT committed
  pipeline/
    download.py        # earthaccess search + download, one dataset at a time
    preprocess.py      # subset, units, regrid to 1 deg, land mask -> data/processed/series.nc
  engine/
    stats.py           # deseasonalize, theil_sen, mann_kendall, fdr  (+ unit tests)
    radar.py           # ranking, opposite-trend map, k-means clusters
    run_all.py         # whole region, all variables -> trends.parquet, clusters.parquet (cache)
  graph/
    schema.yaml        # CONTRACT 0: allowed node types, edge types, required properties
    curator_tools.py   # the checking tools (add_dataset, add_variable, ...) - the only way to write
    curator_agent.py   # the LLM loop that builds the graph; saves a build log
    validate_graph.py  # automatic checks after each build
    export.py          # Neo4j -> graph.json snapshot (+ instructions for neo4j-admin dump)
    seed.yaml          # hand-written backup with the same schema
    load_seed.py       # loads seed.yaml if the curator fails
  agent/
    tools.py           # python functions the investigator can call (graph + engine)
    agent.py           # tool-calling loop + system prompt + number check
    cache/             # saved investigations for the demo questions
  app/
    Home.py            # Streamlit entry page
    pages/             # 1_Ask.py, 2_Trend_map.py, 3_Radar.py, 4_Graph.py, 5_Report.py
  data/processed/      # small result files, committed to the repo
  tests/
"""))
    st.append(H2("4.3 The contracts (agree on these first!)"))
    st.append(P("The team talks through <b>three formats</b>. If we agree on them in the first "
                "hour, everyone can work in parallel with fake data and plug in the real data "
                "later. <b>Contract 0</b> is the graph schema (section 8.4). Contracts 1 and 2 are "
                "the same as in Document 1:"))
    st.append(code("""
// Contract 1: investigation spec (investigator -> engine). Filled from graph queries.
{ "question": "Where is it getting hotter while water becomes scarcer?",
  "concepts": ["surface heating", "water availability"],
  "variables": ["t2m", "precip", "soil_moisture", "et"],
  "region": "mediterranean_north_africa",      // or a sub-region id from the graph
  "period": ["2001-01", "2024-12"],
  "methods": ["anomalies", "theil_sen", "mk_hamed_rao", "bh_fdr", "regional_mean"],
  "outputs": ["trend_maps", "opposite_map", "clusters", "regional_series", "explanation"] }

// Contract 2: result for one variable (engine -> agent / app)
{ "variable": "precip", "unit": "mm/month", "region": "mediterranean_north_africa",
  "period": ["2001-01", "2024-12"],
  "regional": { "slope_per_decade": -1.9, "ci95": [-3.4, -0.3], "p": 0.02, "significant": true },
  "cells": { "n": 610, "sig_up": 41, "sig_down": 128, "pct_sig_area": 27.7 },
  "method": "anomalies; Theil-Sen; MK Hamed-Rao; BH-FDR q=0.10; cos-lat weights",
  "datasets": ["GPM_3IMERGM v07"], "run_id": "2026-11-15T03:12Z-ab12cd3" }
"""))
    st.append(P("<i>Numbers above are placeholders to show the format, not results.</i>", "small"))
    st.append(H2("4.4 One command per phase"))
    st.append(code("""
python run.py download      # phase 1a: NASA -> data/raw (one file at a time)
python run.py preprocess    # phase 1b: -> data/processed/series.nc
python run.py precompute    # whole-region trends + clusters -> trends.parquet, clusters.parquet
python run.py build_graph   # phase 2: curator agent -> Neo4j, then validate + export graph.json
python run.py load_seed     # backup for phase 2 if the curator fails
python run.py app           # phases 3-4: streamlit run app/Home.py
"""))
    st.append(P("A new teammate (or a judge reading the README) can rebuild everything with these "
                "six lines."))
    st.append(PageBreak())

    # -------------------------------------------------------------- 5 data
    st.append(H1("5. The NASA data we use (exactly)"))
    st.append(H2("5.1 Region, period and grid"))
    st.append(P("These choices are made by <b>us, the developers</b>, before the hackathon build "
                "starts. Users then ask questions inside them."))
    st.append(table([
        ["Choice", "Value", "Why"],
        ["Region", "Longitude 10°W → 40°E, latitude 25°N → 47°N "
         "(Mediterranean + North Africa, including Tunisia)", "Known climate hot spot; contains wet "
         "north and dry south, so opposite trends are possible; personally relevant to us."],
        ["Period", "January 2001 → December 2024 (24 years, 288 months). Add 2025 only if all "
         "datasets have complete 2025 files.", "All five datasets cover it; 20+ years is enough for "
         "trend statistics."],
        ["Time step", "Monthly", "The challenge says monthly is easiest; seasons are easy to remove."],
        ["Grid", "1° × 1° (50 × 22 = 1,100 cells; roughly 600 are land)",
         "Small and fast; still shows regional patterns."],
        ["Mask", "Land cells only (where GLDAS has data)", "Soil moisture, ET and NDVI only exist "
         "on land."],
    ], [1.0, 3.0, 3.0]))
    st.append(H2("5.2 The five variables"))
    st.append(table([
        ["Variable", "Dataset (short name, version)", "Name inside the file", "Native grid / unit",
         "We convert to"],
        ["Air temperature at 2 m", "MERRA-2 <b>M2TMNXSLV</b> v5.12.4", "T2M",
         "0.5°×0.625° / K", "°C (−273.15)"],
        ["Precipitation", "GPM IMERG Final monthly <b>GPM_3IMERGM</b> v07", "precipitation "
         "(group “Grid”)", "0.1° / mm/hr", "mm/month (× hours in month)"],
        ["Soil moisture (0–10 cm)", "<b>GLDAS_NOAH025_M</b> v2.1", "SoilMoi0_10cm_inst",
         "0.25° / kg/m²", "kg/m² (= mm of water)"],
        ["Evapotranspiration", "<b>GLDAS_NOAH025_M</b> v2.1", "Evap_tavg", "0.25° / kg/m²/s",
         "mm/day (× 86,400)"],
        ["Vegetation (NDVI)", "MODIS Terra <b>MOD13C2</b> v061", "CMG 0.05 Deg Monthly NDVI",
         "0.05° / integer", "−1..1 (× 0.0001)"],
        ["<i>Stretch:</i> land surface temp.", "MODIS Terra <b>MOD11C3</b> v061", "LST_Day_CMG",
         "0.05° / integer", "K × 0.02 → °C"],
    ], [1.25, 1.75, 1.4, 1.3, 1.3], font=8.2))
    st.append(P("Every value in this table also ends up in the graph as the variable's "
                "<b>recipe</b> (section 8.5). The curator agent reads them from the real files and "
                "from NASA's catalogue; this table is what we use to check its work."))
    st.append(box("note", [
        "<b>Air temperature (MERRA-2) and land surface temperature (MODIS) are different things.</b> "
        "Air temperature is measured in the air at 2 m; land surface temperature is the skin of the "
        "ground and can be 20 °C hotter in a desert afternoon. We start with MERRA-2 because "
        "it is gap-free and easy to read; LST is a stretch goal."]))
    st.append(H2("5.3 How to get the data (step by step)"))
    st.append(bullets([
        "Everyone who downloads creates a free <b>Earthdata Login</b> account at "
        "urs.earthdata.nasa.gov.",
        "In the Earthdata profile, under <i>Applications → Authorized Apps</i>, approve <b>NASA "
        "GESDISC DATA ARCHIVE</b>. MERRA-2, GPM and GLDAS are served by GES DISC and downloads fail "
        "with an error until this is approved. MODIS comes from LP DAAC.",
        "Install: <font name='Mono'>pip install earthaccess xarray netCDF4 h5netcdf pyhdf "
        "pymannkendall scipy statsmodels scikit-learn pandas pyarrow neo4j</font>.",
        "Process <b>one file at a time</b>: download → open → cut the region → "
        "average to 1° → save the small result → delete the big raw file. This keeps the "
        "disk from filling up (global files are tens to hundreds of MB each, and we need 288 per "
        "dataset). <b>Keep one raw file per dataset</b>: the curator agent reads its header.",
        "Run the downloads in parallel (one terminal per dataset) as early as possible on Saturday.",
    ], numbered=True))
    st.append(code("""
import earthaccess, xarray as xr

earthaccess.login()   # reads ~/.netrc or EARTHDATA_USERNAME / EARTHDATA_PASSWORD
BBOX = (-10, 25, 40, 47)  # (west, south, east, north)

results = earthaccess.search_data(short_name="GLDAS_NOAH025_M", version="2.1",
                                  temporal=("2001-01-01", "2024-12-31"), bounding_box=BBOX)
print(len(results))   # expect 288 monthly granules

for granule in results:
    [path] = earthaccess.download([granule], "data/raw/gldas")
    ds = xr.open_dataset(path)[["SoilMoi0_10cm_inst", "Evap_tavg"]]
    ds = ds.sel(lon=slice(-10, 40), lat=slice(25, 47))
    small = ds.coarsen(lat=4, lon=4, boundary="trim").mean()   # 0.25 deg -> 1 deg
    small.to_netcdf(path.replace("raw", "small"))
    # os.remove(path)   # free disk space once it works (keep one file for the curator)
""", "Example: download and shrink GLDAS (the same pattern works for the others)"))
    st.append(H2("5.4 Dataset-specific gotchas"))
    st.append(table([
        ["Dataset", "Watch out for"],
        ["GPM_3IMERGM", "Files are HDF5 with the data inside a group: open with "
         "<font name='Mono'>xr.open_dataset(f, group=\"Grid\", engine=\"h5netcdf\")</font>. The "
         "dimensions are ordered (time, lon, lat) — transpose to (time, lat, lon). Units are mm/hr: "
         "multiply by 24 × days in the month."],
        ["M2TMNXSLV", "Grid is 0.5° × 0.625°, which does not divide evenly into 1°: "
         "use <font name='Mono'>ds.interp(lat=..., lon=...)</font> onto the 1° cell centres "
         "(fine for a smooth field like temperature). Select only T2M; files contain many variables."],
        ["GLDAS_NOAH025_M", "Ocean cells are missing (NaN): this is our land mask. Evap_tavg is a "
         "flux in kg/m²/s: × 86,400 = mm/day."],
        ["MOD13C2 / MOD11C3", "HDF4 files (older format): read with <font name='Mono'>pyhdf</font> "
         "or <font name='Mono'>rioxarray</font>. Apply the scale factor and the fill value. The "
         "global 0.05° grid is large; cut the region first. <b>If reading HDF4 costs more than "
         "2 hours, drop NDVI</b> and keep 4 variables."],
        ["All", "When averaging to 1°, keep a cell only if at least half of its small cells "
         "have data. Write down every file name and version (provenance)."],
    ], [1.3, 5.7]))
    st.append(box("note", [
        "<b>NASA Giovanni</b> (giovanni.gsfc.nasa.gov) can draw an area-averaged time series for the "
        "same datasets in a browser. Use it to <b>check our regional averages</b>: if our curve and "
        "Giovanni's curve look the same, our preprocessing is right. That check is also a strong "
        "point for the Validity score."], title="Validation trick"))
    st.append(box("owner", ["Integration / product engineers run downloads and preprocessing; the "
                            "ML engineer checks units and the final <font name='Mono'>series.nc</font>."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 6 stats
    st.append(H1("6. The statistics engine (hackathon version)"))
    st.append(P("Same eight steps as the full system (Document 1, section 8), applied to each of the "
                "~600 land cells and to the regional average, for each variable. For the whole "
                "region we compute once and save the result (a cache); for a sub-region or a "
                "shorter period, the <b>same code runs on demand</b> when the investigator asks "
                "(section 6.3)."))
    st.append(diagram_stats_pipeline())
    st.append(caption("Figure 3. The eight steps. Everything here is plain Python; no AI is involved."))
    st.append(H2("6.1 The recipe, in plain words"))
    st.append(bullets([
        "<b>Anomalies.</b> For each cell, subtract the average of each calendar month (all "
        "Januaries, all Februaries...). This removes summer/winter.",
        "<b>Slope.</b> Theil–Sen slope (median of all pairwise slopes), reported per decade, "
        "with a 95% confidence interval.",
        "<b>Test.</b> Mann–Kendall with the Hamed–Rao correction for autocorrelation "
        "(neighbouring months look alike, so the plain test would be over-confident).",
        "<b>Many cells.</b> Benjamini–Hochberg FDR across all cells of one variable, with "
        "q = 0.10 (as recommended by Wilks 2016 for maps). A cell is “significant” only if "
        "its q-value ≤ 0.10.",
        "<b>Regional average.</b> Average all land cells weighted by cos(latitude), then run the same "
        "slope and test on that single series.",
        "<b>Stretch:</b> “years needed” estimate for non-significant trends "
        "(Weatherhead et al. 1998, formula in Document 1, section 8.1) and an OLS + t-test comparison.",
    ], numbered=True))
    st.append(code("""
import numpy as np, pandas as pd, pymannkendall as mk
from scipy.stats import theilslopes
from statsmodels.stats.multitest import multipletests

def anomalies(s: pd.Series) -> pd.Series:            # s: monthly values, DatetimeIndex
    return s - s.groupby(s.index.month).transform("mean")

def cell_trend(s: pd.Series, min_valid=0.8):
    a = anomalies(s).dropna()
    if len(a) < min_valid * len(s):
        return None                                   # too many missing months
    t = (a.index - a.index[0]).days / 365.25          # time in years
    slope, intercept, lo, hi = theilslopes(a.values, t, alpha=0.95)
    test = mk.hamed_rao_modification_test(a.values)
    return dict(slope_dec=slope * 10, ci_lo=lo * 10, ci_hi=hi * 10,
                p=test.p, tau=test.Tau, n=len(a))

def add_fdr(df: pd.DataFrame, q=0.10):               # one row per cell, one variable
    ok = df["p"].notna()
    reject, qvals, _, _ = multipletests(df.loc[ok, "p"], alpha=q, method="fdr_bh")
    df.loc[ok, "q"] = qvals
    df.loc[ok, "significant"] = reject
    return df
""", "engine/stats.py — the core (about 30 lines)"))
    st.append(box("warn", [
        "The confidence interval from <font name='Mono'>theilslopes</font> does not account for "
        "autocorrelation, so it can be a bit too narrow. We say so in the report (honesty is part of "
        "Validity). The block bootstrap fix is future work.",
        "Test the engine on <b>fake data</b> first: a series with a known slope + noise must give "
        "back that slope; pure noise should be significant in about 5% of cases before FDR and "
        "rarely after FDR. These tests take 20 minutes and catch most bugs."], title="Be honest"))
    st.append(H2("6.2 Output: trends.parquet"))
    st.append(table([
        ["Column", "Meaning"],
        ["variable, cell_id, lat, lon", "Which variable and which 1° cell"],
        ["slope_dec, ci_lo, ci_hi, unit", "Trend per decade and its 95% interval"],
        ["p, q, significant, tau, n", "Test results (q = after FDR)"],
        ["direction", "up / down / none (none if not significant)"],
        ["region, period", "Which area and which years this row was computed for"],
        ["run_id, datasets", "Provenance: code version + dataset versions"],
    ], [2.4, 4.6]))
    st.append(H2("6.3 On demand: sub-regions and shorter periods"))
    st.append(P("Users will ask things like <i>“Is Tunisia getting drier since 2010?”</i>. The "
                "investigator reads the sub-region's box from the graph and calls the engine with "
                "that box and period. On a few hundred cells this takes seconds. The result is "
                "saved with its region and period, so the same question is instant next time."))
    st.append(table([
        ["Guardrail (code, not AI)", "What the user sees"],
        ["Period shorter than 15 years", "A warning: “Trends over short periods are unreliable; "
         "natural ups and downs can look like a trend.” Below 10 years: refused."],
        ["Sub-region with fewer than 10 land cells", "Refused, with a suggestion of the nearest "
         "larger sub-region in the graph."],
        ["Period outside 2001–2024", "Refused: “Our data covers 2001–2024.”"],
        ["FDR scope", "Always applied across the cells of the area that was asked about, and "
         "the report says so."],
    ], [2.4, 4.6]))
    st.append(box("owner", ["The ML engineer owns stats.py, its tests, run_all.py and the on-demand "
                            "function the investigator calls."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 7 radar
    st.append(H1("7. Radar-lite: automatic discovery"))
    st.append(P("Even in the small version, the app does not just wait for questions. It shows "
                "<b>what is changing the most</b> in the region (or the sub-region being "
                "investigated), without the user picking a variable. Three simple, solid tools:"))
    st.append(H2("7.1 Ranking the variables"))
    st.append(P("For each variable: the percentage of land area (cos-latitude weighted) with a "
                "significant trend after FDR, split into up and down, plus the regional trend. The "
                "Radar page shows them as a ranked list: <i>“Soil moisture: 31% of the area "
                "drying significantly, 4% getting wetter.”</i>"))
    st.append(H2("7.2 The opposite-trend map"))
    st.append(P("For each variable, colour every cell: <font color='#C8423B'><b>significant "
                "increase</b></font>, <font color='#1F5FA8'><b>significant decrease</b></font>, or "
                "grey (no significant change). Next to the map, show the regional average trend. When "
                "both colours appear in large patches, the app highlights it: <i>“The regional "
                "average shows little change because the north and the south move in opposite "
                "directions.”</i> This directly answers the special point of the challenge."))
    st.append(H2("7.3 Trend-signature clusters"))
    st.append(P("Each land cell becomes a list of 5 numbers: its standardised slopes for the 5 "
                "variables. k-means groups similar cells (try k = 3 to 6, choose with the "
                "silhouette score). Each cluster gets a readable name from its average signature, "
                "e.g. <b>“warming + drying”</b> (T2M ↑, precipitation ↓, soil "
                "moisture ↓, NDVI ↓)."))
    st.append(code("""
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

wide = trends.pivot(index="cell_id", columns="variable", values="slope_dec").dropna()
X = StandardScaler().fit_transform(wide)
best = max(range(3, 7), key=lambda k: silhouette_score(
           X, KMeans(k, n_init=10, random_state=0).fit_predict(X)))
wide["cluster"] = KMeans(best, n_init=10, random_state=0).fit_predict(X)
"""))
    st.append(box("rule", ["Clusters only say “these places changed in a similar way”. "
                           "Whether each trend is real is decided by the significance test, not by "
                           "the clustering."]))
    st.append(box("owner", ["The ML engineer owns radar.py."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 8 graph
    st.append(H1("8. The knowledge + evidence graph (hackathon version)"))
    st.append(P("We keep the graph idea from Document 1 with the same two layers. <b>Layer A</b> "
                "(knowledge) is now built and maintained by an <b>AI curator agent</b> "
                "(sections 8.4–8.7), and it holds more than facts: it also holds the "
                "<b>recipes</b>, <b>methods</b> and <b>chart styles</b> that the investigation "
                "follows. <b>Layer B</b> (evidence) is added automatically by code from our results."))
    st.append(box("kid", [
        "The graph is the team's shared brain <b>and</b> its cookbook. It knows that “drought” is "
        "measured by soil moisture, that soil moisture lives in the GLDAS file under the name "
        "SoilMoi0_10cm_inst, that it must be plotted with a blue-to-red colour scale, and that a "
        "paper says less rain leads to drier soil. The investigator just follows the arrows."]))
    st.append(H2("8.1 What goes into seed.yaml (Layer A)"))
    st.append(P("This list is two things at once: the <b>target</b> the curator agent must build "
                "(we check its work against it), and the content of <font name='Mono'>seed.yaml"
                "</font>, the hand-written <b>backup</b> with the same schema that we load if "
                "the curator fails."))
    st.append(table([
        ["Node type", "Nodes to create"],
        ["Mission / Model", "Terra, Aqua, GPM, MERRA-2, GLDAS"],
        ["Instrument", "MODIS (+ the GPM constellation as one node)"],
        ["Dataset", "M2TMNXSLV, GPM_3IMERGM, GLDAS_NOAH025_M, MOD13C2 (+ MOD11C3 if used)"],
        ["Variable", "T2M, precipitation, SoilMoi0_10cm_inst, Evap_tavg, NDVI — each with a "
         "one-sentence definition for students, a unit and a CF standard name"],
        ["Concept", "Surface heating, water availability, drought, vegetation health, "
         "evaporative demand, water cycle"],
        ["Region", "Mediterranean + North Africa, and sub-regions (e.g. Iberia, Maghreb, Tunisia, "
         "Nile Delta, Levant, Sahara margin) as boxes or lists of cells"],
        ["Paper / Report", "5–10 references the team has actually read and checked (e.g. the "
         "IPCC AR6 Mediterranean material). Do not add a paper nobody has opened."],
        ["Method / ChartStyle / HypothesisPattern", "New in version 2: the investigation strategy "
         "(section 8.5)."],
    ], [1.4, 5.6]))
    st.append(P("Edges: CARRIES, MEASURES/PROVIDES, HAS_VARIABLE, INDICATOR_OF (variable → "
                "concept), INFLUENCES (variable → variable, <i>literature</i>, with the paper as "
                "source), PART_OF (region → region)."))
    st.append(H2("8.2 What gets added automatically (Layer B)"))
    st.append(bullets([
        "One <b>Analysis</b> node per run (run_id, code version, date, methods).",
        "One <b>Finding</b> node per variable × sub-region with a significant regional trend, "
        "and one per Radar cluster, holding slope, CI, p, q, period and datasets (provenance).",
        "<b>OPPOSITE_OF</b> edges between findings of the same variable with opposite significant "
        "directions in two sub-regions.",
        "<b>CO_OCCURS_WITH</b> edges when two variables have significant trends in mostly the same "
        "cells.",
        "<b>Hypothesis</b> nodes are created only by the agent, always with status = "
        "“unverified”, and drawn dashed.",
    ]))
    st.append(P("All of these are written by <b>code</b> from the engine's output (the numbers "
                "never pass through the LLM). Every investigation adds to Layer B, so the graph "
                "grows with every question."))
    st.append(H2("8.3 Neo4j or not?"))
    st.append(P("Since everything runs locally, <b>Neo4j is our main graph</b>. We still keep "
                "snapshots, because an AI that writes to a database can also break it."))
    st.append(table([
        ["Option", "Use it for", "Why"],
        ["Neo4j Desktop (or Docker) on one laptop", "The live graph: the curator writes to it, the "
         "investigator reads from it, the Graph page shows it", "Real graph-database use; Cypher "
         "queries make the AI's retrieval precise; Neo4j Browser is great for screenshots."],
        ["neo4j-admin dump", "A restore point after every good curator run", "One bad agent run "
         "cannot destroy the work."],
        ["graph.json (+ networkx)", "Committed to the repo; fallback if Neo4j is not running",
         "Teammates without Neo4j can still run the app; judges can see the graph in the repo."],
    ], [1.8, 2.4, 2.8]))
    st.append(P("<font name='Mono'>export.py</font> writes graph.json from Neo4j after every "
                "validated build, so the two always match."))

    st.append(H2("8.4 The fixed schema (Contract 0)"))
    st.append(P("The curator agent fills the graph, but <b>it cannot invent new kinds of nodes or "
                "relationships</b>. <font name='Mono'>graph/schema.yaml</font> lists what is "
                "allowed and which properties are required. The tools refuse anything else."))
    st.append(table([
        ["Node label", "Required properties (examples)"],
        ["Mission, Instrument", "id, name, source (CMR)"],
        ["Dataset", "id = short_name + version, title, cmr_concept_id, doi, time_start, time_end, "
         "provider (DAAC), local_path"],
        ["Variable", "id = dataset/name_in_file, display_name, definition_for_students, "
         "<b>recipe</b>: group, unit_native, unit_target, scale_factor, add_offset, fill_value, "
         "conversion, cf_standard_name, kind (state / flux / index)"],
        ["Concept", "id, name, synonyms (e.g. drought: “dry”, “drier”, “water stress”)"],
        ["Region", "id, name, bbox (west, south, east, north), n_land_cells, parent"],
        ["Method", "id, name, order, parameters (e.g. q = 0.10), applies_to_kind"],
        ["ChartStyle", "id, chart_type, colormap, label_template (e.g. “{unit} per decade”)"],
        ["Paper", "id, title, year, doi, abstract, read_by (a team member's name)"],
        ["HypothesisPattern", "id, description, required_pattern (in words + a Cypher query)"],
        ["Analysis, Finding, Hypothesis", "Layer B (section 8.2); Hypothesis.status is always "
         "“unverified”"],
    ], [1.6, 5.4], font=8.3))
    st.append(P("Relationship types: CARRIES, PROVIDES, HAS_VARIABLE, IN_DATASET, INDICATOR_OF, "
                "INFLUENCES, PART_OF, NEXT (method → method), APPLIES_TO (method → variable "
                "kind), DRAWN_AS (variable → chart style), SUPPORTED_BY (edge → paper), plus "
                "the Layer B edges ABOUT, IN_REGION, FROM_ANALYSIS, OPPOSITE_OF, CO_OCCURS_WITH, "
                "SUGGESTS."))
    st.append(box("rule", [
        "Every node and edge also has: <b>source</b> (where the fact came from), "
        "<b>created_by</b> (curator / code / investigator / human), <b>confidence</b>, "
        "<b>status</b> (verified / from_paper / hypothesis) and <b>created_at</b>.",
        "Every node has a <b>canonical id</b> (e.g. <font name='Mono'>var:GLDAS_NOAH025_M/"
        "SoilMoi0_10cm_inst</font>) and is written with <b>MERGE</b>, so the same thing can never "
        "exist twice.",
        "The investigation pipeline only uses nodes with status <b>verified</b> or "
        "<b>from_paper</b>. Hypotheses are shown, never used as facts."], title="On everything"))

    st.append(H2("8.5 Recipes and strategy: the graph is the cookbook"))
    st.append(P("This is what makes the graph “contain everything needed for the whole process”. "
                "Here is what the graph knows about one concept, written as a picture in text:"))
    st.append(code("""
(Concept "drought") <-[:INDICATOR_OF]- (Variable SoilMoi0_10cm_inst)
(Variable SoilMoi0_10cm_inst) -[:IN_DATASET]-> (Dataset GLDAS_NOAH025_M v2.1)
      recipe: unit kg/m2, fill -9999, kind = state, file path, name inside the file
(Variable SoilMoi0_10cm_inst) -[:DRAWN_AS]-> (ChartStyle "diverging_trend_map")
      colormap: blue (drier) .. red (wetter), label "{unit} per decade"
(Method anomalies) -[:NEXT]-> (Method theil_sen) -[:NEXT]-> (Method mk_hamed_rao)
      -[:NEXT]-> (Method bh_fdr) -[:NEXT]-> (Method regional_mean)
(Variable precipitation) -[:INFLUENCES {sign:"+"}]-> (Variable SoilMoi0_10cm_inst)
      -[:SUPPORTED_BY]-> (Paper "..."), status = from_paper
(HypothesisPattern "co-trend + literature link")
      "two Findings in the same region + an INFLUENCES edge between their variables
       -> propose a Hypothesis (unverified)"
"""))
    st.append(P("And the query the investigator uses to turn a concept into a full plan:"))
    st.append(code("""
MATCH (c:Concept)<-[:INDICATOR_OF]-(v:Variable)-[:IN_DATASET]->(d:Dataset)
WHERE (c.name = $concept OR $concept IN c.synonyms) AND v.status = "verified"
OPTIONAL MATCH (v)-[:DRAWN_AS]->(cs:ChartStyle)
RETURN v.id, v.display_name, v.definition_for_students, v.unit_target,
       d.id, d.doi, cs.id
"""))
    st.append(box("example", [
        "Adding a sixth variable later (e.g. land surface temperature) means: the curator adds the "
        "dataset, the variable with its recipe, its concepts and its chart style. <b>No new code</b> "
        "is needed in the investigation, because the investigation reads everything from the graph."],
        title="Why this is powerful"))

    st.append(H2("8.6 The curator agent"))
    st.append(P("The curator is an LLM with tools. It reads the schema, looks at what is missing, "
                "and fills it, one checked fact at a time. It runs <b>offline, before the demo</b>, "
                "and saves a <b>build log</b> (every tool call and answer), which also makes a "
                "great 10-second clip for the video: “watch the AI build the graph”."))
    st.append(bullets([
        "<b>Read</b> the schema and the list of target nodes (section 8.1).",
        "<b>Look</b>: call <font name='Mono'>find_node</font> to see what already exists.",
        "<b>Gather</b>: call a source tool (NASA CMR, a file header, a paper abstract).",
        "<b>Write</b>: call an add_ tool. The tool checks the fact against the source and the "
        "schema; if anything is wrong it refuses and says why, and the agent tries again.",
        "<b>Repeat</b> until nothing is missing, then run <font name='Mono'>validate_graph</font>.",
    ], numbered=True))
    st.append(table([
        ["Tool (in curator_tools.py)", "What it checks before writing"],
        ["find_node(label, text)", "Read-only: returns existing nodes with similar names (to avoid "
         "duplicates). Must be called before every add_."],
        ["add_dataset(short_name, version)", "Looks it up in NASA CMR itself and copies the "
         "official title, concept id, DOI and dates. The agent only gives the name."],
        ["add_variable(dataset, name_in_file)", "Opens our real file and reads unit, scale factor, "
         "fill value and group. The agent writes only the student definition and the kind."],
        ["add_concept(name, synonyms)", "Name not already used (checked with find_node)."],
        ["link_variable_to_concept(var, concept, reason)", "Both exist; a reason is required."],
        ["add_region(name, bbox, parent)", "Box is valid and inside our data; counts the land "
         "cells from series.nc."],
        ["add_paper(doi)", "Fetches title, year and abstract from the DOI; a team member must be "
         "listed in read_by."],
        ["add_influence(var_a, var_b, sign, paper_id, quote)", "The paper exists and the quote "
         "really appears in its abstract (string match). Otherwise refused."],
        ["add_method / add_chart_style / add_hypothesis_pattern", "Only from the list in "
         "schema.yaml (we write these few by hand, the agent connects them)."],
        ["validate_graph()", "Runs all the checks of section 8.7 and returns a list of problems."],
    ], [2.6, 4.4], font=8.3))
    st.append(box("rule", [
        "<b>No raw Cypher for the curator.</b> It can only use the tools above.",
        "<b>The LLM never types a number from memory</b> (units, dates, scale factors). Those "
        "come from CMR or the file, through the tool.",
        "Every write records <b>source</b> and <b>created_by = curator</b>."],
        title="Curator rules"))

    st.append(H2("8.7 Review, backup and the seed.yaml fallback"))
    st.append(table([
        ["Check (validate_graph, automatic)", "Why"],
        ["Every Variable has a Dataset, a complete recipe, a ChartStyle and at least one Concept",
         "Otherwise the investigation cannot use it."],
        ["Every INFLUENCES edge has a Paper and a quote", "No unsupported causal claims."],
        ["No two nodes with the same name or synonym", "No duplicates, so queries never miss data."],
        ["No node or edge type outside the schema", "No schema drift."],
        ["Recipes match section 5.2 (units, names)", "Catches hallucinated units."],
    ], [3.6, 3.4]))
    st.append(bullets([
        "After validation passes, <b>two of us spend 30 minutes</b> in Neo4j Browser looking at "
        "every Variable, every INFLUENCES edge and every Paper.",
        "Then: <font name='Mono'>neo4j-admin dump</font> + <font name='Mono'>export.py</font> "
        "(graph.json, committed).",
        "<b>Fallback:</b> if the curator is not ready by Saturday night, load "
        "<font name='Mono'>seed.yaml</font> (same schema) in 5 minutes and keep going. The "
        "investigator does not care who built the graph.",
    ]))
    st.append(box("owner", ["The AI engineer owns schema.yaml, the curator tools and agent, "
                            "validate_graph and export; a teammate writes seed.yaml in parallel."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 9 agent
    st.append(H1("9. The AI investigator (hackathon version)"))
    st.append(P("Instead of six agents, we build <b>one investigator agent</b> (an LLM that can "
                "call tools), and it is <b>guided by the graph</b>: it does not decide from memory "
                "which variables, methods or charts to use; it reads them from the graph. In the "
                "interface we still show the investigation as the same steps as the full system "
                "(Understand → Plan → Analyse → Check → Explain), so judges see the design, and "
                "the code can later be split into separate agents."))
    st.append(H2("9.1 The tools the agent can call"))
    st.append(table([
        ["Tool (Python function)", "What it returns"],
        ["find_concepts(question_words)", "Concepts in the graph matching the words or synonyms "
         "(empty = out of scope)"],
        ["plan_from_graph(concepts, region, period)", "Contract-1 spec: variables + definitions, "
         "datasets, recipes, ordered methods, chart styles — all read from the graph"],
        ["find_variables(concepts)", "Variables linked to the concepts in the graph, with "
         "definitions and datasets"],
        ["get_trend(variable, region, period)", "Contract-2 JSON for the regional trend + cell "
         "counts (from the cache, or computed on demand by the engine)"],
        ["get_opposite_trends(variable, region)", "Sub-regions with opposite significant directions"],
        ["get_clusters(region)", "Cluster signatures, sizes, and their sub-regions"],
        ["get_mechanisms(variable)", "INFLUENCES paths from the graph, with their paper sources"],
        ["propose_hypotheses(findings)", "Candidate hypotheses from HypothesisPattern matches "
         "(co-trends + literature paths)"],
        ["record_hypothesis(text, based_on)", "Saves a hypothesis node labelled “unverified”"],
        ["get_chart(variable, kind)", "A chart spec (type, colours, labels) from ChartStyle; the "
         "app draws it"],
    ], [2.5, 4.5]))
    st.append(H2("9.2 The rules in the system prompt"))
    st.append(bullets([
        "Only use numbers returned by tools. Never compute or guess a statistic.",
        "Always give the slope with its unit, the period, the p- or q-value and whether it is "
        "significant.",
        "Label every explanation as <b>observed</b> (from our tools), <b>literature</b> (from a graph "
        "paper), or <b>hypothesis</b> (your idea, not proven).",
        "Say clearly when the data cannot answer “why”. Correlation is not causation.",
        "Write for a curious high-school student: short sentences, define every technical word.",
        "Follow the plan the graph gives. If the graph has no path for the question (unknown "
        "concept, region or variable), say “our data can't answer this” and suggest a question it "
        "can answer.",
    ]))
    st.append(H2("9.3 Safety net for the demo"))
    st.append(bullets([
        "After each tool-using answer, a small check verifies that every number in the text appears in "
        "the tool outputs (simple string match). If not, the answer is regenerated.",
        "The two demo investigations are <b>cached</b> (saved as JSON) and can be replayed step by "
        "step even with no internet or no API key — useful when recording the video.",
        "The API key lives in a local <font name='Mono'>.env</font> file that is listed in "
        "<font name='Mono'>.gitignore</font>: it must never reach the public repository.",
        "Model: any strong tool-calling LLM the team has access to (for example Claude Sonnet 5.5, "
        "<font name='Mono'>claude-sonnet-5-5</font>). The same model can run the curator.",
    ]))
    st.append(H2("9.4 How the graph guides one investigation"))
    st.append(P("This is the heart of the system. Each step of the investigation reads (or "
                "writes) a specific path in the graph:"))
    st.append(diagram_guided())
    st.append(caption("Figure 4. Left: what the investigator does. Right: the graph path it "
                      "follows at that step. Steps 3, 4 and 6 are plain code."))
    st.append(box("example", [
        "<b>Question:</b> “Is Tunisia getting drier?”",
        "<b>1 · Understand:</b> “drier” matches the synonyms of the concepts <i>drought</i> and "
        "<i>water availability</i>; “Tunisia” matches a Region node.",
        "<b>2 · Plan:</b> the graph gives precipitation, soil moisture, evapotranspiration and NDVI, "
        "their datasets and recipes, the 5 methods in order, and the chart styles. The app shows "
        "this plan with each variable's definition.",
        "<b>3 · Analyse:</b> the engine runs on Tunisia's cells for 2001–2024 → one Contract-2 "
        "result per variable.",
        "<b>4 · Record:</b> code writes the Findings (e.g. soil moisture ↓, significant) and "
        "a CO_OCCURS_WITH edge if two variables changed in the same cells.",
        "<b>5 · Why?:</b> the graph has precipitation →INFLUENCES→ soil moisture from a paper, so "
        "the pattern proposes a <i>hypothesis</i>: “less rain may explain drier soil here”, "
        "status unverified.",
        "<b>6 · Check:</b> every number in the text is found in the tool outputs.",
        "<b>7 · Explain:</b> maps and time series drawn from the chart styles; the answer says "
        "what is observed, what the literature says, and what is only a hypothesis.",
    ], title="Worked example (no real numbers yet)"))
    st.append(box("owner", ["The AI engineer owns tools.py, agent.py, the prompt and the cache; the "
                            "ML engineer owns the on-demand engine call behind get_trend."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 10 app
    st.append(H1("10. The app (Streamlit, local)"))
    st.append(P("Streamlit lets Python developers build a web app quickly. We run it on our own "
                "laptop with <font name='Mono'>python run.py app</font> (it opens in the browser "
                "at localhost). Nothing is deployed; judges see it through the video, the "
                "screenshots and the GitHub repository."))
    st.append(table([
        ["Page", "What is on it"],
        ["Home", "What EarthSleuth is (3 lines), “Ask a question” box, optional sub-region and "
         "period pickers, buttons for the two demo investigations."],
        ["Ask", "The agent at work: the plan read from the graph (variables with definitions, "
         "datasets, region, period, methods), each step lighting up, then the answer with evidence "
         "labels."],
        ["Trend map", "Pick a variable → map of slope per decade, significant cells marked; "
         "opposite-trend view; click a cell → its time series."],
        ["Time series", "Monthly values, anomalies, Theil–Sen line, confidence band, p and q, "
         "regional vs one cell."],
        ["Radar", "Ranked variables, cluster map with signature names."],
        ["Graph", "Interactive graph (pyvis): click a finding to see its datasets, variables, "
         "concepts, papers and hypotheses; a tab shows the curator's build log."],
        ["Report", "Summary of the investigation with methods, numbers, data sources and "
         "provenance; downloadable as Markdown/PDF."],
    ], [1.2, 5.8]))
    st.append(bullets([
        "Maps: Plotly (<font name='Mono'>scatter_map</font> with one square marker per cell) inside "
        "<font name='Mono'>st.plotly_chart(..., on_select=\"rerun\")</font> so clicking a cell opens "
        "its series. Colours and labels come from the ChartStyle nodes.",
        "Colours: red = increase, blue = decrease, grey = not significant (also explained with words "
        "and symbols ↑ ↓ for colour-blind users).",
        "Every variable name shows a “?” tooltip with its one-sentence definition (from the graph).",
        "No NASA logos, flags or mission patches anywhere in the app or slides (submission rule).",
        "A footer says where AI was used (building the graph, the agent's explanations, and AI help "
        "in coding).",
    ]))
    st.append(box("owner", ["Integration / product engineers own the app."]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 11 demo
    st.append(H1("11. Demo and submission"))
    st.append(P("Because we do not deploy, <b>the video (or slides) is the demo</b>. Judges will "
                "not run our code; they will watch, read the summary and maybe open the repo. "
                "Record a real investigation once everything works."))
    st.append(H2("11.1 The story we show"))
    st.append(bullets([
        "(A few seconds) The curator agent building the graph: tool calls scrolling, the graph "
        "growing in Neo4j Browser.",
        "A student asks: <i>“Is it getting hotter and drier around the Mediterranean?”</i>",
        "EarthSleuth plans by walking the graph: “hotter” and “drier” → 4–5 NASA variables, "
        "each explained, with their datasets.",
        "It shows the trend maps: where each variable changes, how much, and where it is significant.",
        "It points out opposite trends that the regional average would hide.",
        "The Radar shows the cluster with the strongest combined signal.",
        "The graph shows how each finding connects to datasets, concepts and literature.",
        "The explanation separates observed facts, literature and unproven hypotheses.",
    ], numbered=True))
    st.append(H2("11.2 The 7-slide deck (the title slide counts!)"))
    st.append(table([
        ["#", "Slide", "Content"],
        ["1", "Title + problem", "EarthSleuth, one-line pitch; “thousands of variables, opposite "
         "trends, is it significant?”"],
        ["2", "Our approach", "Discover · Connect · Investigate; the golden rules in one "
         "line each"],
        ["3", "How it works", "The four phases + NASA datasets used; “a graph built by AI, "
         "checked by tools”"],
        ["4", "Ask → plan", "Screenshot: question, the plan read from the graph, variables with "
         "definitions, datasets"],
        ["5", "Results", "Trend map + opposite-trend map + a time series with slope, CI, p/q"],
        ["6", "Evidence", "Graph screenshot + explanation with observed / literature / hypothesis "
         "labels"],
        ["7", "Impact + next steps", "Who benefits, validation vs Giovanni, future work, GitHub "
         "link"],
    ], [0.3, 1.6, 5.1]))
    st.append(H2("11.3 Draft project summary (about 150 words)"))
    st.append(box("example", [
        "EarthSleuth turns students and curious citizens into Earth-science data detectives. "
        "Instead of asking users to know dataset names, it lets them ask a question in plain "
        "language, such as “Is it getting hotter and drier around the Mediterranean?”. An AI "
        "curator agent first builds a knowledge graph from NASA's catalogue and data files: "
        "datasets, variables, how to read them, which methods apply and what the literature "
        "says, every fact checked by tools. An AI investigator then follows this graph to plan the "
        "investigation with NASA variables (MERRA-2 air temperature, GPM IMERG precipitation, "
        "GLDAS soil moisture and evapotranspiration, MODIS NDVI) for 2001–2024. Trends are measured "
        "with robust Theil–Sen slopes after removing seasons, tested with an autocorrelation-"
        "corrected Mann–Kendall test and corrected for multiple testing. EarthSleuth highlights "
        "opposite trends and shared warming–drying signals, and its explanations separate observed "
        "evidence, literature and unproven hypotheses."], title="Summary draft — edit freely"))
    st.append(H2("11.4 Submission checklist"))
    st.append(table([
        ["□", "Item"],
        ["□", "Public GitHub repository: README (what, how to run with run.py, screenshots), no "
         "secrets (.env not committed), graph.json and small result files included"],
        ["□", "Repository link opens in a private/incognito window (no login, no permission)"],
        ["□", "Demo: 7 slides max (title included) OR a video of 30 seconds max, in English, "
         "recorded from the real local app"],
        ["□", "Demo uploaded to a public host (Google Drive / GitHub / YouTube) and tested logged-out"],
        ["□", "Summary 50–200 words; project details (what, how, benefits, tools, languages)"],
        ["□", "NASA data section: links to M2TMNXSLV, GPM_3IMERGM, GLDAS_NOAH025_M, MOD13C2 pages"],
        ["□", "Other resources listed: libraries, code, images, papers"],
        ["□", "AI use declared (form + note in the app/slides): graph building, explanations, coding"],
        ["□", "No NASA logos, flags or mission insignia in generated content"],
        ["□", "No names, voices or faces of anyone under 18"],
        ["□", "“Submit for Judging” clicked before Sunday 23:59 local time (aim for 22:00)"],
    ], [0.35, 6.65]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 12 team + timeline
    st.append(H1("12. Who does what, and when"))
    st.append(H2("12.1 Roles"))
    st.append(table([
        ["Role", "Owns in the hackathon build"],
        ["AI engineer", "schema.yaml (Contract 0); curator tools + curator agent + validate_graph "
         "+ export; investigator tools, prompt, number check, cached demos; Ask and Graph pages "
         "together with the app owner."],
        ["ML engineer", "stats.py (+ tests on fake data), run_all.py, the on-demand engine call, "
         "radar.py, validation against Giovanni; checks preprocessing units."],
        ["Integration / product engineers", "Earthdata accounts, downloads, preprocess.py, "
         "series.nc; seed.yaml backup (same schema); Streamlit app, maps, charts; run.py and "
         "README; video, slides, summary, submission form."],
    ], [1.6, 5.4]))
    st.append(H2("12.2 Timeline (Saturday → Sunday)"))
    st.append(table([
        ["When", "Goal", "Done means"],
        ["Saturday, first 2 hours", "Kick-off: read both documents; agree on region, variables, "
         "grid, <b>the graph schema (Contract 0)</b> and Contracts 1–2. Create accounts, approve "
         "GES DISC, create the repo, install Neo4j. Start downloads.",
         "Contracts and schema.yaml in the repo; all four downloads running."],
        ["Saturday afternoon → evening", "Preprocessing per dataset; stats engine + tests on "
         "fake data; curator tools (CMR lookup, file header reader); seed.yaml typed in parallel; "
         "Streamlit skeleton on fake data; investigator tools as stubs.",
         "App opens with fake maps; stats tests pass; first curator tools write to Neo4j."],
        ["Saturday night checkpoint", "Real trends for at least 3 variables; first full curator "
         "run.", "Map page shows real data; graph passes validate_graph <b>or</b> seed.yaml is "
         "loaded."],
        ["Sunday morning", "All variables; Radar-lite; on-demand engine; investigator guided by "
         "the graph, wired to real tools; regional averages checked against Giovanni; team "
         "review of the graph + dump.", "One full investigation works end to end."],
        ["Sunday 14:00", "<b>Feature freeze.</b> Only fixes from now on.", "—"],
        ["Sunday 14:00 → 19:00", "Cache the 2 demos; record the video; screenshots; README; "
         "slides; summary; data links; check the repo logged-out.",
         "Everything in the checklist ticked."],
        ["Sunday 19:00 → 22:00", "Rehearse, polish, <b>submit by 22:00</b>.",
         "Submission confirmed; 2-hour safety margin."],
    ], [1.5, 3.7, 1.8]))
    st.append(PageBreak())

    # -------------------------------------------------------------- 13 risks
    st.append(H1("13. Risks and backup plans"))
    st.append(table([
        ["Risk", "Backup plan"],
        ["Downloads are slow or the disk fills up", "One file at a time, shrink to 1° "
         "immediately, delete raw files; if still slow, shorten to 2003–2024 or drop NDVI."],
        ["HDF4 (MODIS) files are hard to read", "Time-box to 2 hours, then drop NDVI and keep 4 "
         "variables."],
        ["Earthdata download errors (401/403)", "Check the GES DISC app approval in the Earthdata "
         "profile and the ~/.netrc file."],
        ["Statistics bug", "Tests on fake data with known slopes; compare regional curves with Giovanni."],
        ["The curator agent is late or buggy", "Load seed.yaml (same schema) and continue; the "
         "investigator does not care who built the graph. Show the curator's partial build log in "
         "the video."],
        ["The curator writes wrong facts", "Checking tools refuse most errors; validate_graph + "
         "30-minute human review; only verified nodes are used."],
        ["A bad agent run breaks the graph", "Restore the last neo4j-admin dump (made after every "
         "good build)."],
        ["Neo4j not running on a teammate's laptop", "The app reads graph.json with networkx."],
        ["LLM API down, slow or out of credits", "Cached demo investigations; the maps and charts "
         "work without the LLM."],
        ["API key pushed to GitHub by mistake", ".env in .gitignore from the first commit; if it "
         "happens, revoke the key immediately."],
        ["Running out of time", "Priority order: (1) stats + maps on real data, (2) a graph "
         "(curator or seed), (3) investigator guided by the graph, (4) Radar clusters. The video, "
         "slides and submission time after 14:00 is protected. A working core beats a broken "
         "everything."],
    ], [2.3, 4.7]))

    # -------------------------------------------------------------- 14 future
    st.append(H1("14. Future work: the road to the full system"))
    st.append(P("Everything below is described in Document 1. We mention it in the presentation as "
                "our roadmap, so judges see that the hackathon build is the first working piece of "
                "a bigger, coherent design."))
    st.append(H2("14.1 Data"))
    st.append(bullets([
        "<b>Real-time retrieval</b>: the user chooses <b>any region, any variables and any "
        "period</b>, and the system fetches exactly those data from NASA (OPeNDAP / Harmony "
        "subsetting), with a cache so repeated questions are instant. The graph's recipes already "
        "contain what this needs (dataset ids, variable names, units).",
        "More variables: MODIS land surface temperature, AIRS temperature and humidity profiles "
        "(trends at different heights of the atmosphere), OMI ozone and NO<sub>2</sub> above cities, GRACE "
        "groundwater, ocean variables.",
        "Finer grids (0.25° and below), daily data, conservative regridding (xESMF).",
        "Proper storage: Zarr on S3/MinIO, PostGIS for regions and per-cell results.",
        "Comparison with ground stations through CUAHSI tools.",
    ]))
    st.append(H2("14.2 Statistics"))
    st.append(bullets([
        "Seasonal Mann–Kendall option, block-bootstrap confidence intervals that respect "
        "autocorrelation, field-significance tests for whole maps.",
        "“Years needed” estimate on every non-significant trend (if not done as a stretch "
        "goal).",
        "Non-linear trends and change points (e.g. a drought that starts in 2015).",
    ]))
    st.append(H2("14.3 Earth Signal Radar"))
    st.append(bullets([
        "Scanning dozens of variables automatically, with an interest score (significant area, "
        "signal-to-noise, spatial coherence).",
        "HDBSCAN clustering, change-point detection (ruptures), Isolation Forest anomalies.",
        "Spatiotemporal Graph Neural Networks on a geographic graph of cells (PyTorch Geometric).",
    ]))
    st.append(H2("14.4 Knowledge graph and AI"))
    st.append(bullets([
        "The curator agent runs <b>continuously</b>: it harvests all relevant NASA CMR "
        "collections, matches variables to CF Standard Names and keeps the graph up to date when "
        "new dataset versions appear.",
        "Literature GraphRAG at scale: many papers ingested with embeddings; mechanisms extracted "
        "with their quotes and checked in a <b>review screen</b> by a human before becoming "
        "<i>literature</i> edges.",
        "The full team of six agents (Knowledge Discovery, Dataset Discovery, Data Engineer, "
        "Statistical Scientist, Auditor, Explainer) orchestrated with LangGraph; the curator and "
        "investigator of the hackathon split into them.",
        "Hypothesis testing: lagged correlations and spatial overlap checks run automatically and "
        "recorded as new evidence.",
    ]))
    st.append(H2("14.5 Product"))
    st.append(bullets([
        "A hosted public web app (React + MapLibre) instead of a local Streamlit app.",
        "Guided question mode for classrooms, lesson plans for teachers.",
        "Shareable investigations and downloadable reports with full provenance.",
        "Multi-language support (e.g. Arabic and French alongside English).",
    ]))
    st.append(PageBreak())

    glossary_section(st, 15, EXTRA_GLOSSARY)
    doc.build_story(st)


if __name__ == "__main__":
    build(sys.argv[1])
