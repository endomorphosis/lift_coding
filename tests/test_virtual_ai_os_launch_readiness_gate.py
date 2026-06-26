from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
READINESS_DOC_PATH = REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md"
VAI_339_REPLAY_PATH = (
    REPO_ROOT / "data" / "virtual_ai_os" / "discovery" / "2026-06-23-vai-339-launch-replay-gate.md"
)
VAI_340_RECEIPT_PATH = (
    REPO_ROOT / "data" / "virtual_ai_os" / "discovery" / "2026-06-23-vai-340-launch-readiness-gate.md"
)
HAO_436_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-23-hao-436-launch-readiness-gate.md"
)
HAO_437_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-23-hao-437-phone-ingress-rehearsal.md"
)
HAO_438_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-23-hao-438-desktop-peer-offload-smoke.md"
)
HAO_439_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-23-hao-439-meta-glasses-terminal-receipt.md"
)
HAO_440_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-23-hao-440-launch-readiness-physical-aggregate.md"
)
MGW_274_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-06-23-mgw-274-launch-readiness-gate.md"
)
MGW_526_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-06-26-mgw-526-headless-aware-hallucinate-runner.md"
)
MGW_534_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-06-26-mgw-534-launch-playwright-validation-gate.md"
)
MGW_538_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-06-26-mgw-538-launch-playwright-validation-gate.md"
)
VAI_522_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-26-vai-522-launch-playwright-validation-gate.md"
)
HAO_701_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-26-hao-701-launch-playwright-validation-gate.md"
)
HAO_705_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "hallucinate_multimodal_control"
    / "discovery"
    / "2026-06-26-hao-705-launch-playwright-validation-gate.md"
)
SWISSKNIFE_PACKAGE_PATH = REPO_ROOT / "swissknife" / "package.json"
SWISSKNIFE_RUNNER_PATH = REPO_ROOT / "swissknife" / "scripts" / "run_playwright_test.mjs"
SWISSKNIFE_PLAYWRIGHT_CONFIG_PATH = (
    REPO_ROOT / "swissknife" / "build-tools" / "configs" / "playwright.meta-glasses.config.ts"
)
SWISSKNIFE_SPEC_PATH = REPO_ROOT / "swissknife" / "test" / "e2e" / "meta-glasses-virtual-os.spec.ts"
SWISSKNIFE_CONTROL_PLANE_FIXTURE_PATH = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "e2e"
    / "fixtures"
    / "mgw-519-meta-glasses-control-plane.json"
)
HALLUCINATE_PACKAGE_PATH = REPO_ROOT / "hallucinate_app" / "package.json"
HALLUCINATE_RUNNER_PATH = REPO_ROOT / "hallucinate_app" / "scripts" / "run_playwright_test.mjs"
HALLUCINATE_SPEC_PATH = (
    REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "multimodal-control-surface.spec.ts"
)
HAO_675_REPLAY_FIXTURE_PATH = (
    REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "fixtures" / "hao-675-launch-replay.json"
)
HAO_705_HALLUCINATE_FIXTURE_PATH = (
    REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "fixtures" / "hao-705-cross-device-launch-gate.json"
)
HAO_705_SWISSKNIFE_FIXTURE_PATH = (
    REPO_ROOT / "swissknife" / "test" / "e2e" / "fixtures" / "hao-705-cross-device-launch-gate.json"
)
VAI_502_CROSS_DEVICE_REPLAY_PATH = (
    REPO_ROOT / "swissknife" / "test" / "e2e" / "fixtures" / "vai-502-cross-device-playwright-replay.json"
)

PYTHON_GATE_COMMAND = (
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
    "pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
)
SWISSKNIFE_PLAYWRIGHT_COMMAND = "npm --prefix swissknife run test:e2e:meta-glasses"
HALLUCINATE_PLAYWRIGHT_COMMAND = (
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
)
HALLUCINATE_MCP_DASHBOARD_COMMAND = (
    "npm --prefix hallucinate_app run test:e2e -- "
    "mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts"
)


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def _load_launch_readiness_receipt() -> dict:
    source = VAI_340_RECEIPT_PATH.read_text(encoding="utf-8")
    return _json_block_after(source, "## LaunchReadinessGate")


def _load_receipt(path: Path, marker: str) -> dict:
    return _json_block_after(path.read_text(encoding="utf-8"), marker)


