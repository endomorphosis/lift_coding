# Law schema register

Register for statute and national-law rows. An adapter reads these schemas and keeps the query shard lookup below. This file does not change the datasets checkout, the site checkout, or a query route.

Read on 2026-11-09. `external/ipfs_datasets` HEAD is `d40ab60649b83781e3849e191c1f2ac8545b042f`. The five dataset files below were clean against that HEAD. Site checkout HEAD is `d41cf3311478e1861d58387b0033065330744097`. The three site files below were clean against that HEAD.

## `country-laws-ir-graphrag/v1`

`ipfs_datasets_py/processors/legal_scrapers/country_laws_ir/__init__.py`, last changed in `9df09d3f50b80beebd5ae8bcd83cf72d034078c2`:

```python
SCHEMA_VERSION = "country-laws-ir-graphrag/v1"
```

The same file assigns `LAYOUT_FAMILY = "skillcenter-huggingface-release/v3"`. That string is not the statute schema. An adapter keeps `SCHEMA_VERSION` and does not store a statute row as the layout-family id.

Site pin in `worldwidelaws.github.io/src/lib/worldwide/data/identity.ts`, last changed in `8eade85b30bfd59f5f886eee0e2740ebf990f8fa`:

```ts
export const CORPUS_SCHEMA_VERSION = 'country-laws-ir-graphrag/v1';
```

## `country-laws-normalize-verify/v1`

`country_laws_ir/verify.py`, last changed in `9df09d3f50b80beebd5ae8bcd83cf72d034078c2`:

```python
SCHEMA_VERSION = "country-laws-normalize-verify/v1"
```

That module is the admission verifier before GraphRAG. Its `schema_version` field uses this string. It does not replace `country-laws-ir-graphrag/v1` on the package.

## Site law and article columns

`worldwidelaws.github.io/src/lib/worldwide/data/schema.ts`, last changed in `72211e93b7df2be38820cb7bf214ee1d56bebba5`:

```ts
export const SCHEMA_VERSION = 1;
export const LAW_SOURCE_SCHEMA = 'worldwide-legal-search.law-source@1';
export const LAW_SECTION_SCHEMA = 'worldwide-legal-search.law-section@1';
```

```ts
/** Column contract pinned to country_laws_ir/schema.py. Values are not invented. */
export const REQUIRED_LAW_COLUMNS = ['id', 'title', 'text'] as const;
export const REQUIRED_ARTICLE_COLUMNS = ['id', 'law_id', 'title', 'text'] as const;
```

Law columns, in order: `id`, `title`, `text`. Article columns, in order: `id`, `law_id`, `title`, `text`.

`country_laws_ir/schema.py`, last changed in `b560f8d60962277b09c12c44457b424de25de83b`, defines the same names in the same order:

```python
REQUIRED_LAW_COLUMNS = ("id", "title", "text")
REQUIRED_ARTICLE_COLUMNS = ("id", "law_id", "title", "text")
```

`scripts/worldwide/normalize.ts`, last changed in `8eade85b30bfd59f5f886eee0e2740ebf990f8fa`, repeats those two arrays as local constants:

```ts
const REQUIRED_LAW_COLUMNS = ['id', 'title', 'text'] as const;
const REQUIRED_ARTICLE_COLUMNS = ['id', 'law_id', 'title', 'text'] as const;
```

An adapter accepts a statute row only when those required columns are present, in that order of requirement. It does not drop a column the source row already has, and it does not invent a required name that these lists omit.

## Query shard functions the adapter keeps

`PLAN.md` says published `country_laws_ir/query.py` reads document shards through `duckdb_store.document_shard_paths` and falls back to `data/bm25/documents`. Adjacency uses `adjacency_shard_paths`. Adapters must not replace that lookup. Query shard lookup stays the published read path. It is not a new route.

`country_laws_ir/query.py` and `country_laws_ir/duckdb_store.py` were last changed in `d40ab60649b83781e3849e191c1f2ac8545b042f`.

`query.py` `bm25` returns `duckdb_store.bm25_search` when that call does not raise. The exception path calls `document_shard_paths`:

```python
        from .duckdb_store import document_shard_paths

        doc_rels = document_shard_paths(self.root, [int(di) for di, _score in ranked])
        if doc_rels is None:
            docs = self._read("data/bm25/documents")
```

