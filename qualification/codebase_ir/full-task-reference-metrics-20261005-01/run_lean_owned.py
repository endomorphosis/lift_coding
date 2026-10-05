"""Finite exact-embedding checks; existing 64KiB artifacts and admission gates."""
from pathlib import Path
import json
import os
import sys
import time
import traceback

from run_owned import DATASETS, BASE, imports, pin, save


def main():
    attempt = sys.argv[1]
    assert attempt.startswith("lean-") and attempt[5:].isdigit()
    out = BASE / "evidence" / attempt
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    record = {"schema": "terminal-authored-metric-finite-lean-owned-attempt@1", "status": "started",
              "cleanup_errors": [], "native_checks": [], "native_lean_calls": 0,
              "training_calls": 0, "optimizer_updates": 0, "PlanCreate_calls": 0,
              "actual_benchmark_instances_or_heldout_data_read": False, "official_benchmark_score": None,
              "full_task_satisfaction": "unknown", "model_convergence_proved": False,
              "universal_cost_model_semantics_proved": False,
              "artifact_retention_profile": "unchanged_core64KiB",
              "selected_tooling_scope": "Observed parent source imports and selected Lean executable/Std root artifact pins; no whole checkout, child, native library or all-loader census."}
    scheduler = lease = None
    try:
        embedding_path = BASE / "lean-preparation/embedding.json"
        binding = pin(embedding_path)
        assert binding["sha256"] == "a2e5d0eaedefaced963ecb6bdee3749333928f7c6d7dda047ed63c01d5a43a7e"
        embedding = json.loads(embedding_path.read_bytes())
        assert pin(Path(embedding["native_result"]["path"])) == embedding["native_result"]
        record["embedding"] = binding
        executable = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.0/bin/lean")
        lean_pins = [pin(executable), pin(executable.parent.parent / "lib/lean/Std.olean")]
        record["selected_lean_toolchain_pins"] = lean_pins
        os.environ["IPFS_DATASETS_RESOURCE_SCHEDULER_PATH"] = str(out / "resources.json")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        sys.path.insert(0, str(DATASETS))
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane
        from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunRequest, ToolRunLimits
        scheduler = get_global_resource_scheduler()
        policy = scheduler.config
        assert policy.proof_safety_enabled and (policy.proof_memory_stall_percent, policy.proof_cpu_stall_percent,
               policy.proof_io_stall_percent, policy.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0)
        tooling_before = imports()
        record["selected_parent_tooling_before"] = tooling_before
        record["resource_policy"] = policy.persisted_dict()
        lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048,
                                  child_process_slots=1, timeout=30)
        record["root_lease"] = lease.to_dict()
        save(out / "started.json", record)
        for source_binding, expected_success in zip(embedding["lean_sources"], (True, False)):
            path = Path(source_binding["path"])
            assert pin(path) == source_binding
            source = path.read_bytes()
            assert pin(path) == source_binding
            name = path.name
            target = out / name
            target.open("xb").write(source)
            object_name = str(Path(name).with_suffix(".olean"))
            argv = (str(executable), "-o", object_name, name) if expected_success else (str(executable), name)
            record["native_lean_calls"] += 1
            result = BoundedToolRunner().run(ToolRunRequest(argv=argv,
                input_files={name: source}, output_paths=(object_name,) if expected_success else (),
                limits=ToolRunLimits(timeout_seconds=20, cpu_seconds=20, max_input_bytes=262144,
                                     max_output_bytes=65536, max_workspace_bytes=16 * 1024 * 1024)))
            artifacts = []
            for output_name, raw in result.output_files.items():
                artifact = out / output_name
                artifact.open("xb").write(raw)
                artifacts.append(pin(artifact))
            passed = result.ok and not any((result.output_truncated, result.workspace_limit_exceeded,
                                           result.timed_out, result.cancelled, result.resource_exhausted)) and bool(artifacts)
            rejected = (result.returncode is not None and result.returncode != 0 and
                not any((result.timed_out, result.cancelled, result.unavailable, result.resource_exhausted,
                         result.output_truncated, result.workspace_limit_exceeded)) and
                "Tactic `decide` proved that the proposition" in result.stdout and "is false" in result.stdout)
            check = {"schema": "terminal-authored-metric-finite-lean-check@1", "source": pin(target),
                     "expected_success": expected_success, "status": "passed" if passed else "rejected" if rejected else "inconclusive",
                     "matches_expectation": passed if expected_success else rejected,
                     "compiled_artifacts": artifacts, "run": result.to_dict(),
                     "finite_observed_values_only": True, "universal_cost_model_semantics_proved": False,
                     "whole_source_equivalence_proved": False, "actual_benchmark_satisfaction_proved": False,
                     "model_convergence_proved": False, "proof_authority": False,
                     "execution_authority": False, "completion_authority": False}
            save(out / (name + ".check.json"), check)
            record["native_checks"].append({"receipt": pin(out / (name + ".check.json")),
                                            "status": check["status"], "matches_expectation": check["matches_expectation"]})
            assert check["matches_expectation"]
        assert pin(embedding_path) == binding
        for row in lean_pins + tooling_before:
            assert pin(Path(row["path"])) == row
        record["selected_parent_tooling_after"] = imports()
        record["selected_parent_tooling_common_pins_stable"] = True
        record["status"] = "passed_eight_finite_bounds_and_rejected_false_control"
    except BaseException as problem:
        record.update(status="unknown_failed_attempt_retained", primary_error_type=type(problem).__name__,
                      primary_error_traceback=traceback.format_exc())
    finally:
        if lease is not None:
            try:
                lease.release()
                record["root_lease"] = lease.to_dict()
            except BaseException as problem:
                record["cleanup_errors"].append(type(problem).__name__)
        record["actual_owned_elapsed_seconds"] = time.monotonic() - start
        if scheduler is not None:
            record["final_scheduler_snapshot"] = scheduler.snapshot()
        save(out / "closed.json", record)
    print(json.dumps({"status": record["status"], "closed": pin(out / "closed.json"),
                      "elapsed_seconds": record["actual_owned_elapsed_seconds"]}))
    return 0 if record["status"] == "passed_eight_finite_bounds_and_rejected_false_control" else 1


if __name__ == "__main__":
    raise SystemExit(main())
