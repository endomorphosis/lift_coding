# VAI-205 Review Decisions For VAI-202 Preserved Diffs

Date: 2026-06-07

Scope: reviewed every preserved `hallucinate_app` source patch saved by VAI-202. The preserved patches target the old top-level `hallucinate_app/python/...` paths; current live equivalents are under `hallucinate_app/hallucinate_app/python/...` and `hallucinate_app/hallucinate_app/experiments/...`.

## Decisions

- `vai-103-attempt-1-1779882686-hallucinate_app-source.patch`: dropped as already represented. The nested stable diffusion demo already has the Uint8 planar RGB channel fix, the corrected comment type, newline cleanup, and a newer `convertPlanarRgbTensorToImageData` path that supersedes the old inline display comment.
- `vai-130-attempt-1-1779966195-hallucinate_app-source.patch`: dropped as already represented. The nested `duckdb_ipld_kit.py` cleanup path already logs a non-fatal cleanup warning instead of silently swallowing the exception.
- `vai-132-attempt-1-1779968911-hallucinate_app-source.patch`: ported. The nested `error_monitor.py` now normalizes full ISO-8601 timestamps before stack-trace matching, and `test_error_monitor.py` covers timestamp-only differences.
- `vai-133-attempt-1-1779967124-hallucinate_app-source.patch`: dropped as superseded. The nested GitHub issue reporter now distinguishes GitHub API errors and logs failures with `exc_info=True`, which preserves the traceback without reverting to a broad `logger.exception` call.
- `vai-137-attempt-1-1779971710-hallucinate_app-source.patch`: intentionally dropped. The nested plasma manager now raises after logging `put` and `get` failures so callers do not receive a confusing `None`; applying the preserved fallback-return behavior would change the current API contract. Temporary-file cleanup already logs `OSError` warnings.
- `vai-143-attempt-1-1780151927-hallucinate_app-source.patch`: dropped as already represented. The nested FAISS loader already logs temporary-index cleanup failures and pickle fallback failures.
- `vai-148-attempt-1-1780156054-hallucinate_app-source.patch`: ported. The nested `ipfs_kit.py` test cleanup now logs failed temp-file removal at debug level.
- `vai-149-attempt-1-1780164088-hallucinate_app-source.patch`: dropped as already represented. The nested mock IPFS add path already logs failed mock-storage reads as warnings.
- `vai-153-attempt-1-1780216008-hallucinate_app-source.patch`: partially ported. Metrics failure logging is already stronger via `logger.exception`; the brittle add/lookup test messages were replaced with explicit error-state handling and safe `dict.get` calls.
- `vai-179-attempt-1-1780240556-hallucinate_app-source.patch`: dropped as already represented. The nested content index lookup already logs `traceback.format_exc()`.
- `vai-192-attempt-1-1780252495-hallucinate_app-source.patch`: dropped as already represented. The nested thread pool scale-test drain already logs timeout and unexpected cleanup exceptions separately.

## Result

No old top-level source files were recreated. Valuable changes were ported into the current nested `hallucinate_app` source layout, and obsolete or already-represented diffs can be treated as reviewed during merged-worktree cleanup.
