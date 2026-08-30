# Parallel Content Sealing and Proof-Carrying TDD — PCTDD-PLAN-V1.1

Status: sealed bootstrap control amendment. Namespace: `parallel-content-sealing-proof-carrying-tdd-v1`.

## V1.1 control amendment and generation migration

This revision amends `PCTDD-PLAN-V1` after g5 exposed a
control-plane defect: non-executable validation prose was materialized as a
command and repeated database claims could outlive the intended attempt cap.
The g5 database, event watermark, accepted PCTDD-000 receipt, failures, and 29
rescue branches remain immutable history. Nothing in g5 is reopened or
silently promoted. The successor is a fresh `pctdd-v1-g6` authority at
`data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6`, served by `quack:127.0.0.1:27278`.

Every task names one protected validation profile through a task-bound
dispatcher. Profiles contain argv arrays only and execute with `shell=False`.
Prose, shell operators, unresolved aliases, mismatched task IDs, incomplete
profile coverage, and profile drift fail before provider dispatch. Recorded W1
rescue commits are exact-reuse candidates only and require independent g6
source/profile/policy validation before admission.

## Outcome and invariant

Build and self-host a fail-closed fast TDD route across the existing accelerator, datasets, and kit authorities. The normative order is: verified exact content reuse; parallel immutable hash/seal preparation; exact datasets-owned semantic selection; fixture-aware execution-key construction; current setup; verified call reuse or current call; current teardown; signed receipt; asynchronous aggregate ZK certification; incremental proof-forest update; serial seal publication; deterministic repair/procedure reuse; minimal-context LLM only for a typed residual.

Parallel work may prepare immutable candidates and independently verify hashes, signatures, proofs, leaves, branches, and blocks. Final ordered WAL append, persisted-byte rehash, generation fence, expected-parent CAS, and current-root publication remain serial, controller-owned, and fail closed.

## Claim boundaries

- A CID establishes exact byte identity under its versioned canonicalization/multicodec/multihash profile, not execution or semantics. A Git blob OID is a verified memo lookup key only; filesystem metadata is candidate-only. A chunk manifest does not replace the raw full-stream CID.
- A signed execution receipt is an allowlisted issuer assertion under verifier-selected policy/key/epoch/revocation state, not independent execution proof.
- An aggregate ZK proof establishes only that the committed admitted receipt set satisfies the selected circuit. It does not prove CPython execution and cannot exceed or upgrade its leaf evidence.
- A direct execution proof establishes only the declared machine/program/committed inputs and outputs.
- An incremental seal commits an accepted parent plus complete valid changed/reused units. `TestPassStatementV1` remains unchanged; composite and aggregate successors are versioned.
- Simulated, mock, structural, or integrity-only proof paths are never production admission. Unknown dependency completeness broadens execution and proving.

## Authority reconciliation

`ipfs_datasets_py` owns deterministic semantic/proof schemas, selection, fixture/test identities, statement meaning, and commitment codecs. `ipfs_kit_py` owns verified immutable storage, hash/branch candidate records, proof forest persistence, WAL, recovery, and root CAS without deciding semantic admission. `ipfs_accelerate_py` owns source freezing, scheduling, pytest/xdist execution, receipt admission, proof batching, fast-loop composition, repair/context/procedure integration, and operational acceptance. Existing IncrementalProofSealer, proof-reuse plugin, semantic-state selector, signed runner attestations, TestPass statements, proof store/WAL/CAS, verification planner, Tactician/Hammer, semantic compression, and procedure compiler are predecessors to extend—not duplicate.

The operational task authority is DuckDB through one authenticated loopback Quack owner. DuckLake is a rebuildable, non-authoritative history/analytics projection that cannot schedule, admit, complete, or block a task. Markdown is sealed bootstrap intent only; PCTDD-000 becomes complete solely through evidence-gated DuckDB CAS.

## Technical workstreams

