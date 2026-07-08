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
checkout. In this repair worktree the dirty path traced to a semantic nested
submodule pointer update inside:

`hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py`

The unresolved pointer moved from `0b9fb4db5d0ae7411d0580164389397b158e5713`
to `9a808ea58e601d53c666b4e1c35e40dcd66fddde`, which is the newer
`ipfs_kit_py` commit already used by the HAO-741 attempt-6 branch family. The
repair committed that pointer in its owning nested repository and propagated the
gitlink commits outward so `hallucinate_app` is no longer dirty internally:

- `eac8dffd7aa168f05154f52476b8517a4aba41fc` in the nested
  `ipfs_datasets_py` repository records the `.tools/ipfs_kit_py` pointer.
- `50ae54703b24ea72b3f00fc3355df594b9ecb68e` in the nested
  `ipfs_accelerate_py` repository records the repaired `ipfs_datasets_py`
  pointer.
- `b7a2577316bbb997bb53547abf106d90bff39ecf` in the nested `.tools/ipfs_kit_py`
  repository records the repaired `ipfs_accelerate_py` pointer.
- `56f3498f9823b01ff1bbb8c926a4deba1a314439` in
  `hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py` records the repaired
  `.tools/ipfs_kit_py` pointer.
- `239adab6e979bd51ef0de72ed32f4173706130a5` in
  `hallucinate_app/ipfs_accelerate_py` records the repaired `ipfs_datasets_py`
  pointer.
- `f7067edf9a443f35f95f7356a63ae5b580db7d4d` in `hallucinate_app` records the
  repaired `ipfs_accelerate_py` pointer.

The packaged `ipfs-accelerate-agent-merge-resolver` console script is not
installed on `PATH` in this repair environment, so the equivalent module entry
point was run directly from `hallucinate_app/ipfs_accelerate_py`:

`python -m ipfs_accelerate_py.agent_supervisor.merge_resolver --events-path /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_events.jsonl --repo-root /home/barberb/lift_coding/data/hallucinate_multimodal_control/worktrees/hao-748-attempt-4-1783527409 --task-id HAO-741 --apply --command "bash -lc 'test -z \"$(git diff --name-only --diff-filter=U)\" && git -C hallucinate_app status --porcelain=v1 | test ! -s /dev/stdin'"`

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
- `python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py tests/integration/test_swissknife_external_ipfs_datasets_interop.py -q`
  passes (15 passed), confirming the layout-drift compatibility repair.
- `python -m pytest tests/integration -q` passes (451 passed, 89 skipped),
  confirming the repaired worktree has no integration regressions.
