# Legal corpus modules task bootstrap

Bootstrap status is `todo`. That is not live progress. Do not copy these ids into the `worldwide-legal-search-v1` DuckDB board. `PLAN.md` wins when a task and this file disagree about a schema. `PARALLEL.md` says which tasks may run together.

Write scopes are the only paths a task may create or edit. A task leaves every other dirty file alone, including `docs/worldwide/supervisor-operations.md`, the SwissKnife media-player dirt, and the SVF-1040 board line.

## LCM-000 Record the pre-refactor baseline
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S1
- Track: inventory
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-000.md
- Authorization: read-only against source repos
- Acceptance: Record `external/ipfs_datasets` `d40ab60649b83781e3849e191c1f2ac8545b042f`, site `d41cf331`, `lift_coding` `38dddb4e77`, `external/ipfs_accelerate` `689454476`, and the framework checkout revision at `/home/barberb/.local/state/ipfs_accelerate_py/worldwide-legal-search-v1/framework`. List unrelated dirty paths without reverting them. State that this plan is not a live campaign.
- Must not: commit, push, reset a checkout, or admit tasks to DuckDB

## LCM-001 Inventory statute and national-law schemas
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-law
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-001.md
- Authorization: read-only
- Acceptance: Quote `country-laws-ir-graphrag/v1`, `country-laws-normalize-verify/v1`, site `REQUIRED_LAW_COLUMNS`, site `REQUIRED_ARTICLE_COLUMNS`, and the `query.py` shard helpers from the files that define them. Record any line that no longer matches `PLAN.md`.
- Must not: edit `country_laws_ir`, widen the catalog, or treat query shard lookup as a new route

## LCM-002 Inventory municipal HTML and pipeline schemas
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-municipal
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-002.md
- Authorization: read-only
- Acceptance: Quote `EXPECTED_COLUMNS` in order, the `doc_order` uint32 rule, the empty-string rule, pipeline `SCHEMA_VERSION` `1.2.0`, `DOC_TYPES`, `REPO_ID`, `NATIONAL_REPO_ID`, and `is_national_key`. Note that `decision` is not caselaw by default.
- Must not: reorder the 19 columns or edit pipeline schema code

## LCM-003 Inventory caselaw sources
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-caselaw
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-003.md
- Authorization: read-only
- Acceptance: Name the schema or column contract actually used by `caselaw_access_program`, `collect_fr_dila`, `collect_de_rii`, `recap_archive_scraper`, and `endomorphosis/world_caselaw` if a local contract exists. State that DILA does not replace `collect_legi` and Rechtsprechung im Internet does not replace `collect_gii`. Record sources that have no version string instead of inventing one.
- Must not: start a GraphRAG build, use `cuda:0`, or merge these sources into one schema

## LCM-004 Inventory regulation sources
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-regulation
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-004.md
- Authorization: read-only
- Acceptance: Name the column or record contract in the CFR, eCFR, Federal Register, `regulation_version_tracker.py`, and state admin-rules scrapers. Keep each source schema distinct from `country-laws-ir-graphrag/v1`.
- Must not: relabel a regulation row as a statute

## LCM-005 Inventory legislative-act sources
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-acts
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-005.md
- Authorization: read-only
- Acceptance: Separate gazette acts and public-law processors from US Code consolidation. Quote the file that makes that difference. List national collectors that fetch acts without opening a new query route.
- Must not: classify `us_code_scraper.py` as a legislative-act schema

## LCM-006 Inventory court identity sources
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S2
- Track: inventory-courts
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-006.md
- Authorization: read-only
- Acceptance: List fields that identify a court as an institution in caselaw and docket sources. State that a court record is not an opinion and not a statute. If a source has no court table, say so.
- Must not: invent a court ontology that the files do not contain

