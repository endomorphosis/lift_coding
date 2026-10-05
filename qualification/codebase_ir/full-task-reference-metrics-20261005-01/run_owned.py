"""Existing published ownership and gates; only new authored public-model evidence."""
from pathlib import Path
import hashlib
import json
import os
import stat
import sys
import time
import traceback

ROOT = Path("/home/barberb/lift_coding")
BASE = Path(__file__).resolve().parent
DATASETS = ROOT / "maintenance/terminal-ir-publication-20261004-01/datasets/checkout"
sys.dont_write_bytecode = True


def pin(path):
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        count = 0
        while block := os.read(fd, 1024 * 1024):
            digest.update(block)
            count += len(block)
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        assert all(getattr(before, key) == getattr(os.fstat(fd), key) == getattr(path.lstat(), key) for key in fields)
        return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def save(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def imports():
    selected = set()
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if name:
            path = Path(name).resolve()
            if path.suffix == ".py" and path.is_relative_to(DATASETS):
                selected.add(path)
    return [pin(path) for path in sorted(selected)]


def main():
    attempt = sys.argv[1]
    assert attempt.startswith("metrics-") and attempt[8:].isdigit()
    out = BASE / "evidence" / attempt
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    record = {"schema": "terminal-authored-reference-metrics-owned-attempt@1", "status": "started",
              "cleanup_errors": [], "official_benchmark_score": None, "training_calls": 0,
              "optimizer_updates": 0, "PlanCreate_calls": 0, "prover_calls": 0,
              "full_task_satisfaction": "unknown", "model_convergence_proved": False,
              "actual_benchmark_instances_or_heldout_data_read": False,
              "selected_tooling_scope": "Observed parent Python source imports from published datasets checkout; no whole checkout, child, native library or all-loader census."}
    scheduler = lease = None
    pins = []
    try:
        source_specs = (
            ("source/cost_model.py", ROOT / ".benchmarks/terminal-bench-2/llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py", "0cf417fd5ff0112defcd46970d37a290c0763c5a9092e91cb3ebb86c3f20e6ce"),
            ("source/reference.py", ROOT / "external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/terminal_codebase_batching_contract_reference.py", "afcfe16033f1c7faa0bc255cf62d98fd667ee28a1514b2a329a69aac29a0e441"),
            ("control.py", BASE / "control.py", None))
        files = {}
        for name, path, expected in source_specs:
            binding = pin(path)
            assert expected is None or binding["sha256"] == expected
            raw = path.read_bytes()
            assert pin(path) == binding
            pins.append(binding)
            files[name] = raw
            target = out / "captured" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.open("xb").write(raw)
        for bucket, first, expected in ((1, 64, "59f779e03963f0f94a66ff19763e7a424fc6d0063cc4b3385a74763b23b41a46"),
                                        (2, 576, "cfd0640d0c8535ced94c3b87467537dcf25c320f8ab02ebd63f9403ba4972f7b")):
            rows = [{"request_id": f"model-b{bucket}-r{i + 1:02d}", "prompt_len": first + 64 * i, "gen_len": 1} for i in range(8)]
            raw = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
            assert hashlib.sha256(raw).hexdigest() == expected
            name = f"task_file/input_data/requests_bucket_{bucket}.jsonl"
            files[name] = raw
            target = out / "captured" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.open("xb").write(raw)
        save(out / "input-manifest.json", {"schema": "terminal-authored-reference-metrics-inputs@1",
            "original_source_pins": pins,
            "files": [{"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in sorted(files.items())],
            "fixture_used_for_training": False, "actual_benchmark_instances_or_heldout_data_read": False})
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
        result = BoundedToolRunner().run(ToolRunRequest(
            argv=(sys.executable, "-I", "-S", "-B", "control.py"), input_files=files,
            output_paths=("result.json", "task_file/output_data/plan_b1.jsonl", "task_file/output_data/plan_b2.jsonl"),
            limits=ToolRunLimits(timeout_seconds=10, cpu_seconds=10, max_input_bytes=262144,
                                 max_output_bytes=65536, max_workspace_bytes=16 * 1024 * 1024)))
        record.update(result.to_dict())
        assert result.ok and not result.output_truncated and result.workspace_cleaned
        outputs = []
        for name, raw in result.output_files.items():
            path = out / "output" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.open("xb").write(raw)
            outputs.append(pin(path))
        record["output_bindings"] = outputs
        observed = json.loads(result.output_files["result.json"])
        record["scoped_result_status"] = observed["status"]
        record["status"] = "passed_native_metrics_recorded" if observed["status"] == "passed_scoped_authored_fixture" else "refuted_native_metrics_recorded"
        for binding in pins:
            assert pin(Path(binding["path"])) == binding
        tooling_after = imports()
        for binding in tooling_before:
            assert pin(Path(binding["path"])) == binding
        record["selected_parent_tooling_after"] = tooling_after
        record["selected_parent_tooling_common_pins_stable"] = True
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
    return 0 if record["status"] in ("passed_native_metrics_recorded", "refuted_native_metrics_recorded") else 1


if __name__ == "__main__":
    raise SystemExit(main())
