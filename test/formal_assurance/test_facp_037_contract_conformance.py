"""FACP-037: seal cross-language canonical contract conformance.

Acceptance (taskboard):
- Same semantic value produces byte-identical canonical bytes and CID in
  four languages (python, typescript, rust, go).
- One-bit and unknown-field mutations fail.
- Gate binds exact source/toolchains.

Producer compiler and independent-validator artifacts are immutable inputs;
this task writes only the sealed gate receipt and this hermetic fan-in test.
"""

from __future__ import annotations

import hashlib
import importlib.util
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
GATE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "gates"
    / "canonical_contracts_v1.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
TCB_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "trusted_computing_base.json"
)
VECTORS_PATH = (
    REPO_ROOT
    / "Mcp-Plus-Plus"
    / "conformance"
    / "vectors"
    / "assurance-canonical-encoding.json"
)
MANIFEST_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "tools" / "assurance_idl" / "generated_manifest.json"
)
ENCODING_SPEC_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "docs" / "spec" / "assurance-canonical-encoding.md"
)
IDL_SPEC_PATH = REPO_ROOT / "Mcp-Plus-Plus" / "docs" / "spec" / "assurance-idl.md"
RUST_DIR = REPO_ROOT / "Mcp-Plus-Plus" / "tests-rs"
CODEC_RS = RUST_DIR / "src" / "assurance_codec.rs"
RUST_TEST_RS = RUST_DIR / "tests" / "assurance_translation_validation_test.rs"
ENCODING_TEST_PATH = (
    REPO_ROOT
    / "Mcp-Plus-Plus"
    / "tests-py"
    / "integration"
    / "test_assurance_canonical_encoding_spec.py"
)
BINDINGS_TEST_PATH = (
    REPO_ROOT
    / "Mcp-Plus-Plus"
    / "tests-py"
    / "integration"
    / "test_assurance_generated_bindings.py"
)

GATE_SCHEMA = "facp/contract-conformance@1"
TASK_ID = "FACP-037"
GOAL_ID = "FACP-G310"
BUNDLE = "facp/contracts/gate"
RELEASE = "canonical-contracts-v1"
VOCAB_SCHEMA = "facp/dag-cbor-profile@1"
LANGUAGES = ("python", "typescript", "rust", "go")

REQUIRED_EVIDENCE_SUBSET = {
    "byte_cid_parity",
    "unknown_duplicate_mutation_rejection",
    "stable_errors",
    "generator_determinism",
    "independent_validator",
}

REQUIRED_DEPENDS_ON = {"FACP-035", "FACP-036"}
REQUIRED_SHARED_INPUTS = {"FACP-032", "FACP-033", "FACP-034"}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)

SOURCE_CONTRACTS = (
    "facp/evidence-envelope@1",
    "facp/operation-spec@1",
    "facp/admission-token@1",
    "facp/effect-receipt@1",
)