## LCM-007 Map duplicate trees, note files, and outliers
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S3
- Track: inventory-copies
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-007.md
- Authorization: read-only
- Acceptance: For each tree named in `PLAN.md`, record whether it vendors a schema, repeats a collector, or both. Confirm the 17 `linked logs` note filenames and the two `skillcenter-huggingface-release/v3` copies. Do not compile the notes into a success claim.
- Must not: delete, rename, or reformat those files

## LCM-008 Inventory display versions
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S3
- Track: inventory-ui
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-008.md
- Authorization: read-only
- Acceptance: Quote site `law-source@1`, `law-section@1`, jurisdiction schema ids, and `CORPUS_SCHEMA_VERSION`. Search SwissKnife for a legal instrument view. Record that `web/js/apps` had no such version when this plan was written, or quote the file if one has appeared.
- Must not: edit the site, SwissKnife, or the visual-functional board

## LCM-009 Inventory docs that describe the current tree
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S3
- Track: inventory-docs
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-009.md
- Authorization: read-only
- Acceptance: List markdown under `legal_scrapers` and `docs/legal` that names a schema version, a column layout, or a package path. Mark which of those would become stale after the new modules land. Do not rewrite them in this task.
- Must not: edit `docs/worldwide/supervisor-operations.md` or the 2026-10-21 refresh plan except to cite it

## LCM-010 Write the law schema register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-law
- Depends on: LCM-001
- Write scope: implementation_plan/legal_corpus_modules/registers/law.md
- Authorization: new register file only
- Acceptance: Name `country-laws-ir-graphrag/v1` and `country-laws-normalize-verify/v1`, the site law and article columns, and the query shard functions the adapter must keep. Include drift from LCM-001.
- Must not: change the datasets checkout

## LCM-011 Write the municipal and pipeline register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-municipal
- Depends on: LCM-002
- Write scope: implementation_plan/legal_corpus_modules/registers/municipal.md
- Authorization: new register file only
- Acceptance: Repeat the 19 column names in order, the append-only extra-column rule, pipeline `1.2.0`, and `DOC_TYPES` as source labels. Say which labels map to law, regulation, act, or "not yet classified".
- Must not: map `decision` to caselaw without a source citation from LCM-003

## LCM-012 Write the caselaw schema register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-caselaw
- Depends on: LCM-003
- Write scope: implementation_plan/legal_corpus_modules/registers/caselaw.md
- Authorization: new register file only
- Acceptance: One section each for CAP, DILA, Rechtsprechung im Internet, RECAP, and world caselaw. Each section has a schema id taken from that source or `unversioned` plus the columns that were actually read.
- Must not: assign one shared column order to all five

## LCM-013 Write the regulation schema register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-regulation
- Depends on: LCM-004
- Write scope: implementation_plan/legal_corpus_modules/registers/regulation.md
- Authorization: new register file only
- Acceptance: One section per regulation source from LCM-004, with the version or record fields that source already uses.
- Must not: reuse `worldwide-legal-search.law-source@1` as the regulation id

## LCM-014 Write the legislative-act schema register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-acts
- Depends on: LCM-005
- Write scope: implementation_plan/legal_corpus_modules/registers/legislative-act.md
- Authorization: new register file only
- Acceptance: List act-shaped sources and explicitly exclude US Code consolidation. Cite `gazette_act` as a pipeline `DOC_TYPES` value that still needs a per-dataset check before an adapter claims it.
- Must not: open a national query route

## LCM-015 Write the court schema register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-courts
- Depends on: LCM-006
- Write scope: implementation_plan/legal_corpus_modules/registers/court.md
- Authorization: new register file only
- Acceptance: Fields that identify a court, the sources those fields came from, and a statement that opinions stay in the caselaw register.
- Must not: create a court row by copying an opinion id

## LCM-016 Write the duplicate-tree disposition
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-copies
- Depends on: LCM-007
- Write scope: implementation_plan/legal_corpus_modules/registers/duplicates.md
- Authorization: new register file only
- Acceptance: For each duplicate tree, say `canonical`, `mirror`, `collector-entry`, or `quarantine`. The 17 note files are `quarantine`. The Argentina and Malta SkillCenter `v3` copies are `leave-in-place`. No path is marked `delete`.
- Must not: authorize a bulk delete

