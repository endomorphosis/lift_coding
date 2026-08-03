# UIR-084 Exact Recovery Repair Receipt

- Schema: `ipfs-datasets-ui-ux-ir/recovery-repair-receipt@1`
- Repair task: `UIR-084`
- Source task: `UIR-002`
- Review timestamp: `2026-08-03T07:33:49Z`
- Reviewer/operator: Codex primary agent with two independent read-only supervisor audits
- Disposition: operational repair completed; exact migration, grant, and one bounded dispatch remain separately fail-closed

## Exact source binding

- Source task CID: `baguqeerae2bmbcm4pssx6rfs3cdgfo275skgk7w5sd3gqdcotddv7qk3s67a`
- Source task key: `task/v1/2682c0899c7ca57f44b2d88662bb5fec94657edd90f6680c4e98c75fc15b97be`
- Source task binding: `baguqeerazbiagz4kwmmpxoxbjfzofndu65nytsumawrqeci4x2bs64wvu46a`
- Denial: `baguqeeralmno2gek33r62naxxenldlqi6ky6hsole47j2pkhfkzhhiauiyra`
- Consumed denial witness: `baguqeeratizeets5x7nsbr3tsuw6ppydjgaxwpatcyckjgodifjjguvrrlaq`
- Failed high-water attempt: `4`
- Terminal event: `sha256:a164918f64e256d3cb6f75bbc3606021ec3aa0d52f470bb7099b4a22337fde61` at sequence `2165`
- Failure kind: `implementation` (`implementation_state_recovered`, reason `inflight_process_missing`)
- Origin stream: `event-log:sha256:07d0903cfe9a1370cbed08e153c45ce6722e382e2ff9700081075bb69209183e`

## Repaired supervisor

- Accelerator commit: `d9fc951f65f31d04eee3baa7fe12e1bab6f10582`
- Accelerator branch: `origin/agent/ui-ux-ir-supervisor-pin-port`
- Prior UIIR accelerator pin: `753c5fd03db4c0f257fd11ead673a3ad27f1d053`
- Full daemon regression: `602 passed`, `0 failed`
- Full merge-queue regression: `56 passed`, `0 failed`
- Focused migration/consumption regressions: `2 passed`, `0 failed`
- Static checks: `py_compile`, Ruff `E9/F821/F822/F823`, and `git diff --check` passed

The repair permanently migrates the legacy denial-consumption witness, anchors the exact contiguous correction high-water, retains and revalidates both root and child recovery refs, fences target movement with an atomically published lease, and permits only the next content-bound correction grant. It does not turn the anchor itself into retry authority.

## Reviewed UIR-002 rescue

- Current target root before this repair: `0cf371a5e0e9b3691ac84b567d1d4fab33bf2a99`
- Current target child gitlink: `82eda806eb958e7c547e67bfb0c42b4dc000d829`
- Approved recovery child: `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`
- Approved recovery child tree: `884ee7a95624fa8d1e908b2fc58fd384bbbdd839`
- Retention branch: `origin/rescue/uir-002-attempt-2-stable-test-symbol`
- Evidence-only replay root (never a migration seed): `6f65f3188c3d3e43443a911b466c5b1326c0c59e`
- Recovery parent `T`: the `agent/ui-ux-ir` commit containing this receipt and the completed UIR-084 block; its exact ID is recorded in the operator backup manifest before migration

The approved child is a descendant of the current child gitlink and preserves the reviewed baseline test symbol. It is intentionally a sibling of rejected attempt-3 child `e61e2e0cf2d6ce9cd18f24f5f21ee753eb84d49e`; ancestry from that rejected sibling is neither required nor claimed.

## Test receipt

- Working tree: clean detached checkout of `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`
- Python: `/usr/bin/python3 -P`, Python `3.12.3`
- Accelerator `PYTHONPATH`: clean `d9fc951f65f31d04eee3baa7fe12e1bab6f10582` checkout
- Command: `python -m pytest tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py -q`
- Population: `32 collected`, `32 passed`, `0 failed`, `0 skipped`
- Return code: `0`
- Test-file SHA-256: `5592ee7b6deba4c8ab4bf5ee11bdae96c707b2ac8cf8cec60aeb83d26d8087d2`
- Captured-output SHA-256: `91b9b17534ceedcd84dd670b33f10dbad352b0aa8373aee6caa9a65d79d7b172`
- Captured-output bytes: `1019`

This unit-test receipt is review evidence, not dispatch authority and not a substitute for the proposal gate. Machine authority must still be derived in order from the durable high-water anchor, this completed task's immutable repair binding, the strict `repair_granted` transition, and transactional `grant_consumed` evidence for attempt 5.

## Required activation order

1. Keep all UIIR supervisors and generated-board writers stopped.
2. Freeze `agent/ui-ux-ir` at the commit containing this receipt; do not run a daemon before migration.
3. Migrate attempts 2 through 4 with approved child `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`.
4. Verify one `legacy_high_water_anchored` record and an unchanged target `T`.
5. Run one non-implementing pass to mint the exact attempt-5 repair grant.
6. Run at most one implementing pass, scoped only to `UIR-002`, from the retained recovery seed.

Any target movement, binding change, missing retention ref, competing lock, duplicate start, or authority mismatch must stop the recovery without invoking a provider.
