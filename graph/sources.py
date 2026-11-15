"""Trusted sources the curator tools read facts from (never the LLM's memory):
- NASA CMR (collections and UMM-Var variable metadata) - public, no login;
- the header of a real downloaded file (data/raw/<dataset>/sample/);
- Crossref / OpenAlex for papers, or an abstract pasted by a team member in papers.yaml.
Every HTTP answer is cached in data/cache/http so repeated builds are fast and offline-friendly.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

import requests
import yaml

from common import config as C
from common.variables import DATASETS

HTTP_CACHE = C.CACHE / "http"
HTTP_CACHE.mkdir(parents=True, exist_ok=True)
PAPERS_YAML = Path(__file__).with_name("papers.yaml")
UA = {"User-Agent": "EarthSleuth/0.1 (NASA Space Apps 2026 student project)"}


class SourceError(RuntimeError):
    pass


def get_json(url: str, params: dict | None = None) -> dict:
    key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    f = HTTP_CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        r = requests.get(url, params=params, headers=UA, timeout=C.HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise SourceError(f"network error calling {url}: {e}") from e
    if r.status_code == 404:
        raise SourceError(f"not found: {url}")
    if not r.ok:
        raise SourceError(f"{url} answered {r.status_code}")
    data = r.json()
    f.write_text(json.dumps(data), encoding="utf-8")
    return data


# ----------------------------------------------------------------------------- CMR
def cmr_collection(short_name: str, version: str) -> dict:
    d = get_json(f"{C.CMR_URL}/collections.umm_json",
                 {"short_name": short_name, "version": version, "page_size": 5})
    items = d.get("items", [])
    if not items:
        raise SourceError(f"CMR has no collection {short_name} version {version}")
    it = items[0]
    umm, meta = it["umm"], it["meta"]
    temporal = (umm.get("TemporalExtents") or [{}])[0]
    rng = (temporal.get("RangeDateTimes") or [{}])[0]
    platforms = [{"name": p.get("ShortName"),
                  "instruments": [i.get("ShortName") for i in p.get("Instruments", [])
                                  if i.get("ShortName") and i.get("ShortName") != "NOT APPLICABLE"]}
                 for p in umm.get("Platforms", [])]
    return dict(
        short_name=umm.get("ShortName"), version=umm.get("Version"),
        title=umm.get("EntryTitle"), cmr_concept_id=meta["concept-id"],
        provider=meta.get("provider-id"), doi=(umm.get("DOI") or {}).get("DOI"),
        time_start=rng.get("BeginningDateTime"), time_end=rng.get("EndingDateTime"),
        platforms=platforms, variable_ids=(meta.get("associations") or {}).get("variables", []),
        processing_level=(umm.get("ProcessingLevel") or {}).get("Id"))


def cmr_variable(collection: dict, name_in_file: str) -> dict | None:
    """UMM-Var record of one variable of a collection (units, fill value, scale...)."""
    ids = collection.get("variable_ids") or []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        d = get_json(f"{C.CMR_URL}/variables.umm_json",
                     {"concept_id": chunk, "page_size": 100})
        for it in d.get("items", []):
            umm = it["umm"]
            names = {umm.get("Name"), (umm.get("Name") or "").split("/")[-1]}
            if name_in_file in names:
                fills = umm.get("FillValues") or []
                return dict(units=umm.get("Units"), long_name=umm.get("LongName"),
                            fill_value=fills[0].get("Value") if fills else None,
                            scale_factor=umm.get("Scale"), add_offset=umm.get("Offset"),
                            definition=umm.get("Definition"),
                            concept_id=it["meta"]["concept-id"])
    return None


# ----------------------------------------------------------------------------- file header
def sample_file(dataset_key: str) -> Path | None:
    folder = C.RAW / dataset_key / "sample"
    files = sorted(p for p in folder.glob("*") if p.is_file()) if folder.exists() else []
    return files[0] if files else None


def file_header(dataset_key: str, name_in_file: str, group: str | None = None) -> dict | None:
    """Attributes of a variable read from a real downloaded file, or None if we have no file."""
    path = sample_file(dataset_key)
    if path is None:
        return None
    fmt = DATASETS[dataset_key].file_format
    if fmt == "HDF4":
        from pyhdf.SD import SD, SDC
        sd = SD(str(path), SDC.READ)
        try:
            a = sd.select(name_in_file).attributes()
        finally:
            sd.end()
        return dict(units=a.get("units"), fill_value=a.get("_FillValue"),
                    scale_factor=a.get("scale_factor"), add_offset=a.get("add_offset"),
                    long_name=a.get("long_name"), file=path.name)
    import h5py
    with h5py.File(path, "r") as f:
        key = f"{group}/{name_in_file}" if group else name_in_file
        if key not in f:
            raise SourceError(f"'{key}' is not in {path.name}")
        attrs = {k: (v.decode() if isinstance(v, bytes) else
                     (v.tolist() if hasattr(v, "tolist") else v)) for k, v in f[key].attrs.items()}

    def first(v):
        if isinstance(v, list):
            v = v[0] if v else None
        return v.decode() if isinstance(v, bytes) else v
    return dict(units=first(attrs.get("units") or attrs.get("Units")),
                fill_value=first(attrs.get("_FillValue")),
                scale_factor=first(attrs.get("scale_factor")),
                add_offset=first(attrs.get("add_offset")),
                long_name=first(attrs.get("long_name") or attrs.get("LongName")), file=path.name)


# ----------------------------------------------------------------------------- papers
def papers_catalog() -> dict[str, dict]:
    data = yaml.safe_load(PAPERS_YAML.read_text(encoding="utf-8")) or {}
    return {p["doi"].lower(): p for p in data.get("papers", [])}


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def paper_metadata(doi: str) -> dict:
    """Title, year and abstract. Abstract priority: papers.yaml (pasted by a human) ->
    Crossref -> OpenAlex."""
    doi = doi.lower().strip()
    cat = papers_catalog().get(doi, {})
    m = get_json(f"https://api.crossref.org/works/{doi}")["message"]
    title = (m.get("title") or [""])[0]
    year = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
    abstract, abs_source = (cat.get("abstract") or "").strip(), "papers.yaml (pasted by team)"
    if not abstract and m.get("abstract"):
        abstract, abs_source = _strip_tags(m["abstract"]), "Crossref"
    if not abstract:
        try:
            w = get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
            inv = w.get("abstract_inverted_index") or {}
            if inv:
                words = sorted(((pos, word) for word, ps in inv.items() for pos in ps))
                abstract, abs_source = " ".join(w_ for _, w_ in words), "OpenAlex"
        except SourceError:
            pass
    return dict(doi=doi, title=_strip_tags(title), year=year, abstract=abstract,
                abstract_source=abs_source if abstract else None,
                journal=(m.get("container-title") or [""])[0])


def normalise(text: str) -> str:
    t = text.lower().replace("‐", "-").replace("–", "-").replace("—", "-")
    t = re.sub(r"[“”\"'’`]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def quote_in_text(quote: str, text: str) -> bool:
    q = normalise(quote).strip(" .")
    return len(q) >= 20 and q in normalise(text)
