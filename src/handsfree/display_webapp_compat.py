"""Display-webapp compatibility checks for smart-glasses constraints."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse


def _is_public_https_url(value: str) -> tuple[bool, str]:
    if not isinstance(value, str) or not value.strip():
        return False, "Missing deployment URL."

    parsed = urlparse(value.strip())
    if parsed.scheme.lower() != "https":
        return False, "Deployment URL must use HTTPS."
    if not parsed.netloc:
        return False, "Deployment URL must include a host."

    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1"}:
        return False, "Deployment URL must be publicly reachable."

    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local:
            return False, "Deployment URL must not point to private or loopback IP space."
    except ValueError:
        # Hostname; keep going.
        pass

    return True, "HTTPS public URL configured."


def _build_check(
    check_id: str, passed: bool, success_message: str, failure_message: str
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "message": success_message if passed else failure_message,
        "severity": "error" if not passed else "info",
    }


def _check_passed(
    check_id: str,
    passed: bool,
    success_message: str,
    failure_message: str,
    *,
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "message": success_message if passed else failure_message,
        "severity": "info" if passed else severity,
    }


def _safe_check_id(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.lower())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized or "unnamed_widget"


def _is_webapp_target_widget(widget: Any) -> bool:
    if not isinstance(widget, dict):
        return False

    render_path = (
        widget.get("render_path")
        or (widget.get("target") if isinstance(widget.get("target"), dict) else {}).get(
            "render_path"
        )
        or (
            widget.get("renderer_hints") if isinstance(widget.get("renderer_hints"), dict) else {}
        ).get("primary_render_path")
    )
    fallback = widget.get("fallback") if isinstance(widget.get("fallback"), dict) else {}
    return (
        widget.get("webapp_target") is True
        or render_path == "display-webapp"
        or widget.get("fallback_render_path") == "display-webapp"
        or fallback.get("render_path") == "display-webapp"
    )


def _widget_viewport(widget: dict[str, Any], default_viewport: dict[str, Any]) -> dict[str, Any]:
    browser_preview = (
        widget.get("browser_preview") if isinstance(widget.get("browser_preview"), dict) else {}
    )
    target = widget.get("target") if isinstance(widget.get("target"), dict) else {}
    for viewport in (
        widget.get("viewport"),
        browser_preview.get("viewport"),
        target.get("viewport"),
        default_viewport,
    ):
        if isinstance(viewport, dict):
            return viewport
    return {}


def _widget_focusable_count(widget: dict[str, Any], default_count: Any) -> Any:
    if isinstance(widget.get("focusable_elements"), int):
        return widget.get("focusable_elements")
    focus_order = widget.get("focus_order")
    if isinstance(focus_order, list):
        return len(focus_order)
    return default_count


def _evaluate_webapp_widgets(
    data: dict[str, Any], base_viewport: dict[str, Any]
) -> list[dict[str, Any]]:
    widgets = data.get("widgets")
    if not isinstance(widgets, list):
        return []

    checks: list[dict[str, Any]] = []
    webapp_widgets = [widget for widget in widgets if _is_webapp_target_widget(widget)]
    if not webapp_widgets:
        return checks

    for index, widget in enumerate(webapp_widgets):
        widget_id = str(widget.get("widget_id") or widget.get("id") or f"widget_{index + 1}")
        check_prefix = f"widget_{_safe_check_id(widget_id)}"
        browser_preview = (
            widget.get("browser_preview") if isinstance(widget.get("browser_preview"), dict) else {}
        )
        viewport = _widget_viewport(widget, base_viewport)
        focusable_elements = _widget_focusable_count(widget, data.get("focusable_elements"))
        focus_order = widget.get("focus_order")
        navigation_order_valid = (
            widget.get("navigation_order_valid")
            if widget.get("navigation_order_valid") is not None
            else data.get("navigation_order_valid")
        )
        if isinstance(focus_order, list) and all(
            isinstance(item, str) and item for item in focus_order
        ):
            navigation_order_valid = bool(navigation_order_valid) and len(set(focus_order)) == len(
                focus_order
            )
        deployment_url = str(widget.get("deployment_url") or data.get("deployment_url") or "")
        url_ok, url_message = _is_public_https_url(deployment_url)
        viewport_ok = viewport.get("width") == 600 and viewport.get("height") == 600
        navigation_model = (
            str(widget.get("navigation_model") or data.get("navigation_model") or "")
            .strip()
            .lower()
        )
        dpad_ok = (
            navigation_model == "dpad_focus"
            and isinstance(focusable_elements, int)
            and focusable_elements > 0
            and navigation_order_valid is True
        )
        dark_theme_supported = (
            widget.get("dark_theme_supported")
            if widget.get("dark_theme_supported") is not None
            else data.get("dark_theme_supported")
        ) is True
        min_contrast_ratio = widget.get("min_contrast_ratio", data.get("min_contrast_ratio"))
        contrast_ok = (
            isinstance(min_contrast_ratio, (float, int)) and float(min_contrast_ratio) >= 4.5
        )
        preview_ok = browser_preview.get("renderable") is True
        preview_viewport = (
            browser_preview.get("viewport")
            if isinstance(browser_preview.get("viewport"), dict)
            else {}
        )
        preview_viewport_ok = (
            preview_viewport.get("width") == 600 and preview_viewport.get("height") == 600
        )

        checks.extend(
            [
                _check_passed(
                    f"{check_prefix}_https_public_url",
                    url_ok,
                    f"{widget_id} uses an HTTPS public deployment URL.",
                    f"{widget_id}: {url_message}",
                ),
                _check_passed(
                    f"{check_prefix}_browser_preview",
                    preview_ok and preview_viewport_ok,
                    f"{widget_id} has a renderable 600x600 browser preview.",
                    f"{widget_id} must declare a renderable 600x600 browser preview.",
                ),
                _check_passed(
                    f"{check_prefix}_viewport_600x600",
                    viewport_ok,
                    f"{widget_id} targets the 600x600 display viewport.",
                    f"{widget_id} must target the 600x600 display viewport.",
                ),
                _check_passed(
                    f"{check_prefix}_dpad_focus_navigation",
                    dpad_ok,
                    f"{widget_id} has D-pad focus navigation and a valid focus order.",
                    f"{widget_id} must use D-pad focus navigation with a validated focus order.",
                ),
                _check_passed(
                    f"{check_prefix}_dark_theme_support",
                    dark_theme_supported,
                    f"{widget_id} supports a dark display theme.",
                    f"{widget_id} must support a dark display theme.",
                ),
                _check_passed(
                    f"{check_prefix}_contrast_ratio",
                    contrast_ok,
                    f"{widget_id} meets the display contrast floor.",
                    f"{widget_id} must meet contrast ratio >= 4.5.",
                ),
            ]
        )

    return checks


def evaluate_display_webapp_readiness(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate display-webapp readiness against glasses constraints."""
    data = payload if isinstance(payload, dict) else {}
    viewport = data.get("viewport") if isinstance(data.get("viewport"), dict) else {}
    width = viewport.get("width")
    height = viewport.get("height")
    navigation_model = str(data.get("navigation_model") or "").strip().lower()
    focusable_elements = data.get("focusable_elements")
    navigation_order_valid = data.get("navigation_order_valid") is True
    dark_theme_supported = data.get("dark_theme_supported") is True
    min_contrast_ratio = data.get("min_contrast_ratio")
    app_connection_documented = data.get("app_connection_documented") is True

    url_ok, url_message = _is_public_https_url(str(data.get("deployment_url") or ""))
    viewport_ok = width == 600 and height == 600
    dpad_ok = (
        navigation_model == "dpad_focus"
        and isinstance(focusable_elements, int)
        and focusable_elements > 0
        and navigation_order_valid
    )
    contrast_ok = isinstance(min_contrast_ratio, (float, int)) and float(min_contrast_ratio) >= 4.5

    checks = [
        _build_check(
            "https_public_url",
            url_ok,
            "Deployment URL is HTTPS and publicly reachable.",
            url_message,
        ),
        _build_check(
            "viewport_600x600",
            viewport_ok,
            "Viewport is configured for 600x600 rendering.",
            "Viewport must be exactly 600x600 for display-glasses web apps.",
        ),
        _build_check(
            "dpad_focus_navigation",
            dpad_ok,
            "D-pad focus navigation is configured with a valid focus order.",
            "Navigation must use dpad_focus with focusable elements and validated order.",
        ),
        _build_check(
            "dark_theme_support",
            dark_theme_supported,
            "Dark theme support is enabled.",
            "Dark theme support is required for display readability.",
        ),
        _build_check(
            "contrast_ratio",
            contrast_ok,
            "Minimum contrast ratio meets or exceeds 4.5.",
            "Minimum contrast ratio must be >= 4.5.",
        ),
        _build_check(
            "app_connection_onboarding",
            app_connection_documented,
            "App-connection onboarding is documented.",
            "Document app-connection onboarding for hosted web-app deployment.",
        ),
    ]
    checks.extend(_evaluate_webapp_widgets(data, viewport))

    ready = all(check["status"] == "pass" for check in checks)
    failures = [check["id"] for check in checks if check["status"] == "fail"]
    return {
        "ready": ready,
        "checks": checks,
        "failure_ids": failures,
        "summary": "display_webapp_ready" if ready else "display_webapp_not_ready",
    }
