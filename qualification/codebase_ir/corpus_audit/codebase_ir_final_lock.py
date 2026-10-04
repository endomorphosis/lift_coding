#!/usr/bin/env python3
"""Pin an unsigned FINAL source/protocol identity independently of predictions."""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final

LOCK_SCHEMA = "codebase-ir-final-input-lock@1"
REPORT_SCHEMA = "codebase-ir-final-input-lock-report@1"
IDENTITY_SCHEMA = "codebase-ir-final-locked-identity@1"
SCOPE = "selected raw FINAL input identity; no producer, exposure, numerical or semantic certification"
CLAIMS = {**dict.fromkeys(final.FALSE_FLAGS, False), "unknown_pretraining_exposure": True,
          "independence_verified": False, "native_closure_certified": False,
          "producer_authentication_verified": False, "teacher_semantics_certified": False,
          "numerical_provenance_verified": False, "learned_weight_dependence_verified": False,
          "native_decoder_compatibility_verified": False, "candidate_model_qualified": False,
          "authoring_training_absence_certified": False}


@dataclass(frozen=True)
class Limits:
    max_total_bytes: int = 16 * 1024 * 1024
    max_files: int = 256

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact lock aggregate bounds required")


DEFAULT_LIMITS = Limits()


class Budget:
    def __init__(self, limits: Limits):
        self.limits, self.bytes, self.files = limits, 0, 0


class Capture(final.Capture):
    """Combine per-bundle evaluation bounds with a shared preallocation ceiling."""
    def __init__(self, path: Path, budget: Budget, manifest_size: int | None = None):
        self.budget, self.manifest_size = budget, manifest_size
        super().__init__(path, final.DEFAULT_LIMITS)

    def _read(self, path: Path, maximum: int) -> bytes:
        if path == self.manifest and self.manifest_size is not None:
            maximum = min(maximum, self.manifest_size)
        if path not in self.files:
            audit._require(len(self.files) < self.limits.max_files
                           and self.budget.files < self.budget.limits.max_files, "lock input file budget exceeded")
            remaining = min(self.limits.max_total_bytes - self.total,
                            self.budget.limits.max_total_bytes - self.budget.bytes)
            audit._require(remaining >= 0, "lock aggregate byte budget exceeded")
            raw = self.regular(path, min(maximum, remaining))
            self.files[path] = raw
            self.total += len(raw)
            self.budget.files += 1
            self.budget.bytes += len(raw)
        raw = self.files[path]
        audit._require(len(raw) <= maximum, "lock input byte budget exceeded")
        return raw


def _descriptor(value):
    audit._closed(value, {"path", "sha256", "size_bytes"}, "locked input descriptor")
    relative = audit._relative_path(value["path"], "locked input path")
    audit._require(not any(part.startswith(".") for part in Path(relative).parts), "hidden/dot lock input refused")
    audit._digest(value["sha256"], "locked input SHA")
    audit._require(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= final.DEFAULT_LIMITS.max_json_bytes,
                   "exact bounded locked JSON descriptor required")
    return relative


def _material(capture: Capture):
    spec = audit._closed(capture.document, {"schema", "protocol", "cohort", "targets", "predictions"}, "locked evaluation input")
    audit._require(spec["schema"] == final.INPUT_SCHEMA, "versioned evaluation manifest required")
    _descriptor(spec["predictions"])
    documents, fixed = {}, {}
    for name in ("protocol", "cohort", "targets"):
        path, raw = capture.descriptor(spec[name])
        documents[name] = final._json(raw, capture.limits)
        fixed[name] = {**spec[name], "canonical_json_sha256": audit._sha(audit._canonical(documents[name]))}
    final._protocol(documents["protocol"])
    scope, sources, families = final._cohort(capture, documents["cohort"], capture.limits)
    # Validate all declared relationships and source-only labels without reading predictions.
    loader = audit._Loader(capture.root, audit.DEFAULT_LIMITS)
    for unit in scope["units"]:
        loader.manual_unit(unit)
    cases = final._targets(documents["targets"], scope["units"], sources, capture.limits)
    selected_sources = {}
    for unit in documents["cohort"]["units"]:
        descriptor = unit["source"]
        selected_sources[descriptor["path"]] = {**descriptor,
            "normalized_ast_sha256": audit.normalized_ast_digest(sources[unit["id"]])}
    source_inventory = [selected_sources[key] for key in sorted(selected_sources)]
    original = {"path": capture.manifest.name, "sha256": audit._sha(capture.raw), "size_bytes": len(capture.raw),
                "canonical_json_sha256": audit._sha(audit._canonical(spec))}
    _descriptor({key: original[key] for key in ("path", "sha256", "size_bytes")})
    protected = {path.relative_to(capture.root).as_posix() for path in capture.files}
    audit._require(spec["predictions"]["path"] not in protected, "mutable predictions overlap locked inputs")
    identity = {"schema": IDENTITY_SCHEMA, "protocol_id": documents["protocol"]["protocol_id"],
                "fixed_inputs": fixed, "sources": source_inventory}
    receipt = {"schema": LOCK_SCHEMA, "scope": SCOPE, "protocol_id": identity["protocol_id"],
               "locked_identity_sha256": audit._sha(audit._canonical(identity)), "original_manifest": original,
               "fixed_inputs": fixed, "sources": source_inventory, "claims": CLAIMS}
    return receipt, cases, scope, families


