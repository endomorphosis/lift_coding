"""Finite adapter contracts; authored responses never invoke a model provider."""
from __future__ import annotations

import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_llm as adapter

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6nS8AAAAASUVORK5CYII=")


class Metadata:
    def __init__(self):
        self.value = {}

    def set_last_cli_observation(self, _provider, value):
        self.value = dict(value)

    def get_last_cli_observation(self, _provider):
        return dict(self.value)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.profile = self.root / "profile.json"
        self.board = self.root / "board.todo.md"
        self.source = self.root / "app.js"
        self.source.write_text("export const label = 'before';\n")
        self.board.write_text("## SVF-001 Review app\n- Status: pending\n- Predicted files: app.js, new.js\n")
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"provider": "grok_cli", "model": "grok-4.7"}}))
        self.image = self.root / "screen.png"
        self.image.write_bytes(PNG)
        self.router_source = self.root / "router.py"
        self.router_source.write_text("# authored finite transport fixture\n")
        self.metadata = Metadata()
        self.calls = []
        self.trace = {"effective_provider_name": "grok_cli", "effective_model_name": "grok-4.7"}
        self.native = {"exit_code": 0, "native_grok_reason_code": "end_turn", "native_grok_error_observed": False,
                       "native_grok_progress": {"response_usable": True, "tool_name_counts": {"read_file": 1, "run_terminal_cmd": 0, "unknown": 0}}}
        self.response = {"schema": adapter.RESPONSE_SCHEMA, "task_id": "SVF-001", "mode": "review", "decision": "pass",
                         "summary": "Authored adapter response, no live model call.", "inspected_screenshots": ["screen.png"], "findings": [], "edits": []}
        self.hook = lambda: None
        self.text = None

        def generate(prompt, **kwargs):
            self.calls.append((prompt, kwargs))
            self.metadata.value = dict(self.native)
            self.hook()
            return self.text if self.text is not None else json.dumps(self.response)

        self.router = SimpleNamespace(__file__=str(self.router_source), find_grok_cli=lambda: "/fixture/grok",
            _grok_cli_auth_available=lambda: True, generate_text=generate, get_last_generation_trace=lambda: dict(self.trace))
        self.backend = patch.object(adapter, "_load_backend", return_value=(self.router, self.metadata))
        self.backend.start()
        self.addCleanup(self.backend.stop)

    def invoke(self, mode="review", **kwargs):
        defaults = {"input_paths": ["app.js"], "screenshot_paths": ["screen.png"], "root": self.root}
        defaults.update(kwargs)
        return adapter.invoke_task_model("profile.json", "SVF-001", mode, **defaults)

    def edit(self, old="before", new="after", path="app.js"):
        return {"path": path, "before_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(), "old": old, "new": new}

    def test_exact_route_and_actual_native_metadata_are_retained(self):
        result = self.invoke(output_path="receipts/review.json")
        self.assertTrue(result["success"])
        self.assertFalse(result["completion_authority"])
        self.assertFalse(result["work_complete"])
        self.assertFalse(result["edits_applied"])
        self.assertFalse(result["vision_observation"]["pixel_delivery_verified"])
        self.assertEqual(result["vision_observation"]["native_read_file_calls"], 1)
        kwargs = self.calls[0][1]
        for key in ("allow_local_fallback", "allow_cross_provider_fallback"):
            self.assertIs(kwargs[key], False)
        self.assertIs(kwargs["disable_model_retry"], True)
        self.assertIs(kwargs["side_effecting"], True)
        self.assertEqual((kwargs["provider"], kwargs["model_name"], kwargs["temperature"]), ("grok_cli", "grok-4.7", 0))
        self.assertEqual(kwargs["grok_tools"], "read_file")
        self.assertIn("use_tool", kwargs["grok_disallowed_tools"])
        self.assertTrue(kwargs["grok_stream_progress"])
        self.assertEqual(kwargs["grok_cli_cmd"], ["/fixture/grok", "--cwd", str(self.root)])
        self.assertEqual(str(uuid.UUID(kwargs["allocation_session_id"])), result["invocation_id"])
        self.assertEqual(json.loads((self.root / "receipts/review.json").read_text()), result)
        self.assertIn("before", self.source.read_text())

    def test_repair_is_only_a_proposal_until_explicit_application(self):
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit()])
        result = self.invoke("repair", predicted_files=["app.js"])
        self.assertIn("before", self.source.read_text())
        receipt = adapter.apply_validated_edits(self.root, result["response"]["edits"], ["app.js"])
        self.assertIn("after", self.source.read_text())
        self.assertTrue(receipt["validation_required"])
        self.assertFalse(receipt["completion_authority"])
        self.assertFalse(list(self.root.glob(".svf-edit-*")))

    def test_wrong_profile_model_fails_before_provider_call(self):
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"model": "grok-4.7-build-fast"}}))
        with self.assertRaisesRegex(adapter.ModelAdapterError, "requires grok_cli"):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_nonzero_config_temperature_is_not_used(self):
        # The adapter never copies an unconstrained temperature into dispatch.
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"temperature": 0.9}}))
        self.invoke()
        self.assertEqual(self.calls[0][1]["temperature"], 0)

    def test_missing_screenshot_is_not_replaced_with_a_placeholder(self):
        self.image.unlink()
        with self.assertRaises(adapter.ModelAdapterError):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_invalid_png_and_missing_visual_input_fail_before_dispatch(self):
        self.image.write_text("not a PNG")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "PNG"):
            self.invoke()
        with self.assertRaisesRegex(adapter.ModelAdapterError, "requires captured"):
            self.invoke(screenshot_paths=[])
        self.assertEqual(self.calls, [])

    def test_unlisted_caller_write_scope_is_rejected(self):
        with self.assertRaisesRegex(adapter.ModelAdapterError, "allowlist exceeds"):
            self.invoke("repair", predicted_files=["board.todo.md"])
        self.assertEqual(self.calls, [])

    def test_effective_fallback_is_rejected_and_failure_receipt_retained(self):
        self.trace["effective_model_name"] = "grok-4.6"
        with self.assertRaisesRegex(adapter.ModelAdapterError, "pinned route"):
            self.invoke(output_path="failed.json")
        receipt = json.loads((self.root / "failed.json").read_text())
        self.assertFalse(receipt["success"])
        self.assertFalse(receipt["completion_authority"])
        self.assertEqual(receipt["effective_route"]["effective_model_name"], "grok-4.6")

    def test_stale_native_observation_cannot_validate_cached_text(self):
        self.metadata.value = dict(self.native)
        self.native = {}
        with self.assertRaisesRegex(adapter.ModelAdapterError, "native Grok completion"):
            self.invoke()

    def test_native_read_count_and_tool_scope_are_enforced(self):
        self.native["native_grok_progress"]["tool_name_counts"]["read_file"] = 0
        with self.assertRaisesRegex(adapter.ModelAdapterError, "image-read activity"):
            self.invoke()
        self.native["native_grok_progress"]["tool_name_counts"]["read_file"] = 1
        self.native["native_grok_progress"]["tool_name_counts"]["run_terminal_cmd"] = 1
        with self.assertRaisesRegex(adapter.ModelAdapterError, "outside the read-only"):
            self.invoke()

    def test_timeout_keeps_native_failure_without_exporting_provider_error(self):
        def fail(_prompt, **_kwargs):
            self.metadata.value = {"timed_out": True, "native_grok_reason_code": "timeout"}
            raise subprocess.TimeoutExpired("private command", 10, stderr="private marker")
        self.router.generate_text = fail
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(output_path="timeout.json")
        raw = (self.root / "timeout.json").read_text()
        receipt = json.loads(raw)
        self.assertTrue(receipt["native_observation"]["timed_out"])
        self.assertFalse(receipt["success"])
        self.assertNotIn("private", raw)

    def test_input_source_and_screenshot_drift_are_rejected(self):
        self.hook = lambda: self.source.write_text("changed during generation")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "changed during invocation"):
            self.invoke()
        self.hook = lambda: self.image.write_bytes(PNG + b"drift")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "screenshot changed"):
            self.invoke()

    def test_router_source_drift_is_rejected(self):
        self.hook = lambda: self.router_source.write_text("changed router")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "router source changed"):
            self.invoke()

    def test_model_must_identify_exact_screenshot_and_task(self):
        self.response["inspected_screenshots"] = ["other.png"]
        with self.assertRaisesRegex(adapter.ModelAdapterError, "every requested screenshot"):
            self.invoke()
        self.response["inspected_screenshots"] = ["screen.png"]
        self.response["task_id"] = "SVF-999"
        with self.assertRaisesRegex(adapter.ModelAdapterError, "identity differs"):
            self.invoke()

    def test_malformed_duplicate_and_nonfinite_json_fail_closed(self):
        for text in ["```json\n{}\n```", '{"schema":1,"schema":2}', '{"value":NaN}']:
            self.text = text
            with self.subTest(text=text), self.assertRaises(adapter.ModelAdapterError):
                self.invoke()

    def test_review_may_not_smuggle_edits_or_completion_authority(self):
        self.response["edits"] = [self.edit()]
        with self.assertRaisesRegex(adapter.ModelAdapterError, "only repair mode"):
            self.invoke()
        self.response["edits"] = []
        self.response["completion_authority"] = True
        with self.assertRaisesRegex(adapter.ModelAdapterError, "response fields"):
            self.invoke()

    def test_out_of_scope_stale_and_ambiguous_edits_are_rejected(self):
        with self.assertRaisesRegex(adapter.ModelAdapterError, "outside declared"):
            adapter.validate_edit_proposals(self.root, [self.edit(path="board.todo.md")], ["app.js"])
        edit = self.edit()
        self.source.write_text("before before")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "before_sha256"):
            adapter.validate_edit_proposals(self.root, [edit], ["app.js"])
        with self.assertRaisesRegex(adapter.ModelAdapterError, "exactly once"):
            adapter.validate_edit_proposals(self.root, [self.edit()], ["app.js"])

    def test_edit_application_refuses_drift_after_proposal_validation(self):
        original = adapter.validate_edit_proposals
        def changing(*args, **kwargs):
            result = original(*args, **kwargs)
            self.source.write_text("independent new source")
            return result
        with patch.object(adapter, "validate_edit_proposals", side_effect=changing):
            with self.assertRaisesRegex(adapter.ModelAdapterError, "changed before edit application"):
                adapter.apply_validated_edits(self.root, [self.edit()], ["app.js"])
        self.assertEqual(self.source.read_text(), "independent new source")

    def test_new_file_proposal_requires_null_hash_and_empty_old_text(self):
        edit = {"path": "new.js", "before_sha256": None, "old": "", "new": "export const created = true;\n"}
        adapter.apply_validated_edits(self.root, [edit], ["new.js"])
        self.assertEqual((self.root / "new.js").read_text(), edit["new"])

    def test_traversal_symlink_and_credentials_are_refused(self):
        for path in ["../outside", ".git/config", ".env", "nested/auth.json"]:
            with self.subTest(path=path), self.assertRaises(adapter.ModelAdapterError):
                adapter.validate_edit_proposals(self.root, [self.edit(path=path)], [path])
        (self.root / "link.js").symlink_to(self.source)
        with self.assertRaisesRegex(adapter.ModelAdapterError, "symbolic links"):
            adapter.validate_edit_proposals(self.root, [self.edit(path="link.js")], ["link.js"])

    def test_output_may_not_overwrite_input_or_escape_root(self):
        for path in ["app.js", "profile.json", "screen.png", "../outside.json"]:
            with self.subTest(path=path), self.assertRaises(adapter.ModelAdapterError):
                self.invoke(output_path=path)
        self.assertEqual(self.calls, [])

    def test_retained_model_receipt_rechecks_native_route_and_response_hash(self):
        receipt = self.invoke()
        llm_validated = adapter.validate_model_receipt(self.root, receipt, task_id="SVF-001", mode="review", require_visual=True)
        self.assertEqual(llm_validated, receipt)
        receipt["response"]["summary"] = "changed after generation"
        with self.assertRaisesRegex(adapter.ModelAdapterError, "retained hash"):
            adapter.validate_model_receipt(self.root, receipt, task_id="SVF-001", require_visual=True)

    def test_retained_model_receipt_rejects_native_failure_and_wrong_effective_provider(self):
        receipt = self.invoke()
        receipt["native_observation"]["exit_code"] = 1
        with self.assertRaisesRegex(adapter.ModelAdapterError, "completed native"):
            adapter.validate_model_receipt(self.root, receipt, task_id="SVF-001")
        receipt["native_observation"]["exit_code"] = 0
        receipt["effective_route"]["effective_provider_name"] = "xai"
        with self.assertRaisesRegex(adapter.ModelAdapterError, "effective route"):
            adapter.validate_model_receipt(self.root, receipt, task_id="SVF-001")

    def test_probe_uses_tiny_route_only_prompt_no_read_tools_and_uuid(self):
        self.source.write_text("HUGE_PLAN_CONTEXT_MUST_NOT_BE_SENT " * 1000)
        self.response.update(mode="probe", inspected_screenshots=[])
        self.native["native_grok_progress"]["tool_name_counts"]["read_file"] = 0
        result = self.invoke("probe", screenshot_paths=[])
        prompt, kwargs = self.calls[0]
        self.assertLess(len(prompt), 1500)
        self.assertNotIn("HUGE_PLAN_CONTEXT", prompt)
        self.assertNotIn("Predicted files", prompt)
        self.assertEqual(kwargs["grok_max_turns"], 1)
        self.assertEqual(kwargs["max_new_tokens"], 4096)
        self.assertIn("read_file", kwargs["grok_disallowed_tools"].split(","))
        self.assertEqual(result["prompt_scope"], "route_probe_only")

    def test_review_has_explicit_prompt_turn_and_output_budgets(self):
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"maxTurns": 24, "maxOutputTokens": 16384}}))
        self.invoke()
        prompt, kwargs = self.calls[0]
        self.assertEqual(kwargs["grok_max_turns"], 8)
        self.assertEqual(kwargs["max_new_tokens"], 12288)
        self.assertIn("do not read any other files", prompt)
        self.assertNotIn("Predicted files", prompt)
        self.source.write_text("x" * 40000)
        with self.assertRaisesRegex(adapter.ModelAdapterError, "prompt exceeds"):
            self.invoke()
        self.assertEqual(len(self.calls), 1)

    def test_image_frame_budget_is_explicit_derived_and_bounded(self):
        images = [{"size_bytes": size} for size in [118665, 155866, 85895, 100663]]
        self.assertEqual(adapter.image_stream_frame_budget(images), 1048576)
        self.assertEqual(adapter.image_stream_frame_budget([]), 262144)
        with self.assertRaisesRegex(adapter.ModelAdapterError, "streaming frame budget"):
            adapter.image_stream_frame_budget([{"size_bytes": 16 * 1024 * 1024}])
        result = self.invoke()
        self.assertEqual(self.calls[0][1]["grok_stream_max_frame_bytes"], result["stream_max_frame_bytes"])

    def test_live_atomic_progress_is_body_free_and_final_state_is_recorded(self):
        original = self.router.generate_text
        observed = []
        def generate(prompt, **kwargs):
            kwargs["grok_progress_callback"]({"frames": 7, "stdout_bytes": 1024, "duration_seconds": 2.5,
                "tool_name_counts": {"read_file": 1, "private-field": 999}, "stream_tainted": False,
                "rawOutput": "PRIVATE_PROVIDER_BODY", "text": "PRIVATE_PROVIDER_BODY", "last_event_seconds": 2.4})
            progress = json.loads((self.root / "receipts/review.progress.json").read_text())
            observed.append(progress)
            self.assertEqual(progress["state"], "running")
            self.assertEqual(progress["stream"]["frames"], 7)
            self.assertNotIn("PRIVATE_PROVIDER_BODY", json.dumps(progress))
            self.assertNotIn("private-field", json.dumps(progress))
            return original(prompt, **kwargs)
        self.router.generate_text = generate
        receipt = self.invoke(output_path="receipts/review.json")
        self.assertEqual(len(observed), 1)
        final = json.loads((self.root / receipt["progress_path"]).read_text())
        self.assertEqual(final["state"], "succeeded")
        self.assertFalse(final["completion_authority"])
        self.assertGreater(final["deadline_at_ms"], final["started_at_ms"])
        self.assertEqual(json.loads((self.root / receipt["attempt_receipt_path"]).read_text()), receipt)

    def test_retry_preserves_previous_failure_and_its_progress(self):
        output = "receipts/review.json"
        original = self.router.generate_text
        def fail(_prompt, **kwargs):
            progress = {"frames": 9, "oversized_frames": 2, "stream_tainted": True, "last_event_seconds": 299,
                        "tool_name_counts": {"read_file": 14}}
            kwargs["grok_progress_callback"](progress)
            self.metadata.value = {"timed_out": True, "native_grok_reason_code": "timeout", "native_grok_progress": progress}
            raise subprocess.TimeoutExpired("fixture", 300)
        self.router.generate_text = fail
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(output_path=output)
        failed_raw = (self.root / output).read_bytes()
        failed = json.loads(failed_raw)
        self.assertIn("stream_frame_budget_exceeded", failed["failure_diagnostics"]["codes"])
        self.assertIn("provider_timeout_with_activity", failed["failure_diagnostics"]["codes"])
        failed_archive = self.root / failed["attempt_receipt_path"]
        self.assertEqual(failed_archive.read_bytes(), failed_raw)
        self.assertEqual(json.loads((self.root / failed["progress_path"]).read_text())["state"], "failed")
        self.router.generate_text = original
        succeeded = self.invoke(output_path=output)
        self.assertTrue(succeeded["success"])
        self.assertNotEqual(failed["attempt_receipt_path"], succeeded["attempt_receipt_path"])
        self.assertEqual(failed_archive.read_bytes(), failed_raw)
        legacy = self.root / "receipts/model-invocations" / ("review-previous-" + hashlib.sha256(failed_raw).hexdigest() + ".json")
        self.assertEqual(legacy.read_bytes(), failed_raw)

    def nested_edit(self, path="scripts/svf_backends/driver.py"):
        return {"path": path, "before_sha256": None, "old": "", "new": "print('real source')\n"}

    def test_nested_new_file_snapshot_and_model_proposal_do_not_create_parents(self):
        edit = self.nested_edit()
        self.board.write_text(self.board.read_text().replace("app.js, new.js", "app.js, " + edit["path"]))
        self.response.update(mode="repair", decision="needs_changes", edits=[edit])
        receipt = self.invoke("repair", predicted_files=[edit["path"]])
        self.assertIsNone(next(item for item in receipt["input_files"] if item["path"] == edit["path"])["sha256"])
        self.assertFalse((self.root / "scripts").exists())
        self.assertEqual(receipt["response"]["edits"], [edit])

    def test_nested_new_file_application_requires_and_rechecks_a_lease(self):
        edit = self.nested_edit()
        with self.assertRaisesRegex(adapter.ModelAdapterError, "requires a lease check"):
            adapter.apply_validated_edits(self.root, [edit], [edit["path"]])
        self.assertFalse((self.root / "scripts").exists())
        checked = []
        result = adapter.apply_validated_edits(self.root, [edit], [edit["path"]], lease_check=lambda: checked.append(True))
        self.assertEqual((self.root / edit["path"]).read_text(), edit["new"])
        self.assertEqual(result["created_directories"], ["scripts", "scripts/svf_backends"])
        self.assertGreaterEqual(len(checked), 5)
        self.assertFalse(result["completion_authority"])
        self.assertEqual(list(self.root.rglob(".svf-edit-*")), [])
        self.assertEqual(list(self.root.rglob(".svf-dir-*")), [])

    def test_file_or_symlink_ancestor_is_refused_without_parent_creation(self):
        (self.root / "blocked").write_text("foreign file")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "ancestor"):
            adapter.validate_edit_proposals(self.root, [self.nested_edit("blocked/sub/driver.py")], ["blocked/sub/driver.py"])
        (self.root / "linked").symlink_to(self.root)
        with self.assertRaisesRegex(adapter.ModelAdapterError, "symbolic"):
            adapter.validate_edit_proposals(self.root, [self.nested_edit("linked/sub/driver.py")], ["linked/sub/driver.py"])
        self.assertEqual((self.root / "blocked").read_text(), "foreign file")

    def test_concurrent_parent_arrival_is_not_replaced_or_rolled_back(self):
        edit = self.nested_edit("backend/driver.py")
        original = adapter._publish_new_directory
        def arrive(parent, temporary, name):
            os.mkdir(name, dir_fd=parent.fd)
            (parent.path / name / "foreign.txt").write_text("preserve")
            original(parent, temporary, name)
        with patch.object(adapter, "_publish_new_directory", side_effect=arrive):
            with self.assertRaisesRegex(adapter.ModelAdapterError, "appeared concurrently"):
                adapter.apply_validated_edits(self.root, [edit], [edit["path"]], lease_check=lambda: None)
        self.assertEqual((self.root / "backend/foreign.txt").read_text(), "preserve")
        self.assertFalse((self.root / edit["path"]).exists())
        self.assertEqual(list(self.root.glob(".svf-dir-*")), [])

    def test_lease_revocation_rolls_back_only_created_empty_directories(self):
        edit = self.nested_edit()
        def lease():
            if (self.root / "scripts/svf_backends").exists():
                raise RuntimeError("lease revoked")
        with self.assertRaisesRegex(RuntimeError, "lease revoked"):
            adapter.apply_validated_edits(self.root, [edit], [edit["path"]], lease_check=lease)
        self.assertFalse((self.root / "scripts").exists())
        self.assertEqual(list(self.root.glob(".svf-dir-*")), [])

    def test_concurrent_new_file_arrival_is_preserved_atomically(self):
        edit = self.nested_edit()
        original = os.link
        def arrive(source, destination, **kwargs):
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=kwargs["dst_dir_fd"])
            with os.fdopen(descriptor, "w") as handle:
                handle.write("foreign concurrent bytes")
            return original(source, destination, **kwargs)
        with patch.object(adapter.os, "link", side_effect=arrive):
            with self.assertRaises(FileExistsError):
                adapter.apply_validated_edits(self.root, [edit], [edit["path"]], lease_check=lambda: None)
        self.assertEqual((self.root / edit["path"]).read_text(), "foreign concurrent bytes")
        self.assertEqual(list(self.root.rglob(".svf-edit-*")), [])

    def test_replaced_parent_symlink_cannot_redirect_apply_outside_root(self):
        edit = self.nested_edit()
        with tempfile.TemporaryDirectory() as outside:
            moved = self.root / "moved-parent"
            def lease():
                if (self.root / "scripts/svf_backends").exists() and not moved.exists():
                    (self.root / "scripts").rename(moved)
                    (self.root / "scripts").symlink_to(outside)
            with self.assertRaisesRegex(adapter.ModelAdapterError, "directory changed"):
                adapter.apply_validated_edits(self.root, [edit], [edit["path"]], lease_check=lease)
            self.assertEqual(list(Path(outside).iterdir()), [])
            self.assertTrue((self.root / "scripts").is_symlink())

    def test_batch_failure_restores_prior_owned_file_and_removes_empty_new_dirs(self):
        before = self.source.read_bytes()
        nested = self.nested_edit()
        with patch.object(adapter.os, "link", side_effect=OSError(errno.ENOSPC, "authored full disk")):
            with self.assertRaises(OSError):
                adapter.apply_validated_edits(self.root, [self.edit(), nested], ["app.js", nested["path"]], lease_check=lambda: None)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse((self.root / "scripts").exists())
        self.assertEqual(list(self.root.rglob(".svf-edit-*")), [])

    def test_rollback_preserves_foreign_updates_inside_a_created_directory(self):
        first = self.nested_edit("backend/first.py")
        second = self.nested_edit("backend/second.py")
        original = os.link
        def fail_second(source, destination, **kwargs):
            if destination == "second.py":
                (self.root / first["path"]).write_text("foreign edit after first commit")
                raise OSError(errno.ENOSPC, "authored full disk")
            return original(source, destination, **kwargs)
        with patch.object(adapter.os, "link", side_effect=fail_second):
            with self.assertRaises(OSError):
                adapter.apply_validated_edits(self.root, [first, second], [first["path"], second["path"]], lease_check=lambda: None)
        self.assertEqual((self.root / first["path"]).read_text(), "foreign edit after first commit")
        self.assertFalse((self.root / second["path"]).exists())
        self.assertEqual(list(self.root.rglob(".svf-edit-*")), [])

    def test_task_limits_are_exact_under_profile_caps_without_route_changes(self):
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"maxTurns": 24, "maxOutputTokens": 16384, "modelContextBytes": 65536}}))
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit()])
        limits = {"maxTurns": 8, "maxOutputTokens": 12288, "modelContextBytes": 49152}
        receipt = self.invoke("repair", predicted_files=["app.js"], task_limits=limits)
        kwargs = self.calls[0][1]
        self.assertEqual(kwargs["grok_max_turns"], 8)
        self.assertEqual(kwargs["max_new_tokens"], 12288)
        self.assertEqual(receipt["model_context_bytes"], 49152)
        self.assertEqual((kwargs["provider"], kwargs["model_name"]), ("grok_cli", "grok-4.7"))
        capped = adapter.model_call_limits({"llm": {"maxTurns": 4, "maxOutputTokens": 4096, "modelContextBytes": 32768}}, "repair", limits)
        self.assertEqual((capped["maxTurns"], capped["maxOutputTokens"], capped["modelContextBytes"]), (4, 4096, 32768))

    def test_invalid_task_limits_fail_before_any_provider_invocation(self):
        for limits in [{"maxTurns": True}, {"maxOutputTokens": "8192"}, {"modelContextBytes": 0}, {"model": "another-model"}]:
            with self.subTest(limits=limits), self.assertRaises(adapter.ModelAdapterError):
                self.invoke(task_limits=limits)
        self.assertEqual(self.calls, [])

    def test_reasoning_effort_is_forwarded_only_when_explicit(self):
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit()])
        for effort in ("low", "medium", "high"):
            with self.subTest(effort=effort):
                receipt = self.invoke("repair", predicted_files=["app.js"],
                    task_limits={"reasoningEffort": effort}, output_path="receipts/repair.json")
                kwargs = self.calls[-1][1]
                self.assertEqual(kwargs["reasoning_effort"], effort)
                self.assertEqual(receipt["reasoning_effort"], effort)
                progress = json.loads((self.root / "receipts/repair.progress.json").read_text())
                self.assertEqual(progress["reasoning_effort"], effort)
                self.assertEqual((kwargs["provider"], kwargs["model_name"], kwargs["temperature"]),
                    ("grok_cli", "grok-4.7", 0))
                self.assertFalse(kwargs["allow_local_fallback"])
                self.assertFalse(kwargs["allow_cross_provider_fallback"])
                self.assertTrue(kwargs["disable_model_retry"])

    def test_default_reasoning_effort_is_omitted(self):
        receipt = self.invoke(output_path="receipts/review.json")
        self.assertNotIn("reasoning_effort", self.calls[0][1])
        self.assertNotIn("reasoning_effort", receipt)
        progress = json.loads((self.root / "receipts/review.progress.json").read_text())
        self.assertNotIn("reasoning_effort", progress)

    def test_repair_profile_effort_is_scoped_and_task_can_override(self):
        profile = {"llm": {"repairReasoningEffort": "low"}}
        self.assertEqual(adapter.model_call_limits(profile, "repair")["reasoningEffort"], "low")
        self.assertEqual(adapter.model_call_limits(profile, "repair", {"reasoningEffort": "high"})["reasoningEffort"], "high")
        for mode in ("review", "probe"):
            self.assertNotIn("reasoningEffort", adapter.model_call_limits(profile, mode))
        for value in (None, False, 1, "LOW", "low --model another"):
            with self.subTest(value=value), self.assertRaisesRegex(adapter.ModelAdapterError, "repairReasoningEffort"):
                adapter.model_call_limits({"llm": {"repairReasoningEffort": value}}, "repair")

    def test_profile_repair_effort_reaches_pinned_router(self):
        self.profile.write_text(json.dumps({"todoPath": "board.todo.md", "llm": {"repairReasoningEffort": "low"}}))
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit()])
        receipt = self.invoke("repair", predicted_files=["app.js"])
        self.assertEqual(receipt["reasoning_effort"], "low")
        kwargs = self.calls[-1][1]
        self.assertEqual((kwargs["reasoning_effort"], kwargs["provider"], kwargs["model_name"]), ("low", "grok_cli", "grok-4.7"))
        self.assertFalse(kwargs["allow_local_fallback"])
        self.assertFalse(kwargs["allow_cross_provider_fallback"])

    def test_thought_only_timeout_is_diagnosed_without_claiming_a_response(self):
        native = {"timed_out": True, "native_grok_progress": {"frames": 300, "text_bytes": 0,
            "event_counts": {"thought": 298}}}
        codes = adapter._failure_diagnostics(native, TimeoutError())["codes"]
        self.assertIn("provider_timeout_with_activity", codes)
        self.assertIn("provider_timeout_without_response", codes)
        native["native_grok_progress"]["text_bytes"] = 200
        self.assertNotIn("provider_timeout_without_response", adapter._failure_diagnostics(native, TimeoutError())["codes"])

    def test_invalid_reasoning_effort_fails_before_provider_invocation(self):
        for value in (None, False, 1, [], {}, "", "LOW", "minimal", "low --model another"):
            with self.subTest(value=value), self.assertRaisesRegex(adapter.ModelAdapterError, "reasoningEffort"):
                self.invoke(task_limits={"reasoningEffort": value})
        self.assertEqual(self.calls, [])

    def test_failed_invocation_retains_explicit_reasoning_effort_without_error_body(self):
        def fail(_prompt, **kwargs):
            self.calls.append((_prompt, kwargs))
            raise RuntimeError("private provider error body")
        self.router.generate_text = fail
        with self.assertRaises(RuntimeError):
            self.invoke(task_limits={"reasoningEffort": "low"}, output_path="receipts/failed.json")
        receipt = json.loads((self.root / "receipts/failed.json").read_text())
        self.assertEqual(receipt["reasoning_effort"], "low")
        self.assertIs(receipt["success"], False)
        self.assertNotIn("private provider", json.dumps(receipt))

    def test_context_budget_failure_is_typed_and_precedes_paid_generation(self):
        self.source.write_text("large existing source line\n" * 200)
        self.response.update(mode="repair", decision="needs_changes", edits=[])
        with self.assertRaises(adapter.ModelContextBudgetError) as caught:
            self.invoke("repair", predicted_files=["app.js"], task_limits={"modelContextBytes": 2048})
        self.assertEqual(caught.exception.limit_bytes, 2048)
        self.assertGreater(caught.exception.actual_bytes, caught.exception.limit_bytes)
        self.assertEqual(self.calls, [])

    def test_failed_literal_hunk_retains_bounded_candidate_and_body_free_diagnostic_without_edits(self):
        before = self.source.read_bytes()
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit(old="absent unique anchor", new="replacement payload")])
        with self.assertRaisesRegex(adapter.EditProposalError, r"path=app.js hunk_index=1 match_count=0"):
            self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
        receipt = json.loads((self.root / "receipts/rejected.json").read_text())
        self.assertFalse(receipt["success"])
        self.assertFalse(receipt["edits_applied"])
        self.assertNotIn("response", receipt)
        self.assertEqual(receipt["rejected_response"], self.response)
        self.assertEqual(receipt["rejected_response_sha256"], adapter._sha(adapter._json(self.response).encode()))
        detail = receipt["edit_validation_error"]
        self.assertEqual((detail["code"], detail["path"], detail["hunk_index"], detail["match_count"]),
                         ("edit_anchor_match_count", "app.js", 1, 0))
        self.assertNotIn("absent unique anchor", json.dumps(detail))
        self.assertNotIn("replacement payload", receipt["reason"])
        self.assertEqual(self.source.read_bytes(), before)
        with self.assertRaises(adapter.ModelAdapterError):
            adapter.validate_model_receipt(self.root, receipt, task_id="SVF-001", mode="repair")

    def test_nonunique_second_hunk_reports_index_and_never_applies_the_first(self):
        self.source.write_text("before duplicate duplicate\n")
        before = self.source.read_bytes()
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit(), self.edit(old="duplicate", new="after")])
        with self.assertRaises(adapter.EditProposalError) as raised:
            self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
        self.assertEqual(raised.exception.diagnostic["hunk_index"], 2)
        self.assertEqual(raised.exception.diagnostic["match_count"], 2)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertIn("rejected_response", json.loads((self.root / "receipts/rejected.json").read_text()))

    def test_unallowlisted_later_hunk_is_never_retained_behind_earlier_literal_failure(self):
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit(old="absent"), self.edit(path="board.todo.md")])
        with self.assertRaisesRegex(adapter.ModelAdapterError, "Predicted files"):
            self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
        receipt = json.loads((self.root / "receipts/rejected.json").read_text())
        self.assertNotIn("rejected_response", receipt)
        self.assertNotIn("edit_validation_error", receipt)
        self.assertEqual(self.source.read_text(), "export const label = 'before';\n")

    def test_edit_shape_validation_remains_mandatory_when_current_bytes_are_not_checked(self):
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit()])
        for change in [lambda e: e.update(path="board.todo.md"), lambda e: e.update(before_sha256="not-a-hash"),
                       lambda e: e.update(old="bad\x00text"), lambda e: e.update(new="x" * (adapter.MAX_FILE_BYTES + 1)),
                       lambda e: e.update(new="bad\ud800text"), lambda e: e.update(actual="invented")]:
            response = json.loads(json.dumps(self.response))
            change(response["edits"][0])
            with self.subTest(edit=list(response["edits"][0])), self.assertRaises(adapter.ModelAdapterError):
                adapter._response(response, "SVF-001", "repair", ["screen.png"], self.root, ["app.js"], validate_edit_bytes=False)

    def test_changed_invocation_input_cannot_be_retained_as_a_rejected_candidate(self):
        self.response.update(mode="repair", decision="needs_changes", edits=[self.edit(old="absent")])
        self.hook = lambda: self.source.write_text("foreign concurrent source\n")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "changed during invocation"):
            self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
        receipt = json.loads((self.root / "receipts/rejected.json").read_text())
        self.assertNotIn("rejected_response", receipt)
        self.assertEqual(self.source.read_text(), "foreign concurrent source\n")

    def test_failed_candidate_with_credential_material_is_not_retained(self):
        for new in ["const api_key = 'sensitive_disposable_fixture_value';", "const token = 'xai-012345678901234567890123';"]:
            self.response.update(mode="repair", decision="needs_changes", edits=[self.edit(old="absent", new=new)])
            with self.assertRaises(adapter.EditProposalError):
                self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
            receipt = json.loads((self.root / "receipts/rejected.json").read_text())
            self.assertNotIn("rejected_response", receipt)
            self.assertIn("edit_validation_error", receipt)
            self.assertNotIn("sensitive_disposable_fixture_value", json.dumps(receipt))
            self.assertNotIn("xai-012345678901234567890123", json.dumps(receipt))

    def test_provider_failures_keep_codes_and_telemetry_without_candidate_or_native_bodies(self):
        def fail(_prompt, **_kwargs):
            self.metadata.value = {"native_grok_reason_code": "process_error", "native_grok_error_body": "private provider body",
                                   "native_grok_progress": {"frames": 2, "stderr": "private stderr", "thought": "private thought"}}
            raise RuntimeError("private exception body")
        self.router.generate_text = fail
        with self.assertRaises(RuntimeError):
            self.invoke("repair", predicted_files=["app.js"], output_path="receipts/rejected.json")
        receipt = json.loads((self.root / "receipts/rejected.json").read_text())
        self.assertNotIn("rejected_response", receipt)
        self.assertIn("native_process_error", receipt["failure_diagnostics"]["codes"])
        self.assertNotIn("private", json.dumps(receipt))
        self.assertEqual(receipt["native_observation"]["native_grok_progress"], {"frames": 2})

    def test_turn_cutoff_survives_generic_process_error_in_safe_diagnostics(self):
        native = {"native_grok_reason_code": "process_error", "native_grok_progress": {
            "final_reason_code": "max_turns", "stream_tainted": True, "rawOutput": "private body"}}
        diagnostic = adapter._failure_diagnostics(native, RuntimeError("private provider body"))
        self.assertIn("native_max_turns", diagnostic["codes"])
        self.assertIn("native_process_error", diagnostic["codes"])
        self.assertNotIn("private", json.dumps(diagnostic))

    def test_inline_repairs_disable_all_native_tools_and_use_one_turn(self):
        profile = json.loads(self.profile.read_text()); profile["llm"]["repairReadPolicy"] = "inline_only"
        self.profile.write_text(json.dumps(profile))
        self.response.update(mode="repair", decision="needs_changes", inspected_screenshots=[], edits=[self.edit()])
        self.native["native_grok_progress"]["tool_name_counts"]["read_file"] = 0
        result = self.invoke("repair", screenshot_paths=[], predicted_files=["app.js"])
        prompt, kwargs = self.calls[-1]
        self.assertEqual(kwargs["grok_tools"], "")
        self.assertIn("read_file", kwargs["grok_disallowed_tools"].split(","))
        self.assertEqual(kwargs["grok_max_turns"], 1)
        self.assertEqual(result["native_tool_allowlist"], [])
        self.assertTrue(result["native_read_file_denied"])
        self.assertIn("Native tools are disabled", prompt)
        adapter.validate_model_receipt(self.root, result, task_id="SVF-001", mode="repair", predicted_files=["app.js"])
        with self.assertRaisesRegex(adapter.ModelAdapterError, "outside declared"):
            adapter.validate_model_receipt(self.root, result, task_id="SVF-001", mode="repair")
        with self.assertRaisesRegex(adapter.ModelAdapterError, "outside declared"):
            adapter.validate_model_receipt(self.root, result, task_id="SVF-001", mode="repair", predicted_files=["new.js"])
        self.assertEqual(self.source.read_text(), "export const label = 'before';\n")

    def test_inline_repair_rejects_a_denied_native_read_without_applying(self):
        profile = json.loads(self.profile.read_text()); profile["llm"]["repairReadPolicy"] = "inline_only"
        self.profile.write_text(json.dumps(profile))
        self.response.update(mode="repair", decision="needs_changes", inspected_screenshots=[], edits=[self.edit()])
        with self.assertRaisesRegex(adapter.ModelAdapterError, "denied read tool"):
            self.invoke("repair", screenshot_paths=[], predicted_files=["app.js"])
        self.assertEqual(self.source.read_text(), "export const label = 'before';\n")


if __name__ == "__main__":
    unittest.main()
