"""Pinned owner-evidence recovery and incomplete handoff controls."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codebase_ir_closure_requests as closure
import codebase_ir_corpus_audit as audit
from test_codebase_ir_corpus_audit import clean_manifest, native_provenance, native_target


def owner_fixture(values=(1, 3, 5), *, generation=1, previous_head=None, git_commit=None, git_tree=None, mode="filesystem"):
    """Minimal source-owner profile records for content-binding tests, no fitting."""
    repository = "fixture:native"
    entries, ast_records, structural_units, raw_sources = [], {}, [], {}
    for role, value in zip(("train", "tune", "canary"), values, strict=True):
        path = role + ".py"
        raw = f"def f(n):\n    return n + {value}\n".encode()
        entry = {"schema": "ipfs-datasets.software-contracts.semantic-snapshot-entry@3", "path": path,
                 "raw_path_hex": path.encode().hex(), "kind": "python", "size_bytes": len(raw),
                 "source_cid": audit._raw_source_cid(raw), "opaque_reason": None, "git_blob_oid": None,
                 "acquisition": "captured", "disposition": "working", "head_blob_oid": None, "index_blob_oids": {}}
        entry["entry_cid"] = closure.structured_cid(entry)
        entries.append(entry)
        raw_sources[path] = raw
    snapshot = {"schema": "ipfs-datasets.software-contracts.semantic-repository-snapshot@4",
                "repository_id": repository, "entries": entries, "mode": mode,
                "max_file_bytes": 65536, "max_entries": 256, "git_tree": git_tree,
                "git_commit": git_commit, "exclusions": [".git"]}
    snapshot["snapshot_cid"] = closure.structured_cid(snapshot)
    for entry in entries:
        path = entry["path"]
        ast_record = {"schema": closure.AST_SCHEMA,
                      "provenance": {"path": path, "repository_id": repository,
                                     "source_cid": entry["source_cid"], "repository_tree_cid": snapshot["snapshot_cid"],
                                     "revision": "snapshot:" + snapshot["snapshot_cid"]},
                      "imports": [], "calls": [], "effects": [], "unsupported": [], "diagnostics": []}
        ast_records[path] = ast_record
        structural_units.append({"schema": "codebase-ir-structural-unit@1", "source_key": "raw:" + path.encode().hex(),
                                 "entry_cid": entry["entry_cid"], "ast_cid": closure.structured_cid(ast_record), "parse_status": "ok"})
    ast_revision = f"rev:{repository}:snapshot:{snapshot['snapshot_cid']}"
    manifest = {"schema": "codebase-ir-structural-manifest@1", "authority": "structural_only",
                "snapshot": snapshot, "semantic_state": {"edges": []}, "ast_revision_id": ast_revision,
                "units": structural_units, "coverage": {"inventory_entries": len(entries), "checked_properties": 0}}
    manifest_cid = closure.structured_cid(manifest)
    receipt = {"schema": "codebase-publication-receipt@1", "repository_id": repository,
               "generation": generation, "manifest_cid": manifest_cid, "snapshot_cid": snapshot["snapshot_cid"],
               "ast_revision_id": ast_revision, "previous_head": previous_head, "operation_id": "fixture:capture",
               "request_cid": closure.structured_cid({"fixture": True})}
    head = {"schema": "codebase-head@1", "repository_id": repository, "generation": generation,
            "manifest_cid": manifest_cid, "snapshot_cid": snapshot["snapshot_cid"], "ast_revision_id": ast_revision,
            "receipt_cid": closure.structured_cid(receipt)}
    targets = {}
    for entry, unit in zip(entries, structural_units, strict=True):
        path = entry["path"]
        target = native_target(path, raw_sources[path])
        details = target["validation"][0]["details"]
        binding = details["source_binding"]
        binding.update({"head": head, "entry": entry, "unit": unit, "ast_cid": unit["ast_cid"],
                        "source_revision": "snapshot:" + snapshot["snapshot_cid"]})
        details.update({"manifest": manifest, "publication_receipt": receipt, "captured_ast": ast_records[path]})
        target["source_digest"] = audit._sha(audit._canonical({"target_schema": audit.NATIVE_TARGET_SCHEMA,
            "source_binding": binding, "authored_contracts": []}))
        targets[path] = target
    return {"manifest": manifest, "head": head, "receipt": receipt, "asts": ast_records,
            "sources": raw_sources, "targets": targets}


class ClosureEvidenceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="closure-evidence-controls-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.cas = self.root / "source-cas"
        self.cas.mkdir()

    def retain_owner(self, fixture):
        for cid, value in [(fixture["head"]["manifest_cid"], fixture["manifest"]),
                           *[(closure.structured_cid(value), value) for value in fixture["asts"].values()]]:
            path = self.cas / "structured" / cid[:4] / cid
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(audit._canonical(value))
        for raw in fixture["sources"].values():
            cid = audit._raw_source_cid(raw)
            path = self.cas / "source" / cid[:4] / cid
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def inputs(self, *, missing_parent=False, git=None, falsely_clean_child=False):
        commit, tree = (None, None) if git is None else git
        parent = owner_fixture(git_commit=commit, git_tree=tree, mode="filesystem" if git is None else "git-clean")
        child = owner_fixture((2, 3, 5), generation=2, previous_head=parent["head"], git_commit=commit, git_tree=tree,
                              mode="filesystem" if git is None else "git-clean" if falsely_clean_child else "git-working")
        value = clean_manifest()
        value["units"] = [value["units"][3]]
        value["native_records"] = []
        for version, fixture in (("root", parent), ("child", child)):
            self.retain_owner(fixture)
            provenance = native_provenance(None if version == "root" else "root")
            provenance.update({"head": fixture["head"], "training_targets": [fixture["targets"]["train.py"]],
                               "tuning_targets": [parent["targets"]["tune.py"]], "canary_targets": [parent["targets"]["canary.py"]],
                               "replay_targets": [parent["targets"]["train.py"]]})
            if version == "child":
                provenance["training_targets"].append(parent["targets"]["train.py"])
                provenance["ancestral_training"] = [{"repository_id": "fixture:native", "path": "train.py",
                    "source_digest": audit._sha(parent["sources"]["train.py"])}]
            raw = audit._canonical({"report": {"codebase_provenance": provenance}})
            path = self.root / (version + ".json")
            path.write_bytes(raw)
            if version != "root" or not missing_parent:
                value["native_records"].append({"version_id": version, "file": path.name,
                                                 "sha256": audit._sha(raw), "unit_metadata": {}})
        path = self.root / "input.json"
        path.write_bytes(audit._canonical(value))
        return path, parent, child

    def run_requests(self, path, name="output", **kwargs):
        return closure.create_closure_requests(path, self.root / name, source_cas=self.cas, **kwargs)

    def init_git(self):
        repository = self.root / "git-repository"
        repository.mkdir()
        for role, value in zip(("train", "tune", "canary"), (1, 3, 5), strict=True):
            (repository / (role + ".py")).write_text(f"def f(n):\n    return n + {value}\n")
        for arguments in (("init", "-q"), ("config", "user.name", "Closure Fixture"),
                          ("config", "user.email", "closure@example.invalid"), ("add", "."),
                          ("commit", "-qm", "retained root fixture")):
            subprocess.run(["git", "-C", str(repository), *arguments], check=True, capture_output=True)
        commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"]).decode().strip()
        tree = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD^{tree}"]).decode().strip()
        return repository, commit, tree

    def test_exact_owner_facts_recovered_but_twenty_claims_remain_open(self):
        path, parent, child = self.inputs()
        report = self.run_requests(path)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["baseline_closure_issue_count"], 20)
        self.assertEqual(report["comparison_closure_issue_count"], 20)
        self.assertEqual(report["closure_request_count"], 4)
        self.assertEqual(report["recovered_manifest_count"], 2)
        self.assertEqual(report["owner_fact_count"], 6)
        self.assertEqual(report["closure_claims_applied"], 0)
        self.assertFalse(report["native_closure_certification_verified"])
        facts = json.loads((self.root / "output" / "owner_facts.json").read_bytes())
        self.assertEqual(len(facts["native_targets"]), 9)
        self.assertEqual(len(facts["source_receipt_predecessors"]), 1)
        self.assertTrue(facts["source_receipt_predecessors"][0]["previous_head_available_and_equal"])
        self.assertTrue(all(row["ast_cas_corroborated"] for row in facts["owner_facts"]))
        self.assertTrue(all(row["structural_inventories"]["imports"]["count"] == 0 for row in facts["owner_facts"]))
        for request in report["closure_requests"]:
            self.assertFalse(request["locally_recovered_facts_are_closure_certificate"])
            self.assertEqual(len(request["proposed_owner_inputs"]), 2)
        self.assertNotEqual(parent["head"]["manifest_cid"], child["head"]["manifest_cid"])

    def test_same_git_head_dirty_successor_is_overlay_not_git_revision(self):
        repository, commit, tree = self.init_git()
        path, _, _ = self.inputs(git=(commit, tree))
        original_worktree = {path.name: path.read_bytes() for path in repository.glob("*.py")}
        report = self.run_requests(path, git_repository=repository)
        facts = json.loads((self.root / "output" / "owner_facts.json").read_bytes())
        overlays = [row for row in facts["owner_facts"] if row["working_overlay_from_shared_git_commit"]]
        self.assertEqual(len(overlays), 1)
        self.assertEqual(overlays[0]["path"], "train.py")
        self.assertNotEqual(overlays[0]["content_sha256"], overlays[0]["git_blob_content_sha256"])
        self.assertTrue(all(row["commit_is_root"] for row in facts["git_snapshot_bindings"]))
        self.assertEqual(report["comparison_closure_issue_count"], 20)
        self.assertEqual(original_worktree, {path.name: path.read_bytes() for path in repository.glob("*.py")})

    def test_false_clean_snapshot_label_refuses_dirty_git_source(self):
        repository, commit, tree = self.init_git()
        path, _, _ = self.inputs(git=(commit, tree), falsely_clean_child=True)
        with self.assertRaisesRegex(audit.AuditInputError, "clean source snapshot differs"):
            self.run_requests(path, git_repository=repository)

    def test_missing_model_ancestor_remains_explicit_despite_recovered_source_heads(self):
        path, _, _ = self.inputs(missing_parent=True)
        report = self.run_requests(path)
        self.assertEqual(report["comparison_audit_status"], "incomplete")
        self.assertIn("native_parent_unavailable", {row["code"] for row in report["other_missing_evidence"]})
        self.assertFalse(report["native_registry_receipts_verified"])
        self.assertEqual(report["closure_claims_applied"], 0)

    def test_embedded_manifest_drift_rejected_even_if_export_hash_repinned(self):
        path, _, _ = self.inputs()
        value = json.loads(path.read_bytes())
        record = value["native_records"][0]
        export_path = self.root / record["file"]
        exported = json.loads(export_path.read_bytes())
        exported["report"]["codebase_provenance"]["training_targets"][0]["validation"][0]["details"]["manifest"]["coverage"]["checked_properties"] = 1
        raw = audit._canonical(exported)
        export_path.write_bytes(raw)
        record["sha256"] = audit._sha(raw)
        path.write_bytes(audit._canonical(value))
        with self.assertRaisesRegex(audit.AuditInputError, "manifest/head CID mismatch"):
            self.run_requests(path)

    def test_owner_cas_binding_drift_is_frontier_and_never_closure(self):
        path, parent, _ = self.inputs()
        cid = parent["head"]["manifest_cid"]
        cas_path = self.cas / "structured" / cid[:4] / cid
        modified = copy.deepcopy(parent["manifest"])
        modified["coverage"]["checked_properties"] = 1
        cas_path.write_bytes(audit._canonical(modified))
        report = self.run_requests(path)
        facts = json.loads((self.root / "output" / "owner_facts.json").read_bytes())
        self.assertIn("source_owner_content_binding_drift", {row["code"] for row in facts["recovery_frontiers"]})
        self.assertEqual(report["recovered_manifest_count"], 1)
        self.assertEqual(report["comparison_closure_issue_count"], 20)

    def test_budget_refusal_precedes_owner_allocation_and_manifest_expansion(self):
        path, _, _ = self.inputs()
        with self.assertRaisesRegex(audit.AuditInputError, "entry budget"):
            self.run_requests(path, name="entry-budget", limits=closure.RecoveryLimits(max_manifest_entries=2))
        real_read = audit._read_bounded
        maxima = []

        def record_read(input_path, maximum):
            if self.cas in Path(input_path).parents:
                maxima.append(maximum)
            return real_read(input_path, maximum)

        with mock.patch.object(audit, "_read_bounded", side_effect=record_read):
            with self.assertRaisesRegex(audit.AuditInputError, "owner artifact byte budget"):
                self.run_requests(path, name="byte-budget", limits=closure.RecoveryLimits(max_owner_bytes=32))
        self.assertEqual(maxima, [32])
        with self.assertRaisesRegex(audit.AuditInputError, "file budget"):
            self.run_requests(path, name="file-budget", limits=closure.RecoveryLimits(max_owner_files=1))

    def test_comparison_uses_first_pinned_manifest_despite_late_role_claim_changes(self):
        path, _, _ = self.inputs()
        initial = path.read_bytes()
        real_get = closure._CAS.get
        changed = False

        def mutating_get(owner, cid, **kwargs):
            nonlocal changed
            if not changed:
                value = json.loads(path.read_bytes())
                value["units"][0]["role"] = "train"
                value["ancestry_complete"] = False
                path.write_bytes(audit._canonical(value))
                changed = True
            return real_get(owner, cid, **kwargs)

        with mock.patch.object(closure._CAS, "get", mutating_get):
            report = self.run_requests(path)
        self.assertEqual(report["input_manifest_sha256"], audit._sha(initial))
        self.assertEqual(report["comparison_closure_issue_count"], 20)
        pinned = json.loads((self.root / "output" / "pinned_input.json").read_bytes())
        self.assertEqual(pinned["units"][0]["role"], "final")
        self.assertTrue(pinned["ancestry_complete"])

    def test_missing_cas_owner_objects_remain_explicit(self):
        path, parent, _ = self.inputs()
        cid = parent["head"]["manifest_cid"]
        (self.cas / "structured" / cid[:4] / cid).unlink()
        report = self.run_requests(path)
        facts = json.loads((self.root / "output" / "owner_facts.json").read_bytes())
        self.assertIn("source_owner_artifact_unavailable", {row["code"] for row in facts["recovery_frontiers"]})
        self.assertEqual(report["comparison_audit_status"], "incomplete")

    def test_git_promisor_recovery_forbids_transport_and_helpers(self):
        repository, _, _ = self.init_git()
        marker = self.root / "transport-invoked"
        helper = self.root / "would-fetch"
        helper.write_text("#!/bin/sh\nprintf invoked > '" + marker.as_posix() + "'\nexit 1\n")
        helper.chmod(0o700)
        for key, value in (("remote.fixture.url", "ext::" + helper.as_posix()), ("remote.fixture.promisor", "true"),
                           ("remote.fixture.partialclonefilter", "blob:none"), ("extensions.partialClone", "fixture"),
                           ("protocol.ext.allow", "always")):
            subprocess.run(["git", "-C", str(repository), "config", key, value], check=True, capture_output=True)
        output = self.root / "git-only"
        output.mkdir()
        owner = closure._Git(repository, output, closure.DEFAULT_RECOVERY_LIMITS)
        with mock.patch.dict(os.environ, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.ext.allow",
                                          "GIT_CONFIG_VALUE_0": "always", "GIT_ALLOW_PROTOCOL": "ext"}):
            self.assertIsNone(owner.object("f" * 40, "blob"))
        self.assertFalse(marker.exists())
        self.assertFalse((output / "git_objects").exists())

    def test_deterministic_request_inventory_and_private_artifacts(self):
        path, _, _ = self.inputs()
        first = self.run_requests(path, "first")
        second = self.run_requests(path, "second")
        self.assertEqual(first, second)
        for filename in ("closure_requests.json", "owner_facts.json", "pinned_input.json"):
            self.assertEqual((self.root / "first" / filename).read_bytes(), (self.root / "second" / filename).read_bytes())
            self.assertEqual((self.root / "first" / filename).stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
