"""PDF 1 - the complete EarthSleuth system (full vision)."""
import sys

from common import *  # noqa: F401,F403
from shared import (challenge_section, diagram_stats_pipeline, glossary_section,
                    problem_section)


# ------------------------------------------------------------------ diagrams
def diagram_architecture():
    W, H = 495, 432
    g = [
        dict(x=0, y=282, w=495, h=98, title="5 · AI AGENT LAYER (LangGraph)", fill=LILAC,
             stroke=PURPLE, tc=PURPLE),
        dict(x=0, y=160, w=242, h=112, title="2 · EARTH SYSTEM KNOWLEDGE GRAPH (Neo4j)",
             fill=CREAM, stroke=ORANGE, tc=ORANGE),
        dict(x=253, y=160, w=242, h=112, title="3 + 4 · ANALYSIS ENGINES (Python)",
             fill=TEAL_L, stroke=TEAL, tc=TEAL),
        dict(x=0, y=58, w=495, h=92, title="1 · SCIENTIFIC DATA PLATFORM", fill=SKY,
             stroke=BLUE, tc=BLUE),
    ]
    b = {
        "ui": bx(0, 390, 495, 40, "<b>6 · THE APP</b> (React + MapLibre)<br/>Ask · Plan "
                 "· Trend maps · Time series · Signal Radar · Graph explorer "
                 "· Report", fill=NAVY, stroke=NAVY, tc=colors.white),
        "orch": bx(150, 338, 195, 26, "<b>Scientific Orchestrator</b>", fill=PURPLE,
                   stroke=PURPLE, tc=colors.white),
        "kg_a": bx(8, 204, 110, 50, "<b>Layer A</b><br/>Scientific knowledge<br/>(stable facts)",
                   stroke=ORANGE),
        "kg_b": bx(124, 204, 110, 50, "<b>Layer B</b><br/>Observational evidence<br/>(our findings)",
                   stroke=ORANGE),
        "rag": bx(8, 167, 226, 30, "<b>GraphRAG</b>: vector search + graph traversal", stroke=ORANGE),
        "stats": bx(261, 204, 110, 50, "<b>Statistics engine</b><br/>trend, p-value, CI, FDR",
                    stroke=TEAL),
        "radar": bx(377, 204, 110, 50, "<b>Earth Signal Radar</b><br/>clusters, anomalies, GNN",
                    stroke=TEAL),
        "res": bx(261, 167, 226, 30, "Typed results (JSON) + full provenance", stroke=TEAL),
        "ext": bx(0, 0, 250, 40, "<b>NASA Earthdata archives</b><br/>MODIS · GPM · AIRS "
                  "· OMI · MERRA-2 · GLDAS · GRACE", fill=LGREY, stroke=GREY),
        "lit": bx(260, 0, 115, 40, "<b>Literature</b><br/>papers, NASA reports", fill=LGREY,
                  stroke=GREY),
        "reg": bx(385, 0, 110, 40, "<b>Region shapes</b><br/>countries, biomes, basins",
                  fill=LGREY, stroke=GREY),
    }
    names = ["Knowledge<br/>Discovery", "Dataset<br/>Discovery", "Data<br/>Engineer",
             "Statistical<br/>Scientist", "Scientific<br/>Auditor", "Scientific<br/>Explainer"]
    for i, n in enumerate(names):
        b["ag%d" % i] = bx(6 + i * 81.5, 290, 76, 38, "<b>%d</b> %s" % (i + 1, n), fs=7.3,
                           stroke=PURPLE)
    data_names = ["<b>Discovery</b><br/>NASA CMR,<br/>CF names",
                  "<b>Acquisition</b><br/>earthaccess,<br/>OPeNDAP, Harmony",
                  "<b>Harmonise + QC</b><br/>regrid, units,<br/>masks, gaps",
                  "<b>Storage</b><br/>Zarr / NetCDF /<br/>Parquet on S3",
                  "<b>PostGIS</b><br/>regions +<br/>spatial results"]
    for i, n in enumerate(data_names):
        b["d%d" % i] = bx(6 + i * 97.5, 64, 90, 64, n, fs=7.3, stroke=BLUE)
    arrows = [
        dict(pts=[("ext", "top"), (125, 58)], color=GREY),
        dict(pts=[("lit", "top"), (317, 58)], color=GREY),
        dict(pts=[("reg", "top"), (440, 58)], color=GREY),
        dict(pts=[(370, 150), (370, 160)], color=TEAL),
        dict(pts=[(120, 150), (120, 160)], color=ORANGE),
        dict(pts=[("orch", "bottom"), (247, 328)], color=PURPLE, both=True),
        dict(pts=[(247, 380), ("ui", "bottom")], color=NAVY, both=True),
        dict(pts=[(121, 272), (121, 282)], color=ORANGE, both=True),
        dict(pts=[(374, 272), (374, 282)], color=TEAL, both=True),
        dict(pts=[("res", "left"), ("kg_b", "right", 0.1)], color=TEAL, label="findings"),
    ]
    return centered(Diagram(W, H, b, arrows, groups=g))


def diagram_kg_example():
    W, H = 495, 245
    v = dict(fill=TEAL_L, stroke=TEAL)
    m = dict(fill=SKY, stroke=BLUE)
    b = {
        "terra": bx(0, 205, 96, 30, "<b>Terra</b><br/>Mission", **m),
        "modis": bx(0, 140, 96, 30, "<b>MODIS</b><br/>Instrument", **m),
        "ndvi": bx(0, 75, 96, 30, "<b>NDVI</b><br/>Variable", **v),
        "gpm": bx(200, 205, 96, 30, "<b>GPM</b><br/>Mission", **m),
        "pr": bx(200, 140, 96, 30, "<b>Precipitation</b><br/>Variable", **v),
        "con": bx(200, 75, 96, 30, "<b>Water availability</b><br/>Concept", fill=CREAM, stroke=ORANGE),
        "gldas": bx(399, 205, 96, 30, "<b>GLDAS</b><br/>Model", **m),
        "sm": bx(399, 140, 96, 30, "<b>Soil moisture</b><br/>Variable", **v),
        "et": bx(399, 75, 96, 30, "<b>Evapotranspiration</b><br/>Variable", **v),
        "find": bx(0, 5, 180, 34, "<b>Finding #001</b> (evidence)<br/>NDVI ↓, p=0.003, "
                   "region X, 2001–2024", fill=CREAM, stroke=ORANGE),
        "hyp": bx(300, 5, 195, 34, "<b>Hypothesis H1</b> (unverified)<br/>less rain → less "
                  "green vegetation", fill=LILAC, stroke=PURPLE, dashed=True),
    }
    a = [
        dict(pts=[("terra", "bottom"), ("modis", "top")], label="CARRIES"),
        dict(pts=[("modis", "bottom"), ("ndvi", "top")], label="MEASURES"),
        dict(pts=[("gpm", "bottom"), ("pr", "top")], label="MEASURES"),
        dict(pts=[("gldas", "bottom"), ("sm", "top")], label="PROVIDES"),
        dict(pts=[("pr", "right", 0.7), ("sm", "left", 0.7)], label="INFLUENCES (literature)",
             color=TEAL),
        dict(pts=[("sm", "bottom"), ("et", "top")], label="LINKED_TO (literature)", color=TEAL),
        dict(pts=[("ndvi", "right"), ("con", "left")], label="INDICATOR_OF", color=ORANGE),
        dict(pts=[("pr", "bottom"), ("con", "top")], label="INDICATOR_OF", color=ORANGE),
        dict(pts=[("find", "top", 0.25), ("ndvi", "bottom")], label="ABOUT", color=ORANGE),
        dict(pts=[("find", "right"), ("hyp", "left")], label="EXPLAINED_BY?", color=PURPLE,
             dashed=True),
        dict(pts=[(340, 39), (340, 147.5), ("pr", "right", 0.25)], label="POINTS_TO",
             color=PURPLE, dashed=True),
    ]
    return centered(Diagram(W, H, b, a))


