"""Run the nine preselected expanded source-only fits through bounded parents."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def binding(path):
    path = Path(path).absolute()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
    return binding(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("plan", "parent", "publication-gate"):
        parser.add_argument("--" + flag, type=Path, required=True)
        parser.add_argument("--" + flag + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = {"plan": binding(args.plan), "parent": binding(args.parent), "gate": binding(args.publication_gate)}
    if any(selected[name]["sha256"] != pin for name, pin in (("plan", args.plan_sha256), ("parent", args.parent_sha256),
                                                            ("gate", args.publication_gate_sha256))):
        raise ValueError("externally selected plan, parent or gate differs")
    plan = json.loads(args.plan.read_bytes())
    worker = binding(plan["helper_binding"]["path"])
    if worker != plan["helper_binding"] or plan["seeds"] != [1729, 1730, 1731]:
        raise ValueError("fixed worker and seeds required")
    selected["worker"] = worker
    output = args.output.absolute()
    if output.exists():
        raise ValueError("fresh batch directory required")
    output.mkdir(mode=0o700)
    records = []
    for lane in ("legacy8", "native384", "native768"):
        for seed in (1729, 1730, 1731):
            name = lane + "-seed" + str(seed)
            command = ["/home/barberb/lift_coding/.venv/bin/python", "-I", "-B", selected["parent"]["path"],
                       "--phase", "training", "--plan", selected["plan"]["path"], "--plan-sha256", args.plan_sha256,
                       "--worker", worker["path"], "--worker-sha256", worker["sha256"], "--lane", lane, "--seed", str(seed),
                       "--publication-gate", selected["gate"]["path"], "--publication-gate-sha256", args.publication_gate_sha256,
                       "--output", str(output / name)]
            save(output / (name + "-command.json"), {"command": command, "selected": selected})
            process = subprocess.run(command, capture_output=True, check=False)
            (output / (name + ".stdout")).write_bytes(process.stdout)
            (output / (name + ".stderr")).write_bytes(process.stderr)
            report_path = output / name / "worker/training-report.json"
            parent_path = output / name / "parent-report.json"
            record = {"lane_id": lane, "seed": seed, "returncode": process.returncode,
                      "parent_report_binding": binding(parent_path) if parent_path.exists() else None,
                      "training_report_binding": binding(report_path) if report_path.exists() else None}
            record["succeeded"] = record["returncode"] == 0 and record["training_report_binding"] is not None
            records.append(record)
            print(json.dumps({"arm": name, "succeeded": record["succeeded"]}), flush=True)
            if not record["succeeded"]:
                break
        if not records[-1]["succeeded"]:
            break
    unchanged = all(binding(value["path"]) == value for value in selected.values())
    reports = [json.loads(Path(r["training_report_binding"]["path"]).read_bytes()) for r in records if r["succeeded"]]
    summary = {"schema": "expanded-source-reconstruction-training-batch/v1", "selected": selected, "arms": records,
               "successful_arms": len(reports), "selected_inputs_unchanged": unchanged,
               "actual_optimizer_updates": sum(r["actual_total_optimizer_updates"] for r in reports),
               "selected_optimizer_updates": sum(r["selected_optimizer_updates"] for r in reports),
               "training_sources_per_arm": 32, "semantic_or_proof_qualification": False}
    summary_binding = save(output / "batch-report.json", summary)
    print(json.dumps({"batch_report_binding": summary_binding, "successful_arms": len(reports)}), flush=True)
    if len(reports) != 9 or not unchanged:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
