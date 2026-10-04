#!/usr/bin/env python3
"""Prepare a new source-only contrast cohort before any prediction export."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
from codebase_ir_final_targets import derive_source

PROTOCOL_ID = "authored-final-contrast-int-bool-20261003@2"
REPORT_SCHEMA = "codebase-ir-source-only-contrast-cohort@1"

# Labels are derived below from these captured bytes, never from this inventory's
# descriptions or from desired instructions. Known/unseen native vocabulary
# membership is deliberately not asserted by names such as small/large literal.
PAIRS = (
    ("literal", "literal_small", "literal_large", "def offset(n: int) -> int:\n    return n + 7\n", "def offset(n: int) -> int:\n    return n + 104729\n"),
    ("guard_boundary", "guard_strict", "guard_inclusive", "def within(n: int, limit: int) -> bool:\n    return n < limit\n", "def within(n: int, limit: int) -> bool:\n    return n <= limit\n"),
    ("guard_polarity", "guard_negated", "guard_positive", "def outside(n: int, limit: int) -> bool:\n    return not (n < limit)\n", "def outside(n: int, limit: int) -> bool:\n    return n >= limit\n"),
    ("operand_order", "subtract_forward", "subtract_reverse", "def subtract(left: int, right: int) -> int:\n    return left - right\n", "def subtract(left: int, right: int) -> int:\n    return right - left\n"),
    ("symbol", "select_left", "select_right", "def select(left: int, right: int) -> int:\n    return left\n", "def select(left: int, right: int) -> int:\n    return right\n"),
    ("unicode", "unicode_forward", "unicode_reverse", "# 区間の順序を保持\ndef 差分(下界: int, 上界: int) -> int:\n    return 下界 - 上界\n", "# 区間の順序を変更\ndef 差分(下界: int, 上界: int) -> int:\n    return 上界 - 下界\n"),
    ("boolean", "flags_and", "flags_or", "def flags(active: bool, blocked: bool) -> bool:\n    return active and not blocked\n", "def flags(active: bool, blocked: bool) -> bool:\n    return active or not blocked\n"),
    ("sort_literal", "literal_integer", "literal_boolean", "def typed(value: int) -> int:\n    return 1\n", "def typed(value: bool) -> bool:\n    return True\n"),
    ("normalized_clone", "clone_plain", "clone_comment", "def clone(n: int) -> int:\n    return n * 13\n", "# Ordinary comment is a byte change, not an AST change.\ndef clone(n: int) -> int:\n    return n * 13  # retained qualification clone\n"),
    ("revision", "revision_before", "revision_after", "def evolving(n: int) -> int:\n    return n + 2\n", "def evolving(n: int) -> int:\n    return n + 3\n"),
)
OTHER = (
    ("dependency_helper", "dependency", "def support(n: int) -> int:\n    return n * 3\n"),
    ("dependency_consumer", "dependency", "def consumer(n: int) -> int:\n    return support(n)\n"),
    ("unsupported_call", "unsupported_call", "def external(n: int) -> int:\n    return remote(n)\n"),
    ("unsupported_effect", "unsupported_effect", "def noisy(n: int) -> int:\n    print(n)\n    return n\n"),
    ("unsupported_default", "unsupported_default", "def defaulted(n: int = 5) -> int:\n    return n + 1\n"),
    ("unsupported_branch", "unsupported_branch", "def branch(n: int) -> int:\n    if n < 0:\n        return -n\n    return n\n"),
    ("unsupported_type", "unsupported_type", "def untyped(n: any) -> int:\n    return n\n"),
    ("unsupported_division", "unsupported_division", "def divide(n: int, d: int) -> int:\n    return n // d\n"),
)
COMPARATORS = (
    ("train", "def training_anchor(n: int) -> int:\n    return -n + 43\n"),
    ("tune", "def tuning_anchor(a: int, b: int) -> bool:\n    return a == b\n"),
    ("canary", "def canary_anchor(enabled: bool) -> bool:\n    return not enabled\n"),
)


def _write(path, value):
    raw = audit._canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)
    return {"path": path.name, "sha256": audit._sha(raw), "size_bytes": len(raw)}


def _groups(units, sources):
    """Keep all declared template/AST/path/dependency/revision connections."""
    parent = {row["id"]: row["id"] for row in units}
    edges, buckets = set(), {}

    def root(name):
        while parent[name] != name:
            name = parent[name]
        return name

    def join(left, right, kind):
        parent[root(right)] = root(left)
        edges.add((kind, *sorted((left, right))))

    for row in units:
        name = row["id"]
        for kind, value in (("template", row["template_family"]),
                            ("normalized_ast", audit.normalized_ast_digest(sources[name])),
                            ("repository_path", (row["repository_id"], row["path"]))):
            key = kind, value
            if key in buckets:
                join(buckets[key], name, kind)
            else:
                buckets[key] = name
        for kind, field in (("dependency", "dependencies"), ("related_revision", "related_revisions")):
            for other in row[field]:
                audit._require(other in parent, "contrast relation names an unavailable unit")
                join(name, other, kind)
    groups = {}
    for row in units:
        groups.setdefault(root(row["id"]), []).append(row["id"])
    return [{"unit_ids": sorted(names), "independence_verified": False} for names in sorted(groups.values())], [
        {"kind": kind, "left": left, "right": right} for kind, left, right in sorted(edges)]


def build(output: Path):
    output = output.absolute()
    lock_tool._preflight_output(output, [Path(__file__).resolve().parent])
    output.mkdir(mode=0o700)
    (output / "source").mkdir(mode=0o700)
    inventory = [(name, family, source) for family, left, right, a, b in PAIRS for name, source in ((left, a), (right, b))]
    inventory.extend(OTHER)
    units, cases, sources = [], [], {}
    for name, family, text in inventory:
        raw = text.encode("utf-8")
        source = output / "source" / (name + ".py")
        source.write_bytes(raw)
        source.chmod(0o600)
        unit_id = "final:" + name
        sources[unit_id] = raw
        row = {"id": unit_id, "role": "final", "repository_id": "qualification:contrast-final-20261003",
               "path": "evolving.py" if family == "revision" else name + ".py",
               "revision": "authored@before" if name == "revision_before" else "authored@after" if name == "revision_after" else "authored@2",
               "source": {"path": "source/" + source.name, "sha256": audit._sha(raw), "size_bytes": len(raw)},
               "dependencies": ["final:dependency_helper"] if name == "dependency_consumer" else [],
               "dependencies_complete": name not in {"dependency_consumer", "unsupported_call", "unsupported_effect"},
               "related_revisions": ["final:revision_before"] if name == "revision_after" else [],
               "revision_relations_complete": True, "template_family": "contrast:" + family}
        units.append(row)
        binding, target, reason = derive_source(raw)
        cases.append({"case_id": name, "unit_id": unit_id, "source_binding": binding,
                      "status": "supported" if target is not None else "unsupported", "target": target,
                      "unsupported_reason": reason,
                      "desired_intent": "Separate future instruction: investigate a requested change; preserve the current source-derived target.",
                      "intent_used_as_label": False})
    for role, text in COMPARATORS:
        name, raw = "comparison_" + role, text.encode()
        source = output / "source" / (name + ".py")
        source.write_bytes(raw)
        source.chmod(0o600)
        unit_id = "comparison:" + role
        sources[unit_id] = raw
        units.append({"id": unit_id, "role": role, "repository_id": "qualification:contrast-comparators-20261003",
                      "path": source.name, "revision": "authored@2", "source": {"path": "source/" + source.name,
                      "sha256": audit._sha(raw), "size_bytes": len(raw)}, "dependencies": [], "dependencies_complete": True,
                      "related_revisions": [], "revision_relations_complete": True, "template_family": "comparison:" + role})
    protocol = {"schema": final.PROTOCOL_SCHEMA, "protocol_id": PROTOCOL_ID, "scope": "authored_qualification_protocol",
                "source_profile": final.PROFILE, "metrics": final.METRICS, "unknown_pretraining_exposure": True,
                "final_selection_forbidden": True, "promotion_forbidden": True, "authoring_training_absence_certified": False,
                "native_decoder_compatibility_verified": False, "teacher_semantics_certified": False,
                "producer_authentication_verified": False}
    cohort = {"schema": final.COHORT_SCHEMA, "scope": "explicit_supplied_source_scope", "ancestry_complete": False,
              "native_exposure_inventory_complete": False, "units": units}
    targets = {"schema": final.TARGETS_SCHEMA, "profile": final.PROFILE, "provenance": {"origin": "authored_source_projection",
               "derived_from_desired_intent": False, "independently_checked_source_semantics": False,
               "native_teacher_compatibility_verified": False}, "cases": cases}
    spec = {"schema": final.INPUT_SCHEMA, "protocol": _write(output / "protocol.json", protocol),
            "cohort": _write(output / "cohort.json", cohort), "targets": _write(output / "targets.json", targets),
            "predictions": {"path": "future_predictions.json", "sha256": audit._sha(b""), "size_bytes": 0}}
    _write(output / "manifest.json", spec)
    # Use the unchanged source/label validator before publishing this generation.
    capture = lock_tool.Capture(output / "manifest.json", lock_tool.Budget(lock_tool.DEFAULT_LIMITS))
    receipt, validated, scope, family_leaks = lock_tool._material(capture)
    _write(output / "supplied_scope.json", scope)
    screen = audit.audit_manifest(output / "supplied_scope.json")
    _write(output / "split_screen.json", screen)
    groups, edges = _groups(units, sources)
    report = {"schema": REPORT_SCHEMA, "status": "passed", **lock_tool.CLAIMS,
              "manifest_sha256": audit._sha(capture.raw), "locked_identity_sha256": receipt["locked_identity_sha256"],
              "protocol_id": PROTOCOL_ID, "case_count": len(validated), "source_unit_count": len(units),
              "supported_case_count": sum(case["status"] == "supported" for case in cases),
              "unsupported_case_count": sum(case["status"] == "unsupported" for case in cases),
              "prediction_bodies_created": False, "prediction_bodies_read": False,
              "prediction_descriptor_scope": "empty-byte placeholder only; future export must supply its own exact descriptor",
              "native_vocabulary_coverage": "unknown", "semantic_equivalence_of_contrasts_verified": False,
              "split_audit_status": screen["status"], "split_issue_count": len(screen["issues"]),
              "split_leaks": screen["leaks"], "template_family_leaks": family_leaks,
              "connected_groups": groups, "explaining_edges": edges,
              "contrast_pairs": [{"kind": family, "case_ids": [left, right]} for family, left, right, _, _ in PAIRS],
              "input_files_unchanged": True, "source_only_labels_rederived": True}
    capture.recheck()
    _write(output / "contrast_inventory.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"contrast cohort refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "case_count", "supported_case_count", "unsupported_case_count")}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
