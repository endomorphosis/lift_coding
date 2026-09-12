# NS-026 production provider and independent historical scorer

This worktree runner extends the NS-006 interface with an admitted scientific
gateway and an independent historical scorer. The NS-006 deterministic
development stub remains available for terminal-state qualification. A stub
is not an admitted development provider invocation.

NS-004's Terra HIGH profile (`openai` / `gpt-5.6-terra` / reasoning `high`
through the quota-guarded Docker Codex fallback) is **not admitted** here.
Docker is absent from the authoritative validation `PATH`, and a usage reset
does not authorize that fallback. Before any development call this tree
freezes `protocol/development_provider_amendment.json`: Grok primary
`grok-4.6` over `https://api.x.ai/v1/chat/completions`, development-only,
`admitted_production=false`. NS-016 still owns the pilot and any final
profile amendment. Scientific calls never switch models inside a paired
block.

## Reproducible commands

All commands are relative to the repository root. `--ledger` is a durable
attempt/effect directory; rerunning the same schedule unit returns the
published receipt and does not re-dispatch a confirmed provider effect.

Probe (never dispatches):

```
python3 papers/completion/neurosymbolic_supervision/experiments/production_gateway.py probe --out "$OUT/probe.json"
```

Actual development provider invocation (frozen amendment; not the stub):

```
python3 papers/completion/neurosymbolic_supervision/experiments/run_comparison.py one-task --task-id ns-dev-boundary-add --arm A --cache local_cold --repetition 0 --record-kind development --path development --admitted-provider --ledger "$LEDGER" --out "$OUT/dev-actual.json"
```

Independent rescoring after the proposal is sealed. Hidden oracles are loaded
only by this process from `receipts/snapshots/NS-005/scorer_only/`:

```
python3 papers/completion/neurosymbolic_supervision/experiments/score_runs.py --attempt "$OUT/dev-actual.json" --out "$OUT/dev-actual.rescored.json"
```

Pinned upstream materialization (exact pre-fix commit; no caller git):

```
python3 papers/completion/neurosymbolic_supervision/experiments/production_gateway.py materialize --task-id ns-hist-01-xmltodict --mode proposal --store "$STORE" --dest "$DEST" --out "$OUT/materialize.json"
```

Stub terminals (not live repairs) still use the NS-006 injected development
path by omitting `--admitted-provider`. `one-arm`, `paired`, and `rescore`
keep the same argv as NS-006.

Live historical tasks use `--task-id ns-hist-01-xmltodict` and
`--path production`. Production remains unavailable until NS-016 admits
Terra HIGH or a versioned production freeze. The independent scorer will
admit a production outcome when `admitted_production` is true and hidden
FAIL_TO_PASS tests pass; it does not blanket-refuse historical tasks.

## Path classes

| `path_class` | Meaning | Can admit production? | Live-repair denominator |
|---|---|---|---|
| `production` | Authorized native provider route with served identity | Only when the production gate admits | Only then |
| `development` | Frozen Grok amendment (`--admitted-provider`) or labeled stub | Never | Never |
| `simulated` | Explicit simulation | Never | Never |

Receipts store the served provider/model/revision actually observed, or
null plus `revision_availability_reason`. Simulated observations cannot
be relabeled production. Development stubs use
`ns-006-injected-development` / `ns-006-deterministic-dev-stub` and
`simulated=true`. Actual development invocations use `xai` / `grok-4.6`
and `simulated=false`.

## Isolation

Proposal sandboxes cannot mount `receipts/snapshots/NS-005/scorer_only/`,
original `.git`, fixed-commit trees, Docker sockets, or host credential
files. Historical materialization exports only admitted pre-fix paths from
the pinned GitHub tarball of `pre_fix_commit`. Hidden FAIL_TO_PASS payloads
are reconstructed by the scorer principal from `fix_commit` after the
proposal is sealed.

## NS-016 freeze handoff

Executable freeze inputs:

- Provider pin: `experiments/production_gateway.py` plus
  `experiments/production_profile.json` and
  `protocol/development_provider_amendment.json`
- Scorer pin: `experiments/score_runs.py`
- Budgets: NS-004 `experiment_manifest.json` budgets, unchanged
- Run instructions: the commands above
- Remaining blockers: Terra HIGH unavailable; no production admission;
  NS-016 must freeze the actual pilot served identity before final A–D

## Limitations

- No billed Terra HIGH / Codex production proposal is dispatched.
- Sampling seed and temperature controls are recorded as unsupported.
- Docker/cgroup container isolation is unavailable in the sealed
  validation profile and is not claimed.
- Semantic-state import may still be blocked without `anyio`.
- This is not a frozen final A–D scientific result.