def test_launch_readiness_receipt_covers_product_critical_hops():
    receipt = _load_launch_readiness_receipt()
    replay = _json_block_after(
        VAI_339_REPLAY_PATH.read_text(encoding="utf-8"),
        "## Deterministic Launch Replay Gate",
    )

    assert receipt["schema"] == "launch_readiness_receipt_v1"
    assert receipt["goal_id"] == "VAIOS-G697"
    assert receipt["requires_physical_devices"] is False
    assert receipt["physical_device_follow_up_required"] is False
    assert receipt["python_gate"]["command"] == PYTHON_GATE_COMMAND
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["pass_together_rule"] == {
        "required_commands": [
            PYTHON_GATE_COMMAND,
            SWISSKNIFE_PLAYWRIGHT_COMMAND,
            HALLUCINATE_PLAYWRIGHT_COMMAND,
        ],
        "same_receipt_lineage": True,
        "gate_state_before_all_pass": "open",
        "gate_state_after_all_pass": "launch_ready",
    }

    covered_hops = {hop["hop"] for hop in receipt["product_critical_hops"]}
    assert covered_hops == {
        "phone_originated_command",
        "hallucinate_app_mediation",
        "swissknife_virtual_desktop",
        "desktop_peer_offload",
        "meta_glasses_terminal",
    }
    assert "desktop_peer_or_phone_local_placement" in replay["covers"]
    assert replay["placement_policy"]["selected_runtime"] == "desktop_peer"
    assert replay["placement_policy"]["fallback_runtime"] == "phone_local"


def test_launch_readiness_receipt_requires_physical_evidence_and_lineage():
    receipt = _load_launch_readiness_receipt()
    hao_437 = _load_receipt(HAO_437_RECEIPT_PATH, "## Real Phone Ingress Rehearsal Fixture")
    hao_438 = _load_receipt(HAO_438_RECEIPT_PATH, "## Desktop-Peer Offload Smoke Fixture")
    hao_439 = _load_receipt(HAO_439_RECEIPT_PATH, "## Meta Glasses Terminal Receipt Fixture")
    hao_440 = _load_receipt(HAO_440_RECEIPT_PATH, "## Physical Readiness Aggregate Fixture")

    requirements = {item["task_id"]: item for item in receipt["physical_readiness_requirements"]}
    assert set(requirements) == {"HAO-437", "HAO-438", "HAO-439"}
    assert requirements["HAO-437"]["receipt_path"] == (
        "data/hallucinate_multimodal_control/discovery/"
        "2026-06-23-hao-437-phone-ingress-rehearsal.md"
    )
    assert requirements["HAO-438"]["receipt_path"] == (
        "data/hallucinate_multimodal_control/discovery/"
        "2026-06-23-hao-438-desktop-peer-offload-smoke.md"
    )
    assert requirements["HAO-439"]["receipt_path"] == (
        "data/hallucinate_multimodal_control/discovery/"
        "2026-06-23-hao-439-meta-glasses-terminal-receipt.md"
    )
    assert requirements["HAO-437"]["artifact_id"] == hao_437["artifact_id"]
    assert requirements["HAO-438"]["artifact_id"] == hao_438["artifact_id"]
    assert requirements["HAO-439"]["artifact_id"] == hao_439["artifact_id"]
    assert all(item["required_for_launch_ready"] is True for item in requirements.values())

    lineage = receipt["playwright_lineage"]
    assert lineage["lineage_id"] == "VAIOS-G697:launch-readiness:phone-desktop-glasses"
    assert lineage["same_receipt_lineage"] is True
    assert [gate["command"] for gate in lineage["required_gates"]] == [
        PYTHON_GATE_COMMAND,
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ]
    assert {gate["surface"] for gate in lineage["required_gates"]} == {
        "python_static_receipt_gate",
        "swissknife_meta_glasses_playwright",
        "hallucinate_app_multimodal_playwright",
    }
    assert receipt["pass_together_rule"]["required_commands"] == [
        gate["command"] for gate in lineage["required_gates"]
    ]

    fallback = receipt["hardware_free_fallback"]
    assert fallback == {
        "explicit": True,
        "physical_capture_unavailable_state": "gate_open_physical_capture_pending",
        "fallback_is_launch_ready": False,
        "fallback_receipts": [
            "data/virtual_ai_os/discovery/2026-06-23-vai-010-hardware-free-e2e-harness.md",
            "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-430-hardware-free-offload-harness.md",
            "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md",
        ],
    }

    assert hao_440["schema"] == "launch_readiness_physical_evidence_aggregate_v1"
    assert hao_440["goal_id"] == receipt["goal_id"]
    assert hao_440["launch_readiness_receipt"] == (
        "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md"
    )
    assert hao_440["required_physical_receipts"] == receipt["physical_readiness_requirements"]
    assert hao_440["playwright_lineage"] == lineage
    assert hao_440["hardware_free_fallback"] == fallback
    assert hao_440["launch_ready_requires"] == [
        "HAO-437 real_phone_ingress_rehearsal_receipt present",
        "HAO-438 desktop_peer_offload_smoke_receipt present",
        "HAO-439 meta_glasses_terminal_receipt present",
        "all Playwright launch gates pass in VAIOS-G697:launch-readiness:phone-desktop-glasses",
        "hardware-free fallback remains explicit and non-launch-ready when physical capture is unavailable",
    ]


