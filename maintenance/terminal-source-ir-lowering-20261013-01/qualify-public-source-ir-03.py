"""Fresh local native lowering qualification using authored public source only."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

S = Path(__file__).resolve().parent


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
    # Native artifacts are freshly created under owner-only umask. No native
    # output, imported compiled object or sealed predecessor is chmod-ed later.
    os.umask(0o077)
    from benchmarks.agent_supervisor.container_coding import terminal_revision_proof_cache as cache
    from benchmarks.agent_supervisor.container_coding.terminal_source_ir_lowering import (
        qualify_current_source_ir_lowering, join_source_ir_lowering)
    from benchmarks.agent_supervisor.container_coding.terminal_source_ir_projection import build_source_ir_projection
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import _open, _scheduler
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
    from ipfs_datasets_py.logic.software_contracts import codebase_integer_lowering_lean as lowering
    from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import IntegerOffsetContract, UnsupportedIntegerProfile
    from ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation import seal_finite_integer_tools
    from ipfs_datasets_py.logic.software_contracts.codebase_resources import acquire_codebase_resources
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunLimits
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane

    expected = json.loads((S / "runtime-source-pins.json").read_bytes())["files"]
    assert [pin(Path(row["path"])) for row in expected] == expected
    started = time.monotonic()
    actual = S / "actual-public-lowering-03"
    actual.mkdir(mode=0o700)
    repository = actual / "repository"
    repository.mkdir(mode=0o755)
    repository.chmod(0o755)
    sources = {"callee.py": b"def increment(n: int) -> int:\n    return n + 1\n",
        "caller.py": b"from callee import increment\n\ndef twice(n: int) -> int:\n    return increment(increment(n))\n\ndef unsupported(expression):\n    return eval(expression)\n"}
    for name, raw in sources.items():
        with (repository / name).open("xb") as stream:
            stream.write(raw)
        (repository / name).chmod(0o644)
    # Only this fresh authored repository receives a commit. Original checkout,
    # Git index and remotes are never mutated by this experiment.
    for argv in (["git", "init", "-q"], ["git", "add", "callee.py", "caller.py"],
            ["git", "-c", "user.name=Public Qualification", "-c",
             "user.email=qualification@example.invalid", "commit", "-qm", "authored public lowering source"]):
        subprocess.run(argv, cwd=repository, capture_output=True, timeout=15, check=True)
    originals = {name: pin(repository / name) for name in sources}
    cx, index = _open(actual)
    scheduler = _scheduler(actual / "resources.json")
    repository_id = "public-source-ir-lowering-01"
    policy = seal_finite_integer_tools(python_executable=Path(sys.executable).resolve(),
        lean_executable=Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean"))
    contract = IntegerOffsetContract(path="callee.py", function_name="increment", parameter="n", offset=1)
    native_controls = []
    with public_replay_without_metadata():
        head = index.prepare_current(repository, repository_id=repository_id, operation_id="initial",
            expected_head=None, scheduler=scheduler).head
        write(actual / "head.json", head.to_dict())
        write(actual / "tool-policy.json", policy)
        qualified = qualify_current_source_ir_lowering(index=index, repository=repository,
            expected_head=head, paths=list(sources), repository_id=repository_id, contract=contract.to_dict(),
            tool_policy=policy, output=actual / "qualified", scheduler=scheduler)
        assert qualified["qualified"] and qualified["cache_status"] == "hit"
        assert len(qualified["uncovered_source_obligations"]) == 1
        proof_dict = json.loads((actual / "qualified/native-proof.json").read_bytes())
        projection = json.loads((actual / "qualified/projection.json").read_bytes())
        positive = lowering.IntegerOffsetLoweringProof.from_dict(proof_dict)
        assert proof_dict["source_ast_lowering_proved"] and proof_dict["native_target_correspondence_proved"]

        wrong_contract = IntegerOffsetContract(path="callee.py", function_name="increment", parameter="n", offset=2)
        wrong = lowering.prove_current_integer_offset_lowering(index, repository, expected_head=head,
            contract=wrong_contract, tool_policy=policy, output=actual / "wrong-goal", scheduler=scheduler,
            timeout_seconds=90, memory_mb=1024)
        lowering.validate_current_integer_offset_lowering(wrong, index, repository, expected_head=head,
            contract=wrong_contract, tool_policy=policy, scheduler=scheduler, timeout_seconds=90, memory_mb=1024)
        wrong_data = wrong.to_dict()
        assert wrong_data["status"] == "model_refuted" and wrong_data["requested_model_theorem_proved"] is False
        assert wrong_data["source_ast_lowering_proved"] is True
        wrong_projection = build_source_ir_projection(source=sources["callee.py"],
            contract=wrong_contract.to_dict(), head=head.to_dict())
        wrong_join = join_source_ir_lowering(projection=wrong_projection, proof=wrong_data)
        write(actual / "wrong-goal-summary.json", {"actual_native_prover_returned": True,
            "cold_validation_passed": True, "model_status": wrong_data["status"],
            "model_counterexample": wrong_data["model_counterexample"], "data_join": wrong_join,
            "native_result_cid": wrong_data["result_cid"], "source_ast_lowering_proved": True,
            "runtime_behavior_verified": False, "proof_authority": False})

        # Separate native jobs: never append commands to the original checked
        # source, modify original .olean or forge successful proof records.
        controls = actual / "controls"
        controls.mkdir(mode=0o700)
        runner = BoundedToolRunner(base_environment={**lowering.native._ENV, "LEAN_PATH": "."})
        def run_control(name, files, arguments):
            limits = ToolRunLimits(timeout_seconds=30, cpu_seconds=30,
                memory_bytes=policy["process_limits"]["lean"]["address_space_bytes"],
                resident_memory_bytes=policy["process_limits"]["lean"]["resident_memory_bytes"],
                max_input_bytes=4 * 1024**2, max_workspace_bytes=16 * 1024**2,
                max_output_bytes=65536, max_output_files=8)
            with acquire_codebase_resources(scheduler=scheduler, timeout_seconds=30, memory_mb=1024) as lease:
                with lease.acquire_child(lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=512,
                        child_process_slots=1, timeout=30, request_id="source-ir-control:" + name) as child:
                    raw = runner.run([policy["lean"]["path"], "-j", "1", *arguments],
                        input_files=files, output_paths=(), limits=limits,
                        cancellation=child.combined_cancellation_signal(None))
            assert not any((raw.timed_out, raw.cancelled, raw.unavailable, raw.output_truncated,
                raw.workspace_limit_exceeded, raw.resource_exhausted))
            assert raw.workspace_cleaned
            process = raw.to_dict()
            process["output_files"] = {name: {"bytes": len(value),
                "sha256": hashlib.sha256(value).hexdigest()} for name, value in raw.output_files.items()}
            receipt = {"schema": "terminal-source-ir-native-control@1", "name": name,
                "input_files": {key: {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                    for key, value in files.items()}, "process": process,
                "limits": {"wall_seconds": 30, "input_bytes": 4 * 1024**2,
                    "workspace_bytes": 16 * 1024**2, "output_bytes": 65536},
                "network_isolation_enforced": False, "source_body_executed": False,
                "proof_authority": False, "runtime_behavior_verified": False}
            write(controls / (name + ".json"), receipt)
            native_controls.append(name)
            return raw, receipt

        changed = deepcopy(proof_dict["translation"])
        changed["native_target_syntax"]["right"]["value"] = 2
        assert changed["source_ast_syntax"] == proof_dict["translation"]["source_ast_syntax"]
        assert [key for key in changed if changed[key] != proof_dict["translation"][key]] == ["native_target_syntax"]
        changed_source, changed_theorems = lowering._lean(changed)
        (controls / "TargetMismatch.lean").write_bytes(changed_source)
        negative, negative_receipt = run_control("target-mismatch", {"TargetMismatch.lean": changed_source},
            ["TargetMismatch.lean"])
        assert negative.returncode != 0 and "nativeTargetExpression" in negative.stdout
        assert "rfl" in negative.stdout and "error" in negative.stdout.lower()

        object_descriptor = proof_dict["artifacts"]["lean_olean"]
        object_raw = lowering._read_bytes(Path(object_descriptor["path"]), lowering.native.MAX_WORKSPACE_BYTES, lambda: None)
        assert hashlib.sha256(object_raw).hexdigest() == object_descriptor["sha256"]
        inspection = ("import IntegerLowering\n" + "\n".join(
            "#print axioms CodebaseIntegerLowering." + name for name in projection["theorems"]) + "\n").encode()
        (controls / "Inspect.lean").write_bytes(inspection)
        axioms, axiom_receipt = run_control("axiom-inventory", {"IntegerLowering.olean": object_raw,
            "Inspect.lean": inspection}, ["Inspect.lean"])
        assert axioms.returncode == 0 and not axioms.stderr
        assert all(name in axioms.stdout for name in projection["theorems"])
        assert "sorryAx" not in axioms.stdout and "admit" not in axioms.stdout
        assert pin(Path(object_descriptor["path"]))["sha256"] == object_descriptor["sha256"]

        try:
            build_source_ir_projection(source=sources["caller.py"],
                contract=IntegerOffsetContract(path="caller.py", function_name="twice", parameter="n", offset=2).to_dict(),
                head=head.to_dict())
        except UnsupportedIntegerProfile as error:
            unsupported = {"status": "unsupported", "error_type": type(error).__name__, "reason": str(error),
                "checker_invoked": False, "source_body_executed": False, "proof_authority": False}
        else:
            raise AssertionError("caller unexpectedly entered closed grammar")

        dimensions = json.loads((actual / "qualified/cache-dimensions.json").read_bytes())
        query = dict(output=actual / "qualified/candidate-cache", expected=qualified["advisory_cache"],
            root=repository, paths=list(sources), repository_id=repository_id, dimensions=dimensions)
        (repository / "callee.py").write_bytes(sources["callee.py"].replace(b"+ 1", b"+ 3"))
        try:
            lowering.validate_current_integer_offset_lowering(positive, index, repository, expected_head=head,
                contract=contract, tool_policy=policy, scheduler=scheduler, timeout_seconds=90, memory_mb=1024)
        except ValueError as error:
            source_refusal = {"refused": True, "error_type": type(error).__name__, "reason": str(error)}
        else:
            raise AssertionError("changed source unexpectedly validated")
        miss = cache.lookup_revision_candidate(**query)
        assert miss["status"] == "miss" and miss["reason"] == "source_changed"
        (repository / "callee.py").write_bytes(sources["callee.py"])
        lowering.validate_current_integer_offset_lowering(positive, index, repository, expected_head=head,
            contract=contract, tool_policy=policy, scheduler=scheduler, timeout_seconds=90, memory_mb=1024)
        assert cache.lookup_revision_candidate(**query)["status"] == "hit"
        assert {name: pin(repository / name) for name in sources} == originals
        assert index.current(repository_id).to_dict() == head.to_dict()
        state = scheduler.snapshot()
        assert state["active_lease_count"] == state["waiting_request_count"] == 0
        cx.close()

        child = subprocess.run([sys.executable, "-B", str(S / "cold-validate-source-ir.py"), str(actual)],
            cwd=S, env=dict(os.environ), capture_output=True, timeout=60, check=True)
        assert len(child.stdout) <= 4096 and len(child.stderr) <= 8192
        (actual / "cold-validation.stderr").write_bytes(child.stderr)
        cold = json.loads(child.stdout)
        assert cold["qualified"] and cold["native_result_cid"] == proof_dict["result_cid"]
        assert cold["head"] == head.to_dict() and cold["cache_status"] == "hit"
        assert cold["native_cold_validation_passed"] and cold["metadata_verified"]
        assert cold["new_prover_invocations"] == cold["active_lease_count"] == cold["waiting_request_count"] == 0
        write(actual / "cold-validation.json", cold)

    assert [pin(Path(row["path"])) for row in expected] == expected
    summary = {"schema": "terminal-source-ir-public-qualification@1", "qualified": True,
        "output": str(actual), "elapsed_milliseconds": int(1000 * (time.monotonic() - started)),
        "head": head.to_dict(), "native_result_cid": proof_dict["result_cid"],
        "projection_id": projection["projection_id"], "native_lowering_proof_jobs": 2,
        "native_lean_processes": 6, "native_control_jobs": native_controls,
        "formal_scope": lowering.SCOPE, "source_ast_lowering_proved": True,
        "native_target_correspondence_proved": True, "model_goal": "model_proved",
        "wrong_goal": "model_refuted", "wrong_goal_counterexample": wrong_data["model_counterexample"],
        "target_mismatch_rejected": True, "axiom_inventory": pin(controls / "axiom-inventory.json"),
        "unsupported_caller": unsupported, "source_change_refused": source_refusal,
        "source_change_cache_miss": {"status": miss["status"], "reason": miss["reason"]},
        "fresh_process_cold_validation": cold, "metadata": qualified["metadata"],
        "original_source_pins_restored": originals, "runtime_source_pins_unchanged": True,
        "active_lease_count": 0, "waiting_request_count": 0,
        "source_body_executed": False, "training_steps": 0, "provider_calls": 0,
        "network_isolation_enforced": False, "source_semantics_verified": False,
        "cpython_equivalence_proved": False, "source_parser_correctness_proved": False,
        "whole_program_semantics_verified": False, "training_convergence_proved": False,
        "full_task_satisfaction": False, "production_activated": False,
        "original_task_budget_qualified": False, "proof_authority": False,
        "execution_authority": False, "completion_authority": False}
    summary["summary_cid"] = cid_for_structured(summary)
    write(S / "actual-qualification.json", summary)
    print(json.dumps({"qualified": True, "model_goal": summary["model_goal"],
        "wrong_goal": summary["wrong_goal"], "target_mismatch_rejected": True,
        "cold_cache": cold["cache_status"], "source_ast_lowering_proved": True,
        "source_semantics_verified": False, "training_steps": 0}))


if __name__ == "__main__":
    main()
