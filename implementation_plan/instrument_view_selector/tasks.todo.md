# Instrument view selector tasks

Bootstrap status is `todo`. That is not live progress. Do not copy these ids into the worldwide-legal-search-v1 DuckDB board. `PLAN.md` wins when a task and this file disagree. `PARALLEL.md` says which tasks may run together.

The supervisor, not the worker, changes a status line. A worker writes its evidence file and, when the acceptance is still false, the source paths in its write scope.

## IVS-001 Site selector module
- Status: completed
- Parent goal: IVS-G010
- Subgoal: IVS-G010.S1
- Track: site-selector
- Depends on: none
- Write scope: /home/barberb/worldwidelaws.github.io/src/lib/worldwide/views/select.ts, /home/barberb/worldwidelaws.github.io/src/lib/worldwide/views/select.test.ts, /home/barberb/lift_coding/implementation_plan/instrument_view_selector/evidence/IVS-001.md
- Authorization: edit only the write scope
- Acceptance: `select.ts` exports `selectInstrumentView`. It accepts the six interface and source-schema pairs in `PLAN.md` and returns no model for a missing id, for caselaw paired with `country-laws-ir-graphrag/v1`, for municipal paired with `law-source@1`, for a null municipal title, and for the filter tokens `decision` and `regulation`. It does not read a caller address. If those files already do this, keep them and write the evidence file. Fixed check: `/home/barberb/worldwidelaws.github.io/node_modules/.bin/jest --runTestsByPath src/lib/worldwide/views/select.test.ts --watchAll=false --forceExit` with cwd `/home/barberb/worldwidelaws.github.io`.
- Must not: commit, push, edit ResultItem, edit SwissKnife, or admit this id to DuckDB

## IVS-002 ResultItem view marker
- Status: completed
- Parent goal: IVS-G010
- Subgoal: IVS-G010.S2
- Track: site-result
- Depends on: IVS-001
- Write scope: /home/barberb/worldwidelaws.github.io/src/components/worldwide/SearchResults.tsx, /home/barberb/worldwidelaws.github.io/tests/worldwide/results.test.tsx, /home/barberb/lift_coding/implementation_plan/instrument_view_selector/evidence/IVS-002.md
- Authorization: edit only the write scope
- Acceptance: A row with no interface id keeps today's markup and has no `data-instrument-view`. An accepted caselaw claim sets `data-instrument-view` to `worldwide-legal-search.caselaw-view@1`, and that attribute is not `law-source@1`. Title text stays. No fetch is added. If this is already true, keep the files and write the evidence file. Fixed check: `/home/barberb/worldwidelaws.github.io/node_modules/.bin/jest --runTestsByPath tests/worldwide/results.test.tsx --watchAll=false --forceExit` with cwd `/home/barberb/worldwidelaws.github.io`.
- Must not: change `executeProductionRetrieval`, the planner, `INSTRUMENT_KINDS`, or the view modules

## IVS-003 SwissKnife pair table
- Status: completed
- Parent goal: IVS-G020
- Subgoal: IVS-G020.S1
- Track: swissknife-selector
- Depends on: none
- Write scope: /home/barberb/lift_coding/swissknife/src/services/legal-corpus-views/select.ts, /home/barberb/lift_coding/swissknife/src/services/legal-corpus-views/index.ts, /home/barberb/lift_coding/swissknife/src/services/legal-corpus-views/README.md, /home/barberb/lift_coding/swissknife/src/services/legal-corpus-views/legal-corpus-views.test.ts, /home/barberb/lift_coding/implementation_plan/instrument_view_selector/evidence/IVS-003.md
- Authorization: edit only the write scope
- Acceptance: `selectInstrumentView` accepts the same six pairs and refuses a missing id, a crossed pair, a null municipal title, and the tokens `decision` and `regulation`. `index.ts` exports it. The README says the package is in this tree and names `worldwide-legal-search.law-source@1`, `worldwide-legal-search.caselaw-view@1`, `worldwide-legal-search.regulation-view@1`, `worldwide-legal-search.legislative-act-view@1`, `worldwide-legal-search.court-view@1`, and `worldwide-legal-search.municipal-instrument-view@1`. `web/js/apps` is untouched. If this is already true, keep the files and write the evidence file. Fixed check: `/home/barberb/lift_coding/swissknife/node_modules/.bin/tsx --test src/services/legal-corpus-views/legal-corpus-views.test.ts` with cwd `/home/barberb/lift_coding/swissknife`.
- Must not: edit `web/js/apps`, the site, or `scripts/svf-cross-workflow-910.mjs`, `920.mjs`, or `930.mjs`

## IVS-004 Prove the view selectors
- Status: completed
- Parent goal: IVS-G030
- Subgoal: IVS-G030.S1
- Track: proof
- Depends on: IVS-001, IVS-002, IVS-003
- Write scope: /home/barberb/lift_coding/implementation_plan/instrument_view_selector/evidence/IVS-004.md
- Authorization: read-only against source; write only the evidence file
- Acceptance: Re-run the IVS-001 jest check, the IVS-002 jest check, the IVS-003 tsx check, and `/home/barberb/lift_coding/external/ipfs_datasets/.venv/bin/python -m ipfs_datasets_py.processors.legal_scrapers.legal_corpus.check_doc_drift` with cwd `/home/barberb/lift_coding/external/ipfs_datasets` and `PYTHONPATH` set to that directory. Record each exit code. Do not restart a supervisor.
- Must not: edit selector source, commit, or restart `worldwide-legal-search-supervisor.service`
