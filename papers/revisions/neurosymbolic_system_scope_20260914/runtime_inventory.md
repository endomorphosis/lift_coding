# Current runtime inventory, 2026-09-14

This is a current source/import audit, not an efficacy result. No applicable `AGENTS.md` was found in the inspected root, external components, or the three explicit original worktrees. Exact profile commits and key file hashes are in `runtime_inventory.json`; dirty overlay bytes, not a commit label alone, identify an experiment's implementation.

## Runnable components and callers

| Mechanism | Current evidence | Limitation / next consumer |
|---|---|---|
| Abstract interpretation and bounded repair | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py` and `autonomous_repair/formal_assurance_cegis.py` both import with system Python. `analyze_python_source` produces findings and `run_bounded_cegis` computes candidates in a fixed grammar. | Search of this source profile finds the repair function's facade and internal mutation benchmark, but no main daemon caller. A new eval caller must actually consume the computed candidate and use a separate execution oracle. Its internal proof/test gates include structural/marker checks and must not be represented as general theorem proving. |
| Semantic patch harness | `semantic_state/harness.py:780` exposes `SemanticCompressionHarness`; `cli.py:1017` constructs it. `_run_loop` consumes `route_model`, can suppress provider dispatch, and applies/validates a candidate inside an isolated worktree before publication. Imports successfully. | Calling a route with fabricated proof counts would merely reproduce old gate controls. Connect independently checked synthesis evidence to the route and observe the next action. The separate `work_loop.py` is a seven-line provisional shim; `run_closed_loop` calling it is not whole-system reasoning. |
| Persistence | `semantic_state/session.py`, `durable_state.py` import. `SemanticStateSession` journals and replays; `IpfsKitDurableStateAdapter` supports content blocks and compare-and-swap roots. Tests include restart preservation, journal-only nonpublication and corruption handling. | Current inspection establishes loadability, not saved planning tokens. Need matched interrupted trajectories and repeated work. |
| Procedure synthesis and execution | The explicit original `.worktrees/proof-carrying-procedure-compiler-v1/ipfs_accelerate_py/agent_supervisor/procedure_compiler/{runtime,cegis,world_model,registry,metrics}.py` all import. `cegis.py:2419` contains the exact `ProcedureCegis` class absent from the prior inventory's inspected profile. | `ProofCarryingProcedureCompiler` is deliberately a P0 parse/validate/invoke facade; its `synthesize` method raises. Use the separate `ProcedureCegis` interface and its actual source profile rather than claiming the facade synthesizes. No caller was found in that profile's `todo_daemon` or `planning` directories by the targeted procedure-name search. |
| Procedure world model | The original procedure profile includes `RepositoryWorldModel`, projection, registry, interpreter, recovery, distillation and trajectory modules. The separate `.worktrees/semantic-addressed-world-model-r2` has `semantic_world` tests and frozen benchmark metadata. | Need held-out downstream consumption and simple retrieval controls; stored descriptions or successful imports are not evidence of avoided model work. |
| Incremental proof sealer | Present under current `proof/incremental_sealing`. | Current import fails with missing `ipfs_datasets_py.logic.zkp.incremental_sealing`. Do not count this source combination as an operational sealer. Exact `CompositionEdge` was not found in targeted accelerate/procedure/current-datasets search; this is not an exhaustive all-worktree absence claim. |

## Historical study and data

The explicit original NS worktree is `.worktrees/vericodegen-neurosymbolic_supervision-2026`, with complete files under `papers/completion/neurosymbolic_supervision`:

- `experiments/run_comparison.py`, `production_gateway.py`, and `score_runs.py` retain the historical run boundaries and cold scoring.
- `benchmark/{tasks.jsonl,splits.json,oracle_manifest.json,provenance.md}` retain benchmark identity/splits. Treat all previously inspected/run tasks as development or historical, not a new untouched holdout.
- `pilot/recovery/final_input_source/host_service/{http_proposer,semantic_context,context_selection,cold_scorer}.py` retain the actual final additive A/B request construction.
- `qualification/production_provider/pilot_service` contains the worker integration and provider receipts. The final run used a fixed single HTTP POST with JSON edits, model alias `grok-4.6`, no tools/retries, and explicit container limits. Its freeze/grant ledger is historical and should remain unchanged.

New work belongs in a separately frozen development manifest and fresh ledger. It must not revive an exhausted historical campaign, reuse an old one-use effect, or represent a new caller as a previously deployed integration.

## Environment and provider access

Current system `python3` can find `anyio`, `duckdb`, `z3`, `pytest`, and `tiktoken`. The repository `.venv/bin/python` can find those except `z3`. The imports above used system Python with explicit `PYTHONPATH`; all listed successful modules resolved to their intended path, not a duplicate package.

No primary API credential environment variables were populated in this shell. The exact primary `~/.grok/auth.json` path exists. Historical `http_proposer.load_credential` checks private ownership/mode, canonical path, and a unique key record, then transmits the key in memory. No credential contents were printed or copied in this audit. Existence is not proof the credential still authorizes requests. Preserve raw usage fields and charge missingness; do not infer settlement from usage.

Reproduce the current symbolic imports:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit python3 -c 'from ipfs_accelerate_py.agent_supervisor.autonomous_repair.formal_assurance_cegis import FormalAssuranceCegis; from ipfs_accelerate_py.agent_supervisor.semantic_state.harness import SemanticCompressionHarness'
```

Reproduce original procedure imports:

```bash
PYTHONPATH=.worktrees/proof-carrying-procedure-compiler-v1:.worktrees/proof-carrying-procedure-compiler-v1/ipfs_datasets_py:external/ipfs_kit python3 -c 'from ipfs_accelerate_py.agent_supervisor.procedure_compiler.cegis import ProcedureCegis; from ipfs_accelerate_py.agent_supervisor.procedure_compiler.runtime import ProofCarryingProcedureCompiler'
```

## Next integrated development evaluation

Freeze fresh bounded program cases before outcomes. Compare model-first with deterministic analysis → bounded synthesis → native routing → common neural residual when synthesis cannot discharge the obligation. The new caller must apply the computed candidate, execute a separate behavioral oracle, retain abstentions/failures, and save all usage. Include supported grammar cases and unknown-frontier residuals so call avoidance cannot consist only of refusing hard work. Then restart from durable accepted state and prove that accepted work is retained without a second provider dispatch while unfinished work continues. Report this as a development integration first; neither a small constructed suite nor positive unit tests closes the whole-system efficiency question.
