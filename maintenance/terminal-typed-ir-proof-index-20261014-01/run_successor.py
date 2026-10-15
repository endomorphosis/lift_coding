"""Prepare exact public source projection and run typed IR/checker experiments."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from train_codebase_ir import read, wire, write

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "terminal-codebase-ir-training-20261014-01"
BASELINE = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout"
DATASETS = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10" / "datasets" / "ipfs_datasets_py"
LEAN = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
POLICY = {"schema": "terminal-typed-ir-proof-experiment-policy@1",
    "source_files": 5, "source_bytes": 15788, "max_file_bytes": 8192,
    "source_repository_scope": "nested_git_root_named_source_files_only",
    "source_execution": False, "training_steps": 0, "provider_calls_permitted": 0,
    "native_codebase_admission": True, "admission_timeout_seconds": 30,
    "native_preparation_timeout_seconds": 120, "reserved_memory_mb": 256,
    "cpu_seconds_hard_limit": 180, "address_space_bytes_hard_limit": 8 * 1024**3,
    "outer_deadline_seconds": 300, "duckdb_threads": 1, "lean_threads": 1,
    "proof_scope": "source_bound_closed_mathematical_integer_alignment_model",
    "cpython_equivalence_proved": False, "whole_program_equivalence_proved": False,
    "training_convergence_proved": False, "full_task_satisfaction_proved": False,
    "provider_token_savings_measured": False, "global_durable_task_budget": False}


def pin(path):
    body = read(path, 32_000_000)
    return {"path": str(path), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def git(repository, *arguments):
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null",
        "-c", "commit.gpgsign=false", *arguments], cwd=repository, text=True,
        stderr=subprocess.PIPE, timeout=30).strip()


def capture_source_repository(output, manifest):
    require_sources = {item["path"]: item["sha256"] for task in manifest["tasks"] for item in task["sources"]}
    expected_paths = {"headless-terminal/environment/base_terminal.py", "feal-differential-cryptanalysis/environment/feal.py",
        "break-filter-js-from-html/environment/filter.py",
        "llm-inference-batching-scheduler/environment/task_file/scripts/baseline_packer.py",
        "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py"}
    if set(require_sources) != expected_paths:
        raise ValueError("exact five public source inputs required")
    original = PRIOR / "experiment-05" / "captured-sources"
    bodies = {}
    records = []
    for name, digest in sorted(require_sources.items()):
        body = read(original / name, 8192)
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError("sealed public source drift")
        bodies[name] = body
        records.append({"path": name, "sha256": digest, "source_text": body.decode("utf-8")})
    if sum(map(len, bodies.values())) != 15788:
        raise ValueError("exact public source byte membership required")
    repository = output / "source-repository"
    repository.mkdir(mode=0o700)
    for name, body in bodies.items():
        target = repository / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    git(repository, "init", "-q")
    git(repository, "add", "--", *sorted(bodies))
    git(repository, "-c", "user.name=Codebase IR experiment", "-c", "user.email=codebase-ir@localhost",
        "commit", "-qm", "Exact public Terminal Bench source projection")
    if Path(git(repository, "rev-parse", "--show-toplevel")) != repository:
        raise ValueError("native snapshot must own an exact nested Git root")
    if set(git(repository, "ls-files").splitlines()) != set(bodies) or git(repository, "status", "--porcelain"):
        raise ValueError("source-only isolated repository membership differs")
    write(output / "capture.json", {"schema": "terminal-public-source-projection@1",
        "repository": str(repository), "projection_git_commit": git(repository, "rev-parse", "HEAD"),
        "original_terminal_bench_commit": manifest["repository"]["head"],
        "source_records": [{k: v for k, v in record.items() if k != "source_text"} for record in records],
        "instructions_in_repository": False, "hidden_inputs": False, "source_execution": False})
    return repository, require_sources, records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.exists() or output.resolve() != output:
        raise ValueError("fresh canonical successor experiment required")
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    from native_structural_ir import prepare_structural_ir, verify_structural_ir
    from align_projection import project_alignment, compile_alignment_proofs, validate_alignment_projection
    from intent_structural_grounding import build_grounding
    from proof_index import create_proof_index, lookup_current_proof
    from metadata_projections import hydrate_and_verify_records
    output.mkdir(mode=0o700)
    write(output / "policy.json", POLICY)
    started = time.monotonic()
    try:
        manifest = json.loads(read(PRIOR / "corpus-manifest-01.json"))
        repository, expected_sources, source_records = capture_source_repository(output, manifest)
        print(json.dumps({"stage": "native_structural_preparation_start", "files": len(expected_sources)}), flush=True)
        structural = prepare_structural_ir(repository=repository, output=output / "structural",
            repository_id="terminal-five-public:" + output.name, expected_sources=expected_sources)
        write(output / "structural-report.json", structural)
        print(json.dumps({"stage": "native_structural_preparation_complete"}), flush=True)
        name = "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py"
        source = read(repository / name, 8192)
        baseline_path = "llm-inference-batching-scheduler/environment/task_file/scripts/baseline_packer.py"
        baseline = read(repository / baseline_path, 8192)
        declared = [node for node in ast.parse(baseline.decode()).body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "GRAN"]
        if len(declared) != 1 or not isinstance(declared[0].value, ast.Constant) or type(declared[0].value.value) is not int or declared[0].value.value != 64:
            raise ValueError("closed alignment property requires exact source-declared GRAN=64")
        write(output / "granularity-source-binding.json", {"source_path": baseline_path,
            "source_sha256": expected_sources[baseline_path], "declared_name": "GRAN", "declared_value": 64,
            "line": declared[0].lineno, "ast_sha256": hashlib.sha256(ast.dump(declared[0], include_attributes=False).encode()).hexdigest(),
            "scope": "source_syntax_only_runtime_constant_value_unproved", "proof_authority": False})
        projection = project_alignment(source_bytes=source, source_path=name, source_sha256=expected_sources[name])
        write(output / "alignment-projection.json", projection)
        proof = compile_alignment_proofs(projection=projection, output=output / "alignment-proofs", lean_executable=LEAN)
        write(output / "alignment-proof-report.json", proof)
        validate_alignment_projection(source_bytes=read(repository / name, 8192), source_path=name,
            source_sha256=expected_sources[name], expected=projection)
        print(json.dumps({"stage": "alignment_lean_complete"}), flush=True)
        instruction = next(task["instruction"] for task in manifest["tasks"] if task["task_id"] == "headless-terminal")
        raw = read(PRIOR / "experiment-05" / "captured-sources" / instruction["path"])
        if hashlib.sha256(raw).hexdigest() != instruction["sha256"]:
            raise ValueError("sealed original instruction drift")
        grounding = build_grounding(instruction_text=raw.decode("utf-8"), instruction_sha256=instruction["sha256"],
            source_records=source_records, structural_manifest=structural["manifest"], alignment_projection=projection)
        write(output / "intent-grounding.json", grounding)
        verified = verify_structural_ir(repository=repository, output=output / "structural", expected=structural)
        indexed = create_proof_index(output=output / "proof-index", structural_report=structural,
            projection=projection, proof_report=proof)
        write(output / "proof-index-report.json", indexed)
        lookup = lookup_current_proof(output=output / "proof-index", repository=repository,
            structural_output=output / "structural", structural_report=structural,
            projection=projection, proof_report=proof)
        write(output / "proof-lookup.json", lookup)
        families = {"typed_codebase_ir": [structural], "typed_arithmetic_projection": [projection],
            "conditional_logic_proofs": [proof], "proof_index": [indexed], "proof_lookups": [lookup],
            "intent_grounding": [grounding], "source_bindings": [{k: v for k, v in row.items() if k != "source_text"}
                for row in source_records], "contracts": [{"task_id": "headless-terminal",
                    "instruction_text": raw.decode(), "instruction_sha256": instruction["sha256"],
                    "status": "unresolved_behavioral_requirements", "proof_authority": False}],
            "ast": [{"manifest": structural["manifest"], "authority": "structural_only"}],
            "kg": [{"semantic_state": structural["manifest"]["semantic_state"], "authority": "structural_only"}],
            "vectors": [{"status": "prior_advisory_models_unchanged_not_retrained",
                "prior_result_sha256": pin(PRIOR / "experiment-05" / "result.json")["sha256"], "proof_authority": False}]}
        metadata = hydrate_and_verify_records(records=families, output=output / "metadata",
            source_snapshot={"schema": "typed-codebase-ir-proof-source-snapshot@1",
                "head": structural["head"], "capture_sha256": pin(output / "capture.json")["sha256"],
                "original_instruction_sha256": instruction["sha256"], "policy": POLICY})
        write(output / "metadata-report.json", metadata)
        final_observation = verify_structural_ir(repository=repository, output=output / "structural", expected=structural)
        if final_observation != verified:
            raise ValueError("native structural observation drift after metadata")
        write(output / "result.json", {"schema": "terminal-typed-ir-proof-experiment@1", "completed": True,
            "structural": structural, "alignment_projection": projection, "alignment_proof": proof,
            "intent_grounding": grounding, "proof_index": indexed, "proof_lookup": lookup,
            "metadata": metadata, "seconds": time.monotonic() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "policy": POLICY, "native_full_supervisor_invoked": False,
            "source_to_model_runtime_equivalence_proved": False, "training_convergence_proved": False,
            "full_task_satisfaction_proved": False, "provider_token_savings_measured": False})
        print(json.dumps({"stage": "successor_experiment_complete"}), flush=True)
    except Exception as error:
        write(output / "failure.json", {"completed": False, "error_type": type(error).__name__, "error": str(error),
            "source_to_model_runtime_equivalence_proved": False, "full_task_satisfaction_proved": False})
        raise


if __name__ == "__main__":
    main()
