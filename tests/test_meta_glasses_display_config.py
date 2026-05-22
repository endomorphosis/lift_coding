"""Meta glasses display widget rollout config tests."""

from __future__ import annotations

from types import SimpleNamespace

from handsfree.agent_providers import _display_widget_action_items_from_context
from handsfree.config import (
    DISPLAY_WIDGET_ENV_VARS,
    DISPLAY_WIDGET_FAILURE_MODES,
    DISPLAY_WIDGET_METRIC_NAMES,
    get_meta_glasses_display_widget_config,
    get_meta_glasses_display_widget_observability_contract,
)
from handsfree.metrics import MetricsCollector, get_metrics_collector


def _clear_display_widget_env(monkeypatch) -> None:
    for name in DISPLAY_WIDGET_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _envelope() -> SimpleNamespace:
    return SimpleNamespace(
        artifact_refs=SimpleNamespace(receipt_ref="sha256:receipt"),
        trace=SimpleNamespace(request_id="corr-render"),
    )


def _receipt(policy_decision: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "descriptor_cid": "sha256:descriptor",
        "widget_cid": "sha256:widget",
        "receipt_cid": "sha256:receipt",
        "widget_id": "handsfree.task-progress-widget",
        "correlation_id": "corr-render",
        "policy_decision": policy_decision or {"outcome": "permit"},
        "mobile_action": {
            "request_id": "render-1",
            "state": {"progress": 0.5},
            "fallback": {
                "render_path": "display-webapp",
                "message": "Display unavailable. Showing widget preview.",
            },
        },
    }


def test_display_widget_config_defaults_expose_rollout_flags(monkeypatch) -> None:
    _clear_display_widget_env(monkeypatch)

    config = get_meta_glasses_display_widget_config()

    assert config.enabled is True
    assert config.require_trusted_descriptor is True
    assert config.allow_webapp_fallback is True
    assert config.native_dat_android is False
    assert config.native_dat_ios is False
    assert config.native_dat_enabled is False
    assert config.render_paths == ("display-webapp-fallback",)
    assert config.rollout_warnings == ()
    assert set(config.env_flags) == set(DISPLAY_WIDGET_ENV_VARS)


def test_display_widget_config_parses_boolean_env_values() -> None:
    config = get_meta_glasses_display_widget_config(
        {
            "HANDSFREE_DISPLAY_WIDGETS_ENABLED": "off",
            "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR": "disabled",
            "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK": "no",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID": "enabled",
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS": "1",
        }
    )

    assert config.enabled is False
    assert config.require_trusted_descriptor is False
    assert config.allow_webapp_fallback is False
    assert config.native_dat_android is True
    assert config.native_dat_ios is True
    assert config.render_paths == ("native-dat-android", "native-dat-ios")


def test_display_widget_config_reports_observability_contract() -> None:
    contract = get_meta_glasses_display_widget_observability_contract()

    assert contract["metric_names"] == DISPLAY_WIDGET_METRIC_NAMES
    assert set(contract["metric_names"]) == {
        "render_success_total",
        "policy_denial_total",
        "bridge_error_total",
        "render_latency_ms",
    }
    assert "policy_denied" in DISPLAY_WIDGET_FAILURE_MODES
    assert "bridge_error" in DISPLAY_WIDGET_FAILURE_MODES
    assert "latency_budget_exceeded" in DISPLAY_WIDGET_FAILURE_MODES


def test_display_widget_actions_are_suppressed_by_rollout_flag(monkeypatch) -> None:
    _clear_display_widget_env(monkeypatch)
    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_ENABLED", "false")

    assert _display_widget_action_items_from_context({}, _receipt(), _envelope()) == []

    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_ENABLED", "true")
    actions = _display_widget_action_items_from_context({}, _receipt(), _envelope())

    assert [action["id"] for action in actions][:3] == [
        "mobile_render_display_widget",
        "mobile_update_display_widget",
        "mobile_clear_display_widget",
    ]


def test_display_widget_webapp_fallback_can_be_disabled(monkeypatch) -> None:
    _clear_display_widget_env(monkeypatch)
    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK", "false")

    actions = _display_widget_action_items_from_context({}, _receipt(), _envelope())
    render_payload = actions[0]["mobile_payload"]

    assert render_payload["type"] == "mobile_render_display_widget"
    assert "fallback" not in render_payload


def test_trusted_descriptor_policy_denials_are_observable(monkeypatch) -> None:
    _clear_display_widget_env(monkeypatch)
    monkeypatch.setenv("HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR", "true")
    metrics = get_metrics_collector()
    metrics.reset()

    actions = _display_widget_action_items_from_context(
        {},
        _receipt({"outcome": "deny", "reasons": ["descriptor is not trusted"]}),
        _envelope(),
    )
    snapshot = metrics.get_snapshot()["display_widget_metrics"]

    assert actions == []
    assert snapshot["policy_denial_total"] == 1
    assert snapshot["policy_denial_counts"] == {"deny": 1}


def test_display_widget_metrics_snapshot_tracks_rollout_metrics() -> None:
    metrics = MetricsCollector()

    metrics.record_display_widget_render_success(
        render_path="native-dat-android",
        latency_ms=42,
    )
    metrics.record_display_widget_policy_denial(reason="policy_denied")
    metrics.record_display_widget_bridge_error(
        error_code="bridge_timeout",
        latency_ms=120,
    )
    metrics.record_display_widget_render_latency(50)

    snapshot = metrics.get_snapshot()["display_widget_metrics"]

    assert snapshot["render_success_total"] == 1
    assert snapshot["render_success_counts"] == {"native-dat-android": 1}
    assert snapshot["policy_denial_total"] == 1
    assert snapshot["policy_denial_counts"] == {"policy_denied": 1}
    assert snapshot["bridge_error_total"] == 1
    assert snapshot["bridge_error_counts"] == {"bridge_timeout": 1}
    assert snapshot["render_latency_ms"] == {"p50": 50, "p95": 120, "count": 3}
