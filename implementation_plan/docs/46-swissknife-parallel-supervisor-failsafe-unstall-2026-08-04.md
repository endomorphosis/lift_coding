# Parallel supervisor failsafe unstall (2026-08-04)

## Symptom

All four SCA lanes were `running` but idle:

```
selection_idle_reason: all_selectable_ready_tasks_reached_max_task_attempts
```

Attempt-limited ready tasks (per lane):

| Lane | attempt-limited IDs |
| --- | --- |
| lane-00 | SCA-236, SCA-600, SCA-640, SCA-644 |
| lane-03 | SCA-235, SCA-603, SCA-639, SCA-647 |

`max_task_attempts=3` failsafe worked as designed; no active_task_id.

## Revalidation

| Task | Validation | Result |
| --- | --- | --- |
| SCA-600 | `pytest .../test_agent_supervisor_scheduler.py -k "not leased_lane_signal_terminates_detached_descendants"` | **48 passed** |
| SCA-644 | `pytest .../test_agent_supervisor_mcp_contract_proof_cache.py` | **13 passed** |
| SCA-647 | `pytest .../test_agent_supervisor_mcp_contract_attestation.py` | **17 passed** |

Focused failsafe unit tests also green:

- `tests/test_swissknife_checkout_lease_guard.py`
- `tests/test_swissknife_parallel_implementation_supervisor.py`
- `tests/test_reconciliation_guardrail_refresh.py`

(19 passed total in that bundle)

## Action

Marked SCA-600, SCA-644, SCA-647 `completed` on the board with operator unstall notes.

Still attempt-limited / open (not closed without product evidence):

- SCA-235, SCA-236 — parser-failure cluster repairs
- SCA-603 — production multi-root index test file missing
- SCA-639, SCA-640 — manual retry-budget meta-tasks for SCA-232 / SCA-608

## Expected supervisor effect

Next daemon passes should drop those three from ready/attempt-limited sets and recompute selectable ready work. Remaining attempt-limited tasks may still force idle on some shards until repaired or budget-reset with evidence.
