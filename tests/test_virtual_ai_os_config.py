from handsfree.config import (
    get_meta_glasses_display_widget_config,
    get_virtual_ai_os_observability_contract,
)


def test_virtual_ai_os_observability_contract_defaults_are_stable() -> None:
    contract = get_virtual_ai_os_observability_contract({})

    assert contract["feature_flags"]["HANDSFREE_ENABLE_METRICS"] is False
    assert contract["feature_flags"]["HANDSFREE_DISPLAY_WIDGETS_ENABLED"] is True
    assert contract["policy_outcomes"] == ["permit", "deny", "require_confirmation"]
    assert "render_success_total" in contract["metric_names"]
    assert "bridge_error" in contract["failure_modes"]
    assert "daemon_mediated" in contract["execution_path_guards"]
    expected_daemon_guard = (
        "retain repo-local backlog board, state snapshots, and isolated worktrees "
        "for rollback-safe retries"
    )
    assert (
        contract["execution_path_guards"]["daemon_mediated"]["rollback_guard"]
        == expected_daemon_guard
    )
    assert "rollback_guard" in contract["execution_path_guards"]["mobile_remote_terminal"]


def test_virtual_ai_os_observability_contract_honors_environment_overrides() -> None:
    contract = get_virtual_ai_os_observability_contract(
        {
            "HANDSFREE_ENABLE_METRICS": "true",
            "HANDSFREE_DISPLAY_WIDGETS_ENABLED": "false",
            "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR": "false",
            "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK": "false",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID": "true",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS": "false",
        }
    )

    assert contract["feature_flags"]["HANDSFREE_ENABLE_METRICS"] is True
    assert contract["feature_flags"]["HANDSFREE_DISPLAY_WIDGETS_ENABLED"] is False
    assert contract["display_widget"]["enabled"] is False
    assert contract["display_widget"]["native_dat_android"] is True
    assert contract["display_widget"]["allow_webapp_fallback"] is False


def test_meta_glasses_display_widget_config_surfaces_rollout_warnings() -> None:
    config = get_meta_glasses_display_widget_config(
        {
            "HANDSFREE_DISPLAY_WIDGETS_ENABLED": "true",
            "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR": "false",
            "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK": "false",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID": "false",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS": "false",
        }
    )

    assert config.render_paths == ()
    assert "display_widgets_enabled_without_render_path" in config.rollout_warnings
    assert "display_widgets_allow_untrusted_descriptors" in config.rollout_warnings