## LCM-017 Write the display and doc register
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S1
- Track: register-ui
- Depends on: LCM-008, LCM-009
- Write scope: implementation_plan/legal_corpus_modules/registers/surfaces.md
- Authorization: new register file only
- Acceptance: List current UI schema ids and the docs LCM-009 marked as future-stale. Reserve new view ids `worldwide-legal-search.caselaw-view@1`, `regulation-view@1`, `legislative-act-view@1`, `court-view@1`, and `municipal-instrument-view@1`. Leave `law-source@1` as the statute view.
- Must not: edit the site while writing the register

## LCM-018 Land the shared instrument interface
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: interface
- Depends on: LCM-010, LCM-011, LCM-012, LCM-013, LCM-014, LCM-015
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/instrument_v1.py
- Authorization: new module only
- Acceptance: Export interface id `legal-corpus.instrument@1`. A record carries `kind`, `source_schema_id`, `source_schema_version`, `source_dataset`, and the untouched source row. Kind names are `law`, `regulation`, `legislative_act`, `caselaw`, `court`, and `municipal_instrument`. Unknown kind is rejected. The module does not import scrapers and does not change `interfaces.py`.
- Validation: compile `instrument_v1.py` with the datasets venv and run a unit test that rejects an unknown kind and an empty source schema id
- Must not: edit `document_role.py`, `interfaces.py`, or `registry.py`

## LCM-020 Land the law kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-law
- Depends on: LCM-018, LCM-010
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/law_v1.py
- Authorization: new file only; create `kinds/` if needed without editing a shared `__init__.py` that another task owns
- Acceptance: Export `legal-corpus.law@1` bound to `country-laws-ir-graphrag/v1` and the verify schema `country-laws-normalize-verify/v1`. Accept a row only when the register's required columns are present. Do not drop extra columns.
- Validation: unit test with one valid fixture and one fixture missing `text`
- Must not: edit `instrument_v1.py` or `query.py`

## LCM-021 Land the regulation kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-regulation
- Depends on: LCM-018, LCM-013
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/regulation_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.regulation@1`. The module records the source schema id from the regulation register and refuses a row that claims `worldwide-legal-search.law-source@1`.
- Validation: unit test that a statute schema id is rejected
- Must not: edit the law kind module

## LCM-022 Land the legislative-act kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-act
- Depends on: LCM-018, LCM-014
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/legislative_act_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.legislative-act@1`. Refuse a row whose source is the US Code consolidation listed in the register.
- Validation: unit test with an act-shaped fixture and a rejected US Code fixture
- Must not: change US Code scrapers

## LCM-023 Land the caselaw kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-caselaw
- Depends on: LCM-018, LCM-012
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/caselaw_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.caselaw@1`. A row names one of the registered source schema ids. Two sources are not coerced into the same columns.
- Validation: unit test that a DILA-shaped row and a CAP-shaped row both pass while keeping their own schema ids
- Must not: import CUDA code or start an embedding job

## LCM-024 Land the court kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-court
- Depends on: LCM-018, LCM-015
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/court_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.court@1`. Required fields are the court identifier and the source schema id from the register. Opinion text is refused.
- Validation: unit test that an opinion body is rejected
- Must not: treat a docket number as a statute id

