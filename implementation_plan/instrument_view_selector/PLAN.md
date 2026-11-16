# Bind a search row to a versioned instrument view only when the row already names that interface

This board is campaign `instrument-view-selector-v1`. The ipfs_accelerate_py agent supervisor executes it through `llm_router`: Grok Build (`grok`) with model `grok-4.7` is the default implementation provider. Codex runs only when that router reports a Grok hard quota. This board is not admitted to the worldwide-legal-search-v1 DuckDB. Do not point `worldwide-legal-search-supervisor.service` at this directory. Do not restart that unit. Do not start `worldwide-legal-search-watchdog.service`.

`goals.objectives.md` holds the goals and subgoals. `tasks.todo.md` holds the tasks. `PARALLEL.md` says which tasks may run together. A task may write only its write scope. The supervisor records `Status: completed` only after the task's evidence file says `Acceptance: met` and the fixed check for that task exits 0. `work_complete` stays false. `completion_authority` stays false.

The implementation daemon is not started against lift_coding for this campaign. Its out-of-scope restore force-checkouts dirty gitlinks.

## Design

Accept a plain record only when it already has the interface id and the source schema that module documents:

- `legal-corpus.law@1` plus `country-laws-ir-graphrag/v1` goes to the law view, schema `worldwide-legal-search.law-source@1`
- `legal-corpus.caselaw@1` plus `unversioned` goes to `worldwide-legal-search.caselaw-view@1` and is not `law-source@1`
- `legal-corpus.regulation@1` plus one registered regulation source schema goes to the regulation view
- `legal-corpus.legislative-act@1` plus one registered act source schema goes to the legislative-act view
- `legal-corpus.court@1` plus `unversioned` goes to the court view and has no opinion body
- `legal-corpus.municipal-instrument@1` plus the 19-column municipal schema goes to `worldwide-legal-search.municipal-instrument-view@1`. A null column still refuses

Refuse when the interface id is absent, unknown, or paired with the wrong source schema. Filter tokens `constitution`, `statute`, `code`, `regulation`, `ordinance`, `treaty`, `decision`, `notice`, `amendment`, `consolidation`, and `unknown` do not select a view. A missing interface id keeps today's `ResultItem` markup.

`ResultItem` may set `data-instrument-view` to the view id when the selector returns a model. It does not replace the title, citation, or inclusion lines. No network call, no place lookup, and no catalog import.

The SwissKnife selector uses the same pair table. No app under `web/js/apps` is edited. The SwissKnife README says the package is in the tree and names the six view ids.

## Standing limits

- Do not change `executeProductionRetrieval`, the planner, `INSTRUMENT_KINDS`, `SCHEMA_VERSION`, `REQUIRED_LAW_COLUMNS`, the municipal 19-column order, or the pins.
- Do not commit, push, reset, or checkout. Do not commit `ipfs_accelerate_py/llm_router.py` or the JevOps seal. Do not edit the untracked `svf-cross-workflow-910.mjs`, `920.mjs`, or `930.mjs` scripts.
- Do not restart a healthy supervisor. Do not hand-complete SwissKnife visual-functional rows.
- Query place stays an argument. No GEOIP.
- Closed national routes stay closed. `collect_fr_dila` does not replace `collect_legi`. `collect_de_rii` does not replace `collect_gii`.
