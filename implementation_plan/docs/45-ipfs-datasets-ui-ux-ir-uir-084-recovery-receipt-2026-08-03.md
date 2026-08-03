# UIR-084 Exact Recovery Repair Receipt

- Schema: `ipfs-datasets-ui-ux-ir/recovery-repair-receipt@1`
- Repair task: `UIR-084`
- Source task: `UIR-002`
- Review timestamp: `2026-08-03T13:36:43Z`
- Reviewer/operator: Codex primary agent with two independent read-only supervisor audits
- Disposition: exact recovery dispatched once, integrated, and freshly validated; independent provider review remains the only UIR-002 acceptance gate

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

## Repaired supervisor and published recovery support

- Accelerator commit prepared for final reconciliation: `12c422b0e171ff3262baf1d7aa0443698d769b4a` (descendant of `0d8e6f189d772163210b177722a8cf589744d635`)
- Accelerator branch: `origin/agent/ui-ux-ir-supervisor-pin-port`
- Pre-repair UIIR accelerator pin: `753c5fd03db4c0f257fd11ead673a3ad27f1d053`
- UIIR accelerator pin before final publication: `8506f7ffefb64df255a0de4d7b9886d3057c19a0`
- Full daemon regression through integrated-recovery hardening: `642 passed`, `0 failed`
- Full backlog-refinery regression: `65 passed`, `0 failed`
- Full merge-queue regression after legacy completed-row normalization: `58 passed`, `0 failed`
- Focused merge-train regression after completed-retry normalization: `20 passed`, `0 failed`
- Focused integrated-recovery regression after final normalization: `14 passed`, `0 failed`
- Full post-merge review regression: `37 passed`, `0 failed`
- Post-merge evidence regression: `16 passed`, `0 failed`
- Independent affected regression sweep: `144 passed`, `0 failed`
- Composite-recovery implementation and review regression: `689 passed`, `0 failed`
- Final composite post-merge review regression: `45 passed`, `0 failed`
- Exact-provider/router/child compatibility regression: `204 passed`, `0 failed`, `1` opt-in live test skipped
- Capacity-aware reviewer regression: `90 passed`, `0 failed`; generated child compilation, `py_compile`, Ruff `E9/F63/F7/F82`, and `git diff --check` passed
- Isolated exact-provider subprocess regression: one failing `codex -m gpt-5.6-sol` invocation, zero Grok invocations
- Static checks: `py_compile`, Ruff `E9/F63/F7/F82`, and `git diff --check` passed

The repair permanently migrates the legacy denial-consumption witness, anchors the exact contiguous correction high-water, retains and revalidates both root and child recovery refs, fences target movement with an atomically published lease, and permits only the next content-bound correction grant. Its explicit migration path proves the exact historical source-task projection at every bindingless event baseline and at the frozen target, while permitting unrelated later board tasks; the automatic denial-consumption path retains its stricter whole-board rule. It does not turn the anchor itself into retry authority.

The later recovery commits admit only a ledger-bound zero-edit seed, distinguish a queue retry from an implementation attempt, re-fence already-integrated topology under the shared repository mutation lease, defer only an exact dead-owner lifecycle race, and clear stale retry reasons on both new completions and idempotently replayed legacy completed rows. They do not create an attempt beyond the authorized attempt 5.

Commit `c50f4747cc571e3c79244849a3918375b549e499` adds a separate `verified-composite-recovery-implementer-provenance@1` proof for the exact UIR-002 recovery. It binds the original Grok implementation events, the closed one-symbol deterministic correction, repair grant and consumption, immutable seed and integration boundary, current target ancestry and gitlink, and a fresh completed-queue witness. Processing-time witnesses cannot satisfy the proof, and ordinary provider provenance remains unchanged. This support permits the independent provider-review gate to evaluate the recovered implementation; it does not itself approve UIR-002.

Commit `efed1917260c1bf68483c22e6b21485f9bc53de7` fixes the live activation path after a fail-closed dry run exposed a semantic mismatch: durable authority state names the original denied commit, not the later recovery seed. The verifier now requires that denied commit to remain a valid full Git identity while the grant, consumption, seed, and Git-lineage fields continue to bind the recovery commit exactly. The real immutable recovery envelope reconstructs successfully, and malformed denial identities still fail closed.