def _preflight_output(output: Path, protected: list[Path]):
    audit._require(not output.exists() and output.resolve(strict=False) == output
                   and output.parent.resolve(strict=True) == output.parent
                   and not any(part.is_symlink() for part in (output, *output.parents)), "fresh canonical lock output required")
    audit._require(not any(output.is_relative_to(root) for root in protected), "output lies inside immutable input scope")


def seal(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    _preflight_output(output, [manifest.parent.resolve(strict=True)])
    budget = Budget(limits)
    capture = Capture(manifest, budget)
    receipt, cases, scope, families = _material(capture)
    capture.recheck()
    output.mkdir(exist_ok=False)
    capture.retain(output)
    capture.recheck()
    final._write(output / "final_lock.json", receipt)
    lock_sha = audit._sha(audit._canonical(receipt) + b"\n")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "scope": SCOPE, **CLAIMS,
              "manifest_sha256": audit._sha(capture.raw), "lock_sha256": lock_sha,
              "locked_identity_sha256": receipt["locked_identity_sha256"], "protocol_id": receipt["protocol_id"],
              "input_files_unchanged": True, "prediction_bodies_read": False,
              "source_unit_count": len(scope["units"]), "source_file_count": len(receipt["sources"]),
              "case_count": len(cases), "template_family_leaks": families, "limits": asdict(limits),
              "input_files": [{"path": path.relative_to(capture.root).as_posix(), "sha256": audit._sha(raw), "size_bytes": len(raw)}
                              for path, raw in sorted(capture.files.items())], "input_bytes": budget.bytes}
    final._write(output / "final_lock_report.json", report)
    return report


def validate_locked(manifest: Path, lock: Path, expected_sha: str, limits: Limits = DEFAULT_LIMITS):
    """Review original retained lock bytes and current fixed bytes before mutation."""
    audit._digest(expected_sha, "required raw lock SHA")
    budget = Budget(limits)
    lock_capture = Capture(lock, budget)
    audit._require(audit._sha(lock_capture.raw) == expected_sha, "raw lock receipt SHA mismatch")
    receipt = audit._closed(lock_capture.document, {"schema", "scope", "protocol_id", "locked_identity_sha256",
        "original_manifest", "fixed_inputs", "sources", "claims"}, "FINAL input lock")
    audit._require(receipt["schema"] == LOCK_SCHEMA and receipt["scope"] == SCOPE
                   and audit._canonical(receipt["claims"]) == audit._canonical(CLAIMS), "unsigned conservative lock profile required")
    original = audit._closed(receipt["original_manifest"], {"path", "sha256", "size_bytes", "canonical_json_sha256"}, "original manifest pin")
    relative = _descriptor({key: original[key] for key in ("path", "sha256", "size_bytes")})
    audit._require(len(Path(relative).parts) == 1, "original manifest basename required")
    retained = Capture(lock.parent / "inputs" / relative, budget, original["size_bytes"])
    audit._require(len(retained.raw) == original["size_bytes"] and audit._sha(retained.raw) == original["sha256"], "original lock manifest bytes drifted")
    expected, _, _, _ = _material(retained)
    audit._require(audit._canonical(expected) == audit._canonical(receipt), "lock inventory/identity differs from original selected bytes")
    current = Capture(manifest, budget)
    candidate, cases, _, _ = _material(current)
    audit._require(candidate["protocol_id"] == receipt["protocol_id"]
                   and candidate["locked_identity_sha256"] == receipt["locked_identity_sha256"]
                   and audit._canonical(candidate["fixed_inputs"]) == audit._canonical(receipt["fixed_inputs"])
                   and audit._canonical(candidate["sources"]) == audit._canonical(receipt["sources"]),
                   "FINAL protocol/cohort/source/label identity changed under locked protocol")
    # The sole mutable descriptor is predictions; capture it once before output creation.
    _, raw = current.descriptor(current.document["predictions"])
    predictions = final._json(raw, current.limits)
    final._predictions(predictions, cases, current.document["protocol"]["sha256"], current.limits)
    for capture in (lock_capture, retained, current):
        capture.recheck()
    return receipt, (lock_capture, retained, current), budget


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = seal(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"FINAL lock refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "lock_sha256", "locked_identity_sha256", "case_count")}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
