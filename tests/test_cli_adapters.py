"""Tests for fixture-backed CLI adapters."""

from handsfree.cli import CLIExecutor, CopilotCLIAdapter, GitHubCLIAdapter
from handsfree.commands.profiles import Profile, ProfileConfig


def test_executor_uses_fixture_mode(monkeypatch):
    """CLI executor should replay fixtures when fixture mode is enabled."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    result = CLIExecutor().execute("gh.pr.view", "gh", pr_number=123)

    assert result.ok is True
    assert result.source == "fixture"
    assert "\"number\":123" in result.stdout


def test_github_cli_adapter_summarizes_pr(monkeypatch):
    """GitHub CLI adapter should produce a spoken summary from fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    profile_config = ProfileConfig.for_profile(Profile.DEFAULT)

    result = GitHubCLIAdapter().summarize_pr(123, profile_config)

    assert "Add command system" in result["spoken_text"]
    assert result["trace"]["provider"] == "github_cli"


def test_copilot_cli_adapter_explains_pr(monkeypatch):
    """Copilot CLI adapter should produce a spoken explanation from fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    profile_config = ProfileConfig.for_profile(Profile.DEFAULT)

    result = CopilotCLIAdapter().explain_pr(123, profile_config)

    assert "profile-aware routing" in result["spoken_text"].lower()
    assert result["trace"]["provider"] == "copilot_cli"


def test_copilot_cli_adapter_summarizes_diff(monkeypatch):
    """Copilot CLI adapter should summarize diffs from fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    profile_config = ProfileConfig.for_profile(Profile.DEFAULT)

    result = CopilotCLIAdapter().summarize_diff(123, profile_config)

    assert "shared action handling" in result["spoken_text"].lower()
    assert result["trace"]["provider"] == "copilot_cli"


def test_copilot_cli_adapter_explains_failure(monkeypatch):
    """Copilot CLI adapter should explain failures from fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    profile_config = ProfileConfig.for_profile(Profile.DEFAULT)

    result = CopilotCLIAdapter().explain_failure(123, profile_config)

    assert "missing fixture" in result["spoken_text"].lower()
    assert result["trace"]["provider"] == "copilot_cli"


def test_copilot_cli_adapter_explains_named_failure(monkeypatch):
    """Copilot CLI adapter should explain a specific failing workflow from fixtures."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    profile_config = ProfileConfig.for_profile(Profile.DEFAULT)

    result = CopilotCLIAdapter().explain_failure(
        123,
        profile_config,
        failure_target="CI Linux",
        failure_target_type="workflow",
    )

    assert "failing in setup" in result["spoken_text"].lower()
    assert result["trace"]["provider"] == "copilot_cli"


def test_github_cli_adapter_requests_reviewers(monkeypatch):
    """GitHub CLI adapter should request reviewers via fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    result = GitHubCLIAdapter().request_review("test/repo", 100, ["alice"])

    assert result["ok"] is True
    assert "review requested" in result["message"].lower()
    assert result["trace"]["provider"] == "github_cli"


def test_github_cli_adapter_merges_pr(monkeypatch):
    """GitHub CLI adapter should merge via fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    result = GitHubCLIAdapter().merge_pr("test/repo", 200, "squash")

    assert result["ok"] is True
    assert "merged successfully" in result["message"].lower()
    assert result["trace"]["provider"] == "github_cli"


def test_github_cli_adapter_comments_on_pr(monkeypatch):
    """GitHub CLI adapter should comment via fixture output."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    result = GitHubCLIAdapter().comment_on_pr("test/repo", 123, "looks good")

    assert result["ok"] is True
    assert "comment posted" in result["message"].lower()
    assert result["trace"]["provider"] == "github_cli"
