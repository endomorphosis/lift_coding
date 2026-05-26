"""Hardware-free Meta Ray-Ban Display simulator fixture tests."""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

from handsfree.display_webapp_compat import evaluate_display_webapp_readiness

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree.api import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "dev" / "meta-rayban-display-simulator"
FIXTURE_PATH = SIMULATOR_DIR / "fixtures" / "task-progress.json"
SIMULATOR_JS = SIMULATOR_DIR / "simulator.js"
SIMULATOR_HTML = SIMULATOR_DIR / "index.html"
WEBAPP_DIR = SIMULATOR_DIR / "webapp"
client = TestClient(app)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_task_progress_fixture_passes_display_webapp_readiness() -> None:
    fixture = _load_fixture()
    result = evaluate_display_webapp_readiness(fixture["readiness"])

    assert result["ready"] is True
    assert result["failure_ids"] == []
    assert fixture["viewport"] == {"width": 600, "height": 600}
    assert fixture["readiness"]["widgets"][0]["focus_order"] == fixture["focus_order"]


def test_task_progress_fixture_regions_and_actions_match_simulator_constraints() -> None:
    fixture = _load_fixture()
    action_ids = {action["id"] for action in fixture["actions"]}
    viewport = fixture["viewport"]

    assert set(fixture["focus_order"]).issubset(action_ids)
    for region in fixture["regions"]:
      assert region["x"] >= 0
      assert region["y"] >= 0
      assert region["width"] > 0
      assert region["height"] > 0
      assert region["x"] + region["width"] <= viewport["width"]
      assert region["y"] + region["height"] <= viewport["height"]
      if region["kind"] == "action":
          assert region["action_id"] in action_ids
      if region["kind"] == "media":
          assert region["media"]["uri"].startswith("https://")


def test_simulator_js_validates_fixture_and_builds_bridge_result() -> None:
    script = f"""
      const fs = require('fs');
      const simulator = require({json.dumps(str(SIMULATOR_JS))});
      const fixture = JSON.parse(fs.readFileSync({json.dumps(str(FIXTURE_PATH))}, 'utf8'));
      const validation = simulator.validateManifest(fixture);
      const result = simulator.buildBridgeResult('render_widget', fixture, 'unavailable', {{
        request_id: 'test-request',
        sensor: {{ heading: 18 }}
      }});
      if (!validation.ok) {{
        throw new Error(validation.errors.join('\\n'));
      }}
      if (result.renderPath !== 'display-webapp') {{
        throw new Error(`unexpected renderPath: ${{result.renderPath}}`);
      }}
      if (result.widgetId !== fixture.widget_id || result.supported !== false) {{
        throw new Error('bridge result did not preserve widget metadata');
      }}
    """
    subprocess.run(["node", "-e", script], check=True, cwd=REPO_ROOT)


def test_simulator_html_declares_keyboard_and_export_controls() -> None:
    html = SIMULATOR_HTML.read_text(encoding="utf-8")
    source = SIMULATOR_JS.read_text(encoding="utf-8")

    assert "display-frame" in html
    assert "600 by 600 display preview" in html
    assert "fixture-select" in html
    assert "export-trace-button" in html
    assert "export-readiness-button" in html
    for token in ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "fetch"]:
        assert token in source


def test_backend_serves_meta_rayban_display_simulator_shell_and_assets() -> None:
    shell = client.get("/simulator/meta-rayban-display")
    script = client.get("/simulator/meta-rayban-display/simulator.js")
    fixture = client.get("/simulator/meta-rayban-display/fixtures/task-progress.json")
    missing = client.get("/simulator/meta-rayban-display/missing.js")

    assert shell.status_code == 200
    assert "text/html" in shell.headers["content-type"]
    assert "display-frame" in shell.text
    assert script.status_code == 200
    assert "validateManifest" in script.text
    assert fixture.status_code == 200
    assert fixture.json()["viewport"] == {"width": 600, "height": 600}
    assert missing.status_code == 404


