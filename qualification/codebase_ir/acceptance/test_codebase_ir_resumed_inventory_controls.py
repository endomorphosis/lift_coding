"""Authored receiving controls; no external workspace, owner, or native tools."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resumed_inventory_controls import receiver as codec


def fixture_bundle():
    """Independently authored closed packets with stated 300/10/4 goldens."""
    def digest(label):
        return codec.sha(label.encode())

    def raw_cid(label):
        return codec.cid_raw(label.encode())

    false = dict.fromkeys(sorted(codec.AUTHORITY), False)
    head = {"schema": "codebase-head@1", "repository_id": "authored-receiver",
            "generation": 1, "snapshot_cid": codec.cid({"snapshot": 1}),
            "manifest_cid": codec.cid({"manifest": 1}), "receipt_cid": codec.cid({"receipt": 1}),
            "ast_revision_id": "authored-revision"}
    artifact = {"bytes": 3, "sha256": digest("one")}
    model = {"artifact": artifact, "artifact_cid": raw_cid("one"), "ancestry": [
        {"artifact": artifact, "version_id": "sha256:" + digest("child")},
        {"artifact": {"bytes": 3, "sha256": digest("two")}, "version_id": "sha256:" + digest("parent")}],
        "version_id": "sha256:" + digest("child"), "variant_id": "authored-variant",
        "contract_sha256": digest("contract"), "feature_space_sha256": digest("basis"),
        "state_sha256": digest("state"), "feature_columns": 53, "latent_width": 8,
        "projection_ids": ["codebase_ir.contracts@1", "codebase_ir.program@1"],
        "projection_widths": {"codebase_ir.contracts@1": 2, "codebase_ir.program@1": 51}}
    paths = ["README.md", *(f"bulk{n:03d}.py" for n in range(291)), "calc.py", "canary.py", "check_offset.py",
             "check_type.py", "malformed.py", "non_utf8.py", "oversized.dat", "tune.py"]
    members = []
    for n, path in enumerate(paths):
        status = "unindexed" if n == 0 else "failed" if n == 296 else "opaque" if n in (297, 298) else "ok"
        members.append({"path": path, "raw_path_hex": path.encode().hex(), "source_key": "raw:" + path.encode().hex(),
                        "entry_cid": codec.cid({"authored_entry": n}), "ast_cid": codec.cid({"authored_ast": n}) if status in ("ok", "failed") else None,
                        "source_cid": None if n == 298 else raw_cid("source-" + str(n)),
                        "source_size_bytes": 65537 if n == 298 else 47, "parse_status": status,
                        "opaque_reason": "undecodable" if n == 297 else "oversized" if n == 298 else None})
    files = {"ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_resume_worker": digest("worker")}
    root = {"schema": "codebase-inventory-resume-root@1", "authority": false, "optimized": True,
            "head": head, "head_cid": codec.cid(head), "members": members, "membership_cid": codec.cid(members),
            "model": model, "implementation": {"files": files, "scope": "listed_local_files_only_not_execution_attestation",
                                               "sha256": codec.sha(codec.wire(files))},
            "limits": {"max_file_bytes": 65536, "max_inferred_rows": 1024, "max_input_bytes": 33554432,
                       "max_inventory_entries": 512, "max_manifest_bytes": 4194304, "max_output_bytes": 16777216,
                       "max_pages": 1024, "max_target_bytes": 4194304, "page_entries": 32}}
    root_id = codec.cid(root)
    numeric = {"adam_steps": [2, 2, 2, 2], "completed_epochs": 2, "feature_columns": 53,
               "latent_width": 8, "state_sha256": model["state_sha256"]}
    transport, pages, summaries = {"root": root}, [], []
    previous = None
    for number in range(10):
        start, end = number * 32, min(number * 32 + 32, 300)
        entries, rows, atoms = [], [], []
        for n in range(start, end):
            member = members[n]
            if n == 0:
                disposition, reason = "unindexed", "captured_source_has_no_ast_projection"
            elif n in (294, 295):
                disposition, reason = "unsupported_target", "native_target_not_complete"
            elif n == 296:
                disposition, reason = "parse_failed", "captured_parse_failed"
            elif n in (297, 298):
                disposition, reason = "opaque", member["opaque_reason"]
            elif number == 0 and n <= 22 or 1 <= number <= 8 and n - start < 22 or number == 9:
                disposition, reason = "inferred", None
            else:
                disposition, reason = "deferred_budget", "page_worker_input_byte_budget"
            eligible = disposition in {"inferred", "deferred_budget", "unsupported_target"}
            cov = [{"projection_id": "codebase_ir.contracts@1", "known_atoms": 2, "unknown_atoms": 0},
                   {"projection_id": "codebase_ir.program@1", "known_atoms": 50, "unknown_atoms": 1}]
            entry = {"member_index": n, "entry_cid": member["entry_cid"], "source_key": member["source_key"],
                     "source_digest": digest("digest-" + str(n)) if eligible else None,
                     "target_sha256": digest("target-" + str(n)) if eligible else None, "reason": reason,
                     "disposition": disposition, "coverage": cov if disposition in ("inferred", "deferred_budget") else [],
                     "inference_index": len(rows) if disposition == "inferred" else None}
            if disposition == "inferred":
                rows.append({"source_digest": entry["source_digest"], "latent": [0.125] * 8,
                             "reconstructed_projection_features": {"codebase_ir.contracts@1": [0.25] * 2,
                                                                   "codebase_ir.program@1": [0.5] * 51}})
                atoms.extend(cov)
            entries.append(entry)
        worker = {"elapsed_ms": 1, "executable_sha256": digest("executable"), "worker_sha256": digest("worker"),
                  "input_bytes": 10, "input_sha256": digest("input"), "output_bytes": 10, "output_sha256": digest("output"),
                  "limits": {"max_input_bytes": 33554432, "max_output_bytes": 16777216, "resident_memory_bytes": 1073741824},
                  "memory_enforcement": "sampled_process_tree_rss_with_possible_overshoot", "returncode": 0,
                  "source_execution_attested": False, "workspace_cleaned": True}
        inference = {"schema": "native-projection-feature-inference/v1", "rows": rows, "coverage": atoms,
                     "representation": "native_compiler_structural_features_not_semantic_text_embeddings",
                     "admitted": False, "decoded_formulas_generated": False, "formalized": False, "promotion_performed": False,
                     "qualified": False, "training_executed": False,
                     **{k: model[k] for k in ("contract_sha256", "feature_space_sha256", "state_sha256")}}
        page = {"schema": "codebase-inventory-resume-page@1", "authority": false, "root_cid": root_id,
                "head_cid": root["head_cid"], "membership_cid": root["membership_cid"], "model_artifact_cid": model["artifact_cid"],
                "page_membership_cid": codec.cid(members[start:end]), "previous_page_cid": previous,
                "start": start, "end": end, "total_entries": 300, "entries": entries, "coverage": codec.coverage(entries),
                "inference": inference, "worker_receipt": worker}
        previous = codec.cid_raw(codec.wire(page))
        summary = {"page_cid": previous, "start": start, "end": end, "membership_cid": page["page_membership_cid"],
                   "inferred_rows": len(rows), "dispositions": page["coverage"]["dispositions"]}
        pages.append(page)
        summaries.append(summary)
        transport[f"page-{number + 1:02d}"] = page
    whole = codec.coverage([e for page in pages for e in page["entries"]]) | {"pages": 10}
    done = {"schema": "codebase-inventory-resume-completion@1", "authority": false, "root_cid": root_id,
            "head_cid": root["head_cid"], "membership_cid": root["membership_cid"], "model_artifact_cid": model["artifact_cid"],
            "coverage": whole, "pages": summaries}
    done_id = codec.cid(done)
    reference_root = copy.deepcopy(root)
    reference_root["optimized"] = False
    reference_page = copy.deepcopy(pages[0])
    reference_page["root_cid"] = codec.cid(reference_root)
    transport.update(completion=done, **{"optout-root": reference_root, "optout-reference-page": reference_page})
    ids = [s["page_cid"] for s in summaries]
    packets, audit_chunks, records = [], [], []
    for n in range(1, 5):
        terminal = n == 4
        created = ids[n * 2:n * 2 + 2]
        request = {"schema": "codebase-inventory-resume-cursor@1", "root_cid": root_id,
                   "previous_page_cid": ids[n * 2 - 1], "next_offset": n * 64}
        next_cursor = None if terminal else {"schema": "codebase-inventory-resume-cursor@1", "root_cid": root_id,
                                            "previous_page_cid": created[-1], "next_offset": min(n * 64 + 64, 300)}
        record = {"schema": "inventory-resume-fresh-process-chunk@1", "run_number": n, "root_cid": root_id,
                  "version_id": model["version_id"], "complete": terminal, "max_pages": 2, "pid": 100 + n,
                  "timeout_seconds": 420.0, "recorded_seconds": float(n), "qualified": True,
                  "source_model_owner_preservation": True, "fit_guard_scope": "authored inert labels only",
                  "post_setup_fit_attempt_count": 0, "final_resources": {"active_lease_count": 0, "waiting_request_count": 0},
                  "numerical_before": numeric, "numerical_after": numeric, "pages_created": created,
                  "prefix_tail_cid": created[-1], "request_cursor": request, "next_cursor": next_cursor,
                  "registry_owner_generation_before": n + 2, "registry_owner_generation_after": n + 2}
        if terminal:
            record.update(completion_cid=done_id, coverage=whole)
        stdout = b"logic tree pin authored inert declaration\n" + codec.wire({"qualified": True, "recorded_seconds": float(n)}) + b"\n"
        packets.append({"record": record, "stdout": stdout, "stderr": b""})
        records.append(record)
        audit_row = {k: record[k] for k in ("run_number", "pid", "pages_created", "request_cursor", "next_cursor", "recorded_seconds",
                                          "registry_owner_generation_before", "registry_owner_generation_after")}
        audit_row.update(native_final_resources=record["final_resources"], stdout_sha256=codec.sha(stdout), stderr_sha256=codec.sha(b""))
        audit_chunks.append(audit_row)
    fresh = {"schema": "inventory-resume-fresh-process@2", "chunks": audit_chunks, "owner_processes": 4,
             "process_origin_attested": False, "reported_no_fitting": True, "all_chunk_current_source_model_closures_retained": True,
             "pages_created": ids[2:], "pids": [101, 102, 103, 104]}
    resume = {"schema": "inventory-resume-fresh-process@2", "complete": True, "completion_cid": done_id, "root_cid": root_id,
              "coverage": whole, "qualified": True, "version_id": model["version_id"], "pid": 104, "pids": [101, 102, 103, 104],
              "pages_created": ids[2:], "process_runs": records, "numerical_before": numeric, "numerical_after": numeric,
              "source_model_owner_preservation": True, "fit_guard_scope": "authored inert labels only", "recorded_seconds": 10.0,
              "post_setup_fit_attempt_count": 0, "registry_owner_generation_before": 3, "registry_owner_generation_after": 6,
              "final_resources": {"active_lease_count": 0, "waiting_request_count": 0}}
    transport_rows = []
    for role in codec.ROLES:
        structured = role in ("root", "completion", "optout-root")
        raw = (json.dumps(transport[role], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
               if structured else codec.wire(transport[role]))
        transport_rows.append({"role": role, "cid": codec.cid_raw(raw, structured), "codec": "dag-json" if structured else "raw",
                               "sha256": codec.sha(raw), "bytes": len(raw)})
    observation = {"schema": "inventory-resume-positive-completed-scan-observation@1", "verified": True,
                   "overall_native_qualification": False, "native_worker_qualified": False,
                   "current_deployment_freshness_attested": False, "numerical_execution_independently_reperformed": False,
                   "process_origin_attested": False, "root_cid": root_id, "completion_cid": done_id, "coverage": whole,
                   "head": head, "membership_cid": root["membership_cid"], "model": model, "ordered_pages": summaries,
                   "numerical_state": numeric, "transport_artifacts": transport_rows, "fresh_process_resume": fresh,
                   "reference_page_worker_receipt": reference_page["worker_receipt"]}
    audit = {"schema": "inventory-resume-worker-independent-audit@1", "authority": "none", "qualified": False,
             "native_jobs_executed": 0, "native_owner_databases_opened": 0, "training_steps": 0,
             "positive_completed_scan": observation,
             "scan": {"root_cid": root_id, "completion_cid": done_id, "coverage": whole,
                      "raw_worker_input_output_not_retained": True, "numerical_execution_independently_reperformed": False,
                      "page_receipts": [{"page_cid": s["page_cid"], "inferred_rows": s["inferred_rows"], "worker_receipt": p["worker_receipt"]}
                                        for p, s in zip(pages, summaries, strict=True)]}}
    flags = dict.fromkeys(("384d_qualified", "cuda_qualified", "production_default_activated", "proof_authority",
                          "scan_execution_attested", "source_execution_attested"), False)
    scan = {**flags, "qualified": False, "error": "authored whole-operation failure", "error_type": "StructuredIdentityError",
            "scan_root_cid": root_id, "completed_scan_cid": done_id, "scan_coverage": whole, "fresh_process_resume": resume}
    historical = {"overall_native_qualification": False, "native_worker_qualified": False, "historical_execution_only": True,
                  "root_cid": root_id, "completion_cid": done_id, "membership_cid": root["membership_cid"], "fresh_process_resume": fresh}
    reuse = {"qualified": False, "fresh_native_validation_required": True, "root_cid": root_id, "completion_cid": done_id,
             "head": head, "coverage": whole, "selected_version_id": model["version_id"], "new_fitting_epochs": 0,
             "new_registry_reopens": 0, "new_scan_pages": 0, "inherited_actual_setup_epochs": 2, "unknown_fitting_epochs": False,
             "source_audit": {"sha256": codec.AUDIT_SHA256, "bytes": codec.AUDIT_BYTES}, "source_scan_summary": historical,
             "copied_cas_objects": 14, "copied_cas_bytes": 816613}
    composed = {**flags, "qualified": True, "worker_launched": True, "scan_reuse": reuse, "source_scan_seed": copy.deepcopy(reuse),
                "scan_coverage": whole, "numerical_before": numeric, "numerical_after": numeric}
    # Separate objects allow mutations to reach the intended join rather than an
    # accidental shared-reference rewrite of both expected and actual values.
    return {key: copy.deepcopy(value) for key, value in {"audit": audit, "scan_result": scan, "composed_result": composed,
                                                        "transport": transport, "chunks": packets, "resume": resume}.items()}


def write_fixture(directory):
    """Create all authored inputs and patch only the three historical pin labels."""
    bundle = fixture_bundle()
    packets = {"historical_scan_audit": codec.wire(bundle["audit"]), "historical_scan_result": codec.wire(bundle["scan_result"])}
    audit_sha, audit_bytes = codec.sha(packets["historical_scan_audit"]), len(packets["historical_scan_audit"])
    for name in ("scan_reuse", "source_scan_seed"):
        bundle["composed_result"][name]["source_audit"].update(sha256=audit_sha, bytes=audit_bytes)
    packets["composed_worker_result"] = codec.wire(bundle["composed_result"])
    packets.update(("transport_" + role, codec.wire(bundle["transport"][role])) for role in codec.ROLES)
    for n, row in enumerate(bundle["chunks"], 1):
        packets.update({f"chunk_{n}_record": codec.wire(row["record"]), f"chunk_{n}_stdout": row["stdout"], f"chunk_{n}_stderr": row["stderr"]})
    packets["resume_record"] = codec.wire(bundle["resume"])
    scope = directory / "authored_inputs"
    scope.mkdir()
    pins = {}
    for role, raw in packets.items():
        path = scope / (role + ".body")
        path.write_bytes(raw)
        pins[role] = {"path": str(path), "sha256": codec.sha(raw), "size_bytes": len(raw)}
    manifest = {"schema": codec.INPUT_SCHEMA, "fixture_origin": codec.ORIGIN,
                **{key: pins[key] for key in ("historical_scan_audit", "historical_scan_result", "composed_worker_result", "resume_record")},
                "transport_artifacts": [{"role": role, "input": pins["transport_" + role]} for role in codec.ROLES],
                "chunks": [{"run_number": n, **{role: pins[f"chunk_{n}_{role}"] for role in ("record", "stdout", "stderr")}} for n in range(1, 5)]}
    path = scope / "manifest.json"
    path.write_bytes(codec.wire(manifest))
    patches = {"AUDIT_SHA256": audit_sha, "AUDIT_BYTES": audit_bytes, "SCAN_SHA256": codec.sha(packets["historical_scan_result"]),
               "COMPOSED_SHA256": codec.sha(packets["composed_worker_result"])}
    return path, patches


class ResumedInventoryTests(unittest.TestCase):
    def setUp(self):
        self.bundle = fixture_bundle()

    def test_independent_golden_dispositions_and_whole_outcomes(self):
        report = codec.reconcile(self.bundle)
        self.assertEqual((report["inventory_member_count"], report["page_count"], report["historical_resumption_count"]), (300, 10, 4))
        self.assertEqual(report["coverage"]["dispositions"], {"inferred": 205, "deferred_budget": 89, "opaque": 2,
                                                           "parse_failed": 1, "unindexed": 1, "unsupported_target": 2})
        self.assertEqual([row["received_member_count"] for row in report["frontiers"]], [0, 32, 64, 128, 192, 256, 300])
        self.assertEqual([row["complete"] for row in report["frontiers"]], [False] * 6 + [True])
        self.assertIs(report["historical_scan_overall_qualified"], False)
        self.assertIs(report["composed_worker_overall_qualified"], True)
        self.assertTrue(all(row["runtime_behavior"] == "unknown" for row in report["source_members"]))
        self.assertEqual(report["numerical_worker_request_custody"], "raw_input_output_unavailable")

    def test_empty_prefix_is_unknown(self):
        view = codec.frontier(self.bundle["transport"]["root"], [])
        self.assertEqual((view["received_member_count"], view["unreceived_member_count"]), (0, 300))
        self.assertIs(view["absence_established"], False)
        self.assertIs(view["complete"], False)

    def test_all_pages_without_completion_still_incomplete(self):
        view = codec.frontier(self.bundle["transport"]["root"], [self.bundle["transport"][f"page-{n:02d}"] for n in range(1, 11)])
        self.assertEqual(view["received_member_count"], 300)
        self.assertIs(view["complete"], False)

    def test_premature_completion_refused(self):
        with self.assertRaisesRegex(codec.Refusal, "entire chain"):
            codec.frontier(self.bundle["transport"]["root"], [self.bundle["transport"]["page-01"]], self.bundle["transport"]["completion"])

    def test_correlated_controls_refuse(self):
        controls = codec.corruption_controls(self.bundle)
        self.assertEqual(len(controls), 26)
        self.assertEqual(len({row["name"] for row in controls}), 26)
        self.assertTrue(all(row["refused"] is True for row in controls))
        self.assertIn("rehashed_numerical_page_against_fixed_audit", {row["name"] for row in controls})

    def test_duplicate_json_refused(self):
        with self.assertRaisesRegex(codec.Refusal, "duplicate"):
            codec.document(b'{"n":0,"n":1}')

    def test_nonfinite_and_surrogate_refused(self):
        for raw in (b'{"n":NaN}', b'{"n":1e999}', b'{"n":"\\ud800"}'):
            with self.subTest(raw=raw), self.assertRaises(codec.Refusal):
                codec.document(raw)

    def test_bool_int_alias_is_distinct(self):
        self.assertFalse(codec.equal({"n": False}, {"n": 0}))
        with self.assertRaises(codec.Refusal):
            codec.integer(False, 0, 0, "position")

    def test_declared_json_byte_budget(self):
        with self.assertRaisesRegex(codec.Refusal, "byte budget"):
            codec.document(b'{"n":0}', limit=6)

    def test_unknown_protocol_field_refused(self):
        self.bundle["transport"]["page-01"]["runtime_fact"] = True
        with self.assertRaisesRegex(codec.Refusal, "fields"):
            codec.reconcile(self.bundle)

    def test_projection_bool_value_refused(self):
        self.bundle["transport"]["page-01"]["inference"]["rows"][0]["latent"][0] = False
        with self.assertRaisesRegex(codec.Refusal, "numerical vector"):
            codec.reconcile(self.bundle)

    def test_deferred_structural_coverage_is_not_inference(self):
        page = self.bundle["transport"]["page-01"]
        row = next(e for e in page["entries"] if e["disposition"] == "deferred_budget")
        self.assertEqual(len(row["coverage"]), 2)
        self.assertIsNone(row["inference_index"])
        codec.reconcile(self.bundle)

    def test_stdout_custody_refused(self):
        self.bundle["chunks"][0]["stdout"] += b"unreported log line\n"
        with self.assertRaisesRegex(codec.Refusal, "stdout/stderr commitment"):
            codec.reconcile(self.bundle)

    def test_chunk_request_bool_offset_refused(self):
        self.bundle["chunks"][0]["record"]["request_cursor"]["next_offset"] = True
        with self.assertRaisesRegex(codec.Refusal, "exact integer"):
            codec.reconcile(self.bundle)

    def test_invented_completion_on_partial_chunk_refused(self):
        self.bundle["chunks"][0]["record"]["completion_cid"] = self.bundle["transport"]["completion"]["root_cid"]
        with self.assertRaisesRegex(codec.Refusal, "fields"):
            codec.reconcile(self.bundle)

    def test_missing_terminal_member_refused(self):
        self.bundle["transport"]["page-10"]["entries"].pop()
        with self.assertRaisesRegex(codec.Refusal, "one disposition"):
            codec.reconcile(self.bundle)

    def test_reuse_bool_new_page_count_refused(self):
        self.bundle["composed_result"]["scan_reuse"]["new_scan_pages"] = False
        with self.assertRaisesRegex(codec.Refusal, "exact integer"):
            codec.reconcile(self.bundle)

    def test_stable_regular_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet"
            path.write_bytes(b"packet")
            self.assertEqual(codec.Capture.read(path, 6), b"packet")

    def test_descriptor_budget_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet"
            path.write_bytes(b"packet")
            with patch.object(codec.os, "read", side_effect=AssertionError("allocation started")):
                with self.assertRaisesRegex(codec.Refusal, "preallocation"):
                    codec.Capture.read(path, 5)

    def test_growth_during_read_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet"
            path.write_bytes(b"ab")
            actual_read = os.read
            calls = []

            def growing_read(fd, limit):
                calls.append(limit)
                if len(calls) == 1:
                    path.write_bytes(b"abcdef")
                return actual_read(fd, limit)

            with patch.object(codec.os, "read", side_effect=growing_read):
                with self.assertRaisesRegex(codec.Refusal, "changed"):
                    codec.Capture.read(path, 2)
            self.assertEqual(calls, [3])

    def test_aggregate_allowance_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet"
            path.write_bytes(b"abcdef")
            capture = codec.Capture()
            capture.total = codec.MAX_TOTAL - 3
            with self.assertRaisesRegex(codec.Refusal, "preallocation"):
                capture.take(path, {"sha256": codec.sha(b"abcdef"), "size_bytes": 6})

    def test_input_symlink_and_fifo_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "target"
            target.write_bytes(b"x")
            alias = Path(temp) / "alias"
            alias.symlink_to(target)
            fifo = Path(temp) / "fifo"
            os.mkfifo(fifo)
            for path in (alias, fifo):
                with self.subTest(path=path), self.assertRaises(codec.Refusal):
                    codec.Capture.read(path, 10)

    def test_final_original_replacement_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet"
            path.write_bytes(b"abcdef")
            capture = codec.Capture()
            capture.take(path)
            path.write_bytes(b"abcdeg")
            with self.assertRaisesRegex(codec.Refusal, "final original"):
                capture.stable()

    def test_full_authored_closure_and_typed_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, patches = write_fixture(root)
            with patch.multiple(codec, **patches):
                report = codec.run(manifest, root / "output")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["input_files"]), 30)
            self.assertEqual(report["control_count"], 26)
            for name in codec.TRUE_FLAGS:
                self.assertIs(report[name], True)
            for name in codec.FALSE_FLAGS:
                self.assertIs(report[name], False)
            for name in codec.ZERO_FIELDS:
                self.assertEqual(type(report[name]), int)
                self.assertEqual(report[name], 0)

    def _late_run(self, change, message):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, patches = write_fixture(root)
            actual_stable, calls = codec.Capture.stable, []

            def late(capture):
                actual_stable(capture)
                calls.append(1)
                if len(calls) == 2:
                    change(root, manifest)

            with patch.multiple(codec, **patches), patch.object(codec.Capture, "stable", late):
                with self.assertRaisesRegex(codec.Refusal, message):
                    codec.run(manifest, root / "output")
            self.assertEqual(len(calls), 2, "control reached the final reread before population")

    def test_late_extra_output_refused(self):
        self._late_run(lambda root, _: (root / "output" / "extra").write_bytes(b"x"), "population")

    def test_late_nested_copy_byte_drift_refused(self):
        def change(root, _):
            path = root / "output" / "inputs" / "chunk_1_stdout.body"
            raw = path.read_bytes()
            path.write_bytes(b"X" + raw[1:])
        self._late_run(change, "late retained/report byte drift")

    def test_late_report_byte_drift_refused(self):
        def change(root, _):
            path = root / "output" / "resumed_inventory_controls.json"
            raw = path.read_bytes()
            path.write_bytes(b"X" + raw[1:])
        self._late_run(change, "late retained/report byte drift")

    def test_late_original_byte_drift_refused(self):
        def change(root, _):
            path = root / "authored_inputs" / "chunk_1_stdout.body"
            raw = path.read_bytes()
            path.write_bytes(b"X" + raw[1:])
        self._late_run(change, "late original byte drift")

    def test_late_output_root_alias_refused(self):
        def change(root, _):
            (root / "output").rename(root / "saved")
            (root / "output").symlink_to(root / "saved", target_is_directory=True)
        self._late_run(change, "canonical absolute path")

    def test_late_nested_copy_symlink_refused(self):
        def change(root, _):
            path = root / "output" / "inputs" / "chunk_1_stdout.body"
            path.unlink()
            path.symlink_to(root / "authored_inputs" / "chunk_1_stdout.body")
        self._late_run(change, "symlink")

    def test_original_drift_during_receiving_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, patches = write_fixture(root)
            actual = codec.reconcile

            def changed(bundle):
                result = actual(bundle)
                packet = root / "authored_inputs" / "chunk_1_stdout.body"
                raw = packet.read_bytes()
                packet.write_bytes(b"X" + raw[1:])
                return result

            with patch.multiple(codec, **patches), patch.object(codec, "reconcile", side_effect=changed):
                with self.assertRaisesRegex(codec.Refusal, "final original"):
                    codec.run(manifest, root / "output")

    def test_output_scope_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, patches = write_fixture(root)
            with patch.multiple(codec, **patches), self.assertRaisesRegex(codec.Refusal, "outside input"):
                codec.run(manifest, manifest.parent / "output")

    def test_fixed_audit_anchor_survives_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, patches = write_fixture(root)
            value = codec.document(manifest.read_bytes())
            pin = value["historical_scan_audit"]
            packet = Path(pin["path"])
            audit = codec.document(packet.read_bytes())
            audit["qualified"] = True
            raw = codec.wire(audit)
            packet.write_bytes(raw)
            pin.update(sha256=codec.sha(raw), size_bytes=len(raw))
            manifest.write_bytes(codec.wire(value))
            with patch.multiple(codec, **patches), self.assertRaisesRegex(codec.Refusal, "independent historical raw anchor"):
                codec.run(manifest, root / "output")


if __name__ == "__main__":
    unittest.main()
