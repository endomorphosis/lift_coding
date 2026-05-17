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


def _build_check(check_id: str, passed: bool, success_message: str, failure_message: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "message": success_message if passed else failure_message,
        "severity": "error" if not passed else "info",
    }


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

    ready = all(check["status"] == "pass" for check in checks)
    failures = [check["id"] for check in checks if check["status"] == "fail"]
    return {
        "ready": ready,
        "checks": checks,
        "failure_ids": failures,
        "summary": "display_webapp_ready" if ready else "display_webapp_not_ready",
    }