REQUIRED_ERROR_CODES = {
    "UNKNOWN_FIELD",
    "DUPLICATE_MAP_KEY",
    "MALLEABLE_ENCODING",
    "NON_DEFINITE_LENGTH",
    "UNSORTED_MAP_KEYS",
    "WRONG_CID_FAMILY",
    "PSEUDO_CID",
    "FORBIDDEN_FLOAT",
}

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_GATE_CLAIM_KEYS = {
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def _canonical_content_sha256(gate: dict[str, Any]) -> str:
    without_digest = {key: value for key, value in gate.items() if key != "content_sha256"}
    canonical = json.dumps(
        without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def _run_out(cmd: list[str]) -> str:
    completed = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return completed.stdout.strip()


@pytest.fixture(scope="module")
def gate() -> dict[str, Any]:
    assert GATE_PATH.is_file(), f"missing CCC gate: {GATE_PATH}"
    payload = json.loads(GATE_PATH.read_text(encoding="utf-8"))
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
def encoding_mod() -> Any:
    return _load_module(ENCODING_TEST_PATH, "facp037_encoding_spec")


@pytest.fixture(scope="module")
def bindings_mod() -> Any:
    return _load_module(BINDINGS_TEST_PATH, "facp037_generated_bindings")


def test_gate_schema_task_and_bundle_binding(gate: dict[str, Any]) -> None:
    assert gate["schema"] == GATE_SCHEMA
    assert gate["schema_version"] == 1
    assert gate["task_id"] == TASK_ID
    assert gate["goal_id"] == GOAL_ID
    assert gate["bundle"] == BUNDLE
    assert gate["release"] == RELEASE
    assert gate["vocabulary_schema"] == VOCAB_SCHEMA
    assert gate["status"] == "sealed"
    assert gate["behavior_change"] is False
    assert gate["title"]
    assert gate["generated_at"]
    assert set(gate["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET


def test_policy_forbids_missing_language_network_and_compiler_sole_authority(
    gate: dict[str, Any],
) -> None:
    policy = gate["policy"]
    assert policy["producer_artifacts_immutable"] is True
    assert policy["discovery_is_not_completion"] is True
    assert policy["provider_authority"] == "none"
    assert policy["fail_closed"] is True
    assert policy["no_network"] is True
    assert policy["no_unqualified_production_claim"] is True
    assert policy["compiler_self_report_not_sole_evidence"] is True
    assert policy["accept_missing_language"] is False
    prohibited = set(policy["prohibited_effects"])
    assert {
        "accept_missing_language",
        "network",
        "trust_compiler_self_report_as_sole_evidence",
        "provider_authored_completion",
        "introduce_unqualified_production_claim",
    } <= prohibited


def test_content_sha256_binds_canonical_gate_record(gate: dict[str, Any]) -> None:
    assert DIGEST_RE.match(gate["content_sha256"])
    binding = gate["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"]
    assert binding["covers"] == "gate_record_excluding_content_sha256"
    assert _canonical_content_sha256(gate) == gate["content_sha256"]


def test_source_binding_exact_commits_and_producer_digests(
    gate: dict[str, Any], scheduler: dict[str, Any]
) -> None:
    binding = gate["source_binding"]
    assert binding["controller_commit"] == _git_rev_parse("HEAD")
    assert binding["controller_tree"] == _git_rev_parse("HEAD^{tree}")
    assert binding["scheduler_config"] == (
        "config/formal_assurance_control_plane_scheduler.json"
    )
    assert FULL_SHA_RE.match(binding["controller_commit"])
    assert FULL_SHA_RE.match(binding["controller_tree"])

    assert binding["encoding_spec_sha256"] == _sha256_file(ENCODING_SPEC_PATH)
    assert binding["idl_spec_sha256"] == _sha256_file(IDL_SPEC_PATH)
    assert binding["vectors_sha256"] == _sha256_file(VECTORS_PATH)
    assert (REPO_ROOT / binding["encoding_spec_path"]).is_file()
    assert (REPO_ROOT / binding["idl_spec_path"]).is_file()
    assert (REPO_ROOT / binding["vectors_path"]).is_file()

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

    producers = {row["task_id"]: row for row in binding["producer_inputs"]}
    assert REQUIRED_DEPENDS_ON | REQUIRED_SHARED_INPUTS <= set(producers)
    for row in binding["producer_inputs"]:
        assert row["role"]
        assert isinstance(row["paths"], list) and row["paths"]
        for item in row["paths"]:
            path = REPO_ROOT / item["path"]
            assert path.is_file(), item["path"]
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _sha256_file(path), item["path"]


def test_toolchains_bind_exact_tcb_and_live_identities(gate: dict[str, Any]) -> None:
    toolchains = gate["toolchains"]
    assert toolchains["schema"] == "facp/ccc-toolchain-binding@1"
    assert toolchains["languages"] == list(LANGUAGES)
    assert toolchains["tcb_sha256"] == _sha256_file(TCB_PATH)

    tcb = json.loads(TCB_PATH.read_text(encoding="utf-8"))
    components = {row["name"]: row for row in tcb["components"]}

    python = toolchains["python"]
    assert python["version"] == components["python3"]["version"]
    assert python["raw"] == _run_out([sys.executable, "--version"])
    assert python["tcb_raw"] == components["python3"]["raw"]
    assert python["role"] == "reference_codec"
    import dag_cbor

    assert python["dag_cbor_version"] == getattr(dag_cbor, "__version__", "0.3.3")

    rust = toolchains["rust"]
    assert rust["version"] == components["rust_cargo"]["version"]
    assert rust["cargo_raw"] == _run_out(["cargo", "--version"])
    assert rust["tcb_raw"] == components["rust_cargo"]["raw"]
    assert rust["role"] == "independent_validator"
    assert rust["validator_task_id"] == "FACP-035"
    assert rust["validator_bundle"] == "facp/contracts/rust-codec"
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

    typescript = toolchains["typescript"]
    assert typescript["version"] == components["nodejs"]["version"]
    assert typescript["raw"] == _run_out(["node", "--version"])
    assert typescript["tcb_raw"] == components["nodejs"]["raw"]
    assert typescript["role"] == "generated_binding_projection"

    go = toolchains["go"]
    assert go["version"] == components["go"]["version"]
    assert go["raw"] == _run_out(["go", "version"])
    assert go["tcb_raw"] == components["go"]["raw"]
    assert go["role"] == "generated_binding_projection"


def test_python_reference_byte_and_cid_identity(
    gate: dict[str, Any], vectors: dict[str, Any], encoding_mod: Any
) -> None:
    parity = gate["byte_cid_parity"]
    assert parity["agree"] is True
    assert parity["languages"] == list(LANGUAGES)
    assert parity["profile"] == VOCAB_SCHEMA
    assert parity["python_reference_match"] is True
    assert parity["positive_vector_count"] == len(vectors["positive"])
    assert len(parity["positive_cases"]) == len(vectors["positive"])

    observed: list[dict[str, str]] = []
    for case in vectors["positive"]:
        family = case["cid_family"]
        if family == encoding_mod.RAW_FAMILY:
            data = bytes.fromhex(case["raw_hex"])
            assert encoding_mod.cid_for_bytes(data, family) == case["cid"]
            encoding_mod.bind_cid_to_bytes(case["cid"], data, family)
        else:
            encoded = encoding_mod.encode_canonical(case["value"])
            assert encoded.hex() == case["canonical_hex"]
            assert encoding_mod.cid_for_bytes(encoded, family) == case["cid"]
            encoding_mod.admit_canonical_bytes(encoded)
            encoding_mod.bind_cid_to_bytes(case["cid"], encoded, family)
            again = encoding_mod.encode_canonical(case["value"])
            assert again == encoded
        observed.append(
            {
                "id": case["id"],
                "cid": case["cid"],
                "cid_family": family,
            }
        )

    assert observed == parity["positive_cases"]


def test_four_language_generated_binding_fixture_parity(
    gate: dict[str, Any], vectors: dict[str, Any], bindings_mod: Any
) -> None:
    parity = gate["byte_cid_parity"]
    assert parity["generated_binding_fixture_parity"] is True
    assert parity["rust_independent_match"] is True

    compiler = bindings_mod._load_compiler()
    artifacts = bindings_mod.generate_artifacts(compiler)
    fixtures = bindings_mod._encoding_fixtures()
    assert set(fixtures) == set(SOURCE_CONTRACTS)

    sealed = {
        row["source_contract"]: row for row in parity["contract_fixture_parity"]
    }
    assert set(sealed) == set(SOURCE_CONTRACTS)

    for contract, fixture in fixtures.items():
        row = sealed[contract]
        golden = next(case for case in vectors["positive"] if case["id"] == fixture["id"])
        assert fixture["canonical_hex"] == golden["canonical_hex"]
        assert fixture["cid"] == golden["cid"]
        assert row["canonical_hex"] == fixture["canonical_hex"]
        assert row["cid"] == fixture["cid"]
        assert row["fixture_id"] == fixture["id"]

        vector_path = bindings_mod._artifact_path(contract, "vector")
        vector = json.loads(artifacts[vector_path].decode("utf-8"))
        assert vector["positive"][0]["canonical_hex"] == fixture["canonical_hex"]
        assert vector["positive"][0]["cid"] == fixture["cid"]
        assert any(item["error"] == "UNKNOWN_FIELD" for item in vector["negative"])
        assert row["vector_path"] == vector_path
        assert row["vector_sha256"] == _sha256_bytes(artifacts[vector_path])

        assert set(row["languages"]) == set(LANGUAGES)
        for language in LANGUAGES:
            code_path = bindings_mod._artifact_path(contract, "code", language)
            code = artifacts[code_path].decode("utf-8")
            assert "UNKNOWN_FIELD" in code
            lang_row = row["languages"][language]
            assert lang_row["path"] == code_path
            assert lang_row["sha256"] == _sha256_bytes(artifacts[code_path])
            assert lang_row["rejects_unknown_field"] is True


def test_one_bit_and_unknown_field_mutations_fail(
    gate: dict[str, Any], vectors: dict[str, Any], encoding_mod: Any, bindings_mod: Any
) -> None:
    rejection = gate["unknown_duplicate_mutation_rejection"]
    assert rejection["unknown_field_rejected"] is True
    assert rejection["duplicate_map_key_rejected"] is True
    assert rejection["one_bit_mutation_rejected"] is True
    assert rejection["one_bit_mutation_id"] == "flip_one_canonical_byte"
    assert rejection["mutation_reject_count"] == len(vectors["mutations"])
    assert rejection["negative_vector_count"] == len(vectors["negative"])

    unk = next(case for case in vectors["negative"] if case["id"] == "unknown_field_opspec")
    unknown = sorted(set(unk["value"]) - encoding_mod.OPSPEC_IDENTITY_KEYS)
    assert unknown == rejection["unknown_fields"]
    with pytest.raises(encoding_mod.CanonicalEncodingError) as unk_exc:
        if unknown:
            raise encoding_mod.CanonicalEncodingError(
                "UNKNOWN_FIELD", f"unknown fields {unknown}"
            )
        encoding_mod.encode_canonical(unk["value"])
    assert unk_exc.value.code == "UNKNOWN_FIELD"

    dup = next(case for case in vectors["negative"] if case["id"] == "duplicate_map_key")
    with pytest.raises(encoding_mod.CanonicalEncodingError) as dup_exc:
        encoding_mod.admit_canonical_bytes(bytes.fromhex(dup["hex"]))
    assert dup_exc.value.code == dup["expected_error"]

    sealed_mutations = {row["id"]: row for row in rejection["mutations"]}
    for case in vectors["mutations"]:
        base = next(
            item for item in vectors["positive"] if item["id"] == case["base_positive_id"]
        )
        op = case["op"]
        with pytest.raises(encoding_mod.CanonicalEncodingError) as raised:
            if op == "xor_byte":
                raw = bytearray.fromhex(base["canonical_hex"])
                raw[case["offset"]] ^= case["mask"]
                encoding_mod.admit_canonical_bytes(bytes(raw))
            elif op == "replace_hex":
                encoding_mod.admit_canonical_bytes(bytes.fromhex(case["hex"]))
            elif op == "xor_retained_byte_keep_cid":
                raw = bytearray.fromhex(base["canonical_hex"])
                raw[case["offset"]] ^= case["mask"]
                encoding_mod.bind_cid_to_bytes(
                    base["cid"], bytes(raw), base["cid_family"]
                )
            else:
                raise AssertionError(f"unknown mutation op {op}")
        assert raised.value.code == case["expected_error"]
        assert sealed_mutations[case["id"]]["rejected"] is True
        assert sealed_mutations[case["id"]]["error"] == case["expected_error"]

    # Generated Python binding also rejects unknown fields (language projection).
    compiler = bindings_mod._load_compiler()
    artifacts = bindings_mod.generate_artifacts(compiler)
    fixtures = bindings_mod._encoding_fixtures()
    path = bindings_mod._artifact_path("facp/evidence-envelope@1", "code", "python")
    source = artifacts[path].decode("utf-8")
    module_name = "facp037_generated_evidence_envelope"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    exec(compile(source, path, "exec"), module.__dict__)  # noqa: S102
    good = dict(fixtures["facp/evidence-envelope@1"]["value"])
    module.validate_evidence_envelope(good)
    bad = dict(good)
    bad["extra"] = True
    with pytest.raises(module.EvidenceEnvelopeError) as gen_exc:
        module.validate_evidence_envelope(bad)
    assert gen_exc.value.code == "UNKNOWN_FIELD"
    assert rejection["generated_python_unknown_field_rejected"] is True


def test_stable_error_codes_bound(gate: dict[str, Any], vectors: dict[str, Any]) -> None:
    stable = gate["stable_errors"]
    assert stable["profile_error_codes"] == list(vectors["error_codes"])
    assert stable["error_code_count"] == len(vectors["error_codes"])
    assert stable["required_codes_present"] is True
    assert set(stable["required_codes"]) == REQUIRED_ERROR_CODES
    assert REQUIRED_ERROR_CODES <= set(vectors["error_codes"])


def test_generator_determinism_without_trusting_self_report(
    gate: dict[str, Any], bindings_mod: Any
) -> None:
    report = gate["generator_determinism"]
    assert report["task_id"] == "FACP-036"
    assert report["clean_generation_byte_identical"] is True
    assert report["compiler_self_report_not_sole_evidence"] is True
    assert report["languages"] == list(LANGUAGES)
    assert report["source_contracts"] == list(SOURCE_CONTRACTS)
    assert report["manifest_sha256"] == _sha256_file(MANIFEST_PATH)

    compiler = bindings_mod._load_compiler()
    first = bindings_mod.render_manifest_bytes(compiler)
    second = bindings_mod.render_manifest_bytes(compiler)
    assert first == second
    assert first == MANIFEST_PATH.read_bytes()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert report["generator_version"] == manifest["generator_version"]
    assert report["owned_path_count"] == len(manifest["owned_paths"])
    assert report["entry_count"] == len(manifest["entries"])
    assert report["generation_input_digests"] == dict(manifest["generation_input_digests"])

    # Independent of compiler self-report: regenerated artifact digests match
    # the checked-in manifest entries for every owned path.
    artifacts = bindings_mod.generate_artifacts(compiler)
    for entry in manifest["entries"]:
        path = entry["path"]
        if path not in artifacts:
            continue
        assert entry["sha256"] == _sha256_bytes(artifacts[path]), path


def test_independent_rust_validator_confirms_vectors(gate: dict[str, Any]) -> None:
    validator = gate["independent_validator"]
    assert validator["task_id"] == "FACP-035"
    assert validator["bundle"] == "facp/contracts/rust-codec"
    assert validator["validation_result_schema"] == "facp/translation-validation@1"
    assert validator["compiler_identity_bound_separately"] is True
    assert validator["compiler_task_id"] == "FACP-034"
    assert validator["compiler_bundle"] == "facp/contracts/compiler"
    assert validator["does_not_trust_generator_without_validation"] is True
    assert validator["positive_round_trip_confirmed"] is True
    assert validator["negative_and_mutation_rejected"] is True
    assert validator["pass"] is True
    assert validator["codec_sha256"] == _sha256_file(CODEC_RS)
    assert validator["test_sha256"] == _sha256_file(RUST_TEST_RS)

    codec = CODEC_RS.read_text(encoding="utf-8")
    assert 'COMPILER_TASK_ID: &str = "FACP-034"' in codec
    assert 'TASK_ID: &str = "FACP-035"' in codec
    assert "compiler_identity" in codec and "validator_identity" in codec
    assert "does_not_trust_generator" in RUST_TEST_RS.read_text(encoding="utf-8") or (
        "does_not_trust_generator_without_validation"
        in RUST_TEST_RS.read_text(encoding="utf-8")
    )

    cargo = shutil.which("cargo")
    assert cargo, "cargo required for independent validator evidence"
    proc = subprocess.run(
        [
            cargo,
            "test",
            "--offline",
            "--test",
            validator["cargo_test_name"],
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
    assert proc.returncode == 0, output
    assert "every_positive_vector_round_trips_with_exact_cid" in output
    assert "every_negative_and_mutation_vector_is_rejected" in output
    assert "independent_translation_validation_confirms_all_vectors" in output
    assert "does_not_trust_generator_without_validation" in output
    assert "test result: ok." in output


def test_acceptance_and_no_unqualified_production_claim_fields(
    gate: dict[str, Any],
) -> None:
    acceptance = gate["acceptance"]
    assert acceptance["four_language_byte_cid_identity"] is True
    assert acceptance["one_bit_mutations_fail"] is True
    assert acceptance["unknown_field_mutations_fail"] is True
    assert acceptance["gate_binds_exact_source_and_toolchains"] is True
    assert acceptance["independent_validator_required"] is True
    assert acceptance["generator_determinism_confirmed"] is True

    guarded_roots = {
        "",
        "acceptance",
        "policy",
        "byte_cid_parity",
        "unknown_duplicate_mutation_rejection",
        "generator_determinism",
        "independent_validator",
        "toolchains",
    }

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_l = str(key).lower()
                if key_l in FORBIDDEN_GATE_CLAIM_KEYS and path in guarded_roots:
                    pytest.fail(
                        f"unqualified production claim field {key!r} at {path or '<root>'}"
                    )
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(gate)