1. Canonicalize once into `PreparedCanonicalBlock@1`, rehash wherever trust crosses, memoize exact source/profile mappings, preserve raw SHA/CID, and add separate chunk manifests.
2. Bound filesystem readers, canonicalizers, hashers, verifiers, provers, store writers, and Merkle reducers. Preserve completion-order-independent output.
3. Build full/delta prepared seals and affected-branch Merkle updates without publication authority; shorten the existing serial sealer commit.
4. Derive collection seed, fixture-definition closure, reviewed fixture-instance commitment, `TestExecutionKeyV2`, and final trace. Opaque or incomplete adapters force full execution.
5. Make post-setup/pre-call reuse primary while running current teardown/finalizers. Pre-setup reuse stays narrowly pure/replay-safe. Never label proof reuse as pytest skip.
6. Bind composite phase receipts to signed runner policy; batch selected populations into aggregate statements/proofs asynchronously; keep direct CPython proof optional.
7. Compose exact selection, receipts, forest delta, seal, repair, compressed residual context, and proof-carrying procedure compilation in `FastTddLoopController@1`.

## Rollout and waves

The closed rollout is `bootstrap -> shadow_hash -> shadow_reuse -> shadow_proof -> protected -> required`. Promotion requires zero identity divergence, false phase reuse, stale reuse, selection false-negative regression, simulated admission, self-authority, unauthorized publication, lost update, escaped critical mutation, or secret/witness leak. Missing performance targets produce non-promotion, never weakened safety.

```text
W0 PCTDD-000
W1 PCTDD-001|002|003|004
W2 PCTDD-005|006|007|021|023|033
W3 PCTDD-008|009|010|022|024|026|034
W4 PCTDD-011|012|013|025|032
W5 PCTDD-014|015|018|027|030|035
W6 PCTDD-016|017|028|029|031|036
W7 PCTDD-019|037|038|039
W8 PCTDD-020|040
W9 PCTDD-041|042|043
W10 PCTDD-044
W11 PCTDD-045
W12 PCTDD-046
W13 PCTDD-047
W14 PCTDD-048
W15 PCTDD-049|050
W16 PCTDD-051
W17 PCTDD-052
W18 PCTDD-053
```

Each worker receives a unique lease/fence/worktree, exact task CID and tree, bounded allowed paths/resources/context, verifier-owned acceptance, and one unique receipt. Shared exports, registries, plugin hooks, schemas, gitlinks, scheduler controls, and release evidence serialize through the current merge authority.

## Verification and benchmarks

Identity tests require serial/parallel/native byte and root equality, strict decoding, profile separation, and Git/chunk identity boundaries. Memo/Merkle tests cover corruption, dirty overlays, mode/type changes, full fallback, stale parents/snapshots, concurrent writers, crash phases, and recovery. Pytest tests cover closure invalidation, privacy-safe adapters, setup/call/teardown truth, xdist controller authority, signatures, aggregate completeness, cancellation, malicious workers, and import safety.

Preregistered hash workloads cover small/mixed/large files, clean and dirty states, 1/10/50% deltas, cold/warm memo, full/delta seal, bounded 1/2/4/8/16 workers, local and reproducible slow I/O. TDD workloads cover all fixture/reuse/proof classes. Supervisor metrics count model calls/tokens/context and exact avoidance causes. Targets are >=90% fewer warm unchanged bytes, >=50% faster 1% delta preparation, >=30% faster warm selected loops, >=25% fewer repeat general-model repairs, and >=30% smaller median model context, all subordinate to zero-regression floors.

## Terminal and rollback

Required completion means every mandatory task has accepted or explicitly permitted typed terminal evidence, validators pass, identities match, the required-mode capstone has complete pre/post roots and publication receipt, and final roots verify transitively. No unavailable prover/key ceremony/performance result may be fabricated. Rollback disables policy promotion, invalidates successor evidence, restores full hashing/execution/reproof fallback, and uses existing WAL/CAS recovery without rewriting predecessor history.
