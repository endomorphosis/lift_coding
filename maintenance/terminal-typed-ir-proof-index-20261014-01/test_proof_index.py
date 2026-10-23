"""Current-source and byte-custody gates for real authored model certificates."""
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess

import pytest

import native_structural_ir as native
import proof_index as index
from align_projection import compile_alignment_proofs, project_alignment
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import ProofHostResources
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import GlobalResourceScheduler, ResourceSchedulerConfig

BODY = b"def align(x: int, g: int) -> int:\n    return ((x + g - 1) // g) * g\n"


@pytest.fixture(scope="module")
def actual_model_proof(tmp_path_factory):
    folder = tmp_path_factory.mktemp("authored-alignment-proof")
    projection = project_alignment(source_bytes=BODY, source_path="unit.py", source_sha256=hashlib.sha256(BODY).hexdigest())
    proof = compile_alignment_proofs(projection=projection, output=folder / "proof",
        lean_executable=Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean"))
    assert proof["qualified"]
    return projection, proof


@pytest.fixture
def prepared(tmp_path, monkeypatch, actual_model_proof):
    repository = tmp_path / "source"
    repository.mkdir()
    (repository / "unit.py").write_bytes(BODY)
    commands = [["git", "init", "-q"], ["git", "add", "--", "unit.py"],
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-c", "user.name=Authored proof index", "-c", "user.email=proof-index@localhost", "commit", "-qm", "Authored unit source"]]
    for command in commands:
        subprocess.run(command, cwd=repository, check=True, capture_output=True)
    # Synthetic admission is restricted to this authored unit fixture.
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path / "authored-resource-state.json",
        proof_resource_sampler=lambda: ProofHostResources(8, 8192, 8192), auto_renew_leases=False))
    monkeypatch.setattr(native, "_scheduler", lambda: scheduler)
    structural = native.prepare_structural_ir(repository=repository, output=tmp_path / "structural",
        repository_id="authored-proof-index:" + tmp_path.name,
        expected_sources={"unit.py": hashlib.sha256(BODY).hexdigest()})
    projection, proof = actual_model_proof
    output = tmp_path / "index"
    created = index.create_proof_index(output=output, structural_report=structural, projection=projection, proof_report=proof)
    return {"output": output, "repository": repository, "structural_output": tmp_path / "structural",
        "structural_report": structural, "projection": projection, "proof_report": proof}, created


def test_real_model_certificate_reopens_under_complete_current_native_head(prepared):
    request, created = prepared
    found = index.lookup_current_proof(**request)
    assert found["proof_id"] == created["proof_id"]
    assert found["live_source_and_complete_head_rechecked"]
    assert found["retained_checker_artifacts_rechecked"]
    assert all(found["mathematical_fragment_claims"].values())
    assert all(found[field] is False for field in index.AUTHORITY)
    assert found["requires_fresh_native_checks_for_admission"]


def test_changed_source_cannot_reuse_historical_alignment_certificate(prepared):
    request, _ = prepared
    (request["repository"] / "unit.py").write_bytes(BODY.replace(b"g - 1", b"g - 2"))
    with pytest.raises(ValueError):
        index.lookup_current_proof(**request)


@pytest.mark.parametrize("mutation", ["certificate_payload", "dependency", "head_column", "extra_record"])
def test_sql_tampering_cannot_pass_byte_and_reverse_dependency_joins(prepared, mutation):
    request, _ = prepared
    with index.owner(request["output"]) as connection:
        if mutation == "certificate_payload":
            connection.execute("UPDATE conditional_proofs SET payload_json='{}'")
        elif mutation == "dependency":
            connection.execute("DELETE FROM proof_dependencies WHERE kind='source'")
        elif mutation == "head_column":
            connection.execute("UPDATE conditional_proofs SET head_id='substituted'")
        else:
            connection.execute("INSERT INTO conditional_proofs SELECT 'extra-record',head_id,source_cid,source_sha256,"
                "projection_id,certificate_sha256,payload_sha256,payload_json FROM conditional_proofs")
    with pytest.raises(ValueError):
        index.lookup_current_proof(**request)


@pytest.mark.parametrize("mutation", ["source_hash", "projection_id", "qualified", "process_fault", "authority",
    "unrelated_theory", "changed_command", "changed_limits", "incomplete_model_claims"])
def test_unqualified_or_unbound_public_records_cannot_enter_closed_profile(prepared, mutation):
    request, _ = prepared
    projection, proof = deepcopy(request["projection"]), deepcopy(request["proof_report"])
    if mutation == "source_hash":
        projection["source"]["sha256"] = "0" * 64
    elif mutation == "projection_id":
        proof["projection_id"] = "0" * 64
    elif mutation == "qualified":
        proof["qualified"] = False
    elif mutation == "process_fault":
        proof["checks"][0]["output_truncated"] = True
    elif mutation == "authority":
        proof["proof_authority"] = True
    elif mutation == "unrelated_theory":
        proof["checks"][0]["artifact"]["sha256"] = "0" * 64
    elif mutation == "changed_command":
        proof["checks"][0]["command"][2] = "2"
    elif mutation == "changed_limits":
        proof["checks"][0]["limits"]["max_output_bytes"] *= 2
    else:
        proof["mathematical_fragment_claims"]["kernel_checked_g64_divisibility"] = False
    with pytest.raises(ValueError):
        index.bindings(request["structural_report"], projection, proof)
