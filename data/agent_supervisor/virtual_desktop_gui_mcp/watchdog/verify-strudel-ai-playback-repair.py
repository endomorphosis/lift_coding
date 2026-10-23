"""Read-only R21 validation. Candidate diagnostics never validate canonical repair.

The canonical preflight pin and final source pins deliberately remain unset
until the operator reviews the actual installed source and Chrome recording.
This proof grants no capture acceptance, task completion or aggregate GO.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / "swissknife"
ARCHIVE = Path(__file__).resolve().parent / "smoke-receipts/strudel-ai-playback"
REVIEWED_PREFLIGHT_SHA256 = '8bb02237dd5bc67ff08e0b5b35113bbae031895b2afa3e79b39a2a8dff5e0975'
APP = "swissknife/web/js/apps/strudel-ai-daw.js"
UNIT = "swissknife/test/scripts/vdg-strudel-ai-playback.test.mjs"
SMOKE = "swissknife/test/e2e/smoke/vdg-strudel-ai-playback-smoke.mjs"
WORKLET = "swissknife/web/js/audio/strudel-processor.js"
MAIN = "swissknife/web/js/main-simple.js"
# Final reviewed r4 bytes. Canonical browser authority still requires its
# separate, deliberately unset preflight pin above.
SOURCES = {
    APP: "71d6ee4eccfcbea029ae9ad56cd450c9603067779e8984d7ea760ed501b6608c",
    UNIT: "5bab4b505ac619b4cd63e020de49a645fb4a4f8df02db4ab94dadd938ae9748b",
    SMOKE: "b958d4dc8357bf3ce1c8bff87050c3fc1698ec9d9084a92dc7fea781cae0b8e9",
    WORKLET: "c403ce40d3b1ae30e2d783c5ef49fcda70ff13fbac7e1d300da5a64823776243",
    MAIN: "b46037cf2eb8b3746db45e13ec07ffbedefa439fc6b0d15f0e16c85277c2c3ef",
}
MINIMUM_TEST_COUNT = 21
FRESH_TEST_COUNT = 38
OLD_APP_SHA256 = "cb3e96a04f718eefac9f7f758462af06640592f24dfc92665249dc0b9907f274"
OLD_REPORT_SHA256 = "ee8add337e23df05f5035216c754e5a81efd2ecea077a13fa0958b90a2d165b7"
OLD_ROW_SHA256 = "75eb615b8b15defee00082e36045452807030c2bc7b979cb07518794dd98de6d"
OLD_FINGERPRINT = "b2ea7be541342f433bc059841a56c6daea51fc7991da69cb9ed4b4aa792c73e8"
BASELINE_SHA256 = "34c7aa1780034a170ff380553db3e291d586444ee7407c356198630b44a075c8"
OLD_IMAGES = {
    "screenshot_before.png": "236d904642cf45e167b7438052c7983b336761b175a4db323d5562cc79ba2ca1",
    "screenshot_after.png": "cfd3da324a6f8177da8903f75807aa517f28f78fa75b4bcdc809b2ae2a882051",
}
TRANSPORTS = ("http", "libp2p")
UNAFFECTED = {f"vdg-{family}/{transport}" for family in ("storage", "datasets", "network", "control") for transport in TRANSPORTS}
ACTIONS = (
    ("play", "#play-btn"), ("pause", "#pause-btn"), ("resume", "#play-btn"), ("stop", "#stop-btn"),
    ("tempo", "#bpm-input"), ("volume", "#master-volume"), ("tap", "#tap-tempo"),
    ("play-for-edit", "#play-btn"), ("live-parameter", '#dynamic-controls input[data-param="gain"]'),
    ("editor", "#strudel-code-editor"),
)
PLAYING = {"play", "resume", "play-for-edit", "live-parameter", "editor"}
STATE_FIELDS = ("playing", "mode", "audio_state", "bpm", "gain", "rms", "worklet", "audio_backend", "reference_frequency",
                "native_oscillator_count", "native_gain_count", "scheduler_active", "scheduled_beats", "audio_cleanup_errors",
                "status", "closed", "frame")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), f"Expected regular proof file: {path}")
    return path


def exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), f"Wrong {label} schema")


def digest(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def no_authority(value):
    for field in ("gui_acceptance", "work_complete", "completion_authority"):
        require(value.get(field) is False, f"Repair proof cannot grant {field}")


def bound_json(path, expected):
    require(digest(expected), "Reviewed proof digest is not pinned")
    require(sha(regular(path)) == expected, f"Reviewed proof bytes changed: {path}")
    return json.loads(path.read_text())


def png(path, expected):
    require(digest(expected) and sha(regular(path)) == expected, f"PNG bytes changed: {path}")
    header = path.read_bytes()[:24]
    require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR"
            and all(value > 0 for value in struct.unpack(">II", header[16:24])), f"Invalid actual PNG: {path}")


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def tap(text, count=None):
    count = FRESH_TEST_COUNT if count is None else count
    require(type(count) is int and count >= MINIMUM_TEST_COUNT, "Final fresh app test count is not pinned")
    for key, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {key} (\d+)$", text, re.M) == [str(expected)], f"Wrong fresh TAP {key}")
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)], "Wrong fresh TAP plan")
    require(len(re.findall(r"^ok \d+ - ", text, re.M)) == count and not re.search(r"^not ok\b", text, re.M),
            "Missing or failed actual test outcomes")


def common_state(state):
    exact(state, STATE_FIELDS, "actual audio state")
    require(type(state["playing"]) is bool and type(state["closed"]) is bool and state["mode"] == "local-preview"
            and state["worklet"] is False, "Actual canonical native-reference mode must remain honest")
    require(number(state["bpm"]) and 20 <= state["bpm"] <= 300 and number(state["gain"]) and 0 <= state["gain"] <= 1
            and number(state["rms"]) and state["rms"] >= 0, "Invalid actual tempo/gain/RMS")
    require(type(state["status"]) is str and type(state["scheduler_active"]) is bool, "Invalid actual status/scheduler")
    require(state["audio_cleanup_errors"] == [], "Actual native audio cleanup failed")
    for key in ("native_oscillator_count", "native_gain_count"):
        require(type(state[key]) is int and state[key] >= 0, "Invalid actual native node count")
    require(state["native_oscillator_count"] == state["native_gain_count"], "Native oscillator/gain ownership differs")
    beats = state["scheduled_beats"]
    require(type(beats) is list, "Actual scheduled beat history required")
    previous = -1
    for beat in beats:
        exact(beat, ("time", "frequency", "bpm"), "actual scheduled native beat")
        require(number(beat["time"]) and beat["time"] >= 0 and beat["time"] > previous and beat["frequency"] == 1000
                and number(beat["bpm"]) and 20 <= beat["bpm"] <= 300, "Actual native beat scheduling differs")
        previous = beat["time"]


def verify_state(state, label, playing=None):
    common_state(state)
    playing = label in PLAYING if playing is None else playing
    require(state["playing"] is playing and state["closed"] is False and state["audio_backend"] == "web-audio-reference",
            f"Wrong actual playback mode/backend: {label}")
    require(state["rms"] > 0.0001 if playing else state["rms"] < 0.000001,
            f"Missing actual {'signal' if playing else 'silence'}: {label}")
    require(state["audio_state"] == "running" if playing else state["audio_state"] in {"running", "suspended"},
            f"Wrong actual AudioContext state: {label}")
    require(state["scheduler_active"] is playing and (state["native_oscillator_count"] >= 1 if playing
            else state["native_oscillator_count"] == 0) and state["reference_frequency"] == (220 if playing else None),
            "Actual reference oscillator/beat scheduler ownership differs")
    require(state["scheduled_beats"] and (not playing or any(beat["bpm"] == state["bpm"] for beat in state["scheduled_beats"])),
            "Actual reference beat history/current BPM missing")
    require(type(state["frame"]) is int and state["frame"] > 0, "Actual mounted visualization frame missing")
    require(re.search(r"metronome/reference tone.*compilation unavailable", state["status"])
            if playing else state["status"] in {"Paused", "Stopped"}, "Playback status must remain truthful")
    if label in {"tempo", "live-tempo"}:
        require(state["bpm"] == 162, "Actual tempo edit did not apply")
    if label == "volume":
        require(abs(state["gain"] - 0.99) < 0.00001, "Actual gain edit did not apply")
    if label == "tap":
        require(60 <= state["bpm"] <= 200, "Actual trusted tap tempo did not apply")


def verify_report(report, archive=ARCHIVE, root=ROOT):
    exact(report, ("schema", "passed", "source_sha256", "canonical_source_sha256", "candidate_module_override", "source_path",
                  "project_root", "profiles", "route_interception", "gui_acceptance", "completion_authority", "work_complete",
                  "owned_resources", "owned_resources_closed", "screenshot_sha256"), "canonical Chrome report")
    no_authority(report)
    require(report["schema"] == "swissknife.vdg-strudel-ai-playback-smoke.v1" and report["passed"] is True,
            "Actual canonical browser recording failed")
    require(report["candidate_module_override"] is False and report["route_interception"] is False,
            "Candidate or intercepted browser recording is not canonical proof")
    require(digest(SOURCES[APP]) and report["source_sha256"] == report["canonical_source_sha256"] == SOURCES[APP]
            and report["source_path"] == str(root / APP) and report["project_root"] == str(root / "swissknife"),
            "Browser recording must use actual canonical app bytes")
    resources = report["owned_resources"]
    exact(resources, ("server_pid", "browser_pid", "server_alive_after_cleanup", "browser_alive_after_cleanup"), "owned resources")
    require(all(type(resources[key]) is int and resources[key] > 0 for key in ("server_pid", "browser_pid"))
            and resources["server_pid"] != resources["browser_pid"], "Missing actual owned process identities")
    require(report["owned_resources_closed"] is True and resources["server_alive_after_cleanup"] is False
            and resources["browser_alive_after_cleanup"] is False, "Owned browser/server cleanup missing")
    profiles = report["profiles"]
    require(type(profiles) is list and len(profiles) == 2
            and [profile.get("transport_profile") for profile in profiles] == list(TRANSPORTS), "Both actual declared profiles required")
    for profile in profiles:
        exact(profile, ("transport_profile", "mounted_without_gesture", "mount_trusted_event_count", "pre_play_state", "cases",
                        "closed_while_playing", "reopened_play_and_cleanup", "actual_factory",
                        "audio_platform_mocked", "actual_signal_and_silence", "module_responses", "page_errors", "posts", "dialogs",
                        "owned_app_resources_closed"), "actual browser profile")
        require(profile["actual_factory"] is True and profile["audio_platform_mocked"] is False
                and profile["actual_signal_and_silence"] is True and profile["reopened_play_and_cleanup"] is True
                and profile["owned_app_resources_closed"] is True, "Missing real mounted audio/reopen behavior")
        require(profile["mounted_without_gesture"] is True and type(profile["mount_trusted_event_count"]) is int
                and profile["mount_trusted_event_count"] == 0, "Actual mount must resolve before any trusted gesture")
        initial = profile["pre_play_state"]
        common_state(initial)
        require(initial["playing"] is False and initial["closed"] is False and initial["rms"] < 0.000001
                and initial["audio_state"] in {"running", "suspended"} and initial["audio_backend"] == "unavailable"
                and initial["reference_frequency"] is None and initial["native_oscillator_count"] == 0
                and initial["scheduler_active"] is False and initial["scheduled_beats"] == []
                and type(initial["frame"]) is int and initial["frame"] > 0
                and re.search(r"metronome/reference tone.*compilation unavailable", initial["status"]),
                "Pre-gesture mount must remain responsive, silent and truthful")
        require(profile["page_errors"] == [] and profile["posts"] == [] and profile["dialogs"] == [],
                "Actual playback must be error-free and local with zero POSTs/dialogs")
        responses = profile["module_responses"]
        require(type(responses) is list and responses and all(type(row) is dict and row == {"status": 200} for row in responses),
                "Actual canonical app module was not loaded successfully")
        cases = profile["cases"]
        require(type(cases) is list and len(cases) == len(ACTIONS), "Missing actual native playback actions")
        for case, (label, selector) in zip(cases, ACTIONS):
            exact(case, ("label", "selector", "trusted_events", "state", "evidence", "passed"), "actual playback action")
            require(case["label"] == label and case["selector"] == selector and case["passed"] is True,
                    "Actual action identity/order mismatch")
            events = case["trusted_events"]
            require(type(events) is list and events, f"No actual trusted event: {label}")
            for event in events:
                exact(event, ("type", "trusted", "id"), "actual native event")
                require(event["type"] in {"click", "input"} and type(event["trusted"]) is bool
                        and (event["id"] is None or type(event["id"]) is str), "Invalid actual event recording")
            wanted_id = selector[1:] if selector.startswith("#") and " " not in selector else ""
            require(any(event["trusted"] is True and event["id"] == wanted_id for event in events),
                    f"Actual trusted control event missing: {label}")
            verify_state(case["state"], label)
            if label == "tempo":
                exact(case["evidence"], ("live_tempo_state",), "actual live tempo evidence")
                live_tempo = case["evidence"]["live_tempo_state"]
                verify_state(live_tempo, "live-tempo", playing=True)
                beats = live_tempo["scheduled_beats"]
                require(any(left["bpm"] == right["bpm"] == 162 and abs(right["time"] - left["time"] - 60 / 162) < 0.00001
                            for left, right in zip(beats, beats[1:])), "Actual native162 BPM scheduling interval missing")
                require(all(any(event["trusted"] is True and event["id"] == control for event in events)
                            for control in ("play-btn", "stop-btn")), "Live tempo proof lacks actual trusted Play/Stop")
            else:
                require(case["evidence"] is None, "Unexpected unreviewed action evidence")
        closed = profile["closed_while_playing"]
        common_state(closed)
        # Analyser buffers can retain their last historical samples after the
        # graph closes; the actual closed AudioContext is the teardown proof.
        require(closed["playing"] is False and closed["closed"] is True and closed["audio_state"] == "closed"
                and closed["frame"] is None and closed["audio_backend"] == "web-audio-reference"
                and closed["reference_frequency"] is None and closed["native_oscillator_count"] == 0
                and closed["scheduler_active"] is False,
                "Closing the actual playing window must silence/close its audio graph")
    expected_pngs = {f"{transport}-{label}-{position}.png" for transport in TRANSPORTS for label, _ in ACTIONS for position in ("before", "after")}
    hashes = report["screenshot_sha256"]
    require(type(hashes) is dict and set(hashes) == expected_pngs, "Actual before/after screenshot set differs")
    directory = archive / "canonical"
    require({p.name for p in directory.glob("*.png")} == expected_pngs, "Actual screenshot directory differs")
    for name, expected in hashes.items():
        png(directory / name, expected)
    return {"actual_profiles": 2, "actual_actions": 20, "actual_pngs": 40, "actual_posts": 0}


def verify_failure(archive=ARCHIVE):
    directory = archive / "actual-failure"
    require(sha(regular(directory / "original-app.js")) == OLD_APP_SHA256, "Original failed app bytes changed")
    report = bound_json(directory / "local-http-1792643190016.json", OLD_REPORT_SHA256)
    row = bound_json(directory / "failed-row.json", OLD_ROW_SHA256)
    require(report["schema"] == "swissknife.virtual-desktop-live-click.v1" and report["target"] == "local"
            and report["row_count"] == len(report["rows"]) == 2178 and report["decision"] == "no_go"
            and report["rows"][2092] == row, "Original complete failed Local report differs")
    require(row["app_id"] == row["launch_id"] == "strudel-ai-daw" and row["selector"] == "#play-btn"
            and row["clicked"] is True and row["failure_reasons"] == ["pageerror"]
            and row["pageerrors"] == ["TypeError: this.strudelEngine.stop is not a function"]
            and row["mcp_call_count"] == row["incomplete_mcp_call_count"] == 0
            and row["observations"] == [] and row["observation"] is None, "Original actual failure was changed or cleared")
    for name, expected in OLD_IMAGES.items():
        png(directory / name, expected)
    return {"original_failed_capture_rows": 2178, "original_failure_row": 2092, "original_failure_pngs": 2}


def verify_preservation(record, live, baseline):
    exact(record, ("schema", "before_app_sha256", "after_app_sha256", "cells", "gui_acceptance", "work_complete", "completion_authority"), "preservation receipt")
    no_authority(record)
    require(record["schema"] == "swissknife.vdg-strudel-ai-preservation.v2" and record["before_app_sha256"] == OLD_APP_SHA256
            and record["after_app_sha256"] == SOURCES[APP], "Wrong actual source boundary")
    require(type(record["cells"]) is dict and set(record["cells"]) == set(baseline["cells"]) == UNAFFECTED
            and set(live["fingerprints"]) == set(live["acquisitions"]) == UNAFFECTED,
            "Exactly eight unaffected Storage/Dataset/Network/Control cells are required")
    require(live["inventory"]["current"] is True, "Actual current inventory required")
    for cell, row in record["cells"].items():
        exact(row, ("before_input_fingerprint", "after_input_fingerprint", "run_id", "report_sha256"), "preserved cell")
        before, actual = baseline["cells"][cell], live["acquisitions"][cell]
        require(row["before_input_fingerprint"] == before["input_fingerprint"] == row["after_input_fingerprint"]
                == live["fingerprints"][cell] == actual["input_fingerprint"], f"Unaffected source fingerprint changed: {cell}")
        require(row["run_id"] == before["run_id"] == actual["run_id"] and row["report_sha256"]
                == before["report_sha256"] == actual["report_sha256"] and actual["capture_complete"] is True
                and actual["row_count"] == before["row_count"], f"Unaffected completed capture changed: {cell}")


def live_evidence():
    code = '''
const fs=require('node:fs'),path=require('node:path');
const {inspectInventory}=require('./scripts/vdg-inventory-contract.cjs');
const {checkCapture}=require('./scripts/check-vdg-capture.cjs');
const {FAMILIES}=require('./scripts/vdg-evidence.cjs');
const {captureInputFingerprint}=require('./scripts/vdg-capture-fingerprint.cjs');
const root=process.cwd(),evidence=path.join(root,'test-results/virtual-desktop-ipfs-mcp-orb');
const inventory=inspectInventory({sourceRoot:root,evidenceRoot:evidence});
if(inventory.current!==true)throw Error('Current actual inventory required: '+inventory.reason);
const fingerprints={},acquisitions={};
for(const family of ['vdg-storage','vdg-datasets','vdg-network','vdg-control'])for(const transport of ['http','libp2p']){
 const key=family+'/'+transport;
 fingerprints[key]=captureInputFingerprint(family,transport,{sourceRoot:root,evidenceRoot:evidence,definition:FAMILIES[family]});
 acquisitions[key]=checkCapture(family,transport,{sourceRoot:root,evidenceRoot:evidence});
}
console.log(JSON.stringify({inventory,fingerprints,acquisitions}));
'''
    process = subprocess.run(["node", "--input-type=commonjs", "-e", code], cwd=SWISS, capture_output=True, text=True, timeout=120)
    require(process.returncode == 0, f"Read-only current inventory/capture check failed: {process.stderr[-4000:]}")
    return json.loads(process.stdout)


def verify_ready_proof():
    receipt = bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    exact(receipt, ("schema", "source_sha256", "canonical_report_sha256", "preservation_sha256", "baseline_sha256",
                    "gui_acceptance", "work_complete", "completion_authority"), "reviewed canonical preflight")
    no_authority(receipt)
    require(receipt["schema"] == "swissknife.vdg-strudel-ai-canonical-preflight.v1" and receipt["source_sha256"] == SOURCES
            and all(digest(value) for value in SOURCES.values())
            and type(FRESH_TEST_COUNT) is int and FRESH_TEST_COUNT >= MINIMUM_TEST_COUNT, "Final canonical source/count pins required")
    def sources():
        for name, expected in SOURCES.items():
            require(sha(regular(ROOT / name)) == expected, f"Reviewed canonical source changed: {name}")
    sources()
    failure = verify_failure()
    report = bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"])
    browser = verify_report(report)
    baseline = bound_json(ARCHIVE / "unaffected-eight-before.json", receipt["baseline_sha256"])
    require(receipt["baseline_sha256"] == BASELINE_SHA256, "Authoritative eight-cell baseline is not the reviewed original")
    no_authority(baseline)
    old = baseline["local_http"]
    require(old["input_fingerprint"] == OLD_FINGERPRINT and old["report_sha256"] == OLD_REPORT_SHA256
            and old["row_count"] == 2178 and old["capture_complete"] is True and old["acceptance_decision"] == "no_go"
            and baseline["strudel_ai_source_before"] == OLD_APP_SHA256, "Original failed source/capture boundary changed")
    require(sha(regular(Path(__file__).resolve().parent / "smoke-receipts/neural-history/unaffected-eight-before.json"))
            == receipt["baseline_sha256"], "Authoritative pre-repair eight-cell baseline differs")
    preservation = bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    live = live_evidence()
    verify_preservation(preservation, live, baseline)
    process = subprocess.run(["node", "--test", "--test-reporter=tap", "test/scripts/vdg-strudel-ai-playback.test.mjs"],
                             cwd=SWISS, capture_output=True, text=True, timeout=120)
    print(process.stdout, end="")
    require(process.returncode == 0, f"Fresh{FRESH_TEST_COUNT} actual app tests failed: {process.stderr}")
    tap(process.stdout)
    sources()
    bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    require(verify_report(bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"])) == browser,
            "Browser proof changed during fresh units")
    require(verify_failure() == failure, "Immutable actual failure proof changed")
    require(bound_json(ARCHIVE / "unaffected-eight-before.json", receipt["baseline_sha256"]) == baseline,
            "Archived pre-repair baseline changed")
    require(sha(regular(Path(__file__).resolve().parent / "smoke-receipts/neural-history/unaffected-eight-before.json"))
            == BASELINE_SHA256, "Authoritative pre-repair baseline changed during fresh units")
    bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    require(live_evidence() == live, "Inventory/acquisition source binding changed during fresh units")
    return {"repair_validated": True, "canonical_product_preflight_validated": True, "fresh_tests": FRESH_TEST_COUNT,
            **browser, **failure, "unaffected_cells_preserved": 8,
            "all_12_acquisitions_and_six_strict_go_gates_still_required": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


if __name__ == "__main__":
    print(json.dumps(verify_ready_proof(), sort_keys=True))
