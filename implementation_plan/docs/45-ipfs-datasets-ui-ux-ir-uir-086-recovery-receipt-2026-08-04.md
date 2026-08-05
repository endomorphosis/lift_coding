# UIR-086 recovery receipt — UIR-010 sealed capability miss (2026-08-04)

## Failure

UIR-010 repair-grant attempt 3 (after UIR-085):

1. Selection reopened once post-merge `task_binding_id` ignored production
   context symbol hints (`61f61e9ae`).
2. Landed-route preflight correctly fell through
   (`post_merge_correction_landed_route_inapplicable`).
3. Durable start CAS succeeded (`grant_consumed`, implementation_started seq 2081).
4. Provider dispatch failed closed:

   `RuntimeError: post-merge correction route lacks one unambiguous sealed capability`

Attempt **consumed** (returncode 1). Durable head:

`grant_consumed` → **`correction_failed` (attempt 3)**  
failure event `sha256:717235bb…` sequence **2086**  
failure record `baguqeerae7fdvpwvf6zgippzjw6bmml7hff23umhelhqwmr6zif522pnkvea`

## Root cause

`_activate_post_merge_correction_landed_route` was the only production sealer.
When landed-route preflight was inapplicable, fallthrough cleared the landed
guard but still dispatched `_run_production_post_merge_correction_route`, which
requires exactly one process-local sealed capability. None was registered.

## Fix

Accelerate: seal after durable start for ordinary / fallthrough corrections
(`_seal_post_merge_correction_route_after_start`), and reuse that sealer from
landed-route activation.

Schema findings remain closed on tip (`f4e4df615`, 25/25 `test_schema.py`).

## Release

Completing this repair mints `repair_granted` for **attempt 4** against the
attempt-3 `correction_failed` head so lane-4 can re-run UIR-010 correction with
sealed fallthrough.
