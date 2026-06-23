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
MGW_274_RECEIPT_PATH = (
    REPO_ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-06-23-mgw-274-launch-readiness-gate.md"
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


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def _load_launch_readiness_receipt() -> dict:
    source = VAI_340_RECEIPT_PATH.read_text(encoding="utf-8")
    return _json_block_after(source, "## LaunchReadinessGate")


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

    for client in ("voice", "gesture", "mouse", "agent", "remote-meta-glasses"):
        assert client in spec_source
    for receipt_term in (
        "policy_decision",
        "mediation_receipt",
        "control_surface_contract",
        "interaction_envelope",
    ):
        assert receipt_term in spec_source


def test_readiness_doc_and_heap_name_the_same_launch_validation_gate():
    doc_source = READINESS_DOC_PATH.read_text(encoding="utf-8")
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
    assert "2026-06-23-mgw-274-launch-readiness-gate.md" in doc_source
    assert "HAO-436" in doc_source
    assert "MGW-274" in doc_source
    assert "VAI-340" in doc_source
    assert "HAO-436" in hao_source
    assert "MGW-274" in mgw_source
    assert "VAI-340" in vai_source
