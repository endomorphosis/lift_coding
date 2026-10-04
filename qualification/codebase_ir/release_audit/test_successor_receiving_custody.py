"""Detached receiving declarations and repaired-metadata refusal controls; stdlib only."""
import base64
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock

_SPEC = importlib.util.spec_from_file_location("receiving_custody", Path(__file__).with_name("successor_receiving_custody.py"))
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


def pin(value):
    raw = m.canonical(value)
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def archived(rows):
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {"files": rows, "regular_files": sum(row["kind"] == "file" for row in rows),
            "regular_bytes": sum(row.get("bytes", 0) for row in rows),
            "inventory_cid": "b" + base64.b32encode(b"\x01\xa9\x02\x12\x20" + sha256(raw).digest()).decode().lower().rstrip("=")}


def refreshed(docs):
    received = docs["actual_receiving"]
    for row in received["actual_relocations"]["relocations"]:
        row["before_sha256"] = sha256(m.wire(row["before"])).hexdigest()
        row["after_sha256"] = sha256(m.wire(row["after"])).hexdigest()
    docs["full_scan_native"]["host_configuration_pin"] = pin(docs["host_configuration"])
    docs["full_scan_audit"]["shared_host"]["configuration_pin"] = pin(docs["host_configuration"])
    native_pin, audit_pin = pin(docs["full_scan_native"]), None
    docs["full_scan_audit"]["audited_result"] = {"path": "result.json", **native_pin}
    audit_pin = pin(docs["full_scan_audit"])
    received["staged"]["native_result"] = native_pin
    received["staged"]["audit"] = audit_pin
    received["host_configuration"] = {"path": "/declared/host.json", **pin(docs["host_configuration"])}
    received["materialized"]["staged_receipt"] = copy.deepcopy(received["staged"])
    received["materialized"]["staged_receipt_sha256"] = sha256(m.wire(received["staged"]) + b"\n").hexdigest()
    received["actual_relocations"]["materialization_sha256"] = sha256(m.wire(received["materialized"]) + b"\n").hexdigest()
    for suffix in ("02", "03"):
        container = docs[f"failed_worker_{suffix}_container"]
        container["source_audit"] = audit_pin
        container["host_configuration_pin"] = pin(docs["host_configuration"])
        container["container_resource_authority"]["parent_host_envelope"]["host_configuration_pin"] = pin(docs["host_configuration"])
        docs[f"failed_worker_{suffix}_native"]["container_resource_authority_pin"] = pin(container["container_resource_authority"])
    return docs


