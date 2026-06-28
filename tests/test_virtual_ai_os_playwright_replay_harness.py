from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SWISSKNIFE_REPLAY_PATH = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-502-cross-device-playwright-replay.json"
)
HALLUCINATE_MEDIATION_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "test"
    / "e2e"
    / "fixtures"
    / "vai-502-control-plane-mediation.json"
)
DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-24-vai-502-cross-device-playwright-replay-harness.md"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def test_vai_502_replay_fixtures_define_hardware_free_cross_device_path():
    swissknife_replay = _load_json(SWISSKNIFE_REPLAY_PATH)
    mediation_replay = _load_json(HALLUCINATE_MEDIATION_PATH)

    assert swissknife_replay["task_id"] == "VAI-502"
    assert mediation_replay["task_id"] == "VAI-502"
    assert swissknife_replay["requires_hardware"] is False
    assert mediation_replay["requires_hardware"] is False
    assert "playwright" in swissknife_replay["schema"]
    assert "mediation_replay" in mediation_replay["schema"]

    assert swissknife_replay["surface"] == "Swissknife virtual desktop"
    assert swissknife_replay["launch"]["ready_selector"] == ".desktop"
    assert swissknife_replay["phone_hosted_execution"]["mode"] == "phone-hosted"
    assert (
        mediation_replay["interaction_envelope"]["control_plane_command"]
        == swissknife_replay["phone_hosted_execution"]["control_plane_command"]
    )
    assert mediation_replay["policy_decision"]["outcome"] == "allow"

    offload = swissknife_replay["desktop_peer_offload"]
    assert offload["selected_peer"].startswith("desktop peer:")
    assert offload["first_attempt"]["placement"] == "desktop_peer"
    assert offload["first_attempt"]["status"] == "timeout"
    assert offload["fallback"]["placement"] == "phone_local"
    assert offload["fallback"]["receipt_id"] == mediation_replay["desktop_peer"]["fallback_receipt_id"]

    glasses_status = swissknife_replay["meta_glasses_status_output"]
    assert glasses_status["participant_id"] == "meta_glasses:terminal"
    assert "Meta glasses status" in glasses_status["status_text"]
    assert glasses_status["render_receipt_id"] in mediation_replay["mediation_receipt"]["must_precede"]
    assert set(mediation_replay["proof_artifacts"]) <= set(swissknife_replay["proof_artifacts"])


def test_vai_502_discovery_receipt_points_supervisor_to_replay_artifacts():
    source = DISCOVERY_PATH.read_text(encoding="utf-8")
    receipt = _json_block_after(source, "## Replay Harness Receipt")

    assert receipt["schema"] == "cross_device_virtual_desktop_playwright_replay_receipt_v1"
    assert receipt["task_id"] == "VAI-502"
    assert receipt["requires_hardware"] is False
    assert receipt["launch_path"]["surface"] == "Swissknife virtual desktop"
    assert receipt["control_plane"]["mediator"] == "Hallucinate App mediation"
    assert receipt["phone_execution"]["mode"] == "phone-hosted"
    assert receipt["desktop_peer_offload"]["fallback"]["placement"] == "phone_local"
    assert "Meta glasses status" in receipt["meta_glasses_status_output"]["status_text"]
    assert SWISSKNIFE_REPLAY_PATH.relative_to(REPO_ROOT).as_posix() in receipt["proof_artifacts"]
    assert HALLUCINATE_MEDIATION_PATH.relative_to(REPO_ROOT).as_posix() in receipt["proof_artifacts"]
