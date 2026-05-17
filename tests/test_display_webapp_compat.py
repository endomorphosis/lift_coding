from handsfree.display_webapp_compat import evaluate_display_webapp_readiness


def test_display_webapp_readiness_passes_for_valid_configuration():
    result = evaluate_display_webapp_readiness(
        {
            "deployment_url": "https://example.com/glasses",
            "viewport": {"width": 600, "height": 600},
            "navigation_model": "dpad_focus",
            "focusable_elements": 8,
            "navigation_order_valid": True,
            "dark_theme_supported": True,
            "min_contrast_ratio": 4.6,
            "app_connection_documented": True,
        }
    )

    assert result["ready"] is True
    assert result["failure_ids"] == []
    assert result["summary"] == "display_webapp_ready"


def test_display_webapp_readiness_reports_failures_for_invalid_configuration():
    result = evaluate_display_webapp_readiness(
        {
            "deployment_url": "http://localhost:3000",
            "viewport": {"width": 800, "height": 600},
            "navigation_model": "touch_only",
            "focusable_elements": 0,
            "navigation_order_valid": False,
            "dark_theme_supported": False,
            "min_contrast_ratio": 3.4,
            "app_connection_documented": False,
        }
    )

    assert result["ready"] is False
    assert result["summary"] == "display_webapp_not_ready"
    assert set(result["failure_ids"]) == {
        "https_public_url",
        "viewport_600x600",
        "dpad_focus_navigation",
        "dark_theme_support",
        "contrast_ratio",
        "app_connection_onboarding",
    }
