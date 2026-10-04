"""Reconstruct selected retained worker stdout digests without running a worker."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import codebase_ir_advisory_evidence as advisory
import codebase_ir_frozen_auxiliary as auxiliary
from codebase_ir_admission_evidence import AdmissionEvidenceError, exact, need, parse_document

INPUT_SCHEMA = "codebase-ir-worker-protocol-input@1"
SCHEMA = "codebase-ir-worker-protocol-retained-audit@1"
REPORT_FILE = "worker_protocol_evidence.json"
WORKER_SCHEMA = "codebase-feature-worker@1"
# This is the reviewed, inert producer body implementing the four-field infer
# response and canonical ASCII JSON with no newline. Other contracts need review.
WORKER_SHA256 = "91174cb51a0832e4cd691e56f94c0d6b34af1f06e6afec2c0d780d58fa3196db"
WORKER_BYTES = 5967
MAX_ENVELOPE_BYTES = 64 * 1024
FALSE_FLAGS = tuple(flag for flag in auxiliary.FLAGS if flag != "worker_protocol_output_digest_rederived") + (
    "worker_protocol_input_digest_rederived",
    "original_worker_output_envelopes_retained",
)
CONTROLS = (
    "receipt_output_digest", "receipt_worker_identity", "correlated_numeric_output",
    "response_schema", "response_training", "response_authority", "response_extra",
    "response_missing", "response_whitespace", "response_key_order",
)


def wire(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def validate_spec(spec: Any) -> None:
    need(type(spec) is dict and set(spec) == {
        "schema", "prior_frozen_manifest", "prior_frozen_report", "protocol_worker_source"
    } and spec["schema"] == INPUT_SCHEMA, "closed protocol input schema required")
    paths = set()
    for name in ("prior_frozen_manifest", "prior_frozen_report", "protocol_worker_source"):
        auxiliary.pin_shape(spec[name], absolute=True)
        need(spec[name]["path"] not in paths, "protocol input aliases refused")
        paths.add(spec[name]["path"])
    need(spec["protocol_worker_source"]["sha256"] == WORKER_SHA256
         and type(spec["protocol_worker_source"]["bytes"]) is int
         and spec["protocol_worker_source"]["bytes"] == WORKER_BYTES,
         "unreviewed worker protocol contract refused")


def envelope(model: dict[str, Any]) -> bytes:
    return wire({"schema": WORKER_SCHEMA, "inference": model["inference"]["inference"],
                 "training_executed": False, "proof_authority": False})


def assert_protocol(model: dict[str, Any], raw: bytes, worker_sha256: str) -> dict[str, Any]:
    facts = auxiliary.assert_auxiliary(model)
    receipt = model["inference"]["worker_receipt"]
    need(worker_sha256 == WORKER_SHA256 and receipt["worker_sha256"] == worker_sha256,
         "retained worker identity differs from reviewed protocol source")
    need(type(raw) is bytes and len(raw) <= MAX_ENVELOPE_BYTES,
         "bounded protocol envelope bytes required")
    decoded = parse_document(raw)
    need(set(decoded) == {"schema", "inference", "training_executed", "proof_authority"}
         and decoded["schema"] == WORKER_SCHEMA and decoded["training_executed"] is False
         and decoded["proof_authority"] is False
         and exact(decoded["inference"], model["inference"]["inference"]),
         "closed inference protocol response differs")
    need(raw == envelope(model), "worker output is not exact canonical stdout bytes")
    digest = hashlib.sha256(raw).hexdigest()
    need(receipt["output_sha256"] == digest, "retained worker output digest differs")
    return facts | {
        "worker_sha256": worker_sha256,
        "retained_executable_sha256": receipt["executable_sha256"],
        "retained_input_sha256": receipt["input_sha256"],
        "reconstructed_output_sha256": digest,
        "reconstructed_output_bytes": len(raw),
        "output_digest_disposition": "rederived_from_retained_inference_and_reviewed_response_contract",
        "input_digest_disposition": "unknown_exact_stdin_not_retained",
        "input_gap": "full request bytes and sampled max_seconds are not selected; the stdin digest is not rederived",
        "source_execution_attested": False,
    }


def mutate(model: dict[str, Any], name: str) -> bytes:
    """Author inert corruptions; rebinding is never process authentication."""
    if name == "receipt_output_digest":
        model["inference"]["worker_receipt"]["output_sha256"] = "0" * 64
    elif name == "receipt_worker_identity":
        model["inference"]["worker_receipt"]["worker_sha256"] = "0" * 64
    elif name == "correlated_numeric_output":
        for role in ("inference", "trained_inference"):
            model[role]["inference"]["rows"][0]["latent"][0] += 0.125
    auxiliary.repin_model(model)
    raw = envelope(model)
    value = parse_document(raw)
    if name == "response_schema":
        value["schema"] = "foreign@1"
    elif name == "response_training":
        value["training_executed"] = True
    elif name == "response_authority":
        value["proof_authority"] = True
    elif name == "response_extra":
        value["unexpected"] = False
    elif name == "response_missing":
        del value["inference"]
    elif name == "response_whitespace":
        return raw + b"\n"
    elif name == "response_key_order":
        return json.dumps(dict(reversed(list(value.items()))), separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode()
    return wire(value)


def controls(cases: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    results = []
    for label, baseline in zip(auxiliary.LABELS, cases["06"], strict=True):
        for name in CONTROLS:
            model = copy.deepcopy(baseline)
            raw = mutate(model, name)
            try:
                assert_protocol(model, raw, WORKER_SHA256)
            except AdmissionEvidenceError as error:
                results.append({"label": label, "control": name, "refused": True,
                                "reason": str(error)})
            else:
                raise AdmissionEvidenceError("authored protocol corruption accepted: " + label + ":" + name)
    return results


def run(manifest: Path, output: Path) -> dict[str, Any]:
    output = output.absolute()
    need(not output.exists() and output.resolve(strict=False) == output
         and not any(parent.is_symlink() for parent in (output, *output.parents)),
         "fresh canonical nonsymlink output required")
    reader = advisory.PinnedReader()
    manifest = manifest.absolute()
    raw = reader.read(manifest, manifest=True)
    spec = parse_document(raw)
    validate_spec(spec)
    frozen_pin = spec["prior_frozen_manifest"]
    frozen = parse_document(reader.read(Path(frozen_pin["path"]), frozen_pin, manifest=True))
    auxiliary.validate_spec(frozen)
    base_pin = frozen["prior_advisory_manifest"]
    base = parse_document(reader.read(Path(base_pin["path"]), base_pin, manifest=True))
    advisory.validate_manifest(base)
    input_paths = [manifest, *(Path(spec[name]["path"]) for name in (
        "prior_frozen_manifest", "prior_frozen_report", "protocol_worker_source")),
        Path(base_pin["path"]), Path(frozen["prior_advisory_report"]["path"])]
    need(not any(output.is_relative_to(Path(row["root"])) for row in base["attempts"])
         and not any(path.is_relative_to(output) for path in input_paths),
         "output overlaps retained source roots or pinned inputs")
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema": SCHEMA, "status": "refused", "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(), **dict.fromkeys(FALSE_FLAGS, False),
        "worker_protocol_output_digest_rederived": False,
        "frozen_auxiliary_artifact_bodies_verified": False, "input_files_unchanged": False,
        "additional_attempted_training_epochs": 0,
        "prior_frozen_manifest_sha256": frozen_pin["sha256"],
        "prior_frozen_report_sha256": spec["prior_frozen_report"]["sha256"],
        "protocol_worker_source_sha256": spec["protocol_worker_source"]["sha256"],
        "limits": {"files": advisory.MAX_FILES, "file_bytes": advisory.MAX_FILE_BYTES,
                   "total_bytes": advisory.MAX_TOTAL_BYTES, "manifest_bytes": advisory.MAX_MANIFEST_BYTES,
                   "envelope_bytes": MAX_ENVELOPE_BYTES},
        "limitations": [
            "Outputs are reconstructed canonical envelopes from retained inference, not separately retained original stdout.",
            "Digest consistency does not authenticate process origin, executable execution, numerical correctness or state replay.",
            "Exact stdin bytes and the sampled max_seconds are not selected; input SHA256 remains an unrederived retained identifier.",
            "Only the explicitly reviewed source contract and nine selected frozen contexts are covered; no current owner authority or runtime closure.",
        ],
    }
    try:
        source_pin = spec["protocol_worker_source"]
        source = reader.read(Path(source_pin["path"]), source_pin, manifest=True)
        need(hashlib.sha256(source).hexdigest() == WORKER_SHA256 and len(source) == WORKER_BYTES,
             "reviewed inert protocol source bytes differ")
        prior_pin = spec["prior_frozen_report"]
        prior = parse_document(reader.read(Path(prior_pin["path"]), prior_pin, manifest=True))
        need(prior["schema"] == auxiliary.SCHEMA and prior["status"] == "passed"
             and prior["input_files_unchanged"] is True and prior["manifest_sha256"] == frozen_pin["sha256"]
             and prior["frozen_auxiliary_artifact_bodies_verified"] is True
             and type(prior["additional_attempted_training_epochs"]) is int
             and prior["additional_attempted_training_epochs"] == 0,
             "prior frozen report/input binding differs")
        for flag in auxiliary.FLAGS:
            need(prior[flag] is False, "prior frozen report has unsupported scope")
        cases = auxiliary.load(frozen, reader)
        selections = [{"attempt": attempt, "label": label, **auxiliary.assert_auxiliary(model)}
                      for attempt, models in cases.items()
                      for label, model in zip(auxiliary.LABELS, models, strict=True)]
        prior_selected = {path: pin for path, pin in reader.pins.items()
                          if path not in {str(manifest), prior_pin["path"], source_pin["path"]}}
        need(exact(prior["selected_input_pins"], prior_selected)
             and exact(prior["selections"], selections)
             and type(prior["selected_frozen_context_count"]) is int
             and prior["selected_frozen_context_count"] == 9
             and type(prior["selected_auxiliary_body_count"]) is int
             and prior["selected_auxiliary_body_count"] == 27,
             "prior frozen selection/inventory differs from fresh offline reconstruction")
        rows = []
        for attempt, models in cases.items():
            for label, model in zip(auxiliary.LABELS, models, strict=True):
                raw_envelope = envelope(model)
                row = {"attempt": attempt, "label": label,
                       **assert_protocol(model, raw_envelope, WORKER_SHA256)}
                name = "attempt-" + attempt + "-" + label + "-reconstructed-output.json"
                path = output / name
                path.write_bytes(raw_envelope)
                need(advisory._bounded_document(path, MAX_ENVELOPE_BYTES) == raw_envelope,
                     "written reconstructed output bytes differ")
                row["reconstructed_output_file"] = name
                rows.append(row)
        results = controls(cases)
        reader.recheck()
        for row in rows:
            body = advisory._bounded_document(output / row["reconstructed_output_file"], MAX_ENVELOPE_BYTES)
            need(len(body) == row["reconstructed_output_bytes"]
                 and hashlib.sha256(body).hexdigest() == row["reconstructed_output_sha256"],
                 "reconstructed output changed before report publication")
        report |= {
            "selections": rows, "selected_frozen_context_count": len(rows),
            "rederived_output_digest_count": len(rows),
            "distinct_rederived_output_digest_count": len({row["reconstructed_output_sha256"] for row in rows}),
            "unrederived_input_digest_count": len(rows),
            "reconstructed_output_bytes": sum(row["reconstructed_output_bytes"] for row in rows),
            "controls": results, "controls_count": len(results),
            "controls_refused": sum(row["refused"] for row in results),
            "controls_scope": "authored inert copies; unsigned pins/context CIDs rebound; no worker invoked",
            "worker_protocol_output_digest_rederived": True,
            "frozen_auxiliary_artifact_bodies_verified": True,
            "input_files_unchanged": True, "status": "passed",
        }
    except (ValueError, OSError, KeyError, TypeError, RecursionError, OverflowError) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    report |= {"read_file_count": len(reader.pins), "read_bytes": reader.total,
               "selected_input_pins": reader.pins, "finished_at": datetime.now(UTC).isoformat()}
    (output / REPORT_FILE).write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.manifest, args.output)
    except (ValueError, OSError, KeyError, TypeError, RecursionError, OverflowError) as error:
        print(json.dumps({"status": "refused", "report": None,
                          "error": type(error).__name__ + ": " + str(error)}, allow_nan=False))
        return 3
    print(json.dumps({"status": report["status"], "report": str(args.output / REPORT_FILE)}, allow_nan=False))
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
