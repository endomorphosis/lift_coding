# Legal corpus module contracts

Board namespace: `legal-corpus-modules-v1`.

This file freezes the contracts an implementation worker must preserve. Inventory tasks confirm these facts against the tree. A mismatch is recorded as drift. It is not silently corrected inside the inventory.

Training checkout: `/home/barberb/lift_coding/external/ipfs_datasets`, published tip `d40ab60649b83781e3849e191c1f2ac8545b042f`. Legal edits belong in that checkout. Nested copies of `ipfs_datasets_py` are not the training tree.

Other tips recorded when this plan was written, and left unchanged by the plan itself:

- `lift_coding` `38dddb4e77491c3df6fc762040759565cfcdaf60`
- `worldwidelaws.github.io` `d41cf331`
- `external/ipfs_accelerate` `6894544768d25aa83f49ff3d463e2b03520b9911`
- live supervisor framework checkout `e1675386d` at `/home/barberb/.local/state/ipfs_accelerate_py/worldwide-legal-search-v1/framework`

## What versioning means here

An instrument kind is a module with a stable interface id and a schema version. An ingest adapter names the source dataset schema it reads and emits rows that still validate as that source schema. A display module names the interface versions it can render. A newer version is a new id or a new version string. Old ids keep their column order and their meaning.

The shared interface to add is `legal-corpus.instrument@1` in a new module, `legal_corpus/instrument_v1.py`. It does not replace `legal_corpus/interfaces.py`. Jurisdiction registration, `LawStatus`, and `StatusMetadata` stay the status vocabulary. `legal-corpus.status@1` pins that vocabulary; it does not add a second list of status words.

`world_law/document_role.py` stays a row label. `ROLES` is `law`, `metadata`, and `informative`. `classify_document_role` returns `(role, reason)` and does not drop or rewrite text. Instrument kind is a second axis. A law-labeled row can still be a statute, a regulation, a legislative act, or another kind. Kind classification must not be implemented by changing `ROLES`.

## Source schemas that stay authoritative

Statute and national law rows already used by search:

- `country_laws_ir` `SCHEMA_VERSION` `country-laws-ir-graphrag/v1` in `country_laws_ir/__init__.py`.
- `country_laws_ir/verify.py` `SCHEMA_VERSION` `country-laws-normalize-verify/v1`.
- Site corpus pin `CORPUS_SCHEMA_VERSION` `country-laws-ir-graphrag/v1` in `worldwidelaws.github.io/src/lib/worldwide/data/identity.ts`.
- Site law rows: `SCHEMA_VERSION` `1`, `worldwide-legal-search.law-source@1`, and `worldwide-legal-search.law-section@1` in `src/lib/worldwide/data/schema.ts`. Required law columns pinned there are `id`, `title`, and `text`. Required article columns are `id`, `law_id`, `title`, and `text`.
- Published `country_laws_ir/query.py` reads document shards through `duckdb_store.document_shard_paths` and falls back to `data/bm25/documents`. Adjacency uses `adjacency_shard_paths` and falls back to `data/graph/adjacency/*.parquet` only when the index is `None`. Adapters must not replace that lookup.

Municipal HTML rows:

- `world_municipal/schema.py` `EXPECTED_COLUMNS`, 19 names in this order: `cid`, `jurisdiction_id`, `jurisdiction_name`, `country`, `doc_id`, `regeling_id`, `regeling_work_id`, `doc_order`, `title`, `structural_path`, `node_label`, `html_title`, `html`, `text`, `source_url`, `xml_url`, `date_effective`, `date_modified`, `retrieved`.
- `doc_order` is the only non-string column (`uint32`). Writers serialize a missing value as `""`. A NULL is a validation failure.
- Country provenance columns are appended after column 19. They are not inserted into the 19.

World law pipeline rows:

- `hub_integrated/world_law_pipeline/schema.py` `SCHEMA_VERSION` `1.2.0`. Version note in that file: `1.1.0` appended optional provenance columns and `extra_metadata`; `1.2.0` appended `pdf_ref`.
- `REPO_ID` `endomorphosis/world_municipal_law`. `NATIONAL_REPO_ID` `endomorphosis/world_national_law`. `PDF_REPO_ID` `endomorphosis/world_law_scanned_pdfs`.
- `NATIONAL_LEVELS` is `country`, `adm1`, `supranational`. `is_national_key` is true when the place key starts with `iso_`.
- `DOC_TYPES` is `code_section`, `ordinance`, `regulation`, `statute`, `gazette_act`, `decision`. That tuple is the pipeline's own vocabulary. `decision` is not caselaw unless the source register says so for that dataset. Adapters store the source `DOC_TYPES` value unchanged.

Caselaw, regulations, legislative acts, and courts are not one shared table:

- Caselaw sources already in the tree include `caselaw_access_program`, France DILA (`collect_fr_dila`, which does not replace `collect_legi`), Germany Rechtsprechung im Internet (`collect_de_rii`, which does not replace `collect_gii`), and `recap_archive_scraper`. `endomorphosis/world_caselaw` is a separate corpus from national statute routes.
- Regulation sources include `federal_scrapers` CFR, eCFR, and Federal Register processors, `regulation_version_tracker.py`, and `state_admin_rules_scraper.py`. A regulation adapter cites those schemas. It does not store a regulation as a `country-laws-ir-graphrag/v1` statute.
- Legislative acts are instruments such as a gazette act or a public law before consolidation. US Code scraping (`us_code_scraper.py`, `uscode_release_processor.py`) stays on the law kind. It is not relabeled as a legislative act.
- Courts are institutions. A court module identifies the body that issued an opinion or a rule. It is not an opinion schema and not a statute schema.

