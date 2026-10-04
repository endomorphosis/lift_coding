"""Authored offline records exercise conversion custody and receiving boundaries."""

import copy
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "foreign_outcome_test_receiver", Path(__file__).parent / "foreign_outcome_controls/receiver.py"
)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def artifact(valid, steps):
    model = (
        "---- MODULE BoundedCounter ----\nVARIABLE n\nInit == n = 0\nSafety == "
        + ("TRUE" if valid else "FALSE")
        + "\n====\n"
    )
    config, tlc = (
        "INIT Init\nNEXT Next\nINVARIANT Safety\n",
        "SPECIFICATION Spec\nINVARIANT Safety\n",
    )
    return {
        "schema_version": "tla-generated-artifact/v1",
        "interface_version": "TLABackend@1",
        "model_text": model,
        "model_digest": r.sha(model.encode()),
        "apalache_config_text": config,
        "apalache_config_digest": r.sha(config.encode()),
        "tlc_config_text": tlc,
        "tlc_config_digest": r.sha(tlc.encode()),
        "artifact_digest": r.sha(("authored:" + str(valid) + ":" + str(steps)).encode()),
        "bounded": True,
        "unbounded_proof": False,
        "bounds": {
            "schema_version": "tla-compile-bounds/v1",
            "max_steps": steps,
            "default_integer_lower": 0,
            "default_integer_upper": 7,
            "max_actions": 128,
            "max_enum_members": 64,
            "max_integer_span": 256,
            "max_module_bytes": 1048576,
            "max_predicates": 256,
            "max_variables": 64,
        },
        "fairness_limitations": [],
        "liveness_properties": [],
        "losses": [],
        "source_map": [],
        "module_name": "BoundedCounter",
        "safety_properties": ["Safety"],
        "source_document_id": "authored:" + str(valid),
        "source_kind": "state_transition",
        "translator": {"id": "state-transition-ir-to-tla", "version": "tla-compiler/v1"},
    }