def test_vai_339_replay_receipt_chain_preserves_session_and_command_identity():
    replay = _json_block_after(
        VAI_339_REPLAY_PATH.read_text(encoding="utf-8"),
        "## Deterministic Launch Replay Gate",
    )
    join_keys = replay["join_keys"]
    receipt_chain = replay["receipt_chain"]

    assert [receipt["receipt"] for receipt in receipt_chain] == [
        "phone_event_receipt",
        "hallucinate_app_mediation_receipt",
        "placement_receipt_cid",
        "desktop_peer_execution_receipt",
        "meta_glasses_render_receipt",
        "recovery_receipt_cid",
        "capability_receipt_cid",
    ]

    previous_receipt_cid = None
    for receipt in receipt_chain:
        assert receipt["session_id"] == join_keys["session_id"]
        assert receipt["command_id"] == join_keys["command_id"]
        assert receipt["correlation_id"] == join_keys["correlation_id"]
        assert receipt["request_id"] == join_keys["request_id"]
        if previous_receipt_cid is None:
            assert receipt["parent_receipt_cids"] == []
        else:
            assert receipt["parent_receipt_cids"] == [previous_receipt_cid]
        previous_receipt_cid = receipt["receipt_cid"]

    by_receipt = {receipt["receipt"]: receipt for receipt in receipt_chain}
    assert by_receipt["hallucinate_app_mediation_receipt"]["policy_decision"] == {
        "outcome": "allow",
        "policy_cid": join_keys["policy_cid"],
    }
    assert by_receipt["placement_receipt_cid"]["selected_runtime"] == "desktop_peer"
    assert by_receipt["placement_receipt_cid"]["fallback_runtime"] == "phone_local"
    assert by_receipt["desktop_peer_execution_receipt"]["desktop_id"] == join_keys["desktop_id"]
    assert by_receipt["meta_glasses_render_receipt"]["widget_id"] == join_keys["widget_id"]
    assert by_receipt["meta_glasses_render_receipt"]["descriptor_cid"] == (
        join_keys["descriptor_cid"]
    )
    assert by_receipt["meta_glasses_render_receipt"]["manifest_cid"] == (
        join_keys["manifest_cid"]
    )
    assert by_receipt["meta_glasses_render_receipt"]["terminal_status"] == "rendered"
    assert by_receipt["recovery_receipt_cid"]["recovered_runtime"] == "phone_local"
    assert by_receipt["recovery_receipt_cid"]["terminal_status"] == "recovered"
    assert by_receipt["capability_receipt_cid"]["receipt_cid"] == (
        join_keys["capability_receipt_cid"]
    )
    assert by_receipt["capability_receipt_cid"]["capability_actions"] == (
        replay["widget_capabilities"]
    )


def test_swissknife_meta_glasses_playwright_gate_is_runnable_and_specific():
    package = json.loads(SWISSKNIFE_PACKAGE_PATH.read_text(encoding="utf-8"))
    runner_source = SWISSKNIFE_RUNNER_PATH.read_text(encoding="utf-8")
    config_source = SWISSKNIFE_PLAYWRIGHT_CONFIG_PATH.read_text(encoding="utf-8")
    spec_source = SWISSKNIFE_SPEC_PATH.read_text(encoding="utf-8")

    assert package["scripts"]["test:e2e:meta-glasses"] == (
        "node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.meta-glasses.config.ts"
    )
    for runner_term in ("node_modules", "@playwright", "test", "cli.js"):
        assert runner_term in runner_source
    assert "ensureE2EDependencies" in runner_source
    assert "SWISSKNIFE_E2E_NO_BOOTSTRAP" in runner_source
    assert "--legacy-peer-deps" in runner_source
    assert "runPlaywright(args)" in runner_source
    assert "playwrightEnv(playwrightArgs)" in runner_source
    assert "usesMetaGlassesConfig" in runner_source
    assert "stablePortForPath(projectRoot)" in runner_source
    assert "SWISSKNIFE_META_GLASSES_E2E_PORT" in runner_source
    assert "SWISSKNIFE_E2E_PORT" in runner_source
    assert "meta-glasses-virtual-os.spec.ts" in config_source
    assert "meta-glasses-chromium" in config_source
    assert "test-results/meta-glasses-virtual-os/results.json" in config_source
    assert "SWISSKNIFE_META_GLASSES_E2E_PORT" in config_source
    assert "SWISSKNIFE_E2E_PORT" in config_source
    assert "python3 -m http.server ${metaGlassesPort}" in config_source
    assert "reuseExistingServer: false" in config_source
    assert "reuseExistingServer: true" not in config_source
    assert "'http://127.0.0.1:3001'" not in config_source
    assert "opens every SwissKnife desktop app" in spec_source
    assert "renderDesktopAppThroughMetaGlassesOrb" in spec_source
    assert "apps-meta-display-report.json" in spec_source
    assert "receiptCid" in spec_source
    helper_source = (
        REPO_ROOT / "swissknife" / "test" / "e2e" / "helpers" / "meta-glasses-app-template.ts"
    ).read_text(encoding="utf-8")
    assert "idempotency_key" in helper_source
    assert "setControlSurfacePolicyEvaluator" in helper_source
    assert "Meta glasses Playwright launch gate permits deterministic display-widget render." in helper_source


