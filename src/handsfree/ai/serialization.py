"""Serialization helpers for API-facing AI execution responses."""

from __future__ import annotations

from typing import Any

from handsfree.models import (
    AIAcceleratedStoredOutput,
    AICapabilityExecuteResponse,
    AICopilotOutput,
    AIFailureAnalysisOutput,
    AISimilarFailuresOutput,
    AIRAGSummaryOutput,
    AIStoredOutputRead,
)

from .models import AICapabilityResult


def build_api_execute_response(result: AICapabilityResult) -> AICapabilityExecuteResponse:
    """Convert a raw capability result into the API response contract."""
    output = result.output if isinstance(result.output, dict) else {"value": result.output}
    output_type, typed_output = _build_typed_output(result.capability_id, output)
    return AICapabilityExecuteResponse(
        ok=result.ok,
        capability_id=result.capability_id,
        execution_mode=result.execution_mode.value,
        output_type=output_type,
        typed_output=typed_output,
        output=output,
        trace=result.trace,
    )


def _build_typed_output(
    capability_id: str,
    output: dict[str, Any],
) -> tuple[
    str | None,
    AIRAGSummaryOutput
    | AICopilotOutput
    | AIFailureAnalysisOutput
    | AISimilarFailuresOutput
    | AIStoredOutputRead
    | AIAcceleratedStoredOutput
    | None,
]:
    if capability_id in {
        "copilot.pr.explain",
        "copilot.pr.diff_summary",
        "copilot.pr.failure_explain",
    }:
        return "copilot_output", AICopilotOutput.model_validate(output)
    if capability_id in {
        "github.pr.rag_summary",
        "github.pr.accelerated_summary",
    }:
        return "rag_summary", AIRAGSummaryOutput.model_validate(output)
    if capability_id in {
        "github.check.failure_rag_explain",
        "github.check.accelerated_failure_explain",
    }:
        return "failure_analysis", AIFailureAnalysisOutput.model_validate(output)
    if capability_id == "github.check.find_similar_failures":
        return "similar_failures", AISimilarFailuresOutput.model_validate(output)
    if capability_id == "ipfs.content.read_ai_output":
        return "stored_output", AIStoredOutputRead.model_validate(output)
    if capability_id == "ipfs.accelerate.generate_and_store":
        return "accelerated_stored_output", AIAcceleratedStoredOutput.model_validate(output)
    return None, None
