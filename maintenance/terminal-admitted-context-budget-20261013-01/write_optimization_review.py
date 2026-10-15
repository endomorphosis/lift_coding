"""Write one bounded, data-only evaluation of AA11 and the AA12 batch diff."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parent
CHECKOUT = ROOT / "checkout"
RELATIVE_BROKER = "ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py"
EXPECTED_FINAL_BROKER = "12ea4b3b5c4041d19666f7c9a01c29cf83b2ed38ac9506ebc47998e631360636"
MAX_BYTES = 8 * 1024 * 1024
FALSE = {
    "execution_authority": False, "completion_authority": False,
    "proof_authority": False, "source_to_model_equivalence_proved": False,
    "semantic_equivalence_proved": False, "convergence_proved": False,
    "full_task_satisfaction": False, "model_training_performed": False,
    "all_metadata_families_compiled_with_Lean": False,
    "Terminal_Bench_harness_used": False, "full_supervisor_entrypoint_used": False,
    "provider_usage_measured": False, "provider_billing_savings_measured": False,
    "whole_task_token_savings_proved": False, "global_task_budget_enforced": False,
    "durable_budget_resume_supported": False, "deadlock_absence_proved": False,
    "runtime_performance_improvement_verified": False,
    "cross_batch_allocation_metadata_FD_custody_added": False,
    "loaded_module_code_attested": False, "transitive_environment_closure_attested": False,
    "published_to_GitHub_or_HuggingFace": False,
}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def stamp(info):
    return tuple(getattr(info, key) for key in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns"))


def capture(path):
    """Only the explicitly named owned public file; retained/fresh byte joins."""
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
        assert before.st_nlink == 1 and 0 < before.st_size <= MAX_BYTES
        raw = os.pread(fd, before.st_size + 1, 0)
        assert len(raw) == before.st_size
        assert stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat())
        fresh = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            assert stamp(before) == stamp(os.fstat(fresh))
            assert os.pread(fresh, before.st_size + 1, 0) == raw
            assert stamp(before) == stamp(os.fstat(fresh)) == stamp(os.fstat(fd)) == stamp(path.lstat())
            assert path.resolve(strict=True) == path
        finally:
            os.close(fresh)
    finally:
        os.close(fd)
    return raw, {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def methods(raw):
    tree = ast.parse(raw.decode("utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "OwnerCheckedContextDispatchBroker")
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


def attribute_calls(node):
    return [item.func.attr for item in ast.walk(node)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)]


def main():
    paths = {
        "progress": ROOT / "actual-start-11/public/broker-progress-samples.json",
        "cleanup": ROOT / "actual-start-11/public/native-cleanup.json",
        "budget": ROOT / "actual-start-11/public/final-budget-state.json",
        "result": ROOT / "actual-start-11/result.json",
        "outer_cleanup": ROOT / "actual-start-11/public/outer-owner-cleanup.json",
        "broker_close": ROOT / "actual-start-11/public/checked-context-dispatch-broker-close-receipt.json",
        "primary_traceback": ROOT / "actual-start-11/public/native-operation-failure-traceback.txt",
        "old_broker": ROOT / "source-before-12" / RELATIVE_BROKER,
        "new_broker": CHECKOUT / RELATIVE_BROKER,
        "scope": CHECKOUT / "ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py",
        "delivery": CHECKOUT / "benchmarks/agent_supervisor/container_coding/terminal_semantic_budget_delivery.py",
        "owner_harness": ROOT / "container_run_admitted_11.py",
        "tests": CHECKOUT / "test/api/test_checked_context_dispatch.py",
    }
    data, pins = {}, {}
    for name, path in paths.items():
        data[name], pins[name] = capture(path)
    assert pins["new_broker"]["bytes"] == 60401
    assert pins["new_broker"]["sha256"] == EXPECTED_FINAL_BROKER
    assert pins["old_broker"]["bytes"] == 59461
    assert pins["old_broker"]["sha256"] == "df38c901c8cbdc75d746eb351f767a7c1feb221c4fb5b3c2c21c4c4847c8891a"
    progress = json.loads(data["progress"])
    samples = progress["samples"]
    assert progress["schema"] == "admitted-budget-broker-progress-samples@1" and len(samples) == 29
    assert progress["diagnostic_only"] is True and progress["deadline_extended"] is False
    assert progress["locking_getters_used"] is progress["current_verification_added"] is False
    assert samples[-1]["elapsed_milliseconds"] == 58518
    assert samples[-1]["owner_process_cpu_elapsed_ns"] == 41887013520
    assert [row["ordinal"] for row in samples] == list(range(29))
    assert all(row["cpu_scope"] == "Aggregate original owner process CPU, including its threads; not broker-only CPU."
               for row in samples)
    born = [row for row in samples if row["broker"]["wrapper_birth_observed"]]
    assert born and born[0]["elapsed_milliseconds"] == 52128
    assert all(row["broker"]["worker_birth_observed"] is False for row in samples)
    initial = [row for row in samples if row["elapsed_milliseconds"] <= 8007]
    assert len(initial) == 5 and all(row["broker"]["boundary"] == "unparsed" for row in initial)
    deepest = [{"elapsed_milliseconds": row["elapsed_milliseconds"],
                "owner_process_cpu_elapsed_ns": row["owner_process_cpu_elapsed_ns"],
                "boundary": row["broker"]["boundary"],
                "wrapper_birth_observed": row["broker"]["wrapper_birth_observed"],
                "worker_birth_observed": row["broker"]["worker_birth_observed"],
                "location": row["broker"]["thread_frames"][-1]} for row in samples]
    assert len({(row["location"]["file"], row["location"]["function"], row["location"]["line"])
                for row in deepest[5:]}) > 1
    cleanup, budget, result, outer, broker_close = [json.loads(data[name]) for name in (
        "cleanup", "budget", "result", "outer_cleanup", "broker_close")]
    assert result["qualified"] is False and result["container"] == "ipfs-admitted-context-budget-aa11"
    assert result["container_disposal"] == {"container_absent": True,
        "only_exact_owned_container_removed": True, "remove_returncode": 0, "stop_returncode": 0}
    assert cleanup["primary_failure"]["type"] == "TimeoutError" and b"TimeoutError" in data["primary_traceback"]
    assert cleanup["STOP_called"] is cleanup["closed"] is True and cleanup["errors"] == []
    assert cleanup["remaining_owner_processes"] == cleanup["final_worker_cleanup_returncode"] == 0
    assert cleanup["stop"]["status"] == "succeeded" and cleanup["stop"]["data"]["old_tree_fenced"] is True
    assert cleanup["stop"]["data"]["isolated_worker_cleanup"]["returncode"] == 0
    assert outer == {"errors": [], "original_budget_closed": True, "scope_closed": True}
    assert broker_close["broker_closed"] is broker_close["socket_removed"] is broker_close["thread_joined"] is True
    assert broker_close["worker_birth_observed"] is False
    assert budget["closed"] is True and len(budget["records"]) == 1
    assert budget["records"][0]["status"] == "aborted"
    assert budget["records"][0]["event"]["event_id"] == "checked-observer:initial"
    assert budget["totals"]["rendered_input_tokens"] == 59134
    assert budget["totals"]["rendered_input_bytes"] == 169372
    old, new = methods(data["old_broker"]), methods(data["new_broker"])
    old_identity = old["_identity_current"].body[:-1]
    new_identity = new["_identity_checkpoint"].body[1:]
    assert [ast.dump(node) for node in old_identity] == [ast.dump(node) for node in new_identity]
    assert attribute_calls(new["_identity_current"]).count("_identity_checkpoint") == 1
    assert attribute_calls(new["_identity_current"]).count("_verify") == 1
    assert attribute_calls(new["_closing_authority"]).count("_identity_current") == 2
    assert attribute_calls(new["_closing_authority"]).count("_claim") == 2
    assert attribute_calls(new["_closing_authority"]).count("_worktree_current") == 2
    assert b"checkpoint = self._identity_checkpoint" in data["new_broker"]
    for name in ("scope", "delivery", "owner_harness", "tests"):
        ast.parse(data[name].decode("utf-8"))
    report = {
        "schema": "terminal-admitted-context-budget-optimization-evaluation@1",
        "evaluation_only": True, "evaluation_passed": True,
        "scope": "Read-only assessment of one preserved failed AA11 run and the exact AA12 broker batch diff.",
        "read_policy": "Explicit named owned regular files, each at most 8 MiB; retained/fresh file-stat and byte joins. No directory recursion or private database/CAS/key bodies.",
        "read_pins": list(pins.values()), "selected_pins": pins,
        "actual11": {
            "qualified": False, "primary_failure": cleanup["primary_failure"],
            "sample_count": len(samples), "last_sample_wall_milliseconds": 58518,
            "last_sample_owner_process_cpu_elapsed_ns": 41887013520,
            "cpu_scope": "Aggregate original owner process CPU including all threads; broker-only CPU was not measured.",
            "initial_samples_unparsed_through_milliseconds": 8007,
            "first_sample_with_wrapper_birth_milliseconds": 52128,
            "first_wrapper_sample_is_birth_time_exact": False,
            "isolated_worker_birth_observed": False,
            "samples": deepest,
            "observation": "Sampled locations change across hashing, projection, semantic replay, catalog and supervisor metadata operations while aggregate owner CPU increases.",
            "inference": "The evidence supports investigating cumulative repeated validation cost. It does not isolate broker CPU, attribute elapsed time to a particular function, or prove absence of locking or I/O stalls.",
            "deadline_extended": False, "deadlock_proved": False,
            "reserved_event_status": "aborted", "reservation_refunded": False,
            "charged_rendered_input_tokens": 59134, "charged_rendered_input_bytes": 169372,
            "charged_new_content_tokens": budget["totals"]["new_content_tokens"],
            "charged_new_content_bytes": budget["totals"]["new_content_bytes"],
            "native_STOP_succeeded": True, "old_tree_fenced": True,
            "remaining_owner_processes": 0, "isolated_cleanup_returncode": 0,
            "original_scope_closed": True, "original_budget_closed": True,
            "broker_thread_joined": True, "broker_socket_removed": True,
            "shutdown_ambiguous_birth_possible": broker_close["ambiguous_birth_possible"],
            "container": result["container"], "container_disposal": result["container_disposal"],
        },
        "static_batch_change": {
            "old_broker": pins["old_broker"], "new_broker": pins["new_broker"],
            "count_scope": "Nominal direct full scope-current calls on the successful two-handoff route, excluding construction, START, observer, commit, cleanup and additional nested work; not a runtime call measurement.",
            "old_nominal_full_current_calls": {"first_handoff": 22, "isolated_handoff": 13, "total": 35},
            "new_nominal_full_current_calls": {"first_handoff": 10, "isolated_handoff": 7, "total": 17},
            "removed_per_file_full_calls": 21, "added_closing_full_calls": 3,
            "worktree_read_checkpoints_per_batch": 7,
            "immutable_identity_checks_preserved_by_AST_comparison": True,
            "per_file_checkpoint_grants_effect_authority": False,
            "closing_order": ["full current validation", "exact native claim comparison",
                "bootstrap/worktree/run-lease/grant-budget checks", "full current validation after protected read batch",
                "post-callback exact native claim comparison", "post-callback bootstrap/worktree/run-lease/grant-budget reread",
                "remaining native attempt acknowledgement expiry check", "return to guarded handoff before prepared ACK"],
            "scope_source_model_producer_guards_waived": False,
            "native_claim_or_coordinator_fences_waived": False,
            "cross_batch_allocation_metadata_FD_custody_added": False,
            "allocation_read_scope": "Bounded fresh owner file reads and exact native binding/lifecycle reconstruction. Original source/model FD custody remains separate.",
            "actual12_performance_measurement_present": False,
        },
        "independent_readonly_review": {
            "review_outcome": "No blocking issue found in the exact batch diff under the existing pinned native producer trust assumptions.",
            "blocking_issues": [],
            "findings": [
                "Only bounded allocation read checkpoints become identity-only; every allocation caller remains inside closing authority.",
                "Full validation brackets the allocation read batch, and current-policy callback results cannot substitute for the subsequent native authority reread.",
                "Claim, bootstrap, allocated worktree, run lease, active grant and remaining attempt expiry are rechecked before prepared authorization.",
                "Original source/model/producers are still checked by the full scope guard, including checks after policy callbacks.",
                "No same-thread recursive scope-current call is evident in the reviewed current-check path; sampled stacks alone do not establish a deadlock.",
                "The added test source explicitly mocks native authority and exercises final-callback claim/grant/worktree/bootstrap/run-lease/proof drift before and after reserve. This evaluator did not execute those tests.",
            ],
            "tests_executed_by_evaluator": 0, "native_jobs_executed_by_evaluator": 0,
            "project_modules_imported_by_evaluator": 0, "subprocesses_invoked_by_evaluator": 0,
            "runtime_authority_reconstructed_from_JSON": False,
        },
        "science_and_authority_ceilings": FALSE,
    }
    # All captured inputs must remain exact through this one report publication.
    for name, path in paths.items():
        assert capture(path)[1] == pins[name]
    raw = wire(report) + b"\n"
    output = ROOT / "optimization-review.json"
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    print(json.dumps({"path": str(output), "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(), "evaluation_passed": True}, sort_keys=True))


if __name__ == "__main__":
    main()