def test_webapp_preview_is_fixed_600x600_and_dpad_operable() -> None:
    html = (WEBAPP_DIR / "index.html").read_text(encoding="utf-8")
    css = (WEBAPP_DIR / "styles.css").read_text(encoding="utf-8")
    app_js = (WEBAPP_DIR / "app.js").read_text(encoding="utf-8")

    assert "width=600,height=600" in html
    assert "data-meta-rayban-display-webapp" in html
    assert "role=\"application\"" in html
    assert "width: 600px" in css
    assert "height: 600px" in css
    assert "overflow: hidden" in css
    for token in ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter"]:
        assert token in app_js
    for token in [
        "descriptor_cid",
        "orb_receipt_cid",
        "correlation_id",
        "sessionStorage",
        "/v1/mobile/orb/register_edge_capabilities",
        "/v1/mobile/orb/publish_glasses_event",
        "/v1/mobile/orb/bind_service",
        "/v1/mobile/orb/subscribe_service_updates",
        "/v1/mobile/orb/invoke_service",
        "/v1/mobile/orb/dispatch_glasses_response",
        "display_action",
        "TASK_SERVICE_DESCRIPTOR",
        "mcp++/profile-a-idl",
        "ORB_SUBSCRIPTIONS_STORAGE_KEY",
        "clearCachedOrbBinding",
        "handsfree:lastDisplayWebappOrbSubscription",
        "handsfree:lastDisplayWebappOrbDispatch",
    ]:
        assert token in app_js


def test_webapp_preview_readiness_descriptor_passes_linter() -> None:
    readiness = json.loads((WEBAPP_DIR / "readiness.json").read_text(encoding="utf-8"))
    result = evaluate_display_webapp_readiness(readiness)

    assert result["ready"] is True
    assert result["failure_ids"] == []
    assert readiness["widgets"][0]["browser_preview"]["renderer"].endswith("webapp/app.js")


def test_webapp_preview_package_declares_static_files_and_png_icons() -> None:
    manifest = json.loads((WEBAPP_DIR / "manifest.webmanifest").read_text(encoding="utf-8"))
    readiness = json.loads((WEBAPP_DIR / "readiness.json").read_text(encoding="utf-8"))

    for relative_path in readiness["static_files"]:
        assert (WEBAPP_DIR / relative_path).is_file()

    assert "readiness.json" in readiness["static_files"]
    assert readiness["hosting"]["requires_publicly_available_https"] is True
    assert readiness["hosting"]["qr_registration_supported"] is True
    assert "Meta AI app" in readiness["hosting"]["meta_ai_app_onboarding"]
    assert "Web apps" in readiness["hosting"]["meta_ai_app_onboarding"]
    assert "native iPhone DAT" in readiness["hosting"]["native_dat_migration_gate"]

    icons = manifest["icons"]
    assert {icon["sizes"] for icon in icons} >= {"52x52", "192x192"}
    assert readiness["manifest"]["icons"] == [
        {"src": "icons/icon-52.png", "sizes": "52x52", "type": "image/png"},
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    ]
    for icon in icons:
        assert icon["type"] == "image/png"
        assert icon["src"].startswith("./icons/")
        icon_path = WEBAPP_DIR / icon["src"].removeprefix("./")
        assert icon_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_ios_rayban_runbooks_cover_https_webapp_onboarding_path() -> None:
    runbook = (REPO_ROOT / "docs" / "ios-rayban-mvp1-runbook.md").read_text(
        encoding="utf-8"
    )
    demo_runbook = (
        REPO_ROOT / "docs" / "ios-rayban-mvp1-demo-runbook.md"
    ).read_text(encoding="utf-8")
    webapp_readme = (WEBAPP_DIR / "README.md").read_text(encoding="utf-8")
    combined = "\n".join([runbook, demo_runbook, webapp_readme])

    for phrase in [
        "publicly available HTTPS",
        "QR",
        "Meta AI app",
        "Web apps",
        "readiness.json",
        "native iPhone DAT",
    ]:
        assert phrase in combined


