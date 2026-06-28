# VAI-214 Merge Retry-Budget Resolution: VAI-155

Date: 2026-06-09
Source task: VAI-155
Resolution task: VAI-214

## Problem

VAI-155 branch (`implementation/vai-155-attempt-1-1780989245`) failed to merge
into main due to `main_checkout_dirty_conflict`. The dirty paths were:
- `hallucinate_app` (submodule with uncommitted state)
- `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

## Root Cause

The `hallucinate_app` submodule contained a pending change in
`hallucinate_app/python/hallucinate_app/ipfs_model_manager.py` that removed
the deprecated `ModelFilter` import from `huggingface_hub`. The `ModelFilter`
class was removed in newer versions of `huggingface_hub`, causing import
failures at runtime.

## Fix Applied

1. Removed `ModelFilter` from the import statement in `ipfs_model_manager.py`:
   ```python
   # Before:
   from huggingface_hub import HfApi, ModelFilter, snapshot_download
   # After:
   from huggingface_hub import HfApi, snapshot_download
   ```
2. Added trailing newline at end of file.
3. Changes committed to submodule branch
   `implementation/vai-214-attempt-1-1780995799-submodule-hallucinate_app`.

## Verification

- `python3 -m py_compile hallucinate_app/python/hallucinate_app/ipfs_model_manager.py` passes
- Submodule pointer updated in parent repository worktree

## Outcome

VAI-155 merge blocker resolved. VAI-155 can be released from strategy
`blocked_tasks`.
