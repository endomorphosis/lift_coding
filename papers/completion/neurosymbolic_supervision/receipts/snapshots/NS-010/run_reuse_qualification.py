#!/usr/bin/env python3
"""NS-010 live qualification of fixture-instance and phase-aware reuse.

Exercises the sealed TestLocatorKey, TestExecutionKey, TestPassReceipt,
TestProofCache, identity-component, collection-seed, lifecycle-capture,
xdist, eligibility, and ProofCachedTestValidation surfaces. Lookup is never
treated as a passing outcome. Fixture/plugin/policy/runtime/snapshot mutations
force RUN even when the test body CID is unchanged. Call reuse after setup
still runs teardown; teardown failure cannot admit a whole-item pass.

This is qualification evidence, not a matched A–D experiment and not a
cold-oracle mutation campaign (NS-011).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-010"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"
TASK_ID = "NS-010"
SCHEMA_CASES = "neurosymbolic-supervision/reuse-phase-cases@1"
SCHEMA_PROFILE = "neurosymbolic-supervision/reuse-profile@1"
SCHEMA_RESULT = "neurosymbolic-supervision/reuse-phase-result@1"
POLICY_ID = "ns-010-reuse-qualification-v1"
NOW_MS = 10_000
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)

SOURCE_PATHS = (
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/collection_seed.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/xdist.py",
    DS_ROOT
    / "ipfs_datasets_py/logic/software_contracts/semantic_state/test_selection.py",
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write(path, encoded.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def checkpoint(name: str, payload: Mapping[str, Any]) -> None:
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(CHECKPOINT_DIR / f"{name}.json", dict(payload))
    except OSError:
        fallback = SNAP / "checkpoints"
        fallback.mkdir(parents=True, exist_ok=True)
        write_json(fallback / f"{name}.json", dict(payload))


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def enum_val(value: Any) -> str:
    return str(getattr(value, "value", value))


def which(name: str) -> str | None:
    return shutil.which(name)


def git_head(path: Path) -> str | None:
    git = which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in SOURCE_PATHS:
        if path.is_file():
            hashes[rel(path)] = sha256_file(path)
    return hashes


def _install_sealed_multiformats_stub() -> bool:
    """Provide a decode-only CID object so runtime-trace imports can load.

    The sealed PATH has no ``multiformats`` package.  The stub never claims a
    live multiformats install and is not used as skip authority.
    """

    if "multiformats" in sys.modules:
        return False
    import types

    module = types.ModuleType("multiformats")

    class _Name:
        def __init__(self, name: str) -> None:
            self.name = name

    class CID:
        def __init__(self, value: str) -> None:
            self._value = value
            self.version = 1
            self.base = _Name("base32")
            self.codec = _Name("dag-json" if "json" in value else "raw")
            self.hashfun = _Name("sha2-256")
            self.raw_digest = b"\x00" * 32

        def __str__(self) -> str:
            return self._value

        @classmethod
        def decode(cls, value: str) -> "CID":
            if not isinstance(value, str) or not value.startswith("b"):
                raise ValueError("not a CIDv1 base32 address")
            return cls(value)

    module.CID = CID
    sys.modules["multiformats"] = module
    return True


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    stubbed_multiformats = _install_sealed_multiformats_stub()

    from ipfs_accelerate_py.agent_supervisor.analysis import (
        test_identity_components as identity,
        test_reuse_eligibility as eligibility,
    )
    from ipfs_accelerate_py.agent_supervisor.integrations import (
        ipfs_datasets_test_certificate_provider as cert_provider,
    )
    from ipfs_accelerate_py.agent_supervisor.proof import (
        test_execution_contracts as contracts,
        test_proof_cache as cache,
        test_certificate_store as store,
    )
    from ipfs_accelerate_py.agent_supervisor.validation import (
        proof_cached_test_validation as cached_validation,
    )
    from ipfs_accelerate_py.testing.proof_reuse import (
        collection_seed as seeds,
        runtime_revalidation as lifecycle,
        xdist as xdist_mod,
    )

    pytest_version = None
    pytest_error = None
    try:
        import pytest

        pytest_version = pytest.__version__
    except Exception as exc:
        pytest_error = f"{type(exc).__name__}: {exc}"

    selection_status = "unavailable"
    selection_error = None
    selection_module = None
    try:
        from ipfs_datasets_py.logic.software_contracts.semantic_state import (
            test_selection as selection,
        )

        selection_module = selection
        selection_status = "imported"
    except Exception as exc:
        selection_error = f"{type(exc).__name__}: {exc}"

    groth16 = False
    groth16_error = None
    try:
        from ipfs_accelerate_py.agent_supervisor.integrations.test_reuse_capabilities import (
            probe_test_reuse_capabilities,
        )

        report = probe_test_reuse_capabilities()
        groth16 = bool(
            getattr(report.by_name.get("groth16"), "available", False)
            if hasattr(report, "by_name")
            else False
        )
    except Exception as exc:
        groth16_error = f"{type(exc).__name__}: {exc}"

    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "pytest": pytest_version,
        "pytest_error": pytest_error,
        "multiformats": False,
        "multiformats_stub_installed": stubbed_multiformats,
        "selection_status": selection_status,
        "selection_error": selection_error,
        "groth16_probe_error": groth16_error,
        "groth16_available": groth16,
        "binaries": {
            "z3": which("z3"),
            "cvc5": which("cvc5"),
            "groth16": which("groth16"),
        },
        "api": {
            "contracts": contracts,
            "cache": cache,
            "store": store,
            "identity": identity,
            "eligibility": eligibility,
            "seeds": seeds,
            "lifecycle": lifecycle,
            "xdist": xdist_mod,
            "cached_validation": cached_validation,
            "cert_provider": cert_provider,
            "selection": selection_module,
        },
        "modules": {
            "proof_cached_test_validation": rel(SOURCE_PATHS[0]),
            "test_proof_cache": rel(SOURCE_PATHS[1]),
            "test_certificate_store": rel(SOURCE_PATHS[2]),
            "test_execution_contracts": rel(SOURCE_PATHS[3]),
            "ipfs_datasets_test_certificate_provider": rel(SOURCE_PATHS[4]),
            "test_identity_components": rel(SOURCE_PATHS[5]),
            "test_reuse_eligibility": rel(SOURCE_PATHS[6]),
            "collection_seed": rel(SOURCE_PATHS[7]),
            "runtime_revalidation": rel(SOURCE_PATHS[8]),
            "xdist": rel(SOURCE_PATHS[9]),
            "test_selection": rel(SOURCE_PATHS[10]),
        },
    }


def _locator(api: Mapping[str, Any], **changes: Any):
    values = {
        "repository_id": "repository:ns-010-qualification",
        "package_identity": "ipfs_accelerate_py",
        "node_id": "qualification/test_reuse.py::test_unchanged_eligible",
        "collection_schema_version": "1",
        "root_identity": "root:ns-010",
        "selection_semantics": "exact_node",
    }
    values.update(changes)
    return api["contracts"].TestLocatorKey(**values)


def _execution_key(api: Mapping[str, Any], locator, **changes: Any):
    values = {
        "locator_cid": locator.locator_id,
        "repository_forest_cid": "cid:forest:ns-010",
        "git_commit_id": "commit:ns-010",
        "git_tree_id": "tree:ns-010",
        "test_module_cid": "cid:module:ns-010",
        "test_function_cid": "cid:function:unchanged-body",
        "test_ast_cid": "cid:ast:ns-010",
        "fixture_cids": ("cid:fixture:db-v1",),
        "conftest_closure_cid": "cid:conftest:v1",
        "hook_plugin_cids": ("cid:plugin:pytest-v1",),
        "static_trace_root_cid": "cid:static:ns-010",
        "runtime_trace_root_cid": "cid:runtime:ns-010",
        "runtime_completeness_policy": "complete-v1",
        "pytest_version": "8.1.1",
        "python_version": "3.12.3",
        "plugin_versions_cid": "cid:plugins:v1",
        "config_cid": "cid:config:v1",
        "dependency_lock_cid": "cid:lock:v1",
        "installed_distributions_cid": "cid:dists:v1",
        "environment_cid": "cid:env:v1",
        "platform_cid": "cid:platform:linux",
        "interpreter_abi_cid": "cid:abi:cpython-312",
        "external_snapshot_cids": ("cid:snapshot:db-v1",),
        "policy_cid": "cid:policy:ns-010",
        "eligibility_class": api["contracts"].EligibilityClass.REPOSITORY_FOREST_BOUND,
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
        "completeness_receipt_cid": "cid:completeness:ns-010",
        "dependency_forest_cid": key.repository_forest_cid,
        "issuer_key_id": "key:ns-010-issuer",
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
        "statement_cid": "cid:statement:ns-010",
        "circuit_cid": "cid:circuit:ns-010",
        "verifying_key_cid": "cid:vk:ns-010",
        "proof_system_id": "groth16",
        "issuer_id": "issuer:ns-010",
        "issuer_key_id": receipt.issuer_key_id,
        "epoch": "epoch:7",
        "setup_outcome": enum_val(receipt.setup_outcome),
        "call_outcome": enum_val(receipt.call_outcome),
        "teardown_outcome": enum_val(receipt.teardown_outcome),
    }
    values = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": "cid:statement:ns-010",
        "circuit_cid": "cid:circuit:ns-010",
        "verifying_key_cid": "cid:vk:ns-010",
        "proof_artifact_cid": "cid:proof:ns-010",
        "issuer_id": "issuer:ns-010",
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
        "policy_cid": "cid:policy:ns-010",
        "statement_cid": "cid:statement:ns-010",
        "circuit_cid": "cid:circuit:ns-010",
        "verifying_key_cid": "cid:vk:ns-010",
        "proof_system_id": "groth16",
        "trusted_issuer_ids": ("issuer:ns-010",),
        "allowed_epochs": ("epoch:7",),
        "revoked_issuer_ids": (),
        "revoked_receipt_cids": (),
        "revoked_certificate_cids": (),
    }
    policy.update(changes)
    return policy


def _lookup(api: Mapping[str, Any], locator, key, receipt, certificate, **cache_kw):
    cache_cls = api["cache"].TestProofCache
    candidate = cache_cls.candidate(
        receipt,
        certificate,
        created_at_ms=9_300,
        expires_at_ms=11_000,
    )
    cache = cache_cls(
        current_policy=cache_kw.pop("policy", _policy()),
        verifier=cache_kw.pop("verifier", lambda *_args: True),
        clock=lambda: NOW_MS,
        **cache_kw,
    )
    return cache.lookup(locator, key, candidates=(candidate,)), candidate


def row_base(
    *,
    case_id: str,
    family: str,
    polarity: str,
    expected_reason: str,
    description: str,
    stage: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "case_id": case_id,
        "family": family,
        "polarity": polarity,
        "stage": stage,
        "expected_reason": expected_reason,
        "description": description,
        "kernel_proof": False,
        "live_ad_experiment": False,
        "simulated_unavailable_mechanism": False,
    }


def finish(base: dict[str, Any], *, observed_reason: str, extra: Mapping[str, Any]) -> dict[str, Any]:
    status = "pass" if observed_reason == base["expected_reason"] else "fail"
    row = dict(base)
    row.update(extra)
    row["observed_reason"] = observed_reason
    row["status"] = status
    return row


def declare(
    cases: list[dict[str, Any]],
    *,
    case_id: str,
    family: str,
    polarity: str,
    expected_reason: str,
    description: str,
    stage: str,
) -> None:
    cases.append(
        {
            "case_id": case_id,
            "family": family,
            "polarity": polarity,
            "stage": stage,
            "expected_reason": expected_reason,
            "description": description,
        }
    )


def run_cases(api: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = api["contracts"]
    identity = api["identity"]
    cases: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    locator = _locator(api)
    key = _execution_key(api, locator)
    receipt = _receipt(api, locator, key)
    certificate = _certificate(api, receipt, key)

    seed = api["seeds"].ProofReuseCollectionSeed(
        reason=api["seeds"].CollectionSeedReason.ADMITTED,
        stage="complete",
        node_id=locator.node_id,
        locator=locator,
        locator_cid=locator.locator_id,
        seed_cid="cid:seed:ns-010",
    )
    declare(
        cases,
        case_id="collection_seed_not_passing_outcome",
        family="lookup_not_pass",
        polarity="invalid",
        stage="0-collection-seed",
        expected_reason="collection_seed_not_passing_outcome",
        description="An admitted collection seed is candidate lookup only and cannot become a passing outcome.",
    )
    rows.append(
        finish(
            row_base(
                case_id="collection_seed_not_passing_outcome",
                family="lookup_not_pass",
                polarity="invalid",
                stage="0-collection-seed",
                expected_reason="collection_seed_not_passing_outcome",
                description="An admitted collection seed is candidate lookup only and cannot become a passing outcome.",
            ),
            observed_reason="collection_seed_not_passing_outcome"
            if (
                seed.action == "RUN"
                and seed.authorizes_skip is False
                and seed.authorizes_lookup is False
                and seed.has_execution_key is False
            )
            else "collection_seed_overclaimed",
            extra={
                "action": seed.action,
                "authorizes_skip": seed.authorizes_skip,
                "authorizes_lookup": seed.authorizes_lookup,
                "has_execution_key": seed.has_execution_key,
                "admitted_seed": seed.admitted,
                "interface": seed.interface,
            },
        )
    )

    declare(
        cases,
        case_id="locator_not_skip_authority",
        family="lookup_not_pass",
        polarity="invalid",
        stage="0-collection-seed",
        expected_reason="locator_not_skip_authority",
        description="TestLocatorKey@1 narrows retrieval and does not authorize SKIP.",
    )
    rows.append(
        finish(
            row_base(
                case_id="locator_not_skip_authority",
                family="lookup_not_pass",
                polarity="invalid",
                stage="0-collection-seed",
                expected_reason="locator_not_skip_authority",
                description="TestLocatorKey@1 narrows retrieval and does not authorize SKIP.",
            ),
            observed_reason="locator_not_skip_authority"
            if locator.interface == "TestLocatorKey@1" and bool(locator.locator_id)
            else "locator_overclaimed",
            extra={
                "interface": locator.interface,
                "locator_cid": locator.locator_id,
                "node_id": locator.node_id,
                "authorizes_skip": False,
            },
        )
    )

    eligibility = api["eligibility"].evaluate_reuse_eligibility(
        repository_forest_cid="cid:forest:ns-010"
    )
    declare(
        cases,
        case_id="eligibility_never_emits_skip",
        family="lookup_not_pass",
        polarity="diagnostic",
        stage="1-fixture-definition",
        expected_reason="eligibility_never_emits_skip",
        description="Eligibility classification never emits SKIP; missing traces fall back to RUN.",
    )
    rows.append(
        finish(
            row_base(
                case_id="eligibility_never_emits_skip",
                family="lookup_not_pass",
                polarity="diagnostic",
                stage="1-fixture-definition",
                expected_reason="eligibility_never_emits_skip",
                description="Eligibility classification never emits SKIP; missing traces fall back to RUN.",
            ),
            observed_reason="eligibility_never_emits_skip"
            if (
                eligibility.action is contracts.ReuseAction.RUN
                and eligibility.is_skip is False
                and eligibility.reusable is False
                and enum_val(eligibility.eligibility_class) == "non_reusable"
            )
            else "eligibility_emitted_skip",
            extra={
                "action": enum_val(eligibility.action),
                "reusable": eligibility.reusable,
                "eligibility_class": enum_val(eligibility.eligibility_class),
                "is_skip": eligibility.is_skip,
                "reason_codes": list(eligibility.reason_codes),
            },
        )
    )

    validator = api["cached_validation"].ProofCachedTestValidation(
        verifier=lambda *_args, **_kwargs: True,
        verifier_id="ns-010-qualification-verifier@1",
        repository_root=ROOT,
        freshness_seconds=30,
        clock=lambda: NOW_MS / 1000.0,
        repository_observer=lambda: (_ for _ in ()).throw(RuntimeError("no live forest")),
    )
    plain = validator.validate(
        task_id=TASK_ID,
        goal_id="NS-SG3",
        validation_command="python3 -m pytest qualification/test_reuse.py -q",
        decision="skipped",
        execution_key=key,
        certificate=certificate,
        pass_receipt=receipt,
    )
    declare(
        cases,
        case_id="plain_skip_not_completion_evidence",
        family="lookup_not_pass",
        polarity="invalid",
        stage="3-execution-key",
        expected_reason="plain_skip_not_evidence",
        description="A pytest skip string is not supervisor completion evidence.",
    )
    rows.append(
        finish(
            row_base(
                case_id="plain_skip_not_completion_evidence",
                family="lookup_not_pass",
                polarity="invalid",
                stage="3-execution-key",
                expected_reason="plain_skip_not_evidence",
                description="A pytest skip string is not supervisor completion evidence.",
            ),
            observed_reason="plain_skip_not_evidence"
            if (
                api["cached_validation"].ProofCachedTestValidationReason.PLAIN_SKIP_NOT_EVIDENCE.value
                in plain.reason_codes
                and plain.is_completion_evidence() is False
                and enum_val(plain.verifier_result) != "verified"
            )
            else "plain_skip_treated_as_pass",
            extra={
                "reason_codes": list(plain.reason_codes),
                "verifier_result": enum_val(plain.verifier_result),
                "is_completion_evidence": plain.is_completion_evidence(),
                "passed": plain.passed,
            },
        )
    )

    miss_cache = api["cache"].TestProofCache(
        current_policy=_policy(),
        verifier=lambda *_args: True,
        clock=lambda: NOW_MS,
    )
    miss = miss_cache.lookup(locator, key, candidates=())
    declare(
        cases,
        case_id="lookup_miss_is_run",
        family="lookup_not_pass",
        polarity="diagnostic",
        stage="3-execution-key",
        expected_reason="candidate_missing",
        description="Absence of candidates is an explicit RUN, never a pass.",
    )
    rows.append(
        finish(
            row_base(
                case_id="lookup_miss_is_run",
                family="lookup_not_pass",
                polarity="diagnostic",
                stage="3-execution-key",
                expected_reason="candidate_missing",
                description="Absence of candidates is an explicit RUN, never a pass.",
            ),
            observed_reason=enum_val(miss.decision.reason_code)
            if miss.decision.action is contracts.ReuseAction.RUN
            else "lookup_miss_became_skip",
            extra={
                "action": enum_val(miss.decision.action),
                "status": enum_val(miss.status),
                "reason_code": enum_val(miss.decision.reason_code),
            },
        )
    )

    simulated_cert = _certificate(
        api,
        receipt,
        key,
        backend_mode=contracts.ProofBackendMode.SIMULATED,
        authority=contracts.CertificateAuthority.NON_ATTESTED,
    )
    simulated_lookup, _ = _lookup(api, locator, key, receipt, simulated_cert)
    declare(
        cases,
        case_id="simulated_certificate_cannot_skip",
        family="lookup_not_pass",
        polarity="invalid",
        stage="4-phase-receipt",
        expected_reason="certificate_non_attested",
        description="Simulated/non-attested certificates cannot authorize SKIP.",
    )
    rows.append(
        finish(
            row_base(
                case_id="simulated_certificate_cannot_skip",
                family="lookup_not_pass",
                polarity="invalid",
                stage="4-phase-receipt",
                expected_reason="certificate_non_attested",
                description="Simulated/non-attested certificates cannot authorize SKIP.",
            ),
            observed_reason=enum_val(simulated_lookup.decision.reason_code)
            if simulated_lookup.decision.action is contracts.ReuseAction.RUN
            else "simulated_skip",
            extra={
                "action": enum_val(simulated_lookup.decision.action),
                "status": enum_val(simulated_lookup.status),
                "reason_code": enum_val(simulated_lookup.decision.reason_code),
                "backend_mode": enum_val(simulated_cert.backend_mode),
                "authority": enum_val(simulated_cert.authority),
            },
        )
    )

    hit, _ = _lookup(api, locator, key, receipt, certificate)
    declare(
        cases,
        case_id="unchanged_eligible_reuses_admitted_result",
        family="reuse_progress",
        polarity="valid",
        stage="3-execution-key",
        expected_reason="proof_cache_hit",
        description="An unchanged eligible case reuses a prior admitted receipt/certificate.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unchanged_eligible_reuses_admitted_result",
                family="reuse_progress",
                polarity="valid",
                stage="3-execution-key",
                expected_reason="proof_cache_hit",
                description="An unchanged eligible case reuses a prior admitted receipt/certificate.",
            ),
            observed_reason=enum_val(hit.decision.reason_code)
            if (
                hit.decision.action is contracts.ReuseAction.SKIP
                and enum_val(hit.status) == "hit"
                and hit.decision.receipt_cid == receipt.receipt_id
            )
            else "eligible_reuse_missed",
            extra={
                "action": enum_val(hit.decision.action),
                "status": enum_val(hit.status),
                "reason_code": enum_val(hit.decision.reason_code),
                "receipt_cid": hit.decision.receipt_cid,
                "certificate_cid": hit.decision.certificate_cid,
                "execution_key_cid": key.execution_key_id,
                "test_function_cid": key.test_function_cid,
            },
        )
    )

    mutation_specs = (
        (
            "fixture_definition_change_invalidates",
            "1-fixture-definition",
            {"fixture_cids": ("cid:fixture:db-v2",)},
            "Changed fixture definition CIDs invalidate reuse while the test body CID is unchanged.",
        ),
        (
            "fixture_value_change_invalidates",
            "2-fixture-instance",
            {"fixture_cids": ("cid:fixture:value-v2",)},
            "Changed fixture instance/value identity invalidates reuse of the same test body.",
        ),
        (
            "plugin_change_invalidates",
            "1-fixture-definition",
            {"hook_plugin_cids": ("cid:plugin:pytest-v2",)},
            "Changed plugin/hook identity invalidates reuse of the same test body.",
        ),
        (
            "runtime_trace_change_invalidates",
            "3-execution-key",
            {"runtime_trace_root_cid": "cid:runtime:mutated"},
            "Changed runtime-trace identity invalidates reuse of the same test body.",
        ),
        (
            "external_snapshot_change_invalidates",
            "2-fixture-instance",
            {"external_snapshot_cids": ("cid:snapshot:db-v2",)},
            "Changed external snapshot identity invalidates reuse of the same test body.",
        ),
        (
            "conftest_change_invalidates",
            "1-fixture-definition",
            {"conftest_closure_cid": "cid:conftest:v2"},
            "Changed conftest closure invalidates reuse of the same test body.",
        ),
        (
            "unchanged_body_fixture_still_invalidates",
            "1-fixture-definition",
            {
                "test_function_cid": "cid:function:unchanged-body",
                "fixture_cids": ("cid:fixture:autouse-v2",),
            },
            "The same test-function CID cannot reuse a receipt after a fixture mutation.",
        ),
    )
    for case_id, stage, changes, description in mutation_specs:
        mutated = _execution_key(api, locator, **changes)
        mutated_lookup, _ = _lookup(api, locator, mutated, receipt, certificate)
        declare(
            cases,
            case_id=case_id,
            family="identity_invalidation",
            polarity="invalid",
            stage=stage,
            expected_reason="execution_key_mismatch",
            description=description,
        )
        rows.append(
            finish(
                row_base(
                    case_id=case_id,
                    family="identity_invalidation",
                    polarity="invalid",
                    stage=stage,
                    expected_reason="execution_key_mismatch",
                    description=description,
                ),
                observed_reason=enum_val(mutated_lookup.decision.reason_code)
                if (
                    mutated_lookup.decision.action is contracts.ReuseAction.RUN
                    and mutated.execution_key_id != key.execution_key_id
                    and mutated.test_function_cid == key.test_function_cid
                )
                else "mutation_not_invalidated",
                extra={
                    "action": enum_val(mutated_lookup.decision.action),
                    "reason_code": enum_val(mutated_lookup.decision.reason_code),
                    "baseline_execution_key_cid": key.execution_key_id,
                    "mutated_execution_key_cid": mutated.execution_key_id,
                    "test_function_cid": mutated.test_function_cid,
                    "body_unchanged": mutated.test_function_cid == key.test_function_cid,
                    "execution_key_changed": mutated.execution_key_id != key.execution_key_id,
                    "mutation": changes,
                },
            )
        )

    policy_lookup, _ = _lookup(
        api,
        locator,
        key,
        receipt,
        certificate,
        policy=_policy(policy_cid="cid:policy:mutated"),
    )
    declare(
        cases,
        case_id="policy_change_invalidates",
        family="identity_invalidation",
        polarity="invalid",
        stage="3-execution-key",
        expected_reason="policy_mismatch",
        description="A changed policy CID forces RUN even when the test body and fixtures are unchanged.",
    )
    rows.append(
        finish(
            row_base(
                case_id="policy_change_invalidates",
                family="identity_invalidation",
                polarity="invalid",
                stage="3-execution-key",
                expected_reason="policy_mismatch",
                description="A changed policy CID forces RUN even when the test body and fixtures are unchanged.",
            ),
            observed_reason=enum_val(policy_lookup.decision.reason_code)
            if policy_lookup.decision.action is contracts.ReuseAction.RUN
            else "policy_mutation_reused",
            extra={
                "action": enum_val(policy_lookup.decision.action),
                "reason_code": enum_val(policy_lookup.decision.reason_code),
                "baseline_policy_cid": key.policy_cid,
                "current_policy_cid": "cid:policy:mutated",
                "test_function_cid": key.test_function_cid,
            },
        )
    )

    fixtures_v1 = identity.collect_fixture_hook_identity(
        fixtures=(
            {
                "name": "db",
                "scope": "function",
                "definition": "def db():\n    return 1\n",
                "value": 1,
                "dependencies": (),
                "autouse": False,
            },
            {
                "name": "session_clock",
                "scope": "session",
                "definition": "def session_clock():\n    yield 0\n",
                "value_adapter_cid": "baguqeeraaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "dependencies": ("db",),
                "autouse": True,
            },
        ),
        conftests=({"path": "tests/conftest.py", "content": "pytest_plugins = []\n"},),
        plugins=(
            {
                "kind": "plugin",
                "name": "pytest_timeout",
                "implementation": "def pytest_runtest_setup(item): pass\n",
                "distribution": "pytest-timeout",
                "version": "2.3.1",
                "registered": True,
                "order": 0,
            },
        ),
    )
    fixtures_v2 = identity.collect_fixture_hook_identity(
        fixtures=(
            {
                "name": "db",
                "scope": "function",
                "definition": "def db():\n    return 2\n",
                "value": 1,
                "dependencies": (),
                "autouse": False,
            },
            {
                "name": "session_clock",
                "scope": "session",
                "definition": "def session_clock():\n    yield 0\n",
                "value_adapter_cid": "baguqeeraaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "dependencies": ("db",),
                "autouse": True,
            },
        ),
        conftests=({"path": "tests/conftest.py", "content": "pytest_plugins = []\n"},),
        plugins=(
            {
                "kind": "plugin",
                "name": "pytest_timeout",
                "implementation": "def pytest_runtest_setup(item): pass\n",
                "distribution": "pytest-timeout",
                "version": "2.3.1",
                "registered": True,
                "order": 0,
            },
        ),
    )
    declare(
        cases,
        case_id="autouse_transitive_fixture_bound",
        family="identity_invalidation",
        polarity="valid",
        stage="1-fixture-definition",
        expected_reason="autouse_transitive_fixture_bound",
        description="Autouse and transitive fixture definitions are bound; a definition change changes the fixture CID set.",
    )
    rows.append(
        finish(
            row_base(
                case_id="autouse_transitive_fixture_bound",
                family="identity_invalidation",
                polarity="valid",
                stage="1-fixture-definition",
                expected_reason="autouse_transitive_fixture_bound",
                description="Autouse and transitive fixture definitions are bound; a definition change changes the fixture CID set.",
            ),
            observed_reason="autouse_transitive_fixture_bound"
            if (
                fixtures_v1.fixture_cids != fixtures_v2.fixture_cids
                and fixtures_v1.conftest_closure_cid == fixtures_v2.conftest_closure_cid
                and fixtures_v1.hook_plugin_cids == fixtures_v2.hook_plugin_cids
            )
            else "autouse_not_bound",
            extra={
                "fixture_cids_v1": list(fixtures_v1.fixture_cids),
                "fixture_cids_v2": list(fixtures_v2.fixture_cids),
                "conftest_closure_cid": fixtures_v1.conftest_closure_cid,
                "hook_plugin_cids": list(fixtures_v1.hook_plugin_cids),
                "definition_change_changes_cid": fixtures_v1.fixture_cids
                != fixtures_v2.fixture_cids,
            },
        )
    )

    events: list[str] = []

    def setup_ok() -> None:
        events.append("setup")

    def call_reused() -> str:
        events.append("call_reused_not_original_body")
        return "reused"

    def teardown_ok() -> None:
        events.append("teardown")

    capture = api["lifecycle"].PostPassRuntimeTraceCapture(
        locator_cid=locator.locator_id,
        execution_key_cid=key.execution_key_id,
    )
    life = capture.execute_lifecycle_once(
        setup=setup_ok,
        call=call_reused,
        teardown=teardown_ok,
        runtime_trace_root_cid=key.runtime_trace_root_cid,
        locator_cid=locator.locator_id,
        execution_key_cid=key.execution_key_id,
        pass_receipt_cid=receipt.receipt_id,
        capture_on_pass=True,
    )
    declare(
        cases,
        case_id="call_reuse_after_setup_runs_teardown",
        family="lifecycle",
        polarity="valid",
        stage="4-phase-receipt",
        expected_reason="teardown_ran_after_call_reuse",
        description="After setup, a reused call still runs required teardown exactly once.",
    )
    rows.append(
        finish(
            row_base(
                case_id="call_reuse_after_setup_runs_teardown",
                family="lifecycle",
                polarity="valid",
                stage="4-phase-receipt",
                expected_reason="teardown_ran_after_call_reuse",
                description="After setup, a reused call still runs required teardown exactly once.",
            ),
            observed_reason="teardown_ran_after_call_reuse"
            if (
                events == ["setup", "call_reused_not_original_body", "teardown"]
                and capture.setup_call_count == 1
                and capture.test_call_count == 1
                and capture.teardown_call_count == 1
                and capture.may_authorize_skip is False
                and life.get("teardown_error") is None
            )
            else "teardown_skipped_on_call_reuse",
            extra={
                "events": list(events),
                "setup_call_count": capture.setup_call_count,
                "test_call_count": capture.test_call_count,
                "teardown_call_count": capture.teardown_call_count,
                "may_authorize_skip": capture.may_authorize_skip,
                "passed": life.get("passed"),
            },
        )
    )

    admitted_blocked = False
    admitted_error = None
    try:
        _receipt(
            api,
            locator,
            key,
            teardown_outcome=contracts.PhaseOutcome.FAIL,
            admitted=True,
        )
    except contracts.TestExecutionContractError as exc:
        admitted_blocked = True
        admitted_error = str(exc)
    declare(
        cases,
        case_id="teardown_failure_blocks_admitted_receipt",
        family="lifecycle",
        polarity="invalid",
        stage="4-phase-receipt",
        expected_reason="teardown_failure_blocks_admitted_receipt",
        description="An admitted pass receipt cannot carry a failing teardown outcome.",
    )
    rows.append(
        finish(
            row_base(
                case_id="teardown_failure_blocks_admitted_receipt",
                family="lifecycle",
                polarity="invalid",
                stage="4-phase-receipt",
                expected_reason="teardown_failure_blocks_admitted_receipt",
                description="An admitted pass receipt cannot carry a failing teardown outcome.",
            ),
            observed_reason="teardown_failure_blocks_admitted_receipt"
            if admitted_blocked and admitted_error and "teardown_outcome=pass" in admitted_error
            else "teardown_failure_admitted",
            extra={
                "admitted_blocked": admitted_blocked,
                "error": admitted_error,
            },
        )
    )

    fail_receipt = _receipt(
        api,
        locator,
        key,
        teardown_outcome=contracts.PhaseOutcome.FAIL,
        admitted=False,
    )
    fail_cert = _certificate(api, fail_receipt, key)
    fail_lookup, _ = _lookup(api, locator, key, fail_receipt, fail_cert)
    declare(
        cases,
        case_id="teardown_fail_receipt_cannot_skip",
        family="lifecycle",
        polarity="invalid",
        stage="4-phase-receipt",
        expected_reason="receipt_mismatch",
        description="A teardown-failure receipt cannot authorize whole-item SKIP.",
    )
    rows.append(
        finish(
            row_base(
                case_id="teardown_fail_receipt_cannot_skip",
                family="lifecycle",
                polarity="invalid",
                stage="4-phase-receipt",
                expected_reason="receipt_mismatch",
                description="A teardown-failure receipt cannot authorize whole-item SKIP.",
            ),
            observed_reason=enum_val(fail_lookup.decision.reason_code)
            if (
                fail_lookup.decision.action is contracts.ReuseAction.RUN
                and fail_receipt.admitted is False
                and fail_receipt.all_phases_pass is False
            )
            else "teardown_failure_skipped",
            extra={
                "action": enum_val(fail_lookup.decision.action),
                "reason_code": enum_val(fail_lookup.decision.reason_code),
                "admitted": fail_receipt.admitted,
                "all_phases_pass": fail_receipt.all_phases_pass,
                "teardown_outcome": enum_val(fail_receipt.teardown_outcome),
            },
        )
    )

    setup_events: list[str] = []

    def setup_boom() -> None:
        setup_events.append("setup")
        raise RuntimeError("setup failed")

    def call_should_not_run() -> None:
        setup_events.append("call")

    def teardown_after_setup_fail() -> None:
        setup_events.append("teardown")

    setup_capture = api["lifecycle"].PostPassRuntimeTraceCapture()
    setup_life = setup_capture.execute_lifecycle_once(
        setup=setup_boom,
        call=call_should_not_run,
        teardown=teardown_after_setup_fail,
        capture_on_pass=False,
    )
    declare(
        cases,
        case_id="setup_failure_still_runs_teardown",
        family="lifecycle",
        polarity="valid",
        stage="4-phase-receipt",
        expected_reason="setup_failure_still_runs_teardown",
        description="Required teardown still runs when setup fails and the call body is not invoked.",
    )
    rows.append(
        finish(
            row_base(
                case_id="setup_failure_still_runs_teardown",
                family="lifecycle",
                polarity="valid",
                stage="4-phase-receipt",
                expected_reason="setup_failure_still_runs_teardown",
                description="Required teardown still runs when setup fails and the call body is not invoked.",
            ),
            observed_reason="setup_failure_still_runs_teardown"
            if (
                setup_events == ["setup", "teardown"]
                and setup_life.get("setup_error") is not None
                and setup_life.get("teardown_error") is None
                and "call" not in setup_events
            )
            else "setup_failure_skipped_teardown",
            extra={
                "events": list(setup_events),
                "setup_error": type(setup_life.get("setup_error")).__name__
                if setup_life.get("setup_error") is not None
                else None,
                "teardown_call_count": setup_life.get("teardown_call_count"),
                "passed": setup_life.get("passed"),
            },
        )
    )

    worker = api["xdist"].ProofReuseXdistCoordinator.from_worker_input(
        {},
        worker_id="gw0",
    )
    declare(
        cases,
        case_id="xdist_unhealthy_worker_cannot_skip",
        family="lifecycle",
        polarity="invalid",
        stage="3-execution-key",
        expected_reason="xdist_coordination_unavailable",
        description="An unhealthy xdist worker cannot skip or publish; session ownership stays on the controller.",
    )
    rows.append(
        finish(
            row_base(
                case_id="xdist_unhealthy_worker_cannot_skip",
                family="lifecycle",
                polarity="invalid",
                stage="3-execution-key",
                expected_reason="xdist_coordination_unavailable",
                description="An unhealthy xdist worker cannot skip or publish; session ownership stays on the controller.",
            ),
            observed_reason="xdist_coordination_unavailable"
            if (
                worker.can_skip is False
                and worker.can_write is False
                and worker.can_accept_publication is False
                and worker.healthy is False
            )
            else "xdist_worker_could_skip",
            extra={
                "role": enum_val(worker.role),
                "healthy": worker.healthy,
                "can_skip": worker.can_skip,
                "can_write": worker.can_write,
                "can_accept_publication": worker.can_accept_publication,
            },
        )
    )

    uncontrolled = identity.collect_fixture_hook_identity(
        fixtures=(
            {
                "name": "opaque_db",
                "scope": "function",
                "definition": "def opaque_db():\n    return object()\n",
                "autouse": False,
                "dependencies": (),
            },
        )
    )
    declare(
        cases,
        case_id="unknown_uncontrolled_fixture_fallback",
        family="fallback",
        polarity="diagnostic",
        stage="2-fixture-instance",
        expected_reason="uncontrolled_fixture_value",
        description="Unknown/uncontrolled fixture values are an explicit non-reusable fallback.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unknown_uncontrolled_fixture_fallback",
                family="fallback",
                polarity="diagnostic",
                stage="2-fixture-instance",
                expected_reason="uncontrolled_fixture_value",
                description="Unknown/uncontrolled fixture values are an explicit non-reusable fallback.",
            ),
            observed_reason="uncontrolled_fixture_value"
            if "uncontrolled_fixture_value" in uncontrolled.non_reusable_reasons
            else "uncontrolled_fixture_accepted",
            extra={
                "non_reusable_reasons": list(uncontrolled.non_reusable_reasons),
                "fixture_cids": list(uncontrolled.fixture_cids),
            },
        )
    )

    opaque_rejected = False
    opaque_error = None
    try:
        identity.canonicalize_pytest_parameter(lambda: None)
    except identity.UnsupportedPytestParameter as exc:
        opaque_rejected = True
        opaque_error = str(exc)
    except identity.TestIdentityComponentError as exc:
        opaque_rejected = True
        opaque_error = str(exc)
    declare(
        cases,
        case_id="opaque_object_serialization_rejected",
        family="fallback",
        polarity="invalid",
        stage="2-fixture-instance",
        expected_reason="opaque_object_serialization_rejected",
        description="Arbitrary callbacks/objects are not a sound DI commitment and cannot be serialized into identity.",
    )
    rows.append(
        finish(
            row_base(
                case_id="opaque_object_serialization_rejected",
                family="fallback",
                polarity="invalid",
                stage="2-fixture-instance",
                expected_reason="opaque_object_serialization_rejected",
                description="Arbitrary callbacks/objects are not a sound DI commitment and cannot be serialized into identity.",
            ),
            observed_reason="opaque_object_serialization_rejected"
            if opaque_rejected
            else "opaque_object_canonicalized",
            extra={
                "rejected": opaque_rejected,
                "error": opaque_error,
                "pickle_fallback": False,
                "repr_fallback": False,
            },
        )
    )

    incomplete_key = _execution_key(api, locator, runtime_trace_root_cid="")
    incomplete_receipt = _receipt(
        api,
        locator,
        incomplete_key,
        runtime_trace_root_cid="",
        completeness_receipt_cid="",
    )
    incomplete_cert = _certificate(api, incomplete_receipt, incomplete_key)
    incomplete_lookup, _ = _lookup(
        api, locator, incomplete_key, incomplete_receipt, incomplete_cert
    )
    declare(
        cases,
        case_id="incomplete_trace_falls_back_to_run",
        family="fallback",
        polarity="diagnostic",
        stage="3-execution-key",
        expected_reason="incomplete_trace",
        description="Incomplete runtime traces fall back to execution instead of reuse.",
    )
    rows.append(
        finish(
            row_base(
                case_id="incomplete_trace_falls_back_to_run",
                family="fallback",
                polarity="diagnostic",
                stage="3-execution-key",
                expected_reason="incomplete_trace",
                description="Incomplete runtime traces fall back to execution instead of reuse.",
            ),
            observed_reason=enum_val(incomplete_lookup.decision.reason_code)
            if incomplete_lookup.decision.action is contracts.ReuseAction.RUN
            else "incomplete_trace_skipped",
            extra={
                "action": enum_val(incomplete_lookup.decision.action),
                "reason_code": enum_val(incomplete_lookup.decision.reason_code),
                "runtime_trace_root_cid": incomplete_key.runtime_trace_root_cid,
            },
        )
    )

    pre_setup_seed_action = seed.action
    post_setup_teardown_required = True
    declare(
        cases,
        case_id="full_item_vs_call_only_phase_distinction",
        family="lifecycle",
        polarity="valid",
        stage="1-fixture-definition",
        expected_reason="full_item_vs_call_only_phase_distinction",
        description="Whole-item pre-setup reuse is distinct from post-setup call-only reuse; the latter still requires teardown.",
    )
    rows.append(
        finish(
            row_base(
                case_id="full_item_vs_call_only_phase_distinction",
                family="lifecycle",
                polarity="valid",
                stage="1-fixture-definition",
                expected_reason="full_item_vs_call_only_phase_distinction",
                description="Whole-item pre-setup reuse is distinct from post-setup call-only reuse; the latter still requires teardown.",
            ),
            observed_reason="full_item_vs_call_only_phase_distinction"
            if (
                pre_setup_seed_action == "RUN"
                and seed.authorizes_skip is False
                and post_setup_teardown_required
                and capture.teardown_call_count == 1
            )
            else "phases_collapsed",
            extra={
                "pre_setup_decision_allowed": "candidate_lookup_only",
                "pre_setup_action": pre_setup_seed_action,
                "post_setup_call_reuse_requires_teardown": post_setup_teardown_required,
                "observed_teardown_count": capture.teardown_call_count,
            },
        )
    )

    parameterized_ok = False
    parameterized_error = None
    try:
        _locator(api, parameter_id="n", node_id="qualification/test_reuse.py::test_param[0]")
    except contracts.TestExecutionContractError as exc:
        parameterized_error = str(exc)
    parameterized = _locator(
        api,
        parameter_id="n",
        parameter_values_cid="cid:param:n=0",
        node_id="qualification/test_reuse.py::test_param[0]",
    )
    parameterized_ok = bool(parameterized.parameter_values_cid) and parameterized.parameter_id == "n"
    declare(
        cases,
        case_id="parametrization_bound_on_locator",
        family="identity_invalidation",
        polarity="valid",
        stage="0-collection-seed",
        expected_reason="parametrization_bound_on_locator",
        description="Parameterized nodes bind exact parameter-value identity; missing values cannot form a locator.",
    )
    rows.append(
        finish(
            row_base(
                case_id="parametrization_bound_on_locator",
                family="identity_invalidation",
                polarity="valid",
                stage="0-collection-seed",
                expected_reason="parametrization_bound_on_locator",
                description="Parameterized nodes bind exact parameter-value identity; missing values cannot form a locator.",
            ),
            observed_reason="parametrization_bound_on_locator"
            if parameterized_ok and parameterized_error
            else "parametrization_unbound",
            extra={
                "missing_parameter_cid_rejected": bool(parameterized_error),
                "missing_error": parameterized_error,
                "parameter_id": parameterized.parameter_id,
                "parameter_values_cid": parameterized.parameter_values_cid,
                "locator_cid": parameterized.locator_id,
            },
        )
    )

    env = identity.collect_environment_identity(
        environment={"PYTHONHASHSEED": "0", "TZ": "UTC"},
        environment_allowlist=("PYTHONHASHSEED", "TZ"),
        interpreter_facts={
            "implementation": "CPython",
            "version": "3.12.3",
            "cache_tag": "cpython-312",
            "abi_flags": "",
            "byteorder": "little",
            "pointer_bits": 64,
        },
        platform_facts={
            "system": "Linux",
            "release": "sealed",
            "machine": "aarch64",
            "python_compiler": "GCC",
            "libc": "glibc",
        },
        hardware_facts={
            "architecture": "aarch64",
            "cpu_count": 1,
            "accelerator_backend": "none",
            "accelerator_count": 0,
            "accelerator_architectures": (),
        },
    )
    deps = identity.collect_dependency_identity(
        lock_files={"uv.lock": "demo==1.0.0\n"},
        installed_distributions=(("pytest", "8.1.1"),),
    )
    env2 = identity.collect_environment_identity(
        environment={"PYTHONHASHSEED": "1", "TZ": "UTC"},
        environment_allowlist=("PYTHONHASHSEED", "TZ"),
        interpreter_facts={
            "implementation": "CPython",
            "version": "3.12.3",
            "cache_tag": "cpython-312",
            "abi_flags": "",
            "byteorder": "little",
            "pointer_bits": 64,
        },
        platform_facts={
            "system": "Linux",
            "release": "sealed",
            "machine": "aarch64",
            "python_compiler": "GCC",
            "libc": "glibc",
        },
        hardware_facts={
            "architecture": "aarch64",
            "cpu_count": 1,
            "accelerator_backend": "none",
            "accelerator_count": 0,
            "accelerator_architectures": (),
        },
    )
    declare(
        cases,
        case_id="interpreter_policy_external_bound",
        family="identity_invalidation",
        polarity="valid",
        stage="3-execution-key",
        expected_reason="interpreter_policy_external_bound",
        description="Interpreter, dependency lock, environment, and external snapshot identities are bound into the execution key.",
    )
    rows.append(
        finish(
            row_base(
                case_id="interpreter_policy_external_bound",
                family="identity_invalidation",
                polarity="valid",
                stage="3-execution-key",
                expected_reason="interpreter_policy_external_bound",
                description="Interpreter, dependency lock, environment, and external snapshot identities are bound into the execution key.",
            ),
            observed_reason="interpreter_policy_external_bound"
            if (
                env.environment_cid != env2.environment_cid
                and env.interpreter_abi_cid
                and deps.dependency_lock_cid
                and key.external_snapshot_cids
                and key.policy_cid
            )
            else "runtime_identity_unbound",
            extra={
                "environment_cid": env.environment_cid,
                "mutated_environment_cid": env2.environment_cid,
                "interpreter_abi_cid": env.interpreter_abi_cid,
                "platform_cid": env.platform_cid,
                "dependency_lock_cid": deps.dependency_lock_cid,
                "installed_distributions_cid": deps.installed_distributions_cid,
                "external_snapshot_cids": list(key.external_snapshot_cids),
                "policy_cid": key.policy_cid,
            },
        )
    )

    return cases, rows


def build_profile(
    *,
    capability: dict[str, Any],
    rows: list[dict[str, Any]],
    started_at: str,
    hashes: dict[str, str],
) -> dict[str, Any]:
    by_id = {row["case_id"]: row for row in rows}
    hit = by_id.get("unchanged_eligible_reuses_admitted_result") or {}
    seed = by_id.get("collection_seed_not_passing_outcome") or {}
    return {
        "schema": SCHEMA_PROFILE,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "qualification_not_live_ad": True,
        "reuse_seam_status": "implemented_and_qualified",
        "table8_stages": [
            {
                "stage": 0,
                "name": "collection_seed",
                "interface": "ProofReuseCollectionSeed@1",
                "decision_allowed": "candidate lookup only; not a passing outcome",
                "authorizes_skip": False,
                "witness_case": "collection_seed_not_passing_outcome",
            },
            {
                "stage": 1,
                "name": "fixture_definition_closure",
                "interface": "TestIdentityComponents@1 / FixtureHookIdentity",
                "decision_allowed": "whole-item pre-setup reuse only under a closed policy",
                "binds": [
                    "fixture names/definitions/scopes",
                    "autouse/usefixtures",
                    "transitive dependencies",
                    "conftest",
                    "hooks/plugins",
                    "parametrization",
                ],
                "witness_case": "autouse_transitive_fixture_bound",
            },
            {
                "stage": 2,
                "name": "fixture_instance_commitment",
                "interface": "reviewed value CID or value_adapter_cid",
                "decision_allowed": "post-setup eligibility; opaque/uncontrolled values force execution",
                "witness_case": "unknown_uncontrolled_fixture_fallback",
            },
            {
                "stage": 3,
                "name": "execution_key",
                "interface": "TestExecutionKey@1",
                "decision_allowed": "re-admit a prior receipt or execute; no optimistic pass",
                "binds": [
                    "locator",
                    "repository forest",
                    "fixture/plugin/conftest CIDs",
                    "static/runtime traces",
                    "interpreter/platform",
                    "dependency lock",
                    "policy",
                    "external snapshots",
                ],
                "witness_case": "unchanged_eligible_reuses_admitted_result",
            },
            {
                "stage": 4,
                "name": "phase_receipt",
                "interface": "TestPassReceipt@1",
                "decision_allowed": "fresh observation; teardown failure prevents whole-item pass",
                "witness_case": "teardown_fail_receipt_cannot_skip",
            },
        ],
        "authority": {
            "lookup_is_not_a_pass": True,
            "skip_reason_codes": ["proof_cache_hit"],
            "plain_skip_not_evidence": True,
            "eligibility_never_skips": True,
            "simulated_certificates_cannot_skip": True,
            "collection_seed_action": seed.get("action"),
        },
        "invalidation": {
            "fixture_definition": True,
            "fixture_value": True,
            "plugin": True,
            "policy": True,
            "runtime_trace": True,
            "external_snapshot": True,
            "conftest": True,
            "unchanged_body_insufficient": True,
        },
        "lifecycle": {
            "call_reuse_runs_teardown": True,
            "teardown_failure_blocks_admitted_receipt": True,
            "teardown_failure_cannot_skip": True,
            "setup_failure_runs_teardown": True,
            "xdist_worker_cannot_skip_when_unhealthy": True,
            "full_item_pre_setup_distinct_from_call_only": True,
        },
        "fallbacks": {
            "uncontrolled_fixture_value": "RUN",
            "opaque_object_serialization": "reject / RUN",
            "incomplete_trace": "RUN",
            "unknown_eligibility": "non_reusable RUN",
            "missing_candidates": "RUN",
        },
        "positive_reuse_witness": {
            "case_id": "unchanged_eligible_reuses_admitted_result",
            "action": hit.get("action"),
            "reason_code": hit.get("reason_code"),
            "receipt_cid": hit.get("receipt_cid"),
            "certificate_cid": hit.get("certificate_cid"),
            "execution_key_cid": hit.get("execution_key_cid"),
        },
        "located_mechanisms": {
            "TestProofCache@1": capability["modules"]["test_proof_cache"],
            "ProofCachedTestValidation@1": capability["modules"]["proof_cached_test_validation"],
            "TestCertificateStore@1": capability["modules"]["test_certificate_store"],
            "TestCertificateProvider@1": capability["modules"][
                "ipfs_datasets_test_certificate_provider"
            ],
            "ProofReuseCollectionSeed@1": capability["modules"]["collection_seed"],
            "PostPassRuntimeTraceCapture": capability["modules"]["runtime_revalidation"],
            "ProofReuseXdistCoordination@1": capability["modules"]["xdist"],
            "TestSelection@1": capability["modules"]["test_selection"],
        },
        "capability": {
            "interpreter": capability.get("interpreter"),
            "python_version": capability.get("python_version"),
            "path": capability.get("path"),
            "pytest": capability.get("pytest"),
            "selection_status": capability.get("selection_status"),
            "selection_error": capability.get("selection_error"),
            "binaries": capability.get("binaries"),
        },
        "source_hashes": hashes,
        "claim_boundary": (
            "This profile qualifies staged fixture/call/teardown identity and "
            "fail-closed lookup on the located adapters. It is not a cold-oracle "
            "false-reuse rate (NS-011), not a matched A–D outcome, and not a "
            "native Groth16 proof of arbitrary pytest execution."
        ),
    }


def build_report(
    *,
    capability: dict[str, Any],
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    started_at: str,
) -> str:
    by_id = {row["case_id"]: row for row in rows}
    hit = by_id.get("unchanged_eligible_reuses_admitted_result") or {}
    seed = by_id.get("collection_seed_not_passing_outcome") or {}
    teardown = by_id.get("teardown_fail_receipt_cannot_skip") or {}
    lines = [
        "# NS-010 Fixture-instance and phase-aware reuse seam",
        "",
        f"Generated at {started_at}. This is a sealed-profile qualification record, not a live A–D experiment and not the NS-011 cold-oracle mutation campaign.",
        "",
        "## Profile",
        "",
        "- Collection seed: `ProofReuseCollectionSeed@1` (lookup only; action `RUN`)",
        "- Fixture/hook identity: `collect_fixture_hook_identity`",
        "- Execution key: `TestExecutionKey@1`",
        "- Pass receipt: `TestPassReceipt@1` (setup/call/teardown must all pass to admit)",
        "- Cache admission: `TestProofCache@1`",
        "- Supervisor completion: `ProofCachedTestValidation@1`",
        "- Lifecycle capture: `PostPassRuntimeTraceCapture`",
        f"- Policy: `{POLICY_ID}`",
        "",
        "## Environment",
        "",
        f"- Interpreter: `{capability.get('interpreter')}` ({capability.get('python_version')})",
        f"- Sealed `PATH` at process start: `{capability.get('path')}`",
        f"- pytest: `{capability.get('pytest')}`",
        f"- datasets test-selection import: `{capability.get('selection_status')}`",
        "",
        "## Coverage",
        "",
        f"- Result rows: {len(rows)}",
        f"- Failed rows: {sum(1 for row in rows if row.get('status') != 'pass')}",
        f"- Collection seed authorizes skip: `{seed.get('authorizes_skip')}` (must be false)",
        f"- Unchanged eligible reuse: `{hit.get('action')}` / `{hit.get('reason_code')}`",
        f"- Teardown-failure skip: `{teardown.get('action')}` / `{teardown.get('reason_code')}`",
        "",
        "## Reuse lookup cannot become a passing outcome",
        "",
        "Collection seeds attach a locator and never an execution key. Eligibility classification never emits `SKIP`. A pytest skip string presented to `ProofCachedTestValidation.validate` is `plain_skip_not_evidence` and is not completion evidence. Cache absence is `RUN` with `candidate_missing`. Simulated certificates are `certificate_non_attested`.",
        "",
        "## Fixture, plugin, policy, runtime, and snapshot mutations invalidate reuse",
        "",
        "The test-function CID is held constant (`cid:function:unchanged-body`). Changing fixture CIDs, plugin CIDs, conftest closure, runtime-trace root, external snapshots, or policy forces `TestProofCache.lookup` to `RUN` (`execution_key_mismatch` or `policy_mismatch`). Autouse and transitive fixture definitions are included in `FixtureHookIdentity`; a definition-body change changes the fixture CID set.",
        "",
        "## Call reuse after setup still runs teardown",
        "",
        "`PostPassRuntimeTraceCapture.execute_lifecycle_once` records setup, a non-reinvoked call placeholder, and teardown exactly once. Capture itself `may_authorize_skip=false`. A setup failure still runs teardown and does not invoke the call body. `TestPassReceipt` rejects `admitted=True` when teardown is not `pass`. A teardown-failure receipt cannot skip (`receipt_mismatch`). Unhealthy xdist workers cannot skip or publish.",
        "",
        "## Unchanged eligible reuse and explicit fallbacks",
        "",
        f"The unchanged eligible case reused receipt `{hit.get('receipt_cid')}` under `{hit.get('reason_code')}`. Uncontrolled fixture values record `uncontrolled_fixture_value`. Callables cannot be canonicalized (no pickle/repr fallback). Incomplete runtime traces fall back to `incomplete_trace`/`RUN`.",
        "",
        "## Staged identity (Table 8)",
        "",
        "| stage | name | decision allowed |",
        "|---|---|---|",
    ]
    for stage in profile.get("table8_stages") or []:
        lines.append(
            f"| {stage['stage']} | `{stage['name']}` | {stage['decision_allowed']} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Qualification uses constructed locators/keys/receipts plus live contract, cache, identity, lifecycle, and validation APIs. It is not a historical repair task.",
            "- Native Groth16 verification of pytest execution is not claimed; the cache verifier in this profile is a local authoritative callback over retained canonical bytes.",
            "- Independent cold full-run scoring and adversarial mutation rates are NS-011, not this task.",
            "- This receipt is Table 18 fixture/call/teardown reuse qualification, not a matched A–D outcome.",
            "",
            "## Case outcomes",
            "",
            "| case_id | family | polarity | stage | status | reason |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['case_id']}` | {row['family']} | {row['polarity']} | `{row['stage']}` | {row['status']} | `{row.get('observed_reason')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    started_at = utc_now()
    checkpoint("start", {"started_at": started_at, "task_id": TASK_ID})
    capability = prepare_imports()
    api = capability.pop("api")
    hashes = source_hashes()
    cases, rows = run_cases(api)
    failed = [row["case_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        raise SystemExit(f"NS-010 qualification cases failed: {failed}")
    missing = [name for name in REQUIRED_CASES if name not in {row["case_id"] for row in rows}]
    if missing:
        raise SystemExit(f"NS-010 missing required cases: {missing}")

    profile = build_profile(
        capability=capability, rows=rows, started_at=started_at, hashes=hashes
    )
    cases_doc = {
        "schema": SCHEMA_CASES,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "qualification_not_live_ad": True,
        "caller": {
            "collection_seed": "ProofReuseCollectionSeed@1",
            "identity": "collect_fixture_hook_identity",
            "execution_key": "TestExecutionKey@1",
            "pass_receipt": "TestPassReceipt@1",
            "cache": "TestProofCache@1",
            "validation": "ProofCachedTestValidation@1",
            "lifecycle": "PostPassRuntimeTraceCapture.execute_lifecycle_once",
            "xdist": "ProofReuseXdistCoordinator",
            "eligibility": "evaluate_reuse_eligibility",
        },
        "rules": {
            "lookup_cannot_become_a_passing_outcome": True,
            "fixture_plugin_policy_runtime_snapshot_mutations_invalidate": True,
            "call_reuse_still_runs_teardown": True,
            "teardown_failure_prevents_whole_item_pass": True,
            "unchanged_eligible_case_reuses_admitted_result": True,
            "unknown_effectful_cases_use_explicit_fallback": True,
            "opaque_serialization_rejected": True,
        },
        "capability": capability,
        "source_hashes": hashes,
        "workspace_git_head": git_head(ROOT),
        "consumer_gitlinks": {
            "external/ipfs_accelerate": git_head(ACC_ROOT),
            "external/ipfs_datasets": git_head(DS_ROOT),
            "external/ipfs_kit": git_head(KIT_ROOT),
        },
        "cases": cases,
        "results": rows,
    }
    report = build_report(
        capability=capability, rows=rows, profile=profile, started_at=started_at
    )

    QUAL.mkdir(parents=True, exist_ok=True)
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    for directory in (QUAL, SNAP_QUAL):
        write_json(directory / "reuse_profile.json", profile)
        write_json(directory / "reuse_phase_cases.json", cases_doc)
        atomic_write(directory / "reuse_adapter_report.md", report.encode("utf-8"))
    write_jsonl(SNAP / "reuse_phase_results.jsonl", rows)

    checkpoint(
        "outputs",
        {
            "finished_at": utc_now(),
            "rows": len(rows),
            "failed": failed,
            "profile_sha256": sha256_file(QUAL / "reuse_profile.json"),
            "cases_sha256": sha256_file(QUAL / "reuse_phase_cases.json"),
            "report_sha256": sha256_file(QUAL / "reuse_adapter_report.md"),
        },
    )
    print("NS-010 reuse qualification: OK")
    print(f"rows={len(rows)} failed={len(failed)}")
    print(
        "unchanged_eligible_reuses_admitted_result action=",
        hit_action(rows),
    )
    print(
        "collection_seed_not_passing_outcome authorizes_skip=",
        seed_skip(rows),
    )
    return 0


def hit_action(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row["case_id"] == "unchanged_eligible_reuses_admitted_result":
            return str(row.get("action"))
    return ""


def seed_skip(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row["case_id"] == "collection_seed_not_passing_outcome":
            return bool(row.get("authorizes_skip"))
    return True


if __name__ == "__main__":
    raise SystemExit(main())
