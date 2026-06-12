# HAO-420 Merge Retry-Budget Repair

Date: 2026-06-12
Source task: HAO-268
Follow-up task: HAO-420

## Summary

The failed HAO-268 outer merge branch is stale and should not be merged wholesale.
`git merge-tree` shows the blocking conflicts are the `hallucinate_app` submodule
pointer and generated `implementation_plan` todo fingerprint churn, not a
remaining semantic conflict in
`hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py`.

## Evidence

- Failed branch from retry-budget evidence:
  `implementation/hao-268-attempt-1-1781238030`
- Merge-tree conflict:
  `hallucinate_app` changed from base `f2a9351` to current `b01f44a` and failed
  branch `4ead615`
- Merge-tree conflict:
  `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`
  contains generated fingerprint churn unrelated to HAO-268
- Current submodule history already contains the HAO-268 cache metrics repair:
  `c1712fc HAO-268: Fix swallowed exceptions in pyarrow_content_index_bridge.py cache metrics`

## Repair

Kept the current `hallucinate_app` submodule lineage, which already includes the
HAO-268 implementation, and applied the cleaner HAO-268 attempt-2 wording for the
cache metrics comments. The metrics side effects still catch `Exception as e`
and log with `logger.exception(...)`, preserving traceback visibility while
keeping cache lookups non-fatal when optional metrics fail.

The requested semantic merge resolver was not run because
`ipfs-accelerate-agent-merge-resolver` is not installed in this environment and
the observed blocker is stale generated outer-repo churn plus a submodule pointer
selection, not a source-level semantic conflict.

## Validation

- `python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py`
- `test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/discovery/2026-06-12-hao-420-hao-268-merge-retry-budget.md`
