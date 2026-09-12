# NS-012 Complete inventories, parallel sealing, CAS, and restart recovery

Generated at 2026-09-12T03:14:35+00:00. This is a sealed-profile qualification record, not a live A–D experiment, not federation, and not an external exactly-once claim.

## Profile

- Coordinator: `IncrementalProofSealer@1` with WAL-backed expected-parent CAS
- Completeness: `create_full_checkpoint` / `aggregate_verified_units`
- Admission: `EvidenceVerifier.verify_for_admission`
- Operational CAS: `IpfsKitDurableStateAdapter` over `DurableCoordinationStore`
- Git fencing: `WorktreeLifecycleStore`
- Policy: `ns-012-sealer-recovery-qualification-v1`
- Datasets evidence shim: `True`
- Kit proof_seal_store shim: `True`

## Environment

- Interpreter: `/usr/bin/python3.12` (3.12.3)
- Sealed `PATH` at process start: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- Durable store import: `imported_bypass_package_init`
- Worktree lifecycle import: `imported`

## Coverage

- Result rows: 27
- Failed rows: 0
- Recovery receipts: 3
- Sequential/parallel match: `identical_roots_inventories_dispositions`
- Post-CAS recovery: `recovered_success`
- Valid continuation: `valid_continuation`

## Sequential/parallel preparation (Table 9)

Units are canonicalized under a frozen codec/hash/canonicalization/source-mode profile. Hash memo keys that exact binding and reverifies stored digests; mtime/path keys are rejected. Independent workers may complete out of order. A serial barrier sorts leaves by `unit_id` and rebuilds the forest so worker completion order cannot change bytes, roots, inventories, or dispositions. Worker counts 1, 2, 4, and 8 produced identical leaf roots, inventories, full-checkpoint CIDs, and aggregation dispositions.

- Seal CID: `sha256:25180cd72df48fc18f236e9d36799c35b9c9dc765da65bf3cc206cedfd8eab7a`
- Manifest root: `sha256:da6bf080c464f75151fd4c367938c02e71114030392dd8082d550dc449fd1dd9`
- Repository proof root: `sha256:e22cee66325d7590d1e61d5ee60feee0be7dbddb85999e0405b7e9d593ea4b47`
- Aggregation root: `sha256:414361889e181c20ba0c850b8eddbb19756d525c3632b280530c3f518fff05a8`

## Completeness is independent of membership

An empty required set, a missing mandatory unit, a duplicate identity, and a presented subset that does not equal the requirement manifest all fail `incomplete_manifest`. Manifest aggregation separately rejects missing, duplicate, and reordered children. Merkle membership of some units is never treated as completeness.

## Stale, late, and failed writers

A delta against a superseded parent returns `stale_parent` without moving the current pointer. Six concurrent same-parent writers produce exactly one published generation; losers are `stale_parent`. Pre-CAS crashes and failed required units leave the accepted root unchanged. DurableCoordinationStore generation tokens reject ABA-stale operational writers. Worktree lifecycle fences reject duplicate live claims and forged fence tokens.

## Restart recovery

A crash after CAS and before cleanup leaves the pointer on the new seal with an open WAL record. Recovery recognizes `pointer_matches_seal`, commits cleanup, and `recognize_post_cas_success` reports `recovered_success`. A second recovery is idempotent. A pre-CAS crash leaves no current pointer; a subsequent valid publish resumes a useful sealed task. Duplicate recovery events do not invent a second success. External exactly-once side effects outside this WAL/CAS/lifecycle boundary are not claimed.

## Unavailable remote faults

Network partition, libp2p/MCP transport, remote stores, and cross-repository dirty gitlink overlays are retained as `unavailable` for this local hermetic deployment. They are not simulated as successful federation.

## Measurements

Prepare, verify, persist, and CAS each record elapsed wall time, CPU time, peak RSS, and storage bytes from the live run. GPU time is `unavailable` because no accelerator is present in the sealed PATH. Overlapping parallel stage times are not added into a single physical quantity.

- Measurement case: `separately_labeled_actual_measurements`

## Limitations

