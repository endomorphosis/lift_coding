"""Cold byte/model/metadata replay, without reviving historical authority."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import stat

from jsonl_io import ROOT, FALSE, inputs, read, write, wire, sha
from jsonl_run import POLICY, FILES, build_base_materials, metadata_records
from jsonl_lean import LEAN_LABELS, build_lean_theory, validate_constraint_lean_evidence
from decoder_lean import DECODER_LABELS, build_decoder_theory, validate_decoder_evidence
from decoder_witnesses import build_decoder_witnesses, EXPECTED_SUMMARY
from observed_files import FILE_PATHS, compare_bundles, reobserve_bundle, validate_bundle, ObservationError

LEAN_LEAVES = {"report.json"} | {
    label + suffix for label in LEAN_LABELS for suffix in (".lean", "-process.json")}
DECODER_LEAVES = {"report.json"} | {
    label + suffix for label in DECODER_LABELS for suffix in (".lean", "-process.json")}
COUNTS = {"total": 30, "accepted": 7, "model_refusal": 9, "file_refusal": 14, "derived_cases": 16}
DECODER_SUMMARY = dict(EXPECTED_SUMMARY)
FAULT_CASES = ("file_changed_after_model", "same_bytes_replacement", "forged_derived_model",
               "plan_changed_after_model", "source_changed_at_exit")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def validate_result(result):
    fields = {"schema", "completed", "policy", "native_head", "source_count", "task_count",
        "file_case_count", "outcome_counts", "all_fixture_expectations_matched", "new_optimizer_updates",
        "external_provider_calls", "source_body_execution", "metadata_original_record_counts",
        "native_capsule_inventory", "decoder_summary", "artifact_pins", "seconds", "peak_rss_kib", *FALSE}
    need(type(result) is dict and set(result) == fields, "closed complete Lean JSONL decoder result required")
    need(result["schema"] == "terminal-lean-jsonl-decoder-experiment@1"
        and result["completed"] is True and wire(result["policy"]) == wire(POLICY),
        "complete original Lean JSONL decoder policy required")
    for key, count in {"source_count": 5, "task_count": 4, "file_case_count": 30,
                       "new_optimizer_updates": 0, "external_provider_calls": 0}.items():
        need(type(result[key]) is int and result[key] == count, "exact work counter required")
    counts = result["outcome_counts"]
    need(type(counts) is dict and set(counts) == set(COUNTS)
        and all(type(counts[key]) is int and counts[key] == count for key, count in COUNTS.items()),
        "exact complete JSONL fixture outcome counts required")
    summary = result["decoder_summary"]
    need(type(summary) is dict and set(summary) == set(DECODER_SUMMARY)
        and all(type(summary[key]) is int and summary[key] == count
                for key, count in DECODER_SUMMARY.items()),
        "exact closed decoder witness summary required")
    need(result["all_fixture_expectations_matched"] is True and result["source_body_execution"] is False
        and all(result[key] is False for key in FALSE), "result promotes unobserved authority")
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    need(wire(CodebaseHead.from_dict(result["native_head"]).to_dict()) == wire(result["native_head"]),
         "complete canonical native head required")
    need(type(result["seconds"]) in {int, float} and math.isfinite(result["seconds"])
        and result["seconds"] >= 0 and type(result["peak_rss_kib"]) is int and result["peak_rss_kib"] >= 0,
        "finite nonnegative diagnostics required")
    for key in ("metadata_original_record_counts", "native_capsule_inventory"):
        need(type(result[key]) is dict and result[key]
            and all(type(k) is str and type(v) is int and v >= 0 for k, v in result[key].items()),
            "closed nonnegative metadata counter map required")


def _directory(path, expected):
    """Inspect only this exact directory inventory; never recurse into a leaf."""
    info = path.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
         and path.resolve(strict=True) == path, "canonical owned artifact directory required")
    need({child.name for child in path.iterdir()} == set(expected),
         "artifact directory has a missing or unknown leaf")


def _case_ids():
    from jsonl_cases import specs
    result = [row["case_id"] for row in specs()]
    need(len(result) == 30 and len(set(result)) == 30
        and all(type(name) is str and Path(name).name == name and name not in {".", ".."}
                for name in result), "exact fixed authored case IDs required")
    return result


def _bundle_inventory(path):
    _directory(path, ("input_data", "output_data"))
    for directory in ("input_data", "output_data"):
        _directory(path / directory, [name.split("/")[1] for name in FILE_PATHS
                                     if name.startswith(directory + "/")])


def _pins(root, pins, expected):
    need(type(pins) is list and len(pins) == len(expected), "complete bounded public artifact pins required")
    names = []
    for row in pins:
        need(type(row) is dict and set(row) == {"relative_path", "bytes", "sha256"},
             "closed public artifact pin required")
        name = row["relative_path"]
        need(type(name) is str and "\\" not in name and all(ord(c) >= 32 for c in name),
             "canonical artifact text required")
        path = Path(name)
        need(not path.is_absolute() and path.as_posix() == name
            and not set(path.parts) & {".", "..", ".git"} and name in expected,
            "closed public core Lean and authored-file artifact scope required")
        need(type(row["bytes"]) is int and 0 <= row["bytes"] <= 32 * 1024**2
            and type(row["sha256"]) is str and len(row["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in row["sha256"]),
            "bounded exact artifact pin required")
        names.append(name)
    need(names == sorted(expected), "complete sorted unique public artifact inventory required")
    acquired, total = {}, 0
    from worker_capture import _read
    for row in pins:
        name = row["relative_path"]
        maximum = 65536 if name.endswith(".jsonl") else 32 * 1024**2
        need(row["bytes"] <= maximum, "artifact exceeds its exact file bound")
        raw = _read(root / name, maximum, empty=row["bytes"] == 0)
        need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "selected public artifact changed")
        total += len(raw)
        need(total <= 128 * 1024**2, "total selected artifact bound exceeded")
        acquired[name] = raw
    return acquired


def artifact_check(output, result):
    need(isinstance(output, Path) and output.is_absolute() and output.resolve(strict=True) == output
        and output.parent == ROOT, "canonical owned selected run required")
    ids = _case_ids()
    _directory(output / "lean", LEAN_LEAVES)
    _directory(output / "decoder-lean", DECODER_LEAVES)
    _directory(output / "file-cases", ids)
    for name in ids:
        _bundle_inventory(output / "file-cases" / name)
    expected = set(FILES) | {"lean/" + name for name in LEAN_LEAVES} | {
        "decoder-lean/" + name for name in DECODER_LEAVES} | {
        "file-cases/" + case + "/" + name for case in ids for name in FILE_PATHS}
    need(len(expected) == 158, "exact 158-leaf public artifact scope required")
    return _pins(output, result["artifact_pins"], expected)


def _fault_artifacts(name, fault, output):
    suffix = "-fault-report.json"
    need(name.endswith(suffix) and name != suffix, "named preceding JSONL fault report required")
    root = ROOT / (name[:-len(suffix)] + "-artifacts")
    _directory(root, FAULT_CASES[:4])
    expected = set()
    for case in FAULT_CASES[:4]:
        _directory(root / case, ("before.json", "after.json", "candidate.json", "current.json", "bundle"))
        _bundle_inventory(root / case / "bundle")
        expected.update(case + "/" + leaf for leaf in ("before.json", "after.json", "candidate.json", "current.json"))
        expected.update(case + "/bundle/" + leaf for leaf in FILE_PATHS)
    acquired = _pins(root, fault["artifact_pins"], expected)
    base = json.loads(read(output / "base-materials.json", 32 * 1024**2))
    contract = base["contract"]
    need(wire(contract["head"]) == wire(fault["native_head"]),
         "fault finite model must bind the selected complete native head")
    from file_model_bridge import build_file_model, validate_file_model, FileModelError
    from jsonl_cases import specs
    chosen = next(row for row in specs() if row["case_id"] == "valid-minimal")
    for case in FAULT_CASES[:4]:
        values = {}
        for leaf in ("before", "after", "candidate", "current"):
            raw = acquired[case + "/" + leaf + ".json"]
            values[leaf] = json.loads(raw)
            need(wire(values[leaf]) == raw, "canonical public fault evidence required")
        before, after, current = (values[key] for key in ("before", "after", "current"))
        bundle_root = root / case / "bundle"
        for observation in (before, after, current):
            validate_bundle(observation)
            need(observation["root"] == str(bundle_root), "fault observation moved outside its authored bundle")
        reobserve_bundle(current, root=bundle_root)
        candidate = values["candidate"]
        need(candidate["case_id"] == "fault-" + case
            and wire(candidate["supplied_metrics"]) == wire(chosen["metrics"]),
            "fault candidate identity and authored metrics differ from the independent recipe")
        arguments = {"contract": contract, "before": before, "after": after,
                     "metrics": chosen["metrics"], "case_id": "fault-" + case}
        rebuilt = build_file_model(**arguments)
        need(rebuilt["evaluation"]["evaluation_passed"] is True, "fault must start from a valid authored finite model")
        comparison = compare_bundles(after, current)
        if case == "forged_derived_model":
            need(comparison["same_file_generations"] is True, "forged-model control must leave file generations unchanged")
            try:
                validate_file_model(candidate, **arguments)
            except FileModelError:
                pass
            else:
                raise ValueError("forged derived model was not independently refused")
        else:
            validate_file_model(candidate, **arguments)
            need(comparison["same_file_generations"] is False, "file control did not change an actual artifact generation")
            try:
                reobserve_bundle(after, root=bundle_root)
            except ObservationError:
                pass
            else:
                raise ValueError("historical fault observation incorrectly regained current authority")
            if case == "same_bytes_replacement":
                need(all(row["bytes_equal"] is True for row in comparison["files"].values()),
                     "replacement control must preserve all four byte payloads")
            elif case == "file_changed_after_model":
                need(comparison["inputs_bytes_equal"] is False, "input fault must change actual input bytes")
            else:
                need(comparison["inputs_bytes_equal"] is True and any(
                    not comparison["files"][path]["bytes_equal"] for path in FILE_PATHS[2:]),
                    "plan fault must change an actual plan byte payload")
    return acquired


def fault_precondition(name, *, output, result, result_raw):
    need(type(name) is str and Path(name).name == name and name not in {".", ".."},
         "owned preceding fault report required")
    raw = read(ROOT / name, 1024**2)
    fault = json.loads(raw)
    expected = {"schema", "qualified", "selected_run", "selected_result_sha256", "native_head", "controls",
        "artifact_pins", "source_restored", "source_body_execution", "external_provider_calls", "new_optimizer_updates", *FALSE}
    need(type(fault) is dict and set(fault) == expected and wire(fault) == raw,
         "closed canonical preceding JSONL faults required")
    need(fault["schema"] == "terminal-jsonl-model-faults@1" and fault["qualified"] is True
        and fault["selected_run"] == output.name and fault["selected_result_sha256"] == sha(result_raw)
        and wire(fault["native_head"]) == wire(result["native_head"]),
        "preceding qualified faults must bind selected result and full native head")
    need(fault["source_restored"] is True and fault["source_body_execution"] is False
        and all(fault[key] is False for key in FALSE)
        and type(fault["external_provider_calls"]) is int and fault["external_provider_calls"] == 0
        and type(fault["new_optimizer_updates"]) is int and fault["new_optimizer_updates"] == 0,
        "native fault scope differs")
    need(type(fault["controls"]) is list and len(fault["controls"]) == len(FAULT_CASES),
         "all exact native JSONL fault controls required")
    for row in fault["controls"]:
        need(type(row) is dict and set(row) == {"case", "rejected", "exception_class", "message"}
            and row["rejected"] is True and type(row["exception_class"]) is str and row["exception_class"]
            and type(row["message"]) is str and row["message"], "closed exact refusal observation required")
    need([row["case"] for row in fault["controls"]] == list(FAULT_CASES), "all exact ordered native fault controls required")
    need(fault["controls"][-1]["exception_class"] == "StaleCodebaseError", "native owner exit refusal required")
    _fault_artifacts(name, fault, output)
    return raw, {"relative_path": name, "bytes": len(raw), "sha256": sha(raw)}


def verify_copied_inputs(output, *, bodies, instructions):
    """Bind the retained whole instruction and source copies at both boundaries."""
    for key, raw in instructions.items():
        need(read(output / "instructions" / key / "instruction.md", 8192) == raw, "whole instruction differs")
    for key, raw in bodies.items():
        need(read(output / "source-repository" / key, 8192) == raw, "whole copied source differs")


def verify(output, fault_name):
    resource.setrlimit(resource.RLIMIT_CPU, (480, 480))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    result_raw = read(output / "result.json", 1024**2)
    result = json.loads(result_raw)
    validate_result(result)
    need(wire(result) == result_raw, "canonical selected result required")
    acquired = artifact_check(output, result)
    fault_raw, fault_pin = fault_precondition(fault_name, output=output, result=result, result_raw=result_raw)
    corpus, bodies, instructions, lineage = inputs()
    need(wire(corpus) == acquired["corpus-manifest.json"] and wire(lineage) == acquired["lineage.json"]
        and wire(POLICY) == acquired["policy.json"], "selected public input lineage or policy differs")
    verify_copied_inputs(output, bodies=bodies, instructions=instructions)
    structural = json.loads(acquired["structural-report.json"])
    from native_structural_ir import verify_structural_ir, _scheduler, _owner
    verify_structural_ir(repository=output / "source-repository", output=output / "structural", expected=structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import verify_native_capsules
    from capsule_codec import build_capsule_codec
    from capsule_run import check_lease
    from file_case_run import validate_file_case_run
    from metadata_projections import _wire as metadata_wire
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as native_metadata
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
    native = json.loads(acquired["native-capsules.json"])
    codecs = json.loads(acquired["codec-views.json"])
    lean = json.loads(acquired["lean-evidence.json"])
    decoder_evidence = json.loads(acquired["decoder-evidence.json"])
    metadata = json.loads(acquired["metadata-report.json"])
    filecases = json.loads(acquired["file-case-report.json"])
    with _scheduler().acquire(ResourceLane.VALIDATION, cpu_slots=1, memory_mb=2048, child_process_slots=1,
            timeout=30, request_id="terminal-jsonl-model:cold-replay") as lease:
        head = CodebaseHead.from_dict(structural["head"])
        with _owner(output / "structural", existing=True) as (index, _):
            index.observe_current(output / "source-repository", expected_head=head, parent_lease=lease,
                admission_timeout_seconds=20, timeout_seconds=120, memory_mb=256)
            verify_native_capsules(CodebaseIRManifest.from_dict(structural["manifest"]), head, native)
            for source in structural["sources"]:
                for arm in ("minified", "aliased"):
                    rebuilt = build_capsule_codec(bodies[source["path"]], source["path"], source["source_cid"],
                        structural["head"], aliases=arm == "aliased")
                    need(wire(rebuilt) == wire(codecs[source["path"]][arm]), "complete byte codec replay differs")
            base = build_base_materials(output=output, structural=structural, corpus=corpus,
                                       bodies=bodies, instructions=instructions, lease=lease)
            need(wire(base) == acquired["base-materials.json"], "deterministic current-source base material replay differs")
            rebuilt_cases = validate_file_case_run(filecases, output=output / "file-cases", contract=base["contract"])
            theory = build_lean_theory(contract=base["contract"], cases=rebuilt_cases["derived_cases"])
            need(wire(theory) == acquired["lean-theory.json"], "byte-derived finite Lean theory replay differs")
            validate_constraint_lean_evidence(lean, theory=theory, output=output / "lean")
            witnesses = build_decoder_witnesses(filecases=rebuilt_cases)
            need(wire(witnesses) == acquired["decoder-witnesses.json"],
                 "exact retained JSONL byte-to-row decoder witnesses differ")
            decoder_theory = build_decoder_theory(witnesses=witnesses)
            need(wire(decoder_theory) == acquired["decoder-theory.json"],
                 "exact byte-to-row decoder Lean theory replay differs")
            validate_decoder_evidence(decoder_evidence, theory=decoder_theory,
                                      output=output / "decoder-lean")
            index.observe_current(output / "source-repository", expected_head=head, parent_lease=lease,
                admission_timeout_seconds=20, timeout_seconds=120, memory_mb=256)
        records = metadata_records(structural=structural, bodies=bodies, instructions=instructions,
            corpus=corpus, native=native, codecs=codecs, lineage=lineage, base=base,
            filecases=rebuilt_cases, theory=theory, lean=lean, witnesses=witnesses,
            decoder_theory=decoder_theory, decoder_evidence=decoder_evidence)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE, cpu_slots=1, memory_mb=256, child_process_slots=1,
                timeout=20, request_id="terminal-jsonl-model:cold-metadata") as child:
            check_lease(child)
            reopened = native_metadata.validate_codebase_ir_metadata(output=output / "metadata",
                expected=metadata["native_metadata"], fresh_process=True)
        restored = {family: [json.loads(line)["payload"] for line in read(
            output / "metadata" / entry["relative_path"], 32 * 1024**2).splitlines()]
            for family, entry in reopened["exports"].items()}
        recovered = reconstruct_terminal_codebase_metadata_records(restored)
        need(metadata_wire(recovered) == metadata_wire(records)
            and sha(metadata_wire(recovered)) == metadata["records_sha256"],
            "complete fresh-process metadata reconstruction differs")
    need(wire(result["native_head"]) == wire(structural["head"])
        and wire(result["metadata_original_record_counts"]) == wire(metadata["family_counts"])
        and wire(result["native_capsule_inventory"]) == wire(native["complete_inventory"]),
        "result source and metadata inventories differ")
    need(result["file_case_count"] == len(rebuilt_cases["entries"])
        and wire(result["outcome_counts"]) == wire(rebuilt_cases["counts"]), "result counters differ from byte replay")
    need(wire(result["decoder_summary"]) == wire(witnesses["summary"]),
         "result decoder summary differs from independent byte-witness replay")
    verify_structural_ir(repository=output / "source-repository", output=output / "structural", expected=structural)
    verify_copied_inputs(output, bodies=bodies, instructions=instructions)
    # Final actual AFTER observations, full selected artifacts, and qualified
    # fault artifacts are rechecked after the fresh metadata subprocess exits.
    validate_file_case_run(filecases, output=output / "file-cases", contract=base["contract"])
    end_fault, end_pin = fault_precondition(fault_name, output=output, result=result, result_raw=result_raw)
    need(artifact_check(output, result) == acquired and read(output / "result.json", 1024**2) == result_raw
        and end_fault == fault_raw and end_pin == fault_pin and inputs()[3] == lineage,
        "selected evidence changed during cold replay")
    return {"schema": "terminal-lean-jsonl-decoder-cold-replay@1", "qualified": True, "selected_run": output.name,
        "selected_result_sha256": sha(result_raw), "selected_native_head": structural["head"],
        "selected_artifact_pins_sha256": sha(wire(result["artifact_pins"])), "preceding_fault_report": fault_pin,
        "qualified_faults_verified_before_positive_replay": True, "complete_metadata_reopened": True,
        "current_owner_entry_and_exit_observed": True, "source_bound_base_materials_rebuilt": True,
        "all_actual_after_file_generations_reobserved": True, "strict_jsonl_rows_and_models_rebuilt": True,
        "lean_evidence_verified_as_historical_finite_model_proofs": True,
        "decoder_witnesses_rebuilt_from_retained_actual_file_bytes": True,
        "decoder_theory_rebuilt": True, "decoder_lean_evidence_verified_as_historical": True,
        "decoder_summary": witnesses["summary"],
        "file_cases_replayed": len(rebuilt_cases["entries"]), "all_fixture_expectations_matched": True,
        "original_task_satisfaction_verified": False, "new_lean_compiler_invocations": 0,
        "external_provider_calls": 0, "source_body_execution": False, **FALSE}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--fault-report", required=True)
    args = parser.parse_args()
    for name in (args.run, args.report, args.fault_report):
        need(Path(name).name == name and name not in {".", ".."}, "owned local names required")
    result = verify(ROOT / args.run, args.fault_report)
    write(ROOT / args.report, result)
    print(json.dumps({"qualified": True, "cold_replay": True}))