`duckdb_store.py` defines the helper:

```python
def document_shard_paths(root: Path, document_indexes: list[int]) -> list[str] | None:
    """Document shards for these indexes, or None when the release has no document index."""
```

`bm25_search` calls that helper and, when it returns `None`, reads the DuckDB view `bm25_documents`:

```python
        doc_rels = document_shard_paths(root, [int(row[0]) for row in scored])
        docs_sql = (
            "bm25_documents"
            if doc_rels is None
            else f"read_parquet({_parquet_sql(root, doc_rels)})"
        )
```

That view is bound here:

```python
    ("bm25_documents", "data/bm25/documents/*.parquet"),
```

An empty list from `document_shard_paths` is not `None`. The `query.py` exception path then builds an empty frame and does not call `_read("data/bm25/documents")`. `bm25_search` returns `[]` when the keyword index exists and selects no posting shards, before it calls `document_shard_paths`.

`query.py` `neighbors` returns `duckdb_store.graph_neighbors` when that call does not raise. The exception path calls `adjacency_shard_paths`:

```python
        from .duckdb_store import adjacency_shard_paths

        for d in dirs:
            indexed = adjacency_shard_paths(self.root, node_cid, d)
            if indexed is None:
                path = self.root / "data" / "graph" / "adjacency" / d
                files = sorted(path.glob("*.parquet"))
```

On that path, `dirs` is `["incoming", "outgoing"]` when `direction` is `"both"`. The glob is under `data/graph/adjacency/incoming/` or `data/graph/adjacency/outgoing/`.

`duckdb_store.py` defines the helper:

```python
def adjacency_shard_paths(root: Path, node_cid: str, direction: str) -> list[str] | None:
    """Adjacency shards whose CID range contains this node, or None when unindexed."""
```

The helper maps direction `in` to index name `incoming` and `out` to `outgoing`, then opens `indexes/graph_{name}_adjacency.parquet`. It returns `None` when that file is missing.

`graph_neighbors` does not glob `data/graph/adjacency/*.parquet`. When its own index file is missing it reads a registered view. The views are:

```python
    ("graph_in", "data/graph/adjacency/in/*.parquet"),
    ("graph_out", "data/graph/adjacency/out/*.parquet"),
    # Legacy country-laws-ir layout still on some Hub packs.
    ("graph_incoming", "data/graph/adjacency/incoming/*.parquet"),
    ("graph_outgoing", "data/graph/adjacency/outgoing/*.parquet"),
```

The adapter keeps both helpers and this call order. It does not replace `document_shard_paths` or `adjacency_shard_paths` with a new route, a flat adjacency glob, or a single shared column list.

## Drift from LCM-001

LCM-001 recorded two mismatches with `PLAN.md`. Both are still true in the files above.

`PLAN.md` says adjacency falls back to `data/graph/adjacency/*.parquet` only when the index is `None`. The `None` condition still matches `query.py` (`indexed is None`) and `graph_neighbors` (the view branch runs when its index file is missing). The flat glob does not. No line in `query.py` or `duckdb_store.py` is `data/graph/adjacency/*.parquet`. The exception path globs `data/graph/adjacency/<direction>/*.parquet` with `incoming` or `outgoing`. `graph_neighbors` reads the four subdirectory views above.

`PLAN.md` does not mention that `bm25` and `neighbors` return `bm25_search` and `graph_neighbors` before those direct helpers run. The helpers still run inside those functions, and again on the exception paths quoted above.

One further difference sits in the same `duckdb_store.py` and was not spelled out by LCM-001. `graph_neighbors` gates the helper on this index map:

```python
            index_name = {
                "in": "graph_in_adjacency.parquet",
                "out": "graph_out_adjacency.parquet",
                "incoming": "graph_incoming_adjacency.parquet",
                "outgoing": "graph_outgoing_adjacency.parquet",
            }.get(d)
```

`adjacency_shard_paths` then renames `in` to `incoming` and `out` to `outgoing` before it opens `indexes/graph_{name}_adjacency.parquet`. For directions `in` and `out`, the gate file and the helper file are different names. An adapter keeps both maps. It does not collapse them into one filename.