def test_hallucinate_multimodal_playwright_gate_is_runnable_and_specific():
    package = json.loads(HALLUCINATE_PACKAGE_PATH.read_text(encoding="utf-8"))
    runner_source = HALLUCINATE_RUNNER_PATH.read_text(encoding="utf-8")
    spec_source = HALLUCINATE_SPEC_PATH.read_text(encoding="utf-8")

    assert package["scripts"]["test:e2e"] == "node scripts/run_playwright_test.mjs test"
    for runner_term in ("node_modules", "@playwright", "test", "cli.js"):
        assert runner_term in runner_source
    assert "ensureE2EDependencies" in runner_source
    assert "runPlaywright(args)" in runner_source
    assert "xvfb-run" in runner_source
    assert "missing_xvfb_for_electron_playwright" in runner_source
    assert "HALLUCINATE_APP_E2E_DISABLE_XVFB" in runner_source
    assert "noDisplayHeadlessGateSpecs" in runner_source
    assert "canRunWithoutVirtualDisplay" in runner_source
    assert "daemon-launch-health.spec.ts" in runner_source
    assert "mcp-dashboard-interoperability.spec.ts" in runner_source
    assert "mcp-feature-exposure.spec.ts" in runner_source
    assert "multimodal-control-surface.spec.ts" in runner_source
    assert "repairable launch-environment blocker" in runner_source
    assert "allowsNoDisplaySpecSkip" not in runner_source
    assert "noDisplaySafeSpecs" not in runner_source

    for client in ("voice", "gesture", "mouse", "agent", "remote-meta-glasses"):
        assert client in spec_source
    for receipt_term in (
        "policy_decision",
        "mediation_receipt",
        "control_surface_contract",
        "interaction_envelope",
    ):
        assert receipt_term in spec_source


def test_meta_glasses_mcp_dashboard_gate_inherits_headless_aware_hallucinate_runner():
    package = json.loads(HALLUCINATE_PACKAGE_PATH.read_text(encoding="utf-8"))
    runner_source = HALLUCINATE_RUNNER_PATH.read_text(encoding="utf-8")
    dashboard_spec_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-dashboard-interoperability.spec.ts"
    ).read_text(encoding="utf-8")
    exposure_spec_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-feature-exposure.spec.ts"
    ).read_text(encoding="utf-8")
    receipt_source = MGW_526_RECEIPT_PATH.read_text(encoding="utf-8")
    normalized_receipt_source = " ".join(receipt_source.split())

    assert package["scripts"]["test:e2e"] == "node scripts/run_playwright_test.mjs test"
    assert HALLUCINATE_MCP_DASHBOARD_COMMAND in receipt_source
    for term in (
        "Meta glasses MCP dashboard validation",
        "headless-aware Hallucinate Playwright runner",
        "camera",
        "microphone",
        "headphones",
        "neural-band",
        "control-plane",
        "missing_xvfb_for_electron_playwright",
        "repairable launch-environment blocker",
        "exit 78",
    ):
        assert term in normalized_receipt_source

    assert "xvfb-run" in runner_source
    assert "process.exit(78)" in runner_source
    assert "missing_xvfb_for_electron_playwright" in runner_source
    assert "noDisplayHeadlessGateSpecs" in runner_source
    assert "canRunWithoutVirtualDisplay" in runner_source
    assert "allowsNoDisplaySpecSkip" not in runner_source
    assert "MCP Dashboard Interoperability - VAIOS-G723" in dashboard_spec_source
    assert "headless backend gate" in dashboard_spec_source
    assert "control_surface_route" in dashboard_spec_source
    assert "dashboard capability catalog" in exposure_spec_source
    assert "VAIOS-G723" in exposure_spec_source


