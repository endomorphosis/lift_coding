"""Pure R21 parser, proof-tamper and DAG tests. Synthetic fixtures grant no GUI authority."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load("r21_verifier_pure_tests", "verify-strudel-ai-playback-repair.py")
admission = load("r21_admitter_pure_tests", "admit-strudel-ai-playback-repair.py")
IMAGE = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=")


def browser_fixture(directory):
    archive = directory / "archive"
    images = archive / "canonical"
    images.mkdir(parents=True)
    report = {"schema": "swissknife.vdg-strudel-ai-playback-smoke.v1", "passed": True,
              "source_sha256": verifier.SOURCES[verifier.APP], "canonical_source_sha256": verifier.SOURCES[verifier.APP],
              "candidate_module_override": False, "source_path": str(directory / verifier.APP),
              "project_root": str(directory / "swissknife"), "profiles": [], "route_interception": False,
              "gui_acceptance": False, "completion_authority": False, "work_complete": False,
              "owned_resources": {"server_pid": 1001, "browser_pid": 1002, "server_alive_after_cleanup": False,
                                  "browser_alive_after_cleanup": False}, "owned_resources_closed": True, "screenshot_sha256": {}}
    for transport in verifier.TRANSPORTS:
        profile = {"transport_profile": transport, "cases": [], "reopened_play_and_cleanup": True, "actual_factory": True,
                   "audio_platform_mocked": False, "actual_signal_and_silence": True, "module_responses": [{"status": 200}],
                   "page_errors": [], "posts": [], "dialogs": [], "owned_app_resources_closed": True}
        beats = [{"time": 1, "frequency": 1000, "bpm": 120}, {"time": 1.5, "frequency": 1000, "bpm": 120},
                 {"time": 2, "frequency": 1000, "bpm": 162}, {"time": 2 + 60 / 162, "frequency": 1000, "bpm": 162}]
        for label, selector in verifier.ACTIONS:
            playing = label in verifier.PLAYING
            state = {"playing": playing, "mode": "local-preview", "audio_state": "running",
                     "bpm": 162 if label == "tempo" else 120, "gain": 0.99 if label == "volume" else 0.8,
                     "rms": 0.02 if playing else 0.0, "worklet": False, "audio_backend": "web-audio-reference",
                     "reference_frequency": 220 if playing else None, "native_oscillator_count": 2 if playing else 0,
                     "native_gain_count": 2 if playing else 0, "scheduler_active": playing, "scheduled_beats": copy.deepcopy(beats),
                     "audio_cleanup_errors": [],
                     "status": "Local audio preview: metronome/reference tone; compilation unavailable" if playing else "Paused" if label == "pause" else "Stopped",
                     "closed": False, "frame": 3}
            wanted_id = selector[1:] if selector.startswith("#") and " " not in selector else ""
            profile["cases"].append({"label": label, "selector": selector, "trusted_events": [{"type": "input" if label in {"editor", "live-parameter", "volume", "tempo"} else "click",
                    "trusted": True, "id": wanted_id}], "state": state, "evidence": None, "passed": True})
            if label == "tempo":
                live_tempo = copy.deepcopy(state)
                live_tempo.update(playing=True, rms=0.02, reference_frequency=220, native_oscillator_count=2,
                                  native_gain_count=2, scheduler_active=True,
                                  status="Local audio preview: metronome/reference tone; compilation unavailable")
                profile["cases"][-1]["evidence"] = {"live_tempo_state": live_tempo}
                profile["cases"][-1]["trusted_events"].extend({"type": "click", "trusted": True, "id": control}
                                                              for control in ("play-btn", "stop-btn"))
            for position in ("before", "after"):
                image = images / f"{transport}-{label}-{position}.png"
                image.write_bytes(IMAGE)
                report["screenshot_sha256"][image.name] = verifier.sha(image)
        profile["closed_while_playing"] = {"playing": False, "mode": "local-preview", "audio_state": "closed", "bpm": 120,
            "gain": 0.99, "rms": 0.02, "worklet": False, "audio_backend": "web-audio-reference", "reference_frequency": None,
            "native_oscillator_count": 0, "native_gain_count": 0, "scheduler_active": False,
            "scheduled_beats": copy.deepcopy(beats), "audio_cleanup_errors": [], "status": "Stopped", "closed": True, "frame": None}
        profile.update(mounted_without_gesture=True, mount_trusted_event_count=0, pre_play_state={"playing": False,
            "mode": "local-preview", "audio_state": "running", "bpm": 120, "gain": 0.8, "rms": 0, "worklet": False,
            "audio_backend": "unavailable", "reference_frequency": None, "native_oscillator_count": 0, "native_gain_count": 0,
            "scheduler_active": False, "scheduled_beats": [],
            "audio_cleanup_errors": [],
            "status": "Local audio preview ready: metronome/reference tone; compilation unavailable", "closed": False, "frame": 3})
        report["profiles"].append(profile)
    return report, archive


class BrowserProofParserTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="r21-pure-", dir=HERE)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pins = mock.patch.object(verifier, "SOURCES", {name: "a" * 64 for name in verifier.SOURCES})
        self.pins.start()
        self.addCleanup(self.pins.stop)
        self.report, self.archive = browser_fixture(self.root)

    def test_valid_synthetic_parser_fixture_has_twenty_actions_and_no_authority(self):
        self.assertEqual(verifier.verify_report(self.report, self.archive, self.root),
                         {"actual_profiles": 2, "actual_actions": 20, "actual_pngs": 40, "actual_posts": 0})
        self.assertIs(self.report["completion_authority"], False)

    def test_browser_canonical_identity_and_cleanup_tampering_rejected(self):
        changes = {
            "candidate": lambda r: r.update(candidate_module_override=True),
            "route_override": lambda r: r.update(route_interception=True),
            "source": lambda r: r.update(source_sha256="b" * 64),
            "canonical_source": lambda r: r.update(canonical_source_sha256="b" * 64),
            "source_path": lambda r: r.update(source_path="/tmp/candidate.js"),
            "project_path": lambda r: r.update(project_root="/tmp/candidate"),
            "failed": lambda r: r.update(passed=False),
            "authority": lambda r: r.update(gui_acceptance=True),
            "completion": lambda r: r.update(completion_authority=True),
            "live_browser": lambda r: r["owned_resources"].update(browser_alive_after_cleanup=True),
            "boolean_pid": lambda r: r["owned_resources"].update(server_pid=True),
            "same_pid": lambda r: r["owned_resources"].update(server_pid=1002),
            "missing_profile": lambda r: r["profiles"].pop(),
            "duplicate_profile": lambda r: r["profiles"][1].update(transport_profile="http"),
            "not_factory": lambda r: r["profiles"][0].update(actual_factory=False),
            "fake_audio": lambda r: r["profiles"][0].update(audio_platform_mocked=True),
            "post": lambda r: r["profiles"][0].update(posts=[{"method": "POST"}]),
            "page_error": lambda r: r["profiles"][0].update(page_errors=["stop missing"]),
            "dialog": lambda r: r["profiles"][0].update(dialogs=[{"dismissed": True}]),
            "module_404": lambda r: r["profiles"][0].update(module_responses=[{"status": 404}]),
            "no_reopen": lambda r: r["profiles"][0].update(reopened_play_and_cleanup=False),
            "no_app_cleanup": lambda r: r["profiles"][0].update(owned_app_resources_closed=False),
            "mount_gesture": lambda r: r["profiles"][0].update(mount_trusted_event_count=1),
            "preplay_signal": lambda r: r["profiles"][0]["pre_play_state"].update(rms=0.03),
            "preplay_playing": lambda r: r["profiles"][0]["pre_play_state"].update(playing=True),
            "preplay_claimed_backend": lambda r: r["profiles"][0]["pre_play_state"].update(audio_backend="web-audio-reference"),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                report = copy.deepcopy(self.report)
                change(report)
                with self.assertRaises(ValueError):
                    verifier.verify_report(report, self.archive, self.root)

    def test_actual_signal_silence_and_trusted_action_tampering_rejected(self):
        changes = {
            "missing_action": lambda r: r["profiles"][0]["cases"].pop(),
            "wrong_selector": lambda r: r["profiles"][0]["cases"][0].update(selector="#unrelated"),
            "wrong_order": lambda r: r["profiles"][0]["cases"].reverse(),
            "untrusted": lambda r: r["profiles"][0]["cases"][0]["trusted_events"][0].update(trusted=False),
            "wrong_control": lambda r: r["profiles"][0]["cases"][0]["trusted_events"][0].update(id="other"),
            "silent_play": lambda r: r["profiles"][0]["cases"][0]["state"].update(rms=0),
            "nan_signal": lambda r: r["profiles"][0]["cases"][0]["state"].update(rms=float("nan")),
            "no_pause_silence": lambda r: r["profiles"][0]["cases"][1]["state"].update(rms=0.01),
            "false_playing": lambda r: r["profiles"][0]["cases"][0]["state"].update(playing=False),
            "fake_compiled_status": lambda r: r["profiles"][0]["cases"][0]["state"].update(status="Compiled Strudel pattern"),
            "fake_worklet": lambda r: r["profiles"][0]["cases"][0]["state"].update(worklet=True),
            "wrong_backend": lambda r: r["profiles"][0]["cases"][0]["state"].update(audio_backend="compiled-strudel"),
            "missing_reference": lambda r: r["profiles"][0]["cases"][0]["state"].update(reference_frequency=None),
            "orphan_scheduler": lambda r: r["profiles"][0]["cases"][1]["state"].update(scheduler_active=True),
            "beat_frequency": lambda r: r["profiles"][0]["cases"][0]["state"]["scheduled_beats"][0].update(frequency=220),
            "missing_live_tempo": lambda r: r["profiles"][0]["cases"][4].update(evidence=None),
            "silent_live_tempo": lambda r: r["profiles"][0]["cases"][4]["evidence"]["live_tempo_state"].update(rms=0),
            "no_actual_162_beat": lambda r: r["profiles"][0]["cases"][4]["evidence"]["live_tempo_state"].update(scheduled_beats=[{"time": 1, "frequency": 1000, "bpm": 120}]),
            "wrong_162_interval": lambda r: r["profiles"][0]["cases"][4]["evidence"]["live_tempo_state"]["scheduled_beats"][-1].update(time=3),
            "tempo": lambda r: r["profiles"][0]["cases"][4]["state"].update(bpm=120),
            "gain": lambda r: r["profiles"][0]["cases"][5]["state"].update(gain=0.8),
            "tap": lambda r: r["profiles"][0]["cases"][6]["state"].update(bpm=301),
            "closed_playing": lambda r: r["profiles"][0]["closed_while_playing"].update(playing=True),
            "orphan_raf": lambda r: r["profiles"][0]["closed_while_playing"].update(frame=8),
            "orphan_audio": lambda r: r["profiles"][0]["closed_while_playing"].update(audio_state="running"),
            "orphan_nodes": lambda r: r["profiles"][0]["closed_while_playing"].update(native_oscillator_count=1, native_gain_count=1),
            "cleanup_error": lambda r: r["profiles"][0]["closed_while_playing"].update(audio_cleanup_errors=["actual close failed"]),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                report = copy.deepcopy(self.report)
                change(report)
                with self.assertRaises(ValueError):
                    verifier.verify_report(report, self.archive, self.root)

    def test_missing_extra_unsafe_or_corrupted_png_is_rejected(self):
        for name, change in {
            "missing": lambda r: r["screenshot_sha256"].pop("http-play-before.png"),
            "escape": lambda r: r["screenshot_sha256"].update({"../elsewhere.png": "a" * 64}),
        }.items():
            with self.subTest(name=name):
                report = copy.deepcopy(self.report)
                change(report)
                with self.assertRaises(ValueError):
                    verifier.verify_report(report, self.archive, self.root)
        image = self.archive / "canonical/http-play-before.png"
        image.write_bytes(b"invalid")
        with self.assertRaises(ValueError):
            verifier.verify_report(self.report, self.archive, self.root)

    def test_symlinked_png_is_not_immutable_proof(self):
        image = self.archive / "canonical/http-play-before.png"
        image.unlink()
        outside = self.root / "other.png"
        outside.write_bytes(IMAGE)
        image.symlink_to(outside)
        with self.assertRaises(ValueError):
            verifier.verify_report(self.report, self.archive, self.root)

    def test_unpinned_canonical_preflight_cannot_run_app_units(self):
        with mock.patch.object(verifier, "REVIEWED_PREFLIGHT_SHA256", None), mock.patch.object(verifier.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "not pinned"):
                verifier.verify_ready_proof()
            run.assert_not_called()


class FreshTapAndPreservationTests(unittest.TestCase):
    def test_fresh_tap_requires_every_real_test_and_no_skips(self):
        count = verifier.FRESH_TEST_COUNT or verifier.MINIMUM_TEST_COUNT
        valid = "\n".join([*(f"ok {index} - meaningful case {index}" for index in range(1, count + 1)), f"1..{count}",
                            f"# tests {count}", f"# pass {count}", "# fail 0", "# cancelled 0", "# skipped 0", "# todo 0"])
        verifier.tap(valid, count)
        for changed in (valid.replace("# skipped 0", "# skipped 1"), valid.replace("ok 1 -", "not ok 1 -"),
                        valid.replace(f"1..{count}", f"1..{count-1}"), valid + "\n# pass 1", valid.replace("# todo 0", "# todo 1")):
            with self.assertRaises(ValueError):
                verifier.tap(changed, count)
        with mock.patch.object(verifier, "FRESH_TEST_COUNT", None), self.assertRaisesRegex(ValueError, "not pinned"):
            verifier.tap(valid)

    def test_exact_baseline_eight_cells_and_all_acquisitions_required(self):
        baseline = {"cells": {cell: {"input_fingerprint": "a" * 64, "run_id": cell.replace("/", "-") + "-unit",
                    "report_sha256": "b" * 64, "row_count": 4} for cell in verifier.UNAFFECTED}}
        live = {"inventory": {"current": True}, "fingerprints": {cell: "a" * 64 for cell in verifier.UNAFFECTED},
                "acquisitions": {cell: {**fields, "capture_complete": True} for cell, fields in baseline["cells"].items()}}
        record = {"schema": "swissknife.vdg-strudel-ai-preservation.v2", "before_app_sha256": verifier.OLD_APP_SHA256,
                  "after_app_sha256": verifier.SOURCES[verifier.APP], "gui_acceptance": False, "work_complete": False,
                  "completion_authority": False, "cells": {cell: {"before_input_fingerprint": "a" * 64,
                  "after_input_fingerprint": "a" * 64, "run_id": fields["run_id"], "report_sha256": "b" * 64}
                  for cell, fields in baseline["cells"].items()}}
        verifier.verify_preservation(record, live, baseline)
        first = next(iter(verifier.UNAFFECTED))
        for field in ("before_input_fingerprint", "after_input_fingerprint", "run_id", "report_sha256"):
            changed = copy.deepcopy(record)
            changed["cells"][first][field] = "changed"
            with self.subTest(field=field), self.assertRaises(ValueError):
                verifier.verify_preservation(changed, live, baseline)
        for kind in ("missing", "extra_local", "incomplete", "row_count", "stale_inventory", "baseline_report"):
            r, l, b = copy.deepcopy(record), copy.deepcopy(live), copy.deepcopy(baseline)
            if kind == "missing":
                l["acquisitions"].pop(first)
            elif kind == "extra_local":
                r["cells"]["vdg-local/http"] = copy.deepcopy(r["cells"][first])
            elif kind == "incomplete":
                l["acquisitions"][first]["capture_complete"] = False
            elif kind == "row_count":
                l["acquisitions"][first]["row_count"] = 5
            elif kind == "stale_inventory":
                l["inventory"]["current"] = False
            else:
                b["cells"][first]["report_sha256"] = "changed"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verifier.verify_preservation(r, l, b)

    def test_immutable_failure_parser_keeps_original_error_and_capture_nogo(self):
        with tempfile.TemporaryDirectory(prefix="r21-failure-", dir=HERE) as temporary:
            archive = Path(temporary)
            directory = archive / "actual-failure"
            directory.mkdir()
            original = directory / "original-app.js"
            original.write_text("synthetic unit app, not execution evidence")
            row = {"app_id": "strudel-ai-daw", "launch_id": "strudel-ai-daw", "selector": "#play-btn", "clicked": True,
                   "failure_reasons": ["pageerror"], "pageerrors": ["TypeError: this.strudelEngine.stop is not a function"],
                   "mcp_call_count": 0, "incomplete_mcp_call_count": 0, "observations": [], "observation": None}
            report = {"schema": "swissknife.virtual-desktop-live-click.v1", "target": "local", "row_count": 2178,
                      "decision": "no_go", "rows": [{} for _ in range(2178)]}
            report["rows"][2092] = row
            rowfile = directory / "failed-row.json"
            reportfile = directory / "local-http-1792643190016.json"
            images = {}
            for name in verifier.OLD_IMAGES:
                image = directory / name
                image.write_bytes(IMAGE)
                images[name] = verifier.sha(image)
            def save():
                rowfile.write_text(json.dumps(row))
                reportfile.write_text(json.dumps(report))
                return mock.patch.multiple(verifier, OLD_APP_SHA256=verifier.sha(original), OLD_ROW_SHA256=verifier.sha(rowfile),
                                           OLD_REPORT_SHA256=verifier.sha(reportfile), OLD_IMAGES=images)
            with save():
                self.assertEqual(verifier.verify_failure(archive)["original_failed_capture_rows"], 2178)
            for kind in ("cleared_error", "go", "wrong_index"):
                changed_row, changed_report = copy.deepcopy(row), copy.deepcopy(report)
                if kind == "cleared_error":
                    row["pageerrors"] = []
                elif kind == "go":
                    report["decision"] = "go"
                else:
                    report["rows"][2092] = {}
                with save(), self.subTest(kind=kind), self.assertRaises(ValueError):
                    verifier.verify_failure(archive)
                row, report = changed_row, changed_report
                report["rows"][2092] = row

    def test_immutable_failure_bytes_cannot_be_replaced_by_same_name(self):
        with tempfile.TemporaryDirectory(prefix="r21-hash-", dir=HERE) as directory:
            proof = Path(directory) / "proof.json"
            proof.write_text('{"synthetic":true}')
            expected = verifier.sha(proof)
            self.assertEqual(verifier.bound_json(proof, expected), {"synthetic": True})
            proof.write_text('{"synthetic":false}')
            with self.assertRaises(ValueError):
                verifier.bound_json(proof, expected)


def board_fixture(r20_status="pending", target_status="pending"):
    return f"""# Synthetic pure unit board; no completion authority

