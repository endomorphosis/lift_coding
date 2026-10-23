"""Read-only R17 product-repair verification; grants no GUI completion authority."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / "swissknife"
ARCHIVE = Path(__file__).resolve().parent / "smoke-receipts/strudel-controls"
SOURCES = {
    "swissknife/web/js/apps/strudel-grandma.js": "c4da0e4efcb88b5f4c4a4d10c2ff3d31d3ee0d20db1786bd49959818a87dd5a6",
    "swissknife/test/scripts/vdg-strudel-grandma-controls.test.mjs": "0feac593251820971ecc7970a96447b37a72ca8a97871c97f353d83f7c171aa8",
    "swissknife/test/e2e/smoke/vdg-strudel-grandma-controls-smoke.mjs": "a354b48aece09d038165210e63d884d4ceb6e7c249d0d5ee30c17502d44adcb8",
}
BINDING_TEST = "swissknife/test/scripts/vdg-strudel-source-binding.test.mjs"
BINDING_TEST_SHA256 = "7a085394d1e7751c797b667d932b9d30785ad408ad67d46d9fe4a64bab84b796"
PREFLIGHT_SHA256 = "798a2b61c15c8bc0efe1e66397bec6ecb1266f8c12a2600c1c7a60a7db026a26"
REPORT_SHA256 = "a88dc22f830514660f211a526625d4551881aa1a81544ab5b6cbe9f4dd94dbd7"
UNIT_LOG_SHA256 = "3f5b58f68916046277d779f81c0b30daa325adffc13447f31cb902b3c20d83cf"
# This is the original matrix exercised by the diagnostic, not a demand that
# a later refreshed global inventory retain unrelated rows or metadata bytes.
ORIGINAL_MATRIX_SHA256 = "915c3a049c61dad3c8ef444e755c5b25bc79488b8368e2a3d31c9678345d8243"
BASE = ":scope > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(1)"
SONGS = BASE + " > main:nth-of-type(1) > section:nth-of-type(1) > div:nth-of-type(1)"
TUTORIAL = BASE + " > footer:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(1)"
SELECTORS = [
    "#help-btn",
    SONGS + " > div:nth-of-type(1) > button:nth-of-type(1)",
    SONGS + " > div:nth-of-type(2) > button:nth-of-type(1)",
    "#play-button", "#stop-button", "#volume-down", "#volume-slider", "#volume-up",
    'button[aria-label="Load Strudel session and sample CIDs"]',
    'button[aria-label="Inspect Strudel pattern context"]',
    'button[aria-label="Request optional Strudel assistance"]',
    'button[aria-label="Simulate Strudel compile error"]',
    'button[aria-label="Simulate Strudel audio backend error"]',
    'button[aria-label="Restore Strudel session"]',
    TUTORIAL + " > button:nth-of-type(1)", TUTORIAL + " > button:nth-of-type(2)",
    ".window-control.maximize", ".window-control.minimize", ".window-control.close",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular_file(path):
    require(not path.is_symlink() and path.is_file(), f"Expected regular file: {path}")
    return path


def exact_keys(record, keys, label):
    require(type(record) is dict and set(record) == set(keys), f"{label}: unexpected schema fields")


def integer(record, key, expected):
    require(type(record.get(key)) is int and record[key] == expected, f"Invalid {key}")


def no_completion_authority(record):
    for key in ("gui_acceptance", "work_complete", "completion_authority"):
        require(record.get(key) is False, f"Diagnostic must not claim {key}")


def check_tap(text, count):
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)], "Wrong TAP plan")
    for key, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {key} (\d+)$", text, re.M) == [str(expected)], f"Wrong TAP {key}")
    require(not re.search(r"^not ok\b", text, re.M), "TAP contains a failed test")
    require(len(re.findall(r"^ok \d+ - ", text, re.M)) == count, "Missing actual TAP test outcomes")


def verify_report(report):
    exact_keys(report, ("passed", "original_controls", "original_control_count", "creation_edit_apply_play_stop_return_verified",
        "invalid_edit_preserves_last_valid_melody", "actual_web_audio", "late_tutorial_cleanup_verified",
        "repeated_mount_verified", "mcp_provider_posts", "page_errors", "cancelled_backend_confirmations",
        "matrix_sha256", "source_sha256", "gui_acceptance", "work_complete", "completion_authority", "owned_resources_closed"), "Browser report")
    no_completion_authority(report)
    for key in ("passed", "creation_edit_apply_play_stop_return_verified", "invalid_edit_preserves_last_valid_melody",
                "late_tutorial_cleanup_verified", "repeated_mount_verified", "owned_resources_closed"):
        require(report[key] is True, f"Browser proof missing {key}")
    integer(report, "original_control_count", 19)
    integer(report, "mcp_provider_posts", 0)
    require(report["page_errors"] == [], "Browser page errors")
    require(report["source_sha256"] == SOURCES["swissknife/web/js/apps/strudel-grandma.js"], "Browser app source changed")
    require(report["matrix_sha256"] == ORIGINAL_MATRIX_SHA256, "Browser original matrix provenance mismatch")
    controls = report["original_controls"]
    require(type(controls) is list and len(controls) == 19, "Missing original controls")
    for row, selector in zip(controls, SELECTORS):
        exact_keys(row, ("selector", "trusted_click", "precondition", "passed"), "Original control")
        require(row["selector"] == selector and row["trusted_click"] is True and row["passed"] is True,
                f"Original selector lacks its trusted successful click: {selector}")
        precondition = {"#play-button": "local creation selected",
                        "#stop-button": "local creation selected; real playback started"}.get(selector, "fresh actual app")
        require(row["precondition"] == precondition, f"Wrong actual control precondition: {selector}")
    audio = report["actual_web_audio"]
    exact_keys(audio, ("state", "playing", "frequencies"), "Actual audio")
    require(audio["state"] == "running" and audio["playing"] is True, "Real WebAudio was not playing")
    frequencies = audio["frequencies"]
    require(type(frequencies) is list and len(frequencies) == 3, "Wrong edited melody length")
    for actual, expected in zip(frequencies, (261.63 / 16, 311.13, 392)):
        require(type(actual) in (int, float) and math.isfinite(actual) and abs(actual - expected) < 0.001,
                "Actual audio does not contain the edited C0/Eb4/G4 melody")
    require(report["cancelled_backend_confirmations"] == [{"type": "confirm", "dismissed": True}] * 2,
            "The two backend persistence prompts were not explicitly cancelled")


def verify_recordings(archive=ARCHIVE):
    preflight_path = regular_file(archive / "preflight.json")
    require(sha(preflight_path) == PREFLIGHT_SHA256, "Reviewed preflight bytes changed")
    receipt = json.loads(preflight_path.read_text())
    exact_keys(receipt, ("schema", "recorded_at", "passed", "source_hashes", "unit_tests", "browser", "scope",
                         "gui_acceptance", "work_complete", "completion_authority"), "Preflight")
    require(receipt["schema"] == "swissknife.vdg-strudel-controls-preflight.v1", "Wrong preflight schema")
    require(receipt["passed"] is True and type(receipt["scope"]) is str and "not canonical VDG capture" in receipt["scope"],
            "Wrong diagnostic scope")
    no_completion_authority(receipt)
    require(receipt["source_hashes"] == SOURCES, "Unexpected reviewed source scope")
    for name, digest in SOURCES.items():
        require(sha(regular_file(ROOT / name)) == digest, f"Source no longer matches the actual browser proof: {name}")
    unit = receipt["unit_tests"]
    exact_keys(unit, ("command", "cwd", "exit_code", "tests", "passed", "failed", "log", "log_sha256"), "Recorded units")
    require(unit["command"] == "node --test --test-reporter=tap test/scripts/vdg-strudel-grandma-controls.test.mjs"
            and unit["cwd"] == "swissknife" and unit["log"] == "units.tap", "Wrong recorded test command")
    for key, expected in (("exit_code", 0), ("tests", 8), ("passed", 8), ("failed", 0)):
        integer(unit, key, expected)
    log_path = regular_file(archive / "units.tap")
    require(sha(log_path) == unit["log_sha256"] == UNIT_LOG_SHA256, "Recorded test log changed")
    check_tap(log_path.read_text(), 8)
    browser = receipt["browser"]
    exact_keys(browser, ("command", "exit_code", "report", "report_sha256", "original_controls", "real_edited_melody_verified",
        "mcp_provider_posts", "page_errors", "owned_resources_closed", "png_count", "png_sha256"), "Recorded browser")
    require(browser["command"] == "node scripts/run-with-owned-port.mjs --env-var SWISSKNIFE_VDG_STRUDEL_SMOKE_PORT --preferred 3087 -- node --import tsx test/e2e/smoke/vdg-strudel-grandma-controls-smoke.mjs",
            "Wrong browser reproduction command")
    for key, expected in (("exit_code", 0), ("original_controls", 19), ("mcp_provider_posts", 0), ("png_count", 39)):
        integer(browser, key, expected)
    require(browser["real_edited_melody_verified"] is True and browser["owned_resources_closed"] is True
            and browser["page_errors"] == [], "Browser preflight is incomplete")
    require(browser["report"] == "browser/result.json", "Unsafe browser report path")
    report_path = regular_file(archive / "browser/result.json")
    require(sha(report_path) == browser["report_sha256"] == REPORT_SHA256, "Actual browser report changed")
    verify_report(json.loads(report_path.read_text()))
    expected_pngs = {f"browser/{index}-{phase}.png" for index in range(19) for phase in ("before", "after")}
    expected_pngs.add("browser/creation-functional.png")
    hashes = browser["png_sha256"]
    require(type(hashes) is dict and set(hashes) == expected_pngs, "Missing or unexpected screenshot pair")
    require({str(file.relative_to(archive)) for file in (archive / "browser").glob("*.png")} == expected_pngs,
            "Screenshot directory does not match the actual39-frame proof")
    for name, digest in hashes.items():
        image = regular_file(archive / name)
        require(sha(image) == digest, f"Screenshot bytes changed: {name}")
        header = image.read_bytes()[:24]
        require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR",
                f"Invalid actual PNG: {name}")
        require(all(size > 0 for size in struct.unpack(">II", header[16:24])), f"Empty PNG dimensions: {name}")
    return {"original_controls_verified": 19, "png_hashes_verified": 39, "recorded_app_tests": 8}


def verify_binding():
    require(sha(regular_file(ROOT / BINDING_TEST)) == BINDING_TEST_SHA256, "Reviewed binding regression changed")
    alias = SWISS / "web/js/apps/strudel.js"
    actual = SWISS / "web/js/apps/strudel-grandma.js"
    require(alias.is_symlink() and os.readlink(alias) == "strudel-grandma.js", "Wrong compatibility source target")
    require(alias.resolve(strict=True) == actual.resolve(strict=True) and os.path.samefile(alias, actual),
            "Declared Strudel source is not the actual factory implementation")
    require(sha(alias) == SOURCES["swissknife/web/js/apps/strudel-grandma.js"], "Declared source bytes differ")


def main():
    verify_binding()
    result = verify_recordings()
    source_scope = [*SOURCES, BINDING_TEST, "swissknife/web/js/main-simple.js",
                    "swissknife/scripts/vdg-capture-fingerprint.cjs", "swissknife/scripts/vdg-evidence.cjs"]
    before = {name: sha(ROOT / name) for name in source_scope}
    command = ["node", "--test", "--test-reporter=tap", "test/scripts/vdg-strudel-grandma-controls.test.mjs",
               "test/scripts/vdg-strudel-source-binding.test.mjs"]
    process = subprocess.run(command, cwd=SWISS, capture_output=True, text=True, timeout=120)
    print(process.stdout, end="")
    if process.stderr:
        print(process.stderr, end="")
    require(process.returncode == 0, f"Fresh8+3 Node tests failed: {process.returncode}")
    check_tap(process.stdout, 11)
    require({name: sha(ROOT / name) for name in source_scope} == before, "Reviewed sources changed during fresh validation")
    verify_binding()
    require(verify_recordings() == result, "Durable recordings changed during fresh validation")
    result.update({"repair_validated": True, "fresh_app_tests": 8, "fresh_source_binding_tests": 3,
                   "source_hashes": before, "mcp_provider_posts": 0, "page_errors": [], "owned_resources_closed": True,
                   "gui_acceptance": False, "work_complete": False, "completion_authority": False})
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