def test_backend_serves_webapp_preview_assets() -> None:
    index = client.get("/simulator/meta-rayban-display/webapp/index.html")
    app_js = client.get("/simulator/meta-rayban-display/webapp/app.js")
    readiness = client.get("/simulator/meta-rayban-display/webapp/readiness.json")
    manifest = client.get("/simulator/meta-rayban-display/webapp/manifest.webmanifest")
    icon = client.get("/simulator/meta-rayban-display/webapp/icons/icon-52.png")

    assert index.status_code == 200
    assert "data-meta-rayban-display-webapp" in index.text
    assert app_js.status_code == 200
    assert "handsfree:lastDisplayWebappEvent" in app_js.text
    assert readiness.status_code == 200
    assert readiness.json()["viewport"] == {"width": 600, "height": 600}
    assert manifest.status_code == 200
    assert manifest.json()["display"] == "fullscreen"
    assert icon.status_code == 200
    assert icon.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_webapp_display_action_event_can_publish_through_mobile_orb_backend() -> None:
    fixture = _load_fixture()
    registered = client.post(
        "/v1/mobile/orb/register_edge_capabilities",
        json={
            "edge_id": "handsfree-meta-rayban-display-webapp-preview-test",
            "platform": "simulator",
            "device_model": "Meta Ray-Ban Display Web App Preview",
            "dat_capabilities": {
                "session": True,
                "audio": False,
                "display": True,
                "displayVideo": False,
                "webAppDisplay": True,
            },
            "local_interface_cids": [
                "handsfree.meta_glasses.mobile.mobile_orb_bridge@0.1.0",
                "handsfree.meta_glasses.display.display_widget_bridge@0.1.0",
                fixture["descriptor_cid"],
            ],
            "transport_preferences": ["local", "http", "mcp-server"],
        },
    )
    assert registered.status_code == 200

    event_payload = {
        "schema": "handsfree.meta-rayban-display/webapp-event",
        "action_id": "pause",
        "operation": "activate",
        "widget_id": fixture["widget_id"],
        "widget_cid": fixture["widget_cid"],
        "descriptor_cid": fixture["descriptor_cid"],
        "orb_receipt_cid": fixture["orb_receipt_cid"],
        "correlation_id": fixture["correlation_id"],
        "recorded_at": "2026-05-23T12:00:00Z",
    }
    published = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": registered.json()["edge_session_id"],
            "event_type": "display_action",
            "payload": event_payload,
            "correlation_id": fixture["correlation_id"],
            "parent_receipt_cids": [fixture["orb_receipt_cid"]],
            "observed_at": event_payload["recorded_at"],
        },
    )

    assert published.status_code == 200
    payload = published.json()
    assert payload["accepted"] is True
    assert payload["event_cid"].startswith("sha256:mobile-orb-event:")
    assert payload["receipt_cid"].startswith("sha256:mobile-orb-receipt:")
    assert payload["routed_operations"] == ["bind_service", "invoke_service"]