def fixture():
    digest = "1" * 64
    namespace, output, staged_destination = "/declared/fullscan", "/declared/receiver", "/declared/stage"
    drain = {"scope": "named_scan_process_owners_only", "active_lease_count": 0, "waiting_request_count": 0,
             "global_active_lease_count": 0, "global_waiting_request_count": 0, "owner_pids": [123]}
    checkpoint = {role: {"artifact": {"bytes": epochs, "sha256": digest}, "adam_steps": [epochs] * 4,
        "completed_epochs": epochs, "feature_columns": 53, "latent_width": 8, "report_sha256": digest,
        "state_sha256": digest} for role, epochs in (("root", 1), ("child", 2))}
    head, previous = {"generation": 2, "snapshot_cid": "child-snapshot"}, {"generation": 1, "snapshot_cid": "parent-snapshot"}
    host = {"schema": "successor-expansion-host-configuration@1", "kernel_enforcement_claimed": False,
            "persisted_config": {"total_cpu_slots": 16}, "state_path": "/declared/admission.json"}
    native = {"schema": "codebase-full-successor-native-qualification@1", "qualified": True, "complete_scan_qualified": True,
        "proof_authority": False, "worker_dispatch_qualified": False, "source_execution_attested": False, "scan_execution_attested": False,
        "cuda_qualified": False, "384d_qualified": False, "production_default_activated": False, "root_cid": "root", "completion_cid": "complete",
        "successor_selection_cid": "selection", "child_version_id": "child", "parent_version_id": "parent", "source_delta_cid": "delta",
        "current_head": head, "previous_head": previous, "checkpoint_states": checkpoint, "coverage": {"inventory_entries": 300, "pages": 10},
        "scheduler_configuration": host["persisted_config"], "scheduler_state_path": host["state_path"], "final_resources": drain}
    audit = {"schema": "codebase-full-successor-independent-audit@1", "qualified": True, "complete_scan_qualified": True,
        "errors": [], "preserved": True, "proof_authority": False, "worker_dispatch_qualified": False, "native_owners_opened": False,
        "sql_executed": False, "git_executed": False, "numerical_execution_independently_reperformed": False, "process_origin_attested": False,
        "namespace": namespace, "complete_scan": {"completion_cid": "complete"}, "shared_host": {}}
    rows = [{"path": ".", "kind": "directory", "mode": 0o700, "mtime_ns": 1}]
    for index in range(1631):
        rows.append({"path": f"member-{index:04}.json", "kind": "file", "mode": 0o444, "mtime_ns": 1,
                     "bytes": 75552029 if index == 0 else 1, "sha256": digest, "nlink": 1})
    for path in ("progress.json", "private/model.duckdb.owner.lock"):
        rows.append({"path": path, "kind": "file", "mode": 0o444, "mtime_ns": 1, "bytes": 1, "sha256": digest, "nlink": 1})
    archive = archived(rows)
    copied = [{"path": "closed-full-scan/" + row["path"], "source_path": row["path"],
               **{key: row[key] for key in ("bytes", "sha256", "mode")}} for row in rows[1:1632]]
    staged = {"schema": "source-successor-dispatch-staged-setup@1", "qualified": True, "fresh_native_receiving_required": True,
        "native_owners_opened": False, "proof_authority": False, "source_execution_attested": False, "scan_execution_attested": False,
        "new_fitting_epochs": 0, "new_scan_pages": 0, "source_namespace": namespace, "staged_destination": staged_destination,
        "root_cid": "root", "completion_cid": "complete", "selection_cid": "selection", "selected_version_id": "child",
        "previous_version_id": "parent", "source_delta_cid": "delta", "current_head": head, "previous_head": previous,
        "checkpoint_states": checkpoint, "inherited_scan_pages": 10, "inherited_reference_pages": 1, "inherited_setup_epochs": 2,
        "source_archive_inventory_cid": archive["inventory_cid"], "copied_members": copied, "copied_files": 1631, "copied_bytes": 75553659}
    relocation_rows = []
    for owner, suffix in (("source", "source-artifacts"), ("registry", "model-artifacts")):
        old, new = namespace + "/private/" + suffix, output + "/private/" + suffix
        before = {"meta": [[1, "schema", "id", "salt", old, 8]]} if owner == "registry" else {"catalog": {"meta": [[1, "schema", "id", "salt", old]]}, "ast": {}}
        after = copy.deepcopy(before)
        meta = after["meta"] if owner == "registry" else after["catalog"]["meta"]
        meta[0][4] = new
        relocation_rows.append({"owner": owner, "old_artifact_root": old, "new_artifact_root": new, "before": before, "after": after,
            "only_local_path_changed": True, "old_native_owners_opened": False, "native_publication_performed": False,
            "fitting_performed": False, "owner_generation_advanced": False})
    registry = copy.deepcopy(relocation_rows[1]["after"])
    registry["meta"][0][5] = 9
    owners = {"source": {"current_head": head, "tables": {}}, "registry": registry, "model_artifacts": []}
    received = {"schema": "source-successor-dispatch-actual-receiving@1", "qualified": True, "error": None,
        "actual_native_receiving_complete": True, "current_source_receiving_verified": True, "current_pins_unchanged": True,
        "proof_authority": False, "signed_admission_qualified": False, "source_execution_attested": False, "scan_execution_attested": False,
        "kernel_resource_enforcement": False, "native_owners_in_old_archives_opened": False, "git_in_old_archives_executed": False,
        "new_scan_pages": 0, "new_fitting_epochs": 0, "inference_attempts": 0, "post_setup_fit_attempt_count": 0,
        "owner_pairs_opened": 1, "registry_owner_generation_increment_from_native_open": 1,
        "closed_source_archive_preserved": True, "old_closed_archive_preserved": True, "staged_archive_preserved": True,
        "own_lease_released": True, "rss_reservation_respected": True, "staged": staged,
        "materialized": {"schema": "source-successor-dispatch-materialized-setup@1", "qualified": True,
            "fresh_native_receiving_required": True, "native_owners_opened": False, "proof_authority": False,
            "new_fitting_epochs": 0, "new_scan_pages": 0, "seed": staged_destination, "output": output},
        "actual_relocations": {"schema": "source-successor-dispatch-copied-store-relocations@1", "qualified": True,
            "native_owner_generation_advanced": False, "old_native_owners_opened": False, "proof_authority": False,
            "new_fitting_epochs": 0, "new_scan_pages": 0, "output": output, "relocations": relocation_rows},
        "source_namespace": namespace, "checkpoint_states_before": checkpoint, "checkpoint_states_after": checkpoint,
        "source_archive_before": archive, "old_archive_before": archived(rows[:2]), "native_owners_before": owners,
        "native_owners_after": copy.deepcopy(owners), "resources_after": drain,
        "admission": {"state_path": host["state_path"], "cpu_slots": 1, "child_process_slots": 1, "memory_mb": 2048},
        "peak_rss_bytes": 1024, "recorded_seconds": 1.5}
    docs = {"full_scan_native": native, "full_scan_audit": audit, "actual_receiving": received, "host_configuration": host,
        "transport_controls": {"schema": "source-successor-dispatch-stdlib-controls@1", "qualified": True, "tests": 79,
            "failures": 0, "errors": 0, "skipped": 0, "new_fitting_epochs": 0, "new_inference_pages": 0, "git_executed": False,
            "native_owners_opened": False, "sql_executed": False, "scope": "synthetic detached transport"},
        "signed_reader_controls": {"schema": "signed-successor-independent-receipt-reader-controls@1", "qualified": True,
            "test_count": 78, "returncode": 0, "scope": "synthetic full300 public-signature controls",
            **dict.fromkeys(("completion_authority", "docker_executed", "git_executed", "inference_executed", "native_owners_opened",
                            "process_origin_attested", "proof_authority", "source_repository_executed", "training_executed"), False)}}
    for suffix in ("02", "03"):
        error = ("SourceSuccessorAuditError", "structured identity rejects unreviewed scalar") if suffix == "02" else ("LeaseTimeoutError", "resumable inventory deadline exceeded")
        phases = [{"name": name, "status": "completed", "elapsed_seconds": 1.0} for name in (
            "materialize_independently_audited_complete_successor", "open_only_new_copied_native_owners", "receive_full_successor_default_pair_120_then30")]
        if suffix == "03":
            phases += [{"name": "initialize_private_signed_owner", "status": "completed", "elapsed_seconds": 1.0},
                {"name": "sign_fresh_full_successor_task_manifest", "status": "failed", "elapsed_seconds": 120.0, "error_type": error[0], "error": error[1]}]
        failed = {"schema": "codebase-signed-successor-native-qualification@1", "qualified": False, "error_type": error[0], "error": error[1],
            "phases": phases, **dict.fromkeys(("proof_authority", "source_execution_attested", "scan_execution_attested", "production_default_activated",
                "cuda_qualified", "384d_qualified", "complete_scan_reexecuted_here", "shares_host_pid_state"), False),
            **dict.fromkeys(("inference_attempt_count", "new_fitting_epochs", "post_setup_fit_attempt_count", "new_scan_pages", "new_reference_pages", "provider_calls"), 0),
            "inherited_scan_pages": 10, "inherited_reference_pages": 1, "inherited_setup_epochs": 2, "local_pool_bounded_by_host_envelope": True,
            "root_cid": "root", "completion_cid": "complete", "selected_version_id": "child", "recorded_seconds": 150.0,
            "public_receivers_reference_close": {"budget_refused": True, "completed": False, "integrity_refusal_claimed": False,
                "deadline_seconds": 30, "elapsed_seconds": 30.01, "error_type": "LeaseTimeoutError", "error": "resumable inventory deadline exceeded"},
            "final_resources": drain}
        host_reservation = {"cpu_slots": 12, "child_process_slots": 12, "memory_mb": 8192, "released": False}
        authority = {"independent_whole_host_pool": False, "shares_host_pid_state": False, "proof_authority": False,
            "parent_host_envelope": {"host_reservation": host_reservation, "container_id": "container-" + suffix},
            "persisted_config": {"total_cpu_slots": 9, "total_memory_mb": 6553}}
        container = {"schema": "signed-successor-worker-offline-container-execution@1", "returncode": 1, "proof_authority": False,
            "production_activated": False, "privileged": False, "network": "none", "host_reservation_acquired": True,
            "host_reservation_released": True, "host_lease_held_after_native_exit": True, "container_removed": True,
            "container_results_copied": True, "new_scan_pages_created": 0, "new_setup_fitting_epochs": 0, "container_id": "container-" + suffix,
            "memory_limit_bytes": 8192 * 1024 * 1024, "cpu_limit": 12, "pids_limit": 512, "elapsed_seconds": 177.0,
            "actual_container_limits": {"inspection_returncode": 0, "cgroup_returncode": 0, "inspection": {"Id": "container-" + suffix,
                "HostConfig": {"Memory": 8192 * 1024 * 1024, "NanoCpus": 12 * 10**9, "PidsLimit": 512, "NetworkMode": "none", "Privileged": False}},
                "cgroup": {"values": {"cpu.max": "1200000 100000", "memory.max": str(8192 * 1024 * 1024), "pids.max": "512"}}},
            "container_resource_authority": authority, "host_reservation": host_reservation,
            "container_absence_observation": {"container_id": "container-" + suffix, "returncode": 0, "stdout": ""}, "host_owned_resources_after_cleanup": drain}
        docs[f"failed_worker_{suffix}_native"], docs[f"failed_worker_{suffix}_container"] = failed, container
    return refreshed(docs)