def authored_case(valid, fixture, life):
    bounds = {
        "max_memory_bytes": 536870912,
        "max_output_bytes": 65536,
        "max_steps": 100000,
        "timeout_ms": 30000,
    }
    request = {
        "schema_version": "proof-backend-request/v1",
        "assumption_ids": ["authored:bounded"],
        "bounds": bounds,
        "claim_digest": fixture["model_digest"],
        "claim_id": "authored:claim:" + str(valid),
        "declaration_id": "authored:declaration:" + str(valid),
        "logic_family": "state_transition",
        "obligation_digest": fixture["artifact_digest"],
        "obligation_id": "authored:obligation:" + str(valid),
        "payload": {"artifacts": fixture},
        "query_kind": "satisfiability",
        "request_id": "authored:request:" + str(valid),
        "requested_backend_id": "apalache",
    }
    rd = r.sha(r.canonical(request))
    capability = {
        "checks_safety": True,
        "checks_liveness": False,
        "checks_fairness": False,
        "finite_trace_only": True,
        "requires_jvm": True,
        "schema_version": "tla-model-checker-capability/v1",
        "backend_version": "ApalacheBackend@1",
        "tool": "apalache",
        "max_declared_steps": 200,
        "executable_candidates": ["apalache-mc", "apalache"],
        "limitations": ["authored bounded limitation"],
    }
    ce = (
        None
        if valid
        else {
            "schema_version": "tla-counterexample/v1",
            "raw": life["output_files"]["apalache-run/violation.tla"],
            "replay_notes": [r.TRACE_NOTE],
            "replayed": True,
            "source": "checker_counterexample_file",
            "states": [],
        }
    )
    receipt = {
        "schema_version": "tla-model-check-receipt/v1",
        "artifact_digest": fixture["artifact_digest"],
        "bounded": True,
        "capability": capability,
        "checked_liveness_properties": [],
        "checked_safety_properties": ["Safety"],
        "command": life["command"],
        "configuration_digest": fixture["apalache_config_digest"],
        "configuration_text": fixture["apalache_config_text"],
        "counterexample": ce,
        "elapsed_ms": 1,
        "executable": "/authored/apalache-mc",
        "fairness_limitations": ["finite traces; no fairness"],
        "jvm_available": True,
        "model_digest": fixture["model_digest"],
        "output_truncated": False,
        "reason": "authored bounded observation",
        "receipt_id": "authored:receipt:" + str(valid),
        "returncode": life["returncode"],
        "status": "passed" if valid else "counterexample",
        "stderr": life["stderr"],
        "stdout": life["stdout"],
        "timeout_seconds": 20.0,
        "tool": "apalache",
        "tool_version": "authored",
        "unbounded_proof": False,
    }
    witness_keys = (
        "artifact_digest",
        "bounded",
        "capability",
        "checked_liveness_properties",
        "checked_safety_properties",
        "configuration_digest",
        "fairness_limitations",
        "model_digest",
        "receipt_id",
        "tool",
        "unbounded_proof",
    )
    witness = {k: receipt[k] for k in witness_keys}
    if not valid:
        witness["counterexample"] = ce
    typed = {
        "schema_version": "typed-backend-result/v1",
        "assumptions": request["assumption_ids"],
        "authority": "model_check",
        "backend_id": "apalache",
        "backend_version": "ApalacheBackend@1",
        "bounds": bounds,
        "diagnostics": [] if valid else [r.TRACE_NOTE],
        "metadata": {
            "executable": "/authored/apalache-mc",
            "jvm_available": True,
            "tool_version": "authored",
        },
        "reason": "authored bounded observation",
        "result_id": "result:apalache:" + rd[:24],
        "result_type": "model_check",
        "status": "satisfied" if valid else "violated",
        "translation_ceiling": "bounded",
        "usage": {"elapsed_ms": 1, "output_bytes": 2, "peak_memory_bytes": 0, "steps": 0},
        "witness": witness,
    }
    usage = {"elapsed_ms": 0, "output_bytes": 0, "peak_memory_bytes": 0, "steps": 0}
    output_digest = r.sha(("authored generic output: " + str(valid)).encode())
    attempt = {
        "schema_version": "proof-backend-attempt/v1",
        "artifact_digests": [],
        "attempt_id": "attempt:apalache:" + rd[:24],
        "backend_id": "apalache",
        "backend_version": "matrix-declared/v1",
        "bounds": bounds,
        "diagnostics": [r.DIAGNOSTIC],
        "output_digest": output_digest,
        "request_digest": rd,
        "status": "succeeded",
        "usage": usage,
    }
    ad = r.sha(r.canonical(attempt))
    generic = {
        "schema_version": "bounded-result/v1",
        "assumption_ids": request["assumption_ids"],
        "attempt_digest": ad,
        "authority": {
            "schema_version": "result-authority/v1",
            "configuration_digest": r.sha(b"authored configuration"),
            "evidence_digests": [],
            "issuer": "apalache",
            "kind": "satisfiability",
            "method": "proof-backend-adapter/v1",
            "scope_digest": rd,
        },
        "backend_id": "apalache",
        "backend_version": "matrix-declared/v1",
        "bounds": bounds,
        "claim_digest": request["claim_digest"],
        "declaration_id": request["declaration_id"],
        "diagnostics": [r.DIAGNOSTIC],
        "obligation_digest": request["obligation_digest"],
        "obligation_id": request["obligation_id"],
        "output_digest": output_digest,
        "payload": {
            "adapter_return_type": "ModelCheckOutcome",
            "result": copy.deepcopy(typed),
            "result_authority": "model_check",
            "result_status": typed["status"],
        },
        "request_digest": rd,
        "result_id": typed["result_id"],
        "result_type": "satisfiability",
        "status": "unknown",
        "usage": usage,
    }
    original = {
        "artifacts": {
            k: v
            for k, v in fixture.items()
            if k not in ("model_text", "apalache_config_text", "tlc_config_text")
        },
        "interface_version": "ApalacheBackend@1",
        "receipt": receipt,
        "request_digest": rd,
        "result": typed,
    }
    return {
        "aggregate_scope_owner": "benchmark",
        "attempt": attempt,
        "attempt_digest": ad,
        "case": r.CASE_IDS[0 if valid else 1],
        "default_lazy_factory_used": True,
        "dispatch": {},
        "elapsed_seconds": 0.01,
        "factory_restored": True,
        "operation_timeout_ms": 30000,
        "original_outcome": original,
        "original_return_observer_restored": True,
        "phase_count": 3,
        "projection_checks": {
            "generic_attempt_status": "succeeded",
            "generic_result_status": "unknown",
            "generic_theorem_authority": False,
            "original_authority": "model_check",
            "original_result_status": typed["status"],
            "payload_exact_original_result": True,
        },
        "raw_witness": None
        if valid
        else {
            "parsed_state_count": 0,
            "path": "apalache-run/violation.tla",
            "raw_state_values": ["0", "1", "2"],
            "scope": "Original raw Apalache file retained; no structural replay attestation",
            "sha256": r.sha(ce["raw"].encode()),
        },
        "request": request,
        "request_digest": rd,
        "result": generic,
        "selected_delegate_count": 1,
        "valid": valid,
    }


