# HAO-748 Merge Retry-Budget Finding: HAO-741

Date: 2026-07-08
Source task: HAO-741
Follow-up task: HAO-748
Retry budget: 3
Observed consecutive merge failures: 3

## Evidence

- Failed command: `git merge (main_checkout_dirty_conflict)`
- Attempts: 3, 4, 6
- Logs: /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-741-attempt-3.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-741-attempt-4.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-741-attempt-6.log
- Merge reason: `main_checkout_dirty_conflict`
- Dirty paths: hallucinate_app
- Branch: `implementation/hao-741-attempt-6-1783524989`
- Main worktree: `/home/barberb/lift_coding`


## Guardrail Result

The accelerator backlog refinery classified this as backlog work instead of
allowing another implementation attempt to loop on the same failure. The source
task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended for normal daemon parsing.

## Resolution

The repeated merge blocker was the dirty `hallucinate_app` gitlink in the main
checkout. In the HAO-748 attempt-5 repair worktree the dirty path traced to a
semantic nested submodule pointer update inside:

`hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py`

The unresolved pointer moved from `0b9fb4db5d0ae7411d0580164389397b158e5713`
to `9a808ea58e601d53c666b4e1c35e40dcd66fddde`, which is the newer
`ipfs_kit_py` commit already used by the HAO-741 attempt-6 branch family. The
repair committed that pointer in its owning nested repository and propagated the
gitlink commits outward so `hallucinate_app` is no longer dirty internally:

- `e901add4393a0592380f6013a0bc95d329eb637e` in the nested
  `ipfs_datasets_py` repository records the `.tools/ipfs_kit_py` pointer.
- `ab80c4da0a20efe05cc25555a8bd5cec6d1fb6eb` in the nested
  `ipfs_accelerate_py` repository records the repaired `ipfs_datasets_py`
  pointer.
- `b036fe1fe3810779e5dcd870a02fbd4285766284` in the nested `.tools/ipfs_kit_py`
  repository records the repaired `ipfs_accelerate_py` pointer.
- `abf2e0481dfdbc0de16e179243643a78ff4aaded` in
  `hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py` records the repaired
  `.tools/ipfs_kit_py` pointer.
- `ec067c8eef21b933880161a86070868dda6fb987` in
  `hallucinate_app/ipfs_accelerate_py` records the repaired `ipfs_datasets_py`
  pointer.
- `a5444bbfbf34e6ed01885a25874390a99fe5d2d2` in `hallucinate_app` records the
  repaired `ipfs_accelerate_py` pointer.

The packaged `ipfs-accelerate-agent-merge-resolver` console script is not
installed on `PATH` in this repair environment, so the equivalent module entry
point was run directly from `hallucinate_app/ipfs_accelerate_py`:

`python -m ipfs_accelerate_py.agent_supervisor.merge_resolver --events-path /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_events.jsonl --repo-root /home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-748-attempt-5-1783528669 --task-id HAO-741 --apply --command "bash -lc 'test -z \"$(git diff --name-only --diff-filter=U)\" && test -z \"$(git -C hallucinate_app status --porcelain=v1)\"'"`

The resolver found the HAO-741 attempt-6 `main_checkout_dirty_conflict` event,
reported dirty path `hallucinate_app`, and returned `applied: true` after the
manual semantic gitlink repair left no unmerged paths and a clean
`hallucinate_app` submodule working tree.

The full integration suite also exposed an external `ipfs_datasets` layout
drift: the legacy
`.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py` path now exists as
an empty compatibility file while the runnable demo lives under
`.tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py`. The repair
updates the SwissKnife and Meta Wearables DAT Android discovery code to select
the first non-empty Bucket VFS demo candidate while continuing to validate the
complete CLI/MCP surface against
`BUCKET_VFS_INTERFACES_COMPLETE.md`.

## Validation

- `test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-07-08-hao-748-hao-741-merge-retry-budget.md`
  passes.
- `python -m pytest tests/integration/test_mobile_external_ipfs_accelerate_interop.py -q`
  passes (8 passed), confirming the HAO-741 mobile to
  `external/ipfs_accelerate` objective evidence remains intact after the
  submodule merge repair.
- `python -m pytest tests/integration -q` was also attempted in this
  HAO-748 attempt-5 worktree. It failed outside the HAO-741 mobile /
  `external/ipfs_accelerate` surface with 31 failures caused by missing
  `external/meta-wearables-dat-android`, `external/meta-wearables-dat-ios`,
  and `external/ipfs_kit` descriptor files; the run still confirmed the
  focused mobile interop test above remains green.
