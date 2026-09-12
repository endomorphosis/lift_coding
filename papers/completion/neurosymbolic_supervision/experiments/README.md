# NS-006 paired comparison runner

Paper-worktree runner for the frozen `ns-core-v1` protocol. It wraps the
existing semantic-state harness and provider gateway when those modules
import, and otherwise executes the same one-proposal loop with explicit
unavailable/development/simulated labels. It does not modify protected
acceptance oracles, elevate production authority, or count development
stubs as live historical repairs.

## Reproducible commands

All commands are relative to the repository root. `--ledger` is a durable
attempt/effect directory; rerunning the same schedule unit returns the
published receipt and does not re-dispatch a confirmed provider effect.

One task (synthetic development unit):

```
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py one-task --task-id ns-dev-boundary-add --arm A --cache local_cold --repetition 0 --record-kind development --path development --ledger "$LEDGER" --out "$OUT/one-task.json"
```

One arm (NS-006 boundary registry):

```
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py one-arm --arm A --registry ns-006-boundary --cache local_cold --repetition 0 --record-kind development --path development --ledger "$LEDGER" --out-dir "$OUT/one-arm"
```

Paired A–D run for one family:

```
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py paired --family-id ns-dev:boundary-add --cache local_cold --repetition 0 --record-kind development --path development --ledger "$LEDGER" --out-dir "$OUT/paired"
```

Independent rescoring (does not trust arm `accepted` / `closes_claim` flags
and does not remount hidden oracles into the proposal sandbox):

```
python3 papers/completion/neurosymbolic_supervision/experiments/score_runs.py --attempt "$OUT/one-task.json" --out "$OUT/one-task.rescored.json"
```

Live historical tasks use the same commands with `--task-id ns-hist-01-xmltodict`
(or `--family-id upstream:martinblech/xmltodict`) and `--path production`.
Without an admitted production reservation and materialized pre-fix tree the
unit terminates `unavailable`. That is a measured boundary, not a solved
repair.

## Path classes

| `path_class` | Meaning | Can admit production? | Live-repair denominator |
|---|---|---|---|
| `production` | Authorized native provider route with served identity | Only when the production gate admits | Only then |
| `development` | Injected labeled stub / local fixture | Never | Never |
| `simulated` | Explicit simulation | Never | Never |

Receipts always store the served provider/model/revision actually observed,
or null plus `revision_availability_reason`. Simulated observations cannot
be relabeled production.

## Terminal states and clocks

Every scheduled unit records exactly one of `solved`, `unsolved`,
`rejected`, `abstained`, `timed_out`, `unavailable`, `cancelled`,
`missing`. End-to-end active elapsed is `time.perf_counter()` over the
whole attempt, including setup, scoring, and recovery. Stage walls are
not summed.

## Isolation and interruption

Proposal sandboxes cannot mount `receipts/snapshots/NS-005/scorer_only/`.
Hidden FAIL_TO_PASS payloads stay with the independent scorer principal.
A confirmed provider effect is stored before scoring; resume scores from
that receipt. A production reservation without a confirmed dispatch is an
unknown effect: it is not replayed and cannot be completed as solved.

## Resource bounds (from `experiment_manifest.json`)

Process-level enforcement: serialized request 64 KiB, admitted patch
16 KiB, one proposal effect, provider/unit wall clocks, host CPU seconds,
and `resource.setrlimit` when the OS allows it. Docker/cgroup container
isolation is probed and recorded; it is unavailable in the sealed
validation profile and is not claimed.

## Limitations

- Semantic-state import remains blocked without `anyio`; development
  context packing uses local AST/name indexing and is not the production
  datasets semantic index.
- No billed production proposal is dispatched by this task. Sampling
  seed and temperature controls are recorded as unsupported.
- Synthetic `ns-dev-*` units qualify the runner interface only.
- Compact NS-005 recipes still require scorer-principal materialization
  of pinned commits before a live unit can execute.
