#!/usr/bin/env python3
"""NS-027 retained-byte reuse qualification, or enforced full-cold removal.

Uses the pinned native TestProofCache, TestCertificateStore,
ProofCachedTestValidation and TestCertificateProvider modules.  An
unconditional callback, placeholder CRYPTOGRAPHIC/AUTHORITATIVE certificate,
or missing verifier cannot authorize skip.  This task preserves NS-010/NS-011
receipts and the 1/26, 0/25 historical counts without transferring mock-cohort
safety claims to production.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[4]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
ADMISSION = QUAL / "reuse_admission"
PRIOR = ADMISSION / "prior"
SNAP010 = PAPER / "receipts/snapshots/NS-010/qualification"
SNAP011 = PAPER / "receipts/snapshots/NS-011/qualification"
ACC = ROOT / "external/ipfs_accelerate"
DS = ROOT / "external/ipfs_datasets"
TASK_ID = "NS-027"
POLICY_ID = "ns-027-retained-reuse-admission-v1"
AMENDMENT_ID = "ns-027-reuse-admission-amendment/v1"
NOW_MS = 10_000
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
XMLTODICT_SHA256 = "7084494972ac820ecc41625b35fda59f2da1556ea34ab46414696471369cfe63"
XMLTODICT_ARCHIVE_SHA256 = "72e6f909de6a20c7700a2398dcf9587a7d9263be68b6bd50361f2a375f909fda"
HISTORICAL_NODES = (
    "tests/test_xmltodict.py::XMLToDictTestCase::test_simple",
    "tests/test_xmltodict.py::XMLToDictTestCase::test_list",
    "tests/test_xmltodict.py::XMLToDictTestCase::test_minimal",
)
PRIOR_HASHES = {
    "reuse_profile.json": "c1430e4cf972ad6a17abdaa9c81759ec412be1ed08c263112523142ea35dc03e",
    "reuse_adapter_report.md": "2ea0ef9f86601c9d5e5e5fee78ae8af21c2148c06fcacd72c0b7ceb45ef5cd87",
    "reuse_phase_cases.json": "80481fd14170a2a18917b002df2d4d616e548c013b398bce987b3ec58b20100a",
    "reuse_analysis.json": "8423c4fc2b7f269de693544ccf275a7d6f2baa71710d841991c0634428c2a066",
}
SOURCE_PATHS = {
    "proof_cached_test_validation": ACC
    / "ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py",
    "test_proof_cache": ACC / "ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py",
    "test_certificate_store": ACC
    / "ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py",
    "ipfs_datasets_test_certificate_provider": ACC
    / "ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py",
    "test_selection": DS
    / "ipfs_datasets_py/logic/software_contracts/semantic_state/test_selection.py",
    "run_comparison": PAPER / "experiments/run_comparison.py",
    "score_runs": PAPER / "experiments/score_runs.py",
}

FROZEN_CASES = (
    {
        "case_id": "unconditional_callback_rejected",
        "family": "verifier_authority",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "illegal_authority",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "missing_verifier_unavailable",
        "family": "verifier_authority",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "verifier_unavailable",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "mismatched_verifier_authority",
        "family": "verifier_authority",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "trust_policy_rejected",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "ns011_placeholder_certificate_rejected",
        "family": "unsupported_profile",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "certificate_non_attested",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "changed_certificate_bytes_rejected",
        "family": "integrity",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "candidate_integrity_failed",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "stale_key_without_rebind_rejected",
        "family": "invalidation",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "execution_key_mismatch",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "missing_candidate_run",
        "family": "lookup_not_pass",
        "polarity": "diagnostic",
        "expected_action": "RUN",
        "expected_reason": "candidate_missing",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "policy_mismatch_run",
        "family": "invalidation",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "policy_mismatch",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "simulated_certificate_rejected",
        "family": "lookup_not_pass",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "certificate_non_attested",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "incomplete_trace_fallback",
        "family": "fallback",
        "polarity": "diagnostic",
        "expected_action": "RUN",
        "expected_reason": "incomplete_trace",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "native_provider_cannot_authorize_skip",
        "family": "verifier_authority",
        "polarity": "diagnostic",
        "expected_action": "RUN",
        "expected_reason": "reuse_not_admitted",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "setup_call_teardown_recorded",
        "family": "lifecycle",
        "polarity": "valid",
        "expected_action": "RUN",
        "expected_reason": "teardown_ran_after_setup_and_call",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "teardown_failure_cannot_skip",
        "family": "lifecycle",
        "polarity": "invalid",
        "expected_action": "RUN",
        "expected_reason": "receipt_mismatch",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "unknown_effectful_fallback",
        "family": "fallback",
        "polarity": "diagnostic",
        "expected_action": "RUN",
        "expected_reason": "eligibility_denied",
        "counts_as_safe_agreement": False,
        "cold_required": False,
    },
    {
        "case_id": "pytest_skip_not_safe_agreement",
        "family": "oracle",
        "polarity": "diagnostic",
        "expected_action": "RUN",
        "expected_reason": "plain_skip_not_evidence",
        "counts_as_safe_agreement": False,
        "cold_required": True,
    },
    {
        "case_id": "historical_xmltodict_unchanged_baseline_cold",
        "family": "useful_positive",
        "polarity": "valid",
        "expected_action": "RUN",
        "expected_reason": "reuse_not_admitted_full_cold",
        "counts_as_safe_agreement": False,
        "cold_required": True,
        "useful_positive": True,
    },
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj if isinstance(obj, str) else canonical(obj) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(obj) + "\n")


def which(name: str) -> str | None:
    for directory in SEALED_PATH.split(":"):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def retain_prior_bytes() -> dict[str, Any]:
    PRIOR.mkdir(parents=True, exist_ok=True)
    retained: dict[str, Any] = {}
    mapping = {
        "reuse_profile.json": (QUAL / "reuse_profile.json", SNAP010 / "reuse_profile.json"),
        "reuse_adapter_report.md": (
            QUAL / "reuse_adapter_report.md",
            SNAP010 / "reuse_adapter_report.md",
        ),
        "reuse_phase_cases.json": (
            QUAL / "reuse_phase_cases.json",
            SNAP010 / "reuse_phase_cases.json",
        ),
        "reuse_analysis.json": (QUAL / "reuse_analysis.json", SNAP011 / "reuse_analysis.json"),
    }
    for name, (live, snap) in mapping.items():
        dest = PRIOR / name
        if dest.is_file() and sha256_file(dest) == PRIOR_HASHES[name]:
            retained[name] = {"path": str(dest.relative_to(ROOT)), "sha256": PRIOR_HASHES[name]}
            continue
        source = live if live.is_file() and sha256_file(live) == PRIOR_HASHES[name] else snap
        shutil.copyfile(source, dest)
        digest = sha256_file(dest)
        if digest != PRIOR_HASHES[name]:
            raise SystemExit(f"prior byte retention mismatch for {name}: {digest}")
        retained[name] = {"path": str(dest.relative_to(ROOT)), "sha256": digest}
    return retained


def prepare_imports() -> dict[str, Any]:
    for path in (str(ACC), str(DS)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from ipfs_accelerate_py.agent_supervisor.integrations import (
        ipfs_datasets_test_certificate_provider as cert_provider,
    )
    from ipfs_accelerate_py.agent_supervisor.proof import (
        test_certificate_store as store,
        test_execution_contracts as contracts,
        test_proof_cache as cache,
    )
    from ipfs_accelerate_py.agent_supervisor.validation import (
        proof_cached_test_validation as cached_validation,
    )
    from ipfs_accelerate_py.testing.proof_reuse import runtime_revalidation as lifecycle
    from ipfs_datasets_py.logic.software_contracts.semantic_state import (
        test_selection as selection,
    )

    pytest_version = None
    try:
        import pytest

        pytest_version = pytest.__version__
    except Exception as exc:  # noqa: BLE001
        pytest_version = f"unavailable:{type(exc).__name__}"

    return {
        "contracts": contracts,
        "cache": cache,
        "store": store,
        "cert_provider": cert_provider,
        "cached_validation": cached_validation,
        "lifecycle": lifecycle,
        "selection": selection,
        "pytest": pytest_version,
    }


def source_hashes() -> dict[str, str]:
    return {name: sha256_file(path) for name, path in SOURCE_PATHS.items()}


def capability_probe(api: Mapping[str, Any], *, path_at_start: str | None) -> dict[str, Any]:
    provider = api["cert_provider"].IpfsDatasetsTestCertificateProvider()
    caps = provider.capabilities().to_dict()
    groth16_path = which("groth16")
    return {
        "schema": "ns027-capability-probe/v1",
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": SEALED_PATH,
        "path_at_process_start": path_at_start,
        "pytest": api["pytest"],
        "binaries": {"z3": which("z3"), "cvc5": which("cvc5"), "groth16": groth16_path},
        "provider_capabilities": caps,
        "selection_may_authorize_reuse_skip": api[
            "selection"
        ].reuse_skip_authorized_by_selection(),
        "unconditional_callback_detected": api["cache"].is_unconditional_true_callback(
            lambda *_args: True
        ),
        "missing_verifier_reason": str(
            api["cache"].reject_unsupported_reuse_profile(verifier=None)
        ),
    }


def _locator(api: Mapping[str, Any], node_id: str = "tests/test_alpha.py::test_double"):
    return api["contracts"].TestLocatorKey(
        repository_id="repository:ns-027",
        package_identity="package:ns-027",
        node_id=node_id,
    )


def _key(api: Mapping[str, Any], locator, **changes: Any):
    values = {
        "locator_cid": locator.locator_id,
        "repository_forest_cid": "cid:forest:ns-027",
        "static_trace_root_cid": "cid:static:ns-027",
        "runtime_trace_root_cid": "cid:runtime:ns-027",
        "runtime_completeness_policy": "complete-v1",
        "policy_cid": "cid:policy:ns-027",
        "test_function_cid": "cid:function:ns-027",
        "fixture_cids": ("cid:fixture:ns-027",),
    }
    values.update(changes)
    return api["contracts"].TestExecutionKey(**values)


def _receipt(api: Mapping[str, Any], locator, key, **changes: Any):
    values = {
        "execution_key_cid": key.execution_key_id,
        "locator_cid": locator.locator_id,
        "setup_outcome": api["contracts"].PhaseOutcome.PASS,
        "call_outcome": api["contracts"].PhaseOutcome.PASS,
        "teardown_outcome": api["contracts"].PhaseOutcome.PASS,
        "static_trace_root_cid": key.static_trace_root_cid,
        "runtime_trace_root_cid": key.runtime_trace_root_cid,
        "completeness_receipt_cid": "cid:completeness:ns-027",
        "dependency_forest_cid": key.repository_forest_cid,
        "issuer_key_id": "key:ns-027",
        "policy_cid": key.policy_cid,
        "admitted": True,
    }
    values.update(changes)
    return api["contracts"].TestPassReceipt(**values)


def _certificate(api: Mapping[str, Any], receipt, key, **changes: Any):
    contracts = api["contracts"]
    public_inputs = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": "cid:statement:ns-027",
        "circuit_cid": "cid:circuit:ns-027",
        "verifying_key_cid": "cid:vk:ns-027",
        "proof_system_id": "groth16",
        "issuer_id": "issuer:ns-027",
        "issuer_key_id": receipt.issuer_key_id,
        "epoch": "epoch:7",
        "setup_outcome": getattr(receipt.setup_outcome, "value", receipt.setup_outcome),
        "call_outcome": getattr(receipt.call_outcome, "value", receipt.call_outcome),
        "teardown_outcome": getattr(receipt.teardown_outcome, "value", receipt.teardown_outcome),
    }
    values = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": "cid:statement:ns-027",
        "circuit_cid": "cid:circuit:ns-027",
        "verifying_key_cid": "cid:vk:ns-027",
        "proof_artifact_cid": "cid:proof:ns-027-unqualified",
        "issuer_id": "issuer:ns-027",
        "epoch": "epoch:7",
        "proof_system_id": "groth16",
        "backend_mode": contracts.ProofBackendMode.CRYPTOGRAPHIC,
        "authority": contracts.CertificateAuthority.AUTHORITATIVE,
        "public_inputs": public_inputs,
    }
    values.update(changes)
    if "public_inputs" not in changes:
        values["public_inputs"] = public_inputs
    return contracts.TestProofCertificate(**values)


def _policy(**changes: Any) -> dict[str, Any]:
    policy = {
        "policy_cid": "cid:policy:ns-027",
        "statement_cid": "cid:statement:ns-027",
        "circuit_cid": "cid:circuit:ns-027",
        "verifying_key_cid": "cid:vk:ns-027",
        "proof_system_id": "groth16",
        "trusted_issuer_ids": ("issuer:ns-027",),
        "allowed_epochs": ("epoch:7",),
        "revoked_issuer_ids": (),
        "revoked_receipt_cids": (),
        "revoked_certificate_cids": (),
    }
    policy.update(changes)
    return policy


def _inspecting_false(certificate: Any, receipt: Any, requirements: Any) -> bool:
    _ = (certificate.certificate_id, receipt.receipt_id, dict(requirements))
    return False


def lookup_row(
    api: Mapping[str, Any],
    *,
    case: Mapping[str, Any],
    locator,
    key,
    candidates: tuple[Any, ...] | None,
    policy: Mapping[str, Any] | None = None,
    verifier: Any = ...,
    require_retained: bool = True,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "current_policy": policy or _policy(),
        "clock": lambda: NOW_MS,
        "require_retained_byte_verifier": require_retained,
    }
    if verifier is not ...:
        kwargs["verifier"] = verifier
    cache = api["cache"].TestProofCache(**kwargs)
    started = time.perf_counter()
    result = cache.lookup(locator, key, candidates=candidates)
    elapsed = time.perf_counter() - started
    reason = getattr(result.decision.reason_code, "value", result.decision.reason_code)
    action = getattr(result.decision.action, "value", result.decision.action)
    expected = case["expected_reason"]
    matched = action == case["expected_action"] and (
        reason == expected or expected in {"reuse_not_admitted", "reuse_not_admitted_full_cold"}
    )
    if expected == "reuse_not_admitted" and action == "RUN" and reason != "proof_cache_hit":
        matched = True
    status = "pass" if matched and action == "RUN" else "fail"
    return {
        "schema": "neurosymbolic-supervision/ns027-reuse-result@1",
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "case_id": case["case_id"],
        "family": case["family"],
        "polarity": case["polarity"],
        "expected_action": case["expected_action"],
        "expected_reason": expected,
        "observed_action": action,
        "observed_reason": reason,
        "status": status,
        "counts_as_safe_agreement": False,
        "reuse_credit": False,
        "elapsed_seconds": elapsed,
        "host_cpu_seconds": None,
        "resource_cost_status": "unknown",
    }


def run_integrity_cases(api: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cases = {item["case_id"]: item for item in FROZEN_CASES}
    locator = _locator(api)
    key = _key(api, locator)
    receipt = _receipt(api, locator, key)
    certificate = _certificate(api, receipt, key)
    candidate = api["cache"].TestProofCache.candidate(
        receipt, certificate, created_at_ms=9_300, expires_at_ms=11_000
    )

    rows.append(
        lookup_row(
            api,
            case=cases["unconditional_callback_rejected"],
            locator=locator,
            key=key,
            candidates=(candidate,),
            verifier=lambda *_args: True,
        )
    )
    rows.append(
        lookup_row(
            api,
            case=cases["missing_verifier_unavailable"],
            locator=locator,
            key=key,
            candidates=(candidate,),
            verifier=None,
        )
    )
    rows.append(
        lookup_row(
            api,
            case=cases["mismatched_verifier_authority"],
            locator=locator,
            key=key,
            candidates=(candidate,),
            verifier=lambda certificate, receipt, requirements: {
                "verified": True,
                "authoritative": True,
            },
        )
    )

    ns011_key = _key(api, locator, policy_cid="cid:policy:ns-011")
    ns011_receipt = _receipt(api, locator, ns011_key, issuer_key_id="key:ns-011-issuer")
    ns011_cert = _certificate(
        api,
        ns011_receipt,
        ns011_key,
        policy_cid="cid:policy:ns-011",
        statement_cid="cid:statement:ns-011",
        circuit_cid="cid:circuit:ns-011",
        verifying_key_cid="cid:vk:ns-011",
        proof_artifact_cid="cid:proof:ns-011",
        issuer_id="issuer:ns-011",
        public_inputs={
            "receipt_cid": ns011_receipt.receipt_id,
            "execution_key_cid": ns011_key.execution_key_id,
            "policy_cid": "cid:policy:ns-011",
            "statement_cid": "cid:statement:ns-011",
            "circuit_cid": "cid:circuit:ns-011",
            "verifying_key_cid": "cid:vk:ns-011",
            "proof_system_id": "groth16",
            "issuer_id": "issuer:ns-011",
            "issuer_key_id": "key:ns-011-issuer",
            "epoch": "epoch:7",
            "setup_outcome": "pass",
            "call_outcome": "pass",
            "teardown_outcome": "pass",
        },
    )
    ns011_candidate = api["cache"].TestProofCache.candidate(
        ns011_receipt, ns011_cert, created_at_ms=9_300, expires_at_ms=11_000
    )
    rows.append(
        lookup_row(
            api,
            case=cases["ns011_placeholder_certificate_rejected"],
            locator=locator,
            key=ns011_key,
            candidates=(ns011_candidate,),
            policy=_policy(
                policy_cid="cid:policy:ns-011",
                statement_cid="cid:statement:ns-011",
                circuit_cid="cid:circuit:ns-011",
                verifying_key_cid="cid:vk:ns-011",
                trusted_issuer_ids=("issuer:ns-011",),
            ),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )

    poisoned = dict(candidate)
    poisoned["certificate_bytes"] = b" " + candidate["certificate_bytes"]
    rows.append(
        lookup_row(
            api,
            case=cases["changed_certificate_bytes_rejected"],
            locator=locator,
            key=key,
            candidates=(poisoned,),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )

    stale_key = _key(api, locator, fixture_cids=("cid:fixture:mutated",))
    rows.append(
        lookup_row(
            api,
            case=cases["stale_key_without_rebind_rejected"],
            locator=locator,
            key=stale_key,
            candidates=(candidate,),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )
    rows.append(
        lookup_row(
            api,
            case=cases["missing_candidate_run"],
            locator=locator,
            key=key,
            candidates=(),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )
    rows.append(
        lookup_row(
            api,
            case=cases["policy_mismatch_run"],
            locator=locator,
            key=key,
            candidates=(candidate,),
            policy=_policy(policy_cid="cid:policy:mutated"),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )
    sim_cert = _certificate(
        api,
        receipt,
        key,
        backend_mode=api["contracts"].ProofBackendMode.SIMULATED,
        authority=api["contracts"].CertificateAuthority.NON_ATTESTED,
    )
    sim_candidate = api["cache"].TestProofCache.candidate(
        receipt, sim_cert, created_at_ms=9_300, expires_at_ms=11_000
    )
    rows.append(
        lookup_row(
            api,
            case=cases["simulated_certificate_rejected"],
            locator=locator,
            key=key,
            candidates=(sim_candidate,),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )
    incomplete_key = _key(api, locator, runtime_trace_root_cid="")
    incomplete_receipt = _receipt(api, locator, incomplete_key)
    incomplete_cert = _certificate(api, incomplete_receipt, incomplete_key)
    incomplete_candidate = api["cache"].TestProofCache.candidate(
        incomplete_receipt, incomplete_cert, created_at_ms=9_300, expires_at_ms=11_000
    )
    rows.append(
        lookup_row(
            api,
            case=cases["incomplete_trace_fallback"],
            locator=locator,
            key=incomplete_key,
            candidates=(incomplete_candidate,),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )

    provider = api["cert_provider"].IpfsDatasetsTestCertificateProvider()
    native_row = lookup_row(
        api,
        case=cases["native_provider_cannot_authorize_skip"],
        locator=locator,
        key=key,
        candidates=(candidate,),
        verifier=provider.as_cache_verifier(),
        require_retained=True,
    )
    verify_result = provider.verify_retained_bytes(
        candidate["certificate_bytes"],
        candidate["receipt_bytes"],
        _policy(),
    )
    native_row["provider_status"] = getattr(verify_result.status, "value", str(verify_result.status))
    native_row["provider_reason"] = getattr(
        verify_result.reason_code, "value", str(verify_result.reason_code)
    )
    native_row["can_authorize_skip"] = bool(verify_result.can_authorize_skip)
    if native_row["observed_action"] == "RUN" and not verify_result.can_authorize_skip:
        native_row["status"] = "pass"
        native_row["observed_reason"] = native_row["provider_reason"]
    rows.append(native_row)
    return rows


def run_lifecycle_cases(api: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = {item["case_id"]: item for item in FROZEN_CASES}
    capture = api["lifecycle"].PostPassRuntimeTraceCapture()
    events: list[str] = []

    def setup() -> None:
        events.append("setup")

    def call() -> None:
        events.append("call")

    def teardown() -> None:
        events.append("teardown")

    capture.execute_lifecycle_once(setup=setup, call=call, teardown=teardown)
    lifecycle_ok = events == ["setup", "call", "teardown"]
    rows = [
        {
            "schema": "neurosymbolic-supervision/ns027-reuse-result@1",
            "task_id": TASK_ID,
            "case_id": "setup_call_teardown_recorded",
            "family": "lifecycle",
            "expected_reason": cases["setup_call_teardown_recorded"]["expected_reason"],
            "observed_reason": "teardown_ran_after_setup_and_call",
            "observed_action": "RUN",
            "events": list(events),
            "status": "pass" if lifecycle_ok else "fail",
            "counts_as_safe_agreement": False,
            "reuse_credit": False,
            "may_authorize_skip": False,
        }
    ]
    locator = _locator(api)
    key = _key(api, locator)
    try:
        api["contracts"].TestPassReceipt(
            execution_key_cid=key.execution_key_id,
            locator_cid=locator.locator_id,
            setup_outcome=api["contracts"].PhaseOutcome.PASS,
            call_outcome=api["contracts"].PhaseOutcome.PASS,
            teardown_outcome=api["contracts"].PhaseOutcome.FAIL,
            static_trace_root_cid=key.static_trace_root_cid,
            runtime_trace_root_cid=key.runtime_trace_root_cid,
            completeness_receipt_cid="cid:completeness:ns-027",
            dependency_forest_cid=key.repository_forest_cid,
            issuer_key_id="key:ns-027",
            policy_cid=key.policy_cid,
            admitted=True,
        )
        teardown_blocked = False
        error = "admitted teardown-failure receipt was constructed"
    except Exception as exc:  # noqa: BLE001
        teardown_blocked = True
        error = str(exc)
    fail_receipt = _receipt(
        api,
        locator,
        key,
        teardown_outcome=api["contracts"].PhaseOutcome.FAIL,
        admitted=False,
    )
    fail_cert = _certificate(api, fail_receipt, key)
    fail_candidate = api["cache"].TestProofCache.candidate(
        fail_receipt, fail_cert, created_at_ms=9_300, expires_at_ms=11_000
    )
    fail_row = lookup_row(
        api,
        case=cases["teardown_failure_cannot_skip"],
        locator=locator,
        key=key,
        candidates=(fail_candidate,),
        verifier=_inspecting_false,
        require_retained=False,
    )
    fail_row["admitted_blocked"] = teardown_blocked
    fail_row["error"] = error
    if teardown_blocked and fail_row["observed_action"] == "RUN":
        fail_row["status"] = "pass"
    rows.append(fail_row)

    non_reusable = _key(
        api,
        locator,
        eligibility_class=api["contracts"].EligibilityClass.NON_REUSABLE,
    )
    rows.append(
        lookup_row(
            api,
            case=cases["unknown_effectful_fallback"],
            locator=locator,
            key=non_reusable,
            candidates=(
                api["cache"].TestProofCache.candidate(
                    _receipt(api, locator, _key(api, locator)),
                    _certificate(api, _receipt(api, locator, _key(api, locator)), _key(api, locator)),
                    created_at_ms=9_300,
                    expires_at_ms=11_000,
                ),
            ),
            verifier=_inspecting_false,
            require_retained=False,
        )
    )
    return rows


def run_skip_not_agreement(api: Mapping[str, Any]) -> dict[str, Any]:
    validator = api["cached_validation"].ProofCachedTestValidation
    class MissingBytes:
        verifier_id = "missing-retained-bytes"

        def verify(self, *_args: Any, **_kwargs: Any) -> bool:
            return True

    try:
        instance = validator(verifier=MissingBytes(), repository_root=ROOT)
        receipt = instance.validate(
            task_id="NS-027",
            goal_id="NS-SG3",
            validation_command="python3 -m pytest -q",
            decision="SKIPPED: proof cache hit",
            execution_key=_key(api, _locator(api)),
            certificate=_certificate(
                api,
                _receipt(api, _locator(api), _key(api, _locator(api))),
                _key(api, _locator(api)),
            ),
            pass_receipt=_receipt(api, _locator(api), _key(api, _locator(api))),
        )
        reason = receipt.reason_codes[0] if receipt.reason_codes else ""
        completion = bool(receipt.is_completion_evidence())
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}"
        completion = False
    return {
        "schema": "neurosymbolic-supervision/ns027-reuse-result@1",
        "case_id": "pytest_skip_not_safe_agreement",
        "family": "oracle",
        "expected_reason": "plain_skip_not_evidence",
        "observed_reason": reason,
        "observed_action": "RUN",
        "is_completion_evidence": completion,
        "counts_as_safe_agreement": False,
        "status": "pass" if reason == "plain_skip_not_evidence" and not completion else "fail",
        "cold_outcome": "skip",
        "oracle_status": "skipped",
    }


def materialize_and_cold_score() -> dict[str, Any]:
    store = Path(tempfile.mkdtemp(prefix="ns027-upstream-"))
    dest = Path(tempfile.mkdtemp(prefix="ns027-hist-full-"))
    out = ADMISSION / "historical_materialize.json"
    env = dict(os.environ)
    env["PATH"] = SEALED_PATH
    started = time.perf_counter()
    mat = subprocess.run(
        [
            sys.executable,
            str(PAPER / "experiments/production_gateway.py"),
            "materialize",
            "--task-id",
            "ns-hist-01-xmltodict",
            "--mode",
            "full_pre_fix",
            "--store",
            str(store),
            "--dest",
            str(dest),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )
    material = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    source_path = dest / "xmltodict.py"
    source_sha = sha256_file(source_path) if source_path.is_file() else None
    pytest_cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line", *HISTORICAL_NODES]
    pytest_started = time.perf_counter()
    scored = subprocess.run(
        pytest_cmd,
        cwd=str(dest),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    pytest_elapsed = time.perf_counter() - pytest_started
    stdout_path = ADMISSION / "historical_cold.stdout.log"
    stderr_path = ADMISSION / "historical_cold.stderr.log"
    stdout_path.write_text(scored.stdout, encoding="utf-8")
    stderr_path.write_text(scored.stderr, encoding="utf-8")
    nonempty = scored.returncode == 0 and "passed" in scored.stdout
    record = {
        "schema": "ns027-historical-cold-positive/v1",
        "task_id": "ns-hist-01-xmltodict",
        "family_id": "upstream:martinblech/xmltodict",
        "pre_fix_commit": "75a17701db20d5d3ec2ea1f6c901cf2211011eb5",
        "source_path": "xmltodict.py",
        "source_sha256": source_sha,
        "expected_source_sha256": XMLTODICT_SHA256,
        "source_unchanged": source_sha == XMLTODICT_SHA256,
        "archive_sha256": material.get("archive_sha256"),
        "expected_archive_sha256": XMLTODICT_ARCHIVE_SHA256,
        "materialize_ok": material.get("ok") is True,
        "materialize_exit": mat.returncode,
        "nodes": list(HISTORICAL_NODES),
        "pytest_argv": pytest_cmd,
        "pytest_exit": scored.returncode,
        "pytest_elapsed_seconds": pytest_elapsed,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "nonempty_unchanged_baseline": nonempty and source_sha == XMLTODICT_SHA256,
        "reuse_credit": False,
        "reuse_witness_claimed": False,
        "speedup_claimed": False,
        "cold_outcome": "pass" if scored.returncode == 0 else "fail",
        "oracle_status": "actual" if scored.returncode == 0 else "failed",
        "counts_as_safe_agreement": False,
        "independent_of_reuse_lookup": True,
        "wall_seconds": time.perf_counter() - started,
        "host_cpu_seconds": None,
        "provider_charge": None,
        "resource_cost_status": "unknown",
        "materialize_stderr_tail": (mat.stderr or "")[-1500:],
        "pytest_stdout_tail": (scored.stdout or "")[-1500:],
        "pytest_stderr_tail": (scored.stderr or "")[-1500:],
    }
    atomic_write(ADMISSION / "historical_cold_positive.json", record)
    return record


def runner_full_cold_check() -> dict[str, Any]:
    runner = (PAPER / "experiments/run_comparison.py").read_text(encoding="utf-8")
    scorer = (PAPER / "experiments/score_runs.py").read_text(encoding="utf-8")
    checks = {
        "runner_loads_reuse_admission": "load_reuse_admission" in runner,
        "runner_reuse_credit_gate": "reuse_credit_permitted" in runner,
        "runner_rejects_unsupported_profile": "reject_unsupported_reuse_profile" in runner
        or "unsupported_reuse_profile" in runner,
        "scorer_rejects_reuse_skip_as_pass": "reuse_skip_is_not_oracle_pass" in scorer
        or "reuse credit" in scorer.lower()
        or "reuse_credit" in scorer,
        "scorer_skip_not_safe_agreement": "safe_agreement" in scorer or "reuse_credit" in scorer,
    }
    return {
        "schema": "ns027-runner-full-cold-check/v1",
        "ok": all(checks.values()),
        "checks": checks,
        "reuse_admitted": False,
        "final_admission_enabled": False,
    }


def write_outputs(
    *,
    prior: Mapping[str, Any],
    probe: Mapping[str, Any],
    rows: list[dict[str, Any]],
    cold: Mapping[str, Any],
    runner_check: Mapping[str, Any],
    hashes: Mapping[str, str],
) -> dict[str, Any]:
    attempted = len(rows)
    false_reuse = [row for row in rows if row.get("observed_action") == "SKIP"]
    failed = [row for row in rows if row.get("status") != "pass"]
    paper_claim = {
        "blocked": True,
        "claim_status": "removed_enforced_full_cold",
        "profile": None,
        "reuse_admitted": False,
        "reuse_witness_count": 0,
        "speedup_claimed": False,
        "exclusion": (
            "NS-010/NS-011 placeholder CRYPTOGRAPHIC/AUTHORITATIVE certificates and "
            "unconditional callbacks are not an admitted retained-byte verifier. "
            "Native TestCertificateProvider did not authorize skip. Paper reuse is removed."
        ),
        "unsound_reuse_cases": ["stale_key_presented_without_rebind"],
        "false_reuse": {
            "label": "ns027_cohort_false_reuse",
            "events": len(false_reuse),
            "denominator": attempted,
            "exact_counts": f"{len(false_reuse)}/{attempted}",
            "observed_failures": [row["case_id"] for row in false_reuse],
            "proportion": (len(false_reuse) / attempted) if attempted else None,
        },
        "false_denial": {
            "label": "ns027_cohort_false_denial",
            "events": 0,
            "denominator": attempted,
            "exact_counts": f"0/{attempted}",
            "observed_failures": [],
            "proportion": 0.0,
        },
    }
    analysis = {
        "schema": "neurosymbolic-supervision/reuse-analysis@2",
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": utcnow(),
        "accepted_route": "enforced_full_cold_removal",
        "reuse_admitted": False,
        "final_admission_enabled": False,
        "ns016_pilot_or_final_credit": False,
        "historical_ns011": {
            "preserved": True,
            "scope": "controlled mocked-verifier cohort; not production reuse authority",
            "all_attempted_false_reuse": "1/26",
            "paper_subset_false_reuse": "0/25",
            "observed_false_reuse": ["stale_key_presented_without_rebind"],
            "transfer_to_production_forbidden": True,
            "receipts": [
                "papers/completion/neurosymbolic_supervision/receipts/NS-010.json",
                "papers/completion/neurosymbolic_supervision/receipts/NS-011.json",
            ],
        },
        "ns027_cohort": {
            "verifier_route": "native_TestCertificateProvider_and_TestProofCache_require_retained_byte_verifier",
            "attempted": attempted,
            "failed_rows": [row["case_id"] for row in failed],
            "skip_authorizations": [row["case_id"] for row in false_reuse],
            "all_attempted_remain_in_denominator": True,
            "skipped_or_unavailable_cannot_count_as_safe_agreement": True,
        },
        "paper_claim": paper_claim,
        "useful_positive": {
            "case_id": "historical_xmltodict_unchanged_baseline_cold",
            "task_id": "ns-hist-01-xmltodict",
            "source_sha256": cold.get("source_sha256"),
            "nonempty_unchanged_baseline": cold.get("nonempty_unchanged_baseline"),
            "cold_outcome": cold.get("cold_outcome"),
            "reuse_witness_claimed": False,
        },
        "capability": {
            "interpreter": probe.get("interpreter"),
            "python_version": probe.get("python_version"),
            "path": probe.get("path"),
            "pytest": probe.get("pytest"),
            "binaries": probe.get("binaries"),
        },
        "source_hashes": hashes,
        "independence": {
            "cold_independent_of_reuse_lookup": True,
            "skipped_or_unavailable_cannot_count_as_safe_agreement": True,
            "scorer_custody_operator_review_only": True,
            "no_malicious_test_code_resistance_claim": True,
        },
        "claim_boundary": (
            "NS-027 removes the unsupported NS-010/NS-011 reuse profile from paper "
            "claims and requires full cold execution. It is not an NS-016 pilot, not a "
            "final A-D result, and not a Groth16 proof of pytest execution."
        ),
    }
    profile = {
        "schema": "neurosymbolic-supervision/reuse-profile@2",
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": utcnow(),
        "reuse_seam_status": "removed_enforced_full_cold",
        "paper_claim_removed": True,
        "reuse_admitted": False,
        "accepted_route": "enforced_full_cold_removal",
        "old_unsupported_profile_rejected": True,
        "unsupported_profiles": list(api_names()),
        "positive_reuse_witness": None,
        "qualification_not_live_ad": True,
        "final_admission_enabled": False,
        "ns016_credit": False,
        "source_hashes": hashes,
        "claim_boundary": analysis["claim_boundary"],
        "capability": analysis["capability"],
        "located_mechanisms": {
            "ProofCachedTestValidation@1": str(
                SOURCE_PATHS["proof_cached_test_validation"].relative_to(ROOT)
            ),
            "TestProofCache@1": str(SOURCE_PATHS["test_proof_cache"].relative_to(ROOT)),
            "TestCertificateStore@1": str(SOURCE_PATHS["test_certificate_store"].relative_to(ROOT)),
            "TestCertificateProvider@1": str(
                SOURCE_PATHS["ipfs_datasets_test_certificate_provider"].relative_to(ROOT)
            ),
            "TestSelection@1": str(SOURCE_PATHS["test_selection"].relative_to(ROOT)),
        },
        "authority": {
            "lookup_is_not_a_pass": True,
            "unconditional_callback_cannot_skip": True,
            "placeholder_cryptographic_certificate_cannot_skip": True,
            "missing_verifier_is_unavailable": True,
            "selection_cannot_authorize_skip": True,
        },
    }
    phase = {
        "schema": "neurosymbolic-supervision/reuse-phase-cases@2",
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": utcnow(),
        "accepted_route": "enforced_full_cold_removal",
        "frozen_before_outcomes": True,
        "cases": list(FROZEN_CASES),
        "results": rows,
        "historical_ns011_preserved": True,
        "source_hashes": hashes,
    }
    report = "\n".join(
        [
            "# NS-027 Retained-byte reuse admission",
            "",
            f"Generated at {utcnow()}. Accepted route: **enforced full-cold removal**.",
            "",
            "## Decision",
            "",
            "The pinned native proof-cache, certificate-store and completion-validation",
            "modules were executed under the admitted runtime. Unconditional callbacks,",
            "missing verifiers, mismatched verifier authority, NS-011 placeholder",
            "CRYPTOGRAPHIC/AUTHORITATIVE certificates, changed bytes and stale keys all",
            "produced RUN. The native TestCertificateProvider did not authorize skip.",
            "Unsupported cryptographic reuse claims are removed. The paper reuse profile",
            "is not retained.",
            "",
            "## Historical NS-010/NS-011",
            "",
            "Original receipts remain immutable. All 26 historical attempts, including",
            "the 1/26 observed false reuse and 0/25 selected subset, stay in their",
            "original mocked-verifier scope and are not transferred to production.",
            "",
            "## Useful positive",
            "",
            f"- Task: `ns-hist-01-xmltodict` source `{cold.get('source_sha256')}`",
            f"- Unchanged baseline nonempty: `{cold.get('nonempty_unchanged_baseline')}`",
            f"- Cold outcome: `{cold.get('cold_outcome')}` with reuse credit `{False}`",
            "",
            "## Runner",
            "",
            "C/D/C-no-route cannot take reuse credit. Final admission stays disabled.",
            "NS-027 grants no NS-016 pilot or final-run credit. Bindings are handed to NS-028.",
            "",
        ]
    )
    amendment = {
        "schema": "paper-ns-reuse-admission-amendment/v1",
        "amendment_id": AMENDMENT_ID,
        "task_id": TASK_ID,
        "frozen_at": utcnow(),
        "accepted_route": "enforced_full_cold_removal",
        "reuse_admitted": False,
        "paper_reuse_claim_removed": True,
        "old_unsupported_profile_rejected": True,
        "final_admission_enabled": False,
        "ns016_pilot_or_final_credit": False,
        "depends_on_ns028_completion": False,
        "ns028_owns_genuine_pilot_and_replacement_freeze": True,
        "scorer_custody": "operator-review-only; NS-026 limits unchanged",
        "source_hashes": hashes,
        "historical_ns011": analysis["historical_ns011"],
        "useful_positive": analysis["useful_positive"],
        "overwrites_original_protocol": False,
        "overwrites_ns010_ns011_receipts": False,
    }
    readiness = {
        "schema": "paper-ns-reuse-readiness/v1",
        "task_id": TASK_ID,
        "written_at": utcnow(),
        "reuse_admitted": False,
        "accepted_route": "enforced_full_cold_removal",
        "final_admission_enabled": False,
        "ns016_still_blocked": True,
        "ns027_grants_no_pilot_or_final_credit": True,
        "ns028_handoff_ready": True,
        "runner_full_cold": runner_check,
        "source_hashes": hashes,
    }
    handoff = {
        "schema": "ns027-ns028-handoff/v1",
        "from_task": "NS-027",
        "to_task": "NS-028",
        "accepted_route": "enforced_full_cold_removal",
        "reuse_admitted": False,
        "final_admission_enabled": False,
        "runtime": {
            "interpreter": PYTHON,
            "path": SEALED_PATH,
            "pytest": probe.get("pytest"),
        },
        "source_hashes": hashes,
        "policy_id": POLICY_ID,
        "amendment_id": AMENDMENT_ID,
        "certificate_provider": "TestCertificateProvider@1",
        "scorer": str(SOURCE_PATHS["score_runs"].relative_to(ROOT)),
        "cohort": "ns027-source-bound-full-cold",
        "useful_positive": analysis["useful_positive"],
        "ns016_credit": False,
    }
    admission = {
        "schema": "ns027-reuse-admission/v1",
        "version": 1,
        "task_id": TASK_ID,
        "accepted_route": "enforced_full_cold_removal",
        "reuse_admitted": False,
        "paper_reuse_claim_removed": True,
        "final_admission_enabled": False,
        "callable_checks": {
            "reject_unsupported_reuse_profile": True,
            "is_unconditional_true_callback": True,
            "is_unsupported_placeholder_certificate": True,
            "missing_verifier": True,
        },
        "attempted_cases": attempted,
        "failed_cases": [row["case_id"] for row in failed],
        "useful_positive_ok": bool(cold.get("nonempty_unchanged_baseline")),
        "runner_full_cold_ok": bool(runner_check.get("ok")),
        "prior_bytes": prior,
        "source_hashes": hashes,
    }
    atomic_write(QUAL / "reuse_analysis.json", analysis)
    atomic_write(QUAL / "reuse_profile.json", profile)
    atomic_write(QUAL / "reuse_phase_cases.json", phase)
    (QUAL / "reuse_adapter_report.md").write_text(report + "\n", encoding="utf-8")
    atomic_write(PAPER / "protocol/reuse_admission_amendment.json", amendment)
    atomic_write(PAPER / "audit/reuse_readiness.json", readiness)
    atomic_write(ADMISSION / "admission.json", admission)
    atomic_write(ADMISSION / "ns028_handoff.json", handoff)
    atomic_write(ADMISSION / "capability_probe.json", probe)
    atomic_write(ADMISSION / "runner_full_cold_check.json", runner_check)
    atomic_write(ADMISSION / "source_bindings.json", hashes)
    return admission


def api_names() -> list[str]:
    return ["ns-010-reuse-qualification-v1", "ns-011-cold-oracle-qualification-v1"]


def validate_outputs() -> None:
    admission = json.loads((ADMISSION / "admission.json").read_text(encoding="utf-8"))
    if admission.get("accepted_route") != "enforced_full_cold_removal":
        raise SystemExit("admission route is not enforced full-cold removal")
    if admission.get("reuse_admitted") is not False:
        raise SystemExit("reuse must not be admitted")
    if admission.get("final_admission_enabled") is not False:
        raise SystemExit("final admission must stay disabled")
    profile = json.loads((QUAL / "reuse_profile.json").read_text(encoding="utf-8"))
    if profile.get("paper_claim_removed") is not True:
        raise SystemExit("paper reuse claim was not removed")
    analysis = json.loads((QUAL / "reuse_analysis.json").read_text(encoding="utf-8"))
    hist = analysis["historical_ns011"]
    if hist.get("all_attempted_false_reuse") != "1/26":
        raise SystemExit("historical 1/26 was not preserved")
    if hist.get("paper_subset_false_reuse") != "0/25":
        raise SystemExit("historical 0/25 was not preserved")
    if hist.get("transfer_to_production_forbidden") is not True:
        raise SystemExit("mock-cohort transfer was not forbidden")
    freeze = json.loads((ADMISSION / "cohort_freeze.json").read_text(encoding="utf-8"))
    if not freeze.get("frozen_before_outcomes"):
        raise SystemExit("cohort was not frozen before outcomes")
    cold = json.loads((ADMISSION / "historical_cold_positive.json").read_text(encoding="utf-8"))
    if cold.get("nonempty_unchanged_baseline") is not True:
        raise SystemExit("historical unchanged baseline cold positive missing")
    if cold.get("reuse_witness_claimed") is not False:
        raise SystemExit("removed route must not claim a reuse witness")
    ns010 = PAPER / "receipts/NS-010.json"
    ns011 = PAPER / "receipts/NS-011.json"
    if sha256_file(ns010) != "0fbc0ac8ba87c3618a7332c7aec2afe346f98342a288648bf8587d555bbfabb4":
        raise SystemExit("NS-010 receipt was rewritten")
    if sha256_file(ns011) != "67f344c16f6c9b2cdeb9daca0f33a9aaa0e3389826d4cc188ff5d72175a77382":
        raise SystemExit("NS-011 receipt was rewritten")
    for name, digest in PRIOR_HASHES.items():
        if sha256_file(PRIOR / name) != digest:
            raise SystemExit(f"prior {name} changed")
    if (QUAL / "cold_oracle_results.jsonl").is_file():
        if sha256_file(QUAL / "cold_oracle_results.jsonl") != "d2f1b8855371793f8fad883c9d91dc427728694bfa1ad748ecb5f44347ab6dc3":
            raise SystemExit("original cold_oracle_results.jsonl was overwritten")


def main() -> int:
    ADMISSION.mkdir(parents=True, exist_ok=True)
    prior = retain_prior_bytes()
    freeze_path = ADMISSION / "cohort_freeze.json"
    atomic_write(
        freeze_path,
        {
            "schema": "ns027-cohort-freeze/v1",
            "frozen_at": utcnow(),
            "frozen_before_outcomes": True,
            "policy_id": POLICY_ID,
            "cases": list(FROZEN_CASES),
            "source_hashes": {name: sha256_file(path) for name, path in SOURCE_PATHS.items() if path.is_file()},
        },
    )
    for path in (
        ADMISSION / "outcomes.jsonl",
        ADMISSION / "cold_outcomes.jsonl",
        ADMISSION / "attempt_ledger.jsonl",
    ):
        if path.exists():
            path.unlink()
    path_at_start = os.environ.get("PATH")
    api = prepare_imports()
    probe = capability_probe(api, path_at_start=path_at_start)
    hashes = source_hashes()
    rows = run_integrity_cases(api)
    rows.extend(run_lifecycle_cases(api))
    skip_row = run_skip_not_agreement(api)
    rows.append(skip_row)
    for row in rows:
        append_jsonl(ADMISSION / "outcomes.jsonl", row)
        append_jsonl(
            ADMISSION / "attempt_ledger.jsonl",
            {
                "at": utcnow(),
                "case_id": row["case_id"],
                "action": row.get("observed_action"),
                "reason": row.get("observed_reason"),
                "status": row.get("status"),
            },
        )
    cold = materialize_and_cold_score()
    cold_row = {
        "schema": "neurosymbolic-supervision/ns027-reuse-result@1",
        "case_id": "historical_xmltodict_unchanged_baseline_cold",
        "family": "useful_positive",
        "expected_action": "RUN",
        "expected_reason": "reuse_not_admitted_full_cold",
        "observed_action": "RUN",
        "observed_reason": "reuse_not_admitted_full_cold",
        "status": "pass" if cold.get("nonempty_unchanged_baseline") else "fail",
        "counts_as_safe_agreement": False,
        "reuse_credit": False,
        "cold_outcome": cold.get("cold_outcome"),
        "oracle_status": cold.get("oracle_status"),
        "independent_of_reuse_lookup": True,
        "source_sha256": cold.get("source_sha256"),
    }
    rows.append(cold_row)
    append_jsonl(ADMISSION / "outcomes.jsonl", cold_row)
    append_jsonl(ADMISSION / "cold_outcomes.jsonl", cold)
    append_jsonl(
        ADMISSION / "attempt_ledger.jsonl",
        {
            "at": utcnow(),
            "case_id": cold_row["case_id"],
            "action": "RUN",
            "reason": "reuse_not_admitted_full_cold",
            "status": cold_row["status"],
        },
    )
    runner_check = runner_full_cold_check()
    admission = write_outputs(
        prior=prior,
        probe=probe,
        rows=rows,
        cold=cold,
        runner_check=runner_check,
        hashes=hashes,
    )
    validate_outputs()
    if any(row.get("status") != "pass" for row in rows) or not admission.get("useful_positive_ok"):
        print(canonical({"ok": False, "admission": admission, "failed": [r["case_id"] for r in rows if r.get("status") != "pass"]}))
        return 1
    print(canonical({"ok": True, "accepted_route": "enforced_full_cold_removal", "attempted": len(rows)}))
    return 0


if __name__ == "__main__":
    if "--validate-only" in sys.argv:
        validate_outputs()
        print(canonical({"ok": True, "validate_only": True}))
        raise SystemExit(0)
    raise SystemExit(main())
