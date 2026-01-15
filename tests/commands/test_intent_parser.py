"""Tests for intent parser."""

import pytest

from handsfree.commands.intent_parser import IntentParser


@pytest.fixture
def parser() -> IntentParser:
    """Create an intent parser instance."""
    return IntentParser()


class TestSystemIntents:
    """Test system control intents."""

    def test_repeat(self, parser: IntentParser) -> None:
        """Test system.repeat intent."""
        result = parser.parse("repeat")
        assert result.name == "system.repeat"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_next(self, parser: IntentParser) -> None:
        """Test system.next intent."""
        result = parser.parse("next")
        assert result.name == "system.next"
        assert result.confidence >= 0.9
        assert result.entities == {}

        result = parser.parse("next one")
        assert result.name == "system.next"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_confirm(self, parser: IntentParser) -> None:
        """Test system.confirm intent."""
        result = parser.parse("confirm")
        assert result.name == "system.confirm"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_cancel(self, parser: IntentParser) -> None:
        """Test system.cancel intent."""
        result = parser.parse("cancel")
        assert result.name == "system.cancel"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_set_profile(self, parser: IntentParser) -> None:
        """Test system.set_profile intent."""
        for profile in ["workout", "kitchen", "commute"]:
            result = parser.parse(f"{profile} mode")
            assert result.name == "system.set_profile"
            assert result.entities["profile"] == profile


class TestInboxIntents:
    """Test inbox-related intents."""

    def test_inbox_list_basic(self, parser: IntentParser) -> None:
        """Test inbox.list with basic phrases."""
        phrases = [
            "what needs my attention",
            "inbox",
            "pr inbox",
            "anything failing",
        ]
        for phrase in phrases:
            result = parser.parse(phrase)
            assert result.name == "inbox.list", f"Failed for: {phrase}"
            assert result.confidence >= 0.9


class TestPRIntents:
    """Test PR-related intents."""

    def test_pr_summarize_with_number(self, parser: IntentParser) -> None:
        """Test pr.summarize with explicit PR number."""
        result = parser.parse("summarize pr 412")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == 412

        result = parser.parse("summarize pull request 123")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == 123

    def test_pr_summarize_last(self, parser: IntentParser) -> None:
        """Test pr.summarize for last PR."""
        result = parser.parse("summarize the last pr")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == "last"

    def test_pr_summarize_what_changed(self, parser: IntentParser) -> None:
        """Test pr.summarize with 'what changed' phrasing."""
        result = parser.parse("what changed in pr 99")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == 99

    def test_pr_request_review_single(self, parser: IntentParser) -> None:
        """Test pr.request_review with single reviewer."""
        result = parser.parse("ask bob to review")
        assert result.name == "pr.request_review"
        assert result.entities["reviewers"] == ["bob"]

    def test_pr_request_review_multiple(self, parser: IntentParser) -> None:
        """Test pr.request_review with multiple reviewers."""
        result = parser.parse("request review from alex and priya on pr 412")
        assert result.name == "pr.request_review"
        assert "alex" in result.entities["reviewers"]
        assert "priya" in result.entities["reviewers"]
        assert result.entities["pr_number"] == 412

    def test_pr_request_review_add(self, parser: IntentParser) -> None:
        """Test pr.request_review with 'add reviewers' phrasing."""
        result = parser.parse("add reviewer charlie to pr 55")
        assert result.name == "pr.request_review"
        assert result.entities["reviewers"] == ["charlie"]
        assert result.entities["pr_number"] == 55

    def test_pr_request_review_ask_with_pr_number(self, parser: IntentParser) -> None:
        """Test pr.request_review with 'ask X to review PR N' phrasing."""
        result = parser.parse("ask bob to review PR 123")
        assert result.name == "pr.request_review"
        assert result.entities["reviewers"] == ["bob"]
        assert result.entities["pr_number"] == 123

    def test_pr_request_reviewers_for_pr(self, parser: IntentParser) -> None:
        """Test pr.request_review with 'request reviewers X Y for PR N' phrasing."""
        result = parser.parse("request reviewers alice bob for PR 789")
        assert result.name == "pr.request_review"
        assert "alice" in result.entities["reviewers"]
        assert "bob" in result.entities["reviewers"]
        assert result.entities["pr_number"] == 789

    def test_pr_request_reviewer_single_for_pr(self, parser: IntentParser) -> None:
        """Test pr.request_review with 'request reviewer X for PR N' phrasing."""
        result = parser.parse("request reviewer alice for PR 456")
        assert result.name == "pr.request_review"
        assert result.entities["reviewers"] == ["alice"]
        assert result.entities["pr_number"] == 456

    def test_pr_merge(self, parser: IntentParser) -> None:
        """Test pr.merge intent."""
        result = parser.parse("merge pr 412")
        assert result.name == "pr.merge"
        assert result.entities["pr_number"] == 412
        assert result.entities["merge_method"] == "merge"

    def test_pr_merge_squash(self, parser: IntentParser) -> None:
        """Test pr.merge with squash method."""
        result = parser.parse("squash merge pr 99")
        assert result.name == "pr.merge"
        assert result.entities["pr_number"] == 99
        assert result.entities["merge_method"] == "squash"

    def test_pr_comment_with_colon(self, parser: IntentParser) -> None:
        """Test pr.comment with colon separator."""
        result = parser.parse("comment on pr 123: looks good")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 123
        assert result.entities["comment_body"] == "looks good"

    def test_pr_comment_with_saying(self, parser: IntentParser) -> None:
        """Test pr.comment with 'saying' phrasing."""
        result = parser.parse("post comment on pr 456 saying great work")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 456
        assert result.entities["comment_body"] == "great work"

    def test_pr_comment_on_pull_request(self, parser: IntentParser) -> None:
        """Test pr.comment with 'pull request' instead of 'pr'."""
        result = parser.parse("comment on pull request 789: this is ready")
        assert result.name == "pr.comment"
        assert result.entities["pr_number"] == 789
        assert result.entities["comment_body"] == "this is ready"


