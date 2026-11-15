"""EarthSleuth - one command per phase (Document 2, section 4.4).

    python run.py status                 what is ready (data, graph, Gemini, Neo4j)
    python run.py download [--dataset gldas] [--start 2001-01 --end 2024-12]
    python run.py sample                 download ONE file per dataset (for the curator)
    python run.py preprocess             data/small -> data/processed/series.nc
    python run.py precompute             whole-region trends, clusters, findings.json
    python run.py build_graph [--fresh]  curator agent (Gemini) -> Neo4j, validate, evidence, export
    python run.py load_seed [--fresh]    backup: seed.yaml -> graph (no LLM, offline)
    python run.py evidence               findings.json -> graph (Layer B)
    python run.py validate               automatic graph checks
    python run.py export | restore       graph.json snapshot / restore the latest snapshot
    python run.py ask "question"         run one investigation in the terminal
    python run.py app                    start the Streamlit app
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from common import config as C  # noqa: E402

log = logging.getLogger("earthsleuth")


def cmd_status(_):
    import xarray as xr
    print(f"Region   : {C.REGION_NAME} {C.REGION.as_tuple()}, {C.PERIOD_START}..{C.PERIOD_END}")
    if C.SERIES_NC.exists():
        with xr.open_dataset(C.SERIES_NC) as ds:
            kind = "SYNTHETIC test data" if int(ds.attrs.get("synthetic", 0)) else "real NASA data"
            print(f"series.nc: {kind}, variables {[v for v in ds.data_vars if v != 'land_mask']}, "
                  f"{int(ds['land_mask'].sum())} land cells, created {ds.attrs.get('created')}")
    else:
        print("series.nc: missing (run `download` + `preprocess`)")
    for key in ("merra2", "imerg", "gldas", "modis_ndvi"):
        n = len(list((C.SMALL / key).glob("*.npz"))) if (C.SMALL / key).exists() else 0
        sample = list((C.RAW / key / "sample").glob("*")) if (C.RAW / key / "sample").exists() else []
        print(f"  {key:11s}: {n:3d}/288 months processed, sample file: {'yes' if sample else 'no'}")
    print(f"Precomputed: {'yes' if C.FINDINGS_JSON.exists() else 'no'}")
    print(f"Gemini key: {'set' if C.GEMINI_API_KEY else 'MISSING'}; Earthdata login: "
          f"{'set' if C.EARTHDATA_USERNAME else 'missing (needed for download)'}")
    from graph.store import Neo4jStore
    try:
        s = Neo4jStore()
        print(f"Neo4j    : reachable at {C.NEO4J_URI}, {s.counts()}")
        s.close()
    except Exception as e:  # noqa: BLE001
        print(f"Neo4j    : NOT reachable ({e.__class__.__name__}); graph.json "
              f"{'exists' if C.GRAPH_JSON.exists() else 'missing'}")


def cmd_download(a):
    from pipeline.download import download_dataset
    keys = ["merra2", "imerg", "gldas", "modis_ndvi"] if a.dataset == "all" else [a.dataset]
    for k in keys:
        print(json.dumps(download_dataset(k, a.start, a.end, threads=a.threads), indent=1))


def cmd_sample(a):
    from pipeline.download import download_sample_only
    keys = ["merra2", "imerg", "gldas", "modis_ndvi"] if a.dataset == "all" else [a.dataset]
    for k in keys:
        print(k, "->", download_sample_only(k))


def cmd_preprocess(_):
    from pipeline.preprocess import build_series
    print("written:", build_series())


def cmd_precompute(_):
    from engine.run_all import precompute
    pkg = precompute()
    print(f"{len(pkg['findings'])} findings, {len(pkg['opposite_pairs'])} opposite pairs, "
          f"{len(pkg['co_occurs'])} co-occurrences -> {C.FINDINGS_JSON}")


def _store(a):
    from graph.store import get_store
    s = get_store("json" if getattr(a, "json", False) else "neo4j")
    print(f"graph backend: {s.backend}")
    return s


def cmd_build_graph(a):
    from graph.curator_agent import build_graph
    s = _store(a)
    if a.fresh:
        s.clear()
    res = build_graph(s, max_turns=a.max_turns)
    print("\nCurator finished:", res["final_message"][:500])
    print(f"tool calls: {res['calls']} (refused: {res['refused']})")
    print("still missing:", res["missing"] or "nothing")
    print("validation problems:", res["problems"] or "none")
    _evidence(s)
    _export(s)


def cmd_load_seed(a):
    from graph.load_seed import load_seed
    s = _store(a)
    if a.fresh:
        s.clear()
    print(load_seed(s))
    from graph.validate_graph import validate
    print("validation problems:", validate(s) or "none")
    _evidence(s)
    _export(s)


def _evidence(s):
    if not C.FINDINGS_JSON.exists():
        print("(no findings.json yet - run `precompute` to add Layer B)")
        return
    from graph.evidence import write_evidence
    pkg = json.loads(C.FINDINGS_JSON.read_text())
    print("evidence:", write_evidence(s, pkg))


def _export(s):
    from graph.export import export_snapshot
    print("snapshot:", export_snapshot(s)["snapshot"])


def cmd_evidence(a):
    _evidence(_store(a))


def cmd_validate(a):
    from graph.validate_graph import validate
    probs = validate(_store(a))
    print("\n".join(probs) if probs else "graph passed all checks")


def cmd_export(a):
    _export(_store(a))
    from graph.export import dump_instructions
    print(dump_instructions())


def cmd_restore(a):
    from graph.export import restore_snapshot
    print("restored nodes:", restore_snapshot(_store(a)))


def cmd_ask(a):
    from agent.investigator import Investigator
    inv = Investigator(store=_store(a), use_llm=not a.no_llm)
    r = inv.run(a.question, on_step=lambda st, status, _: print(f"  [{st}] {status}"))
    print("\n" + r["answer"])
    print(f"\n(saved to {r['saved_to']})")


def cmd_app(_):
    subprocess.call([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "Home.py")])


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "google_genai", "neo4j", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    p = argparse.ArgumentParser(description="EarthSleuth", formatter_class=argparse.RawTextHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    d = sub.add_parser("download")
    d.add_argument("--dataset", default="all", choices=["all", "merra2", "imerg", "gldas",
                                                        "modis_ndvi"])
    d.add_argument("--start", default=C.PERIOD_START)
    d.add_argument("--end", default=C.PERIOD_END)
    d.add_argument("--threads", type=int, default=4)
    d.set_defaults(fn=cmd_download)
    sm = sub.add_parser("sample")
    sm.add_argument("--dataset", default="all", choices=["all", "merra2", "imerg", "gldas",
                                                         "modis_ndvi"])
    sm.set_defaults(fn=cmd_sample)
    for name, fn in (("preprocess", cmd_preprocess), ("precompute", cmd_precompute),
                     ("app", cmd_app)):
        sub.add_parser(name).set_defaults(fn=fn)
    for name, fn in (("evidence", cmd_evidence), ("validate", cmd_validate),
                     ("export", cmd_export), ("restore", cmd_restore)):
        x = sub.add_parser(name)
        x.add_argument("--json", action="store_true", help="use graph.json instead of Neo4j")
        x.set_defaults(fn=fn)
    b = sub.add_parser("build_graph")
    b.add_argument("--fresh", action="store_true", help="empty the graph first")
    b.add_argument("--max-turns", type=int, default=80)
    b.add_argument("--json", action="store_true")
    b.set_defaults(fn=cmd_build_graph)
    ls = sub.add_parser("load_seed")
    ls.add_argument("--fresh", action="store_true")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(fn=cmd_load_seed)
    q = sub.add_parser("ask")
    q.add_argument("question")
    q.add_argument("--no-llm", action="store_true")
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_ask)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
