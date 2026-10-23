"""Pure staged R22 tests. Synthetic fixtures provide no browser or GO authority."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load("r22_verifier_pure_tests", "verify-openrouter-default-action-repair.py")
admission = load("r22_admitter_pure_tests", "admit-openrouter-default-action-repair.py")
IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=")


def preservation_fixture():
    baseline = {"cells": {cell: {"input_fingerprint": "a" * 64, "run_id": cell.replace("/", "-") + "-synthetic",
                "report_sha256": "b" * 64, "row_count": 4} for cell in verifier.UNAFFECTED}}
    live = {"inventory": {"current": True}, "fingerprints": {cell: "a" * 64 for cell in verifier.UNAFFECTED},
            "acquisitions": {cell: {**fields, "capture_complete": True} for cell, fields in baseline["cells"].items()}}
    record = {"schema": "swissknife.vdg-openrouter-preservation.v1", "before_app_sha256": verifier.OLD_APP_SHA256,
              "after_app_sha256": "c" * 64, "gui_acceptance": False, "work_complete": False,
              "completion_authority": False, "cells": {cell: {"before_input_fingerprint": "a" * 64,
              "after_input_fingerprint": "a" * 64, "run_id": fields["run_id"], "report_sha256": "b" * 64}
              for cell, fields in baseline["cells"].items()}}
    return record, live, baseline


def board_fixture(prerequisite="completed", target="pending"):
    return f"""# Synthetic pure unit board; no completion authority

## VDG-013-R20 Prior recovery
- Status: completed
- Depends on:
- Acceptance: immutable prior history
- Refusal count: 3

## VDG-013-R21 Prior exact repair
- Status: {prerequisite}
- Depends on: VDG-013-R20
- Acceptance: immutable product proof

## VDG-039-R01 Original actual batch
- Status: {target}
- Depends on: VDG-013-R21
- Deterministic command: {admission.BATCH_COMMAND}
- Validation: node swissknife/scripts/run-vdg-all-families.mjs --check
- Predicted files: swissknife/test/e2e/families/local-negative-mcp.spec.ts
- Acceptance: all original acquisition requirements
- Implementation timeout seconds: 46800
- Resource class: cpu-browser
- Attempt count: 7

## VDG-060-R01 Original closeout
- Status: pending
- Depends on: VDG-039-R01
- Acceptance: all six strict GO and aggregate GO
"""


class UnapprovedContractTests(unittest.TestCase):
    def test_unset_preflight_pin_fails_before_any_child_or_live_check(self):
        with mock.patch.object(verifier, "REVIEWED_PREFLIGHT_SHA256", None), mock.patch.object(verifier.subprocess, "run") as child, mock.patch.object(verifier, "live_evidence") as live:
            with self.assertRaisesRegex(ValueError, "not pinned"):
                verifier.verify_ready_proof()
            child.assert_not_called()
            live.assert_not_called()

    def test_browser_pass_flag_and_candidate_never_become_proof(self):
        report = {"passed": True, "candidate_module_override": False,
                  "gui_acceptance": False, "work_complete": False, "completion_authority": False}
        with mock.patch.object(verifier, "BROWSER_CONTRACT_FROZEN", False), self.assertRaisesRegex(ValueError, "not frozen"):
            verifier.verify_report(report)
        with self.assertRaisesRegex(ValueError, "not canonical"):
            verifier.verify_report(dict(report, candidate_module_override=True))
        with self.assertRaisesRegex(ValueError, "schema"):
            verifier.verify_report(report)

    def test_synthetic_reports_cannot_grant_gui_or_completion(self):
        for field in ("gui_acceptance", "work_complete", "completion_authority"):
            report = {key: False for key in ("gui_acceptance", "work_complete", "completion_authority")}
            report[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                verifier.no_authority(report)

    def test_tap_rejects_unpinned_count_skips_failed_or_missing_tests(self):
        valid = "\n".join(["ok 1 - real behavior", "ok 2 - other behavior", "1..2", "# tests 2", "# pass 2",
                            "# fail 0", "# cancelled 0", "# skipped 0", "# todo 0"])
        verifier.tap(valid, 2)
        with self.assertRaisesRegex(ValueError, "not pinned"):
            with mock.patch.object(verifier, "FRESH_TEST_COUNT", None):
                verifier.tap(valid)
        for changed in (valid.replace("# skipped 0", "# skipped 1"), valid.replace("ok 1 -", "not ok 1 -"),
                        valid.replace("1..2", "1..1"), valid + "\n# pass 2", valid.replace("# todo 0", "# todo 1")):
            with self.subTest(text=changed), self.assertRaises(ValueError):
                verifier.tap(changed, 2)


class BrowserProofParserTests(unittest.TestCase):
    """Synthetic canonical-shaped fixtures, never rewritten real proof files.

