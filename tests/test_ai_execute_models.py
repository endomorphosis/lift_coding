"""Tests for typed AI execute API models."""

from handsfree.models import (
    AIAccelerateGenerateAndStoreExecuteRequest,
    AIAcceleratedPRSummaryExecuteRequest,
    AIAcceleratedFailureExplainExecuteRequest,
    AICapabilityContext,
    AICapabilityExecuteRequest,
    AICopilotExplainFailureExecuteRequest,
    AICopilotExplainPRExecuteRequest,
    AICopilotSummarizeDiffExecuteRequest,
    AIFailureRAGExplainExecuteRequest,
    AIFailureAnalysisBackend,
    AIFindSimilarFailuresExecuteRequest,
    AIEmbeddingOptions,
    AIGenerationOptions,
    AIIPFSOptions,
    AIPRRAGSummaryExecuteRequest,
    AISummaryBackend,
    AIStoredOutputReadExecuteRequest,
    AIWorkflow,
    Profile,
)


def test_ai_execute_request_builds_typed_options_dict():
    """Typed API option fields should normalize to backend kwargs."""
    request = AICapabilityExecuteRequest(
        capability_id="github.pr.rag_summary",
        profile=Profile.DEFAULT,
        context=AICapabilityContext(repo="openai/example", pr_number=123),
        persist_output=True,
        generation=AIGenerationOptions(model="llama3", temperature=0.2, max_tokens=128),
        embeddings=AIEmbeddingOptions(model="minilm", dimensions=384),
        ipfs=AIIPFSOptions(pin=True),
    )

    options = request.build_options_dict()

    assert options["persist_output"] is True
    assert options["generation_options"] == {
        "model": "llama3",
        "temperature": 0.2,
        "max_tokens": 128,
    }
    assert options["embedding_options"] == {
        "model": "minilm",
        "dimensions": 384,
    }
    assert options["ipfs_options"] == {"pin": True}


def test_ai_execute_request_typed_options_override_legacy_options():
    """Typed fields should win over conflicting legacy generic options."""
    request = AICapabilityExecuteRequest(
        capability_id="github.check.failure_rag_explain",
        options={
            "persist_output": False,
            "generation_options": {"model": "legacy"},
            "ipfs_options": {"pin": False},
        },
        persist_output=True,
        generation=AIGenerationOptions(model="llama3"),
        ipfs=AIIPFSOptions(pin=True),
    )

    options = request.build_options_dict()

    assert options["persist_output"] is True
    assert options["generation_options"] == {"model": "llama3"}
    assert options["ipfs_options"] == {"pin": True}


def test_typed_option_models_preserve_extra_kwargs():
    """Typed option models should allow backend-specific passthrough values."""
    request = AICapabilityExecuteRequest(
        capability_id="ipfs.llm.generate",
        generation=AIGenerationOptions(extra={"top_p": 0.9}),
        embeddings=AIEmbeddingOptions(extra={"truncate": True}),
        ipfs=AIIPFSOptions(extra={"provider": "local"}),
    )

    options = request.build_options_dict()

    assert options["generation_options"] == {"top_p": 0.9}
    assert options["embedding_options"] == {"truncate": True}
    assert options["ipfs_options"] == {"provider": "local"}


def test_ai_execute_request_resolves_capability_id_from_workflow():
    """Workflow aliases should resolve to concrete capability IDs."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.PR_RAG_SUMMARY,
        profile=Profile.DEFAULT,
    )

    assert request.resolve_capability_id() == "github.pr.rag_summary"


def test_ai_execute_request_resolves_accelerated_pr_summary_workflow():
    """Accelerated PR summary workflow should resolve to the correct capability."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.ACCELERATED_PR_SUMMARY,
        profile=Profile.DEFAULT,
        context=AICapabilityContext(pr_number=123),
    )

    assert request.resolve_capability_id() == "github.pr.accelerated_summary"


