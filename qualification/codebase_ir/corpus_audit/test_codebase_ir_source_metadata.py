"""Source reconstruction controls independent of production trainers/owners."""
from __future__ import annotations

import copy
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codebase_ir_corpus_audit as audit
import codebase_ir_source_metadata as metadata
from test_codebase_ir_corpus_audit import clean_manifest, native_provenance, source_unit


class SourceMetadataControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="source-metadata-controls-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def manifest(self, value: dict, name: str = "input.json") -> Path:
        path = self.root / name
        path.write_bytes(audit._canonical(value))
        return path

    def export(self, value: dict, *, accept: bool = False, name: str = "output", limits=audit.DEFAULT_LIMITS) -> dict:
        return metadata.export_metadata(self.manifest(value), self.root / name,
                                        accept_supplied_scope=accept, limits=limits)

    def source_report(self, report, unit_id):
        return next(row for row in report["source_metadata"] if row["unit_id"] == unit_id)

    def codes(self, report, unit_id):
        return {row["code"] for row in self.source_report(report, unit_id)["frontiers"]}

    def native_manifest(self, *, with_parent=True, duplicate_target=False):
        value = clean_manifest()
        value["units"] = [value["units"][3]]
        records = []
        for version, parent in (("root", None), ("child", "root")):
            provenance = native_provenance(parent)
            if version == "root" and duplicate_target:
                provenance["training_targets"].append(copy.deepcopy(provenance["training_targets"][0]))
            raw = audit._canonical({"report": {"codebase_provenance": provenance}})
            path = self.root / (version + ".json")
            path.write_bytes(raw)
            records.append({"version_id": version, "file": path.name, "sha256": audit._sha(raw), "unit_metadata": {}})
        value["native_records"] = records if with_parent else records[1:]
        return value

    def test_default_preserves_unreviewed_native_claims_but_records_resolved_scope(self):
        value = self.native_manifest()
        report = self.export(value)
        self.assertEqual(report["candidate_audit_status"], "incomplete")
        self.assertFalse(report["whole_repository_coverage"])
        self.assertFalse(report["unseen_rename_ancestry_verified"])
        self.assertFalse(report["accept_supplied_scope_caller_claim"])
        self.assertTrue(all(row["static_source_scope_resolved"] for row in report["source_metadata"]))
        row = self.source_report(report, "native/root/training_targets/0")
        self.assertFalse(row["candidate_claims"]["dependencies_complete"])
        self.assertEqual(report["source_unit_count"], 9)
        self.assertFalse(report["training_executed"])
        self.assertFalse(report["final_sources_used_for_fitting"])

    def test_explicit_scope_claim_is_bounded_and_native_heads_targets_pinned(self):
        report = self.export(self.native_manifest(), accept=True)
        self.assertEqual(report["candidate_audit_status"], "clean")
        self.assertTrue(report["candidate_complete_for_declared_scope"])
        self.assertFalse(report["whole_repository_coverage"])
        self.assertFalse(report["native_registry_receipts_verified"])
        self.assertEqual(len(report["native_heads"]), 2)
        self.assertEqual(len(report["native_target_bindings"]), 8)
        for head in report["native_heads"]:
            self.assertEqual(head["head_sha256"], audit._sha(audit._canonical(head["head"])))
        candidate = json.loads((self.root / "output" / "candidate_manifest.json").read_bytes())
        self.assertEqual([row["version_id"] for row in candidate["native_records"]], ["child", "root"])
        replay = next(row for row in candidate["native_records"] if row["version_id"] == "root")
        self.assertIn("native/root/replay_targets/0", replay["unit_metadata"])

    def test_duplicate_targets_keep_index_and_projection_source_identities(self):
        report = self.export(self.native_manifest(duplicate_target=True), accept=True)
        self.assertEqual(report["candidate_audit_status"], "clean")
        identities = {row["unit_id"] for row in report["source_metadata"]}
        self.assertIn("native/root/training_targets/0", identities)
        self.assertIn("native/root/training_targets/1", identities)
        groups = report["observed_ast_clone_groups"]
        self.assertTrue(any({"native/root/training_targets/0", "native/root/training_targets/1"}
                            <= set(row["unit_ids"]) for row in groups))

    def test_simple_import_connects_final_to_train_helper(self):
        value = clean_manifest()
        value["units"][0]["path"] = "helper.py"
        value["units"][3] = source_unit("final", "final", b"import helper\n\ndef consume(n):\n    return helper.increment(n) * 7\n")
        report = self.export(value)
        self.assertEqual(self.source_report(report, "final")["dependencies"], ["train"])
        self.assertEqual(report["candidate_audit_status"], "leaks_found")
        self.assertIn("dependency_connected", {row["kind"] for row in report["candidate_leaks"]})

    def package_manifest(self, consumer_path="pkg/use.py", import_line="from .helper import add"):
        value = clean_manifest()
        value["units"].extend([
            source_unit("pkg-init", "train", b"from .helper import add\n", path="pkg/__init__.py"),
            source_unit("pkg-helper", "train", b"def add(value):\n    return value * 7\n", path="pkg/helper.py"),
            source_unit("pkg-sub-init", "train", b"PACKAGE_MARKER = 7\n", path="pkg/sub/__init__.py"),
        ])
        value["units"][3] = source_unit("final", "final", (import_line + "\n\ndef consume(n):\n    return add(n)\n").encode(), path=consumer_path)
        return value

    def test_package_absolute_relative_and_parent_import_resolution(self):
        cases = [("pkg/use.py", "from .helper import add"), ("pkg/use.py", "from pkg.helper import add"),
                 ("pkg/sub/use.py", "from ..helper import add")]
        for index, (path, line) in enumerate(cases):
            with self.subTest(path=path, line=line):
                report = self.export(self.package_manifest(path, line), name="output" + str(index))
                row = self.source_report(report, "final")
                self.assertTrue(row["static_source_scope_resolved"], row["frontiers"])
                self.assertIn("pkg-init", row["dependencies"])
                self.assertIn("pkg-helper", row["dependencies"])
                if path.startswith("pkg/sub/"):
                    self.assertIn("pkg-sub-init", row["dependencies"])

    def test_missing_initializer_unknown_import_relative_escape_and_star_are_frontiers(self):
        cases = [
            ("use.py", b"import absent\n", "unresolved_import"),
            ("use.py", b"from .helper import add\n", "relative_import_beyond_supplied_package"),
            ("pkg/use.py", b"from ...helper import add\n", "relative_import_beyond_supplied_package"),
            ("use.py", b"from helper import *\n", "wildcard_import_frontier"),
            ("use.py", b"from helper import absent\n", "imported_symbol_unresolved"),
        ]
        for index, (path, raw, expected) in enumerate(cases):
            with self.subTest(path=path, expected=expected):
                value = clean_manifest()
                value["units"][0]["path"] = "helper.py"
                value["units"][3] = source_unit("final", "final", raw, path=path)
                report = self.export(value, accept=True, name="output" + str(index))
                self.assertIn(expected, self.codes(report, "final"))
                self.assertFalse(self.source_report(report, "final")["candidate_claims"]["dependencies_complete"])
        value = self.package_manifest()
        value["units"] = [row for row in value["units"] if row["id"] != "pkg-init"]
        report = self.export(value, accept=True, name="missing-init")
        self.assertIn("unresolved_import", self.codes(report, "final"))

    def test_dynamic_import_exec_unbound_global_and_attribute_calls_never_complete(self):
        cases = [
            (b"__import__('helper')\n", "dynamic_lookup_or_execution"),
            (b"import importlib\nimportlib.import_module('helper')\n", "dynamic_import"),
            (b"from importlib import import_module as load\nload('helper')\n", "dynamic_import_alias"),
            (b"exec('import helper')\n", "dynamic_lookup_or_execution"),
            (b"def consume(n):\n    return foreign(n)\n", "unresolved_global_name"),
            (b"def consume(n):\n    return n.read()\n", "dynamic_attribute_call"),
            (b"def consume(n):\n    import helper\n    return n\n", "conditional_or_local_import_frontier"),
        ]
        for index, (raw, expected) in enumerate(cases):
            with self.subTest(expected=expected):
                value = clean_manifest()
                value["units"][3] = source_unit("final", "final", raw)
                report = self.export(value, accept=True, name="output" + str(index))
                self.assertIn(expected, self.codes(report, "final"))
                self.assertFalse(self.source_report(report, "final")["candidate_claims"]["dependencies_complete"])
                self.assertFalse(report["candidate_complete_for_declared_scope"])

    def test_repeated_revisions_use_same_snapshot_or_mark_ambiguity(self):
        value = clean_manifest()
        value["units"][0]["path"] = "helper.py"
        value["units"].append(source_unit("helper-v1", "train", b"def increment(n):\n    return n + 9\n", path="helper.py", revision="fixture:revision1"))
        value["units"][3] = source_unit("final", "final", b"from helper import increment\n", revision="fixture:revision1")
        report = self.export(value, name="matched")
        self.assertEqual(self.source_report(report, "final")["dependencies"], ["helper-v1"])
        self.assertTrue(report["observed_revision_links"])
        self.assertTrue(all(not row["directed_ancestry_asserted"] for row in report["observed_revision_links"]))
        value["units"][3]["revision"] = "fixture:unseen"
        report = self.export(value, name="ambiguous", accept=True)
        self.assertEqual(self.source_report(report, "final")["dependencies"], ["helper-v1", "train"])
        self.assertIn("ambiguous_import_revision_or_module", self.codes(report, "final"))
        self.assertFalse(report["candidate_complete_for_declared_scope"])

    def test_missing_model_parent_blocks_revision_claim_even_opt_in(self):
        report = self.export(self.native_manifest(with_parent=False), accept=True)
        self.assertEqual(report["candidate_audit_status"], "incomplete")
        self.assertIn("native_parent_unavailable", {row["code"] for row in report["candidate_issues"]})
        self.assertFalse(self.source_report(report, "native/child/training_targets/0")["candidate_claims"]["revision_relations_complete"])

    def test_changed_literal_and_guard_keep_distinct_clone_groups(self):
        value = clean_manifest()
        value["units"][0] = source_unit("train", "train", b"def boundary(n):\n    if n > 0:\n        return n + 1\n    return 0\n")
        value["units"][1] = source_unit("tune", "tune", b"def boundary(n):\n    if n >= 0:\n        return n + 2\n    return 0\n")
        report = self.export(value)
        self.assertEqual(report["candidate_audit_status"], "clean")
        self.assertNotEqual(self.source_report(report, "train")["source_identity"]["normalized_ast_sha256"],
                            self.source_report(report, "tune")["source_identity"]["normalized_ast_sha256"])

    def test_scope_bindings_and_monkeypatch_forms_remain_frontiers(self):
        cases = [
            (b"def f(values):\n    [x for x in values]\n    return x\n", "comprehension_scope_frontier"),
            (b"def f(n):\n    try:\n        return n\n    except ValueError as error:\n        return 0\n", "exception_binding_scope_frontier"),
            (b"def f(n):\n    global outside\n    outside = n\n    return n\n", "global_rebinding_frontier"),
            (b"def f(n):\n    if (x := n):\n        return x\n    return 0\n", "assignment_expression_scope_frontier"),
            (b"def f(n):\n    match n:\n        case x:\n            return x\n", "pattern_binding_scope_frontier"),
            (b"import helper\nhelper.increment = 1\n", "attribute_rebinding_frontier"),
            (b"import helper\nhelper.__dict__['increment'] = 1\n", "module_namespace_mutation_frontier"),
            (b"def f(*values: MissingType):\n    return 1\n", "unresolved_global_name"),
        ]
        for index, (raw, expected) in enumerate(cases):
            with self.subTest(expected=expected):
                value = clean_manifest()
                value["units"][0]["path"] = "helper.py"
                value["units"][3] = source_unit("final", "final", raw)
                report = self.export(value, accept=True, name="scope" + str(index))
                self.assertIn(expected, self.codes(report, "final"))
                self.assertFalse(self.source_report(report, "final")["candidate_claims"]["dependencies_complete"])

    def test_manifest_read_race_rejected_before_unreviewed_second_load(self):
        original = clean_manifest()
        path = self.manifest(original)
        changed = copy.deepcopy(original)
        changed["units"][0]["role"] = "final"
        altered_raw = audit._canonical(changed)
        real_read = audit._read_bounded
        count = 0

        def racing_read(input_path, maximum):
            nonlocal count
            if Path(input_path) == path:
                count += 1
                if count == 2:
                    return altered_raw
            return real_read(input_path, maximum)

        with mock.patch.object(audit, "_read_bounded", side_effect=racing_read):
            with self.assertRaisesRegex(audit.AuditInputError, "manifest changed"):
                metadata.export_metadata(path, self.root / "race-output")
        self.assertFalse((self.root / "race-output").exists())

    def test_renamed_ancestral_final_clone_and_relation_are_detected(self):
        value = self.native_manifest()
        target = native_provenance()["training_targets"][0]
        raw = bytes.fromhex(target["validation"][0]["details"]["source_bytes_hex"])
        value["units"] = [source_unit("final", "final", b"# renamed final negative control\n" + raw,
                                      path="renamed.py", related_revisions=["native/root/training_targets/0"])]
        report = self.export(value, accept=True)
        self.assertEqual(report["candidate_audit_status"], "leaks_found")
        self.assertTrue({"normalized_ast", "related_revision"} <= {row["kind"] for row in report["candidate_leaks"]})

    def test_candidate_outputs_are_deterministic_private_and_do_not_overwrite(self):
        value = self.native_manifest()
        first = self.export(value, name="first")
        second = self.export(value, name="second")
        self.assertEqual(first, second)
        for name in ("candidate_manifest.json", "candidate_audit_report.json", "reconstruction_report.json"):
            left, right = self.root / "first" / name, self.root / "second" / name
            self.assertEqual(left.read_bytes(), right.read_bytes())
            self.assertEqual(stat.S_IMODE(left.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.root / "first").stat().st_mode), 0o700)
        with self.assertRaises(audit.AuditInputError):
            self.export(value, name="first")

    def test_aggregate_budgets_duplicates_and_tampering_rejected(self):
        value = clean_manifest()
        supplement = self.manifest(value, "supplement.json")
        with self.assertRaisesRegex(audit.AuditInputError, "duplicate unit"):
            metadata.export_metadata(self.manifest(value), self.root / "duplicates", supplement_paths=(supplement,))
        with self.assertRaises(audit.AuditInputError):
            self.export(value, limits=audit.Limits(max_units=3))
        value["units"][0]["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(audit.AuditInputError, "digest differs"):
            self.export(value)
        value = self.native_manifest()
        value["native_records"][0]["sha256"] = "0" * 64
        with self.assertRaises(audit.AuditInputError):
            self.export(value)

    def test_supplement_final_fixture_preserves_role_and_cli_success_for_incomplete(self):
        value = self.native_manifest()
        value["units"] = []
        supplemental = {"schema": audit.INPUT_SCHEMA, "units": [clean_manifest()["units"][3]],
                        "native_records": [], "ancestral_training": [], "ancestry_complete": True}
        supplement = self.manifest(supplemental, "final.json")
        path = self.manifest(value)
        completed = subprocess.run([sys.executable, str(Path(metadata.__file__)), "--manifest", str(path),
                                    "--supplement", str(supplement), "--output", str(self.root / "cli")],
                                   capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads((self.root / "cli" / "reconstruction_report.json").read_bytes())
        self.assertEqual(report["candidate_audit_status"], "incomplete")
        self.assertEqual(self.source_report(report, "final")["source_identity"]["role"], "final")
        self.assertFalse(report["promotion_decisions_made"])
        self.assertFalse(report["final_sources_used_for_fitting"])

    def test_authored_final_sources_match_pinned_manifest(self):
        root = Path(__file__).parent
        manifest = json.loads((root / "examples" / "untouched_final_input.json").read_bytes())
        for row in manifest["units"]:
            raw = (root / "fixtures" / "untouched_final" / row["path"]).read_bytes()
            self.assertEqual(row["source"]["bytes_hex"], raw.hex())
            self.assertEqual(row["content_sha256"], audit._sha(raw))
            self.assertEqual(row["role"], "final")


if __name__ == "__main__":
    unittest.main()
