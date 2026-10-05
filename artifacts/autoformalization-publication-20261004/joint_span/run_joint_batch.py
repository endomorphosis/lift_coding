"""Run all three frozen decoder seeds through independent bounded parents."""
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
    for flag in ("plan", "parent"):
        parser.add_argument("--" + flag, type=Path, required=True)
        parser.add_argument("--" + flag + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = {"plan": binding(args.plan), "parent": binding(args.parent)}
    if selected["plan"]["sha256"] != args.plan_sha256 or selected["parent"]["sha256"] != args.parent_sha256:
        raise ValueError("externally selected plan or parent differs")
    plan = json.loads(args.plan.read_bytes())
    worker = binding(plan["helper_binding"]["path"])
    if worker != plan["helper_binding"] or [arm["seed"] for arm in plan["baseline_raw_receipts"]] != [1729, 1730, 1731]:
        raise ValueError("fixed joint helper and all three seeds required")
    selected["worker"] = worker
    output = args.output.absolute()
    if output.exists() or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError("fresh nonsymlink batch directory required")
    output.mkdir(mode=0o700)
    records = []
    for seed in (1729, 1730, 1731):
        name = "seed" + str(seed)
        command = ["/home/barberb/lift_coding/.venv/bin/python", "-I", "-B", selected["parent"]["path"],
                   "--plan", selected["plan"]["path"], "--plan-sha256", args.plan_sha256,
                   "--worker", worker["path"], "--worker-sha256", worker["sha256"], "--seed", str(seed),
                   "--output", str(output / name)]
        save(output / (name + "-command.json"), {"command": command, "selected": selected})
        process = subprocess.run(command, capture_output=True, check=False)
        for suffix, data in (("stdout", process.stdout), ("stderr", process.stderr)):
            path = output / (name + "." + suffix)
            with path.open("xb") as stream:
                os.chmod(path, 0o600)
                stream.write(data)
        parent_path = output / name / "parent-report.json"
        report_path = output / name / "worker/joint-report.json"
        record = {"seed": seed, "returncode": process.returncode,
                  "parent_report_binding": binding(parent_path) if parent_path.exists() else None,
                  "worker_report_binding": binding(report_path) if report_path.exists() else None}
        record["succeeded"] = process.returncode == 0 and record["worker_report_binding"] is not None
        records.append(record)
        print(json.dumps({"seed": seed, "succeeded": record["succeeded"]}), flush=True)
        if not record["succeeded"]:
            break
    unchanged = all(binding(row["path"]) == row for row in selected.values())
    reports = [json.loads(Path(record["worker_report_binding"]["path"]).read_bytes())
               for record in records if record["succeeded"]]
    counts = {key: sum(report["counts"][key] for report in reports)
              for key in reports[0]["counts"]} if reports else {}
    result = {"schema": "source-only-joint-span-batch/v1", "selected": selected, "seeds": records,
              "successful_seeds": len(reports), "selected_inputs_unchanged": unchanged,
              "completed_worker_counts": counts, "incomplete_attempt_counters_not_inferred": True,
              "semantic_accuracy_measured": False, "qualified": False, "proof_authority": False}
    receipt = save(output / "batch-report.json", result)
    print(json.dumps({"successful_seeds": len(reports), "batch_report_binding": receipt}), flush=True)
    return 0 if len(reports) == 3 and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
