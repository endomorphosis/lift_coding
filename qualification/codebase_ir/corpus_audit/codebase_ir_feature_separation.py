#!/usr/bin/env python3
"""Bounded counterfactual column witnesses for an unchanged historical cohort.

This is a scalar count diagnostic. No source, feature recipe, tensor, model,
optimizer, training, compiler or checker is executed.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_final_targets as targets
import codebase_ir_native_feature_coverage as coverage
import codebase_ir_native_source384_diagnostics as native

INPUT_SCHEMA = "codebase-ir-feature-separation-input@1"
REPORT_SCHEMA = "codebase-ir-feature-separation@1"
PROFILE = "qualification/frozen-count-column-counterfactual-separation@1"
INPUT_ROLES = ("feature_coverage_input", "feature_coverage_report")
FROZEN_INPUT_SHA256 = "98e6e5f23529a266fd6f2cab8ed86ac826c965cd9859df9f1cfb854a966b43e7"
FROZEN_REPORT_SHA256 = "0415670ebfb9d40015bc1b7268e51e3d85d78cfbc4a62bf45916be3e9748284c"
FROZEN_INPUT_BYTES = 815
FROZEN_REPORT_BYTES = 102177
TRUE_FLAGS = coverage.TRUE_FLAGS | {"frozen_basis_retained_unmodified", "counterfactual_separation_available",
                                    "minimality_exhaustively_checked"}
FALSE_FLAGS = coverage.FALSE_FLAGS | {"feature_basis_modified", "augmentation_applied_to_native_feature_space",
    "candidate_tensors_modified", "model_quality_gain_verified", "universal_source_label_separation_verified",
    "open_world_literal_coverage_verified", "source_runtime_truth_verified"}


@dataclass(frozen=True)
class Limits:
    max_files: int = 10
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 3 * 1024 * 1024
    max_targets: int = 9
    max_columns: int = 53
    max_atoms: int = 256
    max_source_bytes: int = 65536
    max_oov_columns: int = 3
    max_subsets: int = 8
    max_comparisons: int = 288

    def __post_init__(self):
        audit._require(all(type(v) is int and v > 0 for v in asdict(self).values()), "positive exact separation limits required")


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=150000))


def _same(a, b):
    return audit._canonical(a) == audit._canonical(b)


def _scalar_counts(value, limits):
    """Independent path/type/value enumeration; no native vector normalization."""
    counts = Counter()
    total = 0

    def visit(node, path, depth):
        nonlocal total
        audit._require(depth <= 64, "separation scalar depth budget exceeded")
        if type(node) is dict:
            for name in sorted(node):
                audit._text(name, "separation scalar field", 256)
                visit(node[name], [*path, name], depth + 1)
        elif type(node) is list:
            for index, child in enumerate(node):
                visit(child, [*path, index], depth + 1)
        else:
            audit._require(node is None or type(node) in {str, bool, int, float}, "exact JSON scalar required")
            if type(node) in {int, float}:
                audit._require(native._finite_number(node), "bounded finite scalar number required")
            if type(node) is str:
                audit._require(len(node.encode()) <= 4096, "separation scalar string budget exceeded")
            audit._require(total < limits.max_atoms, "separation scalar atom budget exceeded")
            counts[audit._canonical([path, node]).decode()] += 1
            total += 1

    visit(value, [], 0)
    return counts


def _subset_witness(rows, candidates, subset):
    grouped = defaultdict(list)
    signatures = []
    for row in rows:
        counts = [*row["frozen_basis_counts"], *(row["atoms"][candidates[i][0]][candidates[i][1]] for i in subset)]
        signature = audit._sha(audit._canonical(counts))
        signatures.append({"id": row["id"], "signature_sha256": signature,
                           "extra_counts": counts[len(row["frozen_basis_counts"]):]})
        grouped[signature].append(row)
    pairs = sorted([a["id"], b["id"]] for members in grouped.values()
                   for a, b in itertools.combinations(members, 2) if a["label_sha256"] != b["label_sha256"])
    return {"column_indices": list(subset), "extra_column_count": len(subset),
            "separates_all_distinct_source_labels_in_cohort": not pairs,
            "unseparated_distinct_label_pair_count": len(pairs), "unseparated_distinct_label_pairs": pairs,
            "target_signatures": signatures}


def _search(rows, candidates, limits):
    n = len(candidates)
    audit._require(n <= limits.max_oov_columns and n <= 16, "counterfactual OOV column budget exceeded")
    # Check before constructing a power set or pairwise work allocation.
    subset_count = 1 << n
    audit._require(subset_count <= limits.max_subsets, "exhaustive subset budget exceeded")
    pair_count = len(rows) * (len(rows) - 1) // 2
    audit._require(subset_count * pair_count <= limits.max_comparisons, "exhaustive comparison budget exceeded")
    witnesses = [_subset_witness(rows, candidates, subset) for k in range(n + 1)
                 for subset in itertools.combinations(range(n), k)]
    separating = [w for w in witnesses if w["separates_all_distinct_source_labels_in_cohort"]]
    audit._require(separating, "no existing OOV column subset separates declared labels")
    cardinality = min(w["extra_column_count"] for w in separating)
    minimal = [w for w in separating if w["extra_column_count"] == cardinality]
    # Canonical candidate order, then combinations order, makes the tie-break explicit.
    chosen = minimal[0]
    return witnesses, minimal, chosen


def _diagnostic(original, exports, prior, limits):
    old_limits = coverage.Limits(max_targets=limits.max_targets, max_columns=limits.max_columns,
                                max_atoms=limits.max_atoms, max_source_bytes=limits.max_source_bytes)
    # The unchanged reader validates source/ProgramIR/view/reference/span closure.
    # New counts, labels, selection roles and the exhaustive search below are independently derived.
    closure = coverage._coverage(original, exports, old_limits)
    header = {"schema", "status", "profile", "scope", "manifest_sha256", "input_files", "limits",
              "captured_input_file_count", "captured_input_bytes", "additional_attempted_training_epochs",
              "new_final_assignments", "limitations", *(role + "_sha256" for role in coverage.INPUT_ROLES),
              *coverage.TRUE_FLAGS, *coverage.FALSE_FLAGS}
    audit._closed(prior, header | set(closure), "frozen coverage report")
    audit._require(prior["schema"] == coverage.REPORT_SCHEMA and prior["profile"] == coverage.PROFILE
                   and prior["status"] == "passed", "frozen successful feature coverage required")
    audit._require(all(prior[k] is True for k in coverage.TRUE_FLAGS)
                   and all(prior[k] is False for k in coverage.FALSE_FLAGS)
                   and type(prior["new_final_assignments"]) is type(prior["additional_attempted_training_epochs"]) is int
                   and prior["new_final_assignments"] == prior["additional_attempted_training_epochs"] == 0,
                   "frozen report scope elevation")
    audit._require(all(_same(prior[k], v) for k, v in closure.items()), "frozen coverage report differs from rederived raw closure")
    columns = [tuple(c) for c in exports["parent_export"]["feature_space"]["columns"]]
    audit._require(len(columns) == 53 and len(prior["targets"]) == 9, "closed historical nine-target 53-column cohort required")
    prior_rows = {row["id"]: row for row in prior["targets"]}
    audit._require(len(prior_rows) == 9, "unique frozen target identities required")
    rows, oov = [], set()
    for exported, record in zip((exports["parent_export"], exports["child_export"]), original["native_records"], strict=True):
        lineage = exported["report"]["codebase_provenance"]
        selection_roles = {item["path"]: item["role"] for item in lineage["selections"]}
        for batch, role in coverage.BATCH_ROLES.items():
            for index, target in enumerate(lineage[batch]):
                identifier = f"native/{record['version_id']}/{batch}/{index}"
                previous = prior_rows[identifier]
                details = target["validation"][0]["details"]
                raw = bytes.fromhex(details["source_bytes_hex"])
                binding, label, reason = targets.derive_source(raw, audit.Limits(max_source_bytes=limits.max_source_bytes))
                audit._require(label is not None and reason is None and label["body"].get("operator") == "Add"
                               and label["body"]["right"].get("kind") == "literal"
                               and type(label["body"]["right"]["value"]) is int, "closed supported integer-add literal labels required")
                atoms = {view["projection_id"]: _scalar_counts(view["expression"], limits) for view in target["projections"]}
                counts = [atoms[projection][encoded] for projection, encoded in columns]
                exposure = "train" if role == "replay" else role
                path = details["source_binding"]["path"]
                unknown = [{"field": "type_ref", "native_id": e["expression_id"], "native_kind": "expressions", "value": e["type_ref"]}
                           for e in details["native_program"]["expressions"] if e["type_ref"] == "any"]
                audit._require(_same(previous["source_binding"], binding) and _same(previous["source_label"], label)
                               and previous["source_sha256"] == audit._sha(raw)
                               and previous["source_path_claim"] == path and previous["original_role"] == role
                               and previous["exposure_role"] == selection_roles[path] == exposure
                               and _same(previous["unknown_sort_inventory"], unknown)
                               and _same(previous["frozen_basis_counts"], counts)
                               and previous["frozen_basis_signature_sha256"] == audit._sha(audit._canonical(counts)),
                               "independent source/role/sort/count correspondence differs")
                oov.update((projection, encoded) for projection, values in atoms.items() for encoded in values
                           if (projection, encoded) not in columns)
                rows.append({"id": identifier, "source_label": label, "label_sha256": audit._sha(audit._canonical(label)),
                             "source_binding": binding, "source_sha256": audit._sha(raw), "source_path_claim": path,
                             "original_role": role, "exposure_role": exposure, "frozen_basis_counts": counts,
                             "frozen_basis_signature_sha256": previous["frozen_basis_signature_sha256"],
                             "unknown_sort_inventory": unknown, "projection_losses": previous["projection_losses"], "atoms": atoms})
    audit._require(len(rows) == len(prior_rows) == 9 and {r["id"] for r in rows} == set(prior_rows), "exact final historical population required")
    candidates = sorted(oov, key=lambda column: audit._canonical(list(column)))
    audit._require(len(candidates) == 3, "exact three existing unrepresented literal columns required")
    for projection, encoded in candidates:
        path, value = json.loads(encoded)
        audit._require(projection == "codebase_ir.program@1" and path == ["document", "expressions", 1, "attributes", "value"]
                       and type(value) is int and value in {2, 3, 5}, "only existing integer literal columns may be proposed")
    witnesses, minimal, chosen = _search(rows, candidates, limits)
    audit._require(chosen["extra_column_count"] == 2 and len(minimal) == 3, "historical minimality expectations differ")
    full = witnesses[-1]
    full_missing = sum(count for row in rows for projection, values in row["atoms"].items() for encoded, count in values.items()
                       if (projection, encoded) not in set(columns) | set(candidates))
    audit._require(full_missing == 0 and full["separates_all_distinct_source_labels_in_cohort"], "full OOV coverage witness incomplete")
    # Authored source-only open-world examples use copies of the observed view;
    # they are not additional native observations, evaluation samples or model outputs.
    template = next(v["expression"] for v in exports["parent_export"]["report"]["codebase_provenance"]["training_targets"][0]["projections"]
                    if v["projection_id"] == "codebase_ir.program@1")
    authored = []
    for value in (4, 6):
        raw = f"def step(n: int) -> int:\n    return n + {value}\n".encode()
        binding, label, reason = targets.derive_source(raw)
        audit._require(label is not None and reason is None, "authored open-world source label unavailable")
        view = copy.deepcopy(template)
        view["document"]["expressions"][1]["attributes"]["value"] = value
        counts = _scalar_counts(view, limits)
        vectors = {}
        for proposal, additions in (("minimal", [candidates[i] for i in chosen["column_indices"]]), ("full_oov", candidates)):
            # Contract-view columns are unchanged. Its original counts are retained.
            original_counts = rows[0]["frozen_basis_counts"]
            vector = [counts[encoded] if projection == "codebase_ir.program@1" else original_counts[index]
                      for index, (projection, encoded) in enumerate(columns)]
            vector.extend(counts[encoded] for _, encoded in additions)
            vectors[proposal] = audit._sha(audit._canonical(vector))
        authored.append({"origin": "authored_source_only_counterfactual_not_native_observation", "literal": value,
                         "source_bytes_hex": raw.hex(), "source_binding": binding, "source_label": label,
                         "count_signature_sha256": vectors, "assigned_to_final": False, "model_prediction_available": False})
    audit._require(authored[0]["source_label"] != authored[1]["source_label"]
                   and _same(authored[0]["count_signature_sha256"], authored[1]["count_signature_sha256"]),
                   "open-world remaining ambiguity witness differs")
    for row in rows:
        row.pop("atoms")
    return {"historical_target_count": len(rows), "unique_source_count": closure["unique_source_count"],
            "role_counts": closure["role_counts"], "targets": rows,
            "counterfactual_selection_exposure": {"purpose": "diagnostics_only_not_model_selection",
                "roles": sorted(closure["role_counts"]), "role_counts": closure["role_counts"],
                "training_only_selection": False, "heldout_selection": False, "predeclared_model_selection": False},
            "frozen_basis_column_count": len(columns), "frozen_basis_column_sha256": closure["frozen_basis_column_sha256"],
            "frozen_basis_canonical_sha256": closure["frozen_basis_canonical_sha256"],
            "frozen_basis_columns": [list(c) for c in columns], "candidate_oov_columns": [list(c) for c in candidates],
            "candidate_oov_column_count": len(candidates), "canonical_column_tie_break": "ascending canonical UTF-8 JSON column bytes, then lexicographic index subsets",
            "exhaustive_subset_count": len(witnesses), "subset_witnesses": witnesses,
            "minimal_extra_column_count": chosen["extra_column_count"], "minimal_separating_subset_count": len(minimal),
            "minimal_separating_subsets": [w["column_indices"] for w in minimal], "selected_minimal_column_indices": chosen["column_indices"],
            "selected_minimal_columns": [list(candidates[i]) for i in chosen["column_indices"]],
            "full_oov_extra_column_count": len(candidates), "full_oov_columns": [list(c) for c in candidates],
            "full_oov_unrepresented_atom_occurrence_count": full_missing,
            "unknown_sort_occurrence_count": sum(len(r["unknown_sort_inventory"]) for r in rows),
            "projection_source_span_loss_count": sum(r["projection_losses"]["native_source_span_count"] for r in rows),
            "open_world_ambiguity_witnesses": authored, "normalization_applied_by_auditor": False,
            "new_final_assignments": 0, "additional_attempted_training_epochs": 0}


def _output_population(output, retained, limits):
    """Fence the exact flat copy population immediately before publishing."""
    audit._require(output.resolve(strict=True) == output
                   and not any(part.is_symlink() for part in (output, *output.parents)),
                   "canonical nonsymlink separation output root required")
    before = output.lstat()
    audit._require(stat.S_ISDIR(before.st_mode), "regular separation output directory required")
    audit._require(len(retained) <= limits.max_files, "separation output population budget exceeded")
    expected = {Path(row["retained_path"]).name: row for row in retained}
    audit._require(len(expected) == len(retained)
                   and all(Path(row["retained_path"]).parent == output for row in retained),
                   "unique flat retained output selectors required")
    found = set()
    with os.scandir(output) as entries:
        for entry in entries:
            audit._require(len(found) < len(expected) and entry.name in expected,
                           "unexpected separation output population member")
            state = entry.stat(follow_symlinks=False)
            row = expected[entry.name]
            audit._require(stat.S_ISREG(state.st_mode) and state.st_size == row["size_bytes"],
                           "regular exact-size retained output member required")
            raw = final.Capture.regular(output / entry.name, row["size_bytes"])
            audit._require(audit._sha(raw) == row["sha256"], "final retained output body drift")
            found.add(entry.name)
    after = output.lstat()
    audit._require(found == set(expected) and output.resolve(strict=True) == output
                   and stat.S_ISDIR(after.st_mode)
                   and (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
                   == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns),
                   "separation output root or exact file/directory population drift")


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    audit._require(str(manifest.resolve(strict=True)) == str(manifest), "canonical separation manifest required")
    pins = native.Pins(limits)
    raw_manifest = pins.read(manifest, min(limits.max_file_bytes, 256 * 1024))
    spec = _json(raw_manifest, limits)
    audit._closed(spec, {"schema", *INPUT_ROLES}, "feature separation manifest")
    audit._require(spec["schema"] == INPUT_SCHEMA, "feature separation input schema required")
    audit._require(spec["feature_coverage_input"]["sha256"] == FROZEN_INPUT_SHA256
                   and spec["feature_coverage_input"]["size_bytes"] == FROZEN_INPUT_BYTES
                   and spec["feature_coverage_report"]["sha256"] == FROZEN_REPORT_SHA256
                   and spec["feature_coverage_report"]["size_bytes"] == FROZEN_REPORT_BYTES,
                   "independently fixed prior input/report anchors required")
    _, raw_input = pins.descriptor(spec["feature_coverage_input"])
    _, raw_report = pins.descriptor(spec["feature_coverage_report"])
    prior_spec, prior = _json(raw_input, limits), _json(raw_report, limits)
    audit._closed(prior_spec, {"schema", *coverage.INPUT_ROLES}, "frozen feature coverage input")
    audit._require(prior_spec["schema"] == coverage.INPUT_SCHEMA and prior["manifest_sha256"] == audit._sha(raw_input), "prior input/report exact manifest join failed")
    raw = {}
    for role in coverage.INPUT_ROLES:
        _, raw[role] = pins.descriptor(prior_spec[role])
        audit._require(prior[role + "_sha256"] == prior_spec[role]["sha256"], "prior report export binding differs")
    expected_originals = {spec["feature_coverage_input"]["path"]: spec["feature_coverage_input"],
                          **{prior_spec[role]["path"]: prior_spec[role] for role in coverage.INPUT_ROLES}}
    audit._require(type(prior["input_files"]) is list and len(prior["input_files"]) == 4
                   and {row["path"] for row in prior["input_files"]} == set(expected_originals), "complete prior retained input population required")
    for row in prior["input_files"]:
        audit._closed(row, {"path", "retained_path", "sha256", "size_bytes"}, "prior retained input pin")
        audit._require(_same({k: row[k] for k in ("path", "sha256", "size_bytes")}, expected_originals[row["path"]]), "prior retained copy raw binding differs")
        _, retained = pins.descriptor({"path": row["retained_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
        audit._require(retained == pins.files[Path(row["path"])], "prior original/copy bytes differ")
    lock_tool._preflight_output(output, sorted({p.parent for p in pins.files}))
    original = _json(raw["provenance_input"], limits)
    for role, record in zip(("parent_export", "child_export"), original["native_records"], strict=True):
        audit._require(record["sha256"] == prior_spec[role]["sha256"] and record["file"] == Path(prior_spec[role]["path"]).name,
                       "captured raw export selector join failed")
    exports = {role: _json(raw[role], limits) for role in ("parent_export", "child_export")}
    summary = _diagnostic(original, exports, prior, limits)
    pins.recheck()
    output.mkdir(exist_ok=False)
    retained = []
    for index, (path, value) in enumerate(pins.files.items()):
        copy_path = output / f"input-{index:02d}-{path.name}"
        copy_path.write_bytes(value)
        audit._require(final.Capture.regular(copy_path, len(value)) == value, "separation retained copy mismatch")
        retained.append({"path": str(path), "retained_path": str(copy_path), "sha256": audit._sha(value), "size_bytes": len(value)})
    pins.recheck()
    for row in retained:
        audit._require(final.Capture.regular(Path(row["retained_path"]), row["size_bytes"]) == pins.files[Path(row["path"])], "late separation retained copy drift")
    report = {"schema": REPORT_SCHEMA, "status": "passed", "profile": PROFILE,
              "scope": "exhaustive_counterfactual_scalar_count_separation_of_exact_nine_historical_observations_only",
              "manifest_sha256": audit._sha(raw_manifest), **{role + "_sha256": spec[role]["sha256"] for role in INPUT_ROLES},
              **{role + "_sha256": prior_spec[role]["sha256"] for role in coverage.INPUT_ROLES},
              **dict.fromkeys(TRUE_FLAGS, True), **dict.fromkeys(FALSE_FLAGS, False), **summary,
              "input_files": retained, "captured_input_file_count": len(pins.files), "captured_input_bytes": pins.total, "limits": asdict(limits),
              "limitations": ["Proposed columns are appended only to diagnostic count signatures; the captured basis and tensor/optimizer bodies remain unchanged.",
                  "Minimality is exhaustive over exactly the three existing OOV literal columns and nine retained targets, with duplicate same-label observations preserved.",
                  "Full OOV coverage is for this finite cohort. Authored literals 4 and 6 still collide, so neither proposal supplies an open-world decoder or universal separation.",
                  "Eighteen native any-sort occurrences and 54 native source spans omitted from feature expressions remain unknown or lost after augmentation.",
                  "No normalized native vectors, recipe execution, training, inference, learned gains, source runtime truth, provenance authority or complete ancestry are established.",
                  "Original train/tune/canary/replay exposure roles are preserved. There are no new FINAL assignments or model selections."]}
    _output_population(output, retained, limits)
    final._write(output / "feature_separation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "refused", "reason": str(exc),
                          "unknown_pretraining_exposure": True, **dict.fromkeys(FALSE_FLAGS, False)}, sort_keys=True), file=sys.stderr)
        return 3
    print(json.dumps({"status": report["status"], "historical_targets": report["historical_target_count"],
                      "minimal_extra_columns": report["minimal_extra_column_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
