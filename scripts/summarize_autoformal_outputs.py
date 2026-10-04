#!/usr/bin/env python3
"""Validate saved throughput outputs and summarize repeated identical workloads."""
import argparse
import json
import math
from pathlib import Path
import statistics

from benchmark_autoformal_outputs import digest, ROOT, REPO


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    checks = []
    previous = {}
    dimensions = {"spacy8": 8, "gte384": 384, "gte768": 768}
    for directory in args.runs:
        report = json.loads((directory / "report.json").read_text())
        workload = json.loads((directory / "workload.json").read_text())
        assert digest(workload) == report["workload_sha256"]
        assert len(workload) == 800 and report["cpu_affinity"] == list(range(20))
        if reports:
            for key in ("workload_sha256", "source_bindings", "producer_sha256"):
                assert report[key] == reports[0][key], key
        for method, metrics in report["methods"].items():
            if metrics["status"] != "completed":
                assert method == "leanstral4096" and metrics["status"] == "unavailable"
                continue
            outputs = json.loads((directory / (method + "-outputs.json")).read_text())
            assert len(outputs) == metrics["completed_transactions"] == 800
            assert digest(outputs) == metrics["outputs_sha256"]
            assert [row["id"] for row in outputs] == [row["id"] for row in workload]
            assert math.isclose(metrics["transactions_per_second"], 800 / metrics["wall_seconds"])
            assert math.isclose(metrics["source_lexical_tokens_per_second"], 6400 / metrics["wall_seconds"])
            if method in dimensions:
                for row in outputs:
                    assert len(row["embedding"]) == dimensions[method]
                    assert all(math.isfinite(value) for value in row["embedding"])
                    assert abs(math.hypot(*row["embedding"]) - 1) < 1e-4
                    assert row["native_tokens"] > 0
                deterministic = [row["embedding"] for row in outputs]
                if method in previous:
                    assert deterministic == previous[method], method + " vector replay differs"
                previous[method] = deterministic
                assert sum(row["native_tokens"] for row in outputs) == metrics["native_input_tokens"]
            else:
                deterministic = [{"ir": row["ir"], "text": row["text"]} for row in outputs]
                assert deterministic == previous.setdefault("canonical", deterministic)
                if method == "compiler_groth16_v1":
                    for row in outputs:
                        assert row["verified"] is True
                        assert row["theorem"] == "artifact_" + digest(row["ir"])
                        assert row["proof"]["public_inputs"]["theorem"] == row["theorem"]
                        assert row["proof"]["public_inputs"]["circuit_ref"] == "knowledge_of_axioms@v1"
            checks.append({"run": str(directory), "method": method, "validated_outputs": len(outputs)})
        reports.append(report)
    summary = {"runs": [str(directory) for directory in args.runs], "workload_sha256": reports[0]["workload_sha256"],
               "transactions_per_method_per_run": 800, "cores": 20, "historical_workload_recovered": False,
               "validated_outputs": sum(check["validated_outputs"] for check in checks), "validation": checks,
               "methods": {}}
    lines = ["# Autoformalization output throughput: 800 transactions on 20 CPUs", "",
             "Median of three warm measurements on an identical replacement synthetic workload (800 distinct short statements).",
             "The caller supplies atom vocabulary; vocabulary discovery is outside the compiler timing. Shared-host contention is uncontrolled.", "",
             "| Method | Transactions/s (median) | Source lexical tokens/s | Native input tokens/s | Transactions/s range |",
             "| --- | ---: | ---: | ---: | ---: |"]
    labels = {"compiler": "Compiler + decompiler", "spacy8": "8D spaCy features",
              "gte384": "384D GTE-small", "gte768": "768D multilingual GTE",
              "compiler_groth16_v1": "Compiler + decompiler + Groth16 v1 prove/verify"}
    for method, label in labels.items():
        measurements = [report["methods"][method] for report in reports]
        rates = [row["transactions_per_second"] for row in measurements]
        result = {"label": label, "status": "completed", "transactions_per_second_median": statistics.median(rates),
                  "transactions_per_second_min": min(rates), "transactions_per_second_max": max(rates)}
        for key in ("source_lexical_tokens_per_second", "native_input_tokens_per_second", "output_lexical_tokens_per_second"):
            values = [row[key] for row in measurements if row[key] is not None]
            result[key + "_median"] = statistics.median(values) if values else None
        summary["methods"][method] = result
        native = result["native_input_tokens_per_second_median"]
        lines.append(f"| {label} | {statistics.median(rates):.2f} | {result['source_lexical_tokens_per_second_median']:.2f} | "
                     f"{f'{native:.2f}' if native else '—'} | {min(rates):.2f}–{max(rates):.2f} |")
    summary["methods"]["leanstral4096"] = reports[0]["methods"]["leanstral4096"]
    lines += ["| 4096D Leanstral | — | — | — | Unavailable |", "",
              "Source lexical tokens use Unicode words and punctuation (6,400 per workload). Native input tokens use each encoder's tokenizer; GTE counts include special tokens. Vector coordinates are not generated tokens.",
              "Compiler output lexical tokens/s are saved separately in summary.json. The 8D/384D/768D rows measure encoding, not complete formalization; no learned decoder is invoked.", "",
              "Groth16 v1 generates and verifies actual cryptographic proofs of commitment knowledge bound to the canonical IR digest. This is not a proof of source fidelity or compiler correctness.", "",
              "Leanstral's installed generation server returned HTTP 501: embeddings are disabled. A second model process was not started: the 62.5 GiB model requires at least 68.75 GiB with the existing runner's 10% headroom rule, versus about 45 GiB available at inspection. The existing generation service remains active.", "",
              "All 12,000 measured outputs across three runs were checked for coverage, hashes, matching workload/source bindings and rate arithmetic. Encoder vectors replay exactly, compiler outputs match across repeats and proof/no-proof runs, and all 2,400 ZK rows record successful verification.", "",
              "Run: `python3 scripts/benchmark_autoformal_outputs.py --output artifacts/NEW-RUN-DIRECTORY`.",
              "Each run retains workload.json, report.json, report.md, and actual compiler text/IR, vectors, and serialized proof outputs."]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"validated_outputs": summary["validated_outputs"], "methods": summary["methods"]}, indent=2))


if __name__ == "__main__":
    main()
