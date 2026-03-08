"""Router-level tests for CLI-backed PR comment execution."""

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.repo_policies import create_or_update_repo_policy

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def parser() -> IntentParser:
    return IntentParser()


@pytest.fixture
def db_router() -> CommandRouter:
    conn = init_db(":memory:")
    router = CommandRouter(PendingActionManager(), db_conn=conn)
    yield router
    conn.close()


def test_comment_direct_execution_uses_cli_fixture(
    db_router: CommandRouter, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Policy-allowed comments should execute through CLI fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

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
        session_id="comment-session",
        user_id=TEST_USER_ID,
    )

    assert response["status"] == "ok"
    assert "comment posted" in response["spoken_text"].lower()
