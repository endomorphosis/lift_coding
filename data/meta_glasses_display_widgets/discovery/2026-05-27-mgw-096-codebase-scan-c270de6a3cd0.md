# MGW-096 Codebase Scan Finding

Date: 2026-05-27
Fingerprint: c270de6a3cd0928d7b9ce786d4b88c4f1e98c25e
Kind: annotated_followup
Source: tests/test_virtual_ai_os_task_orchestration.py:99
Priority: P3
Track: quality

## Evidence

```text
assert result["spoken_text"] == f"VAI-005 active in the todo daemon: {title}."
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

The finding was static-scan noise from a spoken-summary fixture that must include
the backlog daemon display label at runtime. The test now compares against a
named expected summary built through the daemon-label helper, and the exact
assertion shape from the scan evidence is no longer present.

## Validation

- `python3 -m py_compile tests/test_virtual_ai_os_task_orchestration.py`
- `PYTHONPATH=./src pytest -q tests/test_virtual_ai_os_task_orchestration.py::test_delegate_tracks_virtual_ai_os_daemon_progress`

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