class ReceivingDeclarations(unittest.TestCase):
    def setUp(self):
        self.docs = fixture()

    def reconcile(self):
        pins = {role: {"size_bytes": pin(value)["bytes"], "sha256": pin(value)["sha256"]} for role, value in self.docs.items()}
        receiving, resources = m.receiving_receipt(self.docs, pins)
        failures = [m.failed_worker_receipt(self.docs[f"failed_worker_{suffix}_native"], self.docs[f"failed_worker_{suffix}_container"],
                    pins, suffix, receiving) for suffix in ("02", "03")]
        controls = m.control_receipts(self.docs)
        return receiving, resources, failures, controls

    def test_complete_declared_receiving_and_separate_failed_workers(self):
        receiving, resources, failures, controls = self.reconcile()
        self.assertEqual(receiving["staged_archive"]["declared_regular_files"], 1631)
        self.assertEqual(len(failures), 2)
        self.assertFalse(failures[1]["signed_worker_qualification"])
        self.assertFalse(resources["actual_receiving"]["live_cleanup_reobserved"])
        self.assertEqual(controls["signed_reader"]["recorded_case_count"], 78)

    def test_repaired_source_path_relocation_preserves_complete_other_rows(self):
        received = self.docs["actual_receiving"]
        received["actual_relocations"]["relocations"][0]["after"]["ast"] = {"forged": True}
        refreshed(self.docs)
        with self.assertRaisesRegex(ValueError, "unrelated owner rows"):
            self.reconcile()

    def test_repaired_registry_owner_advance_refuses_extra_native_change(self):
        received = self.docs["actual_receiving"]
        received["native_owners_after"]["registry"]["extra"] = "unexpected"
        with self.assertRaisesRegex(ValueError, "sole native open"):
            self.reconcile()

    def test_forged_archive_CID_refused_before_named_body_open(self):
        self.docs["actual_receiving"]["source_archive_before"]["inventory_cid"] = "invented"
        with self.assertRaisesRegex(ValueError, "metadata CID"):
            self.reconcile()

    def test_coherent_rehashed_member_mode_change_refused(self):
        r = self.docs["actual_receiving"]
        r["staged"]["copied_members"][0]["mode"] = 0o600
        refreshed(self.docs)
        with self.assertRaisesRegex(ValueError, "byte/mode declarations"):
            self.reconcile()

    def test_coherent_rehashed_excluded_owner_lock_retained_refused(self):
        r = self.docs["actual_receiving"]
        row = r["staged"]["copied_members"][0]
        row["source_path"], row["path"] = "private/model.duckdb.owner.lock", "closed-full-scan/private/model.duckdb.owner.lock"
        refreshed(self.docs)
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_checkpoint_declaration_boolean_epoch_rejected(self):
        self.docs["actual_receiving"]["staged"]["checkpoint_states"]["root"]["completed_epochs"] = True
        refreshed(self.docs)
        with self.assertRaisesRegex(ValueError, "exact integer"):
            self.reconcile()

    def test_historical_inner_pool_is_not_new_whole_host_pool(self):
        self.docs["failed_worker_03_container"]["container_resource_authority"]["independent_whole_host_pool"] = True
        refreshed(self.docs)
        with self.assertRaisesRegex(ValueError, "local accounting scope"):
            self.reconcile()


