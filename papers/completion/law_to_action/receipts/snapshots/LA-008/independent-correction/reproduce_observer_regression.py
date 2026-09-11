#!/usr/bin/env python3
"""Reproduce original LA008 measurement defects beside the corrected observer."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path.cwd()
BASE = ROOT / "papers/completion/law_to_action"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    paths = {"original": BASE / "receipts/snapshots/LA-008/outputs/benchmark/handlers/effects.py",
             "corrected": BASE / "benchmark/handlers/effects.py"}
    output = {"scope": "Synthetic measurement regression only; no benchmark or provider invocation", "versions": {}}
    for version, path in paths.items():
        module = load("observer_regression_" + version, path)
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "exports").mkdir()
            data = b'{"observed":true}'
            (state / "exports/probe.json").write_bytes(data)
            observe = lambda: module.EffectObserver(state).observe(**({"run_id": "reviewer-run"} if version == "corrected" else {}))
            unjournaled = observe()
            event = {"event_schema": "law-to-action-observed-effect/v1", "run_id": "reviewer-run",
                     "handler_version": module.BoundedExportHandler.version,
                     "effect_kind": "filesystem.export_json", "target": "exports/probe.json",
                     "payload_sha256": "0" * 64, "payload_bytes": 0}
            (state / "effects.jsonl").write_text(json.dumps(event) + "\n")
            forged = observe()
            actual_hash = hashlib.sha256((state / "exports/probe.json").read_bytes()).hexdigest()
            if version == "original":
                assert unjournaled["event_count"] == 0 and len(unjournaled["export_files"]) == 1
                assert forged["event_count"] == 1 and "integrity_errors" not in forged
            else:
                assert unjournaled["event_count"] == 1 and unjournaled["journal_consistent"] is False
                assert forged["journal_consistent"] is False
                assert forged["observed_effects"][0]["payload_sha256"] == actual_hash
                assert forged["observed_effects"][0]["payload_bytes"] == len(data)
            output["versions"][version] = {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                           "actual_file_sha256": actual_hash, "actual_file_bytes": len(data),
                                           "unjournaled": unjournaled, "forged_journal": forged}
    output["original_defects_reproduced_and_corrected_rejection_passed"] = True
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
