# HAO-424 Resolution

Date: 2026-06-12
Task: HAO-424
Source task: HAO-326
Kind: merge retry-budget repair

## Finding

The retry-budget evidence in
`2026-06-12-hao-424-hao-326-merge-retry-budget.md` showed repeated merge
failures for `implementation/hao-326-attempt-1-1781241072`.

The intended HAO-326 implementation lives in the `external/ipfs_kit` submodule,
but fresh worktrees could not materialize the expected file because
`.gitmodules` configured `external/ipfs_kit` to clone
`https://github.com/endomorphosis/ipfs_kit_py` while the parent gitlink pointed
at commits from `https://github.com/endomorphosis/ipfs_kit`. Submodule
initialization failed before the merge daemon could verify
`external/ipfs_kit/archive/applied_patches/fix_all_storacha.py`.

## Repair

Updated the `external/ipfs_kit` submodule URL to
`https://github.com/endomorphosis/ipfs_kit` and advanced the parent gitlink to
`58873ab257104981aa9ba7bee0c2368369716be7`, the HAO-326 implementation commit.
That commit is reachable from the corrected remote and contains
`archive/applied_patches/fix_all_storacha.py`.

The `backup_file` function in the materialized file correctly catches only
`(OSError, shutil.Error)`, logs the traceback with `logger.exception`, and
returns `None` on failure. The `update_storacha_kit` caller checks that return
value before replacing `storacha_kit.py`, so the original swallowed-exception
finding is fixed in the owning submodule.

Because the blocker was submodule materialization and not a semantic source
conflict, `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` was
not run.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_all_storacha.py
test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-06-12-hao-424-hao-326-merge-retry-budget.md
```

Both commands passed.
