"""Tests for shared GitHub action execution helpers."""

from handsfree.github.execution import (
    execute_comment_action,
    execute_merge_action,
    execute_request_review_action,
    execute_rerun_action,
)


class _StubAuthProvider:
    def __init__(self, token: str | None):
        self._token = token

    def supports_live_mode(self) -> bool:
        return self._token is not None

    def get_token(self, user_id: str) -> str | None:
        return self._token


def test_execute_request_review_uses_cli_fixture(monkeypatch):
    """Request-review helper should use CLI fixtures when enabled."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

    result = execute_request_review_action("test/repo", 100, ["alice"], "user-1")

    assert result["ok"] is True
    assert result["mode"] == "fixture"
    assert "review requested" in result["message"].lower()


def test_execute_merge_uses_cli_fixture(monkeypatch):
    """Merge helper should use CLI fixtures when enabled."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

    result = execute_merge_action("test/repo", 200, "squash", "user-1")

    assert result["ok"] is True
    assert result["mode"] == "fixture"
    assert "merged successfully" in result["message"].lower()


def test_execute_request_review_uses_api_when_token_available(monkeypatch):
    """Request-review helper should use the API path when live auth is available."""
    monkeypatch.delenv("HANDSFREE_CLI_FIXTURE_MODE", raising=False)
    monkeypatch.delenv("HANDSFREE_GH_CLI_ENABLED", raising=False)
    monkeypatch.setattr(
        "handsfree.github.execution.get_default_auth_provider",
        lambda: _StubAuthProvider("token-123"),
    )
    monkeypatch.setattr(
        "handsfree.github.execution.request_reviewers",
        lambda **kwargs: {"ok": True, "message": "api review requested", "response_data": {}},
    )

    result = execute_request_review_action("test/repo", 42, ["alice"], "user-1")

    assert result["ok"] is True
    assert result["mode"] == "api_live"
    assert result["message"] == "api review requested"


def test_execute_rerun_uses_fixture_without_token(monkeypatch):
    """Rerun helper should fall back to fixture mode without a token."""
    monkeypatch.setattr(
        "handsfree.github.execution.get_default_auth_provider",
        lambda: _StubAuthProvider(None),
    )

    result = execute_rerun_action("test/repo", 77, "user-1")

    assert result["ok"] is True
    assert result["mode"] == "fixture"
    assert "workflow checks re-run" in result["message"].lower()


def test_execute_comment_uses_cli_fixture(monkeypatch):
    """Comment helper should use CLI fixtures when enabled."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

    result = execute_comment_action("test/repo", 123, "looks good", "user-1")

    assert result["ok"] is True
    assert result["mode"] == "fixture"
    assert "comment posted" in result["message"].lower()
