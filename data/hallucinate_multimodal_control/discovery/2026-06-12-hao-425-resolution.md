# HAO-425 Resolution: HAO-353 Merge Retry Budget

Date: 2026-06-12
Repair task: HAO-425
Source task: HAO-353

## Finding

The HAO-353 merge retry was not blocked by a missing change in
`external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py`.
The intended swallowed-exception fix is already committed in the current
`external/ipfs_kit` submodule line:

- `79a1b697` logs PID-file cleanup failures in `kill_existing_servers()`.
- `79a1b697` logs server termination cleanup failures in `main()`.
- `79a1b697` is an ancestor of the current submodule commit `1c33f283`.

The stale HAO-353 branch points `external/ipfs_kit` at `58873ab2`, which would
rewind the submodule from `1c33f283` and drop newer fixes. The HAO-353
submodule pointer should not be accepted during merge repair.

## Merge Repair

Keep the current `external/ipfs_kit` pointer at `1c33f283` or newer. Resolve
the HAO-353 top-level merge by preserving the current submodule pointer and
handling only the two semantic doc conflicts reported by `git merge-tree`:

- `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`
- `implementation_plan/docs/19-virtual-ai-os-submodule-integration.md`

`ipfs-accelerate-agent-merge-resolver` was not available in this worktree, so
the resolver command could not be run here.

## Verification

- `git -C external/ipfs_kit merge-base --is-ancestor 79a1b697 HEAD` returned
  success.
- `git -C external/ipfs_kit merge-base --is-ancestor 58873ab257104981aa9ba7bee0c2368369716be7 HEAD`
  returned success.
- `git merge-tree` showed doc conflicts only; the `fixed_runner.py` fix is
  already present in the current submodule commit.
