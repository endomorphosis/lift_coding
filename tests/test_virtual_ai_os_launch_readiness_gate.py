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
SWISSKNIFE_PACKAGE_PATH = REPO_ROOT / "swissknife" / "package.json"
SWISSKNIFE_RUNNER_PATH = REPO_ROOT / "swissknife" / "scripts" / "run_playwright_test.mjs"
SWISSKNIFE_PLAYWRIGHT_CONFIG_PATH = (
    REPO_ROOT / "swissknife" / "build-tools" / "configs" / "playwright.meta-glasses.config.ts"
)
SWISSKNIFE_SPEC_PATH = REPO_ROOT / "swissknife" / "test" / "e2e" / "meta-glasses-virtual-os.spec.ts"
HALLUCINATE_PACKAGE_PATH = REPO_ROOT / "hallucinate_app" / "package.json"
HALLUCINATE_RUNNER_PATH = REPO_ROOT / "hallucinate_app" / "scripts" / "run_playwright_test.mjs"
HALLUCINATE_SPEC_PATH = (
    REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "multimodal-control-surface.spec.ts"
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
    assert "meta-glasses-virtual-os.spec.ts" in config_source
    assert "meta-glasses-chromium" in config_source
    assert "test-results/meta-glasses-virtual-os/results.json" in config_source
    assert "python3 -m http.server 3001" in config_source
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
    assert "allowsNoDisplaySpecSkip" not in runner_source
    assert "MCP Dashboard Interoperability - VAIOS-G723" in dashboard_spec_source
    assert "headless backend gate" in dashboard_spec_source
    assert "control_surface_route" in dashboard_spec_source
    assert "dashboard capability catalog" in exposure_spec_source
    assert "VAIOS-G723" in exposure_spec_source


def test_readiness_doc_and_heap_name_the_same_launch_validation_gate():
    doc_source = READINESS_DOC_PATH.read_text(encoding="utf-8")
    normalized_doc_source = " ".join(doc_source.split())
    heap_source = HEAP_PATH.read_text(encoding="utf-8")
    hao_source = HAO_436_RECEIPT_PATH.read_text(encoding="utf-8")
    mgw_source = MGW_274_RECEIPT_PATH.read_text(encoding="utf-8")
    vai_source = VAI_340_RECEIPT_PATH.read_text(encoding="utf-8")
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