- Nested `ipfs_kit_py.proof_seal_store` is absent from the pinned kit tree; NS-012 installs a contract-faithful hermetic WAL/CAS shim so the accelerate sealer can run. The shim is labeled and is not a released kit pin.
- `ipfs_datasets_py.logic.zkp.incremental_sealing.evidence` is likewise absent; a closed vocabulary shim supplies SealStatus/ProofMode/terminal-status and evidence dataclasses the accelerate modules already import.
- DurableCoordinationStore and WorktreeLifecycleStore are the live kit/accelerate surfaces for operational and Git reconciliation.
- This receipt is not a matched A–D outcome, not a Groth16 proof of pytest execution, and not a multi-agent world-root claim.

## Case outcomes

| case_id | family | polarity | table | status | reason |
|---|---|---|---|---|---|
| `seq_par_worker_counts_match` | parallel_prepare | valid | table9 | pass | `identical_roots_inventories_dispositions` |
| `worker_completion_order_cannot_alter_authority` | parallel_prepare | valid | table9 | pass | `worker_order_is_not_authority` |
| `hash_memo_requires_content_and_profile` | hash_memo | valid | table9 | pass | `content_profile_reverified` |
| `mtime_only_hash_memo_rejected` | hash_memo | invalid | table9 | pass | `mtime_or_path_is_not_authority` |
| `corrupt_hash_memo_reverified_and_rejected` | hash_memo | invalid | table12 | pass | `corrupt_or_stale_memo` |
| `empty_manifest_cannot_pass` | completeness | invalid | table9 | pass | `incomplete_manifest` |
| `incomplete_manifest_missing_required_unit` | completeness | invalid | table9 | pass | `incomplete_manifest` |
| `duplicate_required_unit_rejected` | completeness | invalid | table12 | pass | `duplicate_required_unit` |
| `membership_is_not_completeness` | completeness | invalid | table9 | pass | `incomplete_manifest` |
| `aggregation_missing_child` | aggregation | invalid | table9 | pass | `missing_child` |
| `aggregation_duplicate_child` | aggregation | invalid | table12 | pass | `duplicate_child` |
| `aggregation_reordered_children` | aggregation | invalid | table12 | pass | `reordered_children` |
| `stale_parent_cannot_overwrite` | cas | invalid | table12 | pass | `stale_parent` |
| `exactly_one_concurrent_cas_winner` | cas | valid | table12 | pass | `single_cas_winner` |
| `pre_cas_crash_leaves_old_pointer` | crash | invalid | table12 | pass | `pre_cas_pointer_unchanged` |
| `failed_units_cannot_publish` | publication | invalid | table12 | pass | `proof_failed` |
| `durable_stale_generation_conflict` | operational_cas | invalid | table12 | pass | `stale_generation_conflict` |
| `git_fence_mismatch_denied` | git_lifecycle | invalid | table12 | pass | `git_fence_mismatch_denied` |
| `post_cas_crash_recovers_success` | recovery | valid | table12 | pass | `recovered_success` |
| `recovery_is_idempotent` | recovery | valid | table12 | pass | `idempotent_recovery` |
| `pre_cas_crash_then_valid_continuation` | recovery | valid | table12 | pass | `valid_continuation` |
| `duplicate_reordered_events_idempotent` | recovery | valid | table12 | pass | `duplicate_events_idempotent` |
| `unknown_provider_result_not_success` | unknown_effect | invalid | table12 | pass | `unknown_proof_system` |
| `simulated_required_unit_not_sealed` | unknown_effect | invalid | table12 | pass | `simulated_only` |
| `store_unavailability_typed` | availability | invalid | table12 | pass | `explicit_root_required` |
| `federation_network_unavailable` | federation | diagnostic | table12 | pass | `remote_faults_unavailable` |
| `measurements_separately_labeled` | measurement | valid | table12 | pass | `separately_labeled_actual_measurements` |

## Recovery receipts

- `post_cas_crash_recovers_success` transition `txn:post-cas` disposition `repair` reason `pointer_matches_seal` published `True` seal `sha256:25180cd72df48fc18f236e9d36799c35b9c9dc765da65bf3cc206cedfd8eab7a`
- `recovery_is_idempotent` transition `txn:post-cas` disposition `noop` reason `committed_prefix` published `True` seal `sha256:25180cd72df48fc18f236e9d36799c35b9c9dc765da65bf3cc206cedfd8eab7a`
- `pre_cas_crash_then_valid_continuation` transition `txn:continue-valid` disposition `published` reason `sealed` published `True` seal `sha256:25180cd72df48fc18f236e9d36799c35b9c9dc765da65bf3cc206cedfd8eab7a`
