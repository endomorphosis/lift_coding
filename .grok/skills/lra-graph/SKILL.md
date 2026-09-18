---
name: lra-graph
description: LRA board-graph traversal, GraphRAG search, and milles neural message-passing. Use for GraphRAG, BFS/DFS, GNN-style reasoning, or CALL ptr://skill/port_{graph_traverse,graphrag,neural_graph}. Never writes Lean.
---

# LRA graph skills

`harness/nca_graph.py`.

- **`port_graph_traverse`** — BFS (default) or DFS on `board_edges`, max 4 hops.
- **JSON-LD first.** Canonical graph is `@context` + `@graph` (`nca_jsonld.py`). DuckDB is an optional adapter (`ingest_duckdb` / `query_duckdb`), never a required import for traverse/GraphRAG/neural-graph.
- **`port_graphrag`** — search JSON-LD, then KG/AST/rg. Pass `duckdb_path` only to project JSON-LD into a sidecar. Hits are not lake admits.
- **`port_neural_graph`** — integer 2-hop sum of neighbor energy milles. Not CUDA.

Jev does not write Lean. Never docker0. Not Arena scores.