def diagram_two_layers():
    W, H = 495, 300
    g = [dict(x=0, y=212, w=495, h=86, title="LAYER A — SCIENTIFIC KNOWLEDGE (stable, from "
              "literature)", fill=SKY, stroke=BLUE, tc=BLUE),
         dict(x=0, y=0, w=495, h=142, title="LAYER B — OBSERVATIONAL EVIDENCE (created by our "
              "investigations)", fill=CREAM, stroke=ORANGE, tc=ORANGE)]
    b = {
        "p": bx(12, 230, 100, 32, "Precipitation", stroke=BLUE),
        "s": bx(135, 230, 100, 32, "Soil moisture", stroke=BLUE),
        "e": bx(258, 230, 100, 32, "Evapotranspiration", stroke=BLUE),
        "v": bx(381, 230, 100, 32, "Vegetation health", stroke=BLUE),
        "run": bx(330, 160, 155, 32, "<b>Analysis run #00421</b><br/>code v1.3, 2026-11-14",
                  fill=colors.white, stroke=GREY),
        "fa": bx(12, 70, 150, 44, "<b>Finding A</b> — South<br/>rainfall ↓ "
                 "−12 mm/decade<br/>p = 0.004, q = 0.03", stroke=ORANGE),
        "fb": bx(175, 70, 150, 44, "<b>Finding B</b> — North<br/>soil moisture ↓<br/>"
                 "p = 0.01, q = 0.06", stroke=ORANGE),
        "h": bx(345, 54, 140, 64, "<b>Hypothesis H7</b><br/>(unverified)<br/>rain decline → "
                "drier soils<br/>status: to test", fill=LILAC, stroke=PURPLE, dashed=True),
    }
    a = [
        dict(pts=[("p", "right"), ("s", "left")], color=BLUE),
        dict(pts=[("s", "right"), ("e", "left")], color=BLUE),
        dict(pts=[("e", "right"), ("v", "left")], color=BLUE),
        dict(pts=[(40, 114), (40, 230)], color=ORANGE, dashed=True, label="ABOUT"),
        dict(pts=[(200, 114), (200, 230)], color=ORANGE, dashed=True, label="ABOUT"),
        dict(pts=[("run", "bottom", 0.1), (345, 150), (90, 150), (90, 114)], color=GREY,
             label="GENERATES"),
        dict(pts=[("run", "left"), (260, 176), (260, 114)], color=GREY),
        dict(pts=[("fb", "right"), ("h", "left", 0.55)], color=PURPLE),
        dict(pts=[(90, 70), (90, 22), (415, 22), (415, 54)], color=PURPLE, label="SUGGESTS"),
    ]
    return centered(Diagram(W, H, b, a, groups=g))


def diagram_agents():
    W, H = 495, 238
    b = {
        "q": bx(150, 205, 195, 30, "<b>User question</b> (plain language)", fill=CREAM,
                stroke=ORANGE),
        "o": bx(130, 140, 235, 40, "<b>Scientific Orchestrator</b><br/>plans · routes · "
             "keeps state · retries", fill=PURPLE, stroke=PURPLE, tc=colors.white),
        "out": bx(110, 0, 275, 32, "<b>Evidence graph + investigation report</b>", fill=NAVY,
                  stroke=NAVY, tc=colors.white),
    }
    names = [("Knowledge<br/>Discovery", "GraphRAG"), ("Dataset<br/>Discovery", "NASA CMR"),
             ("Data<br/>Engineer", "download, QC"), ("Statistical<br/>Scientist", "Python stats"),
             ("Scientific<br/>Auditor", "checks"), ("Scientific<br/>Explainer", "hypotheses")]
    for i, (n, t) in enumerate(names):
        b["a%d" % i] = bx(4 + i * 82, 62, 76, 54, "<b>%d · %s</b><br/><font size=6.5 "
                          "color='#5B6573'>%s</font>" % (i + 1, n, t), fs=7.3, stroke=PURPLE)
    a = [dict(pts=[("q", "bottom"), ("o", "top")], color=ORANGE)]
    for i in range(6):
        cx = 4 + i * 82 + 38
        ox = 140 + i * 43
        a.append(dict(pts=[(ox, 140), (cx, 116)], color=PURPLE, both=True))
    a.append(dict(pts=[("a4", "bottom"), (340, 32)], color=NAVY))
    a.append(dict(pts=[("a5", "bottom"), (380, 32)], color=NAVY))
    return centered(Diagram(W, H, b, a))


