"""Inventory the pinned ranker AST without importing or executing its source.

AST identity and an exact-real expression projection are distinct from a proved
Python interpreter, binary64 refinement, and full source-to-model equivalence.
"""
import ast
import collections
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
SOURCE = WORKSPACE / "artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py"
EXPECTED = "3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a"
FUNCTIONS = {
    "_prepare": "9ff2e5ae2f4603654a98f7ae7b56363e689b27063e8615c80d5865534ae85ecd",
    "_dot": "3ff8d47ab6f2e375b3bd4b81c6a39e364cd5a15ec859ca383b5e41504250de1e",
    "_objective": "129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2",
    "train_terminal_codebase_intent_ranker": "5b87aa5ce21daf1439ed8d51f37557e6aba962130fd4f8732d149cea7ca2ac5a",
}


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    before = pin(SOURCE)
    assert before["bytes"] == 16391 and before["sha256"] == EXPECTED
    tree = ast.parse(SOURCE.read_bytes(), filename=str(SOURCE))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    rows = []
    for name, expected in FUNCTIONS.items():
        node = functions[name]
        dump = ast.dump(node, include_attributes=False)
        assert hashlib.sha256(dump.encode()).hexdigest() == expected
        rows.append({"function": name, "line": node.lineno, "end_line": node.end_lineno,
                     "AST_sha256": expected, "AST": dump,
                     "AST_node_counts": dict(collections.Counter(type(item).__name__ for item in ast.walk(node))),
                     "call_shapes": sorted({ast.unparse(item.func) for item in ast.walk(node) if isinstance(item, ast.Call)})})
    assert pin(SOURCE) == before
    result = {"schema": "ranker-source-model-obligation-binding@1", "status": "AST_identified_semantic_preservation_open",
              "source": before, "producer": pin(Path(__file__).resolve()),
              "functions": rows, "source_source_execution_calls": 0,
              "source_AST_shapes_matched": True, "source_interpreter_theorem_proved": False,
              "original_model_dimensions": {"training_pairs": 4, "coordinates": 80},
              "candidate_real_expression_projection": {
                  "loss": "max(0,-z) + log(1+exp(-abs(z)))",
                  "factor": "if z >= 0 then exp(-z)/(1+exp(-z)) else 1/(1+exp(z))",
                  "gradient": "mu*w_j - (1/n)*sum_i factor(dot(w,d_i))*d_ij",
                  "step": "w_j - eta*gradient_j",
                  "projection_role": "Manually specified exact-real expressions matched to the pinned AST; not a semantics-preserving Python translation theorem",
                  "stored_mu_is_exact_binary64_embedding": True},
              "remaining_semantic_obligations": [
                  "Python evaluation order, comprehension and zip cardinalities, indexing and exception behavior",
                  "Binary64 multiplication, addition, subtraction and division at each source operation",
                  "math.fsum error and accumulation semantics rather than replacing it by a real sum without proof",
                  "math.exp/log1p/sqrt implementation and stable-branch underflow/overflow behavior",
                  "Exact validation and feature preparation semantics, including corpus role filtering and source snapshot joins",
                  "Training loop, receipt/hash construction and all native intermediate states",
                  "Independent Terminal Bench behavior/task validators and full requested intent"],
              "binary64_error_bound_proved": False, "python_ranker_source_equivalence_proved": False,
              "global_autoencoder_convergence_proved": False, "full_task_satisfaction": "unknown",
              "proof_authority": False, "execution_authority": False,
              "completion_authority": False, "planner_activation": False}
    target = ROOT / "source-model-obligations-01.json"
    with target.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"receipt": pin(target), "source_AST_functions": len(rows), "status": result["status"]}))


if __name__ == "__main__":
    main()
