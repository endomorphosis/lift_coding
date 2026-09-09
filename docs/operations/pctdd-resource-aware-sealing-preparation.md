# PCTDD resource-aware sealing: source preparation, not runtime admission

Prepared 2026-09-09. This checkout is deliberately **not deployed**. No live
PCTDD owner, task store, launch route, systemd unit, or accepted runtime capsule
was changed. Do not run its copied `resume`, `launch`, `state-owner`, or
`seal-controls` commands as an installation shortcut.

## Source identities

The clean outer checkout is
`/home/barberb/lift_coding/.worktrees/pctdd-resource-aware-sealing-prep`, branch
`codex/pctdd-resource-aware-sealing-prep`, based on outer commit
`3a6d685f6355d68b9adc897f1c93412fe87a7045`.

Its `external/ipfs_accelerate` is a separate clean linked worktree, branch
`codex/pctdd-resource-aware-sealing-accelerator`, based on
`0fccbf887b8ba25dff4adae7893e774a25895823`; the prepared source commit is
`4d38f10188b8837acc2a1b61197d0c1d8e53e1a4`. Its Git common directory is
`/home/barberb/lift_coding/.git/worktrees/parallel-content-sealing-proof-carrying-tdd-v1/modules/external/ipfs_accelerate`.

The actual dirty source remains
`/home/barberb/lift_coding/.worktrees/pctdd-g9-orphan-recovery/external/ipfs_accelerate`.
Neither its index nor its unfinished changes were copied wholesale or modified
during this preparation. The older
`.worktrees/parallel-content-sealing-proof-carrying-tdd-v1/external/ipfs_accelerate`
alias resolves through Git metadata for a different G8 worker checkout; do not
use that alias as a deployment or staging target.

## Exact patch boundary

All paths below are inside the clean accelerator checkout:

- `_hash_resources.py` under `ipfs_accelerate_py/`: one shared per-UID heavy-hash
  admission domain, bounded per-file slots (default 2, maximum 4, new admission
  reduced under pressure), timeout, unsafe-lock rejection, and fork-safe cleanup.
- `agent_supervisor/runtime/hash_pressure.py`: preserves the legacy public API
  while routing all participants through that shared resource budget.
- `agent_supervisor/proof/incremental_sealing/parallel_verification.py`: caps the
  executor and admits only pure SHA/HMAC verification inside per-worker slots.
  Callbacks and aggregation stay outside slots; waiting consumes the batch
  deadline. Proof checks and deterministic digest semantics remain intact.
- `agent_supervisor/runtime/grok_cli_runner.py`: admits the existing monolithic
  workspace fingerprint as one exclusive heavy batch without changing its
  ordered byte stream. No leaf-digest substitution or metadata cache is used.
- `agent_implementation_route.py`: explicitly includes the root resource module
  in required capsule files and exact module-origin checks.
- `agent_supervisor/runtime/quack_state_server.py` and
  `agent_supervisor/task_sources/duckdb_state.py`: the two temporary in-memory
  Quack clients now pass `config={"threads": "1"}` at connection construction.
  Existing authoritative writer and read-replica connections already specify 1.

No DuckDB schema, shared hash observation owner, authority adapter, mutable-file
cache, provider authorization, or Quack HTTP thread-pool change is included.
The unrelated dirty Grok watchdog cleanup edit was not imported.

## Verification

Run from the clean accelerator checkout with native-library thread limits set
to 1, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `nice -n 10`, and `ionice -c 2 -n 7`:

```
python -m pytest -q \
  test/api/test_resource_rollout_admission.py \
  test/api/test_hash_worker_slots.py \
  test/api/test_quack_temporary_connection_budget.py \
  test/api/parallel_content_sealing/test_pctdd_018_parallel_proof_verification.py \
  test/api/test_agent_supervisor_duckdb_connection_policy.py
```

These focused suites passed in two runs: 80 + 27 = **107 passed**. They cover
cross-process overlap/exclusion, timeouts, pressure, fork FD reuse, unsafe lock
paths, hook reentrancy, unchanged workspace hash identity, capsule closure and
origin, temporary-client error cleanup, and existing proof/connection policy.

An additional broader Grok/Quack run had 93 passed and 20 failed: 19 provider-route
fixture/model/effort mismatches and one disposable Docker toolchain cleanup
verification failure. The smallest route failure,
`test_incomplete_quota_route_defaults_medium_reasoning_effort`, was reproduced
after loading the exact pre-patch HEAD route and Grok modules in memory, without
editing either checkout. The broad suite is not a passing deployment gate.
Both exact disposable container IDs were subsequently confirmed absent; no
model request or live PCTDD job was started by that test.

A tiny isolated DuckDB 1.5.5 probe observed 20 OS threads after import, 39 with
an uncapped temporary connection (`current_setting('threads') = 20`), and 20
with a capped connection (`threads = 1`). The cap prevents the additional client
pool; it does not remove DuckDB's ambient import pool. At the live PCTDD census,
most of its 149 threads were sleeping. Thread count alone is not evidence of
149 concurrent hashes.

## Required admission before deployment

1. Review the successor source and retain exact clean gitlinks. The other two
   submodules remain uninitialized here at their original pinned gitlinks; this
   preparation has not passed full dependency validation.
2. Select the reviewed runtime/source transition while preserving the existing
   G9 task authority. The copied scheduler still names the old G9 absolute owner
   directory, endpoint `quack:127.0.0.1:27278`, and required outer branch
   `agent/parallel-content-sealing-proof-carrying-tdd-v1-g9`. Merely moving paths
   or starting another owner would not supply authority.
3. Regenerate/review the required exact-source controls and dependency seals
   through the supported workflow. The dependency validator checks each nested
   HEAD, tree, gitlink, and clean status against its seal; this source commit
   intentionally does not rewrite those old claims. Bootstrap `launch` demands
   exact-current-source PCTDD-000 sealing. Runtime `resume` uses a distinct
   current-tree preflight plus authenticated canonical task population gate.
4. Coordinate an admission and launch-route switch before touching services or
   live processes. The existing `pctdd_g9_descendant_source_successor.py` is
   specifically a stopped-G8-to-G9 migration, requiring owner fencing and no
   active claims; it is not a generic live-G9 upgrade command. Do not replay it
   on the current owner.
5. After admission, verify the accepted capsule contains the new root helper and
   that the launched source, resource environment, and authority binding match.
   A later shared hash-cache rollout requires an explicitly reviewed adapter
   for this older owner's APIs; the ASEH typed-owner implementation must not be
   copied blindly.