# ------------------------------------------------------------------ content
def build(path):
    doc = Doc(path, "The complete system\nAn agentic knowledge graph for Earth science trends",
              "From satellite observations to tested, explained scientific findings.\n"
              "Document 1 of 2 — the full vision (everything we would build).",
              "Document 1 · Full system vision")
    st = []
    st.append(NextPageTemplate("normal"))
    st.append(Spacer(1, 300))
    st.append(P("<b>What this document is.</b> This is the complete description of the system we "
                "want to build, with all its parts, as if we had unlimited time. It explains the "
                "science problem, the NASA challenge, our idea, and the architecture piece by piece. "
                "A second document (Document 2) describes the smaller version we will actually "
                "build during the hackathon weekend and lists what is left for later."))
    st.append(P("<b>How to read it.</b> Sections 1–2 explain the problem for everyone. Section 3 "
                "is the idea in one place. Sections 4–12 explain each part of the system. "
                "Section 13 walks through one complete investigation. Sections 14–16 cover tools, "
                "team roles and judging. The glossary at the end explains every technical word."))
    st.append(P("Coloured boxes help you skim: <font color='#E58A2B'><b>orange</b></font> = simple "
                "explanation, <font color='#C8423B'><b>red</b></font> = rule we must never break, "
                "<font color='#138A7E'><b>green</b></font> = example, "
                "<font color='#1F5FA8'><b>blue</b></font> = good to know, "
                "<font color='#6A4FA0'><b>purple</b></font> = who owns it."))
    st.append(PageBreak())
    st.append(P("Contents", "H1x"))
    st.append(toc())
    st.append(PageBreak())

    problem_section(st)
    st.append(PageBreak())
    challenge_section(st)
    st.append(PageBreak())

    # ---------------------------------------------------------------- 3 idea
    st.append(H1("3. Our idea: from a chart tool to a science detective"))
    st.append(P("Most tools answer one narrow question: <i>“Is temperature increasing in this "
                "region?”</i> You choose the variable, you choose the place, you get a chart."))
    st.append(P("EarthSleuth is built to answer the questions a real scientist asks next: <i>"
                "“Temperature went up here. What else changed? Did rainfall change too? Did the "
                "soil dry out? Is the vegetation suffering? Where do these changes go in opposite "
                "directions? Which known Earth processes could explain this? And how sure are we?”"
                "</i>"))
    st.append(box("kid", [
        "A normal tool is a <b>thermometer</b>: it tells you one number. EarthSleuth is a "
        "<b>detective</b>: it notices that something is strange, collects clues from many places, "
        "checks each clue carefully, writes everything in a notebook (the graph), and finally tells "
        "you which explanations are possible and which ones are proven."]))
    st.append(H2("3.1 Normal tool vs. EarthSleuth"))
    st.append(table([
        ["", "Typical trend tool", "EarthSleuth"],
        ["Choosing variables", "You must already know the variable name.",
         "You ask in plain words; the system finds the right variables and explains them."],
        ["Where to look", "You pick one place.", "It scans a whole region cell by cell and shows "
         "where things change, including opposite directions."],
        ["Statistics", "Sometimes a trend line.", "Seasons removed, robust slope, Mann–Kendall "
         "with autocorrelation fix, confidence interval, multiple-testing correction."],
        ["Discovery", "None: it only answers what you ask.", "Earth Signal Radar finds interesting "
         "changes you did not ask about."],
        ["Explanation", "None, or a generic chatbot answer.", "Competing hypotheses linked to "
         "evidence and literature, clearly labelled as proven / supported / unverified."],
        ["Memory", "Each chart is forgotten.", "Every finding is stored in a knowledge graph with "
         "full provenance and can be reused."],
    ], [1.3, 2.2, 3.5]))
    st.append(H2("3.2 The three superpowers"))
    st.append(box("note", [
        "Find what is changing <b>without</b> knowing beforehand which variable to look at. The system "
        "scans many variables over many grid cells, tests every trend and ranks the most interesting "
        "ones. This answers the challenge's first objective directly."],
        title="Superpower 1 — DISCOVER (Earth Signal Radar)"))
    st.append(box("note", [
        "Link everything together: missions, instruments, datasets, variables, Earth processes, "
        "regions, scientific papers, our own analyses and our own findings. The graph is the "
        "memory and the brain of the system."],
        title="Superpower 2 — CONNECT (Earth System Knowledge Graph)"))
    st.append(box("note", [
        "Turn a question in plain language into a real, reproducible experiment: plan it, get the "
        "data, run the statistics, check the results, and explain them with evidence."],
        title="Superpower 3 — INVESTIGATE (Autonomous Scientific Investigator)"))
    st.append(P("The three powers feed each other: a discovered trend becomes a node in the graph; "
                "that node becomes context for the next investigation; the growing evidence lets the "
                "system notice connections that no single chart shows."))
    st.append(H2("3.3 Questions EarthSleuth can answer"))
    st.append(bullets([
        "“Is it getting drier in North Africa, and is that significant?”",
        "“Find regions where temperature is increasing while water availability is decreasing.”",
        "“Where does rainfall go up in one part of the Mediterranean and down in another?”",
        "“What is changing the most around Cairo since 2005?” (no variable given)",
        "“Show me all significant findings about water in North Africa that use satellite data.”",
        "“Which other variables behave like this soil-moisture trend?”",
        "“Why might vegetation be declining here? What would we need to check?”",
    ]))
    st.append(H2("3.4 The five golden rules of the system"))
    st.append(box("rule", [
        "<b>1. The graph holds knowledge, not raw numbers.</b> Satellite grids and time series live "
        "in scientific file storage. The graph stores what they mean and how they connect. We never "
        "put millions of pixels into Neo4j.",
        "<b>2. The AI never calculates statistics.</b> Slopes, p-values and confidence intervals "
        "always come from tested Python code. The AI only plans, calls tools and explains the "
        "numbers it receives.",
        "<b>3. An AI idea never silently becomes a fact.</b> Every relationship is labelled as "
        "<i>literature</i> (published science), <i>observed</i> (our own measured result) or "
        "<i>hypothesis</i> (an idea not yet proven).",
        "<b>4. Every finding has full provenance.</b> Dataset and version, variable, region, period, "
        "method, result, date and code version are always stored.",
        "<b>5. Machine learning finds patterns; statistics decides significance.</b> A neural network "
        "can point to an interesting area, but only a statistical test can call a trend significant."],
        title="Golden rules"))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 4 data
    st.append(H1("4. The NASA data we use"))
    st.append(P("NASA data is at the heart of the project (this is the <b>Relevance</b> criterion). "
                "Here is what exists and what each source gives us."))
    st.append(H2("4.1 Missions, instruments and models"))
    st.append(table([
        ["Source", "Type", "What it gives us", "Since", "Typical grid"],
        ["MODIS (on Terra and Aqua)", "Satellite instrument", "Land surface temperature, vegetation "
         "(NDVI, EVI), snow cover, fires, leaf area", "2000 (Terra), 2002 (Aqua)",
         "1 km – 0.05°"],
        ["GPM / IMERG", "Satellite mission + merged product", "Rain and snow (precipitation), "
         "half-hourly to monthly", "June 2000 (IMERG record)", "0.1°"],
        ["AIRS (on Aqua)", "Satellite instrument", "Air temperature and humidity at many heights, "
         "water vapour, CO<sub>2</sub>", "2002", "1°"],
        ["OMI (on Aura)", "Satellite instrument", "Ozone, nitrogen dioxide (air pollution over "
         "cities), sulphur dioxide, aerosols", "2004", "0.25°"],
        ["MERRA-2", "Reanalysis model (GMAO)", "Air temperature, wind, humidity, radiation, "
         "aerosols — complete and gap-free", "1980", "0.5° × 0.625°"],
        ["GLDAS (Noah)", "Land model", "Soil moisture (several depths), evapotranspiration, runoff, "
         "snow water", "2000 (GLDAS-2.1)", "0.25° or 1°"],
        ["GRACE / GRACE-FO", "Satellite gravity mission", "Total water stored on land "
         "(groundwater + soil + lakes)", "2002", "~1° (mascons)"],
    ], [1.5, 1.3, 2.6, 1.2, 1.1]))
    st.append(box("kid", [
        "A <b>mission</b> is the whole project (the satellite and its team). An <b>instrument</b> is "
        "a camera or sensor on the satellite. A <b>dataset</b> is a product made from the "
        "measurements. A <b>variable</b> is one measured quantity inside the dataset. Example: "
        "mission Terra → instrument MODIS → dataset MOD13C2 → variable NDVI."]))
    st.append(H2("4.2 The variables, with simple definitions"))
    st.append(table([
        ["Variable", "In simple words", "Unit", "Main source", "Why it matters"],
        ["Air temperature (2 m)", "How warm the air is at head height.", "°C or K",
         "MERRA-2, AIRS", "The classic sign of warming."],
        ["Land surface temperature", "How hot the ground itself is (it can be much hotter than the "
         "air).", "K", "MODIS", "Shows heating of cities, deserts, dried soils."],
        ["Precipitation", "Rain + snow that falls.", "mm/month", "GPM IMERG",
         "Water input; can trend opposite ways in nearby regions."],
        ["Soil moisture", "Water stored in the top layers of soil.", "kg/m² (= mm)",
         "GLDAS", "Drought indicator; plants depend on it."],
        ["Evapotranspiration", "Water leaving the land into the air (evaporation + plants).",
         "mm/day", "GLDAS, MODIS", "Links water and energy."],
        ["NDVI", "How green and alive vegetation is.", "−1 to 1", "MODIS",
         "Shows greening or browning of the land."],
        ["Total water storage", "All water on and under the land.", "cm of water", "GRACE",
         "Shows groundwater loss (e.g. irrigation)."],
        ["Ozone / NO<sub>2</sub>", "Gases in the air; NO<sub>2</sub> mostly from traffic and "
         "industry.", "Dobson units / molecules per cm²", "OMI", "Air quality above big cities."],
    ], [1.3, 2.1, 0.9, 0.95, 1.75]))
    st.append(H2("4.3 How we find and get the data"))
    st.append(bullets([
        "<b>NASA CMR (Common Metadata Repository)</b> — the search engine of all NASA Earth "
        "data. It tells us which datasets exist, their variables, time coverage, resolution and "
        "where the files (granules) are. Its search API is public.",
        "<b>CF Standard Names</b> — an official dictionary of variable names and units. We use "
        "it to recognise that “T2M” in MERRA-2 and “Tair_f_inst” in GLDAS are both "
        "<i>air_temperature</i>.",
        "<b>Earthdata Login</b> — a free NASA account needed to download most data.",
        "<b>earthaccess</b> (Python library) — logs in, searches CMR and downloads or streams files.",
        "<b>OPeNDAP and Harmony</b> — NASA services that cut out only our region and variable "
        "on the server, so we don't download the whole planet.",
        "<b>Giovanni</b> — NASA's web tool that makes maps and time series; useful to "
        "double-check our numbers.",
        "<b>CUAHSI (HydroShare / HydroClient)</b> — outside hydrology tools and station data, "
        "suggested by the challenge, useful to compare with ground measurements.",
    ]))
    st.append(H2("4.4 Data formats (what the files look like)"))
    st.append(table([
        ["Format", "What it is", "Analogy"],
        ["NetCDF / HDF5 / HDF4", "Files that store big grids with several dimensions (time, "
         "latitude, longitude, height) plus descriptions.", "A spreadsheet with many sheets stacked "
         "like a cube."],
        ["Zarr", "The same idea but cut into small chunks that can be read from the cloud quickly.",
         "The cube cut into Lego bricks; you only fetch the bricks you need."],
        ["Parquet", "A fast table format for results (one row per cell, per variable).",
         "A very efficient Excel table."],
        ["GeoJSON / shapefile", "Shapes of regions (countries, basins, deserts).",
         "Cut-out outlines you lay on the map."],
    ], [1.3, 3.2, 2.5]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 5 architecture
    st.append(H1("5. The architecture: the big picture"))
    st.append(P("The system has six layers. Data flows <b>up</b> from NASA archives to the app; "
                "questions flow <b>down</b> from the user to the engines."))
    st.append(diagram_architecture())
    st.append(caption("Figure 2. The six layers of EarthSleuth."))
    st.append(table([
        ["Layer", "Job in one sentence", "Main technology"],
        ["1 · Data platform", "Find, download, clean, align and store the NASA data.",
         "NASA CMR, earthaccess, xarray, Zarr/NetCDF, S3/MinIO, PostGIS"],
        ["2 · Knowledge graph", "Remember what everything is and how it is connected, "
         "including our own findings.", "Neo4j, Neo4j GraphRAG"],
        ["3 · Statistics engine", "Compute trends and decide if they are significant.",
         "SciPy, pymannkendall, statsmodels, xarray"],
        ["4 · Earth Signal Radar", "Discover interesting patterns automatically.",
         "scikit-learn, HDBSCAN, ruptures, PyTorch Geometric"],
        ["5 · AI agents", "Understand the question, plan the investigation, call the tools, "
         "check and explain.", "LangGraph, a strong tool-calling LLM"],
        ["6 · App", "Let people ask, watch, explore maps and graphs, read the report.",
         "React, TypeScript, MapLibre, FastAPI"],
    ], [1.5, 3.3, 2.2]))
    st.append(box("kid", [
        "Think of a library. Layer 1 is the <b>storeroom</b> full of boxes of data. Layer 2 is the "
        "<b>librarian's card catalogue</b> that knows what every box contains and which boxes are "
        "related. Layers 3 and 4 are the <b>lab</b> where measurements are tested. Layer 5 is the "
        "<b>detective</b> who decides what to test and writes the conclusion. Layer 6 is the "
        "<b>front desk</b> where visitors ask questions."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 6 data platform
    st.append(H1("6. Layer 1 — the scientific data platform"))
    st.append(P("This layer turns messy archives into clean, aligned data that the engines can "
                "trust. It runs in five steps."))
    st.append(H2("6.1 Discovery"))
    st.append(P("Given a list of wanted variables (for example “soil moisture”), we query "
                "NASA CMR to list matching datasets, versions, time coverage, spatial resolution and "
                "access links. Results are written into the knowledge graph as Dataset and Variable "
                "nodes, so the next time we already know them."))
    st.append(H2("6.2 Acquisition"))
    st.append(P("We download only what we need: our region (a bounding box or a shape), our "
                "variables, our period. We prefer server-side subsetting (OPeNDAP, Harmony) to avoid "
                "downloading global files. Every file is logged with its exact name and version."))
    st.append(H2("6.3 Harmonisation (making datasets line up)"))
    st.append(bullets([
        "<b>Same time step.</b> Daily data is averaged to monthly, so every variable has one value "
        "per month.",
        "<b>Same grid (regridding).</b> MODIS might be 0.05°, MERRA-2 0.5° × 0.625°, "
        "GLDAS 0.25°. We convert everything to a common grid (for example 0.25° or 1°) "
        "using area-weighted (conservative) averaging.",
        "<b>Same units.</b> Kelvin → °C; mm/hour → mm/month; kg/m²/s → mm/day "
        "(multiply by 86,400).",
        "<b>Same mask.</b> Land-only variables (soil moisture, NDVI) are compared only over land.",
    ]))
    st.append(box("kid", [
        "Regridding is like having one photo taken with big pixels and another with tiny pixels. "
        "To compare them square by square, we redraw both on the same checkerboard."]))
    st.append(H2("6.4 Quality control"))
    st.append(bullets([
        "Replace “fill values” (like −9999) with “missing”.",
        "Apply the dataset's own quality flags (for example MODIS cloud flags).",
        "Apply scale factors (MODIS NDVI is stored as integers × 0.0001).",
        "Reject a cell's time series if more than 20% of months are missing.",
        "Flag known breaks: a dataset version change or a new satellite can create a fake jump.",
    ]))
    st.append(H2("6.5 Storage"))
    st.append(P("Cleaned grids are stored as Zarr (or NetCDF) on object storage (S3 or MinIO). "
                "Per-cell trend results are stored as Parquet tables and in PostGIS, a database that "
                "understands geography and can answer questions like “which cells are inside "
                "Tunisia?” or “which significant cells touch the coast?”. Region shapes "
                "(countries, biomes, river basins) also live in PostGIS, with a hierarchy "
                "(Africa → North Africa → Tunisia → Northern Tunisia)."))
    st.append(box("owner", ["Integration / product engineers own this layer, with the ML engineer "
                            "defining the exact preprocessing rules."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 7 graph
    st.append(H1("7. Layer 2 — the Earth System Knowledge Graph"))
    st.append(H2("7.1 What is a graph database?"))
    st.append(P("A normal database is made of tables. A <b>graph database</b> stores <b>things</b> "
                "(called <b>nodes</b>) and <b>named links</b> between them (called <b>relationships</b> "
                "or <b>edges</b>). It is perfect when the connections are the important part."))
    st.append(box("kid", [
        "Picture a big wall with photos and red strings, like in a detective movie. Each photo is a "
        "node (“MODIS”, “Soil moisture”, “Tunisia”). Each string has a "
        "label (“MEASURES”, “INFLUENCES”, “LOCATED_IN”). Following the "
        "strings lets you answer questions no single photo can answer."]))
    st.append(diagram_kg_example())
    st.append(caption("Figure 3. A small piece of the knowledge graph. Blue = data sources, green = "
                      "variables, orange = concepts and findings, purple dashed = unproven hypothesis."))
    st.append(H2("7.2 Node types (the kinds of things we store)"))
    st.append(table([
        ["Node", "Examples", "Important properties"],
        ["Mission", "Terra, Aqua, Aura, GPM, GRACE-FO", "launch date, agency"],
        ["Instrument", "MODIS, AIRS, OMI, GMI", "type, resolution"],
        ["Model", "MERRA-2, GLDAS-Noah", "producer, version, start year"],
        ["Dataset", "MOD13C2, GPM_3IMERGM, GLDAS_NOAH025_M", "short name, version, CMR concept id, "
         "time coverage, grid"],
        ["Variable", "NDVI, precipitation, SoilMoi0_10cm_inst", "CF standard name, unit, simple "
         "definition for students"],
        ["Concept / Process", "Water availability, drought, evapotranspiration, urban heat",
         "description, synonyms (for search)"],
        ["Region", "Mediterranean, North Africa, Tunisia, Sahara", "geometry id in PostGIS, type "
         "(country, biome, basin)"],
        ["Paper / Report", "IPCC chapters, research articles, NASA reports", "DOI, year, abstract "
         "embedding"],
        ["Analysis", "Analysis run #00421", "method, parameters, code version, timestamp"],
        ["Finding", "“Soil moisture decreased in region X”", "slope, CI, p, q, "
         "significant?, period"],
        ["Hypothesis", "“Less rain caused drier soils”", "status: proposed / tested / "
         "supported / rejected"],
    ], [1.3, 2.7, 3.0]))
    st.append(H2("7.3 Relationship types (the strings)"))
    st.append(table([
        ["Relationship", "Example", "Kind"],
        ["CARRIES", "Terra → MODIS", "fact"],
        ["MEASURES / PROVIDES", "MODIS → NDVI; GLDAS → soil moisture", "fact"],
        ["PRODUCES", "MODIS → MOD13C2 (dataset)", "fact"],
        ["HAS_VARIABLE", "GLDAS_NOAH025_M → SoilMoi0_10cm_inst", "fact"],
        ["SAME_AS", "T2M (MERRA-2) → air_temperature (CF name)", "fact"],
        ["INDICATOR_OF", "Soil moisture → water availability", "literature"],
        ["INFLUENCES", "Precipitation → soil moisture", "literature"],
        ["PART_OF", "Tunisia → North Africa", "fact"],
        ["USES / ANALYZES / GENERATES", "Analysis → dataset / region / finding", "observed"],
        ["ABOUT / IN_REGION", "Finding → variable / region", "observed"],
        ["CO_OCCURS_WITH", "Finding A → Finding B (same cells, same period)", "observed"],
        ["OPPOSITE_OF", "Rain ↑ in north → rain ↓ in south", "observed"],
        ["SUPPORTED_BY / CONTRADICTED_BY", "Hypothesis → finding or paper", "evidence"],
        ["PROPOSED_CAUSE", "Hypothesis → finding it tries to explain", "hypothesis"],
    ], [2.0, 3.3, 1.2]))
    st.append(H2("7.4 Three kinds of truth"))
    st.append(P("Every relationship that says something about how the Earth works carries a "
                "<b>kind</b> label, a <b>source</b> and a <b>confidence</b>:"))
    st.append(table([
        ["Kind", "Meaning", "Who can create it", "Shown in the app as"],
        ["literature", "Established in published science.", "Curators, or the AI only with a "
         "citation that a human verified.", "Solid line + paper icon"],
        ["observed", "Measured by our own statistics on NASA data.", "Only the statistics engine "
         "(after the Auditor passes it).", "Solid line + chart icon"],
        ["hypothesis", "An idea that has not been proven.", "The AI Explainer.",
         "Dashed purple line + “unverified” badge"],
    ], [1.0, 2.2, 2.4, 1.6]))
    st.append(H2("7.5 Two layers in the same graph"))
    st.append(diagram_two_layers())
    st.append(caption("Figure 4. Layer A holds stable knowledge. Layer B holds what our "
                      "investigations found. New evidence is added to Layer B; it never edits Layer A."))
    st.append(H2("7.6 Provenance: what every finding records"))
    st.append(table([
        ["Field", "Example"],
        ["Dataset + version", "GLDAS_NOAH025_M v2.1 (CMR concept id ...)"],
        ["Variable + unit", "SoilMoi0_10cm_inst, kg/m²"],
        ["Region", "Cells inside the “North Africa” shape, 1° grid, 312 land cells"],
        ["Period", "2001-01 to 2024-12 (288 months)"],
        ["Preprocessing", "monthly mean, anomalies vs 2001–2024 climatology, cos-latitude weights"],
        ["Method", "Theil–Sen slope; Mann–Kendall with Hamed–Rao correction; BH-FDR q = 0.10"],
        ["Result", "−0.8 kg/m² per decade, 95% CI [−1.2, −0.4], p = 0.002, q = 0.03"],
        ["Run info", "analysis id, timestamp, code version (git commit), random seed"],
    ], [1.6, 5.4]))
    st.append(H2("7.7 The semantic layer: from words to measurable variables"))
    st.append(P("People don't ask for “SoilMoi0_10cm_inst”. They ask about “water "
                "availability” or “surface heating”. The graph stores <b>Concept</b> "
                "nodes and links them to the variables that can measure them:"))
    st.append(table([
        ["User words", "Concept in the graph", "Measurable variables (and source)"],
        ["“getting hotter”, “heat”", "Surface heating",
         "Air temperature (MERRA-2, AIRS); land surface temperature (MODIS) — different things!"],
        ["“drier”, “drought”, “water”", "Water availability",
         "Precipitation (GPM), soil moisture and ET (GLDAS), total water storage (GRACE)"],
        ["“plants”, “green”, “desert spreading”", "Vegetation health",
         "NDVI, EVI, leaf area index (MODIS)"],
        ["“air pollution in my city”", "Urban air quality", "NO<sub>2</sub>, aerosols (OMI, MODIS)"],
    ], [1.8, 1.5, 3.7]))
    st.append(H2("7.8 GraphRAG: how the AI uses the graph"))
    st.append(P("<b>RAG</b> means <i>Retrieval-Augmented Generation</i>: before the AI answers, it "
                "first <b>retrieves</b> relevant facts and then writes using only those facts. "
                "<b>GraphRAG</b> retrieves from a graph, in three ways that are combined:"))
    st.append(bullets([
        "<b>Vector search</b> — find nodes whose text means something similar to the question "
        "(using embeddings). “drying” finds “drought” and “water availability”.",
        "<b>Graph traversal</b> — from those nodes, follow the strings: concept → variables "
        "→ datasets → missions; or finding → related findings → papers.",
        "<b>Cypher queries</b> — precise questions written in Neo4j's language, for example:",
    ]))
    st.append(code("""
// Which datasets can measure "water availability"?
MATCH (c:Concept {name:"Water availability"})<-[:INDICATOR_OF]-(v:Variable)<-[:HAS_VARIABLE]-(d:Dataset)
RETURN v.name, v.unit, d.short_name, d.version

// All significant water findings in North Africa that use satellite data
MATCH (f:Finding)-[:ABOUT]->(:Variable)-[:INDICATOR_OF]->(:Concept {name:"Water availability"}),
      (f)-[:IN_REGION]->(:Region)-[:PART_OF*0..]->(:Region {name:"North Africa"}),
      (f)<-[:GENERATES]-(:Analysis)-[:USES]->(:Dataset)<-[:PRODUCES]-(:Instrument)
WHERE f.q_value < 0.10
RETURN f
"""))
    st.append(H2("7.9 A graph that grows by itself"))
    st.append(bullets([
        "New datasets and variables are harvested from NASA CMR on a schedule and added as nodes.",
        "Variable names are matched to CF Standard Names (entity resolution) so duplicates merge.",
        "Every audited finding is added to Layer B, with provenance.",
        "Papers are added with their abstract embeddings; mechanisms extracted from them are stored "
        "as <i>literature</i> edges only after a human check.",
    ]))
    st.append(box("owner", ["The AI engineer owns the schema, the ontology, entity resolution, GraphRAG "
                            "and the evidence graph."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 8 stats
    st.append(H1("8. Layer 3 — the statistics engine"))
    st.append(P("This is the part that directly answers the challenge: <b>how much</b> is something "
                "changing and <b>is it significant</b>. It is plain, tested Python code. No AI "
                "decides any number here."))
    st.append(diagram_stats_pipeline())
    st.append(caption("Figure 5. The eight steps, applied to every grid cell and also to the regional "
                      "average."))
    st.append(H3("Step 1 — Pick a region and cut it into cells"))
    st.append(P("The region comes from PostGIS (a country, a biome, a box drawn by the user). We keep "
                "the grid cells whose centre falls inside it. We analyse each cell <b>and</b> the "
                "regional average. For the average we weight each cell by cos(latitude), because "
                "grid cells get smaller towards the poles."))
    st.append(H3("Step 2 — Build the monthly time series"))
    st.append(P("One value per month for each cell, for at least 20 years if possible (for example "
                "2001–2024 = 288 months). Cells with more than 20% missing months are skipped."))
    st.append(H3("Step 3 — Remove the seasons (anomalies)"))
    st.append(P("For each calendar month we compute the long-term average (the <b>climatology</b>): "
                "the average of all Januaries, all Februaries, and so on. Then each value becomes "
                "<b>value − average for that month</b>. The result is called an <b>anomaly</b>."))
    st.append(box("kid", [
        "Is 30 °C hot? In July in Tunis, no, it's normal. In January, it would be crazy hot. "
        "Anomalies compare each month with what is normal <i>for that month</i>, so summer and winter "
        "no longer hide the long-term change."]))
    st.append(H3("Step 4 — Measure the slope (Theil–Sen)"))
    st.append(P("Take every pair of points in the series, compute the slope between them, and keep "
                "the <b>median</b>: slope = median{ (x<sub>j</sub> − x<sub>i</sub>) / "
                "(t<sub>j</sub> − t<sub>i</sub>) } for all i &lt; j. We report it per decade "
                "(“+0.35 °C/decade”) and also as total change over the period."))
    st.append(box("kid", [
        "Imagine 100 friends each guessing how steep a hill is by looking at two random spots. A few "
        "guesses are crazy (one friend looked at a rock). If you take the middle guess (the median), "
        "the crazy ones don't matter. That's why Theil–Sen is called <b>robust</b>: one extreme "
        "year cannot fool it."]))
    st.append(H3("Step 5 — Test it (Mann–Kendall)"))
    st.append(P("Compare every pair of months: if the later one is higher, count +1; if lower, "
                "count −1. Add everything up: S = Σ sign(x<sub>j</sub> − x<sub>i</sub>). "
                "If there is no trend, S stays near zero. A big positive S means “mostly "
                "going up”. The test converts S into a p-value. It does not need the data to "
                "follow a bell curve, which suits rainfall and other skewed variables."))
    st.append(bullets([
        "<b>Autocorrelation fix (Hamed–Rao).</b> Neighbouring months are similar, which makes "
        "the plain test too confident. The Hamed–Rao version corrects the variance of S, so "
        "p-values are honest.",
        "<b>Seasonal Mann–Kendall</b> (Hirsch). An alternative that compares Januaries with "
        "Januaries, Februaries with Februaries, and so on; useful when seasonality is strong.",
        "<b>Also offered: the t-test on a regression slope</b> (the challenge mentions it). We fit an "
        "ordinary least-squares line and test the slope with a t-test, using an <b>effective sample "
        "size</b> n<sub>eff</sub> = n(1 − φ)/(1 + φ), where φ is the lag-1 "
        "autocorrelation. Showing both tests side by side teaches students that methods can be "
        "compared.",
    ]))
    st.append(H3("Step 6 — Add a confidence interval"))
    st.append(P("We report a 95% confidence interval for the slope (from the Theil–Sen "
                "procedure, or a block bootstrap when autocorrelation is strong). A trend whose "
                "interval does not include zero has a trustworthy direction."))
    st.append(H3("Step 7 — The “many tests” problem (FDR)"))
    st.append(P("If we test 1,000 cells at α = 0.05, about 50 will look significant <b>by pure "
                "luck</b> even if nothing is changing. To avoid painting false alarms on the map, we "
                "use the <b>Benjamini–Hochberg false discovery rate (FDR)</b> procedure:"))
    st.append(bullets([
        "Sort the m p-values from smallest to largest: p<sub>(1)</sub> ≤ p<sub>(2)</sub> "
        "≤ … ≤ p<sub>(m)</sub>.",
        "Find the largest k such that p<sub>(k)</sub> ≤ (k / m) · q.",
        "Call the k smallest p-values significant. Each cell also gets an adjusted value called "
        "<b>q-value</b>.",
        "Because neighbouring cells are correlated, Wilks (2016) recommends q = 0.10 to keep the "
        "overall map at about the 0.05 level. We use that setting and say so in the report.",
    ], numbered=True))
    st.append(box("kid", [
        "If 1,000 people each flip a coin 10 times, a few will get 9 or 10 heads just by luck. If you "
        "declared all of them “magic coin owners”, you'd be wrong. FDR is a rule that "
        "raises the bar when you run many tests, so only the really unusual results get the "
        "“significant” stamp."]))
    st.append(H3("Step 8 — Save the result with provenance"))
    st.append(P("Every cell result and every regional result is saved (Parquet + PostGIS), and the "
                "important ones become Finding nodes in the graph with all provenance fields."))
    st.append(code("""
{
  "cell_id": "lat36.5_lon9.5", "variable": "precipitation", "unit": "mm/month",
  "period": ["2001-01", "2024-12"], "n_months": 288, "missing_pct": 0.0,
  "slope_per_decade": -3.1, "ci95": [-5.0, -1.2], "total_change": -7.4,
  "mk_test": "hamed_rao", "tau": -0.12, "p_value": 0.004, "q_value": 0.031,
  "significant": true, "direction": "decreasing",
  "lag1_autocorr": 0.21, "years_needed_if_not_significant": null
}""", "Example result for one cell (illustrative numbers)"))
    st.append(H2("8.1 “Not significant yet”: how many years would we need?"))
    st.append(P("A trend that fails the test is not useless. Using Weatherhead et al. (1998), we "
                "estimate how many years of data would be needed to detect it:"))
    st.append(P("n* ≈ [ (3.3 · σ<sub>N</sub> / |ω|) · "
                "√((1 + φ) / (1 − φ)) ]<super>2/3</super>  years,", "body"))
    st.append(P("where ω is the trend per year, σ<sub>N</sub> the standard deviation of the "
                "monthly anomalies (noise), and φ their lag-1 autocorrelation. The app can then "
                "say: <i>“This decrease is not significant yet. At this rate, about 31 years of "
                "data would be needed; we have 24.”</i> This turns a negative result into a "
                "lesson, exactly as the challenge suggests."))
    st.append(box("owner", ["The ML engineer owns the statistics engine and its unit tests (for example "
                            "checking our p-values against known results and against Giovanni)."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 9 radar
    st.append(H1("9. Layer 4 — Earth Signal Radar (machine learning)"))
    st.append(P("Most tools wait for the user to choose a variable. The Radar does the opposite: it "
                "<b>sweeps</b> many variables over a region and tells you what is worth looking at."))
    st.append(box("kid", [
        "A weather radar spins around and shows you where the storms are. Our Radar spins through "
        "dozens of variables and thousands of grid cells and shows you where the Earth is changing."]))
    st.append(H2("9.1 The scan"))
    st.append(bullets([
        "Ask the graph for candidate variables suitable for the region (e.g. no snow variables in "
        "the Sahara).",
        "Run the statistics engine for every variable × cell.",
        "Compute an <b>interest score</b> per variable, combining: the share of the region with "
        "significant trends (after FDR), the size of the trend compared with the noise "
        "(signal-to-noise), and how spatially coherent the significant cells are (big connected "
        "patches matter more than scattered single cells).",
        "Rank and present the top discoveries, each linked to its maps and time series.",
    ], numbered=True))
    st.append(H2("9.2 The opposite-trend detector"))
    st.append(P("For each variable we build a map of trend <b>direction</b> (up, down, no "
                "significant change). We then look for large significant patches of opposite sign "
                "inside the same region (a “dipole”). The app shows these side by side with "
                "the regional average, to demonstrate how averaging can hide real changes. This is "
                "the distinctive problem described in the challenge."))
    st.append(H2("9.3 Trend signatures and clustering"))
    st.append(P("Each cell r is described by a vector of its standardised trends:"))
    st.append(P("X<sub>r</sub> = [ β<sub>T</sub>, β<sub>P</sub>, β<sub>SM</sub>, "
                "β<sub>ET</sub>, β<sub>NDVI</sub> ]  (temperature, precipitation, soil "
                "moisture, evapotranspiration, vegetation)"))
    st.append(P("Each β is divided by that variable's noise so that variables with big units "
                "don't dominate. A clustering algorithm (HDBSCAN, or hierarchical clustering) groups "
                "cells with similar “signatures”. A cluster where temperature goes up while "
                "precipitation, soil moisture and NDVI go down is a <b>compound warming–drying "
                "signal</b>. The Radar names each cluster by its signature and sends it to the "
                "Investigator."))
    st.append(H2("9.4 Anomalies and change points"))
    st.append(bullets([
        "<b>Change-point detection</b> (e.g. the PELT algorithm in the <i>ruptures</i> library) finds "
        "the month when a series suddenly changes level or slope, such as after a new dam or a "
        "multi-year drought.",
        "<b>Isolation Forest</b> flags cells whose recent behaviour is unusual compared with their own "
        "history and their neighbours.",
        "Seasonal anomaly scores highlight extreme months (heatwaves, failed rainy seasons).",
    ]))
    st.append(H2("9.5 Spatiotemporal Graph Neural Networks (advanced)"))
    st.append(P("We build a <b>geographic graph</b>: each cell is a node, neighbouring cells are "
                "linked, and extra links can connect cells that are physically related (same river "
                "basin, upwind/downwind). Each node carries its multivariate time series. A "
                "spatiotemporal GNN (built with PyTorch Geometric) learns coherent patterns across "
                "space and time. Uses: detecting regions that evolve together, finding regional "
                "dependencies, and forecasting anomalies."))
    st.append(box("rule", [
        "The GNN and the clusters <b>suggest where to look</b>. Only the statistics engine (with "
        "autocorrelation and FDR corrections) decides whether a trend is significant. A neural "
        "network prediction is never shown as a significance result."]))
    st.append(box("owner", ["The ML engineer owns the Radar: scoring, clustering, change points, "
                            "anomaly detection and the GNN experiments."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 10 agents
    st.append(H1("10. Layer 5 — the AI agents (the Investigator)"))
    st.append(H2("10.1 What is an LLM agent?"))
    st.append(P("An <b>LLM</b> (Large Language Model) is an AI that understands and writes text. An "
                "<b>agent</b> is an LLM that can also <b>use tools</b>: call a function, query the "
                "graph, run the statistics engine. Instead of answering immediately, it makes a plan, "
                "runs the steps and checks the results."))
    st.append(box("kid", [
        "A chatbot is like a student answering from memory. An agent is like a student who is allowed "
        "to go to the library, use a calculator and ask the lab for measurements before answering. "
        "And our rule is: the student must show the calculator's result, not invent one."]))
    st.append(H2("10.2 The team of agents"))
    st.append(diagram_agents())
    st.append(caption("Figure 6. A coordinated team, not free chat: the Orchestrator decides who works "
                      "next, and every agent returns typed (structured) outputs."))
    st.append(table([
        ["Agent", "Job", "Tools it calls", "What it returns"],
        ["Orchestrator", "Understands the question, plans, routes work, keeps state, retries.",
         "All agents", "The investigation plan and final state"],
        ["1 · Knowledge Discovery", "Translates concepts into variables and processes.",
         "GraphRAG, Cypher", "Candidate variables + reasons + related mechanisms"],
        ["2 · Dataset Discovery", "Finds the best datasets for each variable, region, period.",
         "NASA CMR, graph", "Dataset list with versions, coverage, resolution"],
        ["3 · Data Engineer", "Gets and prepares the data.", "earthaccess, OPeNDAP, xarray, QC",
         "Paths to clean, aligned data + QC report"],
        ["4 · Statistical Scientist", "Runs trends, tests, FDR, Radar.", "Stats engine, Radar",
         "Typed results (JSON) with numbers"],
        ["5 · Scientific Auditor", "Checks validity independently (code, not opinion).",
         "Validation functions", "Pass / fail + warnings"],
        ["6 · Scientific Explainer", "Builds competing hypotheses and the report.",
         "Graph, literature search", "Explanations labelled by evidence type"],
    ], [1.5, 2.2, 1.6, 2.0]))
    st.append(H2("10.3 The contract: an investigation specification"))
    st.append(P("The AI side produces a <b>specification</b>, not conclusions. The engines execute "
                "it and return numbers. This contract is the boundary between the AI team and the "
                "ML team."))
    st.append(code("""
{
  "objective": "detect_compound_environmental_trends",
  "question": "Where is it getting hotter while water availability decreases?",
  "concepts": ["surface heating", "water availability"],
  "variables": ["air_temperature", "precipitation", "soil_moisture", "evapotranspiration"],
  "datasets": ["M2TMNXSLV", "GPM_3IMERGM", "GLDAS_NOAH025_M"],
  "region": {"name": "Mediterranean", "source": "postgis:regions/1042"},
  "period": {"start": "2001-01-01", "end": "2024-12-31"},
  "temporal_resolution": "monthly",
  "grid": "1.0deg",
  "methods": ["deseasonalize", "theil_sen", "mann_kendall_hamed_rao", "fdr_bh"],
  "alpha": 0.05, "fdr_q": 0.10,
  "output": ["trend_maps", "opposite_trend_map", "spatial_clusters", "evidence_graph", "report"]
}"""))
    st.append(H2("10.4 The workflow as a state machine"))
    st.append(P("The Orchestrator is built with <b>LangGraph</b>, where each step is a state and "
                "transitions are explicit:"))
    st.append(bullets([
        "<b>UNDERSTAND</b> — parse the question; if something is missing (where? when?), ask "
        "the user a short follow-up.",
        "<b>PLAN</b> — Knowledge Discovery + Dataset Discovery produce the specification; the "
        "user can see and edit it.",
        "<b>ACQUIRE</b> — Data Engineer gets and cleans the data.",
        "<b>ANALYSE</b> — Statistical Scientist runs the engines.",
        "<b>AUDIT</b> — Auditor checks; on failure, go back to ACQUIRE or ANALYSE with the reason "
        "(maximum 2 retries, then report the problem honestly).",
        "<b>RECORD</b> — audited findings are written to Layer B of the graph.",
        "<b>EXPLAIN</b> — Explainer builds competing hypotheses using the graph and literature.",
        "<b>REPORT</b> — final report with maps, numbers, methods, sources and uncertainty.",
    ], numbered=True))
    st.append(H2("10.5 What the Auditor checks"))
    st.append(bullets([
        "Enough data: at least ~20 years and less than 20% missing per cell.",
        "Units are consistent and values are physically plausible (no negative rainfall).",
        "Seasonality was removed; autocorrelation was handled; FDR was applied to maps.",
        "No dataset version change inside the period that could create a fake jump.",
        "Every number in the AI's text exists in the engine's output (string-match check).",
        "Every <i>literature</i> claim has a citation; every unproven link is marked <i>hypothesis</i>.",
    ]))
    st.append(H2("10.6 Guided mode for students"))
    st.append(P("Not everyone wants to type a question. Guided mode asks three or four simple "
                "questions with buttons: <i>What are you curious about?</i> (heat, water, plants, air "
                "quality, oceans) → <i>Where?</i> (map click or a place name) → <i>Since "
                "when?</i> → <i>Compare with something else?</i>. The answers fill the same "
                "specification. Two <b>demo investigations</b> can be replayed step by step so new "
                "users can watch how the tool works."))
    st.append(box("owner", ["The AI engineer owns the Orchestrator, the agents, the specification "
                            "format and the guided mode, together with the product engineers for "
                            "the UI."]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 11 why
    st.append(H1("11. Explaining WHY: the hypothesis engine"))
    st.append(P("After a trend is found, the user can click <b>“Investigate possible causes”"
                "</b>. The Explainer follows mechanism paths in the graph, for example:"))
    st.append(P("<b>Precipitation</b> → (changes water input) → <b>Soil moisture</b> "
                "→ (limits water for plants and evaporation) → <b>Evapotranspiration</b> "
                "→ (less cooling by evaporation) → <b>Land surface temperature</b> → "
                "<b>Vegetation stress</b>"))
    st.append(H2("11.1 Competing hypotheses, not one story"))
    st.append(table([
        ["Candidate explanation", "What we can check with NASA data", "Status shown"],
        ["Less rainfall", "Is precipitation (GPM) also decreasing over the same cells and period?",
         "Supported / not supported by our data"],
        ["Higher evaporative demand (hotter, drier air)", "Are temperature (MERRA-2) and ET "
         "(GLDAS) increasing?", "Supported / not supported"],
        ["Land-use change", "Did NDVI or land cover change abruptly (change point)?",
         "Needs more data"],
        ["Irrigation or groundwater pumping", "Does GRACE show water-storage loss while rainfall is "
         "stable?", "Unresolved hypothesis"],
    ], [2.0, 3.4, 1.6]))
    st.append(H2("11.2 Three labels on every explanation"))
    st.append(bullets([
        "<b>Observed evidence</b> — what our NASA-data analyses actually show (with numbers).",
        "<b>Literature evidence</b> — what published research supports (with citations).",
        "<b>Unresolved hypothesis</b> — what remains to be established.",
    ]))
    st.append(box("rule", [
        "A path in a graph is <b>not proof of cause</b>. Two trends happening together is "
        "<b>correlation</b>, not causation. The system must be able to say “the data are not "
        "enough to know why”. A tool that knows its limits is more trustworthy for judges and "
        "for students."]))
    st.append(H2("11.3 Simple checks the Explainer can request"))
    st.append(bullets([
        "Correlation between the anomaly series of two variables in the same cells (after removing "
        "trends, to avoid counting the trend twice).",
        "Lagged correlation (does rainfall change lead soil-moisture change by 1–3 months?).",
        "Spatial overlap: do the significant cells of both variables coincide?",
        "Each check is run by the statistics engine and recorded as a new observed finding.",
    ]))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 12 app
    st.append(H1("12. Layer 6 — the app"))
    st.append(table([
        ["Screen", "What the user sees and does"],
        ["Home", "“What do you want to investigate?” box, guided mode button, two demo "
         "investigations to watch."],
        ["Plan", "The investigation plan written in simple words: chosen variables (with "
         "definitions), datasets, region, period, methods. The user can edit it."],
        ["Live progress", "Each agent step lights up with what it is doing (“Downloading GLDAS "
         "2001–2024…”)."],
        ["Trend map", "Interactive map (MapLibre): colour = slope per decade; dots = significant "
         "after FDR; click a cell to open its time series."],
        ["Opposite-trend map", "Up / down / no change map next to the regional average chart."],
        ["Time series", "Raw monthly series, anomalies, trend line, confidence band, p and q values, "
         "and “years needed” when not significant."],
        ["Signal Radar", "Ranked list of discoveries with small maps; clusters with their signatures."],
        ["Graph explorer", "Interactive graph: click a finding to see its datasets, mechanisms, "
         "papers and hypotheses."],
        ["Report", "Downloadable report: question, method, results, maps, uncertainty, provenance, "
         "references."],
    ], [1.4, 5.6]))
    st.append(P("Every variable name has a small “?” with a one-sentence definition for "
                "students. Colours are colour-blind safe (blue = decrease, red/orange = increase for "
                "temperature; brown/green for water and vegetation)."))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 13 walkthrough
    st.append(H1("13. One complete investigation, step by step"))
    st.append(P("<i>The story below shows how the parts work together. Numbers are placeholders "
                "to illustrate the format, not real results.</i>"))
    st.append(bullets([
        "<b>The question.</b> A student types: “Find areas around the Mediterranean where it is "
        "getting hotter while water is becoming scarcer.”",
        "<b>Understanding.</b> The Orchestrator recognises two concepts (surface heating, water "
        "availability), a region (Mediterranean) and no period, so it proposes 2001–2024 "
        "(the longest period common to all datasets).",
        "<b>Knowledge Discovery.</b> GraphRAG maps “heating” to air temperature and land "
        "surface temperature, and “water” to precipitation, soil moisture and ET, explaining "
        "why each was chosen.",
        "<b>Dataset Discovery.</b> CMR returns MERRA-2 M2TMNXSLV, GPM_3IMERGM, GLDAS_NOAH025_M and "
        "MOD11C3, with versions and coverage.",
        "<b>Data Engineer.</b> Subsets the region, converts units, regrids to 0.25°, removes fill "
        "values, writes a QC report (e.g. 3% of cells dropped for missing data).",
        "<b>Statistical Scientist.</b> Runs the 8-step pipeline on ~4,000 cells × 5 variables, "
        "plus the Radar: 3 clusters, one with a “temperature ↑, precipitation ↓, soil "
        "moisture ↓” signature in a coherent patch.",
        "<b>Auditor.</b> Confirms record length, units, FDR applied; warns that IMERG has a version "
        "change and that ET from a model is less certain than satellite observations.",
        "<b>Record.</b> Findings A–F written to Layer B with provenance; an OPPOSITE_OF link "
        "between “rain ↑ north” and “rain ↓ south”.",
        "<b>Explain.</b> The Explainer proposes 3 competing hypotheses, runs the overlap and "
        "correlation checks, and labels each one.",
        "<b>Report.</b> The student sees the maps, the time series, the significance, the "
        "explanation with its labels, and can download everything with full provenance.",
    ], numbered=True))
    st.append(PageBreak())

    # ---------------------------------------------------------------- 14 tech
    st.append(H1("14. Technology stack"))
    st.append(table([
        ["Layer", "Technology", "Why"],
        ["Graph database", "Neo4j", "Mature graph DB, Cypher queries, vector indexes."],
        ["GraphRAG", "neo4j-graphrag (Python)", "Official package for vector, hybrid and "
         "Cypher-enhanced retrieval."],
        ["Agent orchestration", "LangGraph", "Explicit states and transitions, typed tool outputs, "
         "retries."],
        ["LLM", "A strong tool-calling model (e.g. Claude Opus or Sonnet)", "Planning, mapping "
         "concepts to variables, writing explanations."],
        ["Embeddings", "A scientific text embedding model", "Search over papers, metadata, concepts."],
        ["Data catalogue", "NASA CMR + earthaccess", "Official discovery and download."],
        ["Data storage", "S3 / MinIO + Zarr / NetCDF / Parquet", "Big gridded data, fast results."],
        ["Geospatial DB", "PostGIS", "Regions, spatial queries, per-cell results."],
        ["Statistics", "xarray, SciPy, pymannkendall, statsmodels", "Trusted, testable methods."],
        ["ML", "scikit-learn, hdbscan, ruptures, PyTorch, PyTorch Geometric", "Clustering, change "
         "points, anomalies, GNN."],
        ["Backend", "FastAPI", "Python API for the engines and the agents."],
        ["Frontend", "React, TypeScript, MapLibre, a graph-visualisation library", "Interactive maps "
         "and graphs."],
    ], [1.5, 2.6, 2.9]))

    # ---------------------------------------------------------------- 15 team
    st.append(H1("15. Who does what"))
    st.append(table([
        ["Role", "Owns", "Main tasks"],
        ["AI engineer", "Earth System Intelligence (graph, GraphRAG, agents)",
         "Graph schema and ontology; CMR metadata ingestion and entity resolution; GraphRAG; "
         "Orchestrator and agents; evidence graph; hypothesis engine and explanations."],
        ["ML engineer", "Environmental Signal Intelligence (statistics, Radar)",
         "Trend engine; significance tests and FDR; years-needed estimate; clustering, change "
         "points, anomalies; GNN experiments; uncertainty."],
        ["Integration / product engineers", "Scientific Data Platform + app",
         "NASA data acquisition, storage, QC; FastAPI backend; React app with maps, charts and graph "
         "explorer; end-to-end integration; presentation."],
    ], [1.4, 2.0, 3.6]))
    st.append(P("The AI and ML engineers meet at the <b>contract</b>: the investigation "
                "specification (AI → ML) and the typed results (ML → AI). Agree on both JSON "
                "formats first, and everyone can work in parallel."))

    # ---------------------------------------------------------------- 16 judging
    st.append(H1("16. Why this scores well with the judges"))
    st.append(table([
        ["Criterion", "What in EarthSleuth earns points"],
        ["Impact", "Turns students and the public into data detectives; no need to know variable "
         "names; works for any region."],
        ["Creativity", "Automatic discovery (Radar), opposite-trend detection, an evidence graph that "
         "separates facts, observations and hypotheses, and an investigator that plans real "
         "experiments."],
        ["Validity", "Correct statistics (anomalies, Theil–Sen, Mann–Kendall with "
         "autocorrelation fix, CIs, FDR), an independent auditor, full provenance."],
        ["Relevance", "Every finding comes from NASA missions and models (MODIS, GPM, AIRS, OMI, "
         "MERRA-2, GLDAS, GRACE) found via NASA CMR."],
        ["Presentation", "One clear story: vague question → plan → maps → "
         "significance → explanation with evidence."],
    ], [1.3, 5.7]))
    st.append(PageBreak())

    glossary_section(st, 17)
    doc.build_story(st)


if __name__ == "__main__":
    build(sys.argv[1])
