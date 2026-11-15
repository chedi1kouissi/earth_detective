# Cypher equivalents of the graph paths (Document 2, sections 8.5 and 9.4)

`graph/queries.py` implements these paths once on top of the store interface, so they work on Neo4j
and on the `graph.json` fallback. Run these in Neo4j Browser (http://localhost:7474) or on the app's
**Graph → Cypher** tab.

## 1 · Understand: concepts matching the question
```cypher
MATCH (c:Concept)
WHERE c.status IN ['verified','from_paper']
  AND any(t IN [c.name] + c.synonyms WHERE $question CONTAINS t)
RETURN c.name, c.synonyms
```

## 2 · Plan: concept → variables → datasets → recipe → chart style
```cypher
MATCH (c:Concept)<-[r:INDICATOR_OF]-(v:Variable)-[:IN_DATASET]->(d:Dataset)
WHERE c.name IN $concepts AND v.status = 'verified'
OPTIONAL MATCH (v)-[:DRAWN_AS]->(cs:ChartStyle)
RETURN v.display_name, v.definition_for_students, r.reason,
       v.name_in_file, v.unit_native, v.unit_target, v.conversion,
       d.short_name, d.version, d.doi, cs.id
```

## 2 · Plan: the method chain
```cypher
MATCH p = (m:Method)-[:NEXT*]->(:Method)
WHERE NOT ()-[:NEXT]->(m)
RETURN [n IN nodes(p) | n.name] AS chain
ORDER BY length(p) DESC LIMIT 1
```

## 2 · Plan: the region and its sub-regions
```cypher
MATCH (s:Region)-[:PART_OF]->(r:Region {code_id: $region})
RETURN r.bbox, collect(s.name) AS sub_regions
```

## 4 · Record: what one investigation produced
```cypher
MATCH (i:Investigation {id: $id})-[:PRODUCED]->(f:Finding)-[:ABOUT]->(v:Variable)
RETURN v.display_name, f.slope_per_decade, f.p, f.region, f.period
```

## 5 · Why?: literature paths between two findings (pattern co_trend_literature)
```cypher
MATCH (fa:Finding)-[:ABOUT]->(a:Variable)-[i:INFLUENCES]->(b:Variable)<-[:ABOUT]-(fb:Finding)
WHERE fa.region = fb.region AND fa.period = fb.period
MATCH (p:Paper {id: i.paper_id})
RETURN a.display_name, i.sign, b.display_name, i.quote, p.title, p.year
```

## 5 · Why?: opposite trends between sub-regions
```cypher
MATCH (up:Finding)-[:OPPOSITE_OF]->(down:Finding)
RETURN up.variable, up.region, up.slope_per_decade, down.region, down.slope_per_decade
```

## Hypotheses and the evidence behind them
```cypher
MATCH (f:Finding)-[:SUGGESTS]->(h:Hypothesis)-[:VIA_PATTERN]->(p:HypothesisPattern)
RETURN h.text, p.name, collect(f.summary) AS based_on
```

## Provenance of a finding
```cypher
MATCH (f:Finding)-[:FROM_ANALYSIS]->(a:Analysis), (f)-[:ABOUT]->(v)-[:IN_DATASET]->(d)
RETURN f.summary, a.run_id, a.methods, d.short_name, d.version, d.doi
```