The next acceptance-only reconciliation successfully minted the completed-queue recovery witness at sequence `2374`, event `sha256:bd1d169d373904842c76ad875c723db6ad05504c226d9ea8909106e5a8bc0249`, after fresh post-merge validation at sequence `2373`. It then failed closed at sequence `2375`: the reviewer requested exact `codex_cli`, but generic router error handling treated that explicit optional provider as eligible for remote failover and launched authenticated Grok after Codex failed. The child rejected the Grok result because its effective provider was not Codex, so no provider output was admitted and UIR-002 remained pending without an attempt 6.

Commit `5a6a0859500e44094b6b11b467555855149c88ba` separates remote cross-provider fallback from local fallback, disables provider and model failover for the exact post-merge reviewer before dispatch, binds both fallback permissions into response-cache identity, pins the isolated child to the exact accelerator source tree, and uses the operator-reviewed `gpt-5.6-sol` Codex model. Commit `5495615ba710fb76980957929ca8a2a47ed8f9e8` preserves version-one envelope and positional-constructor compatibility: an omitted new field retains legacy failover, while the UIR reviewer explicitly records `false`. The real isolated-child regression proves a failed exact Codex call cannot launch Grok.

The next exact-provider pass freshly validated the target at sequence `2404`, minted a recovery witness at sequence `2405`, and failed closed at sequence `2406` when Codex reported an account-wide usage limit. Direct exact-provider probes of `gpt-5.6-sol`, `codex-auto-review`, and `gpt-5.4-mini` all reported the same account limit, with the CLI's explicit next eligible time normalized to `2026-08-10T05:23:00Z`. No Grok process was launched, no provider result was admitted, and no implementation attempt 6 was created.

Commit `12c422b0e171ff3262baf1d7aa0443698d769b4a` transports that condition as a prompt-free, allowlisted typed capacity envelope and records only bounded reset metadata. The supervisor now applies an account-wide Codex review latch before bounded candidate selection, preserves unrelated merge work, advertises the durable wake deadline, and uses a one-shot expiry projection so stale events cannot create a hot loop. Unrelated review failures cannot clear the latch; only a later admitted or denied provider review does. This scheduling repair cannot mint completion authority and preserves queue attempt 2 and implementation attempt 5.

## Reviewed UIR-002 rescue

- Current target root before this repair: `0cf371a5e0e9b3691ac84b567d1d4fab33bf2a99`
- Current target child gitlink: `82eda806eb958e7c547e67bfb0c42b4dc000d829`
- Approved recovery child: `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`
- Approved recovery child tree: `884ee7a95624fa8d1e908b2fc58fd384bbbdd839`
- Retention branch: `origin/rescue/uir-002-attempt-2-stable-test-symbol`
- Evidence-only replay root (never a migration seed): `6f65f3188c3d3e43443a911b466c5b1326c0c59e`
- Frozen recovery baseline `T`: `2c119d08541f8e0783d6138878ff1260130adce4`
- Immutable recovery seed: `1d2fd4b589ca67f46e5461597c4d2230110b74f9`
- Immutable recovery seed tree: `cfba92d1fb498e4d8f98aa7cf5838e6a2036faf5`

The approved child is a descendant of the current child gitlink and preserves the reviewed baseline test symbol. It is intentionally a sibling of rejected attempt-3 child `e61e2e0cf2d6ce9cd18f24f5f21ee753eb84d49e`; ancestry from that rejected sibling is neither required nor claimed.

## Test receipt

- Working tree: clean checkout of `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`
- Python: `/usr/bin/python3 -P`, Python `3.12.3`
- Accelerator `PYTHONPATH`: clean `0d8e6f189d772163210b177722a8cf589744d635` checkout
- Command: `python -m pytest tests/unit/logic/ui_ux_ir/test_mcp_idl_identity_contract.py -q`
- Population: `32 collected`, `32 passed`, `0 failed`, `0 skipped`
- Return code: `0`
- Test-file SHA-256: `5592ee7b6deba4c8ab4bf5ee11bdae96c707b2ac8cf8cec60aeb83d26d8087d2`
- Captured-output SHA-256: `93232f039d75515bbc53f2588ba31f0751c3492871fb0ab00d86a7161f9eb17f`
- Captured-output bytes: `1019`
- Accelerator-pin publication revalidation: the same declared command passed `32/32` against final accelerator commit `efed1917260c1bf68483c22e6b21485f9bc53de7`
- Capacity-latch publication revalidation: the same declared command passed `32/32` against accelerator commit `12c422b0e171ff3262baf1d7aa0443698d769b4a`

