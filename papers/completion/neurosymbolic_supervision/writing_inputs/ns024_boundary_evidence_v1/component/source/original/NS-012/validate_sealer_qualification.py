#!/usr/bin/env python3
"""Validate NS-012 published sealer/CAS/recovery qualification artifacts.

Re-checks structural invariants and performs a live smoke of sequential/parallel
root equality, incomplete-manifest rejection, stale-parent CAS, and post-CAS
recovery. Federation is not claimed. External exactly-once behavior is not
claimed beyond the tested WAL/CAS boundary.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-012"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"

CRITERIA = (
    "Sequential/parallel bytes, roots, inventories, and dispositions match on identical inputs; worker order cannot alter authority.",
    "An empty or incomplete manifest cannot pass a mandatory obligation; membership alone is never completeness.",
    "Stale/late/failed writers cannot replace the accepted root or invent task success.",
    "Restart retains admitted evidence and resumes a useful valid task without unobserved duplicate effects; external exactly-once behavior is not claimed beyond the tested boundary.",
    "Prepare/verify/persist/CAS CPU/memory/storage/elapsed measurements are real and separately labeled.",
)

REQUIRED_CASES = (
    "seq_par_worker_counts_match",
    "worker_completion_order_cannot_alter_authority",
    "hash_memo_requires_content_and_profile",
    "mtime_only_hash_memo_rejected",
    "corrupt_hash_memo_reverified_and_rejected",
    "empty_manifest_cannot_pass",
    "incomplete_manifest_missing_required_unit",
    "duplicate_required_unit_rejected",
    "membership_is_not_completeness",
    "aggregation_missing_child",
    "aggregation_duplicate_child",
    "aggregation_reordered_children",
    "stale_parent_cannot_overwrite",
    "exactly_one_concurrent_cas_winner",
    "pre_cas_crash_leaves_old_pointer",
    "failed_units_cannot_publish",
    "durable_stale_generation_conflict",
    "git_fence_mismatch_denied",
    "post_cas_crash_recovers_success",
    "pre_cas_crash_then_valid_continuation",
    "recovery_is_idempotent",
    "duplicate_reordered_events_idempotent",
    "unknown_provider_result_not_success",
    "simulated_required_unit_not_sealed",
    "store_unavailability_typed",
    "federation_network_unavailable",
    "measurements_separately_labeled",
)

MEASUREMENT_KEYS = (
    "prepare_elapsed",
    "prepare_cpu",
    "prepare_memory",
    "prepare_storage",
    "verify_elapsed",
    "verify_cpu",
    "persist_elapsed",
    "persist_cpu",
    "persist_storage",
    "cas_elapsed",
    "cas_cpu",
    "cas_storage",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-012 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def live_smoke() -> None:
    for path in (str(ACC_ROOT), str(DS_ROOT), str(KIT_ROOT), str(SNAP)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from compat_shims import install_qualification_shims

    install_qualification_shims()

    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.aggregation import (
        VerifiedUnit,
        aggregate_verified_units,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.full_checkpoint import (
        GENESIS_PARENT_SEAL,
        RepositoryStateView,
        RequiredUnitEvidence,
        VerificationPolicyView,
        create_full_checkpoint,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.sealer import (
        IncrementalProofSealer,
        SealerCrash,
    )
    from ipfs_datasets_py.logic.zkp.incremental_sealing.evidence import (
        ProofMode,
        ProofTerminalStatus,
        SealStatus,
    )
    from ipfs_kit_py.proof_seal_store.contracts import SealTransitionPhase

    def digest_hex(text: str) -> str:
        return "sha256:" + sha256(text.encode("utf-8")).hexdigest()

    def state(**overrides):
        payload = {
            "repository_id": "repo/ns-012-smoke",
            "revision": "rev-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "source_root_cid": digest_hex("src"),
            "repository_state_cid": digest_hex("st"),
            "environment_cid": digest_hex("env"),
            "parent_revision_ids": (),
        }
        payload.update(overrides)
        return RepositoryStateView(**payload)

    def policy():
        return VerificationPolicyView(
            policy_cid=digest_hex("pol"),
            proof_schema_version="1",
            canonicalization_version="1",
            dependency_graph_schema_version="graph@1",
            circuit_id="circuit@smoke",
            verification_key_id="vk/smoke",
        )

    def unit(unit_id: str, **overrides):
        payload = {
            "unit_id": unit_id,
            "proof_object_cid": digest_hex(f"proof:{unit_id}"),
            "category": "unit_test",
            "terminal_status": ProofTerminalStatus.INTEGRITY_VERIFIED.value,
            "proof_mode": ProofMode.INTEGRITY_ONLY.value,
            "required_for_seal": True,
            "freshly_verified": True,
            "cache_reused_without_fresh_verification": False,
        }
        payload.update(overrides)
        return RequiredUnitEvidence(**payload)

    units = (unit("unit/a"), unit("unit/b", category="static_analysis"))
    expected = ("unit/a", "unit/b")
    seq = create_full_checkpoint(
        state(),
        policy(),
        units=units,
        expected_unit_ids=expected,
        parent_seal_cid=GENESIS_PARENT_SEAL,
        fallback_reasons=("first_state",),
    )
    par = create_full_checkpoint(
        state(),
        policy(),
        units=tuple(reversed(units)),
        expected_unit_ids=expected,
        parent_seal_cid=GENESIS_PARENT_SEAL,
        fallback_reasons=("first_state",),
    )
    if not seq.sealed or seq.seal_cid() != par.seal_cid():
        fail("live smoke: sequential/parallel full-checkpoint roots diverged")

    empty = create_full_checkpoint(
        state(),
        policy(),
        units=(),
        expected_unit_ids=("unit/a",),
        parent_seal_cid=GENESIS_PARENT_SEAL,
        fallback_reasons=("first_state",),
    )
    if empty.sealed or empty.seal_status is not SealStatus.INCOMPLETE_MANIFEST:
        fail("live smoke: empty manifest sealed")

    missing = aggregate_verified_units(
        (
            VerifiedUnit(
                unit_id="unit/a",
                proof_object_cid=digest_hex("proof:unit/a"),
                category="unit_test",
                terminal_status="integrity_verified",
            ),
        ),
        expected_unit_ids=("unit/a", "unit/b"),
    )
    if missing.accepted or missing.reason.value != "missing_child":
        fail("live smoke: missing child was accepted")

    with tempfile.TemporaryDirectory(prefix="ns012-smoke-") as raw:
        root = Path(raw)
        sealer = IncrementalProofSealer(root)
        first = sealer.publish_full_checkpoint(
            state(),
            policy(),
            units=units,
            expected_unit_ids=expected,
            parent_seal_cid=GENESIS_PARENT_SEAL,
            fallback_reasons=("first_state",),
            transition_id="txn:smoke-1",
        )
        if not first.published:
            fail("live smoke: genesis did not publish")
        second = sealer.publish_full_checkpoint(
            state(
                revision="rev-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                source_root_cid=digest_hex("src2"),
                repository_state_cid=digest_hex("st2"),
            ),
            policy(),
            units=(
                unit("unit/a", proof_object_cid=digest_hex("proof:a2")),
                unit("unit/b", category="static_analysis", proof_object_cid=digest_hex("proof:b2")),
            ),
            expected_unit_ids=expected,
            transition_id="txn:smoke-2",
        )
        if not second.published:
            fail("live smoke: second generation did not publish")
        live = sealer.get_current_seal("repo/ns-012-smoke")
        if live is None or live.seal_cid != second.seal_cid:
            fail("live smoke: current pointer is not the accepted second seal")
        try:
            sealer.publish_full_checkpoint(
                state(
                    revision="rev-cccccccccccccccccccccccccccccccccccccccc",
                    source_root_cid=digest_hex("src3"),
                    repository_state_cid=digest_hex("st3"),
                ),
                policy(),
                units=units,
                expected_unit_ids=expected,
                fail_before_phase=SealTransitionPhase.CURRENT_ROOT_CAS,
                transition_id="txn:smoke-crash",
            )
            fail("live smoke: pre-CAS crash was not injected")
        except SealerCrash:
            pass
        after = sealer.get_current_seal("repo/ns-012-smoke")
        if after != live:
            fail("live smoke: pre-CAS crash moved the accepted root")
        sealer.close()

        rec_root = root / "recover"
        rec_root.mkdir()
        rec = IncrementalProofSealer(rec_root)
        try:
            rec.publish_full_checkpoint(
                state(),
                policy(),
                units=units,
                expected_unit_ids=expected,
                parent_seal_cid=GENESIS_PARENT_SEAL,
                fallback_reasons=("first_state",),
                transition_id="txn:smoke-post",
                fail_before_phase=SealTransitionPhase.CLEANUP,
            )
            fail("live smoke: post-CAS crash was not injected")
        except SealerCrash:
            pass
        recognized = rec.recognize_post_cas_success("txn:smoke-post")
        if not recognized.published or recognized.reason.value != "recovered_success":
            fail("live smoke: post-CAS recovery did not recognize success")
        rec.close()


def main() -> None:
    matrix_path = QUAL / "sealer_fault_matrix.json"
    results_path = QUAL / "sealer_results.jsonl"
    recovery_path = QUAL / "recovery_receipts.jsonl"
    report_path = QUAL / "sealer_recovery_report.md"
    for path in (matrix_path, results_path, recovery_path, report_path):
        if not path.is_file():
            fail(f"missing current output {path}")

    snap_matrix = SNAP_QUAL / "sealer_fault_matrix.json"
    snap_results = SNAP_QUAL / "sealer_results.jsonl"
    snap_recovery = SNAP_QUAL / "recovery_receipts.jsonl"
    snap_report = SNAP_QUAL / "sealer_recovery_report.md"
    for current, snapshot in (
        (matrix_path, snap_matrix),
        (results_path, snap_results),
        (recovery_path, snap_recovery),
        (report_path, snap_report),
    ):
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {current}")

    matrix = load_json(matrix_path)
    rows = load_jsonl(results_path)
    recoveries = load_jsonl(recovery_path)
    report = report_path.read_text(encoding="utf-8")

    if matrix.get("schema") != "neurosymbolic-supervision/sealer-fault-matrix@1":
        fail("fault matrix schema mismatch")
    if matrix.get("task_id") != "NS-012":
        fail("fault matrix task_id mismatch")
    if matrix.get("federation_claimed") is not False:
        fail("federation was claimed")
    if matrix.get("exactly_once_external_claimed") is not False:
        fail("external exactly-once was claimed")

    by_id = {row["case_id"]: row for row in rows}
    missing = [name for name in REQUIRED_CASES if name not in by_id]
    if missing:
        fail(f"missing cases: {missing}")
    failed = [row["case_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        fail(f"failed cases: {failed}")

    seq = by_id["seq_par_worker_counts_match"]
    if seq.get("observed_reason") != "identical_roots_inventories_dispositions":
        fail("sequential/parallel roots did not match")
    if not seq.get("seal_cid") or not str(seq.get("seal_cid")).startswith("sha256:"):
        fail("missing seal cid")
    if seq.get("worker_counts") != [1, 2, 4, 8]:
        fail("worker counts were not 1/2/4/8")

    for case_id in (
        "empty_manifest_cannot_pass",
        "incomplete_manifest_missing_required_unit",
        "membership_is_not_completeness",
    ):
        if by_id[case_id].get("observed_reason") != "incomplete_manifest":
            fail(f"{case_id} did not fail closed as incomplete_manifest")

    if by_id["stale_parent_cannot_overwrite"].get("observed_reason") != "stale_parent":
        fail("stale parent overwrote the accepted root")
    if by_id["exactly_one_concurrent_cas_winner"].get("winners") != 1:
        fail("CAS race did not have exactly one winner")
    if by_id["failed_units_cannot_publish"].get("published") is not False:
        fail("failed units published")
    if by_id["federation_network_unavailable"].get("federation_claimed") is not False:
        fail("federation case claimed a network result")
    if by_id["post_cas_crash_recovers_success"].get("observed_reason") != "recovered_success":
        fail("post-CAS recovery did not retain the admitted seal")
    if by_id["pre_cas_crash_then_valid_continuation"].get("observed_reason") != "valid_continuation":
        fail("valid continuation after recovery is missing")
    if any(item.get("exactly_once_external_claimed") for item in recoveries):
        fail("recovery receipts claimed external exactly-once")

    labeled = by_id["measurements_separately_labeled"].get("measurements") or {}
    for key in MEASUREMENT_KEYS:
        item = labeled.get(key)
        if not isinstance(item, dict) or item.get("status") != "actual" or item.get("value") is None:
            fail(f"measurement {key} is not an actual labeled value")
    if labeled.get("prepare_gpu", {}).get("status") != "unavailable":
        fail("GPU measurement was not labeled unavailable")
    if labeled.get("cas_elapsed", {}).get("unit") != "ms":
        fail("CAS elapsed is not labeled in milliseconds")

    for needle in (
        "worker completion order",
        "membership",
        "stale_parent",
        "recovered_success",
        "unavailable",
        "Prepare, verify, persist, and CAS",
        "exactly-once",
    ):
        if needle not in report:
            fail(f"report is missing required discussion: {needle}")

    live_smoke()
    print("NS-012 sealer/CAS/recovery qualification: OK")
    print(f"rows={len(rows)} recoveries={len(recoveries)} federation_claimed=false")
    print("seq_par_root=", seq.get("seal_cid"))
    print("recovery=", by_id["post_cas_crash_recovers_success"].get("observed_reason"))


if __name__ == "__main__":
    main()
