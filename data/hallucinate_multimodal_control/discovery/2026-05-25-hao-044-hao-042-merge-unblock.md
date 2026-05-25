# HAO-044 HAO-042 Merge Unblock

Date: 2026-05-25
Task: HAO-044
Source task: HAO-042

## Evidence Used

- `2026-05-25-hao-044-hao-042-merge-retry-budget.md` records three failed
  merges of `implementation/hao-042-attempt-3-1779713169`.
- The HAO-042 parent branch points `hallucinate_app` at submodule commit
  `a54282e581d268c7c1b6f0855601823896a3e3d4`.
- The current parent already pointed `hallucinate_app` at
  `64b2c120023b238c55663c1015359c6663596e4d`, which keeps the HAO-042 policy
  compatibility implementation while also retaining newer HAO-043/HAO-044
  board and discovery records.

## Resolution

The merge blocker was the divergent `hallucinate_app` gitlink, not a missing
policy-code change. In the `hallucinate_app` submodule, commit
`b23ba058e74aee458911182fc710db3d0d6aa34b` merges the HAO-042 implementation
commit as a parent while preserving the current tree. That makes the HAO-042
submodule commit an ancestor of the updated gitlink and avoids replaying the
older todo/discovery state from the failed merge branch.

`HAO-042` was also removed from the shared strategy `blocked_tasks` and
failed-merge `deprioritized_tasks` entries after this verification.

The intended HAO-042 implementation remains committed in the submodule:
`python/hallucinate_app/control_surface_policy.py` contains the scoped
`at_time` to `now` evaluator adapter, and
`python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
contains the real upstream regression plus populated-checkout path helper.

## Validation Evidence

- `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy'`
  passed.
- `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
  passed: 7 tests, 0 failures.
- `git -C hallucinate_app merge-base --is-ancestor a54282e581d268c7c1b6f0855601823896a3e3d4 HEAD`
  returned success after the HAO-044 submodule merge commit.
