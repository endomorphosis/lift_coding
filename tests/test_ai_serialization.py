"""Tests for API-facing AI response serialization."""

from handsfree.ai import AIBackendFamily, AIExecutionMode
from handsfree.ai.models import AICapabilityResult
from handsfree.ai.serialization import build_api_execute_response


def test_build_api_execute_response_for_rag_summary():
    """Composite PR summaries should serialize to the typed RAG output model."""
    result = AICapabilityResult(
        capability_id="github.pr.rag_summary",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "headline": "RAG summary for PR #123",
            "summary": "Summary body",
            "spoken_text": "Summary body",
            "repo": "openai/example",
            "pr_number": 123,
            "source_summary": "Base summary",
            "embedding_dimensions": 384,
            "ipfs_cid": "bafy-summary",
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "rag_summary"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "rag_summary"
    assert response.typed_output.schema_version == 1
    assert response.typed_output.repo == "openai/example"
    assert response.typed_output.ipfs_cid == "bafy-summary"


def test_build_api_execute_response_for_accelerated_pr_summary():
    """Accelerated PR summaries should reuse the typed RAG summary output model."""
    result = AICapabilityResult(
        capability_id="github.pr.accelerated_summary",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "headline": "Accelerated summary for PR #123",
            "summary": "Accelerated summary body",
            "spoken_text": "Accelerated summary body",
            "repo": "openai/example",
            "pr_number": 123,
            "source_summary": "Base summary",
            "embedding_dimensions": 256,
            "ipfs_cid": "bafy-accelerated-summary",
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "rag_summary"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "rag_summary"
    assert response.typed_output.pr_number == 123
    assert response.typed_output.ipfs_cid == "bafy-accelerated-summary"


def test_build_api_execute_response_for_failure_analysis():
    """Composite failure analyses should serialize to the typed failure model."""
    result = AICapabilityResult(
        capability_id="github.check.failure_rag_explain",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "headline": "Failure analysis for PR #124",
            "summary": "Check CI Linux setup first.",
            "spoken_text": "Check CI Linux setup first.",
            "repo": "openai/example",
            "pr_number": 124,
            "failure_target": "CI Linux",
            "failure_target_type": "workflow",
            "checks_context": "CI Linux: status=completed, conclusion=failure",
            "embedding_dimensions": 256,
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "failure_analysis"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "failure_analysis"
    assert response.typed_output.schema_version == 1
    assert response.typed_output.failure_target == "CI Linux"
    assert response.typed_output.embedding_dimensions == 256


def test_build_api_execute_response_for_accelerated_failure_analysis():
    """Accelerated failure analyses should reuse the typed failure output model."""
    result = AICapabilityResult(
        capability_id="github.check.accelerated_failure_explain",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "headline": "Accelerated failure analysis for PR #124",
            "summary": "CI Linux is failing during dependency setup.",
            "spoken_text": "The accelerated path thinks CI Linux is failing during setup.",
            "repo": "openai/example",
            "pr_number": 124,
            "failure_target": "CI Linux",
            "failure_target_type": "workflow",
            "checks_context": "CI Linux: status=completed, conclusion=failure",
            "embedding_dimensions": 256,
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "failure_analysis"
    assert response.typed_output is not None
    assert response.typed_output.headline == "Accelerated failure analysis for PR #124"


def test_build_api_execute_response_for_similar_failures():
    """Similar-failure retrieval should serialize to the typed retrieval model."""
    result = AICapabilityResult(
        capability_id="github.check.find_similar_failures",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "repo": "openai/example",
            "pr_number": 124,
            "failure_target": "CI Linux",
            "failure_target_type": "workflow",
            "checks_context": "CI Linux: status=completed, conclusion=failure",
            "embedding_dimensions": 256,
            "ranked_matches": [
                {
                    "score": 0.98,
                    "summary": "Dependency install failed during CI Linux setup.",
                    "repo": "openai/example",
                    "pr_number": 101,
                    "failure_target": "CI Linux",
                    "failure_target_type": "workflow",
                }
            ],
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "similar_failures"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "similar_failures"
    assert response.typed_output.pr_number == 124
    assert response.typed_output.ranked_matches[0]["pr_number"] == 101


def test_build_api_execute_response_for_stored_output_read():
    """CID reads should serialize to the typed stored-output model."""
    result = AICapabilityResult(
        capability_id="ipfs.content.read_ai_output",
        backend_family=AIBackendFamily.IPFS_CONTENT_ROUTER,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output={
            "headline": "Stored summary",
            "summary": "Recovered summary text.",
            "spoken_text": "Recovered summary text.",
            "cid": "bafy123",
            "stored_capability_id": "github.pr.rag_summary",
            "metadata": {"profile": "default"},
            "payload": {"summary": "Recovered summary text."},
        },
        trace={"provider": "ipfs_content_router"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "stored_output"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "stored_output"
    assert response.typed_output.schema_version == 1
    assert response.typed_output.cid == "bafy123"
    assert response.typed_output.metadata["profile"] == "default"


def test_build_api_execute_response_for_accelerated_stored_output():
    """Accelerated generate/store should serialize to the typed stored-output model."""
    result = AICapabilityResult(
        capability_id="ipfs.accelerate.generate_and_store",
        backend_family=AIBackendFamily.COMPOSITE,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "prompt": "summarize this",
            "generated": {"text": "summary"},
            "cid": "bafy-accelerated",
            "stored_bytes": 128,
            "kit_pin": {"ok": True, "cid": "bafy-accelerated"},
        },
        trace={"provider": "composite"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "accelerated_stored_output"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "accelerated_stored_output"
    assert response.typed_output.cid == "bafy-accelerated"
    assert response.typed_output.stored_bytes == 128


def test_build_api_execute_response_for_copilot_output():
    """Copilot capabilities should serialize to the typed Copilot output model."""
    result = AICapabilityResult(
        capability_id="copilot.pr.explain",
        backend_family=AIBackendFamily.COPILOT_CLI,
        execution_mode=AIExecutionMode.CLI_LIVE,
        ok=True,
        output={
            "headline": "Explanation",
            "spoken_text": "Explanation",
            "summary": "Explanation",
        },
        trace={"provider": "copilot_cli"},
    )

    response = build_api_execute_response(result)

    assert response.output_type == "copilot_output"
    assert response.typed_output is not None
    assert response.typed_output.schema_name == "copilot_output"
    assert response.typed_output.schema_version == 1
    assert response.typed_output.headline == "Explanation"
    assert response.output["spoken_text"] == "Explanation"


def test_build_api_execute_response_keeps_generic_shape_for_untyped_capability():
    """Capabilities without a typed serializer should still return generic output only."""
    result = AICapabilityResult(
        capability_id="ipfs.llm.generate",
        backend_family=AIBackendFamily.IPFS_LLM_ROUTER,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output="raw text output",
        trace={"provider": "ipfs_llm_router"},
    )

    response = build_api_execute_response(result)

    assert response.output_type is None
    assert response.typed_output is None
    assert response.output["value"] == "raw text output"
