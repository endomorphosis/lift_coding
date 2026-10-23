"""Actual bounded caller qualification on freshly authored public source only.

This driver is intentionally separate from the retained runtime adapters. Its
fault injections alter only its own fresh experiment, and its compiled imports
are byte copies of genuinely produced native objects. It never executes the
authored Python functions or claims Python import/runtime equivalence.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


T = Path(__file__).resolve().parent
REPOSITORY_ID = "public-call-ir-01"
SOURCES = {
    "callee.py": b"def increment(n: int) -> int:\n    return n + 1\n",
    "caller.py": (
        b"from callee import increment\n\n"
        b"def twice(n: int) -> int:\n"
        b"    return increment(increment(n))\n"
    ),
    "dynamic.py": b"def unsupported(expression):\n    return eval(expression)\n",
}
PUBLIC_FILES = []


def need(value, message):
    if not value:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def new_bytes(path, raw, mode=0o600):
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(raw)
    PUBLIC_FILES.append(path)
    return pin(path)


def new_json(path, value):
    return new_bytes(path, wire(value))


def mutable_bytes(path, raw, mode):
    """Write only a known, existing fresh fixture file without following links."""
    need(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode),
         "canonical existing mutable fixture required")
    descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(raw)


def main():
    os.umask(0o077)
    # Namespace selection precedes package imports. The whole actual workflow
    # also runs under the native public-metadata suppression context.
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["IPFS_ACCELERATE_META_INDEX_DUCKDB"] = str(T / "actual-public-call-01-meta.duckdb")
    os.environ.pop("IPFS_ACCELERATE_META_INDEX_DUCKLAKE", None)
    expected_file = T / "runtime-source-pins.json"
    need(expected_file.is_file(), "root must freeze runtime-source-pins.json before qualification")
    expected = json.loads(expected_file.read_bytes())["files"]
    need(type(expected) is list and expected, "nonempty frozen runtime file inventory required")
    actual = T / "actual-public-call-01"
    need(not actual.exists() and not actual.is_symlink(), "fresh actual experiment namespace required")
    need(not (T / "actual-qualification.json").exists(), "qualification summary must not be overwritten")
    driver_before = pin(Path(__file__).resolve())
    runtime_before = [pin(Path(row["path"])) for row in expected]
    need(runtime_before == expected, "frozen runtime source pins differ before execution")
    started = time.monotonic()

    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
    with public_replay_without_metadata(), redirect_stdout(sys.stderr):
        from benchmarks.agent_supervisor.container_coding import (
            codebase_ir_metadata as storage,
            terminal_call_ir_composition as composition,
            terminal_revision_proof_cache as cache,
        )
        from benchmarks.agent_supervisor.container_coding.terminal_call_ir_projection import build_call_ir_projection
        from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import (
            _open, _scheduler,
        )
        from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunLimits
        from ipfs_datasets_py.logic.software_contracts import codebase_integer_lowering_lean as native
        from ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation import seal_finite_integer_tools
        from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import IntegerOffsetContract
        from ipfs_datasets_py.logic.software_contracts.codebase_resources import acquire_codebase_resources
        from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane

        actual.mkdir(mode=0o700)
        repository = actual / "repository"
        repository.mkdir(mode=0o755)
        repository.chmod(0o755)
        for name, raw in SOURCES.items():
            new_bytes(repository / name, raw, mode=0o644)
        # The only Git mutations are in this just-created authored repository.
        for argv in (
            ["git", "init", "-q"], ["git", "add", *SOURCES],
            ["git", "-c", "user.name=Public Qualification", "-c",
             "user.email=qualification@example.invalid", "commit", "-qm", "authored public call source"],
        ):
            subprocess.run(argv, cwd=repository, capture_output=True, timeout=15, check=True)
        original_sources = {name: pin(repository / name) for name in SOURCES}
        policy = seal_finite_integer_tools(
            python_executable=Path(sys.executable).resolve(),
            lean_executable=Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean"),
        )
        tool_before = {name: pin(Path(policy[name]["path"])) for name in ("python", "lean")}
        callee_contract = IntegerOffsetContract("callee.py", "increment", "n", 1).to_dict()
        caller_contract = IntegerOffsetContract("caller.py", "twice", "n", 2).to_dict()
        scheduler = _scheduler(actual / "resources.json")
        connection, index = _open(actual)
        controls = actual / "controls"
        controls.mkdir(mode=0o700)
        control_receipts = []
        head = None

        def runtime_check():
            need([pin(Path(row["path"])) for row in expected] == expected,
                 "frozen runtime changed during qualification")
            need(pin(Path(__file__).resolve()) == driver_before, "qualification driver changed")
            native.native._policy(policy, lambda: None)

        def originals_check():
            need({name: pin(repository / name) for name in SOURCES} == original_sources,
                 "authored source bytes were not restored")

        def checkpoint():
            runtime_check()
            originals_check()
            if head is not None:
                index.observe_current(repository, expected_head=head, scheduler=scheduler)

        def record_refusal(name, operation):
            try:
                operation()
            except ValueError as error:
                return {"name": name, "refused": True, "error_type": type(error).__name__,
                        "reason": str(error)[:4096], "new_prover_invocations": 0, "proof_authority": False}
            raise ValueError("adversarial control was unexpectedly accepted: " + name)

        def rebind(value, field="result_cid"):
            value[field] = cid_for_structured({key: item for key, item in value.items() if key != field})

        runner = BoundedToolRunner(base_environment={**native.native._ENV, "LEAN_PATH": "."})

        def run_control(name, files, arguments, outputs=()):
            checkpoint()
            limits = ToolRunLimits(
                timeout_seconds=30, cpu_seconds=30,
                memory_bytes=policy["process_limits"]["lean"]["address_space_bytes"],
                resident_memory_bytes=policy["process_limits"]["lean"]["resident_memory_bytes"],
                max_input_bytes=4 * 1024**2, max_workspace_bytes=16 * 1024**2,
                max_output_bytes=65536, max_output_files=8,
            )
            with acquire_codebase_resources(scheduler=scheduler, timeout_seconds=30, memory_mb=1024) as lease:
                signal = lease.combined_cancellation_signal(None)
                with lease.acquire_child(
                    lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=512,
                    child_process_slots=1, timeout=30, cancel_event=signal,
                    request_id="public-call-control:" + name,
                ) as child:
                    raw = runner.run(
                        [policy["lean"]["path"], "-j", "1", *arguments], input_files=files,
                        output_paths=outputs, limits=limits,
                        cancellation=child.combined_cancellation_signal(signal),
                    )
            checkpoint()
            need(not any((raw.timed_out, raw.cancelled, raw.unavailable, raw.output_truncated,
                          raw.workspace_limit_exceeded, raw.resource_exhausted)) and raw.workspace_cleaned,
                 "native control did not complete within its actual bounds")
            need(type(raw.returncode) is int and not raw.error, "native control did not return an actual exit code")
            process = native.native._process(raw, {
                "timeout_ms": 30000, "cpu_seconds": 30,
                "address_space_bytes": limits.memory_bytes,
                "resident_memory_bytes": limits.resident_memory_bytes,
                "max_input_bytes": limits.max_input_bytes, "max_output_bytes": limits.max_output_bytes,
                "max_workspace_bytes": limits.max_workspace_bytes, "max_output_files": limits.max_output_files,
            })
            process["output_files"] = {
                filename: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                           "cid": cid_for_bytes(body)} for filename, body in raw.output_files.items()
            }
            receipt = {
                "schema": "terminal-call-ir-native-control@1", "name": name,
                "input_files": {filename: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                                            "cid": cid_for_bytes(body)} for filename, body in files.items()},
                "process": process, "limits": {"wall_seconds": 30, "cpu_seconds": 30,
                    "input_bytes": 4 * 1024**2, "workspace_bytes": 16 * 1024**2, "output_bytes": 65536},
                "network_isolation_enforced": False, "source_body_executed": False,
                "proof_authority": False, "runtime_behavior_verified": False,
            }
            descriptor = new_json(controls / (name + ".json"), receipt)
            control_receipts.append(descriptor)
            return raw, receipt

        try:
            head = index.prepare_current(
                repository, repository_id=REPOSITORY_ID, operation_id="initial",
                expected_head=None, scheduler=scheduler,
            ).head
            new_json(actual / "head.json", head.to_dict())
            new_json(actual / "tool-policy.json", policy)
            qualified = composition.qualify_current_call_composition(
                index=index, repository=repository, expected_head=head, paths=list(SOURCES),
                repository_id=REPOSITORY_ID, callee_contract=callee_contract, caller_contract=caller_contract,
                tool_policy=policy, output=actual / "qualified", scheduler=scheduler,
            )
            need(qualified["qualified"] is True and qualified["cache_status"] == "hit",
                 "actual caller qualification did not return a current candidate")
            need(all(qualified[key] is False for key in composition.AUTHORITY), "caller authority ceiling differs")
            output = actual / "qualified"
            projection = json.loads((output / "projection.json").read_bytes())
            proof = json.loads(Path(qualified["callee"]["native_proof"]["path"]).read_bytes())
            positive_generated = json.loads((output / "generated.json").read_bytes())
            callee_object = (output / "IntegerLowering.olean").read_bytes()
            caller_object = (output / "CallerComposition.olean").read_bytes()
            need(cid_for_bytes(callee_object) == proof["artifacts"]["lean_olean"]["cid"],
                 "actual imported native callee bytes differ")
            need(qualified["coverage"]["closed_call_model_paths"] == ["callee.py", "caller.py"]
                 and [row["path"] for row in qualified["coverage"]["residuals"]] == ["dynamic.py"],
                 "dynamic source was omitted from residual coverage")
            immutable_paths = {Path(value["path"]) for value in proof["artifacts"].values()}
            immutable_paths.update({Path(qualified["callee"]["native_proof"]["path"]),
                Path(proof["output"]) / "result.json", output / "IntegerLowering.olean",
                output / "CallerComposition.olean", output / "CallerComposition.lean"})
            native_artifacts_before = [pin(path) for path in sorted(immutable_paths)]

            # A genuine refutation of the requested caller offset uses the
            # positive native callee object and a separately checked caller.
            wrong_directory = actual / "wrong-goal"
            wrong_directory.mkdir(mode=0o700)
            wrong_projection = build_call_ir_projection(
                sources={name: SOURCES[name] for name in ("callee.py", "caller.py")},
                callee_contract=callee_contract,
                caller_contract=IntegerOffsetContract("caller.py", "twice", "n", 3).to_dict(),
                head=head.to_dict(),
            )
            wrong_generated = composition.build_call_composition_source(
                projection=wrong_projection, callee_proof=proof,
            )
            new_json(wrong_directory / "projection.json", wrong_projection)
            new_json(wrong_directory / "generated.json", wrong_generated)
            new_bytes(wrong_directory / "CallerComposition.lean", wrong_generated["lean_source"].encode())
            wrong_process, wrong_object = composition._compile_call(
                generated=wrong_generated, callee_object=callee_object, policy=policy,
                scheduler=scheduler, checkpoint=checkpoint, failure_output=wrong_directory,
            )
            new_json(wrong_directory / "process.json", wrong_process)
            new_bytes(wrong_directory / "CallerComposition.olean", wrong_object)
            need(wrong_generated["model_status"] == "model_refuted"
                 and wrong_generated["model_counterexample"] == {"input": 0, "model_output": 2, "required_output": 3},
                 "actual wrong-goal caller refutation differs")
            wrong_summary = {"actual_caller_compiler_returned": True,
                "source_id": wrong_generated["source_id"], "model_status": "model_refuted",
                "model_counterexample": wrong_generated["model_counterexample"],
                "caller_object": pin(wrong_directory / "CallerComposition.olean"),
                "source_callee_proof_origin_verified": False, "source_body_executed": False,
                "proof_authority": False, "cpython_equivalence_proved": False}
            new_json(wrong_directory / "summary.json", wrong_summary)

            # Deliberately violate only the independent target tree. This is
            # negative compiler input, never a manufactured proof record.
            bad_projection = deepcopy(projection)
            bad_projection["native_call_syntax"] = deepcopy(projection["native_call_syntax"]["argument"])
            need([key for key in bad_projection if bad_projection[key] != projection[key]] == ["native_call_syntax"],
                 "negative translation control changed more than the target tree")
            bad_source, _ = composition._lean(bad_projection, proof["result_cid"])
            new_bytes(controls / "TargetMismatch.lean", bad_source.encode())
            negative, negative_receipt = run_control(
                "target-mismatch", {"IntegerLowering.olean": callee_object, "TargetMismatch.lean": bad_source.encode()},
                ["-o", "TargetMismatch.olean", "TargetMismatch.lean"], ("TargetMismatch.olean",),
            )
            diagnostics = negative.stdout + negative.stderr
            need(negative.returncode != 0 and not negative.output_files
                 and "rfl" in diagnostics and "error" in diagnostics.lower()
                 and ("nativeTarget" in diagnostics or "native_call_correspondence" in diagnostics),
                 "actual Lean did not reject the independent caller target mismatch")

            inspect_source = ("import IntegerLowering\nimport CallerComposition\n" + "\n".join(
                "#print axioms CallerComposition." + name for name in positive_generated["theorems"]
            ) + "\n").encode()
            new_bytes(controls / "Inspect.lean", inspect_source)
            axioms, axiom_receipt = run_control("axiom-inventory", {
                "IntegerLowering.olean": callee_object, "CallerComposition.olean": caller_object,
                "Inspect.lean": inspect_source,
            }, ["Inspect.lean"])
            need(axioms.returncode == 0 and not axioms.stderr
                 and all(name in axioms.stdout for name in positive_generated["theorems"])
                 and "sorryAx" not in axioms.stdout and "admit" not in axioms.stdout,
                 "actual caller axiom inventory did not complete without placeholders")

            def cold(expected=qualified):
                return composition.validate_current_call_composition(
                    expected=expected, index=index, repository=repository, expected_head=head,
                    tool_policy=policy, scheduler=scheduler,
                )

            dimensions = json.loads((output / "cache-dimensions.json").read_bytes())
            query = dict(output=output / "candidate-cache", expected=qualified["advisory_cache"],
                root=repository, paths=list(SOURCES), repository_id=REPOSITORY_ID, dimensions=dimensions)
            source_controls = []
            edits = [
                ("callee-edit", "callee.py", SOURCES["callee.py"].replace(b"+ 1", b"+ 4")),
                ("caller-edit", "caller.py", SOURCES["caller.py"].replace(
                    b"increment(increment(n))", b"increment(increment(increment(n)))")),
                ("import-edit", "caller.py", SOURCES["caller.py"].replace(
                    b"from callee import increment", b"from different_callee import increment")),
            ]
            for name, path, changed in edits:
                need(changed != SOURCES[path], "source edit control did not change bytes")
                mutable_bytes(repository / path, changed, 0o644)
                try:
                    refusal = record_refusal(name, cold)
                    miss = cache.lookup_revision_candidate(**query)
                    need(miss["status"] == "miss" and miss["reason"] == "source_changed",
                         "changed source did not invalidate the advisory cache")
                    refusal["cache"] = {"status": miss["status"], "reason": miss["reason"]}
                finally:
                    mutable_bytes(repository / path, SOURCES[path], 0o644)
                originals_check()
                source_controls.append(refusal)
            new_json(controls / "source-edits.json", source_controls)

            header_controls = []
            for field in ("training_steps", "provider_calls"):
                for value in (True, 1):
                    changed = deepcopy(qualified)
                    changed[field] = value
                    rebind(changed)
                    refusal = record_refusal(
                        "header-" + field + "-" + type(value).__name__, lambda changed=changed: cold(changed),
                    )
                    need("zero execution counters" in refusal["reason"], "malformed counter missed header validation")
                    refusal.update(field=field, injected_value=value, parent_file_rewritten=False)
                    header_controls.append(refusal)
            new_json(controls / "malformed-counters.json", header_controls)

            parent_path = output / "result.json"
            child_path = Path(qualified["callee"]["output"]) / "result.json"
            parent_original, child_original = parent_path.read_bytes(), child_path.read_bytes()
            child_controls = []
            for name in ("head-generation", "empty-residuals", "claimed-task-budget", "unsupported-count"):
                changed = deepcopy(qualified)
                child = changed["callee"]
                if name == "head-generation":
                    child["head"]["generation"] += 1
                elif name == "empty-residuals":
                    child["uncovered_source_obligations"] = []
                elif name == "claimed-task-budget":
                    child["original_task_budget_qualified"] = True
                else:
                    child["unsupported_count"] += 1
                rebind(child)
                rebind(changed)
                try:
                    mutable_bytes(child_path, wire(child), 0o600)
                    mutable_bytes(parent_path, wire(changed), 0o600)
                    refusal = record_refusal("child-" + name, lambda changed=changed: cold(changed))
                    need("callee integration header differs" in refusal["reason"]
                         or "callee joins or residuals differ" in refusal["reason"],
                         "rebound child record was not refused at its semantic integration join")
                    child_controls.append(refusal)
                finally:
                    mutable_bytes(child_path, child_original, 0o600)
                    mutable_bytes(parent_path, parent_original, 0o600)
            need(child_path.read_bytes() == child_original and parent_path.read_bytes() == parent_original,
                 "child/parent original JSON bytes were not restored")
            new_json(controls / "rebound-child-records.json", child_controls)

            # Rehydrate a self-consistent native index with one wrong semantic
            # row. Read only its public manifest/exports, not internal DB/CAS.
            metadata_path = output / "metadata"
            storage.validate_codebase_ir_metadata(output=metadata_path, expected=qualified["metadata"])
            manifest = json.loads((metadata_path / "manifest.json").read_bytes())
            records = {}
            for family, declaration in manifest["families"].items():
                export = metadata_path / declaration["export"]["relative_path"]
                need(export == metadata_path / "exports" / (family + ".jsonl"), "native export path differs")
                rows = [json.loads(line) for line in export.read_bytes().splitlines()]
                rows.sort(key=lambda row: row["row_ordinal"])
                need([row["row_ordinal"] for row in rows] == list(range(len(rows))), "native export row order differs")
                records[family] = [row["payload"] for row in rows]
            need(len(records["formal_call_checked_records"]) == 1, "one actual checked-call semantic row required")
            records["formal_call_checked_records"][0]["source_id"] = cid_for_structured({
                "authored_fault_injection": "wrong checked-call semantic source identity"
            })
            metadata_original = controls / "metadata-original-kept"
            metadata_forged = controls / "forged-metadata-retained"
            need(not metadata_original.exists() and not metadata_forged.exists(), "fresh metadata control directories required")
            metadata_path.rename(metadata_original)
            try:
                forged_report = storage.hydrate_codebase_ir_metadata(
                    records=records, source_snapshot=manifest["source_snapshot"], output=metadata_path,
                )
                need(forged_report["fresh_process_readback"]["verified"] is True,
                     "forged semantic index did not pass actual native storage readback")
                changed = deepcopy(qualified)
                changed["metadata"] = forged_report
                rebind(changed)
                mutable_bytes(parent_path, wire(changed), 0o600)
                semantic_index_control = record_refusal("self-consistent-native-metadata", lambda: cold(changed))
                need("stored metadata population differs from regenerated current semantic rows"
                     in semantic_index_control["reason"], "native semantic index corruption missed the population join")
                semantic_index_control.update(
                    actual_native_hydration_returned=True, actual_fresh_process_storage_readback=True,
                    new_prover_invocations=0, mutated_family="formal_call_checked_records",
                    mutated_field="source_id", retained_namespace_relocated_after_control=True,
                )
                new_json(controls / "forged-metadata-report.json", forged_report)
                new_json(controls / "semantic-index-forgery.json", semantic_index_control)
            finally:
                if metadata_path.exists():
                    metadata_path.rename(metadata_forged)
                metadata_original.rename(metadata_path)
                mutable_bytes(parent_path, parent_original, 0o600)

            # Authored callback fault injection: an atomic same-byte replacement
            # must invalidate the original physical source witness.
            original_validate = storage.validate_codebase_ir_metadata
            fired = {"value": False}
            replacement = repository / "caller-replacement.tmp"

            def replace_after_validate(*args, **kwargs):
                report = original_validate(*args, **kwargs)
                if not fired["value"]:
                    fired["value"] = True
                    new_bytes(replacement, SOURCES["caller.py"], mode=0o644)
                    os.replace(replacement, repository / "caller.py")
                return report

            storage.validate_codebase_ir_metadata = replace_after_validate
            try:
                callback_control = record_refusal("same-byte-source-replacement-during-cold-readback", cold)
                need(fired["value"] and "witness changed" in callback_control["reason"],
                     "same-byte callback replacement did not trip the original source witness")
                callback_control.update(authored_callback_fault_injection=True, source_bytes_changed=False,
                                        original_physical_witness_refused=True)
            finally:
                storage.validate_codebase_ir_metadata = original_validate
                if replacement.exists():
                    replacement.unlink()
                mutable_bytes(repository / "caller.py", SOURCES["caller.py"], 0o644)
            originals_check()
            new_json(controls / "same-byte-callback.json", callback_control)

            # This optional generation control has a separate native owner.
            # It never advances the selected experiment's catalog head.
            control_owner = actual / "control-owner"
            control_owner.mkdir(mode=0o700)
            other_connection, other_index = _open(control_owner)
            owner_control = None
            try:
                other_id = REPOSITORY_ID + ":separate-owner-control"
                first = other_index.prepare_current(
                    repository, repository_id=other_id, operation_id="owner-first",
                    expected_head=None, scheduler=scheduler,
                ).head
                mutable_bytes(repository / "callee.py", SOURCES["callee.py"].replace(b"+ 1", b"+ 2"), 0o644)
                second = other_index.prepare_current(
                    repository, repository_id=other_id, operation_id="owner-second",
                    expected_head=first, scheduler=scheduler,
                ).head
                mutable_bytes(repository / "callee.py", SOURCES["callee.py"], 0o644)
                third = other_index.prepare_current(
                    repository, repository_id=other_id, operation_id="owner-restored",
                    expected_head=second, scheduler=scheduler,
                ).head
            except ValueError as error:
                owner_control = {"status": "unsupported", "error_type": type(error).__name__,
                    "reason": str(error)[:4096], "selected_owner_advanced": False,
                    "native_publication_or_control_blocked": True, "proof_authority": False}
            else:
                # Unexpected acceptance is a failed negative control, rather
                # than a publication capability that can be marked unsupported.
                refusal = record_refusal("separate-native-owner-stale-head", lambda: other_index.observe_current(
                    repository, expected_head=first, scheduler=scheduler,
                ))
                need(third.generation > first.generation and first.snapshot_cid == third.snapshot_cid,
                     "native stale-owner control did not preserve source bytes across generations")
                owner_control = {"status": "supported", "first": first.to_dict(), "second": second.to_dict(),
                    "restored": third.to_dict(), "stale_refusal": refusal, "selected_owner_advanced": False}
            finally:
                mutable_bytes(repository / "callee.py", SOURCES["callee.py"], 0o644)
                other_connection.close()
            originals_check()
            new_json(controls / "separate-owner-generation.json", owner_control)

            final_cold = cold()
            need(final_cold["data_validated"] is True and final_cold["cache_status"] == "hit"
                 and final_cold["caller_record_origin_verified"] is False
                 and final_cold["checker_reinvoked"] is False, "final actual cold readback failed")
            need(cache.lookup_revision_candidate(**query)["status"] == "hit", "restored advisory candidate did not replay")
            need(index.current(REPOSITORY_ID).to_dict() == head.to_dict(), "selected native owner head changed")
            index.observe_current(repository, expected_head=head, scheduler=scheduler)
            checkpoint()
            state = scheduler.snapshot()
            need(state["active_lease_count"] == state["waiting_request_count"] == 0, "shared leases leaked")
            native_artifacts_after = [pin(path) for path in sorted(immutable_paths)]
            need(native_artifacts_after == native_artifacts_before, "original native proof/object artifacts changed")
        finally:
            connection.close()

        child = subprocess.run(
            [sys.executable, "-B", str(T / "cold-validate-call-ir.py"), str(actual)],
            cwd=T, env=dict(os.environ), capture_output=True, timeout=120, check=True,
        )
        need(len(child.stdout) <= 4096 and len(child.stderr) <= 8192, "fresh cold process report exceeded bounds")
        new_bytes(actual / "cold-validation.stderr", child.stderr)
        fresh_cold = json.loads(child.stdout)
        need(fresh_cold["data_validated"] is True and fresh_cold["cache_status"] == "hit"
             and fresh_cold["head"] == head.to_dict() and fresh_cold["caller_record_origin_verified"] is False
             and fresh_cold["checker_reinvoked"] is False
             and fresh_cold["new_prover_invocations"] == fresh_cold["active_lease_count"]
             == fresh_cold["waiting_request_count"] == 0,
             "fresh native cold process did not preserve bindings and origin limits")
        new_json(actual / "cold-validation.json", fresh_cold)
        runtime_check()
        originals_check()
        tool_after = {name: pin(Path(policy[name]["path"])) for name in ("python", "lean")}
        need(tool_after == tool_before, "selected native executable bytes changed")
        positive_process = json.loads((actual / "qualified/process.json").read_bytes())
        lean_inventory = [
            {"name": "native-callee-version", "process": proof["lean_certificate"]["version_process"]},
            {"name": "native-callee-lowering", "process": proof["lean_certificate"]["process"]},
            {"name": "positive-caller", "process": positive_process},
            {"name": "wrong-goal-refutation", "process": wrong_process},
            {"name": "negative-target", "process": negative_receipt["process"]},
            {"name": "caller-axiom-inventory", "process": axiom_receipt["process"]},
        ]
        need(len(lean_inventory) == 6 and all(row["process"]["command"][0] == policy["lean"]["path"]
             for row in lean_inventory), "actual selected Lean process inventory differs")
        new_json(actual / "lean-process-inventory.json", lean_inventory)
        # Select named public artifacts from returned descriptors and native
        # manifests only. Never recurse through databases, CAS, or lake bodies.
        public_paths = {path for path in PUBLIC_FILES if path.exists()}
        public_paths.update({Path(__file__).resolve(), T / "cold-validate-call-ir.py", expected_file,
                             actual / "qualified/result.json", T / "actual-qualification.json"})
        for key in ("projection", "generated", "source", "callee_object", "caller_object", "process", "cache_dimensions"):
            public_paths.add(Path(qualified[key]["path"]))
        public_paths.update(immutable_paths)
        child_output = Path(qualified["callee"]["output"])
        public_paths.update({Path(qualified["callee"]["projection"]["path"]),
            child_output / "result.json", child_output / "cache-dimensions.json",
            child_output / "cache-report.json", child_output / "checked-object.olean",
            child_output / "candidate-cache/manifest.json", actual / "qualified/cache-report.json",
            actual / "qualified/candidate-cache/manifest.json"})
        for metadata in (actual / "qualified/metadata", child_output / "metadata",
                         actual / "qualified/candidate-cache/metadata", child_output / "candidate-cache/metadata",
                         metadata_forged):
            retained_manifest = metadata / "manifest.json"
            public_paths.add(retained_manifest)
            retained = json.loads(retained_manifest.read_bytes())
            for family, declaration in retained["families"].items():
                relative = declaration["export"]["relative_path"]
                need(relative == "exports/" + family + ".jsonl", "named metadata export differs")
                public_paths.add(metadata / relative)
            for ordinal, batch in enumerate(retained["batches"]):
                relative = batch["relative_path"]
                need(relative == f"batches/{ordinal:06d}.json", "named metadata batch differs")
                public_paths.add(metadata / relative)
        need(all(path.suffix in {".json", ".jsonl", ".lean", ".olean", ".py", ".stdout", ".stderr"}
                 for path in public_paths), "only explicit public text/proof artifacts may be listed")
        summary = {
            "schema": "terminal-call-ir-public-qualification@1", "qualified": True, "output": str(actual),
            "elapsed_milliseconds": int(1000 * (time.monotonic() - started)), "head": head.to_dict(),
            "caller_result_cid": qualified["result_cid"], "native_callee_result_cid": proof["result_cid"],
            "projection_id": projection["projection_id"], "formal_scope": composition.SCOPE,
            "formal_caller_AST_lowering_proved": True, "formal_dependency_composition_proved": True,
            "native_caller_target_correspondence_proved": True, "native_call_opacity_preserved": True,
            "native_callee_prover_calls": 1, "native_lean_processes": 6,
            "native_lean_process_inventory": pin(actual / "lean-process-inventory.json"),
            "wrong_goal": wrong_summary, "target_mismatch_rejected": True,
            "native_control_receipts": control_receipts, "source_change_controls": source_controls,
            "malformed_counter_controls": header_controls, "rebound_child_controls": child_controls,
            "self_consistent_native_index_control": semantic_index_control,
            "same_byte_callback_control": callback_control, "separate_native_owner_control": owner_control,
            "final_in_process_cold_readback": final_cold, "fresh_process_cold_validation": fresh_cold,
            "coverage": qualified["coverage"], "metadata": qualified["metadata"],
            "original_source_pins_restored": original_sources,
            "native_artifact_pins_before": native_artifacts_before, "native_artifact_pins_after": native_artifacts_after,
            "runtime_source_pins_before": runtime_before,
            "runtime_source_pins_after": [pin(Path(row["path"])) for row in expected],
            "driver_pin_before": driver_before, "driver_pin_after": pin(Path(__file__).resolve()),
            "native_tool_pins_before": tool_before, "native_tool_pins_after": tool_after,
            "public_artifact_paths": sorted(map(str, public_paths)),
            "active_lease_count": 0, "waiting_request_count": 0,
            "source_body_executed": False, "training_steps": 0, "provider_calls": 0,
            "admitted": False, "caller_record_origin_verified": False, **composition.AUTHORITY,
        }
        summary["summary_cid"] = cid_for_structured(summary)
        new_json(T / "actual-qualification.json", summary)
        safe = {"qualified": True, "model_goal": "model_proved", "wrong_goal": "model_refuted",
            "target_mismatch_rejected": True, "cold_cache": fresh_cold["cache_status"],
            "formal_dependency_composition_proved": True, "source_semantics_verified": False,
            "python_import_resolution_proved": False, "cpython_equivalence_proved": False,
            "caller_record_origin_verified": False, "training_steps": 0, "native_lean_processes": 6}
        need(len(wire(safe)) <= 4096, "safe qualification report exceeded bounds")
    print(wire(safe).decode())


if __name__ == "__main__":
    main()