def test_webapp_display_action_can_complete_orb_bind_invoke_dispatch_loop(monkeypatch) -> None:
    monkeypatch.delenv("HANDSFREE_MCP_IPFS_DATASETS_URL", raising=False)
    monkeypatch.delenv("HANDSFREE_MCP_IPFS_DATASETS_COMMAND", raising=False)

    fixture = _load_fixture()
    registered = client.post(
        "/v1/mobile/orb/register_edge_capabilities",
        json={
            "edge_id": "handsfree-meta-rayban-display-webapp-preview-loop-test",
            "platform": "simulator",
            "device_model": "Meta Ray-Ban Display Web App Preview",
            "dat_capabilities": {
                "session": True,
                "audio": False,
                "display": True,
                "displayVideo": False,
                "webAppDisplay": True,
            },
            "local_interface_cids": [
                "handsfree.meta_glasses.mobile.mobile_orb_bridge@0.1.0",
                "handsfree.meta_glasses.display.display_widget_bridge@0.1.0",
                fixture["descriptor_cid"],
            ],
            "transport_preferences": ["local", "http", "mcp-server"],
        },
    )
    assert registered.status_code == 200
    edge_session_id = registered.json()["edge_session_id"]

    event_payload = {
        "schema": "handsfree.meta-rayban-display/webapp-event",
        "action_id": "pause",
        "operation": "activate",
        "widget_id": fixture["widget_id"],
        "widget_cid": fixture["widget_cid"],
        "descriptor_cid": fixture["descriptor_cid"],
        "orb_receipt_cid": fixture["orb_receipt_cid"],
        "correlation_id": fixture["correlation_id"],
        "recorded_at": "2026-05-23T12:00:00Z",
    }
    published = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": edge_session_id,
            "event_type": "display_action",
            "payload": event_payload,
            "correlation_id": fixture["correlation_id"],
            "parent_receipt_cids": [fixture["orb_receipt_cid"]],
            "observed_at": event_payload["recorded_at"],
        },
    )
    assert published.status_code == 200
    published_payload = published.json()

    service_descriptor = {
        "name": "task_status_service",
        "namespace": "handsfree.services.tasks",
        "version": "0.1.0",
        "metadata": {
            "server_family": "ipfs_datasets",
            "tool_name": "tools_dispatch",
            "provider_name": "ipfs_datasets_mcp",
        },
        "methods": [
            {
                "name": "pause_task",
                "inputSchema": {"type": "object"},
                "outputSchema": {"type": "object"},
            }
        ],
        "requires": [
            "mcp++/profile-a-idl",
            "mcp++/profile-b-cid-artifacts",
            "mcp++/invoke",
            "mcp++/receipts",
        ],
        "compatibility": {
            "viewport": fixture["viewport"],
            "render_targets": ["display_widget", "display_webapp", "audio", "mobile_card"],
        },
    }
    binding = client.post(
        "/v1/mobile/orb/bind_service",
        json={
            "edge_session_id": edge_session_id,
            "service_interface_cid": "handsfree.services.tasks.task_status_service@0.1.0",
            "service_descriptor": service_descriptor,
            "operation": "pause_task",
            "transport_preference": "mcp-server",
            "user_intent": "Pause requested.",
            "policy_context": {
                "surface": "meta-rayban-display-webapp-preview",
                "widget_id": fixture["widget_id"],
                "mcp_plus_plus_profiles": service_descriptor["requires"],
            },
        },
    )
    assert binding.status_code == 200
    binding_payload = binding.json()
    binding_metadata = binding_payload["orb_binding"]["transport_binding"]["metadata"]
    assert binding_metadata["descriptor_kind"] == "mcp-idl"
    assert binding_metadata["server_family"] == "ipfs_datasets"
    assert binding_metadata["tool_name"] == "tools_dispatch"
    assert binding_metadata["interface_descriptor"]["requires"] == service_descriptor["requires"]
    assert binding_metadata["interface_descriptor"]["metadata"] == service_descriptor["metadata"]

    subscription = client.post(
        "/v1/mobile/orb/subscribe_service_updates",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "pause_task",
            "arguments": {"task_id": "simulator-task-progress"},
            "stream": "task-progress",
            "correlation_id": fixture["correlation_id"],
        },
    )
    assert subscription.status_code == 200
    subscription_payload = subscription.json()
    assert subscription_payload["generation_key"].endswith(":pause_task:task-progress")
    assert subscription_payload["subscription"]["service_id"] == "task_status_service"
    assert subscription_payload["subscription"]["orb_binding"]["transport"] == "mcp-server"

    display_widget_action = {
        "operation": "update_widget",
        "descriptor_cid": fixture["descriptor_cid"],
        "interface_cid": fixture["descriptor_cid"],
        "widget_id": fixture["widget_id"],
        "widget_cid": fixture["widget_cid"],
        "correlation_id": fixture["correlation_id"],
        "activated_action_id": "pause",
        "manifest": fixture,
        "state": {
            **fixture["state"],
            "last_action": "pause",
            "status": "Pause requested",
        },
        "fallback": {
            "render_path": "display-webapp",
            "message": "Pause requested.",
        },
    }
    invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "pause_task",
            "arguments": {
                "task_id": "simulator-task-progress",
                "action_id": "pause",
                "source_event_cid": published_payload["event_cid"],
                "display_widget_action": display_widget_action,
                "spoken_text": "Pause requested.",
            },
            "glasses_context": {
                "surface": "meta-rayban-display-webapp-preview",
                "input": "dpad-enter",
            },
            "display_context": {
                "viewport": fixture["viewport"],
                "focus_order": fixture["focus_order"],
                "focused_action_id": "pause",
            },
            "correlation_id": fixture["correlation_id"],
            "parent_receipt_cids": [
                published_payload["receipt_cid"],
                fixture["orb_receipt_cid"],
            ],
        },
    )
    assert invoked.status_code == 200
    invoked_payload = invoked.json()
    assert invoked_payload["ok"] is True
    assert invoked_payload["service_result"]["transport_result"]["status"] == "unresolved"
    assert invoked_payload["display_widget_action"]["type"] == "mobile_update_display_widget"
    assert invoked_payload["display_widget_action"]["widget_id"] == fixture["widget_id"]
    assert invoked_payload["display_widget_action"]["activated_action_id"] == "pause"
    assert invoked_payload["display_widget_action"]["orb_receipt_cid"] == (
        invoked_payload["receipt_cid"]
    )

    dispatched = client.post(
        "/v1/mobile/orb/dispatch_glasses_response",
        json={
            "edge_session_id": edge_session_id,
            "result": invoked_payload,
            "render_targets": ["display_webapp", "display_widget", "audio", "mobile_card"],
            "fallback": {
                "render_path": "display-webapp",
                "message": "Pause requested.",
            },
            "correlation_id": fixture["correlation_id"],
            "parent_receipt_cids": [
                published_payload["receipt_cid"],
                invoked_payload["receipt_cid"],
            ],
        },
    )
    assert dispatched.status_code == 200
    dispatched_payload = dispatched.json()
    assert dispatched_payload["display_widget_action"]["type"] == "mobile_update_display_widget"
    assert dispatched_payload["dispatched_actions"][0]["mobile_payload"] == (
        dispatched_payload["display_widget_action"]
    )
    assert dispatched_payload["spoken_text"] == "Pause requested."


def test_static_openapi_documents_meta_rayban_display_simulator_route() -> None:
    raw_spec = (REPO_ROOT / "spec" / "openapi.yaml").read_text(encoding="utf-8")

    assert "/simulator/meta-rayban-display" in raw_spec
    assert "/simulator/meta-rayban-display/{asset_path}" in raw_spec
