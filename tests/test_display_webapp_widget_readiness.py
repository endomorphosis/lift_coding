import copy
import json
from pathlib import Path

from handsfree.display_webapp_compat import evaluate_display_webapp_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_EXAMPLE = (
    REPO_ROOT / "config" / "display_webapp_readiness.meta_glasses_widget.example.json"
)
RENDERER_SOURCE = REPO_ROOT / "swissknife" / "src" / "services" / "meta-glasses-webapp-renderer.ts"


def _load_example() -> dict:
    return json.loads(READINESS_EXAMPLE.read_text(encoding="utf-8"))


def _widget_prefix(widget_id: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in widget_id.lower()
    )
    return "widget_" + "_".join(part for part in normalized.split("_") if part)


def test_meta_glasses_widget_readiness_example_passes_all_gates() -> None:
    payload = _load_example()
    result = evaluate_display_webapp_readiness(payload)
    widget_id = payload["widgets"][0]["widget_id"]
    prefix = _widget_prefix(widget_id)

    assert result["ready"] is True
    assert result["failure_ids"] == []

    check_ids = {check["id"] for check in result["checks"]}
    assert {
        "https_public_url",
        "viewport_600x600",
        "dpad_focus_navigation",
        "dark_theme_support",
        "contrast_ratio",
        "app_connection_onboarding",
        f"{prefix}_https_public_url",
        f"{prefix}_browser_preview",
        f"{prefix}_viewport_600x600",
        f"{prefix}_dpad_focus_navigation",
        f"{prefix}_dark_theme_support",
        f"{prefix}_contrast_ratio",
    }.issubset(check_ids)


def test_webapp_target_widget_readiness_rejects_missing_preview_focus_and_contrast() -> None:
    payload = _load_example()
    broken = copy.deepcopy(payload)
    widget = broken["widgets"][0]
    widget_id = widget["widget_id"]
    prefix = _widget_prefix(widget_id)
    widget["browser_preview"]["renderable"] = False
    widget["browser_preview"]["viewport"] = {"width": 600, "height": 540}
    widget["viewport"] = {"width": 601, "height": 600}
    widget["focus_order"] = ["pause", "pause"]
    widget["navigation_order_valid"] = True
    widget["min_contrast_ratio"] = 4.2

    result = evaluate_display_webapp_readiness(broken)

    assert result["ready"] is False
    assert {
        f"{prefix}_browser_preview",
        f"{prefix}_viewport_600x600",
        f"{prefix}_dpad_focus_navigation",
        f"{prefix}_contrast_ratio",
    }.issubset(set(result["failure_ids"]))


def test_webapp_renderer_source_exports_preview_and_readiness_contracts() -> None:
    source = RENDERER_SOURCE.read_text(encoding="utf-8")

    for token in [
        "export function renderMetaGlassesWebappPreview",
        "export function buildMetaGlassesWebappReadinessDescriptor",
        "export function evaluateMetaGlassesWebappReadiness",
        "export function assertMetaGlassesWebappReady",
        'role="application"',
        "width: 600px",
        "height: 600px",
        "data-mgw-focus-index",
        "ArrowRight",
        "ArrowLeft",
        "min_contrast_ratio",
    ]:
        assert token in source
