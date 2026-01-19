"""Tests for policy evaluation."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.repo_policies import (
    create_or_update_repo_policy,
    get_default_policy,
    get_repo_policy,
)
from handsfree.policy import PolicyDecision, evaluate_action_policy


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_get_default_policy():
    """Test that default policy is conservative."""
    policy = get_default_policy()

    assert policy.allow_merge is False
    assert policy.allow_rerun is True
    assert policy.allow_request_review is True
    assert policy.require_confirmation is True
    assert policy.require_checks_green is True
    assert policy.required_approvals == 1


def test_create_repo_policy(db_conn):
    """Test creating a new repo policy."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    policy = create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=True,
        require_confirmation=False,
    )

    assert policy.user_id == user_id
    assert policy.repo_full_name == repo
    assert policy.allow_merge is True
    assert policy.require_confirmation is False


def test_update_repo_policy(db_conn):
    """Test updating an existing repo policy."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create initial policy
    policy1 = create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=False,
    )

    # Update it
    policy2 = create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=True,
    )

    assert policy1.id == policy2.id  # Same policy, just updated
    assert policy2.allow_merge is True


def test_get_repo_policy(db_conn):
    """Test retrieving a repo policy."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Should return None for non-existent policy
    policy = get_repo_policy(db_conn, user_id, repo)
    assert policy is None

    # Create policy
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
    )

    # Should now return the policy
    policy = get_repo_policy(db_conn, user_id, repo)
    assert policy is not None
    assert policy.repo_full_name == repo


def test_evaluate_action_policy_deny_unknown_action(db_conn):
    """Test that unknown action types are denied."""
    user_id = str(uuid.uuid4())

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name="owner/repo",
        action_type="unknown_action",
    )

    assert result.decision == PolicyDecision.DENY
    assert "unknown action type" in result.reason.lower()


def test_evaluate_action_policy_deny_merge_not_allowed(db_conn):
    """Test that merge is denied when not allowed by policy."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create policy that denies merge
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=False,
    )

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="merge",
    )

    assert result.decision == PolicyDecision.DENY
    assert "not allowed" in result.reason.lower()


def test_evaluate_action_policy_require_confirmation(db_conn):
    """Test that confirmation is required when policy says so."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create policy that allows request_review but requires confirmation
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_request_review=True,
        require_confirmation=True,
    )

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="request_review",
    )

    assert result.decision == PolicyDecision.REQUIRE_CONFIRMATION
    assert "confirmation" in result.reason.lower()


def test_evaluate_action_policy_allow_without_confirmation(db_conn):
    """Test that action is allowed when confirmation is not required."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create policy that allows request_review without confirmation
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_request_review=True,
        require_confirmation=False,
    )

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="request_review",
    )

    assert result.decision == PolicyDecision.ALLOW
    assert "allowed" in result.reason.lower()


def test_evaluate_action_policy_deny_failing_checks(db_conn):
    """Test that merge is denied when checks are failing."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create policy that allows merge but requires green checks
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=True,
        require_checks_green=True,
    )

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="merge",
        pr_checks_status="failing",
    )

    assert result.decision == PolicyDecision.DENY
    assert "failing" in result.reason.lower()


def test_evaluate_action_policy_deny_insufficient_approvals(db_conn):
    """Test that merge is denied when approvals are insufficient."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Create policy that requires 2 approvals
    # Disable both confirmation and checks_green to test approval check in isolation
    create_or_update_repo_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        allow_merge=True,
        required_approvals=2,
        require_confirmation=False,
        require_checks_green=False,  # Disable to avoid check status requirement
    )

    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="merge",
        pr_approvals_count=1,
    )

    assert result.decision == PolicyDecision.DENY
    assert "approval" in result.reason.lower()
    assert result.required_approvals == 2


def test_evaluate_action_policy_uses_default_when_no_policy(db_conn):
    """Test that default policy is used when no policy exists."""
    user_id = str(uuid.uuid4())
    repo = "owner/repo"

    # Don't create any policy - should use default
    result = evaluate_action_policy(
        db_conn,
        user_id=user_id,
        repo_full_name=repo,
        action_type="request_review",
    )

    # Default policy allows request_review but requires confirmation
    assert result.decision == PolicyDecision.REQUIRE_CONFIRMATION


def test_evaluate_action_policy_with_config_repo_override(db_conn):
    """Test that repo-specific config overrides are applied."""
    import tempfile
    from pathlib import Path

    from handsfree.policy_config import reload_policy_config

    user_id = str(uuid.uuid4())
    repo = "owner/test-repo"

    # Create a config with repo override
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
  owner/test-repo:
    allow_merge: true
    require_confirmation: false
    required_approvals: 0
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        # Reload config with test file
        reload_policy_config(temp_path)

        # Evaluate policy - should use repo override
        result = evaluate_action_policy(
            db_conn,
            user_id=user_id,
            repo_full_name=repo,
            action_type="merge",
            pr_checks_status="passing",
        )

        # Should allow merge without confirmation due to repo override
        assert result.decision == PolicyDecision.ALLOW
    finally:
        Path(temp_path).unlink()
        # Reset to default config
        from handsfree.policy_config import clear_policy_config_cache

        clear_policy_config_cache()


def test_evaluate_action_policy_config_override_vs_db_policy(db_conn):
    """Test that database policy takes precedence over config override."""
    import tempfile
    from pathlib import Path

    from handsfree.policy_config import reload_policy_config

    user_id = str(uuid.uuid4())
    repo = "owner/test-repo"

    # Create a config with repo override
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
  owner/test-repo:
    allow_merge: true
    require_confirmation: false
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        # Reload config with test file
        reload_policy_config(temp_path)

        # Create database policy that denies merge
        create_or_update_repo_policy(
            db_conn,
            user_id=user_id,
            repo_full_name=repo,
            allow_merge=False,  # DB policy denies merge
        )

        # Evaluate policy - should use DB policy, not config override
        result = evaluate_action_policy(
            db_conn,
            user_id=user_id,
            repo_full_name=repo,
            action_type="merge",
        )

        # Should deny merge because DB policy takes precedence
        assert result.decision == PolicyDecision.DENY
    finally:
        Path(temp_path).unlink()
        # Reset to default config
        from handsfree.policy_config import clear_policy_config_cache

        clear_policy_config_cache()
