#!/usr/bin/env python3
"""Score a later prediction export against an explicit unsigned FINAL byte lock."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool


def evaluate(manifest: Path, lock: Path, lock_sha256: str, output: Path,
             limits: lock_tool.Limits = lock_tool.DEFAULT_LIMITS):
    manifest, lock, output = manifest.absolute(), lock.absolute(), output.absolute()
    lock_tool._preflight_output(output, [manifest.parent.resolve(strict=True), lock.parent.resolve(strict=True)])
    receipt, captures, budget = lock_tool.validate_locked(manifest, lock, lock_sha256, limits)
    current = captures[-1]
    # All external selected bytes are validated first. The old scorer then reads
    # a private copy of exactly that first capture, preserving original filenames.
    output.mkdir(exist_ok=False)
    report = {"schema": final.REPORT_SCHEMA, "status": "refused", **lock_tool.CLAIMS,
              "manifest_sha256": audit._sha(current.raw), "input_files_unchanged": False,
              "raw_outputs_retained_unmodified": False}
    try:
        current.retain(output / "evaluation")
        captures[0].retain(output / "lock_receipt")
        captures[1].retain(output / "lock_baseline")
        for capture in captures:
            capture.recheck()
        report = final.evaluate(output / "evaluation/inputs" / manifest.name, output / "scored")
        audit._require(report["manifest_sha256"] == audit._sha(current.raw), "private evaluation manifest differs from first capture")
        expected = [{"path": path.relative_to(current.root).as_posix(), "sha256": audit._sha(raw), "size_bytes": len(raw)}
                    for path, raw in sorted(current.files.items())]
        if report["status"] == "passed":
            audit._require(report["input_files"] == expected, "private evaluation selected population differs from first capture")
        for capture in captures:
            capture.recheck()
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(status="refused", input_files_unchanged=False, error=f"locked input drift/refusal: {exc}")
    report.update(lock_tool.CLAIMS)
    report.update(lock_sha256=lock_sha256, lock_enforced=True, protocol_id=receipt["protocol_id"],
                  locked_identity_sha256=receipt["locked_identity_sha256"], lock_original_manifest_sha256=receipt["original_manifest"]["sha256"],
                  lock_scope=lock_tool.SCOPE, lock_bounds={**lock_tool.asdict(limits), "captured_bytes": budget.bytes, "captured_files": budget.files})
    final._write(output / "final_evaluation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.lock, args.lock_sha256, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"locked FINAL evaluation refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report.get(key) for key in ("status", "manifest_sha256", "lock_sha256", "lock_enforced", "prediction_count", "finding_count")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