Outliers that stay outside this interface:

- Hub copies `justicedao__ipfs_argentina_laws-ir` and `justicedao__ipfs_malta_laws-ir` use `SCHEMA_VERSION` `skillcenter-huggingface-release/v3`. They are not `country-laws-ir-graphrag/v1`.
- Intent IR and the legal-IR autoencoder are separate training lanes. They are not ingested by these adapters.
- `external/ipfs_datasets-feature-freeze` is not a source and is not committed.

## Duplicate trees

These trees repeat scrapers and must stop being treated as independent schemas. The first implementation adds a canonical module and a boundary record. It does not delete the copies.

- `hub_dataset_scripts`
- `hub_integrated/justicedao_world_law_scrapers`
- `hub_integrated/legal_scrapers`
- `hub_integrated/world_law_pipeline`
- `international/harvested`
- `national_collectors` and `national_campaigns` (collectors stay the catalog of national entry points; copies of their schemas do not)
- `state_scrapers`
- `world_municipal_campaigns`
- `municipal`

Seventeen files under `hub_integrated/legal_scrapers/` are named `.py` and are notes whose first line is `linked logs/...`. They are not importable Python. Quarantine them in the module map. Do not rewrite them as scrapers and do not pretend `py_compile` accepts them. The names are `al_alfresco_tip26b.py`, `al_close_tip26b.py`, `az_cdx_extra_tip26f.py`, `az_live_gap_tip24o.py`, `az_live_gap_tip26f.py`, `bo_live_cdx_miss_tip26m.py`, `bo_live_failures_tip26a.py`, `bo_live_failures_tip26b.py`, `ir_media_recent_tip25q.py`, `ir_media_recent_tip26b.py`, `ir_media_recent_tip26n.py`, `mw_akn_miss_tip25m.py`, `mw_akn_miss_tip26b.py`, `mw_akn_miss_tip26n.py`, `mw_extra_akn_tip25p.py`, `mw_extra_akn_tip26b.py`, and `mw_extra_akn_tip26m.py`.

## Display modules

The site already versions place and statute display. New kind views are new schema ids. They do not reuse a statute id for an opinion or a docket.

Pinned site contracts:

- `src/lib/worldwide/data/schema.ts`: `SCHEMA_VERSION` `1`, `worldwide-legal-search.law-source@1`, `worldwide-legal-search.law-section@1`, `worldwide-legal-search.quarantine@1`.
- `src/lib/worldwide/jurisdiction/schema.ts`: `SCHEMA_VERSION` `1`, `worldwide-legal-search.jurisdiction-graph@1` and the node, edge, disputed-view, unknown-relationship, and jurisdiction-quarantine ids in that file. Applicability stays `not-asserted`. This graph does not resolve caller coordinates.
- `scripts/worldwide/refresh.ts` and `scripts/worldwide/update.ts`: `SCHEMA_VERSION` `1`.

A search of `swissknife/web/js/apps` found no legal-instrument schema version. SwissKnife display work adds a new package that imports the same interface ids. It does not claim an existing app already versions caselaw or courts.

Each display module exports the interface versions it can render and refuses an unknown version. The query input stays an explicit place. No display module reads caller IP. No display module implements GEOIP.

## Documentation rule

Docs that describe the reorganized tree are written after the code they describe is in the tree. The writer reads the landed `SCHEMA_VERSION`, column list, and file path, and quotes those. A doc that still describes a path or version the file does not export is not done.

Existing reports such as `FINAL_PROJECT_REPORT.md`, `PROJECT_COMPLETE.md`, and the Brave, Hugging Face, and complaint-analysis notes stay in place until a documentation task marks them as historical. They are not deleted as part of an inventory.

`docs/worldwide/supervisor-operations.md` on the site checkout is an unrelated dirty file. This plan does not edit it.

## Standing limits

These limits are inherited from the legal datasets and the finished search campaign. No task in this package removes them.

- Query input is an explicit place, not the caller IP. Do not implement GEOIP. Do not widen the query catalog.
- Belgium, Portugal, Lithuania, and Ghana national routes stay closed. Egypt governorates, South Africa provinces, and Wallis and Futuna stay unpublished.
- `collect_fr_dila` does not replace `collect_legi`. `collect_de_rii` does not replace `collect_gii`. `collect_additions` does not open a query route.
- Do not flip `LEGAL_QUERY_NORMALIZED`. Do not mark pins searchable. Do not upload an older national-fill tree over the norm tip.
- Do not rebuild Germany GraphRAG `justicedao/ipfs_germany_laws_ir` revision `452729c915ee`.
- Do not start Romania GraphRAG while caselaw vector work holds `cuda:0`.
- A dataset is law only with `laws.parquet`, non-HTML `laws-*.parquet` shards, or the 19-column HTML scraper schema.
- Do not commit span-score shards, modal-IR shards, cursors, parquet corpora, secrets, or the feature-freeze directory.
- Do not reset the live worldwide supervisor checkout, restart a healthy supervisor, restart `worldwide-legal-search-watchdog.service`, or reset its incidents.
- Do not admit these tasks into the `worldwide-legal-search-v1` DuckDB board. Do not mark a worldwide task complete from this plan.

## Authorization

New modules, registers, tests, and docs that only add files are the implementation work described here. Deleting a duplicate tree, rewriting a published scraper in place, renumbering `law-source@1`, or opening a closed national route needs a separate named go-ahead. Tasks say which of those they are.