def test_ai_execute_request_prefers_explicit_capability_id_over_workflow():
    """Explicit capability IDs should override the workflow alias."""
    request = AICapabilityExecuteRequest(
        capability_id="copilot.pr.explain",
        workflow=AIWorkflow.PR_RAG_SUMMARY,
    )

    assert request.resolve_capability_id() == "copilot.pr.explain"


def test_ai_execute_request_resolves_workflow_from_capability_id():
    """Known capability IDs should map back to workflow aliases."""
    request = AICapabilityExecuteRequest(
        capability_id="github.check.failure_rag_explain",
    )

    assert request.resolve_workflow() == AIWorkflow.FAILURE_RAG_EXPLAIN


def test_ai_execute_request_returns_none_for_unknown_workflow_mapping():
    """Unknown capability IDs should not invent workflow aliases."""
    request = AICapabilityExecuteRequest(
        capability_id="ipfs.llm.generate",
    )

    assert request.resolve_workflow() is None


def test_ai_execute_request_validates_pr_requirement():
    """PR-oriented workflows should require a PR number."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.PR_RAG_SUMMARY,
    )

    try:
        request.validate_execution_requirements()
    except ValueError as exc:
        assert "context.pr_number" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_ai_execute_request_resolves_accelerated_failure_workflow():
    """Accelerated failure workflow should resolve to the correct capability."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.ACCELERATED_FAILURE_EXPLAIN,
        context=AICapabilityContext(pr_number=123),
    )

    assert request.resolve_capability_id() == "github.check.accelerated_failure_explain"


def test_ai_execute_request_validates_cid_requirement():
    """CID read workflow should require a cid input or option."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.READ_STORED_OUTPUT,
    )

    try:
        request.validate_execution_requirements()
    except ValueError as exc:
        assert "requires inputs.cid or options.cid" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_ai_execute_request_accepts_valid_read_cid_shape():
    """CID read workflow should validate when a cid is supplied."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.READ_STORED_OUTPUT,
        inputs={"cid": "bafy123"},
    )

    request.validate_execution_requirements()


def test_ai_execute_request_validates_prompt_requirement_for_accelerate_store():
    """Accelerated generate/store workflow should require a prompt."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.ACCELERATE_GENERATE_AND_STORE,
    )

    try:
        request.validate_execution_requirements()
    except ValueError as exc:
        assert "requires inputs.prompt or options.prompt" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_ai_execute_request_validates_failure_target_pairing():
    """Failure target type should not be accepted without a target value."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.FAILURE_RAG_EXPLAIN,
        context=AICapabilityContext(pr_number=123, failure_target_type="workflow"),
    )

    try:
        request.validate_execution_requirements()
    except ValueError as exc:
        assert "failure_target and failure_target_type must be provided together" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_ai_execute_request_normalizes_workflow_name_to_failure_target():
    """workflow_name should normalize into the failure target fields."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.FAILURE_RAG_EXPLAIN,
        context=AICapabilityContext(pr_number=123, workflow_name="CI Linux"),
    )

    context = request.normalized_context()

    assert context.failure_target == "CI Linux"
    assert context.failure_target_type == "workflow"


def test_ai_execute_request_normalizes_check_name_to_failure_target():
    """check_name should normalize into the failure target fields."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.COPILOT_EXPLAIN_FAILURE,
        context=AICapabilityContext(pr_number=123, check_name="unit tests"),
    )

    context = request.normalized_context()

    assert context.failure_target == "unit tests"
    assert context.failure_target_type == "check"


