"""Fresh-process exact native source/head/cache and conditional model replay."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from align_projection import evaluate_alignment, validate_alignment_projection
from intent_structural_grounding import build_grounding
from native_structural_ir import verify_structural_ir
from proof_index import lookup_current_proof
from train_codebase_ir import read, write
from run_successor import POLICY

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "terminal-codebase-ir-training-20261014-01"


def validate_result_scope(result):
    if (result.get("schema") != "terminal-typed-ir-proof-experiment@1" or result.get("completed") is not True
            or result.get("policy") != POLICY):
        raise ValueError("exact completed successor schema and finite policy required")
    for key in ("native_full_supervisor_invoked", "source_to_model_runtime_equivalence_proved",
                "training_convergence_proved", "full_task_satisfaction_proved", "provider_token_savings_measured"):
        if result.get(key) is not False:
            raise ValueError("promoted or missing result scope claim")
    grounding = result["intent_grounding"]
    if (grounding["status"] != "structural_nomination_with_blocked_partial_plan"
            or grounding["partial_plan"]["status"] != "blocked_partial_instruction_coverage"
            or grounding["partial_plan"]["coverage"]["accepted"] is not False
            or not any(row["code"] == "unsupported_source_units"
                       for row in grounding["partial_plan"]["coverage"]["errors"])):
        raise ValueError("unresolved original instruction must retain actual native coverage refusal")


def load(path):
    return json.loads(read(path, 32_000_000))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    output = args.experiment.absolute()
    result_path = output / "result.json"
    original = read(result_path, 32_000_000)
    result = json.loads(original)
    validate_result_scope(result)
    repository = output / "source-repository"
    structural = result["structural"]
    before = verify_structural_ir(repository=repository, output=output / "structural", expected=structural)
    projection, proof = result["alignment_projection"], result["alignment_proof"]
    name = projection["source"]["path"]
    validate_alignment_projection(source_bytes=read(repository / name, 8192), source_path=name,
        source_sha256=projection["source"]["sha256"], expected=projection)
    looked_up = lookup_current_proof(output=output / "proof-index", repository=repository,
        structural_output=output / "structural", structural_report=structural, projection=projection, proof_report=proof)
    if looked_up != result["proof_lookup"]:
        raise ValueError("exact cache/certificate/current-source replay differs")
    # Independent closed mathematical reference, not an import of repository
    # functions. Cover negative values and granularity boundaries explicitly.
    inputs = [-4097, -4096, -4095, -129, -128, -127, -65, -64, -63, -1, 0, 1,
              63, 64, 65, 127, 128, 129, 4095, 4096, 4097]
    rows = []
    for number in inputs:
        quotient, remainder = divmod(number, 64)
        expected = 64 * (quotient + (1 if remainder else 0))
        found = evaluate_alignment(projection=projection, x=number, granularity=64)
        if found != expected or not (number <= found < number + 64 and found % 64 == 0):
            raise ValueError("independent mathematical boundary control differs")
        rows.append({"input": number, "model_output": found, "reference_output": expected})
    records = [{"path": row["path"], "sha256": row["sha256"],
                "source_text": read(repository / row["path"], 8192).decode()} for row in structural["sources"]]
    text = read(PRIOR / "experiment-05" / "captured-sources" / "headless-terminal/instruction.md").decode()
    grounding = build_grounding(instruction_text=text, instruction_sha256=hashlib.sha256(text.encode()).hexdigest(),
        source_records=records, structural_manifest=structural["manifest"], alignment_projection=projection)
    if grounding != result["intent_grounding"]:
        raise ValueError("native IntentIR/whole-instruction residual replay differs")
    from benchmarks.agent_supervisor.container_coding.codebase_ir_metadata import validate_codebase_ir_metadata
    metadata = result["metadata"]["native_metadata"]
    validate_codebase_ir_metadata(output=output / "metadata", expected=metadata, fresh_process=True)
    after = verify_structural_ir(repository=repository, output=output / "structural", expected=structural)
    if before != after or read(result_path, 32_000_000) != original:
        raise ValueError("source/head or original result changed during cold replay")
    write(args.report.absolute(), {"schema": "terminal-typed-ir-proof-cold-readback@1", "qualified": True,
        "structural": before, "proof_lookup": looked_up, "mathematical_controls": rows,
        "intent_grounding_exact": True, "native_duckdb_ducklake_restart_exact": True,
        "source_body_execution": False, "training_steps": 0,
        "source_to_model_runtime_equivalence_proved": False, "full_task_satisfaction_proved": False,
        "training_convergence_proved": False, "provider_token_savings_measured": False})
    print(json.dumps({"qualified": True, "source_files": before["source_files"],
                      "mathematical_boundary_controls": len(rows)}))


if __name__ == "__main__":
    main()
