"""Environment-backed HandsFree runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

DISPLAY_WIDGET_ENV_DEFAULTS: dict[str, bool] = {
    "HANDSFREE_DISPLAY_WIDGETS_ENABLED": True,
    "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR": True,
    "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK": True,
    "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID": False,
    "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS": False,
}

DISPLAY_WIDGET_ENV_VARS: tuple[str, ...] = tuple(DISPLAY_WIDGET_ENV_DEFAULTS)

DISPLAY_WIDGET_METRIC_NAMES: dict[str, str] = {
    "render_success_total": "handsfree_display_widget_render_success_total",
    "policy_denial_total": "handsfree_display_widget_policy_denial_total",
    "bridge_error_total": "handsfree_display_widget_bridge_error_total",
    "render_latency_ms": "handsfree_display_widget_render_latency_ms",
}

DISPLAY_WIDGET_FAILURE_MODES: tuple[str, ...] = (
    "unsupported_glasses",
    "stale_display_session",
    "missing_release_channel_access",
    "missing_dat_package",
    "descriptor_validation_failed",
    "policy_denied",
    "bridge_error",
    "latency_budget_exceeded",
)

VIRTUAL_AI_OS_POLICY_OUTCOMES: tuple[str, ...] = (
    "permit",
    "deny",
    "require_confirmation",
)

VIRTUAL_AI_OS_EXECUTION_GUARDS: dict[str, dict[str, str]] = {
    "direct_import": {
        "policy_surface": "handsfree.ai.runtime_router",
        "rollback_guard": "keep direct adapters available when remote providers or submodule revisions regress",
    },
    "mcp_remote": {
        "policy_surface": "handsfree.mcp",
        "rollback_guard": "preserve provider-specific transport configuration and timeout fallback to avoid blocking delegation",
    },
    "daemon_mediated": {
        "policy_surface": "ipfs_datasets_py implementation supervisor",
        "rollback_guard": "retain repo-local backlog board, state snapshots, and isolated worktrees for rollback-safe retries",
    },
    "swissknife_orb": {
        "policy_surface": "swissknife ORB policy receipts",
        "rollback_guard": "treat Swissknife as a reviewed UI/runtime surface and avoid speculative MCP++ source rewiring",
    },
    "mobile_remote_terminal": {
        "policy_surface": "HandsFree mobile + Meta glasses display-widget contract",
        "rollback_guard": "keep native-display-unavailable fallback paths active so remote-terminal actions degrade safely",
    },
}

_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def _env_flag(
    environ: Mapping[str, str],
    name: str,
    default: bool,
) -> bool:
    value = environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


@dataclass(frozen=True)
class MetaGlassesDisplayWidgetConfig:
    """Rollout controls for Meta glasses display widget rendering."""

    enabled: bool
    require_trusted_descriptor: bool
    allow_webapp_fallback: bool
    native_dat_android: bool
    native_dat_ios: bool

    @property
    def native_dat_enabled(self) -> bool:
        return self.native_dat_android or self.native_dat_ios

    @property
    def render_paths(self) -> tuple[str, ...]:
        paths: list[str] = []
        if self.native_dat_android:
            paths.append("native-dat-android")
        if self.native_dat_ios:
            paths.append("native-dat-ios")
        if self.allow_webapp_fallback:
            paths.append("display-webapp-fallback")
        return tuple(paths)

    @property
    def rollout_warnings(self) -> tuple[str, ...]:
        warnings: list[str] = []
        if self.enabled and not self.render_paths:
            warnings.append("display_widgets_enabled_without_render_path")
        if self.enabled and not self.require_trusted_descriptor:
            warnings.append("display_widgets_allow_untrusted_descriptors")
        return tuple(warnings)

    @property
    def env_flags(self) -> dict[str, bool]:
        return {
            "HANDSFREE_DISPLAY_WIDGETS_ENABLED": self.enabled,
            "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR": (
                self.require_trusted_descriptor
            ),
            "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK": self.allow_webapp_fallback,
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID": self.native_dat_android,
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS": self.native_dat_ios,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "require_trusted_descriptor": self.require_trusted_descriptor,
            "allow_webapp_fallback": self.allow_webapp_fallback,
            "native_dat_android": self.native_dat_android,
            "native_dat_ios": self.native_dat_ios,
            "native_dat_enabled": self.native_dat_enabled,
            "render_paths": list(self.render_paths),
            "rollout_warnings": list(self.rollout_warnings),
            "metric_names": dict(DISPLAY_WIDGET_METRIC_NAMES),
            "failure_modes": list(DISPLAY_WIDGET_FAILURE_MODES),
        }


def get_meta_glasses_display_widget_config(
    environ: Mapping[str, str] | None = None,
) -> MetaGlassesDisplayWidgetConfig:
    """Build display widget rollout config from environment variables."""
    source = os.environ if environ is None else environ
    return MetaGlassesDisplayWidgetConfig(
        enabled=_env_flag(
            source,
            "HANDSFREE_DISPLAY_WIDGETS_ENABLED",
            DISPLAY_WIDGET_ENV_DEFAULTS["HANDSFREE_DISPLAY_WIDGETS_ENABLED"],
        ),
        require_trusted_descriptor=_env_flag(
            source,
            "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR",
            DISPLAY_WIDGET_ENV_DEFAULTS[
                "HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR"
            ],
        ),
        allow_webapp_fallback=_env_flag(
            source,
            "HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK",
            DISPLAY_WIDGET_ENV_DEFAULTS["HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK"],
        ),
        native_dat_android=_env_flag(
            source,
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID",
            DISPLAY_WIDGET_ENV_DEFAULTS["HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID"],
        ),
        native_dat_ios=_env_flag(
            source,
            "HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS",
            DISPLAY_WIDGET_ENV_DEFAULTS["HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS"],
        ),
    )


def get_meta_glasses_display_widget_observability_contract() -> dict[str, object]:
    """Return stable metric and failure-mode names for rollout evidence."""
    return {
        "metric_names": dict(DISPLAY_WIDGET_METRIC_NAMES),
        "failure_modes": list(DISPLAY_WIDGET_FAILURE_MODES),
    }


def get_virtual_ai_os_observability_contract(
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return the feature-flag, policy, metric, and rollback contract for virtual-AI-OS paths."""

    source = os.environ if environ is None else environ
    display_widget_config = get_meta_glasses_display_widget_config(source)
    return {
        "feature_flags": {
            **display_widget_config.env_flags,
            "HANDSFREE_ENABLE_METRICS": _env_flag(source, "HANDSFREE_ENABLE_METRICS", False),
        },
        "policy_outcomes": list(VIRTUAL_AI_OS_POLICY_OUTCOMES),
        "metric_names": dict(DISPLAY_WIDGET_METRIC_NAMES),
        "failure_modes": list(DISPLAY_WIDGET_FAILURE_MODES),
        "execution_path_guards": {
            path: dict(contract)
            for path, contract in VIRTUAL_AI_OS_EXECUTION_GUARDS.items()
        },
        "display_widget": display_widget_config.as_dict(),
    }
