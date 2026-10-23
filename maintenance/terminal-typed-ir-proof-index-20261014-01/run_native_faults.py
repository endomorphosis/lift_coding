"""Exercise genuine current-source/head refusals on owned benchmark projections."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from native_structural_ir import prepare_structural_ir, verify_structural_ir, _owner, _scheduler
from proof_index import create_proof_index, lookup_current_proof
from run_successor import capture_source_repository, PRIOR
from train_codebase_ir import read, write
from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseScanLimits, StaleCodebaseError
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    experiment, output = args.experiment.absolute(), args.output.absolute()
    if output.exists() or output.resolve() != output:
        raise ValueError("fresh owned native-fault namespace required")
    output.mkdir(mode=0o700)
    result = json.loads(read(experiment / "result.json", 32_000_000))
    structural = result["structural"]
    projection, proof = result["alignment_projection"], result["alignment_proof"]
    request = dict(output=experiment / "proof-index", repository=experiment / "source-repository",
        structural_output=experiment / "structural", structural_report=structural,
        projection=projection, proof_report=proof)
    before = lookup_current_proof(**request)
    source_path = request["repository"] / projection["source"]["path"]
    original = read(source_path, 8192)
    mutation = original.replace(b"((x + g - 1) // g) * g", b"((x + g - 2) // g) * g", 1)
    if mutation == original:
        raise ValueError("exact original alignment expression required for source fault")
    write(output / "source-mutation-control.json", {"source_path": str(source_path),
        "original_sha256": hashlib.sha256(original).hexdigest(), "mutated_sha256": hashlib.sha256(mutation).hexdigest(),
        "scope": "owned_temporary_source_change_restored_after_refusal"})
    rejected = None
    try:
        source_path.write_bytes(mutation)
        try:
            lookup_current_proof(**request)
        except StaleCodebaseError as error:
            rejected = {"type": type(error).__name__, "message": str(error)}
        if rejected is None:
            raise ValueError("changed actual source did not trigger exact native stale-source refusal")
    finally:
        with source_path.open("wb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
    restored = lookup_current_proof(**request)
    if restored != before or read(source_path, 8192) != original:
        raise ValueError("owned original source/cache did not restore exactly")
    write(output / "source-fault-result.json", {"qualified": True, "native_refusal": rejected,
        "exact_original_source_restored": True, "current_lookup_restored": True,
        "proof_authority": False, "execution_authority": False})
    other_path = request["repository"] / "headless-terminal/environment/base_terminal.py"
    other_original = read(other_path, 8192)
    other_refusal = None
    try:
        other_path.write_bytes(other_original + b"\n# Owned non-alignment source-drift control.\n")
        try:
            lookup_current_proof(**request)
        except StaleCodebaseError as error:
            other_refusal = {"type": type(error).__name__, "message": str(error)}
        if other_refusal is None:
            raise ValueError("historical alignment cache accepted changed indexed BaseTerminal source")
    finally:
        with other_path.open("wb") as stream:
            stream.write(other_original)
            stream.flush()
            os.fsync(stream.fileno())
    if lookup_current_proof(**request) != before:
        raise ValueError("main current lookup did not restore after cross-file source control")
    write(output / "other-source-fault-result.json", {"qualified": True, "source_path": str(other_path),
        "native_refusal": other_refusal, "alignment_source_unchanged": True,
        "original_other_source_restored": True, "historical_grounding_is_current_authority": False})
    manifest = json.loads(read(PRIOR / "corpus-manifest-01.json"))
    repository, expected_sources, _ = capture_source_repository(output, manifest)
    probe = prepare_structural_ir(repository=repository, output=output / "structural",
        repository_id="terminal-five-public:generation-fault:" + output.name, expected_sources=expected_sources)
    create_proof_index(output=output / "proof-index", structural_report=probe, projection=projection, proof_report=proof)
    probe_request = dict(output=output / "proof-index", repository=repository, structural_output=output / "structural",
        structural_report=probe, projection=projection, proof_report=proof)
    lookup_current_proof(**probe_request)
    head = CodebaseHead.from_dict(probe["head"])
    with _owner(output / "structural", existing=True) as (index, _):
        receipt = index.prepare_current(repository, repository_id=head.repository_id,
            operation_id="same-source-generation-02", expected_head=head,
            limits=CodebaseScanLimits(max_entries=5, max_file_bytes=8192),
            scheduler=_scheduler(), memory_mb=256, admission_timeout_seconds=30, timeout_seconds=120)
        actual_head = index.current(head.repository_id)
    if (actual_head != receipt.head or receipt.head.generation != head.generation + 1
            or receipt.head.snapshot_cid != head.snapshot_cid or receipt.head.manifest_cid != head.manifest_cid):
        raise ValueError("actual same-content native publication transition differs")
    rejected_head = None
    try:
        lookup_current_proof(**probe_request)
    except StaleCodebaseError as error:
        rejected_head = {"type": type(error).__name__, "message": str(error)}
    if rejected_head is None:
        raise ValueError("old complete head accepted despite real native generation change")
    write(output / "generation-fault-result.json", {"qualified": True, "old_head": head.to_dict(),
        "new_head": receipt.head.to_dict(), "same_snapshot_cid": True, "same_manifest_cid": True,
        "native_refusal": rejected_head, "old_conditional_record_retained_historical": True,
        "main_experiment_head_mutated": False, "proof_authority": False, "execution_authority": False})
    write(output / "result.json", {"schema": "terminal-native-codebase-proof-fault-checks@1", "qualified": True,
        "source_drift_refused": True, "same_content_new_generation_refused": True,
        "non_alignment_source_drift_refused": True,
        "original_source_restored": True, "main_experiment_head_mutated": False,
        "provider_calls": 0, "source_body_execution": False, "training_steps": 0,
        "proof_authority": False, "full_task_satisfaction_proved": False})
    print(json.dumps({"qualified": True, "source_drift_refused": True, "same_content_new_generation_refused": True}))


if __name__ == "__main__":
    main()
