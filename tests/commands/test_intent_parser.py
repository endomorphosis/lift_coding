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

    def test_result_followup_actions(self, parser: IntentParser) -> None:
        """Test result-navigation follow-up intents."""
        assert parser.parse("open that result").name == "agent.result_open"
        assert parser.parse("what can i do with that result").name == "agent.result_actions"
        assert parser.parse("show task details for that result").name == "agent.result_details"
        assert parser.parse("show another result like this").name == "agent.result_related"
        fetch_rerun = parser.parse("rerun that fetch with https://example.org")
        assert fetch_rerun.name == "agent.result_rerun_fetch"
        assert fetch_rerun.entities["mcp_seed_url"] == "https://example.org"
        dataset_rerun = parser.parse("rerun that dataset search with labor law datasets")
        assert dataset_rerun.name == "agent.result_rerun_dataset"
        assert dataset_rerun.entities["mcp_input"] == "labor law datasets"
        assert parser.parse("save that result to ipfs").name == "agent.result_save_ipfs"
        assert parser.parse("read the cid").name == "agent.result_read"
        assert parser.parse("share that cid").name == "agent.result_share"
        assert parser.parse("unpin that").name == "agent.result_unpin"
        assert parser.parse("pin that").name == "agent.result_pin"
        assert parser.parse("rerun that workflow").name == "agent.result_rerun"


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

    def test_ai_explain_pr(self, parser: IntentParser) -> None:
        """Test ai.explain_pr intent."""
        result = parser.parse("explain pr 123")
        assert result.name == "ai.explain_pr"
        assert result.entities["pr_number"] == 123

        result = parser.parse("explain pr 123 on owner/repo")
        assert result.name == "ai.explain_pr"
        assert result.entities["pr_number"] == 123
        assert result.entities["repo"] == "owner/repo"

        result = parser.parse("use copilot to explain pull request 456")
        assert result.name == "ai.explain_pr"
        assert result.entities["pr_number"] == 456
        assert result.entities["provider"] == "copilot_cli"

    def test_ai_summarize_diff(self, parser: IntentParser) -> None:
        """Test ai.summarize_diff intent."""
        result = parser.parse("summarize diff for pr 123")
        assert result.name == "ai.summarize_diff"
        assert result.entities["pr_number"] == 123

        result = parser.parse("summarize diff")
        assert result.name == "ai.summarize_diff"
        assert result.entities == {}

        result = parser.parse("use copilot to summarize diff for pull request 456")
        assert result.name == "ai.summarize_diff"
        assert result.entities["pr_number"] == 456
        assert result.entities["provider"] == "copilot_cli"

        result = parser.parse("summarize diff for pr 123 on owner/repo")
        assert result.name == "ai.summarize_diff"
        assert result.entities["pr_number"] == 123
        assert result.entities["repo"] == "owner/repo"

    def test_ai_rag_summary(self, parser: IntentParser) -> None:
        """Test ai.rag_summary intent."""
        result = parser.parse("rag summary for pr 123")
        assert result.name == "ai.rag_summary"
        assert result.entities["pr_number"] == 123

        result = parser.parse("augmented summary for pull request 456 on owner/repo")
        assert result.name == "ai.rag_summary"
        assert result.entities["pr_number"] == 456
        assert result.entities["repo"] == "owner/repo"

        result = parser.parse("augmented summary")
        assert result.name == "ai.rag_summary"
        assert result.entities == {}

        result = parser.parse("store augmented summary for pull request 456 on owner/repo to ipfs")
        assert result.name == "ai.rag_summary"
        assert result.entities["pr_number"] == 456
        assert result.entities["repo"] == "owner/repo"
        assert result.entities["persist_output"] is True

        result = parser.parse("use acceleration for augmented summary for pr 123")
        assert result.name == "ai.rag_summary"
        assert result.entities["pr_number"] == 123
        assert result.entities["summary_backend"] == "accelerated"

        result = parser.parse("use acceleration for augmented summary for pr 124 to ipfs")
        assert result.name == "ai.rag_summary"
        assert result.entities["pr_number"] == 124
        assert result.entities["summary_backend"] == "accelerated"
        assert result.entities["persist_output"] is True

    def test_ai_accelerated_rag_summary(self, parser: IntentParser) -> None:
        """Test ai.accelerated_rag_summary intent."""
        result = parser.parse("accelerated rag summary for pr 123")
        assert result.name == "ai.accelerated_rag_summary"
        assert result.entities["pr_number"] == 123

        result = parser.parse("accelerated augmented summary for pull request 456 on owner/repo")
        assert result.name == "ai.accelerated_rag_summary"
        assert result.entities["pr_number"] == 456
        assert result.entities["repo"] == "owner/repo"

        result = parser.parse("accelerated augmented summary")
        assert result.name == "ai.accelerated_rag_summary"
        assert result.entities == {}

    def test_ai_read_cid(self, parser: IntentParser) -> None:
        """Test ai.read_cid intent."""
        result = parser.parse("read summary from cid bafy123")
        assert result.name == "ai.read_cid"
        assert result.entities["cid"] == "bafy123"

        result = parser.parse("show result from ipfs bafy456")
        assert result.name == "ai.read_cid"
        assert result.entities["cid"] == "bafy456"

    def test_ai_accelerate_generate_and_store(self, parser: IntentParser) -> None:
        """Test ai.accelerate_generate_and_store intent."""
        result = parser.parse("accelerate and store summarize the failure cluster")
        assert result.name == "ai.accelerate_generate_and_store"
        assert result.entities["prompt"] == "summarize the failure cluster"

        result = parser.parse(
            "generate and store with acceleration summarize the failure cluster to ipfs"
        )
        assert result.name == "ai.accelerate_generate_and_store"
        assert result.entities["prompt"] == "summarize the failure cluster"
        assert result.entities["kit_pin"] is True

    def test_ai_explain_failure(self, parser: IntentParser) -> None:
        """Test ai.explain_failure intent."""
        result = parser.parse("explain failing checks for pr 123")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 123

        result = parser.parse("explain failing checks")
        assert result.name == "ai.explain_failure"
        assert result.entities == {}

        result = parser.parse("use copilot to explain failure for pull request 456")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 456
        assert result.entities["provider"] == "copilot_cli"

        result = parser.parse("explain workflow CI Linux for pr 789")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 789
        assert result.entities["workflow_name"] == "CI Linux"
        assert "failure_target" not in result.entities
        assert "failure_target_type" not in result.entities

        result = parser.parse("explain check unit tests for pr 790")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 790
        assert result.entities["check_name"] == "unit tests"
        assert "failure_target" not in result.entities
        assert "failure_target_type" not in result.entities

        result = parser.parse("explain workflow CI Linux for pr 789 on owner/repo")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 789
        assert result.entities["repo"] == "owner/repo"

        result = parser.parse("persist explain failure for pull request 123 to ipfs")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 123
        assert result.entities["persist_output"] is True

        result = parser.parse("use acceleration for explain failure for pr 321")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 321
        assert result.entities["failure_backend"] == "accelerated"

        result = parser.parse("use acceleration for explain workflow CI Linux for pr 322")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 322
        assert result.entities["workflow_name"] == "CI Linux"
        assert result.entities["failure_backend"] == "accelerated"

        result = parser.parse("use acceleration for explain failure for pr 323 to ipfs")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 323
        assert result.entities["failure_backend"] == "accelerated"
        assert result.entities["persist_output"] is True

    def test_ai_accelerated_explain_failure(self, parser: IntentParser) -> None:
        """Test ai.accelerated_explain_failure intent."""
        result = parser.parse("accelerated failure analysis for pr 123")
        assert result.name == "ai.accelerated_explain_failure"
        assert result.entities["pr_number"] == 123

        result = parser.parse("accelerated explain workflow CI Linux for pr 123")
        assert result.name == "ai.accelerated_explain_failure"
        assert result.entities["pr_number"] == 123
        assert result.entities["workflow_name"] == "CI Linux"

    def test_ai_find_similar_failures(self, parser: IntentParser) -> None:
        """Test ai.find_similar_failures intent."""
        result = parser.parse("find similar failures for pr 125")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["pr_number"] == 125

        result = parser.parse("find similar failures for pull request 125 on owner/repo")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["pr_number"] == 125
        assert result.entities["repo"] == "owner/repo"

        result = parser.parse("find similar workflow CI Linux failures for pr 125")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["workflow_name"] == "CI Linux"

        result = parser.parse("find similar check unit tests failures for pr 125")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["check_name"] == "unit tests"

        result = parser.parse("find similar failures")
        assert result.name == "ai.find_similar_failures"
        assert result.entities == {}

    def test_ai_find_similar_failures_with_history_cids(self, parser: IntentParser) -> None:
        """Test similar-failure retrieval with explicit history CIDs."""
        result = parser.parse("find similar failures for pr 125 using cids bafy123 and bafy456")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["pr_number"] == 125
        assert result.entities["history_cids"] == ["bafy123", "bafy456"]

        result = parser.parse("find similar workflow CI Linux failures for pr 125 using cid bafy789")
        assert result.name == "ai.find_similar_failures"
        assert result.entities["workflow_name"] == "CI Linux"
        assert result.entities["history_cids"] == ["bafy789"]

    def test_ai_explain_failure_with_history_cids(self, parser: IntentParser) -> None:
        """Test failure analysis with explicit history CIDs."""
        result = parser.parse("explain failure for pr 123 using cid bafy123")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 123
        assert result.entities["history_cids"] == ["bafy123"]

        result = parser.parse("explain workflow CI Linux for pr 123 on owner/repo using cids bafy1, bafy2")
        assert result.name == "ai.explain_failure"
        assert result.entities["pr_number"] == 123
        assert result.entities["repo"] == "owner/repo"
        assert result.entities["workflow_name"] == "CI Linux"
        assert result.entities["history_cids"] == ["bafy1", "bafy2"]

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

    def test_agent_delegate_ipfs_datasets_provider(self, parser: IntentParser) -> None:
        """Test agent.delegate with ipfs_datasets_mcp provider."""
        result = parser.parse("ask the ipfs datasets agent to find legal datasets")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "find legal datasets"
        assert result.entities["provider"] == "ipfs_datasets_mcp"

    def test_direct_dataset_discovery_maps_to_ipfs_datasets(self, parser: IntentParser) -> None:
        """Test direct dataset discovery phrase maps to datasets MCP provider."""
        result = parser.parse("find legal datasets")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "find legal datasets"
        assert result.entities["provider"] == "ipfs_datasets_mcp"
        assert result.entities["mcp_capability"] == "dataset_discovery"
        assert result.entities["mcp_input"] == "legal datasets"

    def test_agent_delegate_ipfs_kit_provider_with_pr(self, parser: IntentParser) -> None:
        """Test provider-specific agent.delegate with PR target."""
        result = parser.parse("ask the ipfs kit agent to pin this CID on pr 412")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "pin this CID"
        assert result.entities["provider"] == "ipfs_kit_mcp"
        assert result.entities["pr_number"] == 412

    def test_direct_ipfs_add_maps_to_ipfs_kit(self, parser: IntentParser) -> None:
        """Test direct IPFS add phrase maps to kit MCP provider."""
        result = parser.parse("add this file to ipfs")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "add this file to ipfs"
        assert result.entities["provider"] == "ipfs_kit_mcp"
        assert result.entities["mcp_capability"] == "ipfs_add"
        assert result.entities["mcp_input"] == "this file"

    def test_direct_ipfs_cat_maps_to_ipfs_kit(self, parser: IntentParser) -> None:
        """Test direct IPFS fetch phrase maps to kit MCP provider and CID payload."""
        result = parser.parse("get bafytestcid from ipfs")
        assert result.name == "agent.delegate"
        assert result.entities["provider"] == "ipfs_kit_mcp"
        assert result.entities["mcp_capability"] == "ipfs_cat"
        assert result.entities["mcp_cid"] == "bafytestcid"

    def test_result_save_ipfs_local_phrase_sets_direct_import_mode(self, parser: IntentParser) -> None:
        result = parser.parse("save that result to ipfs locally")

        assert result.name == "agent.result_save_ipfs"
        assert result.entities["mcp_preferred_execution_mode"] == "direct_import"

    def test_direct_ipfs_pin_maps_to_ipfs_kit(self, parser: IntentParser) -> None:
        """Test direct IPFS pin phrase maps to kit MCP pin capability."""
        result = parser.parse("pin bafytestcid on ipfs")
        assert result.name == "agent.delegate"
        assert result.entities["provider"] == "ipfs_kit_mcp"
        assert result.entities["mcp_capability"] == "ipfs_pin"
        assert result.entities["mcp_cid"] == "bafytestcid"
        assert result.entities["mcp_pin_action"] == "pin"

    def test_direct_workflow_maps_to_ipfs_accelerate(self, parser: IntentParser) -> None:
        """Test direct workflow phrase maps to accelerate MCP provider."""
        result = parser.parse("run a workflow")
        assert result.name == "agent.delegate"
        assert result.entities["instruction"] == "run a workflow"
        assert result.entities["provider"] == "ipfs_accelerate_mcp"

    def test_direct_agentic_fetch_maps_to_ipfs_accelerate(self, parser: IntentParser) -> None:
        """Test direct discover-and-fetch phrase maps to accelerate MCP provider."""
        result = parser.parse("discover and fetch climate regulations from https://example.com")
        assert result.name == "agent.delegate"
        assert result.entities["provider"] == "ipfs_accelerate_mcp"
        assert result.entities["mcp_capability"] == "agentic_fetch"
        assert result.entities["mcp_input"] == "climate regulations"
        assert result.entities["mcp_seed_url"] == "https://example.com"

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

    def test_agent_results_views(self, parser: IntentParser) -> None:
        """Test agent.results saved-view phrases."""
        cases = {
            "agent results": "overview",
            "show latest dataset discoveries": "datasets",
            "show recent ipfs results": "ipfs",
            "summarize latest fetches": "fetches",
        }
        for phrase, expected_view in cases.items():
            result = parser.parse(phrase)
            assert result.name == "agent.results", f"Failed for: {phrase}"
            assert result.entities["view"] == expected_view

    def test_result_navigation_phrases(self, parser: IntentParser) -> None:
        """Result follow-up phrases should reuse system.next."""
        phrases = [
            "next result",
            "show more results",
            "show more dataset discoveries",
            "read more ipfs results",
        ]
        for phrase in phrases:
            result = parser.parse(phrase)
            assert result.name == "system.next", f"Failed for: {phrase}"

    def test_result_open_and_read_followups(self, parser: IntentParser) -> None:
        """Result follow-up action phrases should resolve explicitly."""
        assert parser.parse("open that result").name == "agent.result_open"
        assert parser.parse("read the cid").name == "agent.result_read"
        assert parser.parse("pin that").name == "agent.result_pin"

    def test_agent_pause_without_task_id(self, parser: IntentParser) -> None:
        """Test agent.pause intent without task ID."""
        result = parser.parse("pause agent")
        assert result.name == "agent.pause"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_agent_pause_with_task_id(self, parser: IntentParser) -> None:
        """Test agent.pause intent with task ID."""
        result = parser.parse("pause task 12345678-1234-1234-1234-123456789abc")
        assert result.name == "agent.pause"
        assert result.confidence >= 0.9
        assert result.entities["task_id"] == "12345678-1234-1234-1234-123456789abc"

        # Test with short task ID
        result = parser.parse("pause task abc123")
        assert result.name == "agent.pause"
        assert result.entities["task_id"] == "abc123"

    def test_agent_resume_without_task_id(self, parser: IntentParser) -> None:
        """Test agent.resume intent without task ID."""
        result = parser.parse("resume agent")
        assert result.name == "agent.resume"
        assert result.confidence >= 0.9
        assert result.entities == {}

    def test_agent_resume_with_task_id(self, parser: IntentParser) -> None:
        """Test agent.resume intent with task ID."""
        result = parser.parse("resume task 87654321-4321-4321-4321-210987654321")
        assert result.name == "agent.resume"
        assert result.confidence >= 0.9
        assert result.entities["task_id"] == "87654321-4321-4321-4321-210987654321"

        # Test with short task ID
        result = parser.parse("resume task def456")
        assert result.name == "agent.resume"
        assert result.entities["task_id"] == "def456"


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
