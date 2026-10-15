"""One fresh public, local cache qualification; no target source execution."""
from copy import deepcopy
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
C = R.parent / "terminal-token-reduction-20261007-01/checkout"


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode()


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("xb") as stream:
        stream.write(wire(value))
    path.chmod(0o600)


def main():
    from benchmarks.agent_supervisor.container_coding import terminal_revision_proof_cache as cache
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_logic_qualification import _compile_lean
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_proof_index import capture_terminal_codebase_proof_environment
    from benchmarks.agent_supervisor.container_coding.terminal_input_token_comparison import (
        _load_tokenizer, _measure, _tokenizer_digest, TOKENIZER_SHA256)
    from ipfs_accelerate_py.agent_supervisor.proof.proof_scope_index import (
        invalidate_proof_scope_inputs, ProofScopeIndex)
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata

    expected = json.loads((R / "runtime-source-pins.json").read_bytes())
    assert [pin(Path(row["path"])) for row in expected["files"]] == expected["files"]
    output = R / "actual-public-revision-01"
    output.mkdir(mode=0o700)
    repository = output / "repository"
    repository.mkdir(mode=0o755)
    sources = {"callee.py": b"def increment(value):\n    return value + 1\n",
        "caller.py": b"from callee import increment\n\ndef twice(value):\n    return increment(increment(value))\n\ndef unsupported(expression):\n    return eval(expression)\n"}
    for name, raw in sources.items():
        with (repository / name).open("xb") as stream:
            stream.write(raw)
        (repository / name).chmod(0o644)
    original = {name: pin(repository / name) for name in sources}
    started = time.monotonic()
    snapshot = cache.capture_revision(root=repository, paths=list(sources), repository_id="public-two-module-revision-01")
    assert snapshot["metadata"]["records"]["unsupported"]
    # Strict syntax recognizer for this authored model, not a Python semantics
    # theorem. No target import, eval, worker or provider invocation occurs.
    callee = ast.parse(sources["callee.py"].decode()).body[0]
    assert isinstance(callee, ast.FunctionDef) and callee.name == "increment"
    assert len(callee.body) == 1 and isinstance(callee.body[0], ast.Return)
    expression = callee.body[0].value
    assert isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Add)
    assert isinstance(expression.left, ast.Name) and expression.left.id == "value"
    assert isinstance(expression.right, ast.Constant) and type(expression.right.value) is int and expression.right.value == 1
    caller = ast.parse(sources["caller.py"].decode()).body[1]
    assert caller.name == "twice" and len(caller.body) == 1
    outer = caller.body[0].value
    assert isinstance(outer, ast.Call) and outer.func.id == "increment" and len(outer.args) == 1
    inner = outer.args[0]
    assert isinstance(inner, ast.Call) and inner.func.id == "increment" and len(inner.args) == 1
    assert isinstance(inner.args[0], ast.Name) and inner.args[0].id == "value"
    lean = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
    environment = capture_terminal_codebase_proof_environment(lean_executable=str(lean))
    write(output / "checker-environment.json", environment)
    model = """import Std
set_option autoImplicit false
namespace RevisionCacheModel
def increment (n : Int) : Int := n + 1
def twice (n : Int) : Int := increment (increment n)
theorem twice_model (n : Int) : twice n = n + 2 := by
  simp [twice, increment, Int.add_assoc]
#print axioms twice_model
end RevisionCacheModel
"""
    lean_output = output / "lean"
    lean_output.mkdir(mode=0o700)
    positive = _compile_lean(executable=lean, filename="RevisionCacheModel.lean", source=model,
        output=lean_output, expected_success=True)
    negative_model = """import Std
set_option autoImplicit false
def increment (n : Int) : Int := n + 1
def twice (n : Int) : Int := increment (increment n)
theorem incorrect_model : twice 0 = 3 := by decide
"""
    negative = _compile_lean(executable=lean, filename="IncorrectModel.lean", source=negative_model,
        output=lean_output, expected_success=False)
    assert positive["matches_expectation"] is True and negative["matches_expectation"] is True
    assert len(positive["compiled_artifacts"]) == 1
    write(output / "lean-checks.json", {"positive": positive, "negative": negative,
        "source_to_lean_semantics_proved": False, "scope": "mathematical_integer_model_only"})
    artifact = Path(positive["compiled_artifacts"][0]["path"])
    dimensions = {"source": {"profile": "authored-public-two-module"},
        "expression": "forall n:Int, twice(n)=n+2",
        "formalization": {"model_source": positive["artifact"], "checker_receipts": pin(output / "lean-checks.json")},
        "slice": {"symbols": ["callee.increment", "caller.twice"], "unsupported_excluded_from_model": ["caller.unsupported"]},
        "obligation": {"theorem": "RevisionCacheModel.twice_model", "scope": "generated_integer_model_only"},
        "assumptions": [{"Python_integer_semantics_and_dispatch_equivalence": "unproved", "domain": "mathematical_Int"}],
        "bounds": {"checker_seconds": 20, "source_scope_files": 2},
        "translation": {"adapter": pin(Path(__file__)), "profile": "exact_authored_syntax_arithmetic@1"},
        "provider": "native-lean-model-check",
        "environment": {"sha256": hashlib.sha256(wire(environment)).hexdigest(), "lean": environment["lean"], "network": "disabled_toolrunner"},
        "policy": {"profile": "advisory-revision-candidate-only", "target_execution": False},
        "schema": {"ir": "terminal-revision-metadata@1", "projection": "authored-int-model@1"},
        "checker": "native-Lean4", "network_policy": {"toolrunner_network": "disabled", "provider_calls": 0},
        "evidence_kind": "kernel_checked_proof", "authority_ceiling": "bounded",
        "kernel": environment["lean"], "theorem_registry": {"model_theorem": "RevisionCacheModel.twice_model", "compiled": pin(artifact)}}
    write(output / "dimensions.json", dimensions)
    report = cache.persist_revision_candidate(output=output / "cache", snapshot=snapshot,
        dimensions=dimensions, artifact=artifact)
    assert report["metadata"]["fresh_process_readback"]["verified"] is True
    write(output / "cache-report.json", report)
    query = dict(output=output / "cache", expected=report, root=repository,
        paths=list(sources), repository_id="public-two-module-revision-01", dimensions=dimensions)
    warm = cache.lookup_revision_candidate(**query)
    assert warm["status"] == "hit" and warm["current_source_rechecked"] is True
    child_code = """import json,sys
from pathlib import Path
from benchmarks.agent_supervisor.container_coding.terminal_revision_proof_cache import lookup_revision_candidate
o=Path(sys.argv[1]); r=lookup_revision_candidate(output=o/'cache',expected=json.loads((o/'cache-report.json').read_bytes()),root=o/'repository',paths=['callee.py','caller.py'],repository_id='public-two-module-revision-01',dimensions=json.loads((o/'dimensions.json').read_bytes()))
print(json.dumps({'status':r['status'],'relationship_id':r['relationship']['relationship_id'],'revision_id':r['current_revision_id'],'proof_authority':r['proof_authority']}))
"""
    child = subprocess.run([sys.executable, "-B", "-c", child_code, str(output)],
        env=dict(os.environ), capture_output=True, timeout=60, check=True)
    assert len(child.stdout) <= 4096 and not child.stderr
    independent_lookup = json.loads(child.stdout)
    assert independent_lookup == {"status": "hit", "relationship_id": warm["relationship"]["relationship_id"],
        "revision_id": snapshot["revision_id"], "proof_authority": False}
    misses = {}
    for field in ("translation", "assumptions", "environment", "schema", "kernel", "theorem_registry"):
        changed = deepcopy(dimensions)
        changed[field] = ([*changed[field], {"perturbed": field}] if type(changed[field]) is list
            else {"original": changed[field], "independent_perturbation": field})
        result = cache.lookup_revision_candidate(**{**query, "dimensions": changed})
        assert result["status"] == "miss" and result["reason"] == "key_changed"
        misses[field] = {"status": result["status"], "reason": result["reason"],
            "relationship_id": result["relationship"]["relationship_id"]}
    # Change only callee bytes. The caller stays byte-identical.
    (repository / "callee.py").write_bytes(sources["callee.py"].replace(b"+ 1", b"+ 2"))
    source_miss = cache.lookup_revision_candidate(**query)
    assert source_miss["status"] == "miss" and source_miss["reason"] == "source_changed"
    assert pin(repository / "caller.py") == original["caller.py"]
    (repository / "callee.py").write_bytes(sources["callee.py"])
    # Change the dependency edge independently of the callee bytes.
    (repository / "caller.py").write_bytes(sources["caller.py"].replace(b"from callee import increment", b"from absent import increment"))
    edge_miss = cache.lookup_revision_candidate(**query)
    assert edge_miss["status"] == "miss" and edge_miss["reason"] == "source_changed"
    (repository / "caller.py").write_bytes(sources["caller.py"])
    scope = cache.build_revision_scope_index(snapshot=snapshot, dimensions=dimensions)
    invalidations = {}
    changes = {"callee": ("file", "callee.py"),
        "adapter": ("template", cache.identity(dimensions["translation"])),
        "assumptions": ("assumption", cache.identity(dimensions["assumptions"])),
        "toolchain": ("toolchain", cache.identity(dimensions["environment"])),
        "ir_schema": ("ir_family", cache.identity(dimensions["schema"]))}
    dependencies = snapshot["metadata"]["dependency_edges"]
    changes["dependency_edge"] = ("ast_edge", next(row["edge_id"] for row in dependencies
        if row["source_path"] == "caller.py" and row["target_path"] == "callee.py"))
    with public_replay_without_metadata():
        for name, changed_input in changes.items():
            result = invalidate_proof_scope_inputs(scope, [changed_input])
            roundtrip = invalidate_proof_scope_inputs(ProofScopeIndex.from_dict(scope.to_dict()), [changed_input])
            assert result.to_dict() == roundtrip.to_dict()
            assert "cache:candidate" not in result.active_artifact_ids
            if name == "callee":
                assert "module:caller.py" not in result.active_artifact_ids
            invalidations[name] = {"active_artifact_ids": list(result.active_artifact_ids),
                "cache_stale": True, "roundtrip_identical": True}
    # Count one complete advisory retrieval packet using the already pinned
    # Q tokenizer. This is not a native supervisor/provider input observation.
    packet = {"schema": "public-revision-advisory-packet@1", "intent": "plan against the current two-module arithmetic model",
        "revision_id": snapshot["revision_id"], "artifact": pin(artifact),
        "relationship_id": warm["relationship"]["relationship_id"],
        "dependency_edges": dependencies, "residuals": snapshot["metadata"]["records"]["unsupported"],
        "source_semantics_verified": False, "execution_authority": False, "completion_authority": False}
    write(output / "advisory-packet.json", packet)
    encoding = _load_tokenizer()
    measurement = _measure(wire(packet).decode(), encoding)
    assert _tokenizer_digest(encoding) == TOKENIZER_SHA256
    assert [pin(Path(row["path"])) for row in expected["files"]] == expected["files"]
    assert all(pin(repository / name) == original[name] for name in sources)
    result = {"schema": "public-revision-cache-qualification@1", "qualified": True,
        "public_source_files": original, "source_revision_id": snapshot["revision_id"],
        "cache_report": report, "warm_hit": {"status": warm["status"], "relationship_id": warm["relationship"]["relationship_id"]},
        "fresh_process_cache_lookup": independent_lookup,
        "independent_dimension_misses": misses, "callee_only_source_miss": source_miss["reason"],
        "dependency_edge_miss": edge_miss["reason"], "native_invalidations": invalidations,
        "lean_positive": positive["status"], "lean_negative": negative["status"],
        "lean_scope": "kernel_checked_generated_integer_model_only",
        "lean_source_and_object_pins": [positive["artifact"], *positive["compiled_artifacts"]],
        "lean_axiom_inventory": positive["stdout"], "authored_model_sorry_or_admit": False,
        "family_counts": report["metadata"]["family_counts"],
        "unsupported_count": len(snapshot["metadata"]["records"]["unsupported"]),
        "advisory_packet_local_count": measurement, "token_count_scope": "one_complete_advisory_cache_packet_not_supervisor_input_or_provider_usage",
        "source_body_executed": False, "training_steps": 0, "provider_calls": 0,
        "source_equivalence_proved": False, "full_task_satisfaction": False,
        "model_convergence_proved": False, "token_savings_measured": False,
        "runtime_source_pins_unchanged_at_endpoints": True, "elapsed_seconds": time.monotonic() - started,
        **cache.AUTHORITY}
    write(output / "qualification.json", result)
    print(json.dumps({"qualified": True, "warm_hit": warm["status"], "dimension_misses": len(misses),
        "native_invalidations": len(invalidations), "lean_positive": positive["status"], "lean_negative": negative["status"],
        "rows": report["metadata"]["row_count"], "elapsed_seconds": result["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
