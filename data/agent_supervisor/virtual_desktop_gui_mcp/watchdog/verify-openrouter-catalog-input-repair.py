"""Read-only R23 public-catalog repair validation; never GUI completion authority.

The first operation requires the reviewed canonical preflight. Candidate builds,
unit fixtures and archived partial captures cannot substitute for that proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ast
import hashlib
import json
import marshal
import math
from pathlib import Path
import re
import shlex
import struct
import subprocess
from types import CodeType

ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / "swissknife"
WATCHDOG = Path(__file__).resolve().parent
ARCHIVE = WATCHDOG / "smoke-receipts/openrouter-catalog-input"
BOARD = ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md"
APP = "swissknife/web/js/apps/openrouter.js"
UNIT = "swissknife/test/scripts/vdg-openrouter-catalog-snapshot.test.mjs"
SMOKE = "swissknife/test/e2e/smoke/vdg-openrouter-catalog-snapshot-smoke.mjs"
GUARD = "swissknife/scripts/vdg-openrouter-catalog-input.cjs"
WRAPPER = "swissknife/scripts/run-with-vdg-openrouter-catalog-input.mjs"
LOCAL_SPEC = "swissknife/test/e2e/families/local-negative-mcp.spec.ts"
MAIN = "swissknife/web/js/main-simple.js"
HELPER = "swissknife/test/e2e/helpers/live-click-session.ts"
COLLECTOR = "swissknife/scripts/rendered-control-rows.mjs"
FINGERPRINT = "swissknife/scripts/vdg-capture-fingerprint.cjs"
R15_DRIVER = "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-case-cost-diagnostic.py"
OLD_APP_SHA256 = "9ecb8b8864f18ea880b5f5ede05405c379c119ed7aa18051b1a56b2d993fa731"
RAW_SHA256 = "65a3034c116179fac2ba1511796f0e1a014955986295385dfac8fbc35b7271bc"
PROVENANCE_SHA256 = "19726a9dac6901f79566e387871e286f32633b415ef28fb5f0912e94aa125e3c"
MODEL_IDS_SHA256 = "819a351f4633f638d5d26192f8a57162e8a6ab498aac04e35cd064c3d4947c41"
SOURCE_URL = "https://openrouter.ai/api/v1/models"
OBSERVED_AT = "2026-10-22T17:51:25.969769+00:00"
DESCRIPTOR = {
    "schema": "swissknife.openrouter-catalog-snapshot.v1", "source_url": SOURCE_URL,
    "observed_at": OBSERVED_AT, "raw_sha256": RAW_SHA256, "raw_bytes": 787610,
    "model_count": 468, "model_ids_sha256": MODEL_IDS_SHA256,
    "local_url": f"/vdg-public-inputs/openrouter/{RAW_SHA256}.json",
    "provenance_url": f"/vdg-public-inputs/openrouter/provenance-{PROVENANCE_SHA256}.json",
    "provenance_sha256": PROVENANCE_SHA256,
}
RAW = "swissknife/web/public" + DESCRIPTOR["local_url"]
PROVENANCE = "swissknife/web/public" + DESCRIPTOR["provenance_url"]
SOURCES = {
    APP: "294342a920e7d33729f2b4afdb3c8c352f1c080fc5897f901e2cd0c9225b579a",
    UNIT: "18d8c0d3d5a639155b465732ceb64174a20276ffb786d9e502f38a5f120cf4e0",
    SMOKE: "55a4d7a2bd6e0fe7fdf365a3d3b17185bab20795c1cec9739018c0e3ce68ee67",
    GUARD: "320201344c87a2a17e575d83e67cde129e8d10b457453b1e87c60e7887f5b2ea",
    WRAPPER: "4865da3831aa75f523e33cee3ecad46490430505f0aad209798e664d59c0c4bb",
    LOCAL_SPEC: "e5fcf0733f0048656205101e1cd73b1240562b6a83f8d05779fb3fa651d5d960",
    "swissknife/scripts/build-family-mcp-spec.cjs": "08f61bbbb990dbf6d3bff679ca6f2fe74024cb835a2f96fb795e8ab89276d914",
    "swissknife/scripts/capture-openrouter-catalog-input.mjs": "0c7c91d184d2d0c350e26e07d60bce6b85ed3ac94c5dd5e69e9f0f64e4b79309",
    "swissknife/scripts/vdg-openrouter-catalog-input.test.mjs": "dba1fca4fe9a0b13531c3cc1f1fff08c8bfd3699e5e57cd8e8fec27c0559d01a",
    "swissknife/scripts/vdg-local-todo-isolation.test.mjs": "6a4f2bb2a92244ac605d170f57940927baa34e07347a1535d2051fae017fb0e8",
    "swissknife/test/scripts/vdg-openrouter-default-action.test.mjs": "2fb0e26bcb13a7b4d4263c530c8f897eca6273463973a0520273400120812095",
    "swissknife/test/scripts/vdg-openrouter-catalog.test.mjs": "9f27ed7521c8a9c5a173e02f03bf4748c47e07b65fd91512baedd915416c6f32",
    "swissknife/test/scripts/vdg-local-modal-ownership.test.mjs": "f11486d009f9e49e5fce0373700ba87feff03f3afbf9b81811d04e1c5212531e",
    MAIN: "b46037cf2eb8b3746db45e13ec07ffbedefa439fc6b0d15f0e16c85277c2c3ef",
    HELPER: "1090d340179dda20364dea5dcfafcd49b110495fb72ab56513034b40aa3dd348",
    COLLECTOR: "fed110237552be81dcc46656b9210c60720a6b2e5bcd3482207368a8cb7305b7",
    FINGERPRINT: "e120b7c7041d1b1b9bc0b9593f09861b537685bb1bb369956878f3ef73c44167",
    R15_DRIVER: "04d8386559e91c1b6f5195a46a8e9f5e7b54dbf2adff4ef74d5921741d88a865",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/admit-openrouter-catalog-input-repair.py": "05c0e0a5cf950f25630c762254f7c0277c55d9217777636ebea57edb46274052",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/test-openrouter-catalog-input-admission.py": "8d15deb3513f561082a8a61c86e2527b62dbe8d1bdcbd03d26a66fa51c592ab4",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/test-openrouter-catalog-input-ops.py": "e8c41e09335c2b0388f636cfc19d4e510da1f217ad3e326c16d8fc28283e3b0d",
    RAW: RAW_SHA256, PROVENANCE: PROVENANCE_SHA256,
}
OTHER_SPECS = {
    "accelerate-mcp-invoke.spec.ts": "ecf28a3b776300d73a043fc2bed4b5e6061e52027416f8c3dea7364a54953d69",
    "control-plane-mcp-invoke.spec.ts": "9003c79c2d7844dec7de6951f43c6dc3537fd00ec61ea66de7216935bc2915b9",
    "datasets-mcp-invoke.spec.ts": "55da13746d6c2f2c7a7ee31c8ef1bc21b39092a3658349373282f138cb8a2884",
    "network-mcp-invoke.spec.ts": "231958bfb29e99adc9965196ff34623addcf2d012f3731eb024a4ccd7d9ebbaa",
    "storage-media-mcp-invoke.spec.ts": "8ad032f8c3a617c126251f0e2ac811d3bfa63360c5f6ddac6bd7d92f28a7b488",
}
SOURCES.update({"swissknife/test/e2e/families/" + name: value for name, value in OTHER_SPECS.items()})
REVIEWED_PREFLIGHT_SHA256 = "f304886600093e62e3b1143f8c6295a8024e88c845c2cedaf7fa4c485cbfddee"
BASELINE_SHA256 = "fdb106d4cdb86c60cf49454de05316c8c72ec0aa1e0f62b56d755cbe92d57d86"
FAILURE_PINS = {
    "http-checkpoint.json": "98120d7167267d0685681070ed98265bf759356216a48c63a80361b138e51ac0",
    "libp2p-checkpoint.json": "ac746c15a990eb62e37ce9634000fb9818f082cb4d0fc93a0be44daf4c219bc7",
    "supervisor-log-at-stop.log": "e6a574304ea6bce3e007e161af4a94b029581aa2e2ef83b1687fd251a5eb7555",
    "matrix-before.json": "72762a1a10f62f18a5c30ce2e2d59196ad379ad5d950a9d8726b703375e69e78",
}
TRANSPORTS = ("http", "libp2p")
UNAFFECTED = {f"vdg-{family}/{transport}" for family in ("storage", "datasets", "accelerate", "network", "control") for transport in TRANSPORTS}
TARGET_MODEL = "minimax/minimax-m3.1-flash"
OLD_MODEL = TARGET_MODEL + ":free"
NEIGHBOR_MODEL = "minimax/minimax-m3"
ACTIONS = (("favorite", TARGET_MODEL), ("info", TARGET_MODEL), ("try", TARGET_MODEL),
           ("default", TARGET_MODEL), ("default", TARGET_MODEL), ("default", NEIGHBOR_MODEL),
           ("favorite", TARGET_MODEL), ("favorite", TARGET_MODEL), ("default", TARGET_MODEL), ("default", TARGET_MODEL))
STORAGE_KEYS = {"openrouter_settings", "openrouter_favorites", "openrouter_conversations", "openrouter_history"}
WRAPPER_PREFIX = f"node {WRAPPER} -- "
REPAIR = "VDG-013-R23"
VERIFY_COMMAND = "python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-openrouter-catalog-input-repair.py"
COMMANDS = {
    "VDG-039-R01": ("node swissknife/scripts/run-vdg-all-families.mjs --timeout-seconds 22200", "node swissknife/scripts/run-vdg-all-families.mjs --check"),
    "VDG-036-R01": ("node swissknife/scripts/run-vdg-family.mjs vdg-local http --capture-only", "node swissknife/scripts/check-vdg-capture.cjs vdg-local http"),
    "VDG-036-R02": ("node swissknife/scripts/run-vdg-family.mjs vdg-local libp2p --capture-only", "node swissknife/scripts/check-vdg-capture.cjs vdg-local libp2p"),
    "VDG-036-R03": ("node swissknife/scripts/verify-vdg-family.mjs vdg-local --timeout-seconds 22200", "node swissknife/scripts/verify-vdg-family.mjs vdg-local --check"),
    "VDG-040-R03": ("node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go", "node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go"),
    "VDG-060": ("python3 swissknife/scripts/vdg_closeout_requires_go.py", "node swissknife/scripts/build-gui-mcp-coverage.cjs --require-go"),
}
PROGRAM_NO_GO_LINE = "Program decision: **NO_GO** until VDG-040 reports `decision: GO`."
PROGRAM_GO_LINE = "Program decision: **GO**."
FINAL_FAMILIES = {"vdg-" + value for value in ("storage", "datasets", "accelerate", "network", "control", "local")}
FINAL_CELLS = {family + "/" + transport for family in FINAL_FAMILIES for transport in TRANSPORTS}
LANE_SOURCE = "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py"
GATE_SOURCE = "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/gate_recovery.py"
RECOVERY_MODULE = "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/vdg_pre_command_recovery.py"
RECOVERY_SCRIPT = "swissknife/scripts/recover-vdg-capture-deadline.cjs"
CONTROL_MANIFEST = "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/bundle_lanes.json"
FINAL_LANE_SOURCES = {
    LANE_SOURCE: "f5142db1c49e31f7fefbf5fda7be752a29c9c51ad99116adc3da829fb4ab740f",
    GATE_SOURCE: "f6b4df85c5d220ebc5f715f61e69cdcb083443d4fc98508dec751d46d0805e48",
    RECOVERY_MODULE: "f65e59265af707ff5f65b81be04e55e8aa96dbbe4efa9dd1a4e7ae9a19196570",
    RECOVERY_SCRIPT: "57a4fab03128ed94449c35e0065583f3bd4870abad921477c4506a3a40864ff6",
    CONTROL_MANIFEST: "0d7bc6b9eaf81e6ec848ecd76fe3650602bbe0734e0337d8e048977ce07ce13d",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), f"Expected regular proof file: {path}")
    return path


def bound_json(path, expected):
    require(digest(expected), "Reviewed proof digest is not pinned")
    require(sha(regular(path)) == expected, f"Reviewed proof bytes changed: {path}")
    return json.loads(path.read_bytes())


def no_authority(value):
    require(type(value) is dict, "Proof object required")
    for field in ("gui_acceptance", "work_complete", "completion_authority"):
        require(value.get(field) is False, f"Repair cannot grant {field}")


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def png(path, expected):
    require(digest(expected) and sha(regular(path)) == expected, f"Actual PNG bytes changed: {path}")
    header = path.read_bytes()[:24]
    require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR"
            and all(value > 0 for value in struct.unpack(">II", header[16:24])), f"Invalid actual PNG: {path}")


def local_file(root, relative, prefix=None):
    require(type(relative) is str and relative and not Path(relative).is_absolute()
            and ".." not in Path(relative).parts and "\\" not in relative, "Unsafe proof path")
    if prefix:
        require(relative.startswith(prefix), "Proof path leaves its declared evidence namespace")
    file = root / relative
    require(file.resolve().is_relative_to(root.resolve()), "Proof file escapes its declared root")
    return file


def verify_public_input(raw, provenance_bytes, descriptor=DESCRIPTOR):
    require(descriptor == DESCRIPTOR, "Public input descriptor differs from reviewed source")
    require(hashlib.sha256(raw).hexdigest() == RAW_SHA256 and len(raw) == 787610, "Source-bound raw public response changed")
    require(hashlib.sha256(provenance_bytes).hexdigest() == PROVENANCE_SHA256, "Source-bound public provenance changed")
    provenance = json.loads(provenance_bytes.decode("utf-8", errors="strict"))
    no_authority(provenance)
    require(provenance.get("schema") == "swissknife.openrouter-observed-public-input.v1"
            and provenance.get("source_url") == provenance.get("final_url") == SOURCE_URL
            and provenance.get("http_status") == 200 and provenance.get("reconstructed") is False
            and provenance.get("provider_execution") is False, "Actual public observation provenance required")
    for field in ("raw_sha256", "raw_bytes", "model_count", "model_ids_sha256", "observed_at"):
        require(provenance.get(field) == DESCRIPTOR[field], f"Public provenance {field} mismatch")
    observed = datetime.fromisoformat(provenance["observed_at"])
    requested = datetime.fromisoformat(provenance["requested_at"])
    require(requested.tzinfo is not None and observed.tzinfo is not None and requested <= observed
            <= datetime.now(timezone.utc), "Public input observation time is invalid")
    require(provenance.get("raw_filename") == f"{RAW_SHA256}.json", "Wrong immutable public filename")
    value = json.loads(raw.decode("utf-8", errors="strict"))
    models = value.get("data") if type(value) is dict else None
    require(type(models) is list and len(models) == 468 and all(type(item) is dict for item in models), "Complete raw model response required")
    ids = [item.get("id") for item in models]
    require(all(type(item) is str and item and item == item.strip() and "/" in item for item in ids)
            and len(set(ids)) == 468, "Complete unique model IDs required")
    ids = sorted(ids)
    require(hashlib.sha256(compact(ids)).hexdigest() == MODEL_IDS_SHA256 and TARGET_MODEL in ids
            and OLD_MODEL not in ids, "Same count cannot substitute for the exact source-bound model set")
    return ids


def verify_metadata(metadata):
    require(type(metadata) is dict, "Actual browser catalog metadata required")
    fields = {"mode": "snapshot", "verified": True, "input_sha256": RAW_SHA256,
              "model_ids_sha256": MODEL_IDS_SHA256, "model_count": 468, "raw_bytes": 787610,
              "original_source": SOURCE_URL, "observed_at": OBSERVED_AT,
              "local_url": DESCRIPTOR["local_url"], "provenance_url": DESCRIPTOR["provenance_url"],
              "provenance_sha256": PROVENANCE_SHA256, "cache_ttl_ms": None}
    require(all(key in metadata and type(metadata[key]) is type(value) and metadata[key] == value for key, value in fields.items())
            and metadata.get("stale") is False and metadata.get("error") is None,
            "Actual verified snapshot mode, provenance, or permanent input cache differs")
    require(number(metadata.get("cache_age_ms")) and metadata["cache_age_ms"] >= 0, "Actual public metadata age must be visible")


def selector(model, action):
    return (f'[data-openrouter-model="{model}"][data-openrouter-provider="{model.split("/")[0]}"]'
            f'[data-openrouter-placement="catalog"][data-openrouter-action="{action}"]')


def verify_state(state, model_ids):
    require(type(state) is dict and state.get("mode") == "snapshot", "Actual owning application snapshot mode required")
    verify_metadata(state.get("metadata"))
    require(state.get("model_ids") == model_ids and state.get("model_count") == 468
            and state.get("api_key_present") is False, "Actual complete browser model set differs")
    require(type(state.get("guard_checked_launches")) is int and state["guard_checked_launches"] >= 1,
            "Canonical actual launch guard did not execute")
    favorites = state.get("favorite_ids")
    require(type(favorites) is list and favorites == sorted(set(favorites)) and all(item in model_ids for item in favorites), "Invalid actual favorite model identities")
    require(state.get("default_model") in model_ids and state.get("current_tab") in {"models", "playground"}, "Actual selected model/tab differs")
    require(type(state.get("stored")) is dict and set(state["stored"]) == STORAGE_KEYS
            and all(value is None or type(value) is str for value in state["stored"].values()), "Exact actual owned storage bytes required")
    require(json.loads(state["stored"]["openrouter_favorites"] or "[]") == favorites, "Actual favorite preference was not persisted")
    require(all(type(state.get(field)) is list for field in ("events", "writes", "dialogs", "selected_copies")), "Actual ordered action observations required")


def verify_report(report, directory, model_ids):
    require(report.get("candidate_module_override") is False, "Candidate module override is not canonical proof")
    require(report.get("schema") == "swissknife.openrouter-catalog-snapshot-smoke.v1" and report.get("passed") is True,
            "Actual canonical browser schema/pass required")
    no_authority(report)
    require(report.get("source_sha256") == report.get("canonical_source_sha256") == report.get("canonical_source_sha256_after") == SOURCES[APP]
            and report.get("canonical_source_unchanged") is True and report.get("candidate_source_unchanged") is True,
            "Canonical source must bind the entire actual browser run")
    require(report.get("descriptor") == DESCRIPTOR and report.get("flag") == "1", "Actual Vite input mode/descriptor differs")
    require(report.get("guard_coverage") is True and report.get("guard_source_sha256") == SOURCES[GUARD], "Canonical actual guard coverage required")
    browser_sources = {key: SOURCES[key] for key in (APP, MAIN, HELPER, COLLECTOR, SMOKE)}
    browser_sources["guard_module"] = SOURCES[GUARD]
    require(report.get("source_hashes") == browser_sources, "Canonical browser source pins differ")
    for field in ("posts_attempted", "posts_blocked", "external_catalog_gets", "page_errors", "network_observer_errors"):
        require(report.get(field) == [], f"Unexpected actual browser {field}")
    require(not report.get("error") and not report.get("cleanup_or_source_failure"), "Actual browser run failed")
    profiles = report.get("profiles")
    require(type(profiles) is list and [item.get("transport") for item in profiles] == list(TRANSPORTS), "Both exact profiles required")
    expected_pngs = set()
    for profile in profiles:
        transport = profile["transport"]
        require(profile.get("passed") is True and profile.get("nonunique_selectors") == [] and profile.get("missing_model_actions") == [], "Full real rendered controls must remain uniquely actionable")
        initial = profile.get("initial")
        verify_state(initial, model_ids)
        require(initial["favorite_ids"] == [], "Fresh actual browser preference baseline required")
        controls = profile.get("original_controls")
        require(type(controls) is list and len(controls) == 1881 and all(type(row.get("selector")) is str for row in controls), "All1881 actual controls required")
        selectors = [row["selector"] for row in controls]
        require(len(set(selectors)) == 1881 and {selector(model, action) for model in model_ids for action in ("favorite", "info", "try", "default")}.issubset(selectors), "All four exact controls for every real model required")
        preflight = profile.get("actual_guard_preflight")
        require(type(preflight) is dict and preflight.get("schema") == "swissknife.openrouter-input-preflight.v1"
                and preflight.get("checked_launches") == 1 and preflight.get("provider_execution") is False,
                "Actual mounted guard preflight required")
        no_authority(preflight)
        cases = profile.get("cases")
        require(type(cases) is list and len(cases) == 10, "All ten genuine local actions required per profile")
        for index, (case, (action, model)) in enumerate(zip(cases, ACTIONS)):
            require(case.get("index") == index and case.get("action") == action and case.get("model") == model
                    and case.get("selector") == selector(model, action) and number(case.get("click_ms"))
                    and 0 <= case["click_ms"] <= 8000, "Actual trusted control identity/timing differs")
            before, after = case.get("before"), case.get("after")
            verify_state(before, model_ids); verify_state(after, model_ids)
            require(after["events"][:len(before["events"])] == before["events"]
                    and case.get("trusted_events") == after["events"][len(before["events"]):]
                    and any(event.get("trusted") is True and event.get("model") == model and event.get("action") == action
                            and event.get("placement") == "catalog" for event in case["trusted_events"]), "Actual trusted matching action event required")
            require(after["writes"][:len(before["writes"])] == before["writes"], "Actual write history is discontinuous")
            writes = after["writes"][len(before["writes"]):]
            if action == "favorite":
                added = index != 6
                require((model in after["favorite_ids"]) is added and any(item.get("key") == "openrouter_favorites" for item in writes), "Genuine favorite persistence differs")
            elif action == "info":
                require(any(model in text for text in after["dialogs"][len(before["dialogs"]):]), "Actual real-model information dialog missing")
            elif action == "try":
                require(after["current_tab"] == "playground" and after["default_model"] == model and after["stored"] == before["stored"] and writes == [], "Try must remain an unsaved local selection")
            else:
                require(after["default_model"] == json.loads(after["stored"]["openrouter_settings"])["defaultModel"] == model
                        and {item.get("key") for item in writes} == STORAGE_KEYS and len(writes) == 4,
                        "Explicit Default must preserve all four original real preference writes")
                copies = after["selected_copies"]
                require(len(copies) == 1 + int(model in after["favorite_ids"]) and all(item.get("model") == model
                        and item.get("text") == "✓ Default" and item.get("pressed") == "true" and item.get("card_default") is True for item in copies), "Actual selected catalog/favorite copies differ")
                if index in (4, 9):
                    require(after["stored"] == before["stored"], "Repeated explicit Default changed saved values")
            for phase in ("before", "after"):
                name = f"{transport}-{index}-{phase}.png"
                require(case.get("screenshot_" + phase) == name, "Actual screenshot/action identity differs")
                expected_pngs.add(name)
        final = profile.get("final_reopen")
        verify_state(final, model_ids)
        require(final["default_model"] == TARGET_MODEL and final["favorite_ids"] == [TARGET_MODEL]
                and final["guard_checked_launches"] >= 12, "Real saved preferences and per-launch guard must survive reopen")
        refresh = profile.get("programmatic_refresh")
        require(type(refresh) is dict and refresh.get("method") == "existing app.loadModels()" and refresh.get("ui_control") is False
                and refresh.get("input_response_count_before") == refresh.get("input_response_count_after") == 2,
                "Existing non-UI Refresh observation must retain the actual bound input without refetch")
        verify_metadata(refresh.get("before")); verify_metadata(refresh.get("after"))
    inputs = report.get("input_responses")
    require(type(inputs) is list and len(inputs) == 4, "Actual raw/provenance GETs required in both fresh profiles")
    seen = set()
    for row in inputs:
        identity = row.get("transport"), row.get("path")
        require(identity not in seen and identity[0] in TRANSPORTS and identity[1] in (DESCRIPTOR["local_url"], DESCRIPTOR["provenance_url"])
                and row.get("status") == 200 and row.get("intercepted") is False, "Actual immutable asset route/status differs")
        seen.add(identity)
        expected = RAW_SHA256 if identity[1] == DESCRIPTOR["local_url"] else PROVENANCE_SHA256
        require(row.get("sha256") == expected and type(row.get("bytes")) is int and row["bytes"] > 0, "Actual public asset response digest differs")
        file = local_file(directory, row.get("file"))
        require(file.name == f"{identity[0]}-actual-{'catalog' if expected == RAW_SHA256 else 'provenance'}.json"
                and sha(regular(file)) == expected and file.stat().st_size == row["bytes"], "Archived actual browser response bytes differ")
    modules = report.get("module_responses")
    require(type(modules) is list and [row.get("transport") for row in modules] == list(TRANSPORTS)
            and all(row.get("status") == 200 and row.get("candidate_module_override") is False
                    and row.get("original_path") == "/js/apps/openrouter.js" and row.get("raw_source_sha256") == SOURCES[APP]
                    and row.get("actual_vite_env_injection") is True and row.get("actual_vite_snapshot_env") is True
                    and row.get("source_selection") == "canonical" and type(row.get("from_service_worker")) is bool
                    and digest(row.get("transformed_sha256")) for row in modules), "Canonical actual module delivery required")
    for row in modules:
        file = local_file(directory, row.get("file"))
        require(file.name == f'{row["transport"]}-actual-vite-module.js' and sha(regular(file)) == row["transformed_sha256"],
                "Archived actual Vite module response bytes differ")
        compiled = file.read_text()
        require('import.meta.env =' in compiled and re.search(r'"VITE_VDG_OPENROUTER_CATALOG_SNAPSHOT"\s*:\s*"1"', compiled)
                and RAW_SHA256 in compiled and PROVENANCE_SHA256 in compiled, "Actual Vite compilation/input contract differs")
    require(type(report.get("screenshot_sha256")) is dict and set(report["screenshot_sha256"]) == expected_pngs
            and {file.name for file in directory.glob("*.png")} == expected_pngs, "Exactly40 actual action PNGs required")
    for name, expected in report["screenshot_sha256"].items():
        png(directory / name, expected)
    verify_cleanup(report)
    return {"actual_profiles": 2, "actual_actions": 20, "actual_pngs": 40, "actual_posts": 0,
            "actual_models_per_profile": 468, "actual_controls_per_profile": 1881,
            "source_bound_public_input_sha256": RAW_SHA256, "canonical_guard_verified": True}


def verify_cleanup(report):
    require(report.get("owned_resources_closed") is True, "Actual owned resources remain unclosed")
    tracked = report.get("tracked_processes")
    require(type(tracked) is list and len(tracked) >= 2, "Actual owned process identities required")
    identities = set()
    for row in tracked:
        require(all(type(row.get(key)) is int and row[key] > 0 for key in ("pid", "uid", "pgid", "sid"))
                and type(row.get("ppid")) is int and row["ppid"] >= 0 and str(row.get("start_tick", "")).isdigit()
                and row.get("same_identity_alive") is False, "Actual PID/start/UID cleanup fence differs")
        identity = row["pid"], str(row["start_tick"])
        require(identity not in identities, "Duplicate owned process identity")
        identities.add(identity)
    resources = report.get("resources", {})
    for key in ("vite_pid", "chrome_pid"):
        require(type(resources.get(key)) is int and any(row["pid"] == resources[key] for row in tracked)
                and resources.get(key + "_absent") is True, "Exact owned server/browser absence required")


def verify_failure(archive=ARCHIVE, root=ROOT):
    directory = archive / "actual-failure"
    for name, expected in FAILURE_PINS.items():
        require(sha(regular(directory / name)) == expected, "Immutable original failure/deadline evidence changed")
    log = (directory / "supervisor-log-at-stop.log").read_text()
    require("Test timeout of 21600000ms exceeded." in log, "Original declared six-hour deadline must remain explicit")
    summary = {}
    for transport, row_count, image_count in (("http", 2073, 4124), ("libp2p", 388, 764)):
        checkpoint = json.loads((directory / f"{transport}-checkpoint.json").read_bytes())
        require(checkpoint.get("schema") == "swissknife.vdg-capture-checkpoint.v1" and checkpoint.get("target") == "local"
                and checkpoint.get("transport") == transport and checkpoint.get("capture_complete") is False
                and checkpoint.get("work_complete") is False and checkpoint.get("completion_authority") is False
                and digest(checkpoint.get("input_fingerprint")), "Original partial capture cannot be completed or relabeled")
        payload = checkpoint["payload"]
        require(hashlib.sha256(compact(payload)).hexdigest() == checkpoint["payload_sha256"] and payload.get("pageerrors") == []
                and payload.get("observations") == [] and len(payload["rows"]) == row_count
                and len(payload["image_hashes"]) == image_count, "Original checkpoint payload/count evidence differs")
        failures = [(index, row) for index, row in enumerate(payload["rows"]) if row.get("failure_reasons")]
        require([index for index, _ in failures] == ([] if transport == "http" else [83, 84, 85, 86]), "Original failures may not be erased or manufactured")
        for (index, row), action in zip(failures, ("favorite", "info", "try", "default")):
            require(row.get("app_id") == row.get("launch_id") == "openrouter" and row.get("selector") == selector(OLD_MODEL, action)
                    and row.get("clicked") is False and row.get("visibility") == "not-visible" and row.get("failure_reasons") == ["not-visible"]
                    and row.get("pageerrors") == [] and row.get("mcp_call_count") == row.get("incomplete_mcp_call_count") == 0,
                    "Original exact missing catalog ID/action failure differs")
        for relative, expected in payload["image_hashes"].items():
            # Physical files may live behind the reviewed logical capture symlink.
            require(relative.startswith("swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vdg/live-clicks/")
                    and not Path(relative).is_absolute() and ".." not in Path(relative).parts, "Original PNG path escapes capture namespace")
            png(root / relative, expected)
        summary[transport] = {"partial_rows": row_count, "declared_pngs": image_count, "row_failures": len(failures), "capture_complete": False}
    return {"original_partial_captures": summary, "original_six_hour_deadline_preserved": True,
            "historical_raw_catalog_unavailable": True, "precise_upstream_rename_not_established": True}


def verify_preservation(record, live, baseline):
    no_authority(record); no_authority(baseline)
    require(record.get("schema") == "swissknife.vdg-openrouter-catalog-preservation.v1" and record.get("before_app_sha256") == OLD_APP_SHA256
            and record.get("after_app_sha256") == SOURCES[APP], "Wrong actual application source boundary")
    require(baseline.get("schema") == "swissknife.vdg-catalog-input-ten-before.v1"
            and baseline.get("source_before", {}).get(APP) == OLD_APP_SHA256, "Authoritative ten-cell baseline required")
    require(set(record.get("cells", {})) == set(baseline.get("cells", {})) == set(live.get("fingerprints", {}))
            == set(live.get("acquisitions", {})) == UNAFFECTED and live.get("inventory", {}).get("current") is True,
            "Exactly ten actual unaffected source-current cells required")
    total = 0
    for cell, row in record["cells"].items():
        before, current = baseline["cells"][cell], live["acquisitions"][cell]
        require(row.get("before_input_fingerprint") == before["input_fingerprint"] == row.get("after_input_fingerprint")
                == live["fingerprints"][cell] == current.get("input_fingerprint"), f"Unaffected fingerprint changed: {cell}")
        require(row.get("run_id") == before["run_id"] == current.get("run_id") and row.get("report_sha256") == before["report_sha256"]
                == current.get("report_sha256") and type(current.get("row_count")) is int and current["row_count"] == before["row_count"]
                and current.get("capture_complete") is True, f"Unaffected acquisition identity/report/count changed: {cell}")
        total += current["row_count"]
    require(total == 1714, "Original1714 unaffected rows must remain exact")
    return {"unaffected_cells_preserved": 10, "unaffected_rows_preserved": total}


def parse_board(text):
    require(type(text) is str, "Actual board text required")
    matches = list(re.finditer(r"(?m)^## (VDG-\d+(?:-R\d+)?)\b[^\n]*", text))
    require(matches, "No actual VDG task headers")
    tasks = {}
    for index, match in enumerate(matches):
        task = match.group(1)
        require(task not in tasks, "Duplicate task identity")
        block = text[match.start():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip("\n")
        fields = {}
        for line in block.splitlines()[1:]:
            field = re.fullmatch(r"- ([^:]+):\s*(.*)", line)
            if field:
                key = re.sub(r"[^a-z0-9]+", "_", field.group(1).lower()).strip("_")
                require(key not in fields, f"Duplicate task field: {task}/{key}")
                fields[key] = field.group(2).strip()
        tasks[task] = {"fields": fields, "block": block}
    return text[:matches[0].start()].strip("\n"), tasks


def dependencies(fields):
    return [value.strip() for value in fields.get("depends_on", "").split(",") if value.strip()]


def verify_dag(tasks):
    active, done = set(), set()
    def visit(task):
        require(task in tasks and task not in active, f"Missing dependency or cycle: {task}")
        if task in done:
            return
        active.add(task)
        deps = dependencies(tasks[task]["fields"])
        require(len(deps) == len(set(deps)), "Duplicate dependency edge")
        for value in deps:
            visit(value)
        active.remove(task); done.add(task)
    for task in tasks:
        visit(task)


def verify_transition(before_text, after_text, *, expected_repair_fields=None):
    """Pure admission-only comparison of immutable original64 and amended65 rows.

    The live board can later progress normally. No input files or child commands
    are read/run by this API; the admitter owns the current lifecycle fence.
    """
    before_preamble, before = parse_board(before_text)
    after_preamble, after = parse_board(after_text)
    require(len(before) == 64 and len(after) == 65 and REPAIR not in before and set(after) == set(before) | {REPAIR}, "Only one additive64→65 repair task is allowed")
    require(before_preamble == after_preamble and list(after) == [*before, REPAIR], "Board preamble/history/task order changed")
    require(before.get("VDG-013-R22", {}).get("fields", {}).get("status") == "completed", "R23 requires naturally completed R22")
    for task, entry in before.items():
        wanted = dict(entry["fields"])
        allowed = set()
        if task in COMMANDS:
            require(wanted.get("status") == "pending", "Only the six pending downstream command contracts may strengthen")
            for field, original in zip(("deterministic_command", "validation"), COMMANDS[task]):
                require(wanted.get(field) == original, "Original child argv/declared bound differs")
                wanted[field] = WRAPPER_PREFIX + original; allowed.add(field)
        if task == "VDG-039-R01":
            require(REPAIR not in dependencies(entry["fields"]), "Repair dependency already exists in original snapshot")
            wanted["depends_on"] = ", ".join([*dependencies(entry["fields"]), REPAIR]); allowed.add("depends_on")
        require(after[task]["fields"] == wanted, f"Existing task/status/budget/history changed: {task}")
        # Preserve even non-field acceptance/prose and exact original formatting.
        normalized = after[task]["block"]
        for field in allowed:
            label = next(line.split(":", 1)[0] for line in entry["block"].splitlines() if line.startswith("- ")
                         and re.sub(r"[^a-z0-9]+", "_", line[2:].split(":", 1)[0].lower()).strip("_") == field)
            pattern = r"(?m)^" + re.escape(label) + r":.*$"
            original_line = next(line for line in entry["block"].splitlines() if line.startswith(label + ":"))
            normalized, count = re.subn(pattern, lambda _: original_line, normalized)
            require(count == 1, "Authorized task field identity differs")
        require(normalized == entry["block"], f"Existing task prose or formatting changed: {task}")
    fields = after[REPAIR]["fields"]
    required = {"status": "pending", "priority": "P0", "track": "gate-recovery", "depends_on": "VDG-013-R22",
                "recovery_for": "VDG-039-R01", "deterministic_command": VERIFY_COMMAND, "validation": VERIFY_COMMAND,
                "resource_class": "cpu-small", "implementation_timeout_seconds": "1800"}
    require(all(fields.get(key) == value for key, value in required.items()) and "completion" not in fields,
            "New R23 must be a pending read-only1800s repair after completedR22")
    require(set(fields) == set(required) | {"predicted_files", "acceptance", "conflict_policy"}
            and all(fields[key] for key in ("predicted_files", "acceptance", "conflict_policy")), "Unexpected R23 task contract fields")
    if expected_repair_fields is not None:
        require(fields == expected_repair_fields, "Reviewed exact R23 repair template differs")
    verify_dag(after)
    return {"before_tasks": 64, "after_tasks": 65, "added_task": REPAIR,
            "guarded_tasks": list(COMMANDS), "guarded_command_fields": 12,
            "original_child_argv_and_bounds_preserved": True, "all_existing_statuses_preserved": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


def final_go_preamble(current_preamble, admitted_preamble):
    return (admitted_preamble.splitlines().count(PROGRAM_NO_GO_LINE) == 1
            and admitted_preamble.splitlines().count(PROGRAM_GO_LINE) == 0
            and current_preamble == admitted_preamble.replace(PROGRAM_NO_GO_LINE, PROGRAM_GO_LINE, 1))


def verify_current_contract(current_text, admitted_text, *, final_go_evidence=None):
    current_preamble, current = parse_board(current_text)
    admitted_preamble, admitted = parse_board(admitted_text)
    final_go = current_preamble != admitted_preamble
    require((not final_go or final_go_preamble(current_preamble, admitted_preamble))
            and list(current) == list(admitted), "Live board identities/preamble changed")
    volatile = {"status", "completion", "evidence"}
    for task in admitted:
        original, actual = admitted[task]["fields"], current[task]["fields"]
        if original.get("status") == "completed":
            require(actual == original and current[task]["block"] == admitted[task]["block"],
                    f"Historical completed task fields/prose changed: {task}")
            continue
        require({key: value for key, value in actual.items() if key not in volatile}
                == {key: value for key, value in original.items() if key not in volatile}, f"Live execution contract changed: {task}")
        require(actual.get("status") in {"pending", "ready", "in progress", "in_progress", "completed", "blocked"}, "Invalid live task status")
        original_progress = {}
        for line in admitted[task]["block"].splitlines():
            match = re.fullmatch(r"- ([^:]+):\s*(.*)", line)
            if match:
                key = re.sub(r"[^a-z0-9]+", "_", match.group(1).lower()).strip("_")
                if key in volatile:
                    original_progress[key] = line
        restored = []
        for line in current[task]["block"].splitlines():
            match = re.fullmatch(r"- ([^:]+):\s*(.*)", line)
            key = re.sub(r"[^a-z0-9]+", "_", match.group(1).lower()).strip("_") if match else None
            if key not in volatile:
                restored.append(line)
            elif key in original_progress:
                restored.append(original_progress[key])
        require("\n".join(restored) == admitted[task]["block"], f"Live task title/prose changed: {task}")
    verify_dag(current)
    if final_go:
        require(len(current) == 65 and all(entry["fields"].get("status") == "completed" for entry in current.values()),
                "Final GO requires all65 natural completions including060")
        verify_final_go_evidence(final_go_evidence, current["VDG-060"]["fields"])


def without_generation(value):
    require(type(value) is dict, "Actual final report object required")
    return {key: item for key, item in value.items() if key != "generated_at"}


def parse_closeout_log(text, fields, *, root=ROOT):
    """Read existing command/stdout evidence; never invent a validator exit field."""
    producer = "$ " + fields["deterministic_command"] + f"  # cwd={root}\n"
    validator = "$ " + fields["validation"] + f"  # cwd={root}\n"
    at = text.rfind(producer)
    require(at >= 0 and (at == 0 or text[at - 1] == "\n"), "Actual latest060 producer log boundary missing")
    tail = text[at + len(producer):]
    next_at = re.search(r"(?m)^\$ ", tail)
    require(next_at is not None and tail[next_at.start():].startswith(validator), "Actual060 validator must follow its producer")
    producer_output = tail[:next_at.start()]
    require(producer_output.splitlines().count("closeout allowed") == 1
            and "closeout withheld" not in producer_output, "Actual060 producer did not allow closeout")
    remainder = tail[next_at.start() + len(validator):]
    end = re.search(r"(?m)^\$ ", remainder)
    validation_output = remainder[:end.start()] if end else remainder
    summaries = []
    for line in validation_output.splitlines():
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        if type(value) is dict and "decision" in value and "passed" in value:
            summaries.append(value)
    require(summaries, "Actual060 aggregate validator stdout missing")
    return {"producer_segment_sha256": hashlib.sha256((producer + producer_output).encode()).hexdigest(),
            "validator_segment_sha256": hashlib.sha256((validator + validation_output).encode()).hexdigest(),
            "validator_summary": summaries[-1]}


def current_closeout_contract(fields, *, root=ROOT):
    """Evaluate only the actual pinned pure contract functions, not package init."""
    namespace = {"Path": Path, "hashlib": hashlib, "json": json, "marshal": marshal, "CodeType": CodeType}
    lane = ast.parse((root / LANE_SOURCE).read_text())
    gate = ast.parse((root / GATE_SOURCE).read_text())
    wanted = {"_file_digest", "_declared_evidence", "_runtime_contract_code", "_command_contract"}
    definitions = [node for node in lane.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    definitions += [node for node in gate.body if isinstance(node, ast.FunctionDef) and node.name == "_is_source_path"]
    require({node.name for node in definitions} == wanted | {"_is_source_path"}, "Actual lane contract implementation unavailable")
    suffixes = next((node.value for node in gate.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "_SOURCE_SUFFIXES" for target in node.targets)), None)
    require(suffixes is not None, "Actual lane source classification unavailable")
    namespace["_SOURCE_SUFFIXES"] = ast.literal_eval(suffixes)
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *definitions], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(root / LANE_SOURCE), "exec"), namespace)
    return namespace["_command_contract"](fields, shlex.split(fields["deterministic_command"]),
                                           shlex.split(fields["validation"]), repo_root=root)


def verify_final_go_evidence(proof, fields):
    require(type(proof) is dict and proof.get("schema") == "swissknife.vdg-r23-final-go-evidence.v1", "Actual final GO evidence required")
    no_authority(proof)
    require(proof.get("inventory", {}).get("current") is True and set(proof.get("acquisitions", {})) == FINAL_CELLS,
            "All12 actual source-current acquisitions required before finalGO")
    for cell, acquisition in proof["acquisitions"].items():
        family, transport = cell.split("/")
        require(acquisition.get("family") == family and acquisition.get("transport") == transport
                and acquisition.get("capture_complete") is True and digest(acquisition.get("input_fingerprint"))
                and digest(acquisition.get("report_sha256")) and type(acquisition.get("row_count")) is int
                and acquisition["row_count"] > 0, "Actual final acquisition is incomplete/unbound: " + cell)
    require(set(proof.get("families", {})) == FINAL_FAMILIES, "All six strict family results required")
    for family, record in proof["families"].items():
        fresh, stored = record.get("fresh"), record.get("stored")
        require(type(fresh) is dict and fresh.get("schema") == "swissknife.virtual-desktop-gui-mcp-family.v1"
                and fresh.get("family") == family and fresh.get("decision") == "GO" and fresh.get("passed") is True
                and fresh.get("clicked") is True and fresh.get("gap_count") == 0 and fresh.get("gaps") == []
                and fresh.get("gap_counts") == {} and fresh.get("reasons") == []
                and digest(fresh.get("input_fingerprint")) and fresh.get("work_complete") is False
                and fresh.get("completion_authority") is False and digest(record.get("stored_sha256"))
                and without_generation(fresh) == without_generation(stored), "Current strict family GO/stored semantics differ: " + family)
    aggregate, stored = proof.get("aggregate"), proof.get("stored_aggregate")
    require(type(aggregate) is dict and aggregate.get("schema") == "swissknife.virtual-desktop-gui-mcp-coverage.v1"
            and aggregate.get("decision") == "GO" and aggregate.get("passed") is True and aggregate.get("clicked") is True
            and aggregate.get("gap_count") == 0 and aggregate.get("gaps") == [] and aggregate.get("gap_counts") == {}
            and aggregate.get("reasons") == [] and aggregate.get("repair_tasks") == []
            and aggregate.get("work_complete") is False and aggregate.get("completion_authority") is False
            and digest(proof.get("aggregate_sha256")) and without_generation(aggregate) == without_generation(stored),
            "Fresh strict aggregate GO and actual final aggregate must agree")
    rows = aggregate.get("families")
    require(type(rows) is list and len(rows) == 6 and {item.get("family") for item in rows} == FINAL_FAMILIES,
            "Aggregate must contain exactly all six current families")
    for row in rows:
        fresh = proof["families"][row["family"]]["fresh"]
        require(row.get("input_fingerprint") == fresh["input_fingerprint"] and row.get("evidence_sources") == fresh["evidence_sources"]
                and row.get("decision") == "GO" and row.get("passed") is True and row.get("clicked") is True
                and row.get("gap_count") == 0, "Final aggregate family source provenance differs")
    require(fields.get("status") == "completed" and fields.get("deterministic_command") == WRAPPER_PREFIX + COMMANDS["VDG-060"][0]
            and fields.get("validation") == WRAPPER_PREFIX + COMMANDS["VDG-060"][1], "Original060 producer and validator must naturally complete")
    completion = fields.get("completion", "")
    require(re.fullmatch(r"lane_resume deterministic command exit 0 at \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", completion)
            and proof.get("completion_note") == completion, "Actual natural060 completion note required")
    require(proof.get("lane_source_sha256") == FINAL_LANE_SOURCES and digest(proof.get("ledger_sha256"))
            and digest(proof.get("supervisor_log_sha256")) and digest(proof.get("current_contract")), "Actual lane/log/ledger binding required")
    producer = proof.get("producer_record", {})
    require(type(producer) is dict and type(producer.get("exit_code")) is int and producer["exit_code"] == 0
            and producer.get("contract") == proof["current_contract"]
            and producer.get("retry_contract") == proof["current_contract"]
            and type(producer.get("before")) is dict and producer["before"]
            and producer.get("after") == producer["before"], "Actual current060 read-only producer outcome required")
    log = proof.get("closeout_log", {})
    require(type(log) is dict, "Actual ordered060 command log required")
    summary = log.get("validator_summary", {})
    require(digest(log.get("producer_segment_sha256")) and digest(log.get("validator_segment_sha256"))
            and summary.get("decision") == "GO" and summary.get("passed") is True and summary.get("clicked") is True
            and summary.get("gap_count") == 0 and summary.get("gap_counts") == {} and summary.get("repair_tasks") == []
            and all(summary.get(key) == aggregate.get(key) for key in ("observed_invocation_count", "executed_tool_count")),
            "Actual ordered060 validator GO output required")
    return {"actual_acquisitions": 12, "strict_family_go_count": 6, "aggregate_sha256": proof["aggregate_sha256"],
            "ledger_sha256": proof["ledger_sha256"], "supervisor_log_sha256": proof["supervisor_log_sha256"],
            "natural_060_completion_verified": True, "program_banner_only": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


def live_final_go_evidence(current_text):
    _, current = parse_board(current_text)
    require(len(current) == 65 and all(entry["fields"].get("status") == "completed" for entry in current.values()),
            "FinalGO observations require all65 tasks completed first")
    for name, expected in FINAL_LANE_SOURCES.items():
        require(sha(regular(ROOT / name)) == expected, "Actual reviewed lane completion algorithm changed")
    code = '''
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {FAMILIES,loadFamilyEvidence}=require('./scripts/vdg-evidence.cjs');
const {buildCoverage}=require('./scripts/build-gui-mcp-coverage.cjs');
const {checkCapture}=require('./scripts/check-vdg-capture.cjs');
const {inspectInventory}=require('./scripts/vdg-inventory-contract.cjs');
const root=process.cwd(),evidence=path.join(root,'test-results/virtual-desktop-ipfs-mcp-orb');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const inventory=inspectInventory({sourceRoot:root,evidenceRoot:evidence});
if(inventory.current!==true)throw Error('Current inventory required');
const acquisitions={},families={},files=[];
for(const family of Object.keys(FAMILIES)){
 for(const transport of ['http','libp2p'])acquisitions[family+'/'+transport]=checkCapture(family,transport,{sourceRoot:root,evidenceRoot:evidence});
 const file=path.join(evidence,'vdg/families',FAMILIES[family].target+'.json'),bytes=fs.readFileSync(file);
 const fresh=loadFamilyEvidence(family,{sourceRoot:root,evidenceRoot:evidence});
 families[family]={fresh,stored:JSON.parse(bytes),stored_sha256:hash(bytes)};files.push([file,hash(bytes)]);
}
const file=path.join(evidence,'gui-mcp-coverage.json'),bytes=fs.readFileSync(file);
const aggregate=buildCoverage(Object.values(families).map(row=>row.fresh));files.push([file,hash(bytes)]);
for(const [file,digest]of files)if(hash(fs.readFileSync(file))!==digest)throw Error('Final report changed during read-only checks');
console.log(JSON.stringify({inventory,acquisitions,families,aggregate,stored_aggregate:JSON.parse(bytes),aggregate_sha256:hash(bytes)}));
'''
    result = subprocess.run(["node", "--input-type=commonjs", "-e", code], cwd=SWISS, capture_output=True, text=True, timeout=180)
    require(result.returncode == 0, "Actual read-only final GO verification failed: " + result.stderr[-2000:])
    proof = json.loads(result.stdout)
    lane = WATCHDOG / "lanes/vdg-planning"
    ledger_bytes = regular(lane / "lane_resume_attempts.json").read_bytes()
    ledger = json.loads(ledger_bytes)
    log_bytes = (lane / "supervisor.log").read_bytes()
    fields = current["VDG-060"]["fields"]
    proof.update(schema="swissknife.vdg-r23-final-go-evidence.v1", completion_note=fields.get("completion"),
                 lane_source_sha256=dict(FINAL_LANE_SOURCES), ledger_sha256=hashlib.sha256(ledger_bytes).hexdigest(),
                 supervisor_log_sha256=hashlib.sha256(log_bytes).hexdigest(),
                 producer_record=ledger.get("_command_evidence", {}).get("VDG-060"),
                 current_contract=current_closeout_contract(fields), closeout_log=parse_closeout_log(log_bytes.decode(), fields),
                 gui_acceptance=False, work_complete=False, completion_authority=False)
    require((lane / "lane_resume_attempts.json").read_bytes() == ledger_bytes and (lane / "supervisor.log").read_bytes() == log_bytes,
            "Actual closeout ledger/log changed during final checks")
    for name, expected in FINAL_LANE_SOURCES.items():
        require(sha(regular(ROOT / name)) == expected, "Actual completion algorithm changed during final checks")
    verify_final_go_evidence(proof, fields)
    return proof


def verify_admission(archive=ARCHIVE, watchdog=WATCHDOG):
    receipt = json.loads(regular(watchdog / "catalog-input-admission.json").read_bytes())
    no_authority(receipt)
    require(receipt.get("schema") == "swissknife.vdg-openrouter-catalog-admission.v1" and receipt.get("apply_requested") is True
            and receipt.get("tasks_before") == 64 and receipt.get("tasks_after") == 65
            and receipt.get("admission", {}).get("admitted") is True, "Actual applied64→65 R23 admission receipt required")
    before_path = watchdog / "completion-board-before-catalog-input.todo.snapshot"
    after_path = watchdog / "completion-board-after-catalog-input.todo.snapshot"
    require(receipt.get("before_snapshot") == before_path.name and receipt.get("after_snapshot") == after_path.name,
            "Admission must name the immutable reviewed snapshot files")
    require(digest(receipt.get("board_before_sha256")) and sha(regular(before_path)) == receipt["board_before_sha256"]
            and digest(receipt.get("board_after_sha256")) and sha(regular(after_path)) == receipt["board_after_sha256"], "Immutable admission snapshot bytes differ")
    before, after = before_path.read_text(), after_path.read_text()
    baseline = bound_json(archive / "unaffected-ten-before.json", BASELINE_SHA256)
    require(receipt["board_before_sha256"] == baseline["taskboard_sha256"], "Admission did not begin at the actual held original board")
    require(type(receipt.get("repair_fields")) is dict, "Admission must preserve the reviewed repair row template")
    summary = verify_transition(before, after, expected_repair_fields=receipt["repair_fields"])
    require(receipt.get("transition") == summary, "Admission transition receipt differs")
    require(receipt.get("statuses_history_and_bounds_preserved") is True and receipt.get("guarded_command_fields") == 12
            and receipt.get("exact_original_child_argv_preserved") is True, "Admission cannot weaken existing task contracts")
    fence = receipt.get("identity", {})
    require(type(fence) is dict and fence == baseline["lifecycle_fence"] and fence.get("lane_pid") == 1960744
            and type(fence.get("lock_inode")) is int and fence["lock_inode"] > 0
            and type(fence.get("lock_device")) is int and digest(fence.get("hold_sha256")), "Actual stopped lifecycle fence receipt required")
    current_text = BOARD.read_text()
    current_preamble, current_tasks = parse_board(current_text)
    admitted_preamble, _ = parse_board(after)
    final_evidence = live_final_go_evidence(current_text) if final_go_preamble(current_preamble, admitted_preamble) else None
    verify_current_contract(current_text, after, final_go_evidence=final_evidence)
    return summary


def tap(text, count):
    require(type(count) is int and count > 0, "Fresh test count is not pinned")
    for field, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {field} (\d+)$", text, re.M) == [str(expected)], f"Wrong fresh TAP {field}")
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)]
            and len(re.findall(r"^ok \d+ - ", text, re.M)) == count and not re.search(r"^not ok\b", text, re.M), "Missing actual fresh test outcomes")


def live_evidence():
    code = '''
const path=require('node:path');
const {inspectInventory}=require('./scripts/vdg-inventory-contract.cjs');
const {checkCapture}=require('./scripts/check-vdg-capture.cjs');
const {FAMILIES}=require('./scripts/vdg-evidence.cjs');
const {captureInputFingerprint}=require('./scripts/vdg-capture-fingerprint.cjs');
const guard=require('./scripts/vdg-openrouter-catalog-input.cjs');
const root=process.cwd(),evidence=path.join(root,'test-results/virtual-desktop-ipfs-mcp-orb');
const inventory=inspectInventory({sourceRoot:root,evidenceRoot:evidence});
if(inventory.current!==true)throw Error('Current actual inventory required: '+inventory.reason);
guard.assertCatalogInventory(guard.assertLocalCatalogInput({env:{...process.env,VITE_VDG_OPENROUTER_CATALOG_SNAPSHOT:'1'}}));
const fingerprints={},acquisitions={};
for(const family of ['vdg-storage','vdg-datasets','vdg-accelerate','vdg-network','vdg-control'])for(const transport of ['http','libp2p']){
 const key=family+'/'+transport;
 fingerprints[key]=captureInputFingerprint(family,transport,{sourceRoot:root,evidenceRoot:evidence,definition:FAMILIES[family]});
 acquisitions[key]=checkCapture(family,transport,{sourceRoot:root,evidenceRoot:evidence});
}
console.log(JSON.stringify({inventory,fingerprints,acquisitions}));
'''
    result = subprocess.run(["node", "--input-type=commonjs", "-e", code], cwd=SWISS, capture_output=True, text=True, timeout=180)
    require(result.returncode == 0, "Actual read-only source-current inventory/captures failed: " + result.stderr[-3000:])
    return json.loads(result.stdout)


def verify_ready_proof(require_admission=True):
    # Deliberately first: unapproved/candidate proofs cannot execute children.
    receipt = bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    no_authority(receipt)
    require(receipt.get("schema") == "swissknife.vdg-openrouter-catalog-canonical-preflight.v1"
            and receipt.get("source_sha256") == SOURCES and all(digest(value) for value in SOURCES.values())
            and receipt.get("baseline_sha256") == BASELINE_SHA256, "Reviewed final source/input/baseline contract required")
    def sources():
        for name, expected in SOURCES.items():
            require(sha(regular(ROOT / name)) == expected, "Reviewed canonical source/input changed: " + name)
    sources()
    ids = verify_public_input((ROOT / RAW).read_bytes(), (ROOT / PROVENANCE).read_bytes())
    baseline = bound_json(ARCHIVE / "unaffected-ten-before.json", BASELINE_SHA256)
    require(baseline.get("source_before", {}).get(APP) == OLD_APP_SHA256
            and baseline["source_before"].get(MAIN) == SOURCES[MAIN]
            and baseline["source_before"].get(FINGERPRINT) == SOURCES[FINGERPRINT], "Actual original source/unchanged shared binding differs")
    for name, expected in baseline["source_before"].items():
        require(digest(expected) and sha(regular(local_file(ARCHIVE / "source-before", name))) == expected,
                "Immutable original source bytes differ")
    failure = verify_failure()
    report = bound_json(ARCHIVE / "canonical/result.json", receipt.get("canonical_report_sha256"))
    browser = verify_report(report, ARCHIVE / "canonical", ids)
    preservation = bound_json(ARCHIVE / "preservation.json", receipt.get("preservation_sha256"))
    live = live_evidence()
    preserved = verify_preservation(preservation, live, baseline)
    suites = ((44, [UNIT, "swissknife/test/scripts/vdg-openrouter-default-action.test.mjs",
                    "swissknife/test/scripts/vdg-openrouter-catalog.test.mjs", "swissknife/test/scripts/vdg-local-modal-ownership.test.mjs"]),
              (35, ["swissknife/scripts/vdg-openrouter-catalog-input.test.mjs"]))
    for count, files in suites:
        result = subprocess.run(["node", "--test", "--test-concurrency=1", "--test-reporter=tap", *[str(Path(name).relative_to("swissknife")) for name in files]],
                                cwd=SWISS, capture_output=True, text=True, timeout=180)
        print(result.stdout, end="")
        require(result.returncode == 0, f"Actual fresh{count} source tests failed: {result.stderr[-2000:]}")
        tap(result.stdout, count)
    # The historic R15 driver also verifies the current exact Local generator
    # and six-spec parity while running the original eight Todo tests once.
    result = subprocess.run(["python3", "-B", str(ROOT / R15_DRIVER)], cwd=ROOT, capture_output=True, text=True, timeout=180)
    print(result.stdout, end="")
    require(result.returncode == 0, "Actual historical diagnostic/current parity validation failed: " + result.stderr[-2000:])
    tap(result.stdout, 8)
    diagnostic = json.loads(result.stdout.strip().splitlines()[-1])
    no_authority(diagnostic)
    require(diagnostic.get("diagnostic_validated") is True and diagnostic.get("actual_cases") == 48
            and diagnostic.get("png_hashes_verified") == 96 and diagnostic.get("decision") == "rollback_optional_isolation"
            and diagnostic.get("current_all_family_generation_parity_verified") is True, "Historical optional-isolation rollback/current parity proof differs")
    sources()
    require(bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256) == receipt
            and bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"]) == report
            and bound_json(ARCHIVE / "unaffected-ten-before.json", BASELINE_SHA256) == baseline
            and bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"]) == preservation,
            "Reviewed immutable repair proof changed during actual fresh tests")
    require(live_evidence() == live, "Actual source/current capture binding changed during fresh tests")
    if require_admission:
        admission = verify_admission()
    else:
        admission = None
    return {"repair_validated": True, "canonical_product_preflight_validated": True,
            "fresh_app_tests": 44, "fresh_guard_tests": 35, "fresh_todo_tests": 8, "fresh_tests_total": 87, **browser, **failure, **preserved,
            "admission_verified": require_admission, "admission": admission,
            "all_12_acquisitions_and_six_strict_go_gates_still_required": True,
            "original_child_argv_and_workload_bounds_preserved": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


if __name__ == "__main__":
    print(json.dumps(verify_ready_proof(), sort_keys=True))
