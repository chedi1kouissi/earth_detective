"""Report: the investigation with methods, numbers, data sources and provenance."""
import json

import common_ui as ui
import streamlit as st

ui.page_header("Report", "Everything about the current investigation, ready to download.")

rep = st.session_state.get("investigation")
if not rep:
    st.info("Run or open an investigation on the **Ask** page first.")
    st.stop()


def build_markdown(rep: dict) -> str:
    L = [f"# EarthSleuth investigation", "", f"**Question:** {rep['question']}  ",
         f"**Date:** {rep['created']} · **Investigation id:** `{rep['id']}`  "]
    if rep.get("synthetic"):
        L.append("**WARNING: computed on SYNTHETIC test data, not real NASA data.**  ")
    L += ["", rep.get("answer", ""), ""]
    if rep.get("status") == "done":
        plan = rep["steps"]["Plan"]
        L += ["## Data used", ""]
        for v in plan["variable_details"]:
            d = v["dataset"]
            L.append(f"- **{v['display_name']}** - {d['title']} (DOI {d.get('doi') or 'n/a'}, CMR "
                     f"{d.get('cmr_concept_id')}); variable `{v['recipe']['name_in_file']}` "
                     f"[{v['recipe']['unit_native']}] converted to {v['unit']} "
                     f"({v['recipe']['conversion']}).")
        L += ["", "## Method", ""]
        L += [f"{i + 1}. {m['name']} - {m['description']}" for i, m in enumerate(rep.get("methods", []))]
        L += ["", "## Results (Contract 2)", "", "| variable | slope per decade | 95% CI | p | "
              "significant | area up % | area down % |", "|---|---|---|---|---|---|---|"]
        for r in rep["steps"]["Analyse"]["results"].values():
            g = r["regional"]
            ci = " to ".join(f"{x:+.3g}" for x in g["ci95"]) if g["ci95"][0] is not None else "n/a"
            L.append(f"| {r['display_name']} | {g['slope_per_decade']:+.3g} {r['unit'].replace(' per decade', '')} | "
                     f"{ci} | {ui.fmt_p(g['p'])} | {g['significant']} | "
                     f"{r['cells']['pct_sig_up_area']} | {r['cells']['pct_sig_down_area']} |")
        L += ["", "## Provenance", "",
              f"- Engine run: `{rep['steps']['Record']['analysis']}`",
              f"- Findings written to the graph: {len(rep['findings'])}",
              f"- Graph backend: {rep.get('store')}; explanation mode: "
              f"{rep['steps']['Check']['mode']} (number check passed: "
              f"{rep['steps']['Check']['passed']})",
              "- AI use: Gemini interpreted the question (constrained to graph concepts) and wrote "
              "the explanation from the evidence pack; all numbers come from the statistics engine.",
              "- Statistical caveat: the Theil-Sen confidence interval does not account for "
              "autocorrelation and can be slightly too narrow."]
    return "\n".join(L)


md = build_markdown(rep)
st.markdown(md)
st.download_button("Download report (Markdown)", md, file_name=f"{rep['id'].split(':')[1]}.md")
st.download_button("Download full investigation (JSON)", json.dumps(rep, indent=1, default=str),
                   file_name=f"{rep['id'].split(':')[1]}.json")
