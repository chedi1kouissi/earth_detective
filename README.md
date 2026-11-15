# EarthSleuth 🛰️

*Turn questions about our changing planet into honest, data-backed investigations with NASA data.*
NASA Space Apps Challenge 2026. The design is in [`docs/EarthSleuth_2_Hackathon_Build.pdf`](docs/EarthSleuth_2_Hackathon_Build.pdf)
(the full vision is in `docs/EarthSleuth_1_Full_System.pdf`).

A student asks *"Is Tunisia getting hotter and drier?"*. An **AI investigator** follows a **Neo4j
knowledge graph** (built by an **AI curator agent**, every fact checked by tools) to choose the NASA
variables, runs **real statistics** on 24 years of monthly data, writes the evidence back to the graph,
proposes labelled hypotheses, checks every number, and explains the result for a high-school student.

## The four phases

| Phase | Command | What happens | Output |
|---|---|---|---|
| 1 · Data (once) | `download`, `preprocess` | NASA files → region, units, 1° grid, land mask | `data/processed/series.nc` |
|  | `precompute` | whole-region statistics + Radar-lite (cache) | `trends.parquet`, `findings.json` |
| 2 · Graph (once) | `build_graph` | Gemini curator fills Neo4j through checking tools; validate; evidence; snapshot | Neo4j + `data/graph/graph.json` |
| 3 · Investigation | `app` / `ask` | the investigator walks the graph: plan → stats → evidence → hypotheses → check → explain | answer, charts, report |
| 4 · Result | Report page | numbers, labels (observed / literature / hypothesis), provenance | Markdown / JSON |

## Setup (Windows, Python 3.10+)

```bash
python -m venv detective
detective\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in the values
```

`.env` needs: `GEMINI_API_KEY`, `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (local Neo4j Desktop
running), and for downloads `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`
(free account at https://urs.earthdata.nasa.gov; in your profile approve **NASA GESDISC DATA ARCHIVE**
under *Applications → Authorized Apps*, otherwise GES DISC downloads fail).
**Never commit `.env`** (it is in `.gitignore`).

## Run everything

```bash
python run.py status                      # what is ready
python run.py download                    # ~52 GB streamed, processed and deleted file by file (resumable)
python run.py download --dataset gldas    # or one dataset per terminal, in parallel
python run.py preprocess                  # -> series.nc (land mask from GLDAS)
python run.py precompute                  # whole-region cache + findings.json
python run.py build_graph --fresh         # curator agent (Gemini) -> Neo4j, validate, evidence, snapshot
python run.py app                         # http://localhost:8501
```

Other commands: `load_seed` (hand-written backup graph, offline, no LLM), `evidence`, `validate`,
`export` / `restore` (graph snapshots), `ask "question"` (terminal investigation), `sample`
(one file per dataset so the curator can read real file headers).

## Repository layout

```
run.py                one command per phase
common/               config (region, grid, thresholds), reference variables table, Contracts 1-2
pipeline/             download.py (earthaccess), preprocess.py (readers + 1° binning)
engine/               stats.py (anomalies, Theil-Sen, Mann-Kendall Hamed-Rao, BH-FDR, Weatherhead),
                      analysis.py (on-demand engine + guardrails + cache), radar.py, findings.py, run_all.py
graph/                schema.yaml (CONTRACT 0), strategy.yaml, papers.yaml, store.py (Neo4j / JSON),
                      sources.py (CMR, file headers, Crossref), curator_tools.py, curator_agent.py,
                      validate_graph.py, evidence.py (Layer B), queries.py (graph paths), seed.yaml, export.py
agent/                llm.py (Gemini), tools.py (investigator tools), investigator.py (7 steps)
app/                  Streamlit: Home, Ask, Trend map, Time series, Radar, Graph, Report
docs/                 the two team PDFs
```

## Golden rules (enforced in code)

* **The AI never computes numbers.** Statistics are plain Python; the explanation passes a number check
  (every number must appear in the tool outputs, with the same sign) or is regenerated / replaced by
  a template.
* **The AI decides what goes in the graph, never the facts.** Units, fill values, dates, DOIs come from
  NASA CMR, the real file headers or Crossref. No raw Cypher for the curator. Schema enforced on every
  write, `MERGE` on canonical ids, `validate_graph` after every build.
* **Every finding has provenance** (dataset versions, method, run id).
* **Hypotheses are always labelled** (`status: hypothesis`, drawn dashed).
* **ML suggests, statistics decides** (clusters are named from significant trends only).

## For the team: papers

`graph/papers.yaml` lists 5 verified DOIs. A paper is used only after a teammate **reads it** and writes
their name in `read_by` (and pastes the abstract when Crossref has none). Then run
`python run.py build_graph` again: the curator adds the paper and the `INFLUENCES` links whose quote is
found word-for-word in the abstract.

## AI use (for the submission form)

Gemini builds the knowledge graph (curator agent, tool-checked, human-reviewed), maps questions to
graph concepts, and writes explanations from a fixed evidence pack. AI assistance was used to write code.
No NASA logos are used.

## Data

NASA MERRA-2 `M2TMNXSLV` v5.12.4 (doi:10.5067/AP1B0BA5PD2K) · GPM IMERG `GPM_3IMERGM` v07
(doi:10.5067/GPM/IMERG/3B-MONTH/07) · GLDAS `GLDAS_NOAH025_M` v2.1 (doi:10.5067/SXAVCZFAQLNO) ·
MODIS `MOD13C2` v061 (doi:10.5067/MODIS/MOD13C2.061).