This unit-test receipt was review evidence, not dispatch authority and not a substitute for the proposal gate. Machine authority was subsequently derived in order from the durable high-water anchor, this completed task's immutable repair binding, the strict `repair_granted` transition, and transactional `grant_consumed` evidence for attempt 5.

## Executed bounded recovery

1. The sole authorized attempt 5 started at event sequence `2226`, event ID `sha256:dc1e4d42849c6cd67db581ace2bb94d3337a5e5600860d60375f660b404b615a`, with exact command `[/usr/bin/true]`.
2. Attempt 5 finished successfully at sequence `2258`, event ID `sha256:e78fdf3bbb0d5db8bd2a6d06cca1391998ecbedc08fd80f5c1f6bb942622e5d7`, and handed immutable seed `1d2fd4b589ca67f46e5461597c4d2230110b74f9` to merge request `1785744933984518972-3572011-c7be2096267d`.
3. The target integrated the seed as merge commit `39f774a7286574b2aeacb1ef98b2f69bc041acbd`, with parents exactly `2c119d08541f8e0783d6138878ff1260130adce4` and `1d2fd4b589ca67f46e5461597c4d2230110b74f9`, tree `cfba92d1fb498e4d8f98aa7cf5838e6a2036faf5`, and dataset gitlink `3b6e9cf4d6c055e443cbf652ce829e108bd86b27`.
4. A controlled dead-owner lifecycle reclaim advanced the exact attempt-5 record to terminal fence `4`; one non-implementing queue replay then completed the request and deleted the root and changed-dataset worktrees/branches.
5. Fresh post-merge validation passed the declared `32`-test command at event sequence `2315`, receipt `baguqeera64kngokafpaifzu7rbliz6k6kjxrkcpdoriho2k4qjgudil2cnua`, against exact commit `39f774a7286574b2aeacb1ef98b2f69bc041acbd` and tree `cfba92d1fb498e4d8f98aa7cf5838e6a2036faf5`.
6. Acceptance reconciliation at sequences `2316` and `2317` confirms merge, freshness, semantic, proof, and deterministic-only gates. Only independent `provider_review` remains pending, so UIR-002 correctly stays `todo` rather than being marked complete early.
7. No attempt 6 was created and no implementation start exists after sequence `2226`.
8. The final idempotent queue reconciliation kept the request `completed`, queue attempt `2`, implementation attempt `5`, failure count `1`, and claim generation `7`, while normalizing the obsolete `merge_cleanup_failed` terminal reason to empty in both DuckDB and the completed JSON receipt. It neither claimed work nor changed implementation authority.
9. After the composite verifier was activated, a later acceptance-only pass minted the exact completed recovery witness at sequence `2374`; this was evidence reconciliation, not an implementation attempt.
10. The same pass rejected an unintended Grok reviewer fallback at sequence `2375`. Accelerator commits `5a6a0859500e44094b6b11b467555855149c88ba` and `5495615ba710fb76980957929ca8a2a47ed8f9e8` now fence the reviewer to one exact Codex/model route before any provider fallback can run.
11. A later exact-provider reconciliation at sequences `2404`-`2408` freshly revalidated and preserved every non-provider acceptance gate, then left UIR-002 pending on the external Codex capacity window without launching Grok or creating attempt 6. Accelerator commit `12c422b0e171ff3262baf1d7aa0443698d769b4a` converts that external condition into durable provider-wide scheduling rather than repeated validation and review churn.

The initial post-merge consumer exposed one additional supervisor defect: producer attempt 5 materialized `external/ipfs_datasets`, `external/ipfs_accelerate`, `swissknife`, and `hallucinate_app`, while legacy queue metadata carried only the changed dataset path. The narrower consumer therefore omitted the unchanged accelerator from the first validation checkout and left three exact prunable sibling registrations. A read-only preflight re-proved the exact root, queue, attempt, gitlink, branch-tip, reflog, protection-ref, and porcelain bindings; compare-and-delete cleanup then removed those three registrations and their daemon-only branches plus the exact locked detached validation registration. The root commit and working-tree diff were unchanged, all commit tips remain protected, and no broad worktree prune was used. Producer dependency binding and cleanup lifecycle redesign remain a separately preserved follow-up; the unsafe broad draft was not published. This does not alter the successful integration or authorize another implementation attempt.
