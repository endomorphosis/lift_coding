"""Authored inert codec controls; embedded fragments are not model outputs."""
import base64
import copy
import json
import os
import tempfile
import unittest
import zlib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest import mock

import codebase_ir_corpus_audit as audit
import codebase_ir_native_feature_coverage as tool

FIXTURE_ZLIB = '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'


def packets():
    return json.loads(zlib.decompress(base64.b64decode(FIXTURE_ZLIB)))


def refresh(original, exports):
    for record, role in zip(original["native_records"], ("parent_export", "child_export"), strict=True):
        exported = exports[role]
        report = exported["report"]
        provenance = report["codebase_provenance"]
        for batch in tool.BATCH_ROLES:
            for target in provenance[batch]:
                details = target["validation"][0]["details"]
                target["source_digest"] = audit._sha(audit._canonical({"target_schema": audit.NATIVE_TARGET_SCHEMA,
                    "source_binding": details["source_binding"], "authored_contracts": details["authored_contracts"]}))
        for prefix in ("training", "tuning"):
            values = provenance[prefix + "_targets"]
            report[prefix + "_target_count"] = len(values)
            report[prefix + "_targets_sha256"] = audit._sha(audit._canonical(values))
        report["feature_space_sha256"] = provenance["feature_space_sha256"] = audit._sha(audit._canonical(exported["feature_space"]))
        record["sha256"] = audit._sha(audit._canonical(exported) + b"\n")
    exports["parent_export"]["feature_space"]["training_targets_sha256"] = exports["parent_export"]["report"]["training_targets_sha256"]
    # Both copies deliberately retain one frozen basis, even in forged packets.
    exports["child_export"]["feature_space"] = copy.deepcopy(exports["parent_export"]["feature_space"])
    for record, role in zip(original["native_records"], ("parent_export", "child_export"), strict=True):
        exported = exports[role]
        exported["report"]["feature_space_sha256"] = exported["report"]["codebase_provenance"]["feature_space_sha256"] = audit._sha(audit._canonical(exported["feature_space"]))
        record["sha256"] = audit._sha(audit._canonical(exported) + b"\n")


def source_rebind(target, raw, *, literal=None):
    details = target["validation"][0]["details"]
    binding = details["source_binding"]
    details["source_bytes_hex"] = raw.hex()
    binding["content_sha256"] = audit._sha(raw)
    binding["source_cid"] = binding["entry"]["source_cid"] = audit._raw_source_cid(raw)
    binding["entry"]["size_bytes"] = len(raw)
    details["native_program"]["sources"][0]["content_sha256"] = audit._sha(raw)
    if literal is not None:
        details["native_program"]["expressions"][1]["attributes"]["value"] = literal
        target["projections"][0]["expression"] = tool._program_view(details["native_program"])
        for span in details["correspondence"]["spans"]:
            span["source_text"] = raw[span["start_byte"]:span["end_byte"]].decode()


class NativeFeatureCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.original, self.exports = packets()

    def material(self):
        refresh(self.original, self.exports)
        bodies = {"provenance_input": self.original, **self.exports}
        names = {"provenance_input": "input.json", "parent_export": "parent-export.json", "child_export": "child-export.json"}
        spec = {"schema": tool.INPUT_SCHEMA}
        for role, document in bodies.items():
            path = self.inputs / names[role]
            raw = audit._canonical(document) + b"\n"
            path.write_bytes(raw)
            spec[role] = {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}
        manifest = self.inputs / "feature-input.json"
        manifest.write_bytes(audit._canonical(spec) + b"\n")
        return manifest, spec

    def run_case(self, *, output=None, limits=tool.DEFAULT_LIMITS):
        manifest, _ = self.material()
        return tool.evaluate(manifest, output or self.root / "result", limits)

    def target(self, role="child_export", batch="training_targets", index=0):
        return self.exports[role]["report"]["codebase_provenance"][batch][index]

    def assert_refused(self):
        with self.assertRaises((audit.AuditInputError, KeyError, TypeError, ValueError)):
            self.run_case()

    def test_literal_contrasts_have_independent_golden_counts_and_original_roles(self):
        report = self.run_case()
        self.assertEqual(9, report["historical_target_count"])
        self.assertEqual(4, report["unique_source_count"])
        self.assertEqual(53, report["frozen_basis_column_count"])
        self.assertEqual({"train": 3, "tune": 2, "canary": 2, "replay": 2}, report["role_counts"])
        self.assertEqual(5, report["out_of_vocabulary_atom_count"])
        self.assertEqual(5, report["out_of_vocabulary_target_count"])
        self.assertEqual(18, report["unknown_sort_occurrence_count"])
        self.assertEqual(1, report["distinguishing_collision_group_count"])
        collision = next(g for g in report["collision_groups"] if g["different_source_labels_same_signature"])
        self.assertEqual([2, 3, 5], collision["source_literals"])
        self.assertEqual(["canary", "train", "tune"], collision["original_roles"])
        self.assertEqual(5, len(collision["member_ids"]))
        self.assertTrue(collision["cross_role_literal_collision"])
        by_literal = {}
        for row in report["targets"]:
            value = row["source_label"]["body"]["right"]["value"]
            by_literal[value] = row["frozen_basis_signature_sha256"]
            self.assertEqual(53, row["scalar_atom_count"])
            self.assertEqual(53 if value == 1 else 52, sum(row["frozen_basis_counts"]))
        self.assertNotEqual(by_literal[1], by_literal[2])
        self.assertEqual(by_literal[2], by_literal[3])
        self.assertEqual(by_literal[3], by_literal[5])

    def test_unknowns_and_native_execution_are_not_upgraded(self):
        report = self.run_case()
        self.assertTrue(all(report[name] is True for name in tool.TRUE_FLAGS))
        self.assertTrue(all(report[name] is False for name in tool.FALSE_FLAGS))
        self.assertEqual(0, report["additional_attempted_training_epochs"])
        self.assertEqual(0, report["new_final_assignments"])
        self.assertFalse(report["normalization_applied_by_auditor"])
        self.assertEqual(2, len(report["targets"][0]["unknown_sort_inventory"]))
        self.assertFalse(report["contract_identities"]["parent_export"]["producer_identity_recipe_verified"])

    def test_native_state_is_inert_and_not_decoded(self):
        self.exports["parent_export"]["state"] = {"unknown_numeric_layout": ["not interpreted"]}
        self.exports["child_export"]["state"] = {"another_layout": None}
        report = self.run_case()
        self.assertFalse(report["optimizer_state_replayed"])
        self.assertFalse(report["native_feature_vector_execution_replayed"])

    def test_new_literal_remains_same_signature_without_new_numeric_work(self):
        target = self.target()
        source_rebind(target, b"def step(n: int) -> int:\n    return n + 7\n", literal=7)
        report = self.run_case()
        row = next(r for r in report["targets"] if r["version_id_claim"] == self.original["native_records"][1]["version_id"] and r["original_role"] == "train")
        self.assertEqual(7, row["source_label"]["body"]["right"]["value"])
        self.assertEqual(52, sum(row["frozen_basis_counts"]))

    def test_unsupported_source_disposition_preserves_target_and_any_sorts(self):
        source_rebind(self.target(), b"def step(n: str) -> str:\n    return n + 2\n")
        report = self.run_case()
        self.assertEqual(9, report["historical_target_count"])
        self.assertEqual(1, report["unsupported_source_target_count"])
        self.assertEqual(18, report["unknown_sort_occurrence_count"])
        unsupported = next(r for r in report["targets"] if r["source_label"] is None)
        self.assertIn("annotation", unsupported["source_label_reason"])

    def test_multibyte_comment_requires_byte_span_rebinding(self):
        target = self.target()
        details = target["validation"][0]["details"]
        raw = bytes.fromhex(details["source_bytes_hex"])
        prefix = "# λ\n".encode()
        source_rebind(target, prefix + raw)
        for span in details["native_program"]["spans"] + details["correspondence"]["spans"]:
            span["start_byte"] += len(prefix)
            span["end_byte"] += len(prefix)
        report = self.run_case()
        self.assertEqual(0, report["unsupported_source_target_count"])
        self.assertEqual(1, report["distinguishing_collision_group_count"])

    def test_scalar_atom_type_path_and_value_are_distinct(self):
        atoms = tool._atoms({"x": [True, 1, 1.0, None, "1"]}, tool.DEFAULT_LIMITS)
        self.assertEqual(5, len(atoms))
        self.assertEqual(5, sum(atoms.values()))
        self.assertIn('[["x",0],true]', atoms)
        self.assertIn('[["x",1],1]', atoms)
        self.assertIn('[["x",2],1.0]', atoms)
        self.assertEqual({}, tool._atoms({"empty": []}, tool.DEFAULT_LIMITS))

    def test_source_bytes_cannot_change_under_old_source_binding(self):
        self.target()["validation"][0]["details"]["source_bytes_hex"] = b"def step(n: int) -> int:\n    return n + 9\n".hex()
        self.assert_refused()

    def test_rehashed_source_body_does_not_change_native_teacher_literal(self):
        source_rebind(self.target(), b"def step(n: int) -> int:\n    return n + 9\n")
        self.assert_refused()

    def test_operator_and_operand_forgeries_retain_outer_and_inner_pins(self):
        graph = self.target()["validation"][0]["details"]["native_program"]
        graph["expressions"][2]["operator"] = "sub"
        self.target()["projections"][0]["expression"] = tool._program_view(graph)
        self.assert_refused()

    def test_ordered_reference_forgery_cannot_be_hidden_in_feature_view(self):
        graph = self.target()["validation"][0]["details"]["native_program"]
        graph["expressions"][2]["operand_ids"].reverse()
        graph["expressions"][2]["evaluation_order"].reverse()
        self.target()["projections"][0]["expression"] = tool._program_view(graph)
        self.assert_refused()

    def test_return_forgery_changes_raw_and_projected_graphs(self):
        graph = self.target()["validation"][0]["details"]["native_program"]
        graph["commands"][0]["expression_ids"] = [graph["expressions"][0]["expression_id"]]
        self.target()["projections"][0]["expression"] = tool._program_view(graph)
        self.assert_refused()

    def test_correlated_span_text_and_offsets_still_require_exact_ast_bytes(self):
        details = self.target()["validation"][0]["details"]
        details["native_program"]["spans"][0]["start_byte"] = 1
        details["correspondence"]["spans"][0]["start_byte"] = 1
        details["correspondence"]["spans"][0]["source_text"] = details["correspondence"]["spans"][0]["source_text"][1:]
        self.assert_refused()

    def test_source_reference_hash_and_revision_are_independent_of_target_digest(self):
        self.target()["validation"][0]["details"]["native_program"]["sources"][0]["content_sha256"] = "0" * 64
        self.assert_refused()

    def test_bool_literal_does_not_alias_integer_one(self):
        graph = self.target()["validation"][0]["details"]["native_program"]
        graph["expressions"][1]["attributes"]["value"] = True
        self.target()["projections"][0]["expression"] = tool._program_view(graph)
        self.assert_refused()

    def test_unknown_sort_inventory_cannot_silently_drop_any(self):
        self.target()["validation"][0]["details"]["unknown_inventory"] = []
        self.assert_refused()

    def test_any_is_not_refined_by_source_annotation_alone(self):
        self.target()["projections"][0]["expression"]["document"]["expressions"][0]["type_ref"] = "int"
        self.assert_refused()

    def test_projection_descriptor_and_authority_escalations_are_refused(self):
        self.target()["projections"][0]["feature_only"] = False
        self.assert_refused()

    def test_correlated_basis_vocabulary_extension_is_not_exact_continuation(self):
        basis = self.exports["parent_export"]["feature_space"]
        basis["columns"].append(["codebase_ir.program@1", '[["document","expressions",1,"attributes","value"],2]'])
        basis["columns"].sort()
        self.assert_refused()

    def test_duplicate_and_boolean_path_columns_are_refused(self):
        basis = self.exports["parent_export"]["feature_space"]
        basis["columns"].append(copy.deepcopy(basis["columns"][0]))
        self.assert_refused()
        _, self.exports = packets()
        self.exports["parent_export"]["feature_space"]["columns"][0][1] = '[[true],"contracts"]'
        self.assert_refused()

    def test_missing_target_batch_and_unknown_source_roles_are_refused(self):
        self.exports["child_export"]["report"]["codebase_provenance"]["canary_targets"] = []
        self.assert_refused()

    def test_correlated_selection_and_batch_role_swaps_preserve_independent_roles(self):
        provenance = self.exports["child_export"]["report"]["codebase_provenance"]
        for selection in provenance["selections"]:
            if selection["path"] == "canary.py":
                selection["role"] = "train"
            elif selection["path"] == "train.py":
                selection["role"] = "canary"
        self.assert_refused()
        self.original, self.exports = packets()
        provenance = self.exports["child_export"]["report"]["codebase_provenance"]
        provenance["training_targets"], provenance["tuning_targets"] = provenance["tuning_targets"], provenance["training_targets"]
        self.assert_refused()
        _, self.exports = packets()
        self.exports["child_export"]["report"]["codebase_provenance"]["selections"][0]["role"] = "final"
        self.assert_refused()

    def test_wrong_parent_label_is_not_a_new_generation(self):
        self.exports["child_export"]["report"]["codebase_provenance"]["parent_version_id"] = "sha256:wrong"
        self.assert_refused()

    def test_original_export_selector_repin_cannot_detach_counterparty_body(self):
        manifest, spec = self.material()
        original_path = Path(spec["provenance_input"]["path"])
        original = json.loads(original_path.read_bytes())
        original["native_records"][0]["sha256"] = "0" * 64
        raw = audit._canonical(original) + b"\n"
        original_path.write_bytes(raw)
        spec["provenance_input"]["sha256"] = audit._sha(raw)
        spec["provenance_input"]["size_bytes"] = len(raw)
        manifest.write_bytes(audit._canonical(spec) + b"\n")
        with self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")

    def test_exact_source_target_descriptor_sizes_and_aggregate_caps_precede_reads(self):
        manifest, spec = self.material()
        spec["parent_export"]["size_bytes"] += 1
        manifest.write_bytes(audit._canonical(spec) + b"\n")
        with self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")
        manifest, _ = self.material()
        for limits in (replace(tool.DEFAULT_LIMITS, max_total_bytes=1024), replace(tool.DEFAULT_LIMITS, max_files=3),
                       replace(tool.DEFAULT_LIMITS, max_targets=8), replace(tool.DEFAULT_LIMITS, max_columns=52),
                       replace(tool.DEFAULT_LIMITS, max_atoms=50)):
            with self.assertRaises(audit.AuditInputError):
                tool.evaluate(manifest, self.root / "result", limits)

    def test_strict_json_and_inert_large_numeric_scalars_are_refused(self):
        manifest, _ = self.material()
        manifest.write_bytes(b'{"schema":"x","schema":"y"}')
        with self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")
        with self.assertRaises(audit.AuditInputError):
            tool._atoms({"value": 10**400}, tool.DEFAULT_LIMITS)
        with self.assertRaises(audit.AuditInputError):
            tool._atoms({"value": float("inf")}, tool.DEFAULT_LIMITS)

    def test_original_scope_and_existing_output_are_protected(self):
        manifest, _ = self.material()
        for output in (self.inputs / "new-output", self.inputs, manifest):
            with self.assertRaises(audit.AuditInputError):
                tool.evaluate(manifest, output)

    def test_symlink_input_aliases_are_refused(self):
        manifest, spec = self.material()
        path = Path(spec["child_export"]["path"])
        path.unlink()
        path.symlink_to(spec["parent_export"]["path"])
        with self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")

    def test_hardlink_input_alias_is_refused_before_counterparty_repins(self):
        manifest, spec = self.material()
        parent = Path(spec["parent_export"]["path"])
        child = Path(spec["child_export"]["path"])
        child.unlink()
        os.link(parent, child)
        spec["child_export"]["sha256"] = spec["parent_export"]["sha256"]
        spec["child_export"]["size_bytes"] = spec["parent_export"]["size_bytes"]
        manifest.write_bytes(audit._canonical(spec) + b"\n")
        with self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")

    def test_late_original_drift_after_copy_is_refused(self):
        manifest, spec = self.material()
        victim = Path(spec["child_export"]["path"])
        regular = tool.final.Capture.regular
        def change(path, maximum):
            raw = regular(path, maximum)
            if path.name.startswith("input-03-"):
                victim.write_bytes(victim.read_bytes() + b" ")
            return raw
        with mock.patch.object(tool.final.Capture, "regular", side_effect=change), self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")

    def test_late_retained_copy_drift_is_refused(self):
        manifest, _ = self.material()
        regular = tool.final.Capture.regular
        calls = Counter()
        def change(path, maximum):
            if path.name.startswith("input-03-"):
                calls[path] += 1
                if calls[path] == 2:
                    path.write_bytes(path.read_bytes() + b" ")
            return regular(path, maximum)
        with mock.patch.object(tool.final.Capture, "regular", side_effect=change), self.assertRaises(audit.AuditInputError):
            tool.evaluate(manifest, self.root / "result")

    def test_report_is_deterministic_and_all_retained_inputs_match(self):
        manifest, _ = self.material()
        one = tool.evaluate(manifest, self.root / "one")
        two = tool.evaluate(manifest, self.root / "two")
        for report in (one, two):
            for row in report["input_files"]:
                self.assertEqual(Path(row["path"]).read_bytes(), Path(row["retained_path"]).read_bytes())
        for value in (one, two):
            for row in value["input_files"]:
                row.pop("retained_path")
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