## LCM-025 Land the municipal instrument kind module
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-municipal
- Depends on: LCM-018, LCM-011
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/municipal_instrument_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.municipal-instrument@1`. Validate the 19 canonical columns in order. Allow extra columns only after those 19. Reject a NULL in a string column. `doc_order` stays an integer.
- Validation: unit test for order, a trailing extra column, and a NULL rejection
- Must not: edit `world_municipal/schema.py`

## LCM-026 Pin the existing status vocabulary
- Status: completed
- Parent goal: LCM-G020
- Subgoal: LCM-G020.S2
- Track: kind-status
- Depends on: LCM-018
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/kinds/status_v1.py
- Authorization: new file only
- Acceptance: Export `legal-corpus.status@1` as the existing `LawStatus` and `StatusConfidence` words and `STATUS_FIELD_NAMES` from `interfaces.py`. Reject a new status word.
- Validation: unit test that `current` is accepted and `in_force` is rejected
- Must not: edit `interfaces.py` or add a parallel status enum

## LCM-030 Adapt country-laws IR into the law kind
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S1
- Track: adapter-law
- Depends on: LCM-020
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/country_laws_ir_v1.py, and a matching test under the datasets test tree
- Authorization: new adapter and test
- Acceptance: The adapter reads a fixture with the register's law columns, emits `legal-corpus.law@1`, and keeps `source_schema_version` `country-laws-ir-graphrag/v1`. It calls no network and does not replace `document_shard_paths`.
- Validation: the new unit test
- Must not: edit `country_laws_ir/query.py` or add Ghana, Portugal, Lithuania, or Belgium routes

## LCM-031 Adapt the 19-column municipal schema
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S1
- Track: adapter-municipal
- Depends on: LCM-025
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/world_municipal_v1.py and its test
- Authorization: new adapter and test
- Acceptance: A fixture with the 19 columns and one trailing provenance column passes. A reordered column fails. Output kind is `municipal_instrument` and the source version cites `world_municipal/schema.py`.
- Validation: the new unit test
- Must not: upload municipal shards or change `build_schema`

## LCM-032 Adapt pipeline schema 1.2.0
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S1
- Track: adapter-pipeline
- Depends on: LCM-020, LCM-025, LCM-011
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/world_law_pipeline_v1.py and its test
- Authorization: new adapter and test
- Acceptance: Preserve `SCHEMA_VERSION` `1.2.0` and the source `DOC_TYPES` value on the row. Map only the labels the municipal register classified. Leave `decision` unclassified when the register says so. `iso_` keys stay national-shaped and are not rewritten into municipal ids.
- Validation: the new unit test
- Must not: edit `hub_integrated/world_law_pipeline/schema.py`

## LCM-033 Adapt regulation sources
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-regulation
- Depends on: LCM-021
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/regulation_v1.py and its test
- Authorization: new adapter and test
- Acceptance: One function or class per source section in the regulation register. Each keeps that source's schema id. A CFR fixture does not validate as a statute.
- Validation: the new unit test, using fixtures rather than live GovInfo calls
- Must not: scrape the network or edit `federal_scrapers` in place

## LCM-034 Adapt legislative acts
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-act
- Depends on: LCM-022
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/legislative_act_v1.py and its test
- Authorization: new adapter and test
- Acceptance: Accept the act-shaped fixtures from the register and reject a US Code row. Record `legal-corpus.legislative-act@1` and the source schema id.
- Validation: the new unit test
- Must not: change `us_code_scraper.py` or `public_law_change_processor.py` bytes

## LCM-035 Adapt US Code as law
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S1
- Track: adapter-uscode
- Depends on: LCM-020, LCM-014
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/us_code_v1.py and its test
- Authorization: new adapter and test
- Acceptance: Emit `legal-corpus.law@1` with the US Code source schema id from the law or act register. The legislative-act adapter's rejection of this source still holds.
- Validation: the new unit test
- Must not: relabel the US Code as `legislative_act`

## LCM-036 Adapt Caselaw Access Project rows
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-cap
- Depends on: LCM-023
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/caselaw_cap_v1.py and its test
- Authorization: new adapter and test
- Acceptance: Map a CAP fixture onto `legal-corpus.caselaw@1` while retaining the CAP schema id and the original opinion fields.
- Validation: the new unit test
- Must not: call the CAP API or start vector encoding

## LCM-037 Adapt France DILA caselaw
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-dila
- Depends on: LCM-023
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/caselaw_dila_v1.py and its test
- Authorization: new adapter and test
- Acceptance: DILA rows become caselaw records with the DILA schema id. The adapter does not register itself as `collect_legi` and does not change `get("fr")`.
- Validation: the new unit test plus a catalog assertion that `get("fr")` is still the LEGI collector if that function exists
- Must not: edit `catalog.py` except to read it

## LCM-038 Adapt Germany Rechtsprechung im Internet
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-rii
- Depends on: LCM-023
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/caselaw_rii_v1.py and its test
- Authorization: new adapter and test
- Acceptance: RII rows keep the RII schema id and do not replace `collect_gii`. Do not rebuild Germany GraphRAG revision `452729c915ee`.
- Validation: the new unit test
- Must not: start a GraphRAG or embedding job

## LCM-039 Adapt RECAP archive rows
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-recap
- Depends on: LCM-023
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/caselaw_recap_v1.py and its test
- Authorization: new adapter and test
- Acceptance: A RECAP fixture keeps RECAP field names and the RECAP schema id under `legal-corpus.caselaw@1`. Court identity, if present, is a reference, not a copied court module row, unless LCM-040 consumes it.
- Validation: the new unit test
- Must not: download RECAP archives

## LCM-040 Adapt court identity
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S2
- Track: adapter-court
- Depends on: LCM-024
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/adapters/court_v1.py and its test
- Authorization: new adapter and test
- Acceptance: Build `legal-corpus.court@1` from the court register's identifier fields. Drop opinion text. Cite the source schema.
- Validation: the new unit test
- Must not: merge court rows into caselaw rows

## LCM-041 Guard closed national routes
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S3
- Track: guard-routes
- Depends on: LCM-016
- Write scope: a new test file under the datasets test tree named for this task
- Authorization: new test only
- Acceptance: The test reads `national_collectors/catalog.py` and fails if Belgium, Portugal, Lithuania, or Ghana gain a statute route, or if `get("fr")` or `get("de")` change collector. It also fails if a new adapter module registers those routes.
- Validation: run that test
- Must not: edit `catalog.py`

## LCM-042 Quarantine the non-Python note files
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S3
- Track: guard-notes
- Depends on: LCM-016
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/quarantine_notes_v1.py and its test
- Authorization: new module and test; do not modify the 17 notes
- Acceptance: The module lists the 17 filenames from `PLAN.md` and the test asserts each file's first line still starts with `linked logs/`. The canonical index must be able to skip them. The files stay in their current paths.
- Validation: the new unit test
- Must not: rename, delete, or "fix" the notes into Python

## LCM-043 Leave SkillCenter v3 copies in place
- Status: completed
- Parent goal: LCM-G030
- Subgoal: LCM-G030.S3
- Track: guard-outliers
- Depends on: LCM-016
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-043.md and a new test that only reads the two copies
- Authorization: new test and evidence note
- Acceptance: The test asserts `justicedao__ipfs_argentina_laws-ir` and `justicedao__ipfs_malta_laws-ir` still report `skillcenter-huggingface-release/v3` and are not imported by `instrument_v1.py`. Intent IR and the legal-IR autoencoder are named as out of scope.
- Validation: the new unit test
- Must not: move those copies onto `country-laws-ir-graphrag/v1` or commit the feature-freeze directory

## LCM-050 Export one canonical package index
- Status: completed
- Parent goal: LCM-G040
- Subgoal: LCM-G040.S1
- Track: index
- Depends on: LCM-020, LCM-021, LCM-022, LCM-023, LCM-024, LCM-025, LCM-026, LCM-030, LCM-031, LCM-032, LCM-033, LCM-034, LCM-035, LCM-036, LCM-037, LCM-038, LCM-039, LCM-040, LCM-042
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/module_index_v1.py and its test
- Authorization: new index only
- Acceptance: The index lists every kind and adapter version id. Importing it does not import the 17 note files, the SkillCenter `v3` copies, or a scraper side effect. It does not edit `legal_corpus/__init__.py`.
- Validation: the new unit test
- Must not: rewrite `legal_corpus/__init__.py` in a way that changes jurisdiction registration

## LCM-051 Record the hub_dataset_scripts boundary
- Status: completed
- Parent goal: LCM-G040
- Subgoal: LCM-G040.S2
- Track: boundary-hub-scripts
- Depends on: LCM-050, LCM-016
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/hub_dataset_scripts/CANONICAL_MODULE.md
- Authorization: one new markdown file; no scraper edits; bulk retirement needs a later named go-ahead
- Acceptance: The file points mirrors at `module_index_v1` and lists groups from the duplicate register. It states that the tree was not deleted.
- Must not: move or rewrite the per-country scripts

## LCM-052 Record the hub_integrated boundary
- Status: completed
- Parent goal: LCM-G040
- Subgoal: LCM-G040.S2
- Track: boundary-hub-integrated
- Depends on: LCM-050, LCM-016
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/hub_integrated/CANONICAL_MODULE.md
- Authorization: one new markdown file
- Acceptance: Cover `justicedao_world_law_scrapers`, `legal_scrapers`, and `world_law_pipeline`. Point schema authority at the versioned modules. Name the 17 notes as quarantine. State that pipeline `schema.py` remains the `1.2.0` source of truth until a named go-ahead says otherwise.
- Must not: edit `world_law_pipeline/schema.py`

## LCM-053 Record the harvested-copy boundary
- Status: completed
- Parent goal: LCM-G040
- Subgoal: LCM-G040.S2
- Track: boundary-harvested
- Depends on: LCM-050, LCM-016
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/international/harvested/CANONICAL_MODULE.md
- Authorization: one new markdown file
- Acceptance: Identify harvested copies that repeat a canonical schema and point them at the index. Leave collector entry points in `national_collectors` as collectors, not as a second schema.
- Must not: delete harvested scripts

## LCM-060 Write the display contract
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S1
- Track: ui-contract
- Depends on: LCM-017, LCM-020, LCM-021, LCM-022, LCM-023, LCM-024, LCM-025
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/contract.ts
- Authorization: new site module
- Acceptance: Export `worldwide-legal-search.instrument-view-contract@1`. Map each reserved view id from LCM-017 to the kind version it can render. Reject an unknown instrument version. Document that the query place is an argument, not caller IP, and that jurisdiction applicability stays `not-asserted`.
- Validation: a site unit test for an unknown version and for the absence of a geoip field
- Must not: change `SCHEMA_VERSION` in `data/schema.ts` or `jurisdiction/schema.ts`, and do not edit `supervisor-operations.md`

## LCM-061 Declare the site law view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-law
- Depends on: LCM-060, LCM-020
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/law.ts and its test
- Authorization: new view module
- Acceptance: Export that this view renders `worldwide-legal-search.law-source@1` and `law-section@1` for `legal-corpus.law@1` / `country-laws-ir-graphrag/v1`. Refuse `legal-corpus.caselaw@1`.
- Validation: the new test
- Must not: renumber `SCHEMA_VERSION` `1` or change the required law columns

## LCM-062 Add the site caselaw view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-caselaw
- Depends on: LCM-060, LCM-023
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/caselaw.ts and its test
- Authorization: new view module
- Acceptance: Export `worldwide-legal-search.caselaw-view@1`. Accept only `legal-corpus.caselaw@1` plus a source schema id the caselaw register lists. Show the source schema id in the view model. Do not render a caselaw row through `law-source@1`.
- Validation: the new test
- Must not: add a query route or a GEOIP lookup

## LCM-063 Add the site regulation view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-regulation
- Depends on: LCM-060, LCM-021
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/regulation.ts and its test
- Authorization: new view module
- Acceptance: Export `worldwide-legal-search.regulation-view@1` bound to `legal-corpus.regulation@1`. Refuse a statute schema id.
- Validation: the new test
- Must not: present CFR text as a consolidated statute

## LCM-064 Add the site legislative-act view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-act
- Depends on: LCM-060, LCM-022
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/legislative-act.ts and its test
- Authorization: new view module
- Acceptance: Export `worldwide-legal-search.legislative-act-view@1`. Refuse a US Code law row.
- Validation: the new test
- Must not: change the law view

## LCM-065 Add the site court view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-court
- Depends on: LCM-060, LCM-024
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/court.ts and its test
- Authorization: new view module
- Acceptance: Export `worldwide-legal-search.court-view@1` bound to `legal-corpus.court@1`. The view has no opinion body field.
- Validation: the new test
- Must not: embed caselaw text in the court view

## LCM-066 Add the SwissKnife view package
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S3
- Track: ui-swissknife
- Depends on: LCM-060, LCM-020, LCM-021, LCM-022, LCM-023, LCM-024, LCM-025
- Write scope: swissknife/src/services/legal-corpus-views/ and its tests
- Authorization: new SwissKnife package
- Acceptance: Export the same view ids as LCM-060 through LCM-065 and LCM-067's municipal id, each naming the instrument version it accepts. Refuse an unknown version. Do not read caller IP.
- Validation: the new SwissKnife unit test
- Must not: edit `implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md`, media-player files, or a running supervisor unit

## LCM-067 Add the site municipal instrument view
- Status: completed
- Parent goal: LCM-G050
- Subgoal: LCM-G050.S2
- Track: ui-municipal
- Depends on: LCM-060, LCM-025
- Write scope: worldwidelaws.github.io/src/lib/worldwide/views/municipal-instrument.ts and its test
- Authorization: new view module
- Acceptance: Export `worldwide-legal-search.municipal-instrument-view@1`. Require the 19 column names and accept trailing provenance fields. Refuse a NULL displayed as if it were an empty string that the schema did not allow; the adapter already rejects NULL, and the view rejects a missing canonical column.
- Validation: the new test
- Must not: reorder columns in the view model

## LCM-070 Document the landed interfaces
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S1
- Track: docs-interfaces
- Depends on: LCM-018, LCM-020, LCM-021, LCM-022, LCM-023, LCM-024, LCM-025, LCM-026
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/docs/instrument-modules.md
- Authorization: new doc written after the modules exist
- Acceptance: Every version string and kind name is copied from the landed Python files, with the path cited. The doc says `document_role.ROLES` and `LawStatus` were not replaced. If a module is missing, this task stays todo.
- Must not: describe a module that has not landed or update this plan's bootstrap status to completed

## LCM-071 Document the landed adapters
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S1
- Track: docs-adapters
- Depends on: LCM-030, LCM-031, LCM-032, LCM-033, LCM-034, LCM-035, LCM-036, LCM-037, LCM-038, LCM-039, LCM-040, LCM-041, LCM-042, LCM-043
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/docs/adapters.md
- Authorization: new doc
- Acceptance: One section per adapter file that exists on disk. Each section quotes that file's source schema id. Closed routes and the DILA/LEGI and RII/GII splits are stated from the guard tests, not from memory.
- Must not: claim a live network fetch or a GraphRAG rebuild ran

## LCM-072 Document the landed display versions
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S1
- Track: docs-ui
- Depends on: LCM-060, LCM-061, LCM-062, LCM-063, LCM-064, LCM-065, LCM-066, LCM-067
- Write scope: worldwidelaws.github.io/docs/worldwide/instrument-views.md and swissknife/src/services/legal-corpus-views/README.md
- Authorization: new docs next to the views
- Acceptance: Quote each view schema id from the TypeScript or SwissKnife source. State that place is explicit and GEOIP is absent. Leave `supervisor-operations.md` untouched.
- Must not: claim GitHub Pages deployed, or claim `tsc`, Jest, or Playwright passed unless those commands were run and their exit status is in the receipt

## LCM-073 Document the module map after the boundaries land
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S1
- Track: docs-map
- Depends on: LCM-050, LCM-051, LCM-052, LCM-053
- Write scope: external/ipfs_datasets/docs/legal/legal_corpus_module_map.md
- Authorization: new doc
- Acceptance: Map each duplicate tree to its `CANONICAL_MODULE.md` and to `module_index_v1.py`. Say the copies were not deleted. Include the quarantine notes and the SkillCenter outliers as left in place.
- Must not: rewrite `docs/legal/justicedao_refresh_plan_20261021.md` history

## LCM-074 Mark older reports as historical
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S1
- Track: docs-historical
- Depends on: LCM-009, LCM-073
- Write scope: only the files LCM-009 listed, and only a short banner at the top of each
- Authorization: banner edits; no deletion
- Acceptance: Each banner points at `legal_corpus_module_map.md` and says the report describes the tree from before the module boundary. Reports that LCM-009 did not list are unchanged. Banners are not applied to `supervisor-operations.md`.
- Must not: delete `FINAL_PROJECT_REPORT.md`, `PROJECT_COMPLETE.md`, or the refresh plans

## LCM-075 Check documentation against the tree
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S2
- Track: docs-drift
- Depends on: LCM-070, LCM-071, LCM-072, LCM-073, LCM-074
- Write scope: external/ipfs_datasets/ipfs_datasets_py/processors/legal_scrapers/legal_corpus/check_doc_drift.py and its test
- Authorization: new checker
- Acceptance: The checker reads version constants from the landed kind, adapter, and view modules and fails when `instrument-modules.md`, `adapters.md`, or the view docs omit one or cite a different string. The receipt includes the command and the exit status.
- Validation: run the checker and its test
- Must not: update a doc inside the checker to hide a mismatch

## LCM-080 Check UI versions against Python versions
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S2
- Track: accept-versions
- Depends on: LCM-075
- Write scope: the drift checker if it does not already compare view contracts, otherwise evidence/LCM-080.md only
- Authorization: extend the checker or write the evidence file
- Acceptance: `instrument-view-contract@1` accepts exactly the kind versions exported by the Python modules. A mismatch exits non-zero with both strings. The passing run's output is stored in the evidence file.
- Validation: the checker command
- Must not: loosen either side to force a match

## LCM-081 Check closed routes and explicit place
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S2
- Track: accept-guards
- Depends on: LCM-041, LCM-060, LCM-072
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-081.md
- Authorization: run existing tests and record results
- Acceptance: Record the exit status of the closed-route test and the display-contract test. Confirm the view contract source has no GEOIP or caller-IP field. Restate that Belgium, Portugal, Lithuania, Ghana, Egypt governorates, South Africa provinces, and Wallis and Futuna stay unpublished.
- Must not: flip `LEGAL_QUERY_NORMALIZED` or upload a dataset

## LCM-082 Prove this plan is not on the worldwide board
- Status: completed
- Parent goal: LCM-G010
- Subgoal: LCM-G010.S1
- Track: guard-admission
- Depends on: none
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-082.md
- Authorization: read-only
- Acceptance: Show that `worldwide-legal-search-v1` required task ids do not include `LCM-` ids, and that the supervisor host config does not point at `implementation_plan/legal_corpus_modules`. Record the campaign stage observed while reading. Do not restart the supervisor.
- Must not: edit campaign DuckDB, markdown task status, or the supervisor unit

## LCM-083 Repeat the non-admission check after the docs land
- Status: completed
- Parent goal: LCM-G060
- Subgoal: LCM-G060.S2
- Track: guard-admission
- Depends on: LCM-075, LCM-082
- Write scope: implementation_plan/legal_corpus_modules/evidence/LCM-083.md
- Authorization: read-only
- Acceptance: Repeat the LCM-082 checks after documentation exists. Fail if any `LCM-` id was inserted into the worldwide required set or if a task in this file was marked complete inside DuckDB. This file's own `Status: todo` lines are changed to a receipt reference only by the person accepting the receipt, not by an agent supervisor.
- Must not: self-mark a worldwide task or an LCM task complete in DuckDB
