# Instrument view selector goals

Root, goals, and subgoals are planning records. Completion is not these status fields. This package is not admitted to a DuckDB board. `PLAN.md` is the contract. The default implementation model is Grok Build `grok-4.7`.

## IVS-G000 Bind a search row to a versioned instrument view
- Status: planned
- Parent goal ids json: []
- Required task ids json: ["IVS-001", "IVS-002", "IVS-003", "IVS-004"]
- Objective: A search row reaches a versioned instrument view only when the row already names that interface and source schema.
- Acceptance: Every required task has an evidence file and a passing fixed check. Filter tokens still do not select a view.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G010 Select the site view from an existing interface id
- Status: planned
- Parent goal ids json: ["IVS-G000"]
- Required task ids json: ["IVS-001", "IVS-002"]
- Objective: The site selector and ResultItem marker accept the six documented pairs and refuse a missing or crossed id.
- Acceptance: IVS-001 and IVS-002 are completed. Rows with no interface id keep today's markup.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G010.S1 Pure site selector
- Status: planned
- Parent goal ids json: ["IVS-G010"]
- Required task ids json: ["IVS-001"]
- Objective: One pure function beside the existing view modules.
- Acceptance: The IVS-001 evidence check exits 0.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G010.S2 Result item marker
- Status: planned
- Parent goal ids json: ["IVS-G010"]
- Required task ids json: ["IVS-002"]
- Objective: ResultItem sets data-instrument-view only when the selector returns a model.
- Acceptance: The IVS-002 evidence check exits 0.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G020 Select the same pair in SwissKnife
- Status: planned
- Parent goal ids json: ["IVS-G000"]
- Required task ids json: ["IVS-003"]
- Objective: The SwissKnife package accepts the same pairs and the README names the landed view ids.
- Acceptance: The IVS-003 evidence check exits 0. web/js/apps is untouched.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G020.S1 SwissKnife pair table and README
- Status: planned
- Parent goal ids json: ["IVS-G020"]
- Required task ids json: ["IVS-003"]
- Objective: Pair table, export, test, and the README sentence.
- Acceptance: The IVS-003 evidence check exits 0.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G030 Prove the selectors
- Status: planned
- Parent goal ids json: ["IVS-G000"]
- Required task ids json: ["IVS-004"]
- Objective: Re-run the site view tests, the SwissKnife view test, and check_doc_drift.
- Acceptance: The IVS-004 evidence check exits 0. No supervisor is restarted.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted

## IVS-G030.S1 Re-run the view checks
- Status: planned
- Parent goal ids json: ["IVS-G030"]
- Required task ids json: ["IVS-004"]
- Objective: One proof pass after the selectors land.
- Acceptance: The IVS-004 evidence check exits 0.
- Board namespace: instrument-view-selector-v1
- Completion authority: not admitted