def test_ai_execute_request_rejects_conflicting_workflow_name_target():
    """workflow_name should not conflict with an explicit failure target."""
    request = AICapabilityExecuteRequest(
        workflow=AIWorkflow.FAILURE_RAG_EXPLAIN,
        context=AICapabilityContext(
            pr_number=123,
            workflow_name="CI Linux",
            failure_target="Lint",
        ),
    )

    try:
        request.normalized_context()
    except ValueError as exc:
        assert "workflow_name conflicts with context.failure_target" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_pr_rag_summary_typed_request_converts_to_execute_request():
    """The PR summary typed request should produce the generic workflow request."""
    request = AIPRRAGSummaryExecuteRequest(
        pr_number=123,
        repo="openai/example",
        persist_output=True,
        ipfs=AIIPFSOptions(pin=True),
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.PR_RAG_SUMMARY
    assert execute_request.context.pr_number == 123
    assert execute_request.context.repo == "openai/example"
    assert execute_request.persist_output is True
    assert execute_request.ipfs is not None
    assert execute_request.ipfs.pin is True


def test_pr_rag_summary_typed_request_can_select_accelerated_backend():
    """The PR summary typed request should support accelerated backend selection."""
    request = AIPRRAGSummaryExecuteRequest(
        pr_number=123,
        repo="openai/example",
        summary_backend=AISummaryBackend.ACCELERATED,
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.ACCELERATED_PR_SUMMARY
    assert execute_request.context.pr_number == 123


def test_accelerated_pr_summary_typed_request_converts_to_execute_request():
    """The accelerated PR summary typed request should preserve repo and PR context."""
    request = AIAcceleratedPRSummaryExecuteRequest(
        pr_number=123,
        repo="openai/example",
        generation=AIGenerationOptions(model="llama3"),
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.ACCELERATED_PR_SUMMARY
    assert execute_request.context.pr_number == 123
    assert execute_request.context.repo == "openai/example"
    assert execute_request.generation is not None


def test_copilot_explain_pr_typed_request_converts_to_execute_request():
    """The Copilot PR explain typed request should preserve repo and PR context."""
    request = AICopilotExplainPRExecuteRequest(
        pr_number=123,
        repo="openai/example",
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.COPILOT_EXPLAIN_PR
    assert execute_request.context.pr_number == 123
    assert execute_request.context.repo == "openai/example"


def test_copilot_summarize_diff_typed_request_converts_to_execute_request():
    """The Copilot diff summary typed request should preserve repo and PR context."""
    request = AICopilotSummarizeDiffExecuteRequest(
        pr_number=123,
        repo="openai/example",
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.COPILOT_SUMMARIZE_DIFF
    assert execute_request.context.pr_number == 123
    assert execute_request.context.repo == "openai/example"


def test_accelerate_generate_and_store_typed_request_converts_to_execute_request():
    """Accelerated generate/store typed request should preserve prompt and pin options."""
    request = AIAccelerateGenerateAndStoreExecuteRequest(
        prompt="summarize this",
        kit_pin=True,
        metadata={"repo": "openai/example"},
        generation=AIGenerationOptions(model="llama3"),
        ipfs=AIIPFSOptions(pin=False),
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.ACCELERATE_GENERATE_AND_STORE
    assert execute_request.inputs["prompt"] == "summarize this"
    assert execute_request.inputs["kit_pin"] is True
    assert execute_request.inputs["metadata"] == {"repo": "openai/example"}
    assert execute_request.generation is not None
    assert execute_request.ipfs is not None


def test_accelerated_failure_explain_typed_request_converts_to_execute_request():
    """Accelerated failure typed request should preserve named target context."""
    request = AIAcceleratedFailureExplainExecuteRequest(
        pr_number=123,
        repo="openai/example",
        workflow_name="CI Linux",
        history_cids=["bafy1"],
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.ACCELERATED_FAILURE_EXPLAIN
    assert execute_request.context.pr_number == 123
    assert execute_request.context.workflow_name == "CI Linux"
    assert execute_request.inputs["history_cids"] == ["bafy1"]


def test_failure_rag_explain_typed_request_can_select_accelerated_backend():
    """Failure RAG typed request should support accelerated backend selection."""
    request = AIFailureRAGExplainExecuteRequest(
        pr_number=123,
        repo="openai/example",
        workflow_name="CI Linux",
        failure_backend=AIFailureAnalysisBackend.ACCELERATED,
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.ACCELERATED_FAILURE_EXPLAIN
    assert execute_request.context.workflow_name == "CI Linux"


def test_copilot_explain_failure_typed_request_converts_named_target():
    """The Copilot failure typed request should preserve named workflow context."""
    request = AICopilotExplainFailureExecuteRequest(
        pr_number=123,
        workflow_name="CI Linux",
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.COPILOT_EXPLAIN_FAILURE
    assert execute_request.context.pr_number == 123
    assert execute_request.context.workflow_name == "CI Linux"


def test_copilot_explain_failure_typed_request_rejects_mixed_named_targets():
    """Copilot failure typed requests should not allow both workflow and check names."""
    try:
        AICopilotExplainFailureExecuteRequest(
            pr_number=123,
            workflow_name="CI Linux",
            check_name="unit tests",
        )
    except ValueError as exc:
        assert "workflow_name and check_name are mutually exclusive" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_failure_rag_typed_request_converts_workflow_context():
    """The failure analysis typed request should preserve workflow-scoped context."""
    request = AIFailureRAGExplainExecuteRequest(
        pr_number=123,
        workflow_name="CI Linux",
        generation=AIGenerationOptions(model="llama3"),
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.FAILURE_RAG_EXPLAIN
    assert execute_request.context.pr_number == 123
    assert execute_request.context.workflow_name == "CI Linux"
    assert execute_request.generation is not None
    assert execute_request.generation.model == "llama3"


def test_failure_rag_typed_request_carries_history_cids():
    """Failure analysis typed requests should forward history CIDs into generic inputs."""
    request = AIFailureRAGExplainExecuteRequest(
        pr_number=123,
        workflow_name="CI Linux",
        history_cids=["bafy-failure-1", "bafy-failure-2"],
    )

    execute_request = request.to_execute_request()

    assert execute_request.inputs["history_cids"] == ["bafy-failure-1", "bafy-failure-2"]


def test_find_similar_failures_typed_request_converts_to_execute_request():
    """The similar-failures request should preserve retrieval inputs and workflow context."""
    request = AIFindSimilarFailuresExecuteRequest(
        pr_number=123,
        workflow_name="CI Linux",
        history_candidates=[{"summary": "Prior CI Linux dependency failure"}],
        top_k=2,
    )

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.FIND_SIMILAR_FAILURES
    assert execute_request.context.pr_number == 123
    assert execute_request.context.workflow_name == "CI Linux"
    assert execute_request.inputs["history_candidates"] == [
        {"summary": "Prior CI Linux dependency failure"}
    ]
    assert execute_request.options["top_k"] == 2


def test_find_similar_failures_typed_request_carries_history_cids():
    """Similar-failure typed requests should forward history CIDs into generic inputs."""
    request = AIFindSimilarFailuresExecuteRequest(
        pr_number=123,
        history_cids=["bafy-similar-1"],
    )

    execute_request = request.to_execute_request()

    assert execute_request.inputs["history_cids"] == ["bafy-similar-1"]


def test_failure_rag_typed_request_rejects_mixed_named_targets():
    """Failure analysis typed requests should not allow both workflow and check names."""
    try:
        AIFailureRAGExplainExecuteRequest(
            pr_number=123,
            workflow_name="CI Linux",
            check_name="unit tests",
        )
    except ValueError as exc:
        assert "workflow_name and check_name are mutually exclusive" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_stored_output_read_typed_request_converts_to_execute_request():
    """Stored output typed requests should normalize CID input for the generic workflow."""
    request = AIStoredOutputReadExecuteRequest(cid="bafy123")

    execute_request = request.to_execute_request()

    assert execute_request.workflow == AIWorkflow.READ_STORED_OUTPUT
    assert execute_request.inputs == {"cid": "bafy123"}
