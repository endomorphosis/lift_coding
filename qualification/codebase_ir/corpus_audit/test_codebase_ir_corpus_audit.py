"""Adversarial controls for the standalone source split auditor."""
from __future__ import annotations

import copy
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codebase_ir_corpus_audit as audit


def source_unit(name: str, role: str, raw: bytes, **changes) -> dict:
    row = {
        "id": name, "role": role, "repository_id": "fixture:corpus", "path": name + ".py",
        "revision": "fixture:revision0", "content_sha256": hashlib.sha256(raw).hexdigest(),
        "source": {"bytes_hex": raw.hex()}, "dependencies": [], "dependencies_complete": True,
        "related_revisions": [], "revision_relations_complete": True,
    }
    row.update(changes)
    return row


def clean_manifest() -> dict:
    return {
        "schema": audit.INPUT_SCHEMA,
        "units": [source_unit(role, role, f"def increment(n):\n    return n + {index}\n".encode())
                  for index, role in enumerate(audit.ROLES, 1)],
        "native_records": [], "ancestral_training": [], "ancestry_complete": True,
    }


def native_target(path: str, raw: bytes, snapshot: str = "fixture:snapshot0") -> dict:
    binding = {
        "schema": audit.NATIVE_BINDING_SCHEMA,
        "head": {"schema": "codebase-head@1", "repository_id": "fixture:native", "generation": 1,
                 "snapshot_cid": snapshot, "manifest_cid": "fixture:manifest", "receipt_cid": "fixture:receipt",
                 "ast_revision_id": f"rev:fixture:native:snapshot:{snapshot}"},
        "repository_id": "fixture:native", "path": path, "source_key": "raw:" + path.encode().hex(),
        "entry": {"path": path, "size_bytes": len(raw), "source_cid": audit._raw_source_cid(raw),
                  "raw_path_hex": path.encode().hex(), "entry_cid": "fixture:entry"},
        "source_cid": audit._raw_source_cid(raw), "content_sha256": hashlib.sha256(raw).hexdigest(),
        "unit": {"schema": "codebase-ir-structural-unit@1", "source_key": "raw:" + path.encode().hex(),
                 "entry_cid": "fixture:entry", "ast_cid": "fixture:ast", "parse_status": "ok"},
        "ast_cid": "fixture:ast",
        "source_revision": "snapshot:" + snapshot,
    }
    target_identity = {"target_schema": audit.NATIVE_TARGET_SCHEMA,
                       "source_binding": binding, "authored_contracts": []}
    return {
        "schema_version": "autoencoder-domain-targets/v1", "domain_id": "codebase_ir",
        "source_digest": hashlib.sha256(audit._canonical(target_identity)).hexdigest(),
        "projections": [], "validation": [{"validator_id": "codebase_ir.exact_native_target_replay@1",
            "details": {**target_identity, "source_bytes_hex": raw.hex()}}],
        "unsupported": [], "qualification_gaps": [], "ready_for_training": False,
        "qualified": False, "admitted": False, "formalized": False,
    }


def native_provenance(parent: str | None = None) -> dict:
    target_rows = {role: native_target(role + ".py", f"def f(n):\n    return n + {index}\n".encode())
                   for index, role in enumerate(("train", "tune", "canary"), 1)}
    value = dict.fromkeys(audit.NATIVE_PROVENANCE_FIELDS, False)
    value.update({
        "schema": audit.NATIVE_LINEAGE_SCHEMA, "head": {"repository_id": "fixture:native"},
        "selections": [{"path": role + ".py", "role": role, "contracts": []}
                       for role in ("train", "tune", "canary")],
        "parent_version_id": parent, "continuation": "fresh_feature_basis" if parent is None else "exact_frozen_basis_adam_resume",
        "training_targets": [target_rows["train"]], "tuning_targets": [target_rows["tune"]],
        "canary_targets": [target_rows["canary"]], "replay_targets": [copy.deepcopy(target_rows["train"])],
        "ancestral_training": [] if parent is None else [{"repository_id": "fixture:native",
            "path": "train.py", "source_digest": target_rows["train"]["validation"][0]["details"]["source_binding"]["content_sha256"]}],
    })
    return value


