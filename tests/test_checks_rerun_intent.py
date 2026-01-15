"""Integration tests for checks.rerun intent command flow."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter

# Use a fixed UUID for testing
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


@pytest.fixture
def parser() -> IntentParser:
    """Create an intent parser instance."""
    return IntentParser()


@pytest.fixture
def pending_manager() -> PendingActionManager:
    """Create a pending actions manager."""
    return PendingActionManager()


@pytest.fixture
def db_router(pending_manager: PendingActionManager):
    """Create a command router with database connection."""
    from handsfree.db import init_db

    db_conn = init_db(":memory:")
    router = CommandRouter(pending_manager, db_conn=db_conn)
    yield router
    db_conn.close()


client = TestClient(app)


class TestChecksRerunIntentParsing:
    """Test intent parsing for checks.rerun commands."""

    def test_parse_rerun_checks_with_pr(self, parser: IntentParser) -> None:
        """Test parsing 'rerun checks for pr 123'."""
        result = parser.parse("rerun checks for pr 123")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 123

    def test_parse_rerun_ci_with_pr(self, parser: IntentParser) -> None:
        """Test parsing 'rerun ci for pr 456'."""
        result = parser.parse("rerun ci for pr 456")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 456

    def test_parse_rerun_without_pr(self, parser: IntentParser) -> None:
        """Test parsing 'rerun checks' without PR number."""
        result = parser.parse("rerun checks")
        assert result.name == "checks.rerun"
        assert result.entities == {}


class TestChecksRerunConfirmationFlow:
    """Test confirmation flow for checks.rerun intent."""

    def test_requires_confirmation_in_workout_profile(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that checks.rerun requires confirmation in workout profile."""
        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.WORKOUT,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response
        assert "token" in response["pending_action"]
        assert "confirm" in response["spoken_text"].lower()

    def test_no_confirmation_in_commute_profile_with_policy(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test checks.rerun with policy allowing direct execution."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows rerun without confirmation
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=False,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        # Should execute directly in fixture mode
        assert response["status"] == "ok"
        assert "pending_action" not in response
        assert "checks re-run" in response["spoken_text"].lower()


class TestChecksRerunPolicyIntegration:
    """Test policy integration for checks.rerun intent."""

    def test_policy_denies_rerun(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that policy can deny checks.rerun."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that denies rerun
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=False,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        assert response["status"] == "error"
        assert "not allowed" in response["spoken_text"].lower()

    def test_policy_requires_confirmation(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that policy can require confirmation."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that requires confirmation
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=True,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response
        assert "token" in response["pending_action"]

    def test_requires_pr_number(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that checks.rerun requires PR number for execution."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows rerun
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=False,
        )

        intent = parser.parse("rerun checks")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        # Should error because no PR number provided
        assert response["status"] == "error"
        assert "pr number" in response["spoken_text"].lower()


class TestChecksRerunAuditLogging:
    """Test audit logging for checks.rerun intent."""

    def test_audit_log_successful_execution(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that successful execution creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows rerun
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=False,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-1",
        )

        assert response["status"] == "ok"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="rerun", limit=10)
        assert len(logs) > 0
        assert logs[0].ok is True
        assert logs[0].target == "default/repo#123"
        assert logs[0].result.get("message") == "Checks re-run (fixture)"

    def test_audit_log_policy_denial(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that policy denial creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that denies rerun
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=False,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-2",
        )

        assert response["status"] == "error"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="rerun", limit=10)
        assert len(logs) > 0
        denied_log = next((log for log in logs if not log.ok), None)
        assert denied_log is not None
        assert denied_log.result.get("error") == "policy_denied"

    def test_audit_log_confirmation_required(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that confirmation required creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that requires confirmation
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=True,
        )

        intent = parser.parse("rerun checks for pr 123")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-3",
        )

        assert response["status"] == "needs_confirmation"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="rerun", limit=10)
        assert len(logs) > 0
        confirm_log = next(
            (log for log in logs if log.result.get("status") == "needs_confirmation"), None
        )
        assert confirm_log is not None
        assert confirm_log.ok is True
        assert "token" in confirm_log.result


class TestChecksRerunRateLimiting:
    """Test rate limiting for checks.rerun intent."""

    def test_rate_limit_enforced(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that rate limiting is enforced for checks.rerun."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows rerun
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_rerun=True,
            require_confirmation=False,
        )

        # Make 2 requests (burst_max is 2 for rerun, will hit burst limit after this)
        for i in range(2):
            intent = parser.parse(f"rerun checks for pr {100 + i}")
            response = db_router.route(
                intent,
                Profile.COMMUTE,
                session_id="test-session",
                user_id=TEST_USER_ID,
                idempotency_key=f"test-key-rate-{i}",
            )
            assert response["status"] == "ok"

        # 3rd request should be rate limited (burst limit exceeded)
        intent = parser.parse("rerun checks for pr 200")
        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-rate-6",
        )

        assert response["status"] == "error"
        assert "rate limit" in response["spoken_text"].lower()