def test_mgw_534_meta_glasses_input_routing_has_launch_playwright_gate():
    receipt_source = MGW_534_RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = _load_receipt(MGW_534_RECEIPT_PATH, "## Gate Fixture")
    fixture = json.loads(SWISSKNIFE_CONTROL_PLANE_FIXTURE_PATH.read_text(encoding="utf-8"))
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    swissknife_spec_source = SWISSKNIFE_SPEC_PATH.read_text(encoding="utf-8")
    hallucinate_spec_source = HALLUCINATE_SPEC_PATH.read_text(encoding="utf-8")

    assert receipt["schema"] == "mgw_launch_playwright_validation_gate_v1"
    assert receipt["task_id"] == "MGW-534"
    assert receipt["goal_id"] == "VAIOS-G727"
    assert receipt["goal_packet"] == "goal_packet/launch/external/ec964340486b"
    assert receipt["packet_goals"] == ["VAIOS-G727", "VAIOS-G729"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["python_gate"]["command"] == (
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
        "pytest tests/test_hallucinate_multimodal_control_todo_queue.py "
        "tests/test_virtual_ai_os_launch_readiness_gate.py -q"
    )
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["launch_packet_command"] == (
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
        "pytest tests/test_hallucinate_multimodal_control_todo_queue.py "
        "tests/test_virtual_ai_os_launch_readiness_gate.py -q && "
        "(test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && "
        "(test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
    )

    required_inputs = set(receipt["required_inputs"])
    events_by_device = {event["device"]: event for event in fixture["events"]}
    assert required_inputs == {"camera", "microphone", "headphones", "captouch", "Neural Band"}
    assert required_inputs.issubset(events_by_device)
    assert events_by_device["captouch"]["event_type"] == "captouch.intent"
    assert events_by_device["captouch"]["payload"]["gesture"] == "single_tap"

    for event in events_by_device.values():
        assert event["control_plane"] == {
            "route": "swissknife.mobile_orb.publish_glasses_event",
            "operation": "publish_glasses_event",
        }
        assert event["transport"]["bluetooth"] == "route-state"
        assert event["transport"]["wifi"] == "app-level-handoff"
        assert event["handoff"]["ipfs_cids"]
        assert event["handoff"]["libp2p_session_id"] == "libp2p-mgw-519-playwright"
        assert event["handoff"]["mcp_plus_plus_profile"] == fixture["profile"]
        assert event["receipts"]

    assert {item["receipt_cid"] for item in fixture["replay_receipts"]} == {
        event["receipts"][0] for event in fixture["events"]
    }
    assert all(item["preserve_for_dat_replay"] is True for item in fixture["replay_receipts"])
    assert {"external/meta-wearables-dat-android", "external/meta-wearables-dat-ios", "mobile"} == set(
        receipt["mobile_edges"]
    )

    for required_term in (
        "MGW-534",
        "VAIOS-G727",
        "VAIOS-G729",
        "launch Playwright validation gate",
        "swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json",
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ):
        assert required_term in receipt_source
        assert required_term in heap_source

    assert "opens every SwissKnife desktop app" in swissknife_spec_source
    assert "remote-meta-glasses" in hallucinate_spec_source
    assert "mobile-orb-publish-glasses-event" in hallucinate_spec_source


def test_hao_701_meta_glasses_input_routing_has_hallucinate_owned_gate():
    receipt_source = HAO_701_RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = _load_receipt(HAO_701_RECEIPT_PATH, "## Gate Fixture")
    fixture = json.loads(SWISSKNIFE_CONTROL_PLANE_FIXTURE_PATH.read_text(encoding="utf-8"))
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    hallucinate_spec_source = HALLUCINATE_SPEC_PATH.read_text(encoding="utf-8")

    assert receipt["schema"] == "hao_launch_playwright_validation_gate_v1"
    assert receipt["task_id"] == "HAO-701"
    assert receipt["goal_id"] == "VAIOS-G727"
    assert receipt["goal_packet"] == "goal_packet/launch/external/ec964340486b"
    assert receipt["packet_goals"] == ["VAIOS-G727", "VAIOS-G729"]
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["shared_packet_receipt"] == (
        "data/meta_glasses_display_widgets/discovery/"
        "2026-06-26-mgw-534-launch-playwright-validation-gate.md"
    )
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["supervisor_alignment"] == {
        "objective_heap_goal": "VAIOS-G727",
        "packet_sibling_goal": "VAIOS-G729",
        "backlog_task": "HAO-701",
        "shared_packet_task": "MGW-534",
        "keeps_supervisor_fed_backlog_aligned": True,
    }

    assert set(receipt["required_inputs"]) == {
        "camera",
        "microphone",
        "headphones",
        "captouch",
        "Neural Band",
    }
    assert set(receipt["required_inputs"]).issubset({event["device"] for event in fixture["events"]})
    assert receipt["required_transports"] == [
        "Bluetooth transport",
        "Wi-Fi transport",
        "IPFS",
        "libp2p",
        "MCP++",
    ]
    assert receipt["mobile_edges"] == [
        "external/meta-wearables-dat-android",
        "external/meta-wearables-dat-ios",
        "mobile",
    ]
    assert receipt["route"] == [
        "Meta glasses interface",
        "Meta Wearables DAT",
        "mobile phone",
        "Swissknife applications",
        "Hallucinate App mediation",
        "control plane",
    ]

    for gate in receipt["playwright_gates"]:
        if gate["surface"] == "hallucinate_app":
            for term in gate["route_terms"]:
                assert term in hallucinate_spec_source

    for required_term in (
        "HAO-701",
        "MGW-534",
        "VAIOS-G727",
        "VAIOS-G729",
        "launch Playwright validation gate",
        "2026-06-26-hao-701-launch-playwright-validation-gate.md",
        "swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json",
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ):
        assert required_term in receipt_source
        assert required_term in heap_source


def test_mgw_538_cross_device_offload_replay_has_launch_playwright_gate():
    receipt_source = MGW_538_RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = _load_receipt(MGW_538_RECEIPT_PATH, "## Gate Fixture")
    replay = _json_block_after(
        VAI_339_REPLAY_PATH.read_text(encoding="utf-8"),
        "## Deterministic Launch Replay Gate",
    )
    hao_675 = json.loads(HAO_675_REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    swissknife_spec_source = SWISSKNIFE_SPEC_PATH.read_text(encoding="utf-8")
    hallucinate_spec_source = HALLUCINATE_SPEC_PATH.read_text(encoding="utf-8")

    assert receipt["schema"] == "mgw_cross_device_offload_launch_playwright_gate_v1"
    assert receipt["task_id"] == "MGW-538"
    assert receipt["goal_id"] == "VAIOS-G726"
    assert receipt["execution_packet"] == "execution_packet/521842cea53f"
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["python_gate"]["command"] == PYTHON_GATE_COMMAND
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["launch_packet_command"] == (
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
        "pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q && "
        "(test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && "
        "(test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
    )

    assert receipt["source_replay_receipts"] == [
        "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md",
        "hallucinate_app/test/e2e/fixtures/hao-675-launch-replay.json",
        "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md",
    ]
    assert receipt["placement_policy"] == {
        "selected_runtime": replay["placement_policy"]["selected_runtime"],
        "fallback_runtime": replay["placement_policy"]["fallback_runtime"],
        "selected_runtime_receipt": "desktop_peer_execution_receipt",
        "fallback_runtime_receipt": "recovery_receipt_cid",
    }
    assert receipt["required_receipt_chain"] == [
        item["receipt"] for item in replay["receipt_chain"]
    ]
    assert receipt["supervisor_alignment"] == {
        "objective_heap_goal": "VAIOS-G726",
        "backlog_task": "MGW-538",
        "merge_family": "objective/VAIOS-G726",
        "merge_role": "validation_gate",
        "keeps_supervisor_fed_backlog_aligned": True,
    }

    assert hao_675["schema"] == "launch_replay_playwright_receipt_v1"
    assert hao_675["pass_fail_receipts"]["desktop_peer_offload"] == "passed"
    assert hao_675["pass_fail_receipts"]["production_launch_readiness"] == "passed"
    assert "desktop peer offload receipt" in hao_675["route"]
    assert "Playwright launch replay" in swissknife_spec_source
    assert "phone-hosted Swissknife virtual desktop" in swissknife_spec_source
    assert "desktop peer offload" in swissknife_spec_source
    assert "Hallucinate App mediation" in hallucinate_spec_source
    assert "ipfs_kit_py" in hallucinate_spec_source
    assert "ipfs_datasets_py" in hallucinate_spec_source
    assert "ipfs_accelerate_py" in hallucinate_spec_source
    assert "MCP++" in hallucinate_spec_source
    assert {capability["server_package"] for capability in hao_675["service_capabilities"]} == {
        "ipfs_kit_py",
        "ipfs_datasets_py",
        "ipfs_accelerate_py",
    }
    assert all(
        "Profile E P2P" in capability["mcp_plus_plus_profiles"]
        for capability in hao_675["service_capabilities"]
    )

    for required_term in (
        "MGW-538",
        "VAIOS-G726",
        "execution_packet/521842cea53f",
        "launch Playwright validation gate",
        "phone-hosted Swissknife virtual desktop",
        "desktop peer offload",
        "Hallucinate App mediation",
        "IPFS",
        "libp2p",
        "MCP++",
        "launch readiness receipt",
        "cross-device e2e validation",
        "Playwright launch replay",
        "2026-06-26-mgw-538-launch-playwright-validation-gate.md",
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ):
        assert required_term in receipt_source
        assert required_term in heap_source


def test_vai_522_cross_device_offload_replay_has_launch_playwright_gate():
    receipt_source = VAI_522_RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = _load_receipt(VAI_522_RECEIPT_PATH, "## Gate Fixture")
    shared_receipt = _load_receipt(MGW_538_RECEIPT_PATH, "## Gate Fixture")
    replay = _json_block_after(
        VAI_339_REPLAY_PATH.read_text(encoding="utf-8"),
        "## Deterministic Launch Replay Gate",
    )
    hao_675 = json.loads(HAO_675_REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))
    heap_source = HEAP_PATH.read_text(encoding="utf-8")

    assert receipt["schema"] == "vai_cross_device_offload_launch_playwright_gate_v1"
    assert receipt["task_id"] == "VAI-522"
    assert receipt["goal_id"] == "VAIOS-G726"
    assert receipt["bundle"] == "objective/launch/cross-device-virtual-desktop-offload-replay"
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["missing_evidence_source"] == (
        "data/virtual_ai_os/discovery/2026-06-26-vai-522-objective-gap-4ca32c914d33.md"
    )
    assert receipt["shared_validation_gate"] == (
        "data/meta_glasses_display_widgets/discovery/"
        "2026-06-26-mgw-538-launch-playwright-validation-gate.md"
    )
    assert receipt["python_gate"]["command"] == PYTHON_GATE_COMMAND
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["launch_packet_command"] == shared_receipt["launch_packet_command"]
    assert receipt["source_replay_receipts"] == shared_receipt["source_replay_receipts"]
    assert receipt["route"] == shared_receipt["route"]
    assert receipt["join_keys"] == shared_receipt["join_keys"]
    assert receipt["placement_policy"] == shared_receipt["placement_policy"]
    assert receipt["required_receipt_chain"] == shared_receipt["required_receipt_chain"]
    assert receipt["required_receipt_chain"] == [
        item["receipt"] for item in replay["receipt_chain"]
    ]
    assert receipt["supervisor_alignment"] == {
        "objective_heap_goal": "VAIOS-G726",
        "backlog_task": "VAI-522",
        "shared_backlog_task": "MGW-538",
        "merge_family": "objective/VAIOS-G726",
        "merge_role": "validation_gate",
        "keeps_supervisor_fed_backlog_aligned": True,
    }
    assert receipt["placement_policy"]["selected_runtime"] == (
        replay["placement_policy"]["selected_runtime"]
    )
    assert receipt["placement_policy"]["fallback_runtime"] == (
        replay["placement_policy"]["fallback_runtime"]
    )
    assert hao_675["pass_fail_receipts"]["desktop_peer_offload"] == "passed"
    assert hao_675["pass_fail_receipts"]["production_launch_readiness"] == "passed"

    for required_term in (
        "VAI-522",
        "MGW-538",
        "VAIOS-G726",
        "launch Playwright validation gate",
        "phone-hosted Swissknife virtual desktop",
        "desktop peer offload",
        "Hallucinate App mediation",
        "IPFS",
        "libp2p",
        "MCP++",
        "launch readiness receipt",
        "cross-device e2e validation",
        "Playwright launch replay",
        "2026-06-26-vai-522-launch-playwright-validation-gate.md",
        "2026-06-26-mgw-538-launch-playwright-validation-gate.md",
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ):
        assert required_term in receipt_source
        assert required_term in heap_source


def test_hao_705_cross_device_offload_replay_has_launch_playwright_gate():
    receipt_source = HAO_705_RECEIPT_PATH.read_text(encoding="utf-8")
    receipt = _load_receipt(HAO_705_RECEIPT_PATH, "## Gate Fixture")
    hallucinate_fixture = json.loads(HAO_705_HALLUCINATE_FIXTURE_PATH.read_text(encoding="utf-8"))
    swissknife_fixture = json.loads(HAO_705_SWISSKNIFE_FIXTURE_PATH.read_text(encoding="utf-8"))
    replay = json.loads(VAI_502_CROSS_DEVICE_REPLAY_PATH.read_text(encoding="utf-8"))
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    swissknife_spec_source = SWISSKNIFE_SPEC_PATH.read_text(encoding="utf-8")
    hallucinate_spec_source = HALLUCINATE_SPEC_PATH.read_text(encoding="utf-8")

    assert hallucinate_fixture == swissknife_fixture
    assert receipt["schema"] == "hao_cross_device_launch_playwright_gate_v1"
    assert receipt["task_id"] == "HAO-705"
    assert receipt["goal_id"] == "VAIOS-G726"
    assert receipt["evidence_term"] == "launch Playwright validation gate"
    assert receipt["missing_evidence_source"] == (
        "data/hallucinate_multimodal_control/discovery/"
        "2026-06-26-hao-705-objective-gap-4ca32c914d33.md"
    )
    assert receipt["lineage_id"] == "VAIOS-G726:cross-device-virtual-desktop-offload-launch-replay"
    assert receipt["python_gate"]["command"] == PYTHON_GATE_COMMAND
    assert {gate["command"] for gate in receipt["playwright_gates"]} == {
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert receipt["validation_command"] == (
        f"{PYTHON_GATE_COMMAND} && "
        "(test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && "
        "(test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
    )
    assert receipt["playwright_fixture"] == (
        "hallucinate_app/test/e2e/fixtures/hao-705-cross-device-launch-gate.json"
    )
    assert receipt["mirrored_swissknife_fixture"] == (
        "swissknife/test/e2e/fixtures/hao-705-cross-device-launch-gate.json"
    )

    assert hallucinate_fixture["schema"] == receipt["schema"]
    assert hallucinate_fixture["task_id"] == receipt["task_id"]
    assert hallucinate_fixture["goal_id"] == receipt["goal_id"]
    assert hallucinate_fixture["evidence_term"] == receipt["evidence_term"]
    assert hallucinate_fixture["source_gap_receipt"] == receipt["missing_evidence_source"]
    assert hallucinate_fixture["launch_gate_receipt"] == receipt["receipt_path"]
    assert hallucinate_fixture["playwright_commands"] == {
        "python": PYTHON_GATE_COMMAND,
        "swissknife": SWISSKNIFE_PLAYWRIGHT_COMMAND,
        "hallucinate_app": HALLUCINATE_PLAYWRIGHT_COMMAND,
    }
    assert set(hallucinate_fixture["required_backends"]) == {
        "ipfs_kit_py",
        "ipfs_datasets_py",
        "ipfs_accelerate_py",
    }
    assert set(hallucinate_fixture["pass_fail_receipts"].values()) == {"passed"}
    assert hallucinate_fixture["supervisor_alignment"] == receipt["supervisor_alignment"]

    assert replay["schema"] == "cross_device_virtual_desktop_playwright_replay_v1"
    assert replay["phone_hosted_execution"]["mode"] == (
        hallucinate_fixture["replay_assertions"]["phone_hosted_mode"]
    )
    assert replay["phone_hosted_execution"]["control_plane_command"] == (
        hallucinate_fixture["replay_assertions"]["control_plane_command"]
    )
    assert replay["desktop_peer_offload"]["first_attempt"]["placement"] == (
        hallucinate_fixture["replay_assertions"]["selected_runtime"]
    )
    assert replay["desktop_peer_offload"]["fallback"]["placement"] == (
        hallucinate_fixture["replay_assertions"]["fallback_runtime"]
    )
    assert replay["desktop_peer_offload"]["first_attempt"]["receipt_id"] == (
        hallucinate_fixture["replay_assertions"]["desktop_peer_receipt"]
    )
    assert replay["desktop_peer_offload"]["fallback"]["receipt_id"] == (
        hallucinate_fixture["replay_assertions"]["phone_fallback_receipt"]
    )
    assert replay["meta_glasses_status_output"]["render_receipt_id"] == (
        hallucinate_fixture["replay_assertions"]["meta_glasses_render_receipt"]
    )
    assert replay["lineage_id"] == (
        hallucinate_fixture["replay_assertions"]["launch_readiness_lineage"]
    )

    for required_term in (
        "HAO-705",
        "VAIOS-G726",
        "launch Playwright validation gate",
        "phone-hosted Swissknife virtual desktop",
        "desktop peer offload",
        "mobile phone",
        "Hallucinate App mediation",
        "IPFS",
        "libp2p",
        "MCP++",
        "launch readiness receipt",
        "cross-device e2e validation",
        "Playwright launch replay",
        "hao-705-cross-device-launch-gate.json",
        "vai-502-cross-device-playwright-replay.json",
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
    ):
        assert required_term in receipt_source
        assert required_term in heap_source

    assert "HAO-705 cross-device launch gate fixture" in swissknife_spec_source
    assert "HAO-705 cross-device launch gate fixture" in hallucinate_spec_source


def test_readiness_doc_and_heap_name_the_same_launch_validation_gate():
    doc_source = READINESS_DOC_PATH.read_text(encoding="utf-8")
    normalized_doc_source = " ".join(doc_source.split())
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    hao_source = HAO_436_RECEIPT_PATH.read_text(encoding="utf-8")
    mgw_source = MGW_274_RECEIPT_PATH.read_text(encoding="utf-8")
    vai_source = VAI_340_RECEIPT_PATH.read_text(encoding="utf-8")
VAI_518_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-26-vai-518-launch-playwright-validation-gate.md"
)
    receipt = _load_launch_readiness_receipt()

    required_terms = [
        "LaunchReadinessGate",
        "launch_readiness_receipt_v1",
        "launch Playwright validation gate",
        PYTHON_GATE_COMMAND,
        SWISSKNIFE_PLAYWRIGHT_COMMAND,
        HALLUCINATE_PLAYWRIGHT_COMMAND,
        "phone-hosted Swissknife virtual desktop",
        "desktop-peer offload",
        "Hallucinate App mediation",
        "Meta glasses terminal",
    ]

    for term in required_terms:
        assert term in doc_source
        assert term in heap_source
        assert term in hao_source
        assert term in mgw_source
        assert term in vai_source

    assert receipt["readiness_doc"] == "docs/launch/phone_desktop_glasses_readiness.md"
    assert vai_receipt["task_id"] == "VAI-518"
    assert "VAI-518" in vai_receipt_source
    assert "VAI-518" in heap_source
    assert "MGW-534" in receipt_source
    assert "MGW-534" in heap_source
    assert "VAI-340 launch readiness gate" in heap_source
    assert "HAO-436 launch readiness gate" in heap_source
    assert "MGW-274 launch readiness gate" in heap_source
    assert "2026-06-23-vai-340-launch-readiness-gate.md" in heap_source
    assert "2026-06-23-mgw-274-launch-readiness-gate.md" in heap_source
    assert "2026-06-23-hao-436-launch-readiness-gate.md" in heap_source
    assert "2026-06-23-vai-340-launch-readiness-gate.md" in doc_source
    assert "2026-06-23-hao-436-launch-readiness-gate.md" in doc_source
    assert "2026-06-23-hao-440-launch-readiness-physical-aggregate.md" in doc_source
    assert "2026-06-23-hao-440-launch-readiness-physical-aggregate.md" in heap_source
    assert "physical_readiness_requirements" in vai_source
    assert "HAO-440 physical readiness aggregate" in doc_source
    assert "HAO-440 physical readiness aggregate" in heap_source
    assert "Hardware-free fallback remains explicit and non-launch-ready" in normalized_doc_source
    assert "hardware_free_fallback" in vai_source
    assert "2026-06-23-mgw-274-launch-readiness-gate.md" in doc_source
    assert "HAO-436" in doc_source
    assert "HAO-440" in doc_source
    assert "MGW-274" in doc_source
    assert "VAI-340" in doc_source
    assert "HAO-436" in hao_source
    assert "MGW-274" in mgw_source
    assert "VAI-340" in vai_source