def packet(failed=False):
    count = 3 if failed else 6
    fixtures = {str(v).lower(): artifact(v, 3 if failed else 64) for v in (False, True)}
    requests, launches, lives, budgets, envs = [], [], [], [], []
    for i in range(count):
        valid, ph = i // 3 == 0, ("setup", "model", "help")[i % 3]
        label = r.CASE_IDS[0 if valid else 1]
        case = label + ":constructor" if ph == "setup" else label
        argv = (
            ["/authored/java", "-version"]
            if ph == "setup"
            else ["/authored/apalache-mc", "version"]
            if ph == "help"
            else ["/authored/apalache-mc", "check", "--length=64", "BoundedCounter.tla"]
        )
        fi = fixtures[str(valid).lower()]
        requests.append(
            {
                "case": case,
                "argv": argv,
                "limits": {"timeout_seconds": 20.0},
                "input_sha256": {
                    "BoundedCounter.tla": fi["model_digest"],
                    "apalache.cfg": fi["apalache_config_digest"],
                },
                "input_bytes": {
                    "BoundedCounter.tla": len(fi["model_text"].encode()),
                    "apalache.cfg": len(fi["apalache_config_text"].encode()),
                },
            }
        )
        lease = {
            "lease_id": "authored:lease:" + str(i),
            "cancelled": False,
            "parent_lease_id": None,
            "cpu_slots": 1,
            "memory_mb": 256 if ph == "setup" else 512,
            "child_process_slots": 1 if ph == "setup" else 3,
        }
        launches.append(
            {
                "case": case,
                "argv": ["/authored/prlimit", "--"] + argv,
                "launch_lease_id": lease["lease_id"],
                "owned_leases": [lease],
                "root_allocations": {
                    k: lease[k] for k in ("cpu_slots", "memory_mb", "child_process_slots")
                },
            }
        )
        native = {
            "command": argv,
            "returncode": 12 if ph == "model" and not valid else 0,
            "stdout": "authored stdout",
            "stderr": "",
            "elapsed_seconds": 0.01,
            "workspace_cleaned": True,
            "output_files": {
                "apalache-run/violation.tla": "State0 == n = 0\nState1 == n = 1\nState2 == n = 2\n"
            }
            if ph == "model" and not valid
            else {},
            **{k: False for k in r.LIFE_FALSE},
        }
        lives.append(
            {
                "case": case,
                "request": {
                    "argv": argv,
                    "stdin_is_empty": True,
                    "java_option_environment_absent": True,
                    "timeout_seconds": 20.0,
                },
                "result": native,
            }
        )
        budgets.append(
            {
                "case": label,
                "phase": ph,
                "deadline": 130.0,
                "at_monotonic": 100.0,
                "remaining_seconds": 30.0,
                "request_timeout_seconds": 20.0,
            }
        )
        if ph != "setup":
            envs.append(
                {
                    "case": label,
                    "phase": ph,
                    "foreign_configuration_environment_absent": True,
                    "private_home_and_tmpdir": True,
                    "jvm_args": "-Xmx256m -XX:ActiveProcessorCount=1",
                    "jvm_gc_args": "-XX:+UseSerialGC",
                }
            )
    config = {"authored": "policy"}
    source_pins = {"/authored/source/never_open.py": r.sha(b"authored source metadata")}
    shared = {"config": config, "owned_active_leases": 0, "owned_waiting_requests": 0}
    result = {
        "audit_sha256": {},
        "cases": []
        if failed
        else [
            authored_case(v, fixtures[str(v).lower()], lives[i * 3 + 1]["result"])
            for i, v in enumerate((True, False))
        ],
        "checks": {
            k: True
            for k in (
                "java_selection_environment_restored",
                "owned_work_drained",
                "selected_tool_files_unchanged",
                "shared_config_unchanged",
                "sources_stable",
            )
        },
        "child_usage": {},
        "dispatches": [],
        "elapsed_seconds": 0.1,
        "launches": count,
        "lifecycles": count,
        "native_lifecycles": count,
        "packaged_native_entries": [],
        "phase_counts": {"help": count // 3, "model": count // 3, "setup": count // 3},
        "prelaunch_lifecycles": 0,
        "runtime": {},
        "schema": "registry-foreign-outcome-benchmark@1",
        "scope": {
            "aggregate_scope_owner": "benchmark",
            "default_registry_aggregate_budget_claim": False,
            "factory_override": "authored selection",
            "hard_aggregate_resource_guarantee": False,
            "installation": False,
            "jvm_probe_injected": False,
            "native_transport_injected": False,
            "new_proof_cache_or_replay": False,
            "raw_counterexample_only": True,
            "registry_route": "default_backend_registry/LazyMatrixProofBackend",
            "throughput_scaling_claim": False,
            "tlc_execution": False,
        },
        "shared_after": copy.deepcopy(shared),
        "shared_before": copy.deepcopy(shared),
        "shared_pool_compatibility": {},
        "source_pins_after": source_pins,
        "source_pins_before": source_pins,
        "status": "failed" if failed else "passed",
        "tool_files_after": source_pins,
        "tool_files_before": source_pins,
        "tool_selection": {},
    }
    if failed:
        result["error"] = (
            "AssertionError: Apalache logical/actual command differs from reviewed argv"
        )
    else:
        result["checks"].update(
            {
                k: True
                for k in (
                    "exact_foreign_typed_payload",
                    "exact_two_serial_cases",
                    "expected_real_phases",
                    "native_environments_sanitized",
                    "no_generic_authority_promotion",
                    "observer_and_factory_restored",
                    "owned_apalache_jvm_environments",
                )
            }
        )
    command = {
        "after": source_pins,
        "before": source_pins,
        "argv": ["/authored/python", "benchmark.py"],
        "cwd": "/authored",
        "env_overrides": {},
        "freeze_sha256": r.sha(b"authored freeze"),
        "returncode": int(failed),
        "seconds": 0.1,
    }
    docs = {
        "result": result,
        "command_result": command,
        "request_audit": requests,
        "launch_audit": launches,
        "lifecycle_audit": lives,
        "phase_budget_audit": budgets,
        "environment_audit": envs,
        "fixtures": fixtures,
        "scheduler_config": {"config": config},
    }
    result["audit_sha256"] = {
        leaf: r.sha(r.canonical(docs[role])) for role, leaf in r.LEAVES.items()
    }
    return docs


def write_fixture(root):
    inputs = root / "inputs"
    inputs.mkdir()
    initial, accepted = packet(True), packet()
    q = {
        "schema": "registry-foreign-outcome-qualification@1",
        "status": "passed_partial_scope",
        "selected_tests": 1914,
        "new_foreign_tests": 82,
        "focused_tests": 363,
        "native_success_cases": 2,
        "native_phases": 6,
        "total_native_phases_across_attempts": 9,
        "deselected_legacy_native_tests": 15,
        "test_counts_summed": False,
        "new_cache_replay": False,
        "new_codebase_smt_execution": False,
        "production_tasks_closed": [],
        "checks": {"passed": True},
        "initial_native_attempt": {
            "native_phases": 3,
            "accepted": False,
            "status": "failed",
            "returned_case_serialized": False,
        },
        "selected_test_cases": ["authored:" + str(i) for i in range(1914)],
        "preservation": {"prior_artifacts": 1341, "prior_qualifications": 16},
        "artifact_sha256": {},
        "additional_suite_counts": {},
        "focused_attempts": {},
        "native_seconds": 0.1,
        "native_wrapper_seconds": 0.2,
        "recorded_at_utc": "authored historical observation",
    }
    evolution = {
        "/not/opened/owner" + str(i): {
            "kind": kind,
            "after_sha256": r.sha(b"after"),
            "before_sha256": r.sha(b"before"),
            "diff_sha256": r.sha(b"diff"),
            "after_snapshot": "not-opened.py",
            "before_snapshot": "not-opened.py",
            "diff": "not-opened.diff",
        }
        for i, kind in enumerate(("production", "existing_test"))
    }
    anchors = {}

    def write(role, value):
        path = inputs / (role + ".json")
        raw = r.canonical(value)
        path.write_bytes(raw)
        pin = {"path": str(path), "sha256": r.sha(raw), "size": len(raw)}
        if role in r.ANCHORS:
            anchors[role] = pin["sha256"]
        return pin

    manifest = {
        "schema": r.INPUT_SCHEMA,
        "fixture_origin": "retained_registry_foreign_outcome_receipts",
        "attempts": [],
    }
    for ident, docs in (("initial_failed", initial), ("accepted", accepted)):
        row = {
            "id": ident,
            **{role: write(ident + "." + role, value) for role, value in docs.items()},
        }
        manifest["attempts"].append(row)
        prefix = "native" if ident == "initial_failed" else "native-selected"
        q["artifact_sha256"][prefix + "/result.json"] = row["result"]["sha256"]
        q["artifact_sha256"][prefix + "-command-result.json"] = row["command_result"]["sha256"]
        for role in r.ROLES:
            if role != "command_result":
                leaf = {
                    "result": "result.json",
                    "fixtures": "fixtures.json",
                    "scheduler_config": "saved-scheduler-config.json",
                    **r.LEAVES,
                }[role]
                q["artifact_sha256"][prefix + "/" + leaf] = row[role]["sha256"]
    manifest["source_evolution"] = write("source_evolution", evolution)
    q["artifact_sha256"]["source-evolution.json"] = manifest["source_evolution"]["sha256"]
    manifest["qualification"] = write("qualification", q)
    path = inputs / "manifest.json"
    path.write_bytes(r.canonical(manifest))
    return path, manifest, anchors


class ForeignOutcomeControls(unittest.TestCase):
    def test_authored_accepted_conversion_preserves_unknown(self):
        report = r.reconcile_attempt("accepted", packet())
        self.assertEqual(
            [x["generic_result_status"] for x in report["cases"]], ["unknown", "unknown"]
        )
        self.assertEqual(
            [x["typed_result_status"] for x in report["cases"]], ["satisfied", "violated"]
        )

    def test_authored_failed_attempt_is_separate(self):
        report = r.reconcile_attempt("initial_failed", packet(True))
        self.assertFalse(report["accepted"])
        self.assertEqual(report["recorded_native_phase_count"], 3)
        self.assertEqual(report["accepted_case_count"], 0)
        self.assertEqual(
            (report["declared_artifact_steps"], report["actual_model_command_steps"]), (3, 64)
        )

    def test_twenty_repaired_record_controls_are_reachable(self):
        controls = r.mutation_controls(packet())
        self.assertEqual(len(controls), 20)
        self.assertTrue(all(x["refused"] for x in controls))

    def test_generic_original_payload_equality_is_typed(self):
        d = packet()
        d["result"]["cases"][0]["result"]["payload"]["result"]["usage"]["steps"] = False
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("accepted", d)

    def test_repaired_request_digest_does_not_rebind_old_result(self):
        d = packet()
        c = d["result"]["cases"][0]
        c["request"]["declaration_id"] = "authored:changed"
        c["request_digest"] = r.sha(r.canonical(c["request"]))
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("accepted", d)

    def test_boolean_generic_usage_is_rejected(self):
        d = packet()
        d["result"]["cases"][0]["result"]["usage"]["steps"] = False
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("accepted", d)

    def test_boolean_owned_lease_count_is_rejected(self):
        d = packet()
        d["launch_audit"][0]["owned_leases"][0]["cpu_slots"] = True
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("accepted", d)

    def test_foreign_allocations_are_only_lower_bound(self):
        d = packet()
        for row in d["launch_audit"]:
            row["root_allocations"]["cpu_slots"] += 2
        self.assertTrue(r.reconcile_attempt("accepted", d)["historical_owned_resource_drain"])

    def test_fairness_promotion_is_rejected(self):
        d = packet()
        c = d["result"]["cases"][0]
        c["original_outcome"]["receipt"]["capability"]["checks_fairness"] = True
        c["result"]["payload"]["result"] = copy.deepcopy(c["original_outcome"]["result"])
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("accepted", d)

    def test_failed_attempt_cannot_publish_accepted_case(self):
        d = packet(True)
        d["result"]["cases"] = packet()["result"]["cases"][:1]
        with self.assertRaises(r.Refusal):
            r.reconcile_attempt("initial_failed", d)

    def test_metadata_source_pins_are_not_opened(self):
        self.assertEqual(len(r.reconcile_attempt("accepted", packet())["cases"]), 2)

    def test_duplicate_json_rejected(self):
        with self.assertRaises(r.Refusal):
            r.document(b'{"x":1,"x":2}')

    def test_nonfinite_json_rejected(self):
        for raw in (b"NaN", b"Infinity", b"1e9999"):
            with self.subTest(raw=raw), self.assertRaises(r.Refusal):
                r.document(raw)

    def test_depth_is_bounded_before_json_parse(self):
        with self.assertRaises(r.Refusal):
            r.document(b"[" * 33 + b"0" + b"]" * 33)

    def test_surrogate_json_rejected(self):
        with self.assertRaises(r.Refusal):
            r.document(b'"\\ud800"')

    def test_integer_json_bound(self):
        with self.assertRaises(r.Refusal):
            r.document(str(2**63).encode())

    def test_positive_receiver_and_retained_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest, anchors = write_fixture(root)
            original = {
                Path(p["path"]): Path(p["path"]).read_bytes()
                for p in [manifest["qualification"], manifest["source_evolution"]]
                + [v for a in manifest["attempts"] for k, v in a.items() if k != "id"]
            }
            with patch.object(r, "ANCHORS", anchors):
                report = r.audit(path, root / "output")
            self.assertEqual(report["selected_file_count"], 20)
            self.assertEqual(len(list((root / "output").rglob("*.json"))), 22)
            self.assertTrue(all(report[x] is True for x in r.TRUE))
            self.assertTrue(all(report[x] is False for x in r.FALSE))
            self.assertTrue(all(type(report[x]) is int and report[x] == 0 for x in r.ZERO))
            self.assertEqual(report["production_tasks_closed"], [])
            self.assertTrue(all(p.read_bytes() == b for p, b in original.items()))

    def test_bad_manifest_schema(self):
        self.manifest_fault(lambda m: m.update(schema="future@2"))

    def test_unknown_manifest_field(self):
        self.manifest_fault(lambda m: m.update(current_authority=True))

    def test_selected_order_changed(self):
        self.manifest_fault(lambda m: m["attempts"].reverse())

    def test_selected_body_duplicate(self):
        self.manifest_fault(lambda m: m["attempts"][1].update(result=m["attempts"][0]["result"]))

    def test_selected_size_boolean(self):
        self.manifest_fault(lambda m: m["qualification"].update(size=True))

    def test_selected_digest_repaired_but_anchor_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, m, anchors = write_fixture(root)
            pin = m["qualification"]
            p = Path(pin["path"])
            raw = p.read_bytes() + b"\n"
            p.write_bytes(raw)
            pin.update(size=len(raw), sha256=r.sha(raw))
            path.write_bytes(r.canonical(m))
            with patch.object(r, "ANCHORS", anchors), self.assertRaises(r.Refusal):
                r.audit(path, root / "output")

    def test_selected_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, m, anchors = write_fixture(root)
            p = Path(m["qualification"]["path"])
            moved = p.with_name("moved.json")
            p.rename(moved)
            p.symlink_to(moved)
            with patch.object(r, "ANCHORS", anchors), self.assertRaises(r.Refusal):
                r.audit(path, root / "output")

    def test_selected_fifo_is_refused_without_open(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "fifo"
            os.mkfifo(p)
            with self.assertRaises(r.Refusal):
                r.bounded(p, 100)

    def test_body_cap_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "body"
            p.write_bytes(b"abc")
            with (
                patch.object(r.os, "open", side_effect=AssertionError("must not open")),
                self.assertRaises(r.Refusal),
            ):
                r.bounded(p, 2)

    def test_output_must_be_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _, anchors = write_fixture(root)
            (root / "output").mkdir()
            with patch.object(r, "ANCHORS", anchors), self.assertRaises(r.Refusal):
                r.audit(path, root / "output")

    def test_output_cannot_nest_with_selected_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _, anchors = write_fixture(root)
            with patch.object(r, "ANCHORS", anchors), self.assertRaises(r.Refusal):
                r.audit(path, path.parent / "output")

    def test_aggregate_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _, anchors = write_fixture(root)
            with (
                patch.object(r, "ANCHORS", anchors),
                patch.object(r, "MAX_TOTAL", 10),
                self.assertRaises(r.Refusal),
            ):
                r.audit(path, root / "output")

    def test_late_original_change_refused(self):
        self.late_fault("original")

    def test_late_retained_copy_change_refused(self):
        self.late_fault("copy")

    def test_late_retained_manifest_change_refused(self):
        self.late_fault("manifest")

    def test_late_report_change_refused(self):
        self.late_fault("report")

    def test_late_extra_file_refused(self):
        self.late_fault("extra")

    def test_late_extra_directory_refused(self):
        self.late_fault("directory")

    def test_late_output_symlink_refused(self):
        self.late_fault("symlink")

    def test_late_mutation_after_first_population_check_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _, anchors = write_fixture(root)
            ordinary = r.population
            count = [0]

            def population(output, expected):
                ordinary(output, expected)
                count[0] += 1
                if count[0] == 1:
                    (output / "extra").write_text("late")

            with (
                patch.object(r, "ANCHORS", anchors),
                patch.object(r, "population", population),
                self.assertRaises(r.Refusal),
            ):
                r.audit(path, root / "output")

    def manifest_fault(self, mutate):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest, anchors = write_fixture(root)
            mutate(manifest)
            path.write_bytes(r.canonical(manifest))
            with patch.object(r, "ANCHORS", anchors), self.assertRaises((r.Refusal, OSError)):
                r.audit(path, root / "output")

    def late_fault(self, kind):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest, anchors = write_fixture(root)
            ordinary = r.final_fence

            def fence(capture, output, expected):
                if kind == "original":
                    Path(manifest["qualification"]["path"]).write_bytes(b"changed")
                elif kind == "copy":
                    (output / "retained/00-qualification.json").write_bytes(b"changed")
                elif kind == "manifest":
                    (output / "retained/input_manifest.json").write_bytes(b"changed")
                elif kind == "report":
                    (output / r.REPORT_NAME).write_bytes(b"changed")
                elif kind == "extra":
                    (output / "extra").write_bytes(b"changed")
                elif kind == "directory":
                    (output / "extra").mkdir()
                elif kind == "symlink":
                    (output / "extra").symlink_to(path)
                ordinary(capture, output, expected)

            with (
                patch.object(r, "ANCHORS", anchors),
                patch.object(r, "final_fence", fence),
                self.assertRaises((r.Refusal, OSError)),
            ):
                r.audit(path, root / "output")


if __name__ == "__main__":
    unittest.main()