class TestChecksIntents:
    """Test checks-related intents."""

    def test_checks_rerun_with_pr(self, parser: IntentParser) -> None:
        """Test checks.rerun for specific PR."""
        result = parser.parse("rerun checks for pr 123")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 123

        result = parser.parse("rerun checks on pr 456")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 456

    def test_checks_rerun_ci_with_pr(self, parser: IntentParser) -> None:
        """Test checks.rerun with 'ci' phrasing."""
        result = parser.parse("rerun ci for pr 789")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 789

        result = parser.parse("rerun ci on pr 101")
        assert result.name == "checks.rerun"
        assert result.entities["pr_number"] == 101

    def test_checks_rerun_without_pr(self, parser: IntentParser) -> None:
        """Test checks.rerun without explicit PR number."""
        result = parser.parse("rerun checks")
        assert result.name == "checks.rerun"
        assert result.entities == {}

        result = parser.parse("rerun ci")
        assert result.name == "checks.rerun"
        assert result.entities == {}

    def test_checks_status_for_pr(self, parser: IntentParser) -> None:
        """Test checks.status for specific PR."""
        result = parser.parse("checks for pr 412")
        assert result.name == "checks.status"
        assert result.entities["pr_number"] == 412

    def test_checks_status_ci(self, parser: IntentParser) -> None:
        """Test checks.status with 'ci status' phrasing."""
        result = parser.parse("ci status")
        assert result.name == "checks.status"

    def test_checks_status_repo(self, parser: IntentParser) -> None:
        """Test checks.status for specific repo."""
        result = parser.parse("what's failing on owner/repo")
        assert result.name == "checks.status"
        assert result.entities["repo"] == "owner/repo"


class TestAgentIntents:
    """Test agent-related intents."""

    def test_agent_delegate_issue(self, parser: IntentParser) -> None:
        """Test agent.delegate for issue."""
        result = parser.parse("ask the agent to fix issue 918")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "fix"
        assert result.entities["issue_number"] == 918

    def test_agent_delegate_pr(self, parser: IntentParser) -> None:
        """Test agent.delegate for PR."""
        result = parser.parse("have the agent address review comments on pr 412")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "address review comments"
        assert result.entities["pr_number"] == 412

    def test_agent_delegate_copilot(self, parser: IntentParser) -> None:
        """Test agent.delegate with copilot provider."""
        result = parser.parse("tell copilot to handle issue 100")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "handle"
        assert result.entities["issue_number"] == 100
        assert result.entities["provider"] == "copilot"

    def test_agent_progress(self, parser: IntentParser) -> None:
        """Test agent.status intent (and backwards compatibility with 'progress' phrase)."""
        phrases = [
            "agent status",
            "what's the agent doing",
            "summarize agent progress",
            "agent progress",  # backwards compatibility
        ]
        for phrase in phrases:
            result = parser.parse(phrase)
            assert result.name == "agent.status", f"Failed for: {phrase}"


class TestUnknownIntents:
    """Test handling of unknown/invalid inputs."""

    def test_unknown_input(self, parser: IntentParser) -> None:
        """Test that unrecognized input returns unknown intent."""
        result = parser.parse("hello world")
        assert result.name == "unknown"
        assert result.confidence == 0.0
        assert result.entities["text"] == "hello world"

    def test_empty_input(self, parser: IntentParser) -> None:
        """Test handling of empty input."""
        result = parser.parse("")
        assert result.name == "unknown"
        assert result.confidence == 0.0


class TestNoisyTranscripts:
    """Test parser robustness with noisy transcripts."""

    def test_with_filler_words(self, parser: IntentParser) -> None:
        """Test parsing with filler words."""
        result = parser.parse("um can you summarize pr 412 please")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == 412

    def test_with_politeness(self, parser: IntentParser) -> None:
        """Test parsing with polite phrases."""
        result = parser.parse("could you please show me the inbox")
        assert result.name == "inbox.list"

    def test_case_insensitive(self, parser: IntentParser) -> None:
        """Test that parsing is case-insensitive."""
        result = parser.parse("INBOX")
        assert result.name == "inbox.list"

        result = parser.parse("Summarize PR 123")
        assert result.name == "pr.summarize"
        assert result.entities["pr_number"] == 123
