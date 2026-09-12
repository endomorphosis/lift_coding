"""Normal signed metadata fixtures, never pilot execution or scientific evidence."""
import sys
sys.dont_write_bytecode = True
import base64
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
PACKAGE = HERE.parent
SPEC = importlib.util.spec_from_file_location("guard", HERE / "scripts/ns028_completion_guard.py")
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
SPEC = importlib.util.spec_from_file_location("paper", HERE / "scripts/paper_supervisors.py")
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)
CLIENT = HERE / G.SERVICE / "pilot_client.py"


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = tempfile.TemporaryDirectory(prefix="normal-ns028-signature-control-")
        cls.key = Path(cls.keys.name) / "signing.pem"
        subprocess.run(["/usr/bin/openssl", "genpkey", "-algorithm", "ED25519", "-out", str(cls.key)], check=True, capture_output=True)
        cls.public = subprocess.check_output(["/usr/bin/openssl", "pkey", "-in", str(cls.key), "-pubout", "-outform", "DER"])
    @classmethod
    def tearDownClass(cls):
        cls.keys.cleanup()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="constructed-ns028-completion-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.receipt = {"outputs": {}, "artifacts": {}}
        self.rows, self.bodies = [], {}
        client = self.root / G.SERVICE / "pilot_client.py"
        client.parent.mkdir(parents=True)
        shutil.copyfile(CLIENT, client)
        self.assertEqual(G.sha(client.read_bytes()), G.CLIENT_SHA)
        self.hpath = "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py"
        self.put(self.hpath, b"# constructed source bytes, never imported\n")
        self.pins = {self.hpath: G.sha(b"# constructed source bytes, never imported\n")}
        self.freeze = {"schema": "paper-ns-final-experiment-freeze/v1", "retained_executable_arms": ["A", "B"],
                       "first_final_attempt_started": False, "immutable_pins": self.pins}
        self.freeze["freeze_sha256"] = G.sha(G.canon(self.freeze))
        self.put(G.PAPER + "artifacts/final_experiment_freeze.json", self.freeze)
        final = {"freeze_sha256": self.freeze["freeze_sha256"], "first_final_attempt_started": False}
        self.put(G.PAPER + "protocol/final_run_manifest.json", final)
        self.hproof = G.PAPER + "pilot/recovery/root_native_harness_execution.json"
        self.hlog = G.PAPER + "pilot/recovery/root_native_harness_execution.log"
        self.put(self.hlog, b"constructed normal execution-metadata fixture, not a native research run\n")
        self.proof = {"schema": "ns028-root-native-harness-execution/v1", "executed": True, "fixture": False,
                      "execution_kind": "actual_native_python_import_and_call", "source_path": self.hpath,
                      "source_sha256": self.pins[self.hpath], "checks": {k: True for k in G.HARNESSES},
                      "command": {"argv": ["python3", "constructed-only.py"], "exit_code": 0, "log": self.hlog},
                      "test_fixture_only": True}
        self.put(self.hproof, self.proof)
        self.authority = {"schema": "ns028-root-completion-authority/v1", "task_id": "NS-028", "approved": True,
                          "client_sha256": G.CLIENT_SHA, "retained_arms": ["A", "B"], "batch_sha256": "a" * 64,
                          "freeze_file_sha256": self.evidence_sha(G.PAPER + "artifacts/final_experiment_freeze.json"),
                          "final_manifest_file_sha256": self.evidence_sha(G.PAPER + "protocol/final_run_manifest.json"),
                          "source_pins": self.pins, "cells": {},
                          "native_harness": {"evidence_path": self.hproof, "evidence_sha256": self.evidence_sha(self.hproof),
                                             "source_path": self.hpath, "source_sha256": self.pins[self.hpath],
                                             "log_path": self.hlog, "log_sha256": self.evidence_sha(self.hlog)},
                          "constructed_test_authority_only": True}
        for unit in G.UNITS:
            for arm in ("A", "B"):
                for repetition in (0, 1, 2):
                    cid = G.cell_id(unit, arm, repetition)
                    req = {"schema": "operator-pilot-request/v2", "batch_sha256": "a" * 64, "cell_id": cid,
                           "unit": unit, "arm": arm, "repetition": repetition, "cache": "local_cold",
                           "record_kind": "pilot", "grant_sha256": "b" * 64, "grant_id": "constructed-" + cid,
                           "request_id": "constructed-request-" + cid, "amendment_sha256": "c" * 64}
                    offer = {"request": req, "profile": {"constructed": True, "implemented_arm": arm,
                             "implemented_cache": "local_cold", "mechanism_profile_sha256": G.sha(G.canon({"constructed_arm": arm}))}, "source_sha256": "d" * 64,
                             "public_key_sha256": G.sha(self.public),
                             "public_verifier": {"algorithm": "Ed25519", "encoding": "spki_der_base64",
                                                 "data": base64.b64encode(self.public).decode()}}
                    prefix = G.PAPER + "pilot/host_receipts/" + cid + "/"
                    self.put(prefix + "offer.json", offer)
                    binding = {k: v for k, v in req.items() if k not in ("schema", "request_id")}
                    binding.update(profile=offer["profile"], source_sha256=offer["source_sha256"], manifest_sha256="e" * 64,
                                   offer_sha256=self.evidence_sha(prefix + "offer.json"))
                    rb = {"grant_sha256": req["grant_sha256"], "candidate_sha256": "f" * 64, "source_sha256": "d" * 64,
                          "batch_sha256": "a" * 64, "cell_id": cid}
                    review = {"approved": True, "binding": rb, "test_fixture_only": True}
                    self.put(prefix + "operator_review.json", review)
                    score = {"schema": "ns-historical-cold-host-result/v1", "split": "pilot", "unit_id": unit,
                             "candidate_sha256": "f" * 64, "manifest_sha256": "e" * 64, "success": True,
                             "timed_out": False, "container_exit_code": 0,
                             "scorer": {"success": True, "visible_collected": 2, "visible_passed": 2,
                                        "hidden_collected": 1, "hidden_passed": 1}}
                    body = {**binding, "schema": "operator-pilot-receipt/v2", "request_sha256": G.sha(G.canon(req)),
                            "inert_qualification": False, "final_scientific_run": False, "production_final_admitted": False,
                            "historical_population_admitted": False, "status": "completed", "error": None,
                            "provider_invoked": True, "served_profile_admitted": True, "historical_pilot_unit_admitted": True,
                            "provider_termination": {"termination_proven": True}, "operator_review_kind": "ai_operator",
                            "trust_scope": "specific_reviewed_pilot_candidate_only", "automatic_adversarial_scorer_integrity_qualified": False,
                            "operator_review_sha256": self.evidence_sha(prefix + "operator_review.json"),
                            "operator_review_binding": rb, "candidate_sha256": "f" * 64, "scorer": score,
                            "test_fixture_only": True}
                    self.bodies[cid] = body
                    self.put(prefix + "response.json", self.sign(body))
                    self.authority["cells"][cid] = {"binding": binding, "offer_sha256": binding["offer_sha256"],
                                                    "public_key_sha256": G.sha(self.public), "terminal_filename": "response.json",
                                                    "terminal_sha256": self.evidence_sha(prefix + "response.json")}
                    self.rows.append({"cell_id": cid, "task_id": unit, "arm": arm, "repetition": repetition,
                                      "cache": "local_cold", "record_kind": "pilot", "split": "pilot",
                                      "terminal": True, "status": "completed", "counts_as_live_repair": True,
                                      "live_repair_admitted": True})
        self.publish()
    def sign(self, body):
        p = self.root / "constructed-sign-input"
        p.write_bytes(G.canon(body))
        signature = subprocess.check_output(["/usr/bin/openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(self.key), "-in", str(p)])
        return {"receipt": body, "signature": base64.b64encode(signature).decode(), "public_key_sha256": G.sha(self.public)}
    def put(self, name, value):
        raw = value if isinstance(value, bytes) else G.canon(value)
        snapshot = G.PAPER + "receipts/snapshots/NS-028/guard-fixture/" + name
        p = self.root / snapshot
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        self.receipt["outputs"][name] = snapshot
        self.receipt["artifacts"][snapshot] = G.sha(raw)
    def evidence_sha(self, name):
        return self.receipt["artifacts"][self.receipt["outputs"][name]]
    def publish(self):
        self.put(G.PAPER + "pilot/results.jsonl", b"\n".join(G.canon(x) for x in self.rows) + b"\n")
        p = self.root / G.AUTHORITY
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(G.canon(self.authority))
    def resign(self, cid):
        path = G.PAPER + "pilot/host_receipts/" + cid + "/response.json"
        self.put(path, self.sign(self.bodies[cid]))
        self.authority["cells"][cid]["terminal_sha256"] = self.evidence_sha(path)
    def test_constructed_24_signed_cells_with_nonempty_arms_pass(self):
        r = G.verify(self.root, self.receipt)
        self.assertEqual(r["terminal_cells"], 24)
        self.assertEqual(r["useful_witnesses"], {"A": 12, "B": 12})
    def test_pending_row_rejected_even_with_complete_met_judgments(self):
        self.receipt.update(status="complete", criteria=[{"status": "met"}])
        self.rows[0].update(status="pending_operator_inputs", terminal=False)
        self.publish()
        with self.assertRaisesRegex(ValueError, "pending or nonterminal"):
            G.verify(self.root, self.receipt)
    def test_actual_stopped_false_receipt_rejected(self):
        saved = HERE / "tests/fixtures/ns028_pending_completion"
        receipt = json.loads((saved / G.PAPER / "receipts/NS-028.json").read_text())
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["criteria"][4]["status"], "met")
        with self.assertRaisesRegex(ValueError, "pending or nonterminal"):
            G.verify(saved, receipt)
    def test_empty_design_rejected(self):
        self.freeze["retained_executable_arms"] = []
        self.put(G.PAPER + "artifacts/final_experiment_freeze.json", self.freeze)
        with self.assertRaisesRegex(ValueError, "nonempty"):
            G.verify(self.root, self.receipt)
    def test_post_outcome_single_arm_removal_rejected_even_with_root_metadata(self):
        self.freeze["retained_executable_arms"] = ["A"]
        self.authority["retained_arms"] = ["A"]
        self.put(G.PAPER + "artifacts/final_experiment_freeze.json", self.freeze)
        self.publish()
        with self.assertRaisesRegex(ValueError, "no post-outcome arm removal"):
            G.verify(self.root, self.receipt)
    def test_one_arm_has_no_useful_signed_cold_witness(self):
        for row in self.rows:
            if row["arm"] == "B":
                row.update(counts_as_live_repair=False, live_repair_admitted=False)
                self.bodies[row["cell_id"]]["scorer"]["success"] = False
                self.resign(row["cell_id"])
        self.publish()
        with self.assertRaisesRegex(ValueError, "every retained arm"):
            G.verify(self.root, self.receipt)
    def test_duplicate_or_missing_cell_rejected(self):
        self.rows[-1] = copy.deepcopy(self.rows[0]); self.publish()
        with self.assertRaisesRegex(ValueError, "24 unique"):
            G.verify(self.root, self.receipt)
    def test_worker_key_not_accepted_as_its_own_authority(self):
        self.authority["cells"][self.rows[0]["cell_id"]]["public_key_sha256"] = "0" * 64
        self.publish()
        with self.assertRaisesRegex(ValueError, "untrusted host verifier"):
            G.verify(self.root, self.receipt)
    def test_changed_signed_receipt_fails_real_verifier(self):
        cid = self.rows[0]["cell_id"]; path = G.PAPER + "pilot/host_receipts/" + cid + "/response.json"
        signed = self.sign(self.bodies[cid]); signed["receipt"]["patch_bytes"] = 101
        self.put(path, signed); self.authority["cells"][cid]["terminal_sha256"] = self.evidence_sha(path); self.publish()
        with self.assertRaisesRegex(ValueError, "signature invalid"):
            G.verify(self.root, self.receipt)
    def test_missing_root_authority_rejected(self):
        self.authority["approved"] = False; self.publish()
        with self.assertRaisesRegex(ValueError, "not admitted actual evidence"):
            G.verify(self.root, self.receipt)
    def test_same_mechanism_different_arm_labels_rejected(self):
        for item in self.authority["cells"].values():
            item["binding"]["profile"]["mechanism_profile_sha256"] = "7" * 64
        self.publish()
        with self.assertRaisesRegex(ValueError, "same mechanism"):
            G.verify(self.root, self.receipt)
    def test_stale_freeze_or_source_rejected(self):
        self.put(self.hpath, b"# changed constructed source\n")
        with self.assertRaisesRegex(ValueError, "frozen source bytes changed"):
            G.verify(self.root, self.receipt)
    def test_missing_actual_harness_rejected(self):
        self.authority["native_harness"] = None; self.publish()
        with self.assertRaisesRegex(ValueError, "actual native harness"):
            G.verify(self.root, self.receipt)
    def test_fixture_harness_cannot_satisfy_execution(self):
        self.proof["fixture"] = True; self.put(self.hproof, self.proof)
        self.authority["native_harness"]["evidence_sha256"] = self.evidence_sha(self.hproof); self.publish()
        with self.assertRaisesRegex(ValueError, "actual native import"):
            G.verify(self.root, self.receipt)
    def test_unknown_provider_termination_rejected(self):
        cid = self.rows[0]["cell_id"]; self.bodies[cid]["provider_termination"]["termination_proven"] = False
        self.resign(cid); self.publish()
        with self.assertRaisesRegex(ValueError, "actual terminated"):
            G.verify(self.root, self.receipt)
    def test_boolean_or_zero_collected_count_gets_no_credit(self):
        cid = self.rows[0]["cell_id"]; self.bodies[cid]["scorer"]["scorer"]["visible_collected"] = True
        self.resign(cid); self.publish()
        with self.assertRaisesRegex(ValueError, "row repair credit differs"):
            G.verify(self.root, self.receipt)
    def test_unbound_candidate_review_rejected(self):
        cid = self.rows[0]["cell_id"]; self.bodies[cid]["operator_review_sha256"] = "0" * 64
        self.resign(cid); self.publish()
        with self.assertRaisesRegex(ValueError, "actual bound candidate review"):
            G.verify(self.root, self.receipt)
    def test_known_signed_failure_is_retained_without_success_credit(self):
        row = self.rows[0]; cid = row["cell_id"]
        prefix = G.PAPER + "pilot/host_receipts/" + cid + "/"
        body = self.bodies[cid]
        body.update(status="operator_reconciliation_required", error={"type": "ConstructedParseFailure"},
                    historical_pilot_unit_admitted=False, scorer={"executed": False})
        original = self.sign(body)
        self.put(prefix + "response.json", original)
        binding = {k: body[k] for k in ("grant_sha256", "request_sha256", "batch_sha256", "cell_id",
                                        "source_sha256", "manifest_sha256", "amendment_sha256")}
        binding["profile_sha256"] = G.sha(G.canon(body["profile"]))
        record = {"schema": "operator-pilot-failure-accounting-review/v1", "approved": True,
                  "reviewer_kind": "ai_operator", "scope": "terminal_failure_accounting_only",
                  "human_annotation": False, "final_admission": False,
                  "classification": "known_proposal_failure", "binding": binding}
        disposition = {"schema": "operator-pilot-failure-disposition/v1", "status": "terminal_failed",
                       "terminal": True, "classification": "known_proposal_failure", "binding": binding,
                       "original_filename": "result.json", "original_receipt_sha256": self.evidence_sha(prefix + "response.json"),
                       "preserved_original_body_sha256": G.sha(G.canon(body)), "operator_record": record,
                       "operator_record_sha256": G.sha(G.canon(record)), "provider_termination": body["provider_termination"],
                       "new_provider_calls": 0, "new_scorer_calls": 0,
                       **{k: False for k in ("retry_allowed", "success_credit", "score_credit", "historical_pilot_unit_admitted", "final_admitted", "human_annotation")}}
        self.put(prefix + "disposition.json", self.sign(disposition))
        self.authority["cells"][cid].update(terminal_filename="disposition.json", terminal_sha256=self.evidence_sha(prefix + "disposition.json"))
        row.update(status="terminal_failed", counts_as_live_repair=False, live_repair_admitted=False)
        self.publish()
        result = G.verify(self.root, self.receipt)
        self.assertEqual(result["useful_witnesses"], {"A": 11, "B": 12})
        self.assertEqual(result["terminal_cells"], 24)
    def test_missing_final_freeze_is_rejected(self):
        del self.receipt["outputs"][G.PAPER + "artifacts/final_experiment_freeze.json"]
        with self.assertRaisesRegex(ValueError, "required evidence lacks"):
            G.verify(self.root, self.receipt)
    def test_mandatory_task_and_goal_shared_contract_path_rejects_pending(self):
        self.rows[0].update(status="pending_operator_inputs", terminal=False); self.publish()
        # Valid ordinary hash/receipt provenance, with no experiment execution.
        criterion = "constructed integration control"
        log = G.PAPER + "receipts/snapshots/NS-028/integration.log"
        p = self.root / log; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("constructed only\n")
        self.receipt["artifacts"][log] = G.sha(p.read_bytes())
        self.receipt.update(schema="paper-task-evidence/v1", task_id="NS-028", status="complete",
                            completed_at="2026-09-12T10:00:00Z", source_versions={"scope": "constructed only"},
                            criteria=[{"criterion": criterion, "status": "met", "explanation": "constructed only", "evidence": [log]}],
                            commands=[{"argv": ["python3", "-c", "pass"], "exit_code": 0, "log": log}])
        path = self.root / G.PAPER / "receipts/NS-028.json"; path.write_bytes(G.canon(self.receipt))
        shutil.copyfile(HERE / "scripts/ns028_completion_guard.py", self.root / "scripts/ns028_completion_guard.py")
        task = {"id": "NS-028", "acceptance_criteria": [criterion], "deliverables": list(self.receipt["outputs"])}
        with patch.object(P, "ROOT", self.root), self.assertRaisesRegex(ValueError, "pending or nonterminal"):
            P._verify_task_contract("neurosymbolic_supervision", task, check_current=False)


class ProtectionTests(unittest.TestCase):
    def test_actual_campaign_argv_protects_verifier_and_root_authority(self):
        spec = importlib.util.spec_from_file_location("campaign_guard_control", HERE / "scripts/paper_supervisor_campaign.py")
        campaign = importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)
        cfg = {k: "constructed-" + k for k in ("task_prefix", "state_prefix", "pdf", "manifest_path", "review_path", "todo_path", "objective_path")}
        ready = {"quack_endpoint": "quack://invalid.example", "endpoint_secret_handle": "constructed-no-secret",
                 "store_id": "constructed", "store_generation": 1, "schema_revision": 1}
        with patch.object(campaign, "cfg", return_value=cfg):
            argv = campaign.native_argv(Path("/constructed"), "neurosymbolic_supervision", Path("/constructed/lane"), ready)
        protected = {argv[i + 1] for i, item in enumerate(argv) if item == "--implementation-protected-path"}
        self.assertTrue({"scripts/paper_supervisors.py", "scripts/ns028_completion_guard.py", G.AUTHORITY} <= protected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