## VDG-013-R19 Prior recovery
- Status: completed
- Depends on:
- Acceptance: immutable prior history
- Refusal count: 3

## VDG-013-R20 Neural repair
- Status: {r20_status}
- Depends on: VDG-013-R19
- Acceptance: separate exact repair

## VDG-039-R01 Original actual batch
- Status: {target_status}
- Depends on: VDG-013-R20
- Deterministic command: {admission.BATCH_COMMAND}
- Validation: node swissknife/scripts/run-vdg-all-families.mjs --check
- Predicted files: swissknife/test/e2e/families/local-mcp-invoke.spec.ts
- Acceptance: all original acquisition requirements
- Implementation timeout seconds: 46800
- Resource class: cpu-browser
- Attempt count: 7

## VDG-060-R01 Original closeout
- Status: pending
- Depends on: VDG-039-R01
- Acceptance: all six strict GO and aggregate GO
"""


class AdmissionAndFenceTests(unittest.TestCase):
    def test_pending_or_completed_r20_allows_only_one_additive_dependency(self):
        for r20 in ("pending", "completed"):
            original = board_fixture(r20)
            result, before, after = admission.build_admission(original)
            self.assertTrue(result["admitted"])
            self.assertEqual(set(after) - set(before), {"VDG-013-R21"})
            self.assertEqual(after["VDG-013-R21"]["depends_on"], "VDG-013-R20")
            self.assertEqual(after["VDG-013-R21"]["resource_class"], "cpu-small")
            self.assertEqual(after["VDG-013-R21"]["implementation_timeout_seconds"], "1800")
            self.assertEqual(after["VDG-013-R21"]["deterministic_command"], after["VDG-013-R21"]["validation"])
            self.assertTrue(all(before[task]["status"] == after[task]["status"] for task in before))
            self.assertEqual(after["VDG-060-R01"], before["VDG-060-R01"])
            self.assertEqual(after["VDG-039-R01"]["attempt_count"], "7")
            self.assertEqual(after["VDG-039-R01"]["implementation_timeout_seconds"], "46800")
            repeated, _, _ = admission.build_admission(result["todo_text"])
            self.assertFalse(repeated["admitted"])
            self.assertEqual(repeated["todo_text"], result["todo_text"])

    def test_completed_batch_or_unapproved_r20_status_refused(self):
        for status in ("completed", "in_progress", "blocked"):
            with self.subTest(target=status), self.assertRaises(ValueError):
                admission.build_admission(board_fixture(target_status=status))
        for status in ("failed", "blocked", "in_progress"):
            with self.subTest(r20=status), self.assertRaises(ValueError):
                admission.build_admission(board_fixture(r20_status=status))

    def test_changed_original_command_or_cycle_is_rejected(self):
        original = board_fixture()
        with self.assertRaises(ValueError):
            admission.build_admission(original.replace(admission.BATCH_COMMAND, "node swissknife/scripts/other.mjs"))
        with self.assertRaises(ValueError):
            admission.build_admission(original.replace("- Depends on: VDG-013-R19", "- Depends on: VDG-039-R01"))
        with self.assertRaises(ValueError):
            admission.build_admission(original.replace("## VDG-013-R20 Neural repair", "## VDG-013-R99 Missing R20"))

    def test_node_entrypoint_parser_handles_flags_without_accepting_argument_data(self):
        cases = [(["node", "--import", "tsx", "run-vdg-family.mjs"], "run-vdg-family.mjs"),
                 (["nodejs", "--require=preload", "run-vdg-all-families.mjs"], "run-vdg-all-families.mjs"),
                 (["node", "--", "verify-vdg-family.mjs"], "verify-vdg-family.mjs"),
                 (["node", "other.mjs", "run-vdg-family.mjs"], "other.mjs"),
                 (["node", "--eval", "data", "run-vdg-family.mjs"], None),
                 (["python3", "run-vdg-family.mjs"], None)]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                self.assertEqual(admission.node_script(argv), expected)

    def test_owned_stopped_fence_rejects_pid_file_or_hold_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="r21-fence-", dir=HERE) as directory:
            root = Path(directory)
            lane = root / "lanes/vdg-planning"
            lane.mkdir(parents=True)
            (lane / "vdg-planning.resume.lock").touch(mode=0o600)
            status = {"pid": 1000000000, "state": "stopped", "terminal_reason": "resume_stopped"}
            (lane / "vdg_planning_status.json").write_text(json.dumps(status))
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
                hold.write_text(json.dumps({"reason": "unrelated operator hold", "lane_pid": 1000000000}))
                with self.assertRaisesRegex(ValueError, "controlled repair hold"):
                    with admission.lifecycle_fence(root, root):
                        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