The immutable real candidate remains marked candidate_module_override:true.
Only in-memory unit data normalizes that flag and source pair to exercise the
canonical parser. Tiny synthetic PNGs replace real screenshots in tempdirs.
"""
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="r22-parser-unit-", dir=HERE)
        self.addCleanup(temporary.cleanup)
        self.archive = Path(temporary.name)
        shutil.copytree(verifier.ARCHIVE / "actual-failure", self.archive / "actual-failure")
        shutil.copyfile(verifier.ARCHIVE / "precondition.json", self.archive / "precondition.json")
        self.report = json.loads((verifier.ARCHIVE / "candidate/result.json").read_text())
        self.assertIs(self.report["candidate_module_override"], True)
        self.report["candidate_module_override"] = False
        self.report["canonical_source_sha256"] = self.report["canonical_source_sha256_after"] = verifier.SOURCES[verifier.APP]
        directory = self.archive / "canonical"
        directory.mkdir()
        for name in self.report["screenshot_sha256"]:
            image = directory / name
            image.write_bytes(IMAGE)
            self.report["screenshot_sha256"][name] = verifier.sha(image)
        for row in self.report["catalog_responses"]:
            shutil.copyfile(verifier.ARCHIVE / "candidate" / row["file"], directory / row["file"])

    def test_valid_synthetic_shape_has_twenty_actions_zero_posts_and_no_authority(self):
        self.assertEqual(verifier.verify_report(self.report, self.archive), {"actual_profiles": 2, "actual_actions": 20,
                         "actual_pngs": 40, "actual_posts": 0, "original_controls_per_profile": 1881,
                         "real_catalog_models_per_profile": 468})
        self.assertIs(self.report["completion_authority"], False)

    def test_real_candidate_remains_rejected_without_canonical_source_relabeling(self):
        candidate = json.loads((verifier.ARCHIVE / "candidate/result.json").read_text())
        with self.assertRaisesRegex(ValueError, "not canonical"):
            verifier.verify_report(candidate, self.archive)

    def test_source_profiles_post_attempts_cleanup_and_unproven_causality_tampering_rejected(self):
        changes = {
            "source": lambda r: r.update(source_sha256="a" * 64),
            "canonical": lambda r: r.update(canonical_source_sha256=verifier.OLD_APP_SHA256),
            "changed_during_run": lambda r: r.update(canonical_source_unchanged=False),
            "helper_pin": lambda r: r["source_hashes"].update({verifier.HELPER: "a" * 64}),
            "reproduced_claim": lambda r: r.update(original_timeout_reproduced=True),
            "causal_claim": lambda r: r.update(original_timeout_causality_established=True),
            "post_attempt": lambda r: r.update(posts_attempted=[{"method": "POST"}]),
            "blocked_post": lambda r: r.update(posts_blocked=[{"method": "POST"}]),
            "page_error": lambda r: r.update(page_errors=["actual failure"]),
            "live_browser": lambda r: r["resources"].update(chrome_pid_absent=False),
            "boolean_pid": lambda r: r["resources"].update(vite_pid=True),
            "duplicate_profile": lambda r: r["profiles"][1].update(transport="http"),
            "missing_profile": lambda r: r["profiles"].pop(),
            "reset_state": lambda r: r["profiles"][0].update(no_case_storage_reset=False),
            "missing_original_control": lambda r: r["profiles"][0].update(original_control_count=1880),
            "unresolved_selector": lambda r: r["profiles"][0].update(unresolved_original_selectors=["#missing"]),
            "historical_storage_claim": lambda r: r["precondition"].update(raw_historical_storage_snapshot=True),
            "gui_authority": lambda r: r.update(gui_acceptance=True),
        }
        for name, change in changes.items():
            report = copy.deepcopy(self.report)
            change(report)
            with self.subTest(name=name), self.assertRaises(ValueError):
                verifier.verify_report(report, self.archive)

    def test_actual_dom_identity_trusted_scroll_persistence_and_other_actions_required(self):
        first = lambda r: r["profiles"][0]["cases"][0]
        changes = {
            "missing_action": lambda r: r["profiles"][0]["cases"].pop(),
            "wrong_selector": lambda r: first(r).update(selector="#other"),
            "untrusted": lambda r: first(r)["trusted_events"][0].update(trusted=False),
            "replaced_root": lambda r: first(r)["after"].update(root_same=False),
            "detached_target": lambda r: first(r)["after"].update(target_same=False),
            "lost_focus": lambda r: first(r)["after"].update(target_focused=False),
            "replaced_controls": lambda r: first(r)["after"].update(all_model_control_nodes_same=False),
            "handler_replaced_root": lambda r: first(r)["trusted_events"][0].update(root_same_before_handler=False),
            "handler_wrong_target": lambda r: first(r)["trusted_events"][0].update(target_same_before_handler=False),
            "scroll_changed": lambda r: first(r)["after"]["scroll"][0].update(top=1),
            "missing_genuine_write": lambda r: first(r)["write_events"].pop(),
            "repeat_changed_owned_data": lambda r: r["profiles"][0]["cases"][1]["after"]["storage"].update(openrouter_conversations='["changed"]'),
            "favorite_not_removed": lambda r: r["profiles"][0]["cases"][4]["after"].update(favorite_count=61),
            "info_not_shown": lambda r: r["profiles"][0]["cases"][6]["after"].update(dialogs=[]),
            "try_saved": lambda r: r["profiles"][0]["cases"][7]["after"].update(persisted_default=verifier.TARGET_MODEL),
            "try_save_path_lost": lambda r: r["profiles"][0]["cases"][8]["before"].update(default_model=verifier.NEIGHBOR_MODEL),
            "close_lost_preferences": lambda r: first(r)["persisted_after_close"].update(default_model=verifier.PREVIOUS_MODEL),
            "dropped_model": lambda r: first(r)["after"].update(model_count=467),
            "bool_timing": lambda r: first(r).update(click_ms=True),
        }
        for name, change in changes.items():
            report = copy.deepcopy(self.report)
            change(report)
            with self.subTest(name=name), self.assertRaises(ValueError):
                verifier.verify_report(report, self.archive)

    def test_raw_catalog_hash_and_real_model_inventory_cannot_be_replaced(self):
        response = self.report["catalog_responses"][0]
        path = self.archive / "canonical" / response["file"]
        catalog = json.loads(path.read_text())
        catalog["data"].pop()
        path.write_text(json.dumps(catalog))
        response["sha256"] = verifier.sha(path)
        with self.assertRaisesRegex(ValueError, "catalog"):
            verifier.verify_report(self.report, self.archive)

    def test_missing_unsafe_extra_or_corrupted_png_is_rejected(self):
        name = next(iter(self.report["screenshot_sha256"]))
        for kind in ("missing", "unsafe", "extra"):
            report = copy.deepcopy(self.report)
            if kind == "missing":
                report["screenshot_sha256"].pop(name)
            elif kind == "unsafe":
                report["screenshot_sha256"]["../escaped.png"] = "a" * 64
            else:
                report["screenshot_sha256"]["unreviewed.png"] = "a" * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verifier.verify_report(report, self.archive)
        (self.archive / "canonical" / name).write_bytes(b"not png")
        with self.assertRaises(ValueError):
            verifier.verify_report(self.report, self.archive)


class TenCellPreservationTests(unittest.TestCase):
    def test_all_ten_completed_cells_include_accelerate_and_exclude_local(self):
        self.assertEqual(len(verifier.UNAFFECTED), 10)
        self.assertIn("vdg-accelerate/http", verifier.UNAFFECTED)
        self.assertIn("vdg-accelerate/libp2p", verifier.UNAFFECTED)
        self.assertNotIn("vdg-local/http", verifier.UNAFFECTED)
        with mock.patch.object(verifier, "SOURCES", {verifier.APP: "c" * 64}):
            verifier.verify_preservation(*preservation_fixture())

    def test_exact_source_acquisition_hash_row_count_and_current_inventory_required(self):
        for kind in ("missing_cell", "extra_local", "changed_fp", "changed_run", "changed_report", "incomplete",
                     "row_count", "bool_row_count", "stale_inventory", "different_baseline", "authority"):
            record, live, baseline = preservation_fixture()
            first = next(iter(verifier.UNAFFECTED))
            if kind == "missing_cell":
                live["acquisitions"].pop(first)
            elif kind == "extra_local":
                record["cells"]["vdg-local/http"] = dict(record["cells"][first])
            elif kind == "changed_fp":
                live["fingerprints"][first] = "d" * 64
            elif kind == "changed_run":
                live["acquisitions"][first]["run_id"] = "other"
            elif kind == "changed_report":
                live["acquisitions"][first]["report_sha256"] = "d" * 64
            elif kind == "incomplete":
                live["acquisitions"][first]["capture_complete"] = False
            elif kind in {"row_count", "bool_row_count"}:
                live["acquisitions"][first]["row_count"] = True if kind == "bool_row_count" else 5
            elif kind == "stale_inventory":
                live["inventory"]["current"] = False
            elif kind == "different_baseline":
                baseline["cells"][first]["report_sha256"] = "d" * 64
            else:
                record["completion_authority"] = True
            with mock.patch.object(verifier, "SOURCES", {verifier.APP: "c" * 64}), self.subTest(kind=kind), self.assertRaises(ValueError):
                verifier.verify_preservation(record, live, baseline)


class ImmutableFailureTests(unittest.TestCase):
    def test_original_timeout_and_false_completion_are_required(self):
        with tempfile.TemporaryDirectory(prefix="r22-failure-", dir=HERE) as temporary:
            archive = Path(temporary)
            directory = archive / "actual-failure"
            directory.mkdir()
            original = directory / "source-before-openrouter.js"
            original.write_text("synthetic original app; no GUI authority")
            row = {"app_id": "openrouter", "launch_id": "openrouter", "selector": verifier.FAILED_SELECTOR,
                   "clicked": False, "failure_reasons": ["locator.click: Timeout 3000ms exceeded.".ljust(180, "."), "click-failed"],
                   "pageerrors": [], "mcp_call_count": 0, "incomplete_mcp_call_count": 0, "observations": [], "observation": None}
            checkpoint = {"schema": "swissknife.vdg-capture-checkpoint.v1", "target": "local", "transport": "http",
                "input_fingerprint": verifier.OLD_FINGERPRINT, "payload_sha256": verifier.OLD_PAYLOAD_SHA256,
                "capture_complete": False, "work_complete": False, "completion_authority": False,
                "payload": {"rows": [{} for _ in range(361)]}}
            checkpoint["payload"]["rows"][322] = row
            rowfile, checkpointfile = directory / "failed-row.json", directory / "checkpoint-before.json"
            images = {}
            for name in verifier.OLD_IMAGES:
                image = directory / name
                image.write_bytes(IMAGE)
                images[name] = verifier.sha(image)
            def pins():
                rowfile.write_text(json.dumps(row)); checkpointfile.write_text(json.dumps(checkpoint))
                return mock.patch.multiple(verifier, OLD_APP_SHA256=verifier.sha(original), OLD_ROW_SHA256=verifier.sha(rowfile),
                    OLD_CHECKPOINT_SHA256=verifier.sha(checkpointfile), OLD_IMAGES=images)
            with pins():
                self.assertEqual(verifier.verify_failure(archive)["original_failure_row"], 322)
            for kind in ("cleared", "clicked", "completed", "wrong_index", "invented_fulltrace"):
                saved_row, saved_checkpoint = copy.deepcopy(row), copy.deepcopy(checkpoint)
                if kind == "cleared":
                    row["failure_reasons"] = []
                elif kind == "clicked":
                    row["clicked"] = True
                elif kind == "completed":
                    checkpoint["capture_complete"] = True
                elif kind == "wrong_index":
                    checkpoint["payload"]["rows"][322] = {}
                else:
                    row["failure_reasons"][0] += " invented full trace"
                with pins(), self.subTest(kind=kind), self.assertRaises((ValueError, IndexError)):
                    verifier.verify_failure(archive)
                row, checkpoint = saved_row, saved_checkpoint
                checkpoint["payload"]["rows"][322] = row

    def test_bound_json_rejects_changed_bytes_or_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="r22-immutable-", dir=HERE) as temporary:
            path = Path(temporary) / "proof.json"
            path.write_text('{"synthetic": true}')
            pin = verifier.sha(path)
            self.assertTrue(verifier.bound_json(path, pin)["synthetic"])
            path.write_text('{"synthetic": false}')
            with self.assertRaises(ValueError):
                verifier.bound_json(path, pin)
            target = path.with_name("other.json")
            path.rename(target); path.symlink_to(target)
            with self.assertRaises(ValueError):
                verifier.bound_json(path, verifier.sha(target))


class AdditiveAdmissionTests(unittest.TestCase):
    def test_only_r22_and_original_batch_dependency_are_added(self):
        original = board_fixture()
        result, before, after = admission.build_admission(original)
        self.assertTrue(result["admitted"])
        self.assertEqual(set(after) - set(before), {"VDG-013-R22"})
        self.assertEqual(after["VDG-013-R22"]["depends_on"], "VDG-013-R21")
        self.assertEqual(after["VDG-013-R22"]["resource_class"], "cpu-small")
        self.assertEqual(after["VDG-013-R22"]["implementation_timeout_seconds"], "1800")
        self.assertEqual(after["VDG-013-R22"]["deterministic_command"], after["VDG-013-R22"]["validation"])
        self.assertEqual(after["VDG-039-R01"]["attempt_count"], "7")
        self.assertEqual(after["VDG-039-R01"]["implementation_timeout_seconds"], "46800")
        self.assertEqual(after["VDG-060-R01"], before["VDG-060-R01"])
        self.assertTrue(all(after[task]["status"] == fields["status"] for task, fields in before.items()))
        repeated, _, _ = admission.build_admission(result["todo_text"])
        self.assertFalse(repeated["admitted"])
        self.assertEqual(repeated["todo_text"], result["todo_text"])

    def test_unfinished_r21_or_nonpending_original_batch_are_rejected(self):
        for status in ("pending", "in_progress", "blocked", "failed"):
            with self.subTest(prerequisite=status), self.assertRaises(ValueError):
                admission.build_admission(board_fixture(prerequisite=status))
        for status in ("completed", "in_progress", "blocked"):
            with self.subTest(target=status), self.assertRaises(ValueError):
                admission.build_admission(board_fixture(target=status))

    def test_changed_original_command_or_cyclic_dependencies_are_rejected(self):
        original = board_fixture()
        with self.assertRaises(ValueError):
            admission.build_admission(original.replace(admission.BATCH_COMMAND, "node swissknife/scripts/other.mjs"))
        with self.assertRaises(ValueError):
            admission.build_admission(original.replace("- Depends on: VDG-013-R20", "- Depends on: VDG-039-R01"))

    def test_owned_stopped_fence_rejects_mismatched_owner_and_hold(self):
        with tempfile.TemporaryDirectory(prefix="r22-fence-", dir=HERE) as temporary:
            root = Path(temporary)
            lane = root / "lanes/vdg-planning"
            lane.mkdir(parents=True)
            (lane / "vdg-planning.resume.lock").touch(mode=0o600)
            (lane / "vdg_planning_status.json").write_text(json.dumps({"pid": 1000000000, "state": "stopped",
                                                                      "terminal_reason": "resume_stopped"}))
            pidfile = lane / "vdg_planning_bundle_supervisor.pid"
            pidfile.write_text("1000000000\n")
            hold = root / "repair-dispatcher.hold"
            hold.write_text(json.dumps({"reason": "controlled VDG completion repairs", "lane_pid": 1000000000}))
            with mock.patch.object(admission, "active_captures", return_value=[]):
                with admission.lifecycle_fence(root, root) as identity:
                    admission.recheck_fence(identity, root, root)
                pidfile.write_text("1000000001\n")
                with self.assertRaisesRegex(ValueError, "PID file disagree"):
                    with admission.lifecycle_fence(root, root):
                        pass
                pidfile.write_text("1000000000\n")
                hold.write_text(json.dumps({"reason": "unrelated hold", "lane_pid": 1000000000}))
                with self.assertRaisesRegex(ValueError, "controlled repair hold"):
                    with admission.lifecycle_fence(root, root):
                        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
