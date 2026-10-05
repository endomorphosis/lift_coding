"""Evaluate public formulas on authored requests; no benchmark instance reads."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path("source").resolve()))
from cost_model import CostModel
from reference import build_global_shape_contract_reference

paths = [Path("task_file/input_data") / f"requests_bucket_{i}.jsonl" for i in (1, 2)]
before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
buckets = [[json.loads(line) for line in path.read_text().splitlines()] for path in paths]
assert len(buckets) == 2 and all(len(bucket) == 8 for bucket in buckets)
assert [r["prompt_len"] for r in buckets[0]] == list(range(64, 513, 64))
assert [r["prompt_len"] for r in buckets[1]] == list(range(576, 1025, 64))
assert all(r["gen_len"] == 1 for bucket in buckets for r in bucket)
assert len({r["request_id"] for bucket in buckets for r in bucket}) == 16
reference = build_global_shape_contract_reference(buckets)
plans = reference["plans"]
shapes = set()
batch_shapes = {}
exact_once = True
coverage = True
batch_consistency = True
for bucket, plan in zip(buckets, plans):
    requests = {row["request_id"]: row for row in bucket}
    exact_once &= Counter(row["request_id"] for row in bucket) == Counter(row["request_id"] for row in plan)
    for row in plan:
        shape = row["shape"]
        triple = tuple(shape[key] for key in ("seq_align", "heads_align", "hidden_align"))
        request = requests[row["request_id"]]
        coverage &= all(type(component) is int for component in triple)
        coverage &= triple[0] % 64 == 0 and triple[0] >= ((request["prompt_len"] + 63) // 64) * 64
        coverage &= triple[1:] == (32, 4096)
        old = batch_shapes.setdefault(row["batch_id"], triple)
        batch_consistency &= old == triple
        shapes.add(triple)
structural = {"included_exactly_once": bool(exact_once), "aligned_and_covering_shapes": bool(coverage),
              "global_at_most_eight_shapes": len(shapes) <= 8,
              "consistent_shape_within_each_batch": bool(batch_consistency)}
thresholds = ({"cost": 3.0e11, "pad_ratio": 0.055, "p95_latency_ms": 2.1e6, "sequential_timecost": 2.7e8},
              {"cost": 4.8e10, "pad_ratio": 0.15, "p95_latency_ms": 2.1e5, "sequential_timecost": 3.2e7})
predictions = ({"cost": 313580032, "pad_ratio": 0, "p95_latency_ms": 6234.784, "sequential_timecost": 16747.136},
               {"cost": 1548802560, "pad_ratio": 0, "p95_latency_ms": 13024.3136, "sequential_timecost": 41388.672})
model = CostModel(granularity=64)
results = []
comparisons = []
for index, (bucket, plan, bounds, predicted) in enumerate(zip(buckets, plans, thresholds, predictions), 1):
    metrics = model.plan_metrics({row["request_id"]: row for row in bucket}, plan)
    results.append({"bucket": index, "metrics": metrics, "batch_count": len({row["batch_id"] for row in plan})})
    for key, bound in bounds.items():
        value = metrics[key]
        assert type(value) in (float, int) and math.isfinite(value)
        comparisons.append({"bucket": index, "metric": key, "observed_binary64": float(value),
                            "threshold_binary64": float(bound), "comparison": "strictly_less_than",
                            "passed": value < bound, "source_derived_prediction": predicted[key],
                            "prediction_matches_observation": math.isclose(value, predicted[key], rel_tol=1e-12, abs_tol=1e-6)})
    out = Path("task_file/output_data") / f"plan_b{index}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in plan))
after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
frame = before == after
assert len(comparisons) == 8
scoped_pass = all(structural.values()) and all(row["passed"] for row in comparisons) and frame
source_pins = []
for name in ("source/cost_model.py", "source/reference.py"):
    raw = Path(name).read_bytes()
    source_pins.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
result = {"schema": "terminal-authored-reference-native-cost-result@1",
          "status": "passed_scoped_authored_fixture" if scoped_pass else "refuted_scoped_authored_fixture",
          "source_pins_in_ephemeral_workspace": source_pins,
          "granularity": model.g, "cost_constants": vars(model.c), "buckets": results,
          "all_eight_strict_threshold_comparisons": comparisons,
          "structural_four_clauses": structural, "global_unique_shapes": sorted(shapes),
          "shared_representatives": reference["shared_representatives"],
          "input_hashes_before": before, "input_hashes_after": after, "input_bytes_unchanged": frame,
          "source_prediction_matches_observations": all(row["prediction_matches_observation"] for row in comparisons),
          "actual_benchmark_instances_or_heldout_data_used": False, "official_benchmark_score": None,
          "full_task_satisfaction": "unknown", "universal_source_equivalence_proved": False,
          "model_convergence_proved": False, "training_calls": 0, "optimizer_updates": 0,
          "PlanCreate_calls": 0, "prover_calls": 0, "default_activation": False,
          "proof_authority": False, "execution_authority": False, "completion_authority": False}
Path("result.json").write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
print(json.dumps({"status": result["status"], "strict_thresholds": sum(row["passed"] for row in comparisons),
                  "global_shapes": len(shapes), "inputs_unchanged": frame}))
