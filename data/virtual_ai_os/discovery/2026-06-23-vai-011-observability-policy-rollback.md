# VAI-011 Observability, Policy, and Rollback Coverage

Task: Add observability, policy, and rollback coverage.

Evidence added:

- `src/handsfree/virtual_ai_os_observability.py` defines deterministic
  supervisor artifacts for policy decisions, placement changes, remote
  execution receipts, validation failures, and rollback events.
- `get_virtual_ai_os_observability_contract()["artifact_contract"]` advertises
  the stable contract id, artifact types, required fields, and reconcile keys.
- `tests/test_virtual_ai_os_observability.py` proves deterministic artifact ids,
  ordered parent links, config exposure, retry-from behavior, and full coverage
  of the VAI-011 acceptance event set.
- `implementation_plan/docs/19-virtual-ai-os-submodule-integration.md` now
  documents how supervisors should use `task_id`, `correlation_id`, and
  `artifact_id` to retry or reconcile without manual archaeology.

Operational handoff:

- Store artifacts as append-only JSON records or bundle snapshots wherever the
  daemon keeps task evidence.
- Retry from `bundle["supervisor_actions"]["retry_from"]` when a rollback event
  exists.
- Reconcile cross-surface work by the tuple `(task_id, correlation_id,
  artifact_id)`.

Validation:

- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_observability.py`
