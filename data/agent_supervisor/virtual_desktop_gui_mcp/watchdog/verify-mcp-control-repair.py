"""Read-only R18 verification of the actual Control repair; no GUI authority."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / "swissknife"
WATCHDOG = Path(__file__).resolve().parent
ARCHIVE = WATCHDOG / "smoke-receipts/mcp-control-native"
GUARD_ARCHIVE = WATCHDOG / "smoke-receipts/control-primary-mount"
PREFLIGHT_SHA256 = "259d457f8341b544a8d8a68c6dc38fb5f04bb260b6d9ab160b934cb8adf31439"
GUARD_PREFLIGHT_SHA256 = "059c4c862667677ff7e4b0a7cc119c6ada0b418f605dfc33c58d942adb1a0ac7"
GUARD_TAP_SHA256 = "3be8a2e20359d67ac2756c0ca89058dc9201c694ebf341f59f815a64a14ea20d"
SOURCES = {
    "swissknife/web/js/apps/mcp-control.js": "1de745cae633055bcde7424b6163ac9040da251c5c66b0138da58190316ef5b2",
    "swissknife/test/scripts/vdg-mcp-control-mounted.test.mjs": "8f5d6ad02689020c86258e873b47dc9b0e2f662788497169a31bee45b8593940",
    "swissknife/test/e2e/smoke/vdg-mcp-control-mounted-smoke.mjs": "4dd9d1af6aad7e6e7f11712f3c96af5450b68cfbbbb09fc276fb301e2c94436f",
    "swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts": "9003c79c2d7844dec7de6951f43c6dc3537fd00ec61ea66de7216935bc2915b9",
}
GUARD_SOURCES = {
    "swissknife/scripts/build-family-mcp-spec.cjs": "dcdaa5d0772d5455b4b1a55f6725637635d78275972e5f1be139921e0287f5a1",
    "swissknife/scripts/vdg-control-primary-mount.test.mjs": "b07c9c122440ad0c73ef8f05e261de77de921e2a6acd0198f7ba10e763992b09",
    "swissknife/scripts/vdg-local-todo-isolation.test.mjs": "6a4f2bb2a92244ac605d170f57940927baa34e07347a1535d2051fae017fb0e8",
    "swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts": SOURCES["swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts"],
    "swissknife/test/e2e/families/local-negative-mcp.spec.ts": "65624bd17b6a0ceb8e0c9493da2da2f6790ce688f6cbc22d433b1d1d225975d3",
    "swissknife/test/e2e/families/storage-media-mcp-invoke.spec.ts": "8ad032f8c3a617c126251f0e2ac811d3bfa63360c5f6ddac6bd7d92f28a7b488",
    "swissknife/test/e2e/families/datasets-mcp-invoke.spec.ts": "55da13746d6c2f2c7a7ee31c8ef1bc21b39092a3658349373282f138cb8a2884",
    "swissknife/test/e2e/families/accelerate-mcp-invoke.spec.ts": "ecf28a3b776300d73a043fc2bed4b5e6061e52027416f8c3dea7364a54953d69",
    "swissknife/test/e2e/families/network-mcp-invoke.spec.ts": "231958bfb29e99adc9965196ff34623addcf2d012f3731eb024a4ccd7d9ebbaa",
}
R15_DRIVER = WATCHDOG / "verify-openrouter-case-cost-diagnostic.py"
R15_SHA256 = "2b0d44fa13deef26e5ae77ca8ab265be83c561f1badfb47e6a979b631348a082"
MODALS = ("templates-modal", "add-server-modal", "add-remote-modal", "discovery-modal", "metrics-modal")
APP_SHA = SOURCES["swissknife/web/js/apps/mcp-control.js"]
GUARD_SHA = SOURCES["swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts"]
BEFORE_SOURCE_SHA = "3040a8cdbf73e52ecdb2425ed5d81c1606a937972655a32ea61d880a2253eb40"
MODAL_SOURCE_SHA = "5c4cd16ce3c91fd8cd1b2acd4923e7a751239c8e3db595c72562a0fe07036cec"
MODAL_ARTIFACT_MAP_SHA = "0de760e0a25be5ce680dcfe0bde4c7b2faada6cc0bc8c9ee4a602963b8162ed2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def regular(file):
    require(file.is_file() and not file.is_symlink(), f"Expected regular proof file: {file}")
    return file


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), f"Wrong {label} schema")


def integer(value, key, expected):
    require(type(value.get(key)) is int and value[key] == expected, f"Invalid {key}")


def no_authority(value):
    for field in ("gui_acceptance", "work_complete", "completion_authority"):
        require(value.get(field) is False, f"Diagnostic cannot grant {field}")


def load_bound(file, digest):
    require(sha(regular(file)) == digest, f"Reviewed proof bytes changed: {file}")
    return json.loads(file.read_text())


def png(file, digest):
    require(sha(regular(file)) == digest, f"PNG bytes changed: {file}")
    header = file.read_bytes()[:24]
    require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR"
            and all(size > 0 for size in struct.unpack(">II", header[16:24])), f"Invalid actual PNG: {file}")


def tap(text, count):
    for name, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {name} (\d+)$", text, re.M) == [str(expected)], f"Wrong fresh TAP {name}")
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)], "Wrong fresh TAP plan")
    require(len(re.findall(r"^ok \d+ - ", text, re.M)) == count and not re.search(r"^not ok\b", text, re.M),
            "Missing or failed actual test outcomes")


def screenshot_reference(value, diagnostics, basename):
    require(type(value) is str and Path(value).parent == Path(diagnostics) and Path(value).name == basename,
            "Original browser screenshot provenance mismatch")


def verify_profile(report, transport):
    keys(report, ("diagnostics", "transport", "source_sha256", "guard_source_sha256", "cases", "module_responses",
        "page_errors", "posts", "gui_acceptance", "work_complete", "completion_authority", "initial_state",
        "initial_visible_primary_controls", "initial_screenshot", "guard_checked_launches", "passed", "owned_resources_closed"), "browser profile")
    no_authority(report)
    require(report["passed"] is True and report["owned_resources_closed"] is True, "Incomplete actual browser profile")
    require(report["transport"] == transport and report["source_sha256"] == APP_SHA
            and report["guard_source_sha256"] == GUARD_SHA, "Browser source/transport mismatch")
    require(report["posts"] == [] and report["page_errors"] == [], "Browser POST or page error")
    integer(report, "guard_checked_launches", 7)
    require(report["module_responses"] == [{"path": "/js/apps/mcp-control.js", "status": 200}], "Real module did not load cleanly")
    initial = report["initial_state"]
    keys(initial, ("host_records", "remote_records", "connected_remotes", "libp2p_status_available", "libp2p_error"), "initial browser state")
    for field in ("host_records", "remote_records", "connected_remotes"):
        integer(initial, field, 0)
    require(initial["libp2p_status_available"] is True and initial["libp2p_error"] is None, "Browser status was unavailable")
    controls = report["initial_visible_primary_controls"]
    require(type(controls) is list and len(controls) == 14, "Missing real primary app controls")
    for control in controls:
        keys(control, ("tag", "id", "text"), "visible primary control")
        require(control["tag"] in ("BUTTON", "INPUT", "SELECT") and type(control["text"]) is str and control["text"], "Invalid primary control")
    require({(row["tag"], row["id"]) for row in controls if row["id"]} == {
        ("INPUT", "server-search"), ("SELECT", "status-filter"), ("SELECT", "type-filter")}, "Actual input/filter controls missing")
    require([row["text"] for row in controls[:7]] == ["🔄 Refresh", "📋 Templates", "🖥️ Add Host Daemon",
        "🌐 Add Browser Remote", "🔍 Discovery", "📊 Metrics", "🔄 libp2p"], "Primary app action controls differ")
    cases = report["cases"]
    require(type(cases) is list and len(cases) == 14, "Incomplete actual browser cases")
    require(cases[0] == {"action": "refresh server records", "trusted_click": True} and cases[0]["trusted_click"] is True,
            "Real records refresh was not clicked")
    for index, modal in enumerate(MODALS, 1):
        row = cases[index]
        keys(row, ("action", "trusted_open_and_close", "screenshot"), "actual modal action")
        require(row["action"] == modal and row["trusted_open_and_close"] is True, f"Modal was not actually exercised: {modal}")
        screenshot_reference(row["screenshot"], report["diagnostics"], f"{modal}.png")
    require(cases[6] == {"action": "refresh libp2p status", "trusted_click": True}
            and cases[6]["trusted_click"] is True
            and cases[7] == {"action": "own search and filter inputs", "actual_input_events": True}
            and cases[7]["actual_input_events"] is True, "Missing actual local read/filter actions")
    for index, modal in enumerate(MODALS, 8):
        row = cases[index]
        keys(row, ("action", "trusted_close", "dialog_removed", "next_factory_mount_usable"), "owning modal close")
        require(row["action"] == f"trusted titlebar Close while {modal} remains open", "Wrong owning dialog close sequence")
        require(all(row[field] is True for field in ("trusted_close", "dialog_removed", "next_factory_mount_usable")),
                f"Actual trusted Close/reopen/cleanup failed for {modal}")
    require(cases[13] == {"action": "trusted close and reopen actual factory", "passed": True} and cases[13]["passed"] is True,
            "Final factory reopen failed")
    screenshot_reference(report["initial_screenshot"], report["diagnostics"], "actual-mounted.png")


def verify_recordings(archive=ARCHIVE, guard_archive=GUARD_ARCHIVE):
    receipt = load_bound(archive / "preflight.json", PREFLIGHT_SHA256)
    require(receipt["schema"] == "swissknife.vdg.mcp-control-repair-preflight.v1", "Wrong repair preflight schema")
    no_authority(receipt)
    require(receipt["source_hashes"] == SOURCES, "Unexpected app repair source scope")
    for name, digest in SOURCES.items():
        require(sha(regular(ROOT / name)) == sha(regular(archive / "frozen-source" / name)) == digest, f"App proof is stale: {name}")
    tests = receipt["tests"]
    require(tests["cwd"] == str(SWISS) and tests["argv"] == ["node", "--test", "test/scripts/vdg-mcp-control-mounted.test.mjs"], "Wrong recorded app test command")
    for field, value in (("exit_code", 0), ("passed", 8), ("failed", 0)):
        integer(tests, field, value)
    require(type(tests["duration_ms"]) in (int, float) and math.isfinite(tests["duration_ms"]) and tests["duration_ms"] > 0, "Invalid actual app test duration")
    before = receipt["before"]
    require(before["artifact_dir"] == "before" and before["result_json"] == "before/result.json"
            and before["source_sha256"] == BEFORE_SOURCE_SHA and before["v8_parse"] is False and before["acorn_parse"] is False,
            "Original unparseable module failure is missing")
    integer(before, "module_status", 500)
    require(before["confirmed_fallback"] is True and before["actual_instance_exists"] is False, "Original generic fallback was not diagnosed")
    integer(before, "generic_gateway_controls", 3); integer(before, "posts", 0)
    original = load_bound(archive / before["result_json"], before["result_sha256"])
    no_authority(original)
    require(original["source_sha256"] == BEFORE_SOURCE_SHA and original["confirmed_fallback"] is True
            and original["actual_instance_exists"] is False and original["owned_resources_closed"] is True,
            "Original browser failure provenance changed")
    require(original["module_responses"] == [{"status": 500, "path": "/js/apps/mcp-control.js"}]
            and original["posts"] == [] and original["page_errors"] == [], "Wrong actual original module response")
    integer(original, "error_app_count", 1); integer(original, "real_server_list_count", 0); integer(original, "generic_gateway_controls", 3)
    require("App Load Error" in original["window_text"], "Original primary app error absent")
    require(sha(regular(archive / "before/mcp-control.js")) == BEFORE_SOURCE_SHA, "Original failed module bytes changed")
    require(before["screenshot"] == "before/mcp-control-before.png", "Wrong original failure screenshot")
    png(archive / before["screenshot"], before["screenshot_sha256"])
    modal = receipt["additional_actual_modal_failure"]
    require(modal["artifact_dir"] == "modal-interception-before-fix" and modal["result_json"] == "modal-interception-before-fix/result.json"
            and modal["source_sha256"] == MODAL_SOURCE_SHA and modal["trusted_titlebar_close_blocked"] is True
            and modal["intercepting_node"] == "div#templates-modal.modal", "Actual modal interception failure missing")
    failure = load_bound(archive / modal["result_json"], modal["result_sha256"])
    no_authority(failure)
    require(failure["passed"] is False and failure["owned_resources_closed"] is True and failure["source_sha256"] == MODAL_SOURCE_SHA
            and failure["posts"] == [] and failure["page_errors"] == [], "Wrong modal failure provenance")
    require(failure["pending_case"] == "trusted titlebar Close while templates-modal remains open"
            and "intercepts pointer events" in failure["error"] and 'id="templates-modal"' in failure["error"], "Wrong actual pointer interception error")
    artifact_map = load_bound(archive / "modal-interception-before-fix/artifact-sha256.json", MODAL_ARTIFACT_MAP_SHA)
    require(artifact_map["exact_source_sha256"] == MODAL_SOURCE_SHA, "Wrong failed-modal source snapshot")
    failure_pngs = 0
    for name, digest in artifact_map["files"].items():
        require(Path(name).name == name and name not in (".", ".."), "Unsafe failed-modal artifact name")
        file = archive / "modal-interception-before-fix" / name
        require(sha(regular(file)) == digest, f"Failed-modal artifact changed: {name}")
        if name.endswith(".png"):
            png(file, digest); failure_pngs += 1
    require(failure_pngs == 8, "Missing actual failed-modal PNGs")
    require(modal["screenshot"] == "modal-interception-before-fix/failure.png", "Wrong modal failure screenshot")
    png(archive / modal["screenshot"], modal["screenshot_sha256"])
    require(set(receipt["profiles"]) == {"http", "libp2p"}, "Both actual guarded profiles are required")
    for transport, summary in receipt["profiles"].items():
        directory = f"after-{transport}"
        require(summary["artifact_dir"] == directory and summary["result_json"] == f"{directory}/result.json", "Unsafe profile artifact path")
        require(summary["source_sha256"] == APP_SHA and summary["guard_source_sha256"] == GUARD_SHA, "Wrong actual profile sources")
        for field, value in (("guard_checked_launches", 7), ("case_count", 14), ("primary_root_count", 1), ("app_error_count", 0),
                             ("posts", 0), ("page_errors", 0), ("observed_initial_primary_control_count", 14)):
            integer(summary, field, value)
        require(all(summary[field] is True for field in ("passed", "actual_instance_exists", "owned_resources_closed"))
                and summary["route_interception"] is False and summary["metrics_success_rate"] == "Not measured", "Actual primary app/metric proof missing")
        verify_profile(load_bound(archive / summary["result_json"], summary["result_sha256"]), transport)
        expected = {f"{directory}/actual-mounted.png", *(f"{directory}/{modal}.png" for modal in MODALS),
                    *(f"{directory}/{modal}-before-owning-close.png" for modal in MODALS)}
        require(set(summary["screenshot_sha256"]) == expected, "Missing actual repaired modal screenshot pair")
        require({str(file.relative_to(archive)) for file in (archive / directory).glob("*.png")} == expected, "Unexpected actual repaired profile screenshot set")
        for name, digest in summary["screenshot_sha256"].items():
            png(archive / name, digest)
    require(receipt["inventory"] == {"historical_mcp_control_rows": 8, "actual_primary_control_count_per_profile": 14,
        "fresh_inventory_required": True, "fresh_control_http_and_libp2p_acquisitions_required": True}, "Product diagnostic cannot replace fresh acquisition")
    no_authority(receipt["scope"])
    require(receipt["scope"]["source_frozen"] is True and receipt["scope"]["owner_services_modified"] is False
            and receipt["scope"]["shared_harness_fingerprint_bootstrap_board_modified"] is False, "Repair scope changed")
    guard = load_bound(guard_archive / "preflight.json", GUARD_PREFLIGHT_SHA256)
    require(guard["schema"] == "swissknife.vdg-control-primary-mount-preflight.v1" and guard["source_sha256"] == GUARD_SOURCES,
            "Guard proof source scope mismatch")
    require(guard["passed"] is True and guard["local_spec_unchanged"] is True and guard["work_complete"] is False
            and guard["completion_authority"] is False, "Guard tests do not grant GUI authority")
    require(guard["counts"] == {"tests": 21, "pass": 21, "fail": 0, "cancelled": 0, "skipped": 0}, "Wrong recorded guard test outcomes")
    for name, digest in GUARD_SOURCES.items():
        require(sha(regular(ROOT / name)) == digest, f"Guard/generator/family source changed: {name}")
    require(sha(regular(guard_archive / "tests.tap")) == guard["test_output"]["sha256"] == GUARD_TAP_SHA256, "Guard TAP bytes changed")
    tap((guard_archive / "tests.tap").read_text(), 21)
    return {"actual_profiles": 2, "actual_cases": 28, "owning_dialog_close_reopen_cases": 10,
            "actual_guarded_mounts": 14, "png_hashes_verified": 31}


def main():
    result = verify_recordings()
    scope = {**SOURCES, **GUARD_SOURCES, str(R15_DRIVER.relative_to(ROOT)): R15_SHA256}
    for name, digest in scope.items():
        require(sha(regular(ROOT / name)) == digest, f"Reviewed source changed: {name}")
    parse = subprocess.run(["node", "--experimental-vm-modules", "--input-type=commonjs", "-e",
        'const fs=require("node:fs"),vm=require("node:vm");new vm.SourceTextModule(fs.readFileSync(process.argv[1],"utf8"));',
        str(ARCHIVE / "before/mcp-control.js")], cwd=SWISS, capture_output=True, text=True, timeout=15)
    require(parse.returncode != 0 and "Unexpected token 'const'" in parse.stderr, "Archived original parse failure no longer reproduces")
    command = ["node", "--test", "--test-reporter=tap", "test/scripts/vdg-mcp-control-mounted.test.mjs",
               "scripts/vdg-control-primary-mount.test.mjs", "scripts/vdg-local-todo-isolation.test.mjs"]
    fresh = subprocess.run(command, cwd=SWISS, capture_output=True, text=True, timeout=120)
    print(fresh.stdout, end="")
    require(fresh.returncode == 0, f"Fresh Control/guard/Todo tests failed: {fresh.stderr}")
    tap(fresh.stdout, 29)
    environment = dict(os.environ, PYTHONOPTIMIZE="0", PYTHONDONTWRITEBYTECODE="1", IPFS_TEST_PROOF_REUSE_MODE="off")
    diagnostic = subprocess.run([sys.executable, "-B", str(R15_DRIVER)], cwd=ROOT, env=environment,
                                capture_output=True, text=True, timeout=120)
    print(diagnostic.stdout, end="")
    require(diagnostic.returncode == 0, f"Amended R15 historical diagnostic failed: {diagnostic.stderr}")
    r15 = json.loads(diagnostic.stdout.splitlines()[-1])
    no_authority(r15)
    require(r15["diagnostic_validated"] is True and r15["decision"] == "rollback_optional_isolation"
            and r15["actual_cases"] == 48 and r15["png_hashes_verified"] == 96
            and r15["historical_rollback_sources_verified"] is True and r15["canonical_local_sources_restored"] is True
            and r15["current_all_family_generation_parity_verified"] is True, "R15 diagnostic or current generation parity failed")
    require(verify_recordings() == result, "Actual proof changed during fresh tests")
    require(all(sha(ROOT / name) == digest for name, digest in scope.items()), "Source changed during fresh tests")
    result.update({"repair_validated": True, "fresh_app_tests": 8, "fresh_guard_tests": 13, "fresh_todo_generation_tests": 8,
                   "amended_r15_diagnostic_validated": True, "source_hashes": scope,
                   "posts": 0, "page_errors": [], "owned_resources_closed": True,
                   "fresh_inventory_and_control_acquisitions_required": True,
                   "gui_acceptance": False, "work_complete": False, "completion_authority": False})
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
