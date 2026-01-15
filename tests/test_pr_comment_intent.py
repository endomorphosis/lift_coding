"""Integration tests for pr.comment intent command flow."""

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


class TestPRCommentIntentParsing:
    """Test intent parsing for pr.comment commands."""

    def test_parse_comment_on_pr_with_colon(self, parser: IntentParser) -> None:
        """Test parsing 'comment on PR 123: looks good'."""
        result = parser.parse("comment on PR 123: looks good")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 123
        assert result.entities["comment_body"] == "looks good"

    def test_parse_comment_on_pull_request(self, parser: IntentParser) -> None:
        """Test parsing 'comment on pull request 456: great work'."""
        result = parser.parse("comment on pull request 456: great work")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 456
        assert result.entities["comment_body"] == "great work"

    def test_parse_post_comment_saying(self, parser: IntentParser) -> None:
        """Test parsing 'post comment on PR 789 saying this is ready'."""
        result = parser.parse("post comment on PR 789 saying this is ready")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 789
        assert result.entities["comment_body"] == "this is ready"

    def test_parse_long_comment(self, parser: IntentParser) -> None:
        """Test parsing comment with longer text."""
        result = parser.parse(
            "comment on PR 100: I reviewed the changes and they look great. LGTM!"
        )
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 100
        assert "reviewed the changes" in result.entities["comment_body"]


class TestPRCommentConfirmationFlow:
    """Test confirmation flow for pr.comment intent."""

    def test_requires_confirmation_in_workout_profile(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that pr.comment requires confirmation in workout profile."""
        intent = parser.parse("comment on PR 123: looks good")

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

    def test_no_confirmation_with_policy_allow(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.comment with policy allowing direct execution."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment without confirmation
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        intent = parser.parse("comment on PR 123: looks good")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        # Should execute directly in fixture mode
        assert response["status"] == "ok"
        assert "pending_action" not in response
        assert "comment posted" in response["spoken_text"].lower()


class TestPRCommentPolicyIntegration:
    """Test policy integration for pr.comment intent."""

    def test_policy_denies_comment(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that policy can deny pr.comment."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that denies comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=False,
        )

        intent = parser.parse("comment on PR 123: looks good")

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
            allow_comment=True,
            require_confirmation=True,
        )

        intent = parser.parse("comment on PR 123: looks good")

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
        """Test that pr.comment requires PR number for execution."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        # Create an intent manually without PR number (since parser won't match)
        from handsfree.commands.intent_parser import ParsedIntent

        intent = ParsedIntent(
            name="pr.comment",
            confidence=1.0,
            entities={"comment_body": "looks good"},
        )

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        # Should error because no PR number provided
        assert response["status"] == "error"
        assert "pr number" in response["spoken_text"].lower()

    def test_requires_comment_body(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that pr.comment requires comment body."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        # Create an intent manually without comment body
        from handsfree.commands.intent_parser import ParsedIntent

        intent = ParsedIntent(
            name="pr.comment",
            confidence=1.0,
            entities={"pr_number": 123},
        )

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
        )

        # Should error because no comment body provided
        assert response["status"] == "error"
        assert "comment text" in response["spoken_text"].lower()


class TestPRCommentAuditLogging:
    """Test audit logging for pr.comment intent."""

    def test_audit_log_successful_execution(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that successful execution creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        intent = parser.parse("comment on PR 123: looks good")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-1",
        )

        assert response["status"] == "ok"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="comment", limit=10)
        assert len(logs) > 0
        assert logs[0].ok is True
        assert logs[0].target == "default/repo#123"
        assert logs[0].result.get("message") == "Comment posted (fixture)"
        assert logs[0].request.get("comment_body") == "looks good"

    def test_audit_log_policy_denial(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that policy denial creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that denies comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=False,
        )

        intent = parser.parse("comment on PR 123: looks good")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-2",
        )

        assert response["status"] == "error"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="comment", limit=10)
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
            allow_comment=True,
            require_confirmation=True,
        )

        intent = parser.parse("comment on PR 123: looks good")

        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-3",
        )

        assert response["status"] == "needs_confirmation"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="comment", limit=10)
        assert len(logs) > 0
        confirm_log = next(
            (log for log in logs if log.result.get("status") == "needs_confirmation"), None
        )
        assert confirm_log is not None
        assert confirm_log.ok is True
        assert "token" in confirm_log.result


class TestPRCommentRateLimiting:
    """Test rate limiting for pr.comment intent."""

    def test_rate_limit_enforced(self, db_router: CommandRouter, parser: IntentParser) -> None:
        """Test that rate limiting is enforced for pr.comment."""
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        # Make 3 requests (burst_max is 3 for comment, will hit burst limit after this)
        for i in range(3):
            intent = parser.parse(f"comment on PR {100 + i}: test comment {i}")
            response = db_router.route(
                intent,
                Profile.COMMUTE,
                session_id="test-session",
                user_id=TEST_USER_ID,
                idempotency_key=f"test-key-rate-{i}",
            )
            assert response["status"] == "ok"

        # 4th request should be rate limited (burst limit exceeded)
        intent = parser.parse("comment on PR 200: should be rate limited")
        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-rate-4",
        )

        assert response["status"] == "error"
        assert "rate limit" in response["spoken_text"].lower()

    def test_rate_limit_creates_audit_log(
        self, db_router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that rate limiting creates audit log entry."""
        from handsfree.db.action_logs import get_action_logs
        from handsfree.db.repo_policies import create_or_update_repo_policy

        # Set up policy that allows comment
        create_or_update_repo_policy(
            db_router.db_conn,
            user_id=TEST_USER_ID,
            repo_full_name="default/repo",
            allow_comment=True,
            require_confirmation=False,
        )

        # Hit rate limit
        for i in range(10):
            intent = parser.parse(f"comment on PR {100 + i}: test comment {i}")
            db_router.route(
                intent,
                Profile.COMMUTE,
                session_id="test-session",
                user_id=TEST_USER_ID,
                idempotency_key=f"test-key-rate-limit-{i}",
            )

        # This one should be rate limited
        intent = parser.parse("comment on PR 200: should be rate limited")
        response = db_router.route(
            intent,
            Profile.COMMUTE,
            session_id="test-session",
            user_id=TEST_USER_ID,
            idempotency_key="test-key-rate-limit-final",
        )

        assert response["status"] == "error"

        # Check audit log
        logs = get_action_logs(db_router.db_conn, action_type="comment", limit=20)
        rate_limited_log = next(
            (log for log in logs if log.result.get("error") == "rate_limited"), None
        )
        assert rate_limited_log is not None
        assert rate_limited_log.ok is False