class CorpusAuditControls(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="corpus-audit-controls-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def run_audit(self, value: dict, limits: audit.Limits = audit.DEFAULT_LIMITS) -> dict:
        path = self.root / "manifest.json"
        path.write_bytes(audit._canonical(value))
        return audit.audit_manifest(path, limits)

    def kinds(self, report: dict) -> set[str]:
        return {row["kind"] for row in report["leaks"]}

    def codes(self, report: dict) -> set[str]:
        return {row["code"] for row in report["issues"]}

    def native_export(self, value: dict, version: str = "root", metadata: dict | None = None) -> dict:
        path = self.root / (version + ".json")
        raw = audit._canonical(value)
        path.write_bytes(raw)
        return {"version_id": version, "file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                "unit_metadata": {} if metadata is None else metadata}

    def test_clean_control_has_all_four_roles_and_deterministic_report(self):
        manifest = clean_manifest()
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "clean")
        self.assertTrue(report["complete_for_declared_scope"])
        self.assertTrue(report["leak_free_within_declared_scope"])
        self.assertEqual(report["leaks"], [])
        self.assertEqual(report, self.run_audit(manifest))
        self.assertFalse(report["training_executed"])
        self.assertFalse(report["proof_authority"])

    def test_exact_bytes_and_normalized_clone_cross_roles(self):
        manifest = clean_manifest()
        manifest["units"][1] = source_unit("tune", "tune", bytes.fromhex(manifest["units"][0]["source"]["bytes_hex"]))
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "leaks_found")
        self.assertTrue(report["complete_for_declared_scope"])
        self.assertIn("exact_bytes", self.kinds(report))
        self.assertIn("normalized_ast", self.kinds(report))

    def test_comments_parentheses_blank_lines_and_formatting_clone(self):
        manifest = clean_manifest()
        raw = b"# extra ordinary comment\n\ndef increment( n ):\n    # another comment\n    return (n+1)\n"
        manifest["units"][1] = source_unit("tune", "tune", raw)
        report = self.run_audit(manifest)
        self.assertIn("normalized_ast", self.kinds(report))
        self.assertNotIn("exact_bytes", self.kinds(report))

    def test_changed_guard_operator_and_literal_remain_distinct(self):
        pairs = [
            (b"def f(n):\n    return n + 1\n", b"def f(n):\n    return n + 2\n"),
            (b"def f(n):\n    return n + 1\n", b"def f(n):\n    return n - 1\n"),
            (b"def f(n):\n    if n > 0:\n        return n\n    return 0\n",
             b"def f(n):\n    if n >= 0:\n        return n\n    return 0\n"),
            (b"def f(n):\n    return True\n", b"def f(n):\n    return 1\n"),
            (b"def f(n):\n    return 'one'\n", b"def f(n):\n    return 'two'\n"),
        ]
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                manifest = clean_manifest()
                manifest["units"][:2] = [source_unit("train", "train", left), source_unit("tune", "tune", right)]
                self.assertEqual(self.run_audit(manifest)["status"], "clean")

    def test_names_docstrings_and_type_comments_retained(self):
        pairs = [
            (b"def f(n):\n    return n+1\n", b"def g(n):\n    return n+1\n"),
            (b"def f(n):\n    'doc one'\n    return n\n", b"def f(n):\n    'doc two'\n    return n\n"),
            (b"n = 1 # type: int\n", b"n = 1 # type: str\n"),
        ]
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                self.assertNotEqual(audit.normalized_ast_digest(left), audit.normalized_ast_digest(right))

    def test_unicode_exact_utf8_bytes_and_ast_clone(self):
        left = "def café(变量):\n    return 变量 + 1\n".encode()
        right = "# π\n\ndef café(变量):\n    return (变量+1)\n".encode()
        manifest = clean_manifest()
        manifest["units"][:2] = [source_unit("train", "train", left), source_unit("tune", "tune", right)]
        report = self.run_audit(manifest)
        self.assertIn("normalized_ast", self.kinds(report))
        row = next(row for row in report["units"] if row["id"] == "train")
        self.assertEqual(row["size_bytes"], len(left))
        self.assertGreater(row["size_bytes"], len(left.decode()))

    def test_transitive_dependency_connected_groups(self):
        manifest = clean_manifest()
        manifest["units"][0]["dependencies"] = ["tune"]
        manifest["units"][1]["dependencies"] = ["final"]
        report = self.run_audit(manifest)
        group = next(row for row in report["leaks"] if row["kind"] == "dependency_connected")
        self.assertEqual(group["unit_ids"], ["final", "train", "tune"])
        self.assertEqual(group["roles"], ["final", "train", "tune"])

    def test_revision_path_and_explicit_rename_groups(self):
        manifest = clean_manifest()
        manifest["units"][1]["path"] = "train.py"
        manifest["units"][1]["revision"] = "fixture:revision1"
        self.assertIn("same_repository_path", self.kinds(self.run_audit(manifest)))
        manifest["units"][1]["path"] = "renamed.py"
        manifest["units"][1]["related_revisions"] = ["train"]
        report = self.run_audit(manifest)
        self.assertIn("related_revision", self.kinds(report))
        self.assertNotIn("same_repository_path", self.kinds(report))

    def test_combined_clone_plus_dependency_transitive_closure(self):
        manifest = clean_manifest()
        raw = bytes.fromhex(manifest["units"][0]["source"]["bytes_hex"])
        manifest["units"][1] = source_unit("tune", "tune", raw, dependencies=["canary"])
        report = self.run_audit(manifest)
        group = next(row for row in report["leaks"] if row["kind"] == "combined_connected")
        self.assertEqual(group["unit_ids"], ["canary", "train", "tune"])
        self.assertEqual({edge["kind"] for edge in group["edges"]},
                         {"exact_bytes", "normalized_ast", "dependency_connected"})

    def test_missing_dependency_is_incomplete_and_shared_reference_still_groups(self):
        manifest = clean_manifest()
        manifest["units"][0]["dependencies"] = ["unknown-module"]
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["leak_free_within_declared_scope"])
        self.assertIn("unresolved_dependencies", self.codes(report))
        manifest["units"][1]["dependencies"] = ["unknown-module"]
        report = self.run_audit(manifest)
        self.assertIn("dependency_connected", self.kinds(report))
        self.assertFalse(report["complete_for_declared_scope"])

    def test_missing_revision_ancestry_and_role_never_look_clean(self):
        manifest = clean_manifest()
        manifest["units"].pop()
        manifest["ancestry_complete"] = False
        manifest["units"][0]["related_revisions"] = ["unknown-ancestor"]
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(self.codes(report), {"split_role_unavailable", "ancestry_not_declared_complete",
                                            "unresolved_related_revisions"})

    def test_unknown_metadata_never_looks_clean(self):
        manifest = clean_manifest()
        manifest["units"][0]["dependencies_complete"] = False
        manifest["units"][1]["revision_relations_complete"] = False
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(self.codes(report), {"dependencies_not_declared_complete",
                                            "revision_relations_not_declared_complete"})

    def test_exact_ancestor_source_join_detects_evaluation_exposure(self):
        manifest = clean_manifest()
        row = manifest["units"][1]
        manifest["ancestral_training"] = [{key: row[key] for key in ("repository_id", "path", "content_sha256")}]
        report = self.run_audit(manifest)
        self.assertIn("exact_bytes", self.kinds(report))
        self.assertIn("normalized_ast", self.kinds(report))
        self.assertTrue(report["complete_for_declared_scope"])
        ancestor = next(row for row in report["units"] if row["id"] == "ancestral/0")
        self.assertEqual(ancestor["role"], "train")
        self.assertTrue(ancestor["source_bytes_verified"])

    def test_missing_ancestor_bytes_still_detects_changed_evaluation_path(self):
        manifest = clean_manifest()
        row = manifest["units"][1]
        manifest["ancestral_training"] = [{"repository_id": row["repository_id"], "path": row["path"],
                                            "content_sha256": "f" * 64}]
        report = self.run_audit(manifest)
        self.assertIn("same_repository_path", self.kinds(report))
        self.assertIn("ancestral_source_unavailable", self.codes(report))
        self.assertFalse(report["complete_for_declared_scope"])

    def test_strict_roles_and_duplicate_ids(self):
        for role in ("training", "final_test", ["train"], None, 1, "Train", " train"):
            with self.subTest(role=role):
                manifest = clean_manifest()
                manifest["units"][0]["role"] = role
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(manifest)
        manifest = clean_manifest()
        manifest["units"][1]["id"] = "train"
        with self.assertRaisesRegex(audit.AuditInputError, "duplicate unit"):
            self.run_audit(manifest)

    def test_unknown_fields_ambiguous_sources_and_invalid_reference_lists(self):
        for field, value in (("dependencies", ["train", "train"]), ("dependencies", "train"),
                             ("dependencies_complete", 1), ("revision_relations_complete", None),
                             ("surprise", True), ("source", {"bytes_hex": "00", "file": "train.py"})):
            with self.subTest(field=field, value=value):
                manifest = clean_manifest()
                manifest["units"][0][field] = value
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(manifest)

    def test_tampered_source_rejected_before_ast_parse(self):
        manifest = clean_manifest()
        manifest["units"][0]["content_sha256"] = "0" * 64
        with mock.patch.object(audit, "normalized_ast_digest", side_effect=AssertionError("AST parsed early")):
            with self.assertRaisesRegex(audit.AuditInputError, "digest differs"):
                self.run_audit(manifest)

    def test_exact_file_source_binding_and_missing_traversal_symlink_controls(self):
        manifest = clean_manifest()
        raw = bytes.fromhex(manifest["units"][0]["source"]["bytes_hex"])
        (self.root / "train.py").write_bytes(raw)
        manifest["units"][0]["source"] = {"file": "train.py"}
        self.assertEqual(self.run_audit(manifest)["status"], "clean")
        for value in ("missing.py", "../train.py", str(self.root / "train.py"), "./train.py"):
            with self.subTest(value=value):
                manifest["units"][0]["source"] = {"file": value}
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(manifest)
        (self.root / "linked.py").symlink_to(self.root / "train.py")
        manifest["units"][0]["source"] = {"file": "linked.py"}
        with self.assertRaises(audit.AuditInputError):
            self.run_audit(manifest)

    def test_nonregular_source_rejected_without_blocking(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO control requires POSIX")
        os.mkfifo(self.root / "source.pipe")
        manifest = clean_manifest()
        manifest["units"][0]["source"] = {"file": "source.pipe"}
        with self.assertRaisesRegex(audit.AuditInputError, "regular input"):
            self.run_audit(manifest)

    def test_invalid_unicode_syntax_and_noncanonical_hex_rejected(self):
        for raw in (b"\xff", b"def incomplete(:\n", b"x = '\x00'\n"):
            with self.subTest(raw=raw):
                manifest = clean_manifest()
                manifest["units"][0] = source_unit("train", "train", raw)
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(manifest)
        manifest = clean_manifest()
        manifest["units"][0]["source"]["bytes_hex"] = "AA"
        with self.assertRaisesRegex(audit.AuditInputError, "canonical lowercase"):
            self.run_audit(manifest)

    def test_json_duplicate_keys_nonfinite_unicode_and_depth_rejected(self):
        path = self.root / "manifest.json"
        for raw in (b'{"schema":1,"schema":2}', b'{"x":NaN}', b'{"x":1e999}',
                    b'{"x":"\\ud800"}', b'{}\n{}', b'\xff'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaises(audit.AuditInputError):
                    audit.audit_manifest(path)
        path.write_bytes(b'{"x":' + b'[' * 100 + b'0' + b']' * 100 + b'}')
        with self.assertRaisesRegex(audit.AuditInputError, "depth budget"):
            audit.audit_manifest(path)

    def test_unit_json_source_total_and_link_budgets(self):
        for limits in (audit.Limits(max_units=2), audit.Limits(max_json_bytes=16),
                       audit.Limits(max_total_json_bytes=16), audit.Limits(max_source_bytes=8),
                       audit.Limits(max_total_source_bytes=50), audit.Limits(max_ast_nodes=2)):
            with self.subTest(limits=limits):
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(clean_manifest(), limits)
        manifest = clean_manifest()
        manifest["units"][0]["dependencies"] = ["tune", "canary"]
        with self.assertRaisesRegex(audit.AuditInputError, "link|dependency"):
            self.run_audit(manifest, audit.Limits(max_links=1))
        with self.assertRaisesRegex(audit.AuditInputError, "AST node/depth"):
            audit.normalized_ast_digest(b"x = " + b"+" * 70 + b"1\n", audit.Limits(max_ast_depth=8))

    def test_native_export_adapts_embedded_bytes_without_loading_trainer(self):
        manifest = clean_manifest()
        manifest["units"] = [manifest["units"][3]]
        manifest["native_records"] = [self.native_export({"report": {"codebase_provenance": native_provenance()}})]
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("dependencies_not_declared_complete", self.codes(report))
        self.assertFalse(report["native_replay_performed"])
        self.assertEqual(len(report["units"]), 5)
        self.assertNotIn("ipfs_datasets_py.logic.software_contracts.codebase_source_training", sys.modules)

    def test_native_explicit_metadata_can_complete_declared_source_scope(self):
        manifest = clean_manifest()
        manifest["units"] = [manifest["units"][3]]
        metadata = {f"native/root/{field}/0": {"dependencies": [], "dependencies_complete": True,
                    "related_revisions": [], "revision_relations_complete": True}
                    for field in ("training_targets", "tuning_targets", "canary_targets", "replay_targets")}
        manifest["native_records"] = [self.native_export(native_provenance(), metadata=metadata)]
        report = self.run_audit(manifest)
        self.assertEqual(report["status"], "clean")
        self.assertFalse(report["native_replay_performed"])

    def test_native_parent_child_ancestry_and_unavailable_parent(self):
        manifest = clean_manifest()
        manifest["units"] = [manifest["units"][3]]
        root = self.native_export(native_provenance(), "root")
        child = self.native_export(native_provenance("root"), "child")
        manifest["native_records"] = [child, root]
        report = self.run_audit(manifest)
        self.assertNotIn("native_parent_unavailable", self.codes(report))
        self.assertNotIn("ancestral_source_unavailable", self.codes(report))
        self.assertEqual(len([row for row in report["units"] if row["origin"] == "ancestral_training"]), 1)
        manifest["native_records"] = [child]
        report = self.run_audit(manifest)
        self.assertIn("native_parent_unavailable", self.codes(report))
        self.assertFalse(report["complete_for_declared_scope"])

    def test_native_changed_ancestry_identity_and_cycle_are_rejected(self):
        root = native_provenance()
        child = native_provenance("root")
        child["ancestral_training"][0]["source_digest"] = "f" * 64
        manifest = clean_manifest()
        manifest["native_records"] = [self.native_export(root, "root"), self.native_export(child, "child")]
        with self.assertRaisesRegex(audit.AuditInputError, "ancestry training identities"):
            self.run_audit(manifest)
        first, second = native_provenance("second"), native_provenance("first")
        manifest["native_records"] = [self.native_export(first, "first"), self.native_export(second, "second")]
        with self.assertRaisesRegex(audit.AuditInputError, "cyclic native ancestry"):
            self.run_audit(manifest)

    def test_native_tamper_export_hash_embedded_bytes_and_source_binding(self):
        for variant in ("file_digest", "embedded_bytes", "target_digest", "head", "authority", "unknown_metadata"):
            with self.subTest(variant=variant):
                provenance = native_provenance()
                target = provenance["training_targets"][0]
                if variant == "embedded_bytes":
                    target["validation"][0]["details"]["source_bytes_hex"] = "ff"
                elif variant == "target_digest":
                    target["source_digest"] = "0" * 64
                elif variant == "head":
                    target["validation"][0]["details"]["source_binding"]["head"]["repository_id"] = "foreign"
                elif variant == "authority":
                    provenance["proof_authority"] = True
                record = self.native_export(provenance)
                if variant == "file_digest":
                    record["sha256"] = "0" * 64
                elif variant == "unknown_metadata":
                    record["unit_metadata"] = {"native/root/unknown/0": {}}
                manifest = clean_manifest()
                manifest["native_records"] = [record]
                with self.assertRaises(audit.AuditInputError):
                    self.run_audit(manifest)

    def test_cli_exit_codes_private_output_and_no_overwrite(self):
        path = self.root / "manifest.json"
        script = Path(audit.__file__)
        for variant, expected in (("clean", 0), ("leaky", 1), ("incomplete", 2), ("invalid", 3)):
            manifest = clean_manifest()
            if variant == "leaky":
                manifest["units"][0]["dependencies"] = ["tune"]
            elif variant == "incomplete":
                manifest["units"][0]["dependencies_complete"] = False
            elif variant == "invalid":
                manifest["units"][0]["role"] = "alias"
            path.write_bytes(audit._canonical(manifest))
            output = self.root / (variant + "-report.json")
            completed = subprocess.run([sys.executable, str(script), str(path), "--output", str(output)],
                                       capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, expected, completed.stderr)
            self.assertEqual(output.exists(), variant != "invalid")
            if output.exists():
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
                old = output.read_bytes()
                completed = subprocess.run([sys.executable, str(script), str(path), "--output", str(output)],
                                           capture_output=True, text=True, timeout=15)
                self.assertEqual(completed.returncode, 3)
                self.assertEqual(output.read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
