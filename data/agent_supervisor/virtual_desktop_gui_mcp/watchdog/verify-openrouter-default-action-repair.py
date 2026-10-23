"""Read-only R22 repair validation. Canonical preflight is unapproved until pinned.

Source pins bind the reviewed final candidate and actual test contract. The
canonical entrypoint fails before child/live checks until the operator reviews
the installed canonical Chrome proof, current census and ten-cell preservation.
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
ARCHIVE = Path(__file__).resolve().parent / "smoke-receipts/openrouter-default-action"
APP = "swissknife/web/js/apps/openrouter.js"
UNIT = "swissknife/test/scripts/vdg-openrouter-default-action.test.mjs"
SMOKE = "swissknife/test/e2e/smoke/vdg-openrouter-default-action-smoke.mjs"
MAIN = "swissknife/web/js/main-simple.js"
HELPER = "swissknife/test/e2e/helpers/live-click-session.ts"
CATALOG_UNIT = "swissknife/test/scripts/vdg-openrouter-catalog.test.mjs"
MODAL_UNIT = "swissknife/test/scripts/vdg-local-modal-ownership.test.mjs"
CRON = "swissknife/web/js/apps/cron.js"
FINGERPRINT = "swissknife/scripts/vdg-capture-fingerprint.cjs"
BROWSER_SOURCE_PATHS = (APP, UNIT, SMOKE, MAIN, HELPER, CATALOG_UNIT, MODAL_UNIT)
SOURCES = {'swissknife/web/js/apps/openrouter.js': '9ecb8b8864f18ea880b5f5ede05405c379c119ed7aa18051b1a56b2d993fa731', 'swissknife/test/scripts/vdg-openrouter-default-action.test.mjs': '2fb0e26bcb13a7b4d4263c530c8f897eca6273463973a0520273400120812095', 'swissknife/test/e2e/smoke/vdg-openrouter-default-action-smoke.mjs': '46d175f49b645956bb00e621cfd45549cab10bf8b9ee239bb1b0e830c0a9e327', 'swissknife/web/js/main-simple.js': 'b46037cf2eb8b3746db45e13ec07ffbedefa439fc6b0d15f0e16c85277c2c3ef', 'swissknife/test/e2e/helpers/live-click-session.ts': '1090d340179dda20364dea5dcfafcd49b110495fb72ab56513034b40aa3dd348', 'swissknife/test/scripts/vdg-openrouter-catalog.test.mjs': '9f27ed7521c8a9c5a173e02f03bf4748c47e07b65fd91512baedd915416c6f32', 'swissknife/test/scripts/vdg-local-modal-ownership.test.mjs': 'f11486d009f9e49e5fce0373700ba87feff03f3afbf9b81811d04e1c5212531e', 'swissknife/web/js/apps/cron.js': '555ee78165b7dc7abfa6a86b5b19ce887dd465fcb0fde09f8afeb3aff8815e7d', 'swissknife/scripts/vdg-capture-fingerprint.cjs': 'e120b7c7041d1b1b9bc0b9593f09861b537685bb1bb369956878f3ef73c44167'}
UNCHANGED_DIAGNOSTIC_SHA256 = "4d1534de75f10b6beddd191e57e268f09bbada07dca7ec7f5958d58aad678e1a"
PRECONDITION_SHA256 = "08026da5138ae45f6ae360b4c8498d1914f27946429d1e4751264e15c8eebe0a"
TARGET_MODEL = "google/gemini-4-argon:batch"
PREVIOUS_MODEL = "google/gemini-4-argon"
NEIGHBOR_MODEL = "google/gemini-nano-banana-2.1"
ACTIONS = (("default", TARGET_MODEL), ("default", TARGET_MODEL), ("default", PREVIOUS_MODEL),
           ("default", NEIGHBOR_MODEL), ("favorite", TARGET_MODEL), ("favorite", TARGET_MODEL),
           ("info", TARGET_MODEL), ("try", TARGET_MODEL), ("default", TARGET_MODEL), ("default", TARGET_MODEL))
STORAGE_KEYS = ("openrouter_settings", "openrouter_favorites", "openrouter_conversations", "openrouter_history")
STATE_FIELDS = ("model_count", "favorite_count", "current_tab", "default_model", "persisted_default", "api_key_present",
                "favorites", "catalog_controls", "favorite_controls", "controls", "storage", "writes", "events", "dialogs",
                "root_same", "target_same", "target_focused", "all_model_control_nodes_same", "scroll")
REVIEWED_PREFLIGHT_SHA256 = "9bfa31b4300a13d67f23f7b1e7d4f5641746a03eafe639f6a5644a09c91d4db5"
FRESH_TEST_COUNT = 28
BROWSER_CONTRACT_FROZEN = True
OLD_APP_SHA256 = "ab83f92522095599c4dfa2ac740fdc09a229ac31bbf43fff00ec811d58e605d2"
OLD_CHECKPOINT_SHA256 = "ccb6c76394b4a6cb47807002fe23f0d4071d7c0b5360a323daf0d4de09500192"
OLD_PAYLOAD_SHA256 = "82afc292fb330df6dc0ec033ee29dfdb723014a0c1182d51e1a34cbf4dd8e0a9"
OLD_ROW_SHA256 = "62bfe590fd6bae2b64a86cdf7400e58c6dcf38561a1003e709824aad8697e0bc"
OLD_FINGERPRINT = "73c771a71764277b4c3526451e31092755d1f7428ea15f18df270e08cfa7b025"
BASELINE_SHA256 = "e2b01d6f58f7d13da7273b64f0c8a3c58c30c3445cb8557010176e28f1654a45"
OLD_IMAGES = {
    "screenshot-before.png": "6162b14acf1d3b1feacce80860d8d13f80d5bc511d0f55b91cebcb6d3a7a2932",
    "screenshot-after.png": "321997f41b4f606dbb3d84b58a68bf86710c6b04b9393082494f60fe4c6c1d3e",
}
FAILED_SELECTOR = ('[data-openrouter-model="google/gemini-4-argon:batch"]'
                   '[data-openrouter-provider="google"][data-openrouter-placement="catalog"]'
                   '[data-openrouter-action="default"]')
TRANSPORTS = ("http", "libp2p")
UNAFFECTED = {f"vdg-{family}/{transport}" for family in
              ("storage", "datasets", "accelerate", "network", "control") for transport in TRANSPORTS}


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


def tap(text, count=None):
    count = FRESH_TEST_COUNT if count is None else count
    require(type(count) is int and count > 0, "Final fresh app test count is not pinned")
    for key, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {key} (\d+)$", text, re.M) == [str(expected)], f"Wrong fresh TAP {key}")
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)], "Wrong fresh TAP plan")
    require(len(re.findall(r"^ok \d+ - ", text, re.M)) == count and not re.search(r"^not ok\b", text, re.M),
            "Missing or failed actual test outcomes")


def verify_failure(archive=ARCHIVE):
    directory = archive / "actual-failure"
    require(sha(regular(directory / "source-before-openrouter.js")) == OLD_APP_SHA256,
            "Original failed app bytes changed")
    checkpoint = bound_json(directory / "checkpoint-before.json", OLD_CHECKPOINT_SHA256)
    row = bound_json(directory / "failed-row.json", OLD_ROW_SHA256)
    require(checkpoint["schema"] == "swissknife.vdg-capture-checkpoint.v1"
            and checkpoint["target"] == "local" and checkpoint["transport"] == "http"
            and checkpoint["input_fingerprint"] == OLD_FINGERPRINT
            and checkpoint["payload_sha256"] == OLD_PAYLOAD_SHA256
            and checkpoint["capture_complete"] is False and checkpoint["work_complete"] is False
            and checkpoint["completion_authority"] is False
            and len(checkpoint["payload"]["rows"]) == 361 and checkpoint["payload"]["rows"][322] == row,
            "Original stopped failed Local checkpoint differs")
    require(row["app_id"] == row["launch_id"] == "openrouter" and row["selector"] == FAILED_SELECTOR
            and row["clicked"] is False and row["failure_reasons"][-1] == "click-failed"
            and len(row["failure_reasons"]) == 2 and len(row["failure_reasons"][0]) == 180
            and row["failure_reasons"][0].startswith("locator.click: Timeout 3000ms exceeded.")
            and row["pageerrors"] == [] and row["mcp_call_count"] == row["incomplete_mcp_call_count"] == 0
            and row["observations"] == [] and row["observation"] is None,
            "Original exact timeout failure was changed, cleared or reconstructed")
    for name, expected in OLD_IMAGES.items():
        png(directory / name, expected)
    return {"original_failed_checkpoint_rows": 361, "original_failure_row": 322, "original_failure_pngs": 2}


def verify_preservation(record, live, baseline):
    exact(record, ("schema", "before_app_sha256", "after_app_sha256", "cells", "gui_acceptance", "work_complete",
                   "completion_authority"), "preservation receipt")
    no_authority(record)
    require(record["schema"] == "swissknife.vdg-openrouter-preservation.v1"
            and record["before_app_sha256"] == OLD_APP_SHA256
            and digest(SOURCES[APP]) and record["after_app_sha256"] == SOURCES[APP], "Wrong actual source boundary")
    require(type(record["cells"]) is dict and set(record["cells"]) == set(baseline["cells"]) == UNAFFECTED
            and set(live["fingerprints"]) == set(live["acquisitions"]) == UNAFFECTED,
            "Exactly ten unaffected Storage/Dataset/Accelerate/Network/Control cells are required")
    require(live["inventory"]["current"] is True, "Actual current inventory required")
    for cell, row in record["cells"].items():
        exact(row, ("before_input_fingerprint", "after_input_fingerprint", "run_id", "report_sha256"), "preserved cell")
        before, actual = baseline["cells"][cell], live["acquisitions"][cell]
        require(row["before_input_fingerprint"] == before["input_fingerprint"] == row["after_input_fingerprint"]
                == live["fingerprints"][cell] == actual["input_fingerprint"], f"Unaffected source fingerprint changed: {cell}")
        require(row["run_id"] == before["run_id"] == actual["run_id"] and row["report_sha256"]
                == before["report_sha256"] == actual["report_sha256"] and actual["capture_complete"] is True
                and type(actual["row_count"]) is int and actual["row_count"] == before["row_count"],
                f"Unaffected completed capture changed: {cell}")


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def verify_precondition(inputs, archive=ARCHIVE):
    exact(inputs, ("diagnostic_only", "source_checkpoint", "checkpoint_sha256", "seed_favorite_ids", "seed_default_model",
                   "seed_default_basis", "failed_row"), "reconstructed diagnostic precondition")
    checkpoint = bound_json(archive / "actual-failure/checkpoint-before.json", OLD_CHECKPOINT_SHA256)
    expected = []
    for row in checkpoint["payload"]["rows"][:322]:
        if row.get("app_id") == "openrouter" and row.get("clicked") is True and '[data-openrouter-action="favorite"]' in row.get("selector", ""):
            match = re.search(r'\[data-openrouter-model="([^"]+)"\]', row["selector"])
            require(match is not None, "Original favorite action lacks exact model identity")
            if match[1] not in expected:
                expected.append(match[1])
    require(inputs["diagnostic_only"] is True and inputs["checkpoint_sha256"] == OLD_CHECKPOINT_SHA256
            and inputs["failed_row"] == checkpoint["payload"]["rows"][322]
            and len(expected) == 61 and inputs["seed_favorite_ids"] == expected
            and inputs["seed_default_model"] == PREVIOUS_MODEL
            and inputs["seed_default_basis"] == "Source-inferred from successful preceding default row318, not historical storage byte proof",
            "Reconstructed actions are not a historical stored-favorites snapshot")
    require(type(inputs["source_checkpoint"]) is str and Path(inputs["source_checkpoint"]).name ==
            f"local-http-{OLD_FINGERPRINT}.json", "Wrong original source checkpoint identity")
    return inputs


def verify_unchanged_diagnostic(archive=ARCHIVE):
    directory = archive / "unchanged-diagnostic"
    report = bound_json(directory / "report.json", UNCHANGED_DIAGNOSTIC_SHA256)
    require(report["schema"] == "swissknife.openrouter-default-diagnostic.v1" and report["passed"] is True
            and report["diagnostic_only"] is True and report["completion_authority"] is False and report["work_complete"] is False
            and report["canonical_module_override"] is False and report["source_sha256"] == report["source_sha256_after"] == OLD_APP_SHA256
            and report["reproduced_failure"] is False and report["posts"] == report["page_errors"] == []
            and report["owned_resources_closed"] is True, "Original unchanged-source diagnostic was altered or overstated")
    require(report["resources"]["vite_pid_absent"] is True and report["resources"]["chrome_pid_absent"] is True,
            "Original diagnostic owned cleanup differs")
    expected = (TARGET_MODEL, PREVIOUS_MODEL, TARGET_MODEL, NEIGHBOR_MODEL, TARGET_MODEL, PREVIOUS_MODEL, TARGET_MODEL, PREVIOUS_MODEL)
    require(len(report["cases"]) == 8, "Original diagnostic must retain all eight actual cases")
    for index, (case, model) in enumerate(zip(report["cases"], expected)):
        require(case["index"] == index and case["id"] == model and case["clicked"] is True
                and case["normal_error"] is None and case["forced_error"] is None and case["closed_root_count"] == 0
                and case["after"]["default_model"] == case["after"]["persisted_default"] == model
                and any(event["trusted"] is True and event["model"] == model for event in case["trusted_clicks"])
                and any(method["old_root_connected"] is False and method["root_same"] is False for method in case["setters"]),
                "Original diagnostic must retain successful clicks and observed detached-root behavior")
    expected_pngs = {f"{index}-{phase}.png" for index in range(8) for phase in ("before", "after")}
    require(set(report["screenshot_sha256"]) == expected_pngs, "Original diagnostic PNG set differs")
    for name, expected_sha in report["screenshot_sha256"].items():
        png(directory / name, expected_sha)
    return {"unchanged_diagnostic_passed_cases": 8, "original_target_passed_cases": 4,
            "original_timeout_reproduced": False, "original_timeout_causality_established": False}


def verify_state(state, model_ids):
    exact(state, STATE_FIELDS, "actual OpenRouter state")
    require(type(state["model_count"]) is int and state["model_count"] == 468 and state["api_key_present"] is False,
            "Actual full catalog or no-provider precondition differs")
    favorites = state["favorites"]
    require(type(favorites) is list and len(set(favorites)) == len(favorites)
            and all(type(model) is str and model in model_ids for model in favorites)
            and type(state["favorite_count"]) is int and state["favorite_count"] == len(favorites), "Actual favorites differ")
    exact(state["storage"], STORAGE_KEYS, "actual owned storage")
    for value in state["storage"].values():
        require(value is None or type(value) is str, "Actual owned storage must retain raw bytes")
    require(json.loads(state["storage"]["openrouter_settings"])["defaultModel"] == state["persisted_default"]
            and json.loads(state["storage"]["openrouter_favorites"]) == favorites, "Actual persisted settings/favorites differ")
    require(state["default_model"] in model_ids and state["persisted_default"] in model_ids
            and state["current_tab"] in {"models", "playground"}, "Actual default/tab is invalid")
    for key in ("root_same", "target_same", "target_focused", "all_model_control_nodes_same"):
        require(type(state[key]) is bool, "Actual DOM identity state missing")
    for key in ("writes", "events", "dialogs", "scroll", "controls"):
        require(type(state[key]) is list, "Actual ordered state history required")
    for entry in state["scroll"]:
        exact(entry, ("connected", "top", "left"), "actual scroll ancestor")
        require(type(entry["connected"]) is bool and number(entry["top"]) and number(entry["left"]), "Actual scroll ownership differs")
    for entry in state["writes"]:
        exact(entry, ("key", "length", "time"), "actual owned storage write")
        require(entry["key"] in STORAGE_KEYS and type(entry["length"]) is int and entry["length"] >= 0
                and number(entry["time"]) and entry["time"] >= 0, "Invalid actual storage write")
    for event in state["events"]:
        exact(event, ("trusted", "model", "action", "placement", "tab", "time", "root_same_before_handler",
                      "target_same_before_handler", "scroll_before_handler"), "actual captured event")
        require(type(event["trusted"]) is bool and number(event["time"]) and event["time"] >= 0
                and type(event["root_same_before_handler"]) is bool and type(event["target_same_before_handler"]) is bool
                and type(event["scroll_before_handler"]) is list, "Invalid actual captured event")
    require(all(type(message) is str for message in state["dialogs"]), "Actual dialog records differ")
    controls = state["controls"]
    if state["current_tab"] == "playground":
        require(controls == [] and state["catalog_controls"] == state["favorite_controls"] == 0, "Unexpected model controls on Playground")
        return
    require(state["catalog_controls"] == 468 * 4 and state["favorite_controls"] == len(favorites) * 4
            and len(controls) == 468 + len(favorites), "Full original catalog/favorite controls changed")
    seen = set()
    for control in controls:
        exact(control, ("model", "placement", "text", "pressed", "card_default"), "actual Default control")
        identity = (control["model"], control["placement"])
        require(identity not in seen and control["model"] in model_ids and control["placement"] in {"catalog", "favorites"},
                "Actual Default controls are missing, duplicated or unrelated")
        seen.add(identity)
        selected = control["model"] == state["default_model"]
        require(control["text"] == ("✓ Default" if selected else "Set Default")
                and control["pressed"] == str(selected).lower() and control["card_default"] is selected,
                "Actual default labels/ARIA/card state differ")
    require(seen == {(model, "catalog") for model in model_ids} | {(model, "favorites") for model in favorites},
            "All real catalog and actual favorite copies must remain present")


def verify_report(report, archive=ARCHIVE, root=ROOT):
    no_authority(report)
    require(report.get("candidate_module_override") is False, "Candidate browser evidence is not canonical proof")
    require(BROWSER_CONTRACT_FROZEN is True, "Final actual OpenRouter browser contract is not frozen")
    exact(report, ("schema", "passed", "work_complete", "gui_acceptance", "completion_authority", "candidate_module_override",
                  "source_sha256", "canonical_source_sha256", "precondition", "original_timeout_reproduced",
                  "original_timeout_causality_established", "source_hashes", "profiles", "posts_attempted", "posts_blocked",
                  "page_errors", "module_responses", "catalog_responses", "resources", "driver_limitation", "stage",
                  "canonical_source_sha256_after", "canonical_source_unchanged", "screenshot_sha256", "owned_resources_closed",
                  "finished_at"), "canonical Chrome report")
    require(report["schema"] == "swissknife.openrouter-default-action-smoke.v1" and report["passed"] is True
            and digest(SOURCES[APP]) and report["source_sha256"] == report["canonical_source_sha256"]
            == report["canonical_source_sha256_after"] == SOURCES[APP] and report["canonical_source_unchanged"] is True,
            "Actual canonical app source differs")
    require(report["source_hashes"] == {name: SOURCES[name] for name in BROWSER_SOURCE_PATHS}, "Actual browser source pins differ")
    require(report["original_timeout_reproduced"] is False and report["original_timeout_causality_established"] is False,
            "Focused DOM repair cannot claim the original timeout was reproduced or causally resolved")
    require(report["posts_attempted"] == report["posts_blocked"] == report["page_errors"] == [],
            "Actual local actions must attempt zero provider/MCP POSTs and have zero page errors")
    resources = report["resources"]
    exact(resources, ("vite_pid", "chrome_pid", "vite_pid_absent", "chrome_pid_absent"), "owned resources")
    require(all(type(resources[key]) is int and resources[key] > 0 for key in ("vite_pid", "chrome_pid"))
            and resources["vite_pid"] != resources["chrome_pid"] and resources["vite_pid_absent"] is True
            and resources["chrome_pid_absent"] is True and report["owned_resources_closed"] is True,
            "Actual owned browser/server cleanup missing")
    inputs = verify_precondition(bound_json(archive / "precondition.json", PRECONDITION_SHA256), archive)
    precondition = report["precondition"]
    exact(precondition, ("sha256", "reconstructed_prior_favorite_actions", "raw_historical_storage_snapshot",
                         "seed_favorite_ids", "default_model"), "browser reconstructed precondition")
    require(precondition["sha256"] == PRECONDITION_SHA256 and precondition["reconstructed_prior_favorite_actions"] is True
            and precondition["raw_historical_storage_snapshot"] is False
            and precondition["seed_favorite_ids"] == inputs["seed_favorite_ids"]
            and precondition["default_model"] == PREVIOUS_MODEL, "Browser precondition was altered or overstated")
    responses = report["module_responses"]
    require(responses == [{"transport": transport, "status": 200, "path": "/js/apps/openrouter.js"}
                          for transport in TRANSPORTS], "Both actual app modules must load successfully")
    catalogs = report["catalog_responses"]
    require(type(catalogs) is list and len(catalogs) == 2, "Both actual public catalogs required")
    catalog_ids = {}
    for row, transport in zip(catalogs, TRANSPORTS):
        exact(row, ("transport", "status", "sha256", "file"), "actual public catalog response")
        require(row["transport"] == transport and row["status"] == 200 and row["file"] == f"{transport}-actual-catalog.json",
                "Wrong actual public catalog response")
        catalog = bound_json(archive / "canonical" / row["file"], row["sha256"])
        data = catalog.get("data")
        require(type(data) is list and len(data) == 468 and all(type(item) is dict and type(item.get("id")) is str for item in data),
                "Full real public catalog required")
        ids = {item["id"] for item in data}
        require(len(ids) == 468 and {TARGET_MODEL, PREVIOUS_MODEL, NEIGHBOR_MODEL}.issubset(ids), "Actual catalog identities differ")
        catalog_ids[transport] = ids
    profiles = report["profiles"]
    require(type(profiles) is list and len(profiles) == 2, "Both actual declared profiles required")
    for profile, transport in zip(profiles, TRANSPORTS):
        exact(profile, ("transport", "cases", "passed", "initial", "original_control_count", "unresolved_original_selectors",
                        "no_case_storage_reset"), "actual browser profile")
        require(profile["transport"] == transport and profile["passed"] is True and profile["original_control_count"] == 1881
                and profile["unresolved_original_selectors"] == [] and profile["no_case_storage_reset"] is True,
                "All original controls and real persistence must remain available")
        ids = catalog_ids[transport]
        initial = profile["initial"]
        verify_state(initial, ids)
        require(initial["favorites"] == inputs["seed_favorite_ids"] and initial["default_model"] == initial["persisted_default"]
                == PREVIOUS_MODEL and initial["current_tab"] == "models", "Actual mounted initial state differs")
        require(type(profile["cases"]) is list and len(profile["cases"]) == 10, "All ten actual actions are required")
        for index, (case, (action, model)) in enumerate(zip(profile["cases"], ACTIONS)):
            fields = ["index", "action", "model", "selector", "before", "screenshot_before", "before_action", "click_ms",
                      "after", "trusted_events", "write_events", "screenshot_after"]
            if action == "default":
                fields.append("trusted_scroll_before_handler")
            if index != 7:
                fields.append("persisted_after_close")
            exact(case, fields, "actual local action")
            selector = f'[data-openrouter-model="{model}"][data-openrouter-provider="google"][data-openrouter-placement="catalog"][data-openrouter-action="{action}"]'
            require(case["index"] == index and case["action"] == action and case["model"] == model and case["selector"] == selector
                    and number(case["click_ms"]) and 0 <= case["click_ms"] <= 8000, "Actual action identity/timing differs")
            before, at_click, after = case["before"], case["before_action"], case["after"]
            for state in (before, at_click, after):
                verify_state(state, ids)
            require(case["trusted_events"] == after["events"][len(at_click["events"]):]
                    and case["write_events"] == after["writes"][len(at_click["writes"]):], "Actual event/write history differs")
            trusted = [event for event in case["trusted_events"] if event["trusted"] is True and event["model"] == model
                       and event["action"] == action and event["placement"] == "catalog"]
            require(trusted, "Actual trusted exact control action missing")
            require(case["screenshot_before"] == f"{transport}-{index}-before.png"
                    and case["screenshot_after"] == f"{transport}-{index}-after.png", "Actual action PNG identity differs")
            if action == "default":
                require(after["default_model"] == after["persisted_default"] == model and after["current_tab"] == "models"
                        and all(after[key] is True for key in ("root_same", "target_same", "target_focused", "all_model_control_nodes_same")),
                        "Actual explicit Default must preserve root/buttons/focus and persist exact selection")
                require(trusted[0]["root_same_before_handler"] is True and trusted[0]["target_same_before_handler"] is True
                        and case["trusted_scroll_before_handler"] == trusted[0]["scroll_before_handler"] == after["scroll"]
                        and all(entry["connected"] is True for entry in after["scroll"]),
                        "Actual trusted handler must preserve scroll and DOM identity")
                require({entry["key"] for entry in case["write_events"]} == set(STORAGE_KEYS),
                        "Every explicit Default must preserve all four genuine owned storage writes")
                if index in {1, 9}:
                    require(after["storage"] == at_click["storage"], "Repeated Default must preserve already saved values")
            elif action == "favorite":
                wanted = [item for item in inputs["seed_favorite_ids"] if index != 4 or item != TARGET_MODEL]
                require(after["favorites"] == wanted and after["favorite_count"] == (60 if index == 4 else 61)
                        and any(entry["key"] == "openrouter_favorites" for entry in case["write_events"]),
                        "Genuine favorite remove/add writes were lost")
            elif action == "info":
                require(any(model in message for message in after["dialogs"][len(at_click["dialogs"]):]), "Actual model info dialog missing")
            else:
                require(after["current_tab"] == "playground" and after["default_model"] == model
                        and after["persisted_default"] == NEIGHBOR_MODEL and after["storage"] == at_click["storage"]
                        and case["write_events"] == [], "Try must remain an unsaved local selection")
            if index == 8:
                require(before["current_tab"] == "models" and before["default_model"] == TARGET_MODEL
                        and before["persisted_default"] == NEIGHBOR_MODEL, "Try→Models→explicit Save path missing")
            if index != 7:
                closed = case["persisted_after_close"]
                exact(closed, ("default_model", "favorite_count"), "real persisted state after trusted close")
                require(closed == {"default_model": after["persisted_default"], "favorite_count": after["favorite_count"]},
                        "Real saved state was lost on close/reopen")
    expected_pngs = {f"{transport}-{index}-{phase}.png" for transport in TRANSPORTS for index in range(10)
                     for phase in ("before", "after")}
    require(type(report["screenshot_sha256"]) is dict and set(report["screenshot_sha256"]) == expected_pngs
            and {path.name for path in (archive / "canonical").glob("*.png")} == expected_pngs, "Actual40-PNG set differs")
    for name, expected in report["screenshot_sha256"].items():
        png(archive / "canonical" / name, expected)
    return {"actual_profiles": 2, "actual_actions": 20, "actual_pngs": 40, "actual_posts": 0,
            "original_controls_per_profile": 1881, "real_catalog_models_per_profile": 468}


def live_evidence():
    code = '''
const path=require('node:path');
const {inspectInventory}=require('./scripts/vdg-inventory-contract.cjs');
const {checkCapture}=require('./scripts/check-vdg-capture.cjs');
const {FAMILIES}=require('./scripts/vdg-evidence.cjs');
const {captureInputFingerprint}=require('./scripts/vdg-capture-fingerprint.cjs');
const root=process.cwd(),evidence=path.join(root,'test-results/virtual-desktop-ipfs-mcp-orb');
const inventory=inspectInventory({sourceRoot:root,evidenceRoot:evidence});
if(inventory.current!==true)throw Error('Current actual inventory required: '+inventory.reason);
const fingerprints={},acquisitions={};
for(const family of ['vdg-storage','vdg-datasets','vdg-accelerate','vdg-network','vdg-control'])for(const transport of ['http','libp2p']){
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
    # This first operation rejects the unset canonical pin before any child.
    receipt = bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    exact(receipt, ("schema", "source_sha256", "canonical_report_sha256", "preservation_sha256", "baseline_sha256",
                    "gui_acceptance", "work_complete", "completion_authority"), "reviewed canonical preflight")
    no_authority(receipt)
    require(receipt["schema"] == "swissknife.vdg-openrouter-canonical-preflight.v1" and receipt["source_sha256"] == SOURCES
            and all(digest(value) for value in SOURCES.values()) and type(FRESH_TEST_COUNT) is int and FRESH_TEST_COUNT > 0,
            "Final canonical source/count pins required")

    def sources():
        for name, expected in SOURCES.items():
            require(sha(regular(ROOT / name)) == expected, f"Reviewed canonical source changed: {name}")

    sources()
    failure = verify_failure()
    diagnostic = verify_unchanged_diagnostic()
    inputs = verify_precondition(bound_json(ARCHIVE / "precondition.json", PRECONDITION_SHA256))
    browser = verify_report(bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"]))
    baseline = bound_json(ARCHIVE / "unaffected-ten-before.json", receipt["baseline_sha256"])
    require(receipt["baseline_sha256"] == BASELINE_SHA256, "Authoritative ten-cell baseline differs")
    no_authority(baseline)
    require(baseline["schema"] == "swissknife.vdg-openrouter-ten-before.v1"
            and baseline["source_before"][APP] == OLD_APP_SHA256
            and baseline["source_before"][MAIN] == SOURCES[MAIN]
            and baseline["source_before"][FINGERPRINT] == SOURCES[FINGERPRINT], "Original actual source boundary changed")
    old = baseline["local_failed_checkpoint"]
    require(old["sha256"] == OLD_CHECKPOINT_SHA256 and old["input_fingerprint"] == OLD_FINGERPRINT
            and old["row_count"] == 361 and old["failed_row_index"] == 322
            and old["failed_row_sha256"] == OLD_ROW_SHA256 and old["capture_complete"] is False,
            "Original failed checkpoint boundary changed")
    preservation = bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    live = live_evidence()
    verify_preservation(preservation, live, baseline)
    process = subprocess.run(["node", "--test", "--test-concurrency=1", "--test-reporter=tap",
                              *[str(Path(name).relative_to("swissknife")) for name in (UNIT, CATALOG_UNIT, MODAL_UNIT)]],
                             cwd=SWISS, capture_output=True, text=True, timeout=120)
    print(process.stdout, end="")
    require(process.returncode == 0, f"Fresh{FRESH_TEST_COUNT} actual app tests failed: {process.stderr}")
    tap(process.stdout)
    sources()
    bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    require(verify_report(bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"])) == browser,
            "Canonical browser proof changed during fresh units")
    require(verify_failure() == failure and verify_unchanged_diagnostic() == diagnostic,
            "Immutable actual failure or unchanged-source diagnostic changed")
    require(verify_precondition(bound_json(ARCHIVE / "precondition.json", PRECONDITION_SHA256)) == inputs,
            "Reconstructed diagnostic precondition changed")
    require(bound_json(ARCHIVE / "unaffected-ten-before.json", receipt["baseline_sha256"]) == baseline,
            "Authoritative ten-cell baseline changed during fresh units")
    bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    require(live_evidence() == live, "Inventory/acquisition source binding changed during fresh units")
    return {"repair_validated": True, "canonical_product_preflight_validated": True, "fresh_tests": FRESH_TEST_COUNT,
            **browser, **failure, **diagnostic, "unaffected_cells_preserved": 10,
            "all_12_acquisitions_and_six_strict_go_gates_still_required": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


if __name__ == "__main__":
    print(json.dumps(verify_ready_proof(), sort_keys=True))
