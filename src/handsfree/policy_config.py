"""Policy configuration loader.

Loads policy configuration from YAML file with safe defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PolicyConfig:
    """Policy configuration loaded from YAML file."""

    allow_merge: bool
    allow_rerun: bool
    allow_request_review: bool
    allow_comment: bool
    require_confirmation: bool
    require_checks_green: bool
    required_approvals: int


@dataclass
class PolicyConfigFile:
    """Complete policy configuration including repo overrides."""

    default: PolicyConfig
    repos: dict[str, PolicyConfig]


def _parse_policy_config(data: dict[str, Any]) -> PolicyConfig:
    """Parse a policy configuration dictionary into a PolicyConfig object.

    Args:
        data: Dictionary containing policy configuration.

    Returns:
        PolicyConfig object with parsed values.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    required_fields = [
        "allow_merge",
        "allow_rerun",
        "allow_request_review",
        "allow_comment",
        "require_confirmation",
        "require_checks_green",
        "required_approvals",
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate boolean fields
    bool_fields = [
        "allow_merge",
        "allow_rerun",
        "allow_request_review",
        "allow_comment",
        "require_confirmation",
        "require_checks_green",
    ]
    for field in bool_fields:
        if not isinstance(data[field], bool):
            raise ValueError(f"Field '{field}' must be a boolean")

    # Validate integer fields
    if not isinstance(data["required_approvals"], int):
        raise ValueError("Field 'required_approvals' must be an integer")
    if data["required_approvals"] < 0:
        raise ValueError("Field 'required_approvals' must be non-negative")

    return PolicyConfig(
        allow_merge=data["allow_merge"],
        allow_rerun=data["allow_rerun"],
        allow_request_review=data["allow_request_review"],
        allow_comment=data["allow_comment"],
        require_confirmation=data["require_confirmation"],
        require_checks_green=data["require_checks_green"],
        required_approvals=data["required_approvals"],
    )


def _get_default_config() -> PolicyConfig:
    """Get safe default policy configuration.

    Returns:
        PolicyConfig with conservative default values.
    """
    return PolicyConfig(
        allow_merge=False,
        allow_rerun=True,
        allow_request_review=True,
        allow_comment=True,
        require_confirmation=True,
        require_checks_green=True,
        required_approvals=1,
    )


def load_policy_config(config_path: str | None = None) -> PolicyConfigFile:
    """Load policy configuration from YAML file.

    Args:
        config_path: Path to the policy configuration YAML file.
                    If None, uses default path: config/policies.yaml

    Returns:
        PolicyConfigFile with default and repo-specific configurations.
        If file is missing or invalid, returns safe defaults.
    """
    if config_path is None:
        # Default path relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = os.path.join(project_root, "config", "policies.yaml")

    # If file doesn't exist, return safe defaults
    if not os.path.exists(config_path):
        return PolicyConfigFile(default=_get_default_config(), repos={})

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("Config file must contain a YAML dictionary")

        # Parse default policy
        if "default" not in data:
            raise ValueError("Config file must contain 'default' section")

        default_config = _parse_policy_config(data["default"])

        # Parse repo overrides
        repos = {}
        if "repos" in data and isinstance(data["repos"], dict):
            for repo_name, repo_data in data["repos"].items():
                if not isinstance(repo_name, str):
                    raise ValueError(f"Repository name must be a string: {repo_name}")
                if not isinstance(repo_data, dict):
                    raise ValueError(
                        f"Repository config must be a dictionary: {repo_name}"
                    )

                # Merge repo-specific config with defaults
                merged_data = {
                    "allow_merge": repo_data.get(
                        "allow_merge", default_config.allow_merge
                    ),
                    "allow_rerun": repo_data.get(
                        "allow_rerun", default_config.allow_rerun
                    ),
                    "allow_request_review": repo_data.get(
                        "allow_request_review", default_config.allow_request_review
                    ),
                    "allow_comment": repo_data.get(
                        "allow_comment", default_config.allow_comment
                    ),
                    "require_confirmation": repo_data.get(
                        "require_confirmation", default_config.require_confirmation
                    ),
                    "require_checks_green": repo_data.get(
                        "require_checks_green", default_config.require_checks_green
                    ),
                    "required_approvals": repo_data.get(
                        "required_approvals", default_config.required_approvals
                    ),
                }
                repos[repo_name] = _parse_policy_config(merged_data)

        return PolicyConfigFile(default=default_config, repos=repos)

    except (yaml.YAMLError, ValueError, KeyError, OSError) as e:
        # If config file is invalid, log warning and return safe defaults
        import logging

        logging.warning(f"Failed to load policy config from {config_path}: {e}")
        logging.warning("Using safe default policy configuration")
        return PolicyConfigFile(default=_get_default_config(), repos={})


# Cache the loaded configuration
_cached_config: PolicyConfigFile | None = None


def get_policy_config(config_path: str | None = None) -> PolicyConfigFile:
    """Get the policy configuration (cached).

    Args:
        config_path: Optional path to config file. Uses default if None.

    Returns:
        PolicyConfigFile with configurations.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_policy_config(config_path)
    return _cached_config


def reload_policy_config(config_path: str | None = None) -> PolicyConfigFile:
    """Reload policy configuration from file.

    Args:
        config_path: Optional path to config file. Uses default if None.

    Returns:
        Newly loaded PolicyConfigFile.
    """
    global _cached_config
    _cached_config = load_policy_config(config_path)
    return _cached_config


def clear_policy_config_cache():
    """Clear the cached policy configuration.

    Used primarily for testing to ensure clean state between tests.
    """
    global _cached_config
    _cached_config = None
