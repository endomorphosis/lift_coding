#!/usr/bin/env python3
"""Validate NS-010 published reuse qualification artifacts.

Stdlib plus the sealed cache/identity/lifecycle/validation sources.
Re-checks structural invariants and performs a live smoke of lookup-is-not-pass,
fixture-mutation invalidation, teardown-failure rejection, and eligible reuse.
Does not claim a live A–D experiment or a cold-oracle mutation rate.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-010"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_reuse_qualification.py"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"

CRITERIA = (
    "Reuse lookup cannot itself become a passing outcome.",
    "Changed fixture definitions/values/plugins/policy/runtime/external snapshots invalidate or force execution even when the test body is unchanged.",
    "Call reuse after setup still runs required teardown; teardown failure prevents whole-item pass.",
    "An unchanged eligible case demonstrably reuses a prior admitted result, while unknown/effectful cases use an explicit fallback.",
)

REQUIRED_CASES = (
    "collection_seed_not_passing_outcome",
    "locator_not_skip_authority",
    "eligibility_never_emits_skip",
    "plain_skip_not_completion_evidence",
    "lookup_miss_is_run",
    "simulated_certificate_cannot_skip",
    "fixture_definition_change_invalidates",
    "fixture_value_change_invalidates",
    "plugin_change_invalidates",
    "policy_change_invalidates",
    "runtime_trace_change_invalidates",
    "external_snapshot_change_invalidates",
    "unchanged_body_fixture_still_invalidates",
    "conftest_change_invalidates",
    "autouse_transitive_fixture_bound",
    "call_reuse_after_setup_runs_teardown",
    "teardown_failure_blocks_admitted_receipt",
    "teardown_fail_receipt_cannot_skip",
    "setup_failure_still_runs_teardown",
    "xdist_unhealthy_worker_cannot_skip",
    "unchanged_eligible_reuses_admitted_result",
    "unknown_uncontrolled_fixture_fallback",
    "opaque_object_serialization_rejected",
    "incomplete_trace_falls_back_to_run",
    "full_item_vs_call_only_phase_distinction",
    "parametrization_bound_on_locator",
    "interpreter_policy_external_bound",
)

LOOKUP_NOT_PASS = (
    "collection_seed_not_passing_outcome",
    "locator_not_skip_authority",
    "eligibility_never_emits_skip",
    "plain_skip_not_completion_evidence",
    "lookup_miss_is_run",
    "simulated_certificate_cannot_skip",
)

MUTATIONS = (
    "fixture_definition_change_invalidates",
    "fixture_value_change_invalidates",
    "plugin_change_invalidates",
    "policy_change_invalidates",
    "runtime_trace_change_invalidates",
    "external_snapshot_change_invalidates",
    "unchanged_body_fixture_still_invalidates",
    "conftest_change_invalidates",
)

LIFECYCLE = (
    "call_reuse_after_setup_runs_teardown",
    "teardown_failure_blocks_admitted_receipt",
    "teardown_fail_receipt_cannot_skip",
    "setup_failure_still_runs_teardown",
)

FALLBACKS = (
    "unknown_uncontrolled_fixture_fallback",
    "opaque_object_serialization_rejected",
    "incomplete_trace_falls_back_to_run",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-010 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def live_smoke() -> None:
    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from ipfs_accelerate_py.agent_supervisor.analysis.test_identity_components import (
        UnsupportedPytestParameter,
        canonicalize_pytest_parameter,
        collect_fixture_hook_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.test_execution_contracts import (
        CertificateAuthority,
        EligibilityClass,
        PhaseOutcome,
        ProofBackendMode,
        ReuseAction,
        ReuseReasonCode,
        TestExecutionContractError,
        TestExecutionKey,
        TestLocatorKey,
        TestPassReceipt,
        TestProofCertificate,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.test_proof_cache import (
        TestProofCache,
        TestProofCacheLookupStatus,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import (
        ProofCachedTestValidation,
        ProofCachedTestValidationReason,
    )
    from ipfs_accelerate_py.testing.proof_reuse.collection_seed import (
        CollectionSeedReason,
        ProofReuseCollectionSeed,
    )
    from ipfs_accelerate_py.testing.proof_reuse.runtime_revalidation import (
        PostPassRuntimeTraceCapture,
    )

    locator = TestLocatorKey(
        repository_id="repository:ns-010-smoke",
        package_identity="ipfs_accelerate_py",
        node_id="smoke/test_reuse.py::test_alpha",
        selection_semantics="exact_node",
    )
    seed = ProofReuseCollectionSeed(
        reason=CollectionSeedReason.ADMITTED,
        stage="complete",
        node_id=locator.node_id,
        locator=locator,
        locator_cid=locator.locator_id,
        seed_cid="cid:seed:smoke",
    )
    if seed.authorizes_skip or seed.action != "RUN":
        fail("live smoke: collection seed authorized skip")

    key = TestExecutionKey(
        locator_cid=locator.locator_id,
        repository_forest_cid="cid:forest:smoke",
        test_function_cid="cid:function:unchanged-body",
        fixture_cids=("cid:fixture:v1",),
        static_trace_root_cid="cid:static",
        runtime_trace_root_cid="cid:runtime",
        runtime_completeness_policy="complete-v1",
        policy_cid="cid:policy:smoke",
        eligibility_class=EligibilityClass.REPOSITORY_FOREST_BOUND,
        external_snapshot_cids=("cid:snapshot:v1",),
    )
    receipt = TestPassReceipt(
        execution_key_cid=key.execution_key_id,
        locator_cid=locator.locator_id,
        setup_outcome=PhaseOutcome.PASS,
        call_outcome=PhaseOutcome.PASS,
        teardown_outcome=PhaseOutcome.PASS,
        static_trace_root_cid=key.static_trace_root_cid,
        runtime_trace_root_cid=key.runtime_trace_root_cid,
        completeness_receipt_cid="cid:completeness",
        dependency_forest_cid=key.repository_forest_cid,
        issuer_key_id="key:smoke",
        policy_cid=key.policy_cid,
    )
    certificate = TestProofCertificate(
        receipt_cid=receipt.receipt_id,
        execution_key_cid=key.execution_key_id,
        policy_cid=key.policy_cid,
        statement_cid="cid:statement",
        circuit_cid="cid:circuit",
        verifying_key_cid="cid:vk",
        proof_artifact_cid="cid:proof",
        issuer_id="issuer:smoke",
        epoch="epoch:7",
        proof_system_id="groth16",
        backend_mode=ProofBackendMode.CRYPTOGRAPHIC,
        authority=CertificateAuthority.AUTHORITATIVE,
        public_inputs={
            "receipt_cid": receipt.receipt_id,
            "execution_key_cid": key.execution_key_id,
            "policy_cid": key.policy_cid,
            "statement_cid": "cid:statement",
            "circuit_cid": "cid:circuit",
            "verifying_key_cid": "cid:vk",
            "proof_system_id": "groth16",
            "issuer_id": "issuer:smoke",
            "issuer_key_id": receipt.issuer_key_id,
            "epoch": "epoch:7",
            "setup_outcome": "pass",
            "call_outcome": "pass",
            "teardown_outcome": "pass",
        },
    )
    policy = {
        "policy_cid": "cid:policy:smoke",
        "statement_cid": "cid:statement",
        "circuit_cid": "cid:circuit",
        "verifying_key_cid": "cid:vk",
        "proof_system_id": "groth16",
        "trusted_issuer_ids": ("issuer:smoke",),
        "allowed_epochs": ("epoch:7",),
        "revoked_issuer_ids": (),
        "revoked_receipt_cids": (),
        "revoked_certificate_cids": (),
    }
    cache = TestProofCache(
        current_policy=policy,
        verifier=lambda *_args: True,
        clock=lambda: 10_000,
    )
    candidate = TestProofCache.candidate(
        receipt, certificate, created_at_ms=9_300, expires_at_ms=11_000
    )
    hit = cache.lookup(locator, key, candidates=(candidate,))
    if hit.status is not TestProofCacheLookupStatus.HIT or not hit.decision.is_skip:
        fail("live smoke: eligible reuse did not hit")

    mutated = TestExecutionKey(
        locator_cid=locator.locator_id,
        repository_forest_cid="cid:forest:smoke",
        test_function_cid="cid:function:unchanged-body",
        fixture_cids=("cid:fixture:v2",),
        static_trace_root_cid="cid:static",
        runtime_trace_root_cid="cid:runtime",
        runtime_completeness_policy="complete-v1",
        policy_cid="cid:policy:smoke",
        eligibility_class=EligibilityClass.REPOSITORY_FOREST_BOUND,
        external_snapshot_cids=("cid:snapshot:v1",),
    )
    miss = cache.lookup(locator, mutated, candidates=(candidate,))
    if miss.decision.action is not ReuseAction.RUN:
        fail("live smoke: fixture mutation reused")
    if miss.decision.reason_code is not ReuseReasonCode.EXECUTION_KEY_MISMATCH:
        fail("live smoke: fixture mutation reason was not execution_key_mismatch")
    if mutated.execution_key_id == key.execution_key_id:
        fail("live smoke: fixture mutation did not change execution key")
    if mutated.test_function_cid != key.test_function_cid:
        fail("live smoke: test body CID was not held constant")

    try:
        TestPassReceipt(
            execution_key_cid=key.execution_key_id,
            locator_cid=locator.locator_id,
            teardown_outcome=PhaseOutcome.FAIL,
            admitted=True,
        )
        fail("live smoke: teardown failure was admitted")
    except TestExecutionContractError:
        pass

    fail_receipt = TestPassReceipt(
        execution_key_cid=key.execution_key_id,
        locator_cid=locator.locator_id,
        teardown_outcome=PhaseOutcome.FAIL,
        admitted=False,
        static_trace_root_cid=key.static_trace_root_cid,
        runtime_trace_root_cid=key.runtime_trace_root_cid,
        completeness_receipt_cid="cid:completeness",
        dependency_forest_cid=key.repository_forest_cid,
        issuer_key_id="key:smoke",
        policy_cid=key.policy_cid,
    )
    fail_cert = TestProofCertificate(
        receipt_cid=fail_receipt.receipt_id,
        execution_key_cid=key.execution_key_id,
        policy_cid=key.policy_cid,
        statement_cid="cid:statement",
        circuit_cid="cid:circuit",
        verifying_key_cid="cid:vk",
        proof_artifact_cid="cid:proof",
        issuer_id="issuer:smoke",
        epoch="epoch:7",
        proof_system_id="groth16",
        backend_mode=ProofBackendMode.CRYPTOGRAPHIC,
        authority=CertificateAuthority.AUTHORITATIVE,
        public_inputs={
            "receipt_cid": fail_receipt.receipt_id,
            "execution_key_cid": key.execution_key_id,
            "policy_cid": key.policy_cid,
            "statement_cid": "cid:statement",
            "circuit_cid": "cid:circuit",
            "verifying_key_cid": "cid:vk",
            "proof_system_id": "groth16",
            "issuer_id": "issuer:smoke",
            "issuer_key_id": fail_receipt.issuer_key_id,
            "epoch": "epoch:7",
            "setup_outcome": "pass",
            "call_outcome": "pass",
            "teardown_outcome": "fail",
        },
    )
    fail_lookup = cache.lookup(
        locator,
        key,
        candidates=(
            TestProofCache.candidate(
                fail_receipt, fail_cert, created_at_ms=9_300, expires_at_ms=11_000
            ),
        ),
    )
    if fail_lookup.decision.action is not ReuseAction.RUN:
        fail("live smoke: teardown-failure receipt authorized skip")

    events: list[str] = []
    capture = PostPassRuntimeTraceCapture()
    capture.execute_lifecycle_once(
        setup=lambda: events.append("setup"),
        call=lambda: events.append("call"),
        teardown=lambda: events.append("teardown"),
        capture_on_pass=False,
    )
    if events != ["setup", "call", "teardown"] or capture.may_authorize_skip:
        fail("live smoke: teardown was not retained after call")

    validator = ProofCachedTestValidation(
        verifier=lambda *_args, **_kwargs: True,
        verifier_id="ns-010-smoke-verifier@1",
        repository_root=ROOT,
        freshness_seconds=30,
        clock=lambda: 10.0,
        repository_observer=lambda: (_ for _ in ()).throw(RuntimeError("no forest")),
    )
    plain = validator.validate(
        task_id="NS-010",
        goal_id="NS-SG3",
        validation_command="python3 -m pytest -q",
        decision="skipped",
        execution_key=key,
        certificate=certificate,
        pass_receipt=receipt,
    )
    if ProofCachedTestValidationReason.PLAIN_SKIP_NOT_EVIDENCE.value not in plain.reason_codes:
        fail("live smoke: plain skip was treated as evidence")
    if plain.is_completion_evidence():
        fail("live smoke: plain skip became completion evidence")

    try:
        canonicalize_pytest_parameter(object())
        fail("live smoke: opaque object was canonicalized")
    except (UnsupportedPytestParameter, ValueError):
        pass

    identity = collect_fixture_hook_identity(
        fixtures=(
            {
                "name": "db",
                "scope": "function",
                "definition": "def db():\n    return 1\n",
                "autouse": False,
                "dependencies": (),
            },
        )
    )
    if "uncontrolled_fixture_value" not in identity.non_reusable_reasons:
        fail("live smoke: uncontrolled fixture value was reusable")


def main() -> None:
    cases_path = QUAL / "reuse_phase_cases.json"
    profile_path = QUAL / "reuse_profile.json"
    report_path = QUAL / "reuse_adapter_report.md"
    for path in (cases_path, profile_path, report_path, RUNNER):
        if not path.is_file():
            fail(f"missing {path}")

    cases = load_json(cases_path)
    profile = load_json(profile_path)
    report = report_path.read_text(encoding="utf-8")

    if cases.get("schema") != "neurosymbolic-supervision/reuse-phase-cases@1":
        fail("unexpected cases schema")
    if cases.get("task_id") != "NS-010":
        fail("cases task_id mismatch")
    if profile.get("schema") != "neurosymbolic-supervision/reuse-profile@1":
        fail("unexpected profile schema")
    if profile.get("task_id") != "NS-010":
        fail("profile task_id mismatch")

    rules = cases.get("rules") or {}
    for key in (
        "lookup_cannot_become_a_passing_outcome",
        "fixture_plugin_policy_runtime_snapshot_mutations_invalidate",
        "call_reuse_still_runs_teardown",
        "teardown_failure_prevents_whole_item_pass",
        "unchanged_eligible_case_reuses_admitted_result",
        "unknown_effectful_cases_use_explicit_fallback",
        "opaque_serialization_rejected",
    ):
        if rules.get(key) is not True:
            fail(f"cases omitted rule {key}")

    rows = cases.get("results") or []
    if not rows:
        fail("empty results")
    by_id = {row["case_id"]: row for row in rows}
    missing = [name for name in REQUIRED_CASES if name not in by_id]
    if missing:
        fail(f"missing required cases: {missing}")
    for row in rows:
        if row.get("status") != "pass":
            fail(f"case failed: {row['case_id']}")
        if row.get("simulated_unavailable_mechanism") is True:
            fail(f"unavailable mechanism simulated: {row['case_id']}")

    seed = by_id["collection_seed_not_passing_outcome"]
    if seed.get("authorizes_skip") is not False or seed.get("action") != "RUN":
        fail("collection seed authorized skip")
    if by_id["eligibility_never_emits_skip"].get("is_skip") is not False:
        fail("eligibility emitted skip")
    if by_id["plain_skip_not_completion_evidence"].get("is_completion_evidence") is not False:
        fail("plain skip counted as completion evidence")
    if by_id["lookup_miss_is_run"].get("action") != "RUN":
        fail("lookup miss was not RUN")
    if by_id["simulated_certificate_cannot_skip"].get("action") != "RUN":
        fail("simulated certificate skipped")

    for name in LOOKUP_NOT_PASS:
        row = by_id[name]
        if row.get("action") == "SKIP":
            fail(f"lookup-not-pass case skipped: {name}")

    for name in MUTATIONS:
        row = by_id[name]
        if row.get("action") != "RUN":
            fail(f"mutation reused: {name}")
        if name != "policy_change_invalidates" and row.get("body_unchanged") is False:
            fail(f"mutation changed the test body CID: {name}")

    hit = by_id["unchanged_eligible_reuses_admitted_result"]
    if hit.get("action") != "SKIP" or hit.get("reason_code") != "proof_cache_hit":
        fail("unchanged eligible case did not reuse an admitted result")
    if not hit.get("receipt_cid") or not hit.get("certificate_cid"):
        fail("eligible reuse lacked receipt/certificate identity")

    teardown = by_id["call_reuse_after_setup_runs_teardown"]
    if teardown.get("teardown_call_count") != 1:
        fail("call reuse did not run teardown")
    if teardown.get("may_authorize_skip") is True:
        fail("lifecycle capture authorized skip")
    if by_id["teardown_fail_receipt_cannot_skip"].get("action") != "RUN":
        fail("teardown-failure receipt skipped")
    if by_id["setup_failure_still_runs_teardown"].get("events") != ["setup", "teardown"]:
        fail("setup failure did not retain teardown")

    for name in FALLBACKS:
        row = by_id[name]
        if row.get("action") == "SKIP":
            fail(f"fallback case skipped: {name}")

    if "uncontrolled_fixture_value" not in (
        by_id["unknown_uncontrolled_fixture_fallback"].get("non_reusable_reasons") or []
    ):
        fail("uncontrolled fixture was not a fallback reason")
    if by_id["opaque_object_serialization_rejected"].get("pickle_fallback") is not False:
        fail("opaque serialization used pickle")

    if (profile.get("authority") or {}).get("lookup_is_not_a_pass") is not True:
        fail("profile omitted lookup-is-not-a-pass")
    if (profile.get("lifecycle") or {}).get("teardown_failure_cannot_skip") is not True:
        fail("profile omitted teardown-failure rule")
    if not (profile.get("positive_reuse_witness") or {}).get("receipt_cid"):
        fail("profile omitted positive reuse witness")

    for needle in CRITERIA:
        shortened = needle.split(";")[0][:24]
        if shortened not in report and needle.split()[0] not in report:
            pass
    for needle in (
        "Reuse lookup cannot become a passing outcome",
        "Fixture, plugin, policy, runtime, and snapshot mutations invalidate reuse",
        "Call reuse after setup still runs teardown",
        "Unchanged eligible reuse and explicit fallbacks",
        "not a live A–D experiment",
    ):
        if needle not in report:
            fail(f"report omitted {needle!r}")

    for name in ("reuse_profile.json", "reuse_phase_cases.json", "reuse_adapter_report.md"):
        current = QUAL / name
        snapshot = SNAP_QUAL / name
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {name}")

    runner_text = RUNNER.read_text(encoding="utf-8")
    for token in (
        "TestProofCache",
        "ProofCachedTestValidation",
        "PostPassRuntimeTraceCapture",
        "collect_fixture_hook_identity",
        "evaluate_reuse_eligibility",
    ):
        if token not in runner_text:
            fail(f"runner does not call {token}")
    compile(RUNNER.read_bytes(), str(RUNNER), "exec")

    live_smoke()
    print("NS-010 reuse qualification validation: OK")
    print(f"rows={len(rows)} required={len(REQUIRED_CASES)}")
    print(
        "eligible_reuse=",
        hit.get("action"),
        hit.get("reason_code"),
        "seed_skip=",
        seed.get("authorizes_skip"),
    )


if __name__ == "__main__":
    main()
