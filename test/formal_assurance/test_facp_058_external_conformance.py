"""FACP-058: qualify an independent cross-language conformance implementation.

Acceptance (taskboard):
- Independent implementation passes the full required vector set with matching
  canonical identity/errors, or release remains blocked with exact
  counterexamples.
- Independence relationship is documented and content-bound.

Owns only the sanitized external-conformance receipt and this hermetic fan-in
test. FACP-035 Rust assurance_codec, public vectors, FACP-037/048/049 artifacts
are immutable inputs. Generated FACP-036 projections are not independent
evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "qualification"
    / "external_conformance.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
TCB_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "trusted_computing_base.json"
)
CCC_GATE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "gates"
    / "canonical_contracts_v1.json"
)
VECTORS_PATH = (
    REPO_ROOT
    / "Mcp-Plus-Plus"
    / "conformance"
    / "vectors"
    / "assurance-canonical-encoding.json"
)
ENCODING_SPEC_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "docs" / "spec" / "assurance-canonical-encoding.md"
)
CONTRACTS_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "schemas" / "assurance" / "v1" / "repository-contracts.json"
)
TRANSLATION_MODULE_PATH = (
    REPO_ROOT
    / "external"
    / "ipfs_datasets"
    / "ipfs_datasets_py"
    / "logic"
    / "translation_validation"
    / "formal_assurance.py"
)
GENERATED_MANIFEST_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "tools" / "assurance_idl" / "generated_manifest.json"
)
RUST_DIR = REPO_ROOT / "Mcp-Plus-Plus" / "tests-rs"
CODEC_RS = RUST_DIR / "src" / "assurance_codec.rs"
RUST_TEST_RS = RUST_DIR / "tests" / "assurance_translation_validation_test.rs"

RECEIPT_SCHEMA = "facp/external-conformance@1"
TASK_ID = "FACP-058"
GOAL_ID = "FACP-G810"
BUNDLE = "facp/release/external-conformance"
RELEASE = "external-conformance-v1"
VOCAB_SCHEMA = "facp/dag-cbor-profile@1"

REQUIRED_EVIDENCE_SUBSET = {
    "implementation_source_toolchain_identity",
    "positive_negative_mutation_vectors",
    "canonical_bytes_cids_errors",
    "assumptions",
    "failures",
}

REQUIRED_DEPENDS_ON = {"FACP-037", "FACP-048", "FACP-049"}
REQUIRED_SHARED_INPUTS = {"FACP-033", "FACP-035"}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)

REQUIRED_PROHIBITED_EFFECTS = {
    "use_generated_implementation_as_independent_validator",
    "network_interoperability_claim_without_observation",
    "omit_failing_vectors",
    "network",
    "provider_authored_completion",
    "introduce_unqualified_production_claim",
}

REQUIRED_CARGO_MARKERS = (
    "every_positive_vector_round_trips_with_exact_cid",
    "every_negative_and_mutation_vector_is_rejected",
    "independent_translation_validation_confirms_all_vectors",
    "does_not_trust_generator_without_validation",
    "test result: ok.",
)

REQUIRED_COMPOSITION_GUARANTEES = {
    "guarantee:mcp.normative_contract_registry",
    "guarantee:datasets.translation_receipt_names_loss",
}
REQUIRED_COMPOSITION_ASSUMPTIONS = {
    "assumption:datasets.canonical_contracts",
    "assumption:accelerate.operation_spec_closed",
    "assumption:swissknife.datasets_translation",
}
REQUIRED_COMPOSITION_BOUNDARIES = {
    "boundary:datasets->mcp.contracts",
    "boundary:accelerate->mcp.contracts",
    "boundary:swissknife->datasets.translation",
}

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_RECEIPT_CLAIM_KEYS = {
    "success",
    "available",
    "supported",
    "verified",
    "proven",
    "authorized",
    "allowed",
    "current",
    "production",
    "capability",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_content_sha256(receipt: dict[str, Any]) -> str:
    without_digest = {
        key: value for key, value in receipt.items() if key != "content_sha256"
    }
    canonical = json.dumps(
        without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _git_rev_parse(*args: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return completed.stdout.strip()


def _gitlink_commit(path: str) -> str:
    completed = subprocess.run(
        ["git", "ls-tree", "HEAD", path],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    parts = completed.stdout.strip().split()
    assert len(parts) >= 3, completed.stdout
    assert parts[1] == "commit", completed.stdout
    return parts[2]


def _run_out(cmd: list[str]) -> str:
    completed = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return completed.stdout.strip()


def _hermetic_cargo_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    env["CARGO_NET_OFFLINE"] = "true"
    env["CARGO_TERM_COLOR"] = "never"
    for key in (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "all_proxy",
    ):
        env[key] = "http://127.0.0.1:9"
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    return env


@pytest.fixture(scope="module")
def receipt() -> dict[str, Any]:
    assert RECEIPT_PATH.is_file(), f"missing external conformance receipt: {RECEIPT_PATH}"
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    assert SCHEDULER_PATH.is_file(), f"missing scheduler: {SCHEDULER_PATH}"
    payload = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def vectors() -> dict[str, Any]:
    assert VECTORS_PATH.is_file(), VECTORS_PATH
    payload = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def contracts() -> dict[str, Any]:
    assert CONTRACTS_PATH.is_file(), CONTRACTS_PATH
    payload = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def ccc_gate() -> dict[str, Any]:
    assert CCC_GATE_PATH.is_file(), CCC_GATE_PATH
    payload = json.loads(CCC_GATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_receipt_schema_task_bundle_goal_and_evidence_subset(
    receipt: dict[str, Any],
) -> None:
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["schema_version"] == 1
    assert receipt["task_id"] == TASK_ID
    assert receipt["goal_id"] == GOAL_ID
    assert receipt["bundle"] == BUNDLE
    assert receipt["release"] == RELEASE
    assert receipt["vocabulary_schema"] == VOCAB_SCHEMA
    assert receipt["status"] in {"sealed", "blocked"}
    assert receipt["behavior_change"] is False
    assert receipt["title"]
    assert receipt["generated_at"]
    assert set(receipt["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET


def test_policy_forbids_generated_validator_network_and_omit_failures(
    receipt: dict[str, Any],
) -> None:
    policy = receipt["policy"]
    assert policy["producer_artifacts_immutable"] is True
    assert policy["discovery_is_not_completion"] is True
    assert policy["provider_authority"] == "none"
    assert policy["fail_closed"] is True
    assert policy["no_network"] is True
    assert policy["no_unqualified_production_claim"] is True
    assert policy["no_network_interop_claim_without_observation"] is True
    assert policy["generated_implementation_not_independent_validator"] is True
    assert policy["omit_failing_vectors_forbidden"] is True
    assert policy["external_implementation_source_immutable"] is True
    assert REQUIRED_PROHIBITED_EFFECTS <= set(policy["prohibited_effects"])


def test_content_sha256_binds_canonical_receipt(receipt: dict[str, Any]) -> None:
    assert DIGEST_RE.match(receipt["content_sha256"])
    binding = receipt["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"]
    assert binding["covers"] == "gate_record_excluding_content_sha256"
    assert _canonical_content_sha256(receipt) == receipt["content_sha256"]


def test_source_binding_commits_forest_and_depends_on(
    receipt: dict[str, Any], scheduler: dict[str, Any]
) -> None:
    binding = receipt["source_binding"]
    assert binding["controller_commit"] == _git_rev_parse("HEAD")
    assert binding["controller_tree"] == _git_rev_parse("HEAD^{tree}")
    assert binding["scheduler_config"] == (
        "config/formal_assurance_control_plane_scheduler.json"
    )
    assert FULL_SHA_RE.match(binding["controller_commit"])
    assert FULL_SHA_RE.match(binding["controller_tree"])

    assert binding["vectors_sha256"] == _sha256_file(VECTORS_PATH)
    assert binding["encoding_spec_sha256"] == _sha256_file(ENCODING_SPEC_PATH)
    assert (REPO_ROOT / binding["vectors_path"]).is_file()
    assert (REPO_ROOT / binding["encoding_spec_path"]).is_file()

    forest = {entry["path"]: entry for entry in binding["planning_forest"]}
    assert set(forest) == set(PLANNING_FOREST_PATHS)
    sb = scheduler["source_binding"]
    for path, entry in forest.items():
        assert FULL_SHA_RE.match(entry["gitlink_commit"])
        assert entry["gitlink_commit"] == _gitlink_commit(path)
        field = entry["planning_revision_field"]
        assert entry["scheduler_planning_revision"] == sb[field]
        assert entry["matches_scheduler_planning_revision"] is (
            entry["gitlink_commit"] == sb[field]
        )

    assert set(binding["depends_on"]) == REQUIRED_DEPENDS_ON
    assert set(binding["shared_producer_inputs"]) == REQUIRED_SHARED_INPUTS


def test_producer_input_digests_match_filesystem(receipt: dict[str, Any]) -> None:
    producers = {row["task_id"]: row for row in receipt["source_binding"]["producer_inputs"]}
    assert REQUIRED_DEPENDS_ON | REQUIRED_SHARED_INPUTS <= set(producers)
    assert "FACP-036" in producers  # negative independence witness
    for row in receipt["source_binding"]["producer_inputs"]:
        assert row["role"]
        assert isinstance(row["paths"], list) and row["paths"]
        for item in row["paths"]:
            path = REPO_ROOT / item["path"]
            assert path.is_file(), item["path"]
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _sha256_file(path), item["path"]


def test_toolchain_binds_tcb_and_live_cargo_identity(receipt: dict[str, Any]) -> None:
    toolchains = receipt["toolchain"]
    assert toolchains["schema"] == "facp/ccc-toolchain-binding@1"
    assert toolchains["languages"] == ["rust"]
    assert toolchains["tcb_sha256"] == _sha256_file(TCB_PATH)
    assert toolchains["tcb_path"] == (
        "implementation_plan/formal_assurance_control_plane/baseline/"
        "trusted_computing_base.json"
    )

    tcb = json.loads(TCB_PATH.read_text(encoding="utf-8"))
    components = {row["name"]: row for row in tcb["components"]}

    rust = toolchains["rust"]
    assert rust["version"] == components["rust_cargo"]["version"]
    assert rust["cargo_raw"] == _run_out(["cargo", "--version"])
    assert rust["tcb_raw"] == components["rust_cargo"]["raw"]
    assert rust["role"] == "independent_implementation"
    assert rust["implementation_task_id"] == "FACP-035"
    assert rust["implementation_bundle"] == "facp/contracts/rust-codec"
    cargo_vv = _run_out(["cargo", "-Vv"])
    commit = None
    for line in cargo_vv.splitlines():
        if line.startswith("commit-hash:"):
            commit = line.split(":", 1)[1].strip()
            break
    assert rust["cargo_commit"] == commit
    assert FULL_SHA_RE.match(rust["cargo_commit"]) or DIGEST_RE.match(
        rust["cargo_commit"]
    )


def test_independence_relationship_excludes_generated_manifest_and_compiler(
    receipt: dict[str, Any],
) -> None:
    impl = receipt["independent_implementation"]
    assert impl["language"] == "rust"
    assert impl["task_id"] == "FACP-035"
    assert impl["bundle"] == "facp/contracts/rust-codec"
    assert impl["maintenance"] == "hand_authored_not_generator_owned"
    assert impl["codec_sha256"] == _sha256_file(CODEC_RS)
    assert impl["test_sha256"] == _sha256_file(RUST_TEST_RS)
    assert impl["cargo_test_name"] == "assurance_translation_validation_test"
    assert (REPO_ROOT / impl["codec_path"]).resolve() == CODEC_RS.resolve()
    assert (REPO_ROOT / impl["test_path"]).resolve() == RUST_TEST_RS.resolve()

    relation = impl["independence_relationship"]
    assert relation["schema"] == "facp/independence-relationship@1"
    assert relation["not_generated_binding"] is True
    assert relation["absent_from_generated_manifest_owned_paths"] is True
    assert relation["compiler_identity_bound_separately"] is True
    assert relation["compiler_task_id"] == "FACP-034"
    assert relation["compiler_bundle"] == "facp/contracts/compiler"
    assert relation["does_not_trust_generator_without_validation"] is True
    assert relation["does_not_import_assurance_idl_compiler"] is True
    assert relation["distinct_from_python_reference_codec"] is True
    assert relation["distinct_from_facp036_generated_projections"] is True
    assert relation["content_bound"] is True
    assert "FACP-035" in relation["reading"]
    assert "generated" in relation["reading"].lower()
    assert relation["generated_manifest_sha256"] == _sha256_file(GENERATED_MANIFEST_PATH)

    manifest = json.loads(GENERATED_MANIFEST_PATH.read_text(encoding="utf-8"))
    owned = set(manifest.get("owned_paths") or [])
    assert impl["codec_path"] not in owned
    assert not any(path.startswith("Mcp-Plus-Plus/tests-rs/src/assurance_codec") for path in owned)
    assert not any(
        "assurance_idl/generated" in path and path.endswith("assurance_codec.rs")
        for path in owned
    )

    codec = CODEC_RS.read_text(encoding="utf-8")
    assert 'COMPILER_TASK_ID: &str = "FACP-034"' in codec
    assert 'TASK_ID: &str = "FACP-035"' in codec
    assert "compiler_identity" in codec and "validator_identity" in codec
    assert "assurance_idl" not in codec
    assert "compiler.py" not in codec
    assert "std::net" not in codec
    assert "std::process" not in codec

    test_src = RUST_TEST_RS.read_text(encoding="utf-8")
    assert "does_not_trust_generator_without_validation" in test_src
    assert "independent_translation_validation_confirms_all_vectors" in test_src


def test_hermetic_cargo_runs_full_public_vector_set(receipt: dict[str, Any]) -> None:
    impl = receipt["independent_implementation"]
    execution = receipt["vector_execution"]
    cargo = shutil.which("cargo")
    assert cargo, "cargo required for independent implementation evidence"

    if receipt["status"] == "sealed":
        assert impl["pass"] is True
        assert execution["pass"] is True
    else:
        assert receipt["status"] == "blocked"
        assert isinstance(receipt["failures"], list) and receipt["failures"]

    proc = subprocess.run(
        [
            cargo,
            "test",
            "--offline",
            "--test",
            impl["cargo_test_name"],
            "--",
            "--nocapture",
        ],
        cwd=str(RUST_DIR),
        env=_hermetic_cargo_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")

    observation = execution["cargo_observation"]
    assert observation["command"] == [
        "cargo",
        "test",
        "--offline",
        "--test",
        "assurance_translation_validation_test",
        "--",
        "--nocapture",
    ]

    if receipt["status"] == "sealed":
        assert proc.returncode == 0, output
        assert observation["returncode"] == 0
        for marker in REQUIRED_CARGO_MARKERS:
            assert marker in output, marker
            assert marker in observation["required_markers_observed"]
    else:
        # Blocked receipts must still expose exact counterexamples; live cargo
        # may fail, but failures must not be omitted.
        assert receipt["failures"], "blocked receipt must list exact counterexamples"
        for failure in receipt["failures"]:
            assert failure.get("id"), failure
            assert "expected" in failure or "expected_error" in failure
            assert "observed" in failure or "error" in failure


def test_sealed_positive_cids_and_counts_match_vectors_file(
    receipt: dict[str, Any], vectors: dict[str, Any]
) -> None:
    execution = receipt["vector_execution"]
    assert execution["vectors_sha256"] == _sha256_file(VECTORS_PATH)
    assert execution["vectors_schema"] == "facp/assurance-canonical-encoding-vectors@1"
    assert execution["profile"] == VOCAB_SCHEMA
    assert execution["positive_vector_count"] == len(vectors["positive"])
    assert execution["negative_vector_count"] == len(vectors["negative"])
    assert execution["mutation_vector_count"] == len(vectors["mutations"])

    sealed = {row["id"]: row for row in execution["positive_cases"]}
    assert set(sealed) == {case["id"] for case in vectors["positive"]}
    for case in vectors["positive"]:
        row = sealed[case["id"]]
        assert row["cid"] == case["cid"]
        assert row["cid_family"] == case["cid_family"]
        if receipt["status"] == "sealed":
            assert row["canonical_identity_match"] is True
            assert execution["canonical_identity_match"] is True


def test_sealed_negative_and_mutation_errors_match_vectors_file(
    receipt: dict[str, Any], vectors: dict[str, Any]
) -> None:
    execution = receipt["vector_execution"]
    sealed_neg = {row["id"]: row for row in execution["negative_cases"]}
    assert set(sealed_neg) == {case["id"] for case in vectors["negative"]}
    for case in vectors["negative"]:
        row = sealed_neg[case["id"]]
        assert row["expected_error"] == case["expected_error"]
        if receipt["status"] == "sealed":
            assert row["rejected"] is True
            assert row["error_match"] is True

    sealed_mut = {row["id"]: row for row in execution["mutations"]}
    assert set(sealed_mut) == {case["id"] for case in vectors["mutations"]}
    for case in vectors["mutations"]:
        row = sealed_mut[case["id"]]
        assert row["expected_error"] == case["expected_error"]
        if receipt["status"] == "sealed":
            assert row["rejected"] is True
            assert row["error_match"] is True

    assert execution["stable_error_codes"] == list(vectors["error_codes"])
    assert execution["stable_error_codes_bound"] is True
    if receipt["status"] == "sealed":
        assert execution["error_codes_match"] is True


def test_failures_empty_when_sealed_or_exact_counterexamples_when_blocked(
    receipt: dict[str, Any], vectors: dict[str, Any]
) -> None:
    vector_ids = (
        {case["id"] for case in vectors["positive"]}
        | {case["id"] for case in vectors["negative"]}
        | {case["id"] for case in vectors["mutations"]}
    )
    if receipt["status"] == "sealed":
        assert receipt["failures"] == []
        assert receipt["acceptance"][
            "independent_implementation_passes_full_required_vector_set"
        ] is True
        assert receipt["acceptance"]["canonical_identity_and_errors_match"] is True
    else:
        assert receipt["status"] == "blocked"
        assert receipt["failures"], "blocked release must list exact counterexamples"
        assert receipt["acceptance"][
            "independent_implementation_passes_full_required_vector_set"
        ] is False
        for failure in receipt["failures"]:
            assert failure["id"] in vector_ids
            # Fail-closed: never omit the identity of a failing vector.
            assert failure.get("expected") is not None or failure.get("expected_error")


def test_composition_contracts_bind_facp_048(
    receipt: dict[str, Any], contracts: dict[str, Any]
) -> None:
    section = receipt["composition_contracts"]
    assert section["task_id"] == "FACP-048"
    assert section["schema"] == "facp/repository-contracts@1"
    assert section["bundle"] == "facp/composition/contracts"
    assert section["sha256"] == _sha256_file(CONTRACTS_PATH)
    assert (REPO_ROOT / section["path"]).resolve() == CONTRACTS_PATH.resolve()
    assert section["fail_closed"] is True
    assert section["discovery_via_repository_import_forbidden"] is True
    assert section["does_not_discharge_live_effect_observation"] is True

    assert contracts["schema"] == "facp/repository-contracts@1"
    assert contracts["fail_closed"] is True
    assert contracts["discovery_via_repository_import_forbidden"] is True

    contract_text = json.dumps(contracts, sort_keys=True)
    assert set(section["relevant_guarantees"]) == REQUIRED_COMPOSITION_GUARANTEES
    assert set(section["relevant_assumptions"]) == REQUIRED_COMPOSITION_ASSUMPTIONS
    assert set(section["relevant_boundaries"]) == REQUIRED_COMPOSITION_BOUNDARIES
    for identifier in (
        REQUIRED_COMPOSITION_GUARANTEES
        | REQUIRED_COMPOSITION_ASSUMPTIONS
        | REQUIRED_COMPOSITION_BOUNDARIES
    ):
        assert identifier in contract_text, identifier
    assert "network" not in section["reading"].lower() or "does not" in section["reading"].lower()


def test_translation_safety_binds_facp_049_module_markers(receipt: dict[str, Any]) -> None:
    section = receipt["translation_safety"]
    assert section["task_id"] == "FACP-049"
    assert section["bundle"] == "facp/translation/validation"
    assert section["module_sha256"] == _sha256_file(TRANSLATION_MODULE_PATH)
    assert (REPO_ROOT / section["module_path"]).resolve() == TRANSLATION_MODULE_PATH.resolve()
    assert set(section["evidence_schemas"]) >= {
        "facp/translation-receipt@1",
        "facp/deontic-refinement@1",
        "facp/rewrite-trust@1",
    }
    assert section["silent_drop_forbidden"] is True
    assert section["permission_broadening_forbidden"] is True
    assert section["heuristic_rewrite_not_admitted_to_proof_extraction"] is True
    assert section["claim_equivalence_without_criteria_forbidden"] is True
    assert section["precondition_pass"] is True

    source = TRANSLATION_MODULE_PATH.read_text(encoding="utf-8")
    assert 'TASK_ID: Final[str] = "FACP-049"' in source or 'TASK_ID' in source and "FACP-049" in source
    assert "SILENT_DROP_FORBIDDEN" in source
    assert "facp/translation-receipt@1" in source
    assert "facp/deontic-refinement@1" in source
    assert "facp/rewrite-trust@1" in source
    assert "ADMIT_HEURISTIC_INTO_PROOF_EXTRACTION" in source
    assert "CLAIM_EQUIVALENCE_WITHOUT_CRITERIA" in source

    # Import-time constants (hermetic; no network).
    datasets_root = str(REPO_ROOT / "external" / "ipfs_datasets")
    if datasets_root not in sys.path:
        sys.path.insert(0, datasets_root)
    from ipfs_datasets_py.logic.translation_validation import formal_assurance as tv

    assert tv.TASK_ID == "FACP-049"
    assert tv.SILENT_DROP_FORBIDDEN is True
    assert tv.ADMIT_HEURISTIC_INTO_PROOF_EXTRACTION is False
    assert tv.CLAIM_EQUIVALENCE_WITHOUT_CRITERIA is False


def test_canonical_contracts_gate_facp_037_still_sealed(
    receipt: dict[str, Any], ccc_gate: dict[str, Any]
) -> None:
    section = receipt["canonical_contract_gate"]
    assert section["task_id"] == "FACP-037"
    assert section["schema"] == "facp/contract-conformance@1"
    assert section["sha256"] == _sha256_file(CCC_GATE_PATH)
    assert section["gate_content_sha256"] == ccc_gate["content_sha256"]
    assert section["status_required"] == "sealed"
    assert section["status_observed"] == ccc_gate["status"]
    assert ccc_gate["status"] == "sealed"
    assert ccc_gate["independent_validator"]["pass"] is True
    assert section["independent_validator_section_pass"] is True
    assert section["precondition_pass"] is True
    assert ccc_gate["independent_validator"]["codec_sha256"] == _sha256_file(CODEC_RS)


def test_acceptance_flags_and_no_unqualified_production_claim_fields(
    receipt: dict[str, Any],
) -> None:
    acceptance = receipt["acceptance"]
    assert acceptance["independence_relationship_documented_and_content_bound"] is True
    assert acceptance["composition_contracts_bound"] is True
    assert acceptance["translation_safety_precondition_bound"] is True
    assert acceptance["canonical_contract_gate_precondition_bound"] is True
    assert acceptance["release_blocked_with_counterexamples_if_fail"] is True
    assert acceptance["network_interoperability_not_claimed"] is True

    if receipt["status"] == "sealed":
        assert acceptance[
            "independent_implementation_passes_full_required_vector_set"
        ] is True
        assert acceptance["canonical_identity_and_errors_match"] is True

    guarded_roots = {
        "",
        "acceptance",
        "policy",
        "independent_implementation",
        "vector_execution",
        "composition_contracts",
        "translation_safety",
        "canonical_contract_gate",
        "toolchain",
    }

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_l = str(key).lower()
                if key_l in FORBIDDEN_RECEIPT_CLAIM_KEYS and path in guarded_roots:
                    pytest.fail(
                        f"unqualified production claim field {key!r} at {path or '<root>'}"
                    )
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(receipt)


def test_does_not_claim_network_interoperability(receipt: dict[str, Any]) -> None:
    assert receipt["policy"]["no_network"] is True
    assert receipt["policy"]["no_network_interop_claim_without_observation"] is True
    assert receipt["acceptance"]["network_interoperability_not_claimed"] is True
    assert receipt["composition_contracts"]["does_not_discharge_live_effect_observation"] is True
    # Sanitized receipt must not assert observed network interop.
    blob = json.dumps(receipt).lower()
    for forbidden in (
        '"network_interoperability": true',
        '"interop_observed": true',
        '"live_network_pass": true',
    ):
        assert forbidden not in blob