def mutation_test(path, value):
    def test(self):
        target = self.docs
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        refreshed(self.docs)
        with self.assertRaises(ValueError):
            self.reconcile()
    return test


MUTATIONS = {
    "receiving_signed_authority": (("actual_receiving", "signed_admission_qualified"), True),
    "receiving_training_alias": (("actual_receiving", "new_fitting_epochs"), False),
    "receiving_page_inference": (("actual_receiving", "new_scan_pages"), 1),
    "receiving_two_owner_pairs": (("actual_receiving", "owner_pairs_opened"), 2),
    "receiving_boolean_owner_pair": (("actual_receiving", "owner_pairs_opened"), True),
    "receiving_wrong_generation_increment": (("actual_receiving", "registry_owner_generation_increment_from_native_open"), 2),
    "receiving_boolean_resource_drain": (("actual_receiving", "resources_after", "active_lease_count"), False),
    "receiving_unclean_resource_drain": (("actual_receiving", "resources_after", "waiting_request_count"), 1),
    "receiving_false_source_preservation": (("actual_receiving", "closed_source_archive_preserved"), False),
    "receiving_wrong_admission_memory": (("actual_receiving", "admission", "memory_mb"), 4096),
    "staged_wrong_complete_scan_denominator": (("full_scan_native", "coverage", "inventory_entries"), 299),
    "staged_wrong_inherited_epochs": (("actual_receiving", "staged", "inherited_setup_epochs"), 4),
    "staged_wrong_inherited_reference_pages": (("actual_receiving", "staged", "inherited_reference_pages"), 10),
    "staged_wrong_member_count": (("actual_receiving", "staged", "copied_files"), 1630),
    "staged_wrong_byte_sum": (("actual_receiving", "staged", "copied_bytes"), 75553660),
    "staged_selected_child_substitution": (("actual_receiving", "staged", "selected_version_id"), "parent"),
    "failed_whole_attempt_promoted": (("failed_worker_02_native", "qualified"), True),
    "failed_reference_timeout_promoted_to_integrity": (("failed_worker_02_native", "public_receivers_reference_close", "integrity_refusal_claimed"), True),
    "failed_reference_close_completed": (("failed_worker_03_native", "public_receivers_reference_close", "completed"), True),
    "failed_attempt_added_fit": (("failed_worker_03_native", "new_fitting_epochs"), 1),
    "failed_attempt_extra_provider_calls": (("failed_worker_02_native", "provider_calls"), 1),
    "failed_attempt_missing_sign_phase": (("failed_worker_03_native", "phases"), []),
    "failed_attempt_terminal_reason_substituted": (("failed_worker_03_native", "error"), "not a deadline"),
    "failed_container_driver_success": (("failed_worker_03_container", "returncode"), 0),
    "failed_container_boolean_returncode": (("failed_worker_03_container", "returncode"), True),
    "failed_container_reserved_memory_doubled": (("failed_worker_02_container", "host_reservation", "memory_mb"), 16384),
    "failed_container_stored_reservation_release_alias": (("failed_worker_03_container", "host_reservation", "released"), True),
    "failed_container_removed_flag": (("failed_worker_03_container", "container_removed"), False),
    "failed_container_host_not_released": (("failed_worker_02_container", "host_reservation_released"), False),
    "failed_container_bad_cgroup_memory": (("failed_worker_03_container", "actual_container_limits", "cgroup", "values", "memory.max"), "max"),
    "failed_container_wrong_ID": (("failed_worker_03_container", "actual_container_limits", "inspection", "Id"), "another"),
    "failed_container_network_access": (("failed_worker_02_container", "network"), "host"),
    "transport_synthetic_native_upgrade": (("transport_controls", "native_owners_opened"), True),
    "transport_case_count_substituted": (("transport_controls", "tests"), 78),
    "signed_reader_case_count_substituted": (("signed_reader_controls", "test_count"), 79),
    "signed_reader_process_origin_authority": (("signed_reader_controls", "process_origin_attested"), True),
    "signed_reader_native_qualification": (("signed_reader_controls", "docker_executed"), True),
}
for label, (path, value) in MUTATIONS.items():
    setattr(ReceivingDeclarations, "test_refuses_" + label, mutation_test(path, value))


class ReceivingFiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.docs = fixture()
        self.rows = []
        for index, role in enumerate(m.ROLES):
            p = self.root / f"{index:02}.json"
            raw = m.canonical(self.docs[role])
            p.write_bytes(raw)
            self.rows.append({"role": role, "path": str(p), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)})
        self.pins = {row["role"]: row["sha256"] for row in self.rows}
        self.manifest = self.root / "input.json"
        self.spec = {"schema": m.INPUT_SCHEMA, "selected_profile": m.PROFILE, "selected_files": self.rows}
        self.manifest.write_bytes(m.canonical(self.spec))
        self.output = self.root / "output"

    def audit(self):
        with mock.patch.object(m, "PUBLIC_PINS", self.pins):
            return m.audit(self.manifest, self.output)

    def test_positive_closed13_body_output_and_local_receipt(self):
        report = self.audit()
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 13)
        self.assertTrue(report["qualified"])
        self.assertEqual(report["selected_file_count"], 10)
        self.assertEqual(report["custody"]["original_file_count"], 11)
        for field in m.FALSE_FLAGS:
            self.assertIs(report[field], False)
        for field in m.ZERO_FIELDS:
            self.assertIs(type(report[field]), int)
            self.assertEqual(report[field], 0)
        nested = report["custody"]["local_receipt"]
        self.assertEqual(sha256(Path(nested["path"]).read_bytes()).hexdigest(), nested["sha256"])

    def test_repaired_all_manifest_pins_cannot_replace_fixed_public_body(self):
        self.docs["actual_receiving"]["recorded_seconds"] = 2.5
        p = Path(self.rows[2]["path"])
        raw = m.canonical(self.docs["actual_receiving"])
        p.write_bytes(raw)
        self.rows[2]["sha256"], self.rows[2]["size_bytes"] = sha256(raw).hexdigest(), len(raw)
        self.manifest.write_bytes(m.canonical(self.spec))
        with self.assertRaisesRegex(ValueError, "public selection"):
            self.audit()

    def test_extra_selected_descriptor_field_refused(self):
        self.rows[0]["extra"] = True
        self.manifest.write_bytes(m.canonical(self.spec))
        with self.assertRaisesRegex(ValueError, "closed selected"):
            self.audit()

    def test_reordered_selected_roles_refused(self):
        self.rows[0], self.rows[1] = self.rows[1], self.rows[0]
        self.manifest.write_bytes(m.canonical(self.spec))
        with self.assertRaisesRegex(ValueError, "ordered selected"):
            self.audit()

    def test_boolean_size_refused_before_selected_body_open(self):
        self.rows[0]["size_bytes"] = True
        self.manifest.write_bytes(m.canonical(self.spec))
        with self.assertRaisesRegex(ValueError, "exact integer"):
            self.audit()

    def test_oversized_descriptor_refused_before_body_open(self):
        self.rows[0]["size_bytes"] = m.MAX_FILE + 1
        self.manifest.write_bytes(m.canonical(self.spec))
        with self.assertRaisesRegex(ValueError, "exact integer"):
            self.audit()

    def test_symlink_selected_body_refused(self):
        p = Path(self.rows[0]["path"])
        p.rename(self.root / "real.json")
        p.symlink_to(self.root / "real.json")
        with self.assertRaisesRegex(ValueError, "nonsymlink"):
            self.audit()

    def test_fifo_selected_body_refused_without_blocking(self):
        p = Path(self.rows[0]["path"])
        p.unlink()
        os.mkfifo(p)
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.audit()

    def test_late_selected_original_replacement_refused(self):
        stable = m.Capture.stable
        calls = 0
        def changed(capture):
            nonlocal calls
            calls += 1
            if calls == 2:
                Path(self.rows[2]["path"]).write_bytes(b"changed")
            return stable(capture)
        with mock.patch.object(m.Capture, "stable", changed), self.assertRaises(ValueError):
            self.audit()

    def test_late_selected_copy_replacement_refused(self):
        stable = m.Capture.stable
        def changed(capture):
            if any(p.parent.name == "retained" for p in capture.files):
                p = self.output / "retained/02-actual_receiving.json"
                p.chmod(0o600)
                p.write_bytes(b"changed")
            return stable(capture)
        with mock.patch.object(m.Capture, "stable", changed), self.assertRaises(ValueError):
            self.audit()

    def test_extra_output_file_after_main_raw_reread_refused(self):
        raw = m.Capture.raw
        def changed(path, maximum):
            value = raw(path, maximum)
            if path.name == "successor_receiving_custody.json":
                (self.output / "unexpected").write_bytes(b"changed")
            return value
        with mock.patch.object(m.Capture, "raw", staticmethod(changed)), self.assertRaisesRegex(ValueError, "owned output population"):
            self.audit()

    def test_late_local_nested_report_corruption_refused(self):
        raw = m.Capture.raw
        def changed(path, maximum):
            if path.name == "selected_custody.json":
                path.chmod(0o600)
                path.write_bytes(b"changed")
            return raw(path, maximum)
        with mock.patch.object(m.Capture, "raw", staticmethod(changed)), self.assertRaises(ValueError):
            self.audit()

    def test_duplicate_JSON_member_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            m.document(b'{"x":0,"x":1}')

    def test_nonfinite_JSON_refused(self):
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.document(b'{"x":NaN}')

    def test_surrogate_JSON_refused(self):
        with self.assertRaisesRegex(ValueError, "bounded JSON text"):
            m.document(b'{"x":"\\ud800"}')

    def test_excessive_JSON_depth_refused_before_decode(self):
        with self.assertRaisesRegex(ValueError, "allocation bound"):
            m.document(b'{"x":' + b'[' * 40 + b'0' + b']' * 40 + b'}')

    def test_elapsed_deadline_refused(self):
        with mock.patch.object(m, "MAX_SECONDS", -1), self.assertRaisesRegex(ValueError, "deadline"):
            self.audit()

    def test_existing_output_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "fresh canonical"):
            self.audit()

    def test_output_within_selected_path_ancestor_refused(self):
        self.output = Path(self.rows[0]["path"]) / "output"
        with self.assertRaises(ValueError):
            self.audit()

    def test_explicit_remap_cannot_omit_selected_member(self):
        remap = {str(self.manifest): str(self.manifest), **{row["path"]: row["path"] for row in self.rows[:-1]}}
        with mock.patch.object(m, "PUBLIC_PINS", self.pins), self.assertRaisesRegex(ValueError, "relocated input population"):
            m.audit(self.manifest, self.output, relocated_sources=remap)


if __name__ == "__main__":
    unittest.main()
