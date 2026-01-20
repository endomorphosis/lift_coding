"""Tests for policy configuration loader."""

import tempfile
from pathlib import Path

import pytest

from handsfree.policy_config import (
    PolicyConfig,
    _get_default_config,
    _parse_policy_config,
    load_policy_config,
    reload_policy_config,
)


def test_get_default_config():
    """Test that default config has conservative settings."""
    config = _get_default_config()

    assert config.allow_merge is False
    assert config.allow_rerun is True
    assert config.allow_request_review is True
    assert config.allow_comment is True
    assert config.require_confirmation is True
    assert config.require_checks_green is True
    assert config.required_approvals == 1


def test_parse_policy_config_valid():
    """Test parsing a valid policy config dictionary."""
    data = {
        "allow_merge": True,
        "allow_rerun": True,
        "allow_request_review": True,
        "allow_comment": True,
        "require_confirmation": False,
        "require_checks_green": False,
        "required_approvals": 2,
    }

    config = _parse_policy_config(data)

    assert config.allow_merge is True
    assert config.allow_rerun is True
    assert config.allow_request_review is True
    assert config.allow_comment is True
    assert config.require_confirmation is False
    assert config.require_checks_green is False
    assert config.required_approvals == 2


def test_parse_policy_config_missing_field():
    """Test that parsing fails when required field is missing."""
    data = {
        "allow_merge": True,
        "allow_rerun": True,
        # Missing other required fields
    }

    with pytest.raises(ValueError, match="Missing required field"):
        _parse_policy_config(data)


def test_parse_policy_config_invalid_boolean():
    """Test that parsing fails when boolean field has wrong type."""
    data = {
        "allow_merge": "yes",  # Should be boolean
        "allow_rerun": True,
        "allow_request_review": True,
        "allow_comment": True,
        "require_confirmation": True,
        "require_checks_green": True,
        "required_approvals": 1,
    }

    with pytest.raises(ValueError, match="must be a boolean"):
        _parse_policy_config(data)


def test_parse_policy_config_invalid_integer():
    """Test that parsing fails when integer field has wrong type."""
    data = {
        "allow_merge": True,
        "allow_rerun": True,
        "allow_request_review": True,
        "allow_comment": True,
        "require_confirmation": True,
        "require_checks_green": True,
        "required_approvals": "one",  # Should be integer
    }

    with pytest.raises(ValueError, match="must be an integer"):
        _parse_policy_config(data)


def test_parse_policy_config_negative_approvals():
    """Test that parsing fails when required_approvals is negative."""
    data = {
        "allow_merge": True,
        "allow_rerun": True,
        "allow_request_review": True,
        "allow_comment": True,
        "require_confirmation": True,
        "require_checks_green": True,
        "required_approvals": -1,
    }

    with pytest.raises(ValueError, match="must be non-negative"):
        _parse_policy_config(data)


def test_load_policy_config_missing_file():
    """Test that missing config file returns safe defaults."""
    config_file = load_policy_config("/nonexistent/path/policies.yaml")

    assert config_file.default.allow_merge is False
    assert config_file.default.allow_rerun is True
    assert config_file.default.require_confirmation is True
    assert len(config_file.repos) == 0


def test_load_policy_config_valid_yaml():
    """Test loading a valid YAML config file."""
    yaml_content = """
default:
  allow_merge: true
  allow_rerun: true
  allow_request_review: true
  allow_comment: true
  require_confirmation: false
  require_checks_green: false
  required_approvals: 0

repos: {}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = load_policy_config(temp_path)

        assert config_file.default.allow_merge is True
        assert config_file.default.require_confirmation is False
        assert config_file.default.required_approvals == 0
        assert len(config_file.repos) == 0
    finally:
        Path(temp_path).unlink()


def test_load_policy_config_with_repo_overrides():
    """Test loading config with per-repo overrides."""
    yaml_content = """
default:
  allow_merge: false
  allow_rerun: true
  allow_request_review: true
  allow_comment: true
  require_confirmation: true
  require_checks_green: true
  required_approvals: 1

repos:
  owner/repo1:
    allow_merge: true
    require_confirmation: false
  owner/repo2:
    required_approvals: 3
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = load_policy_config(temp_path)

        # Check default
        assert config_file.default.allow_merge is False
        assert config_file.default.required_approvals == 1

        # Check repo1 override
        assert "owner/repo1" in config_file.repos
        repo1 = config_file.repos["owner/repo1"]
        assert repo1.allow_merge is True
        assert repo1.require_confirmation is False
        assert repo1.required_approvals == 1  # Inherited from default

        # Check repo2 override
        assert "owner/repo2" in config_file.repos
        repo2 = config_file.repos["owner/repo2"]
        assert repo2.allow_merge is False  # Inherited from default
        assert repo2.required_approvals == 3
    finally:
        Path(temp_path).unlink()


def test_load_policy_config_invalid_yaml():
    """Test that invalid YAML returns safe defaults."""
    yaml_content = """
this is: not
valid: yaml: content
  with: bad indentation
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = load_policy_config(temp_path)

        # Should fall back to safe defaults
        assert config_file.default.allow_merge is False
        assert config_file.default.require_confirmation is True
        assert len(config_file.repos) == 0
    finally:
        Path(temp_path).unlink()


def test_load_policy_config_missing_default():
    """Test that config without default section returns safe defaults."""
    yaml_content = """
repos:
  owner/repo:
    allow_merge: true
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = load_policy_config(temp_path)

        # Should fall back to safe defaults
        assert config_file.default.allow_merge is False
        assert len(config_file.repos) == 0
    finally:
        Path(temp_path).unlink()


def test_load_policy_config_malformed_repo_config():
    """Test that malformed repo config falls back to safe defaults."""
    yaml_content = """
default:
  allow_merge: false
  allow_rerun: true
  allow_request_review: true
  allow_comment: true
  require_confirmation: true
  require_checks_green: true
  required_approvals: 1

repos:
  owner/repo:
    allow_merge: "not a boolean"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = load_policy_config(temp_path)

        # Should fall back to safe defaults due to validation error
        assert config_file.default.allow_merge is False
        assert len(config_file.repos) == 0
    finally:
        Path(temp_path).unlink()


def test_reload_policy_config():
    """Test reloading policy configuration."""
    from handsfree.policy_config import clear_policy_config_cache

    yaml_content = """
default:
  allow_merge: true
  allow_rerun: true
  allow_request_review: true
  allow_comment: true
  require_confirmation: false
  require_checks_green: false
  required_approvals: 0

repos: {}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        config_file = reload_policy_config(temp_path)

        assert config_file.default.allow_merge is True
        assert config_file.default.require_confirmation is False
    finally:
        Path(temp_path).unlink()
        clear_policy_config_cache()
