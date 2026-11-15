"""Graph storage with the schema enforced on every write (Contract 0).

Two backends with the same interface:
- Neo4jStore: the live graph (Neo4j Desktop / Docker on our laptop).
- JsonStore: graph.json snapshot, used as backup and when Neo4j is not running.

Every node gets the extra label :Entity and a unique `id`, and is written with MERGE,
so the same thing can never exist twice.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml

from common import config as C

log = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).with_name("schema.yaml")


class SchemaError(ValueError):
    """A write that does not respect Contract 0. The message explains what is wrong."""


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(props: dict[str, Any]) -> dict[str, Any]:
    """Neo4j properties must be primitives or lists of primitives: dicts become JSON strings."""
    out = {}
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, dict) or (isinstance(v, list) and any(isinstance(x, (dict, list))
                                                               for x in v)):
            out[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, tuple):
            out[k] = list(v)
        else:
            out[k] = v
    return out


class GraphStore:
    """Schema checks shared by both backends. Subclasses implement the _raw methods."""
    backend = "abstract"

    # ------------------------------------------------------------------ validation
    def _check_node(self, label: str, node_id: str, props: dict, status: str, created_by: str):
        sch = load_schema()
        if label not in sch["nodes"]:
            raise SchemaError(f"Node label '{label}' is not in the schema. Allowed: "
                              f"{', '.join(sch['nodes'])}.")
        spec = sch["nodes"][label]
        reserved = {"label", "id"} & set(props)
        if reserved:
            raise SchemaError(f"Property names {sorted(reserved)} are reserved by the store.")
        if not node_id.startswith(spec["id_prefix"]):
            raise SchemaError(f"{label} ids must start with '{spec['id_prefix']}' (got '{node_id}').")
        missing = [p for p in spec["required"] if props.get(p) in (None, "", [])]
        if missing:
            raise SchemaError(f"{label} '{node_id}' is missing required properties: {missing}.")
        if status not in sch["statuses"]:
            raise SchemaError(f"status must be one of {sch['statuses']}.")
        if created_by not in sch["creators"]:
            raise SchemaError(f"created_by must be one of {sch['creators']}.")
        if label == "Hypothesis" and status != "hypothesis":
            raise SchemaError("A Hypothesis node must always have status 'hypothesis'.")

    def _check_rel(self, src: dict, rel: str, dst: dict, props: dict):
        sch = load_schema()
        if rel not in sch["relationships"]:
            raise SchemaError(f"Relationship '{rel}' is not in the schema. Allowed: "
                              f"{', '.join(sch['relationships'])}.")
        spec = sch["relationships"][rel]
        if src["label"] not in spec["from"] or dst["label"] not in spec["to"]:
            raise SchemaError(f"{rel} must go from {spec['from']} to {spec['to']} "
                              f"(got {src['label']} -> {dst['label']}).")
        missing = [p for p in spec.get("required", []) if props.get(p) in (None, "", [])]
        if missing:
            raise SchemaError(f"{rel} is missing required properties: {missing}.")

    # ------------------------------------------------------------------ public API
    def merge_node(self, label: str, node_id: str, props: dict, *, source: str,
                   created_by: str, status: str = "verified", confidence: float = 1.0) -> dict:
        self._check_node(label, node_id, props, status, created_by)
        meta = dict(source=source, created_by=created_by, status=status,
                    confidence=float(confidence), updated_at=now())
        existing = self.get(node_id)
        if existing and existing["label"] != label:
            raise SchemaError(f"'{node_id}' already exists as a {existing['label']}.")
        if not existing:
            meta["created_at"] = meta["updated_at"]
        return self._merge_node_raw(label, node_id, _clean({**props, **meta}))

    def merge_rel(self, src_id: str, rel: str, dst_id: str, props: dict | None = None, *,
                  source: str, created_by: str, status: str = "verified",
                  confidence: float = 1.0) -> dict:
        props = props or {}
        src, dst = self.get(src_id), self.get(dst_id)
        if src is None:
            raise SchemaError(f"Node '{src_id}' does not exist (create it first).")
        if dst is None:
            raise SchemaError(f"Node '{dst_id}' does not exist (create it first).")
        self._check_rel(src, rel, dst, props)
        meta = dict(source=source, created_by=created_by, status=status,
                    confidence=float(confidence), updated_at=now())
        return self._merge_rel_raw(src_id, rel, dst_id, _clean({**props, **meta}))

    def search(self, label: str | None, text: str, limit: int = 10) -> list[dict]:
        """Case-insensitive match on id / name / display_name / synonyms / code_id."""
        t = text.lower().strip()
        out = []
        for n in self.nodes(label):
            hay = [str(n.get(k, "")).lower() for k in ("id", "name", "display_name", "code_id",
                                                        "short_name", "title", "name_in_file")]
            syn = n.get("synonyms") or []
            if isinstance(syn, str):
                syn = [syn]
            hay += [str(s).lower() for s in syn]
            if any(t and (t in h or (len(h) > 2 and h in t)) for h in hay if h):
                out.append(n)
        return out[:limit]

    def counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for n in self.nodes():
            c[n["label"]] = c.get(n["label"], 0) + 1
        c["_relationships"] = len(self.rels())
        return c

    def export_json(self, path: Path = C.GRAPH_JSON) -> Path:
        data = {"exported_at": now(), "backend": self.backend,
                "nodes": self.nodes(), "relationships": self.rels()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str),
                        encoding="utf-8")
        return path

    def import_json(self, path: Path = C.GRAPH_JSON) -> int:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for n in data["nodes"]:
            n = dict(n)
            label = n.pop("label")
            self._merge_node_raw(label, n.pop("id"), _clean(n))
        for r in data["relationships"]:
            r = dict(r)
            self._merge_rel_raw(r.pop("src"), r.pop("type"), r.pop("dst"), _clean(r))
        return len(data["nodes"])

    # ------------------------------------------------------------------ to implement
    def _merge_node_raw(self, label, node_id, props) -> dict: raise NotImplementedError
    def _merge_rel_raw(self, src, rel, dst, props) -> dict: raise NotImplementedError
    def get(self, node_id: str) -> dict | None: raise NotImplementedError
    def nodes(self, label: str | None = None) -> list[dict]: raise NotImplementedError
    def rels(self, rel: str | None = None) -> list[dict]: raise NotImplementedError
    def out(self, node_id: str, rel: str | None = None) -> list[tuple[dict, dict]]: raise NotImplementedError
    def inc(self, node_id: str, rel: str | None = None) -> list[tuple[dict, dict]]: raise NotImplementedError
    def delete_node(self, node_id: str) -> None: raise NotImplementedError
    def clear(self) -> None: raise NotImplementedError
    def close(self) -> None: pass


# ============================================================================ Neo4j
class Neo4jStore(GraphStore):
    backend = "neo4j"

    def __init__(self, uri=C.NEO4J_URI, user=C.NEO4J_USER, password=C.NEO4J_PASSWORD,
                 database=C.NEO4J_DATABASE):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password),
                                           connection_timeout=5, max_transaction_retry_time=5,
                                           notifications_min_severity="OFF")
        self.driver.verify_connectivity()
        self.database = database
        self._ensure_constraints()

    def _run(self, q: str, **params) -> list[dict]:
        records, _, _ = self.driver.execute_query(q, params, database_=self.database)
        return [r.data() for r in records]

    def _ensure_constraints(self):
        self._run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE")
        for label in load_schema()["nodes"]:
            self._run(f"CREATE INDEX {label.lower()}_id IF NOT EXISTS FOR (n:{label}) ON (n.id)")

    @staticmethod
    def _node(record: dict) -> dict:
        n = dict(record["props"])
        n["label"] = next(l for l in record["labels"] if l != "Entity")
        return n

    def _merge_node_raw(self, label, node_id, props):
        # label was validated against the schema, so it is safe to put in the query text
        rows = self._run(f"MERGE (n:Entity {{id: $id}}) SET n:{label}, n += $props "
                         "RETURN properties(n) AS props, labels(n) AS labels",
                         id=node_id, props=props)
        return self._node(rows[0])

    def _merge_rel_raw(self, src, rel, dst, props):
        rows = self._run(f"MATCH (a:Entity {{id: $a}}), (b:Entity {{id: $b}}) "
                         f"MERGE (a)-[r:{rel}]->(b) SET r += $props RETURN properties(r) AS p",
                         a=src, b=dst, props=props)
        if not rows:
            raise SchemaError(f"Could not link {src} -> {dst}.")
        return {"src": src, "type": rel, "dst": dst, **rows[0]["p"]}

    def get(self, node_id):
        rows = self._run("MATCH (n:Entity {id: $id}) RETURN properties(n) AS props, "
                         "labels(n) AS labels", id=node_id)
        return self._node(rows[0]) if rows else None

    def nodes(self, label=None):
        q = (f"MATCH (n:{label}) " if label else "MATCH (n:Entity) ") + \
            "RETURN properties(n) AS props, labels(n) AS labels ORDER BY n.id"
        if label and label not in load_schema()["nodes"]:
            return []
        return [self._node(r) for r in self._run(q)]

    def rels(self, rel=None):
        if rel and rel not in load_schema()["relationships"]:
            return []
        pat = f"[r:{rel}]" if rel else "[r]"
        rows = self._run(f"MATCH (a:Entity)-{pat}->(b:Entity) RETURN a.id AS src, type(r) AS type, "
                         "b.id AS dst, properties(r) AS p")
        return [{"src": r["src"], "type": r["type"], "dst": r["dst"], **r["p"]} for r in rows]

    def _nbr(self, node_id, rel, direction):
        if rel and rel not in load_schema()["relationships"]:
            return []
        pat = f"[r:{rel}]" if rel else "[r]"
        arrow = f"-{pat}->" if direction == "out" else f"<-{pat}-"
        rows = self._run(f"MATCH (a:Entity {{id: $id}}){arrow}(b:Entity) RETURN properties(r) AS rp, "
                         "type(r) AS type, properties(b) AS props, labels(b) AS labels", id=node_id)
        return [({"type": r["type"], **r["rp"]}, self._node(r)) for r in rows]

    def out(self, node_id, rel=None):
        return self._nbr(node_id, rel, "out")

    def inc(self, node_id, rel=None):
        return self._nbr(node_id, rel, "in")

    def delete_node(self, node_id):
        self._run("MATCH (n:Entity {id: $id}) DETACH DELETE n", id=node_id)

    def clear(self):
        self._run("MATCH (n:Entity) DETACH DELETE n")

    def cypher(self, query: str, **params) -> list[dict]:
        """Read-only Cypher for the Graph page and documentation examples."""
        return self._run(query, **params)

    def close(self):
        self.driver.close()


# ============================================================================ JSON
class JsonStore(GraphStore):
    backend = "json"

    def __init__(self, path: Path | None = C.GRAPH_JSON, autosave: bool = True):
        self.path = Path(path) if path else None
        self.autosave = autosave and self.path is not None
        self._nodes: dict[str, dict] = {}
        self._rels: dict[tuple[str, str, str], dict] = {}
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for n in data.get("nodes", []):
                self._nodes[n["id"]] = dict(n)
            for r in data.get("relationships", []):
                self._rels[(r["src"], r["type"], r["dst"])] = dict(r)

    def _save(self):
        if self.autosave:
            self.export_json(self.path)

    def _merge_node_raw(self, label, node_id, props):
        n = self._nodes.setdefault(node_id, {"id": node_id})
        n["label"] = label
        n.update(props)
        self._save()
        return dict(n)

    def _merge_rel_raw(self, src, rel, dst, props):
        r = self._rels.setdefault((src, rel, dst), {"src": src, "type": rel, "dst": dst})
        r.update(props)
        self._save()
        return dict(r)

    def get(self, node_id):
        n = self._nodes.get(node_id)
        return dict(n) if n else None

    def nodes(self, label=None):
        return [dict(n) for k, n in sorted(self._nodes.items())
                if label is None or n["label"] == label]

    def rels(self, rel=None):
        return [dict(r) for r in self._rels.values() if rel is None or r["type"] == rel]

    def out(self, node_id, rel=None):
        return [({k: v for k, v in r.items() if k not in ("src", "dst")}, dict(self._nodes[d]))
                for (s, t, d), r in self._rels.items()
                if s == node_id and (rel is None or t == rel) and d in self._nodes]

    def inc(self, node_id, rel=None):
        return [({k: v for k, v in r.items() if k not in ("src", "dst")}, dict(self._nodes[s]))
                for (s, t, d), r in self._rels.items()
                if d == node_id and (rel is None or t == rel) and s in self._nodes]

    def delete_node(self, node_id):
        self._nodes.pop(node_id, None)
        self._rels = {k: v for k, v in self._rels.items() if node_id not in (k[0], k[2])}
        self._save()

    def clear(self):
        self._nodes, self._rels = {}, {}
        self._save()


# ============================================================================ factory
def get_store(prefer: str = "neo4j", json_path: Path = C.GRAPH_JSON) -> GraphStore:
    """Neo4j if it is reachable, otherwise the graph.json snapshot (with a warning)."""
    if prefer == "neo4j":
        try:
            return Neo4jStore()
        except Exception as e:  # noqa: BLE001 - any connection problem -> fallback
            log.warning("Neo4j not reachable (%s) - using %s instead", e.__class__.__name__,
                        json_path)
    return JsonStore(json_path)


def parse_json_prop(v: Any) -> Any:
    """Undo _clean() for properties stored as JSON strings."""
    if isinstance(v, str) and v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def iter_ids(items: Iterable[dict]) -> list[str]:
    return [i["id"] for i in items]
