"""Shared AI capability registry and execution helpers."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from handsfree.cli import CLIExecutor, CopilotCLIAdapter, GitHubCLIAdapter
from handsfree.commands.profiles import Profile, ProfileConfig
from handsfree.ipfs_datasets_routers import (
    get_embeddings_router,
    get_ipfs_router,
    get_llm_router,
)
from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_adapter
from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter

from .models import (
    AICapabilityRequest,
    AICapabilityResult,
    AICapabilitySpec,
    AIBackendFamily,
    AIExecutionMode,
)


_CAPABILITIES: dict[str, AICapabilitySpec] = {
    "copilot.pr.explain": AICapabilitySpec(
        capability_id="copilot.pr.explain",
        title="Explain Pull Request",
        description="Use GitHub Copilot CLI to explain a pull request.",
        backend_family=AIBackendFamily.COPILOT_CLI,
        execution_modes=(AIExecutionMode.FIXTURE, AIExecutionMode.CLI_LIVE),
        required_inputs=("pr_number",),
        optional_inputs=("profile_config",),
        tags=("github", "copilot", "pull_request", "explanation"),
    ),
    "copilot.pr.diff_summary": AICapabilitySpec(
        capability_id="copilot.pr.diff_summary",
        title="Summarize Pull Request Diff",
        description="Use GitHub Copilot CLI to summarize a pull request diff.",
        backend_family=AIBackendFamily.COPILOT_CLI,
        execution_modes=(AIExecutionMode.FIXTURE, AIExecutionMode.CLI_LIVE),
        required_inputs=("pr_number",),
        optional_inputs=("profile_config",),
        tags=("github", "copilot", "pull_request", "summary"),
    ),
    "copilot.pr.failure_explain": AICapabilitySpec(
        capability_id="copilot.pr.failure_explain",
        title="Explain Pull Request Failure",
        description="Use GitHub Copilot CLI to explain failing checks for a pull request.",
        backend_family=AIBackendFamily.COPILOT_CLI,
        execution_modes=(AIExecutionMode.FIXTURE, AIExecutionMode.CLI_LIVE),
        required_inputs=("pr_number",),
        optional_inputs=("failure_target", "failure_target_type", "profile_config"),
        tags=("github", "copilot", "pull_request", "checks"),
    ),
    "ipfs.llm.generate": AICapabilitySpec(
        capability_id="ipfs.llm.generate",
        title="Generate Text",
        description="Generate text through ipfs_datasets_py llm_router.",
        backend_family=AIBackendFamily.IPFS_LLM_ROUTER,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("prompt",),
        optional_inputs=("generation_options",),
        tags=("ipfs", "llm", "generation"),
    ),
    "ipfs.embeddings.embed_text": AICapabilitySpec(
        capability_id="ipfs.embeddings.embed_text",
        title="Embed Text",
        description="Embed one text through ipfs_datasets_py embeddings_router.",
        backend_family=AIBackendFamily.IPFS_EMBEDDINGS_ROUTER,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("text",),
        optional_inputs=("embedding_options",),
        tags=("ipfs", "embeddings", "vector"),
    ),
    "ipfs.embeddings.embed_texts": AICapabilitySpec(
        capability_id="ipfs.embeddings.embed_texts",
        title="Embed Texts",
        description="Embed multiple texts through ipfs_datasets_py embeddings_router.",
        backend_family=AIBackendFamily.IPFS_EMBEDDINGS_ROUTER,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("texts",),
        optional_inputs=("embedding_options",),
        tags=("ipfs", "embeddings", "vector", "batch"),
    ),
    "ipfs.retrieval.rank_texts": AICapabilitySpec(
        capability_id="ipfs.retrieval.rank_texts",
        title="Rank Candidate Texts",
        description=(
            "Use embeddings_router to embed a query and candidate texts, then "
            "return similarity-ranked candidate results."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("query_text", "candidates"),
        optional_inputs=("embedding_options", "top_k"),
        tags=("ipfs", "embeddings", "retrieval", "ranking"),
    ),
    "ipfs.content.add_bytes": AICapabilitySpec(
        capability_id="ipfs.content.add_bytes",
        title="Add Content To IPFS",
        description="Store bytes through ipfs_datasets_py ipfs_router.",
        backend_family=AIBackendFamily.IPFS_CONTENT_ROUTER,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("data",),
        optional_inputs=("ipfs_options",),
        tags=("ipfs", "storage", "content"),
        read_only=False,
    ),
    "ipfs.content.read_ai_output": AICapabilitySpec(
        capability_id="ipfs.content.read_ai_output",
        title="Read Stored AI Output",
        description="Load a stored AI output payload from IPFS by CID.",
        backend_family=AIBackendFamily.IPFS_CONTENT_ROUTER,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("cid",),
        optional_inputs=("profile_config",),
        tags=("ipfs", "storage", "content", "read"),
    ),
    "ipfs.accelerate.generate": AICapabilitySpec(
        capability_id="ipfs.accelerate.generate",
        title="Accelerated Text Generation",
        description="Generate text through ipfs_accelerate_py canonical router modules.",
        backend_family=AIBackendFamily.IPFS_ACCELERATE,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("prompt",),
        optional_inputs=("generation_options",),
        tags=("ipfs", "accelerate", "llm", "generation"),
    ),
    "ipfs.accelerate.embed": AICapabilitySpec(
        capability_id="ipfs.accelerate.embed",
        title="Accelerated Embeddings",
        description="Generate embeddings through ipfs_accelerate_py canonical router modules.",
        backend_family=AIBackendFamily.IPFS_ACCELERATE,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.MCP_REMOTE),
        required_inputs=("texts",),
        optional_inputs=("embedding_options",),
        tags=("ipfs", "accelerate", "embeddings", "vector"),
    ),
    "ipfs.kit.pin": AICapabilitySpec(
        capability_id="ipfs.kit.pin",
        title="Pin Content With IPFS Kit",
        description="Pin content through ipfs_kit_py canonical backend modules.",
        backend_family=AIBackendFamily.IPFS_KIT,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.CLI_LIVE, AIExecutionMode.MCP_REMOTE),
        required_inputs=("cid",),
        optional_inputs=("ipfs_options",),
        tags=("ipfs", "kit", "pin"),
        read_only=False,
    ),
    "ipfs.kit.unpin": AICapabilitySpec(
        capability_id="ipfs.kit.unpin",
        title="Unpin Content With IPFS Kit",
        description="Unpin content through ipfs_kit_py canonical backend modules.",
        backend_family=AIBackendFamily.IPFS_KIT,
        execution_modes=(AIExecutionMode.DIRECT_IMPORT, AIExecutionMode.CLI_LIVE, AIExecutionMode.MCP_REMOTE),
        required_inputs=("cid",),
        optional_inputs=("ipfs_options",),
        tags=("ipfs", "kit", "pin"),
        read_only=False,
    ),
    "ipfs.accelerate.generate_and_store": AICapabilitySpec(
        capability_id="ipfs.accelerate.generate_and_store",
        title="Accelerated Generate And Store",
        description=(
            "Generate text through ipfs_accelerate_py, store the result through "
            "the IPFS router, and optionally pin it through ipfs_kit_py."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("prompt",),
        optional_inputs=("generation_options", "ipfs_options", "kit_pin", "metadata"),
        tags=("ipfs", "accelerate", "storage", "kit", "generation"),
        read_only=False,
    ),
    "github.pr.rag_summary": AICapabilitySpec(
        capability_id="github.pr.rag_summary",
        title="RAG-Style Pull Request Summary",
        description=(
            "Combine GitHub pull request context with embeddings and LLM routing "
            "to produce an augmented PR summary."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("pr_number",),
        optional_inputs=(
            "repo",
            "profile_config",
            "generation_options",
            "embedding_options",
            "persist_output",
            "ipfs_options",
        ),
        tags=("github", "ipfs", "embeddings", "llm", "rag", "pull_request"),
    ),
    "github.pr.accelerated_summary": AICapabilitySpec(
        capability_id="github.pr.accelerated_summary",
        title="Accelerated Pull Request Summary",
        description=(
            "Combine GitHub pull request context with embeddings and "
            "ipfs_accelerate_py generation to produce an augmented PR summary."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("pr_number",),
        optional_inputs=(
            "repo",
            "profile_config",
            "generation_options",
            "embedding_options",
            "persist_output",
            "ipfs_options",
        ),
        tags=("github", "ipfs", "accelerate", "embeddings", "summary", "pull_request"),
    ),
    "github.check.failure_rag_explain": AICapabilitySpec(
        capability_id="github.check.failure_rag_explain",
        title="RAG-Style Failure Analysis",
        description=(
            "Combine GitHub check context with embeddings and LLM routing "
            "to produce an augmented failure explanation."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("pr_number",),
        optional_inputs=(
            "repo",
            "failure_target",
            "failure_target_type",
            "github_provider",
            "history_candidates",
            "history_cids",
            "top_k",
            "profile_config",
            "generation_options",
            "embedding_options",
            "persist_output",
            "ipfs_options",
        ),
        tags=("github", "ipfs", "embeddings", "llm", "rag", "checks", "failure"),
    ),
    "github.check.accelerated_failure_explain": AICapabilitySpec(
        capability_id="github.check.accelerated_failure_explain",
        title="Accelerated Failure Analysis",
        description=(
            "Combine GitHub check context, retrieval, and ipfs_accelerate_py "
            "generation to produce an augmented failure explanation."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("pr_number",),
        optional_inputs=(
            "repo",
            "failure_target",
            "failure_target_type",
            "github_provider",
            "history_candidates",
            "history_cids",
            "top_k",
            "profile_config",
            "generation_options",
            "embedding_options",
            "persist_output",
            "ipfs_options",
        ),
        tags=("github", "ipfs", "accelerate", "embeddings", "checks", "failure"),
    ),
    "github.check.find_similar_failures": AICapabilitySpec(
        capability_id="github.check.find_similar_failures",
        title="Find Similar Failures",
        description=(
            "Combine current failure context with embeddings-based retrieval to "
            "rank similar prior failures."
        ),
        backend_family=AIBackendFamily.COMPOSITE,
        execution_modes=(AIExecutionMode.ORCHESTRATED,),
        required_inputs=("pr_number", "history_candidates"),
        optional_inputs=(
            "repo",
            "failure_target",
            "failure_target_type",
            "github_provider",
            "embedding_options",
            "history_cids",
            "top_k",
        ),
        tags=("github", "ipfs", "embeddings", "retrieval", "checks", "failure"),
    ),
}


def list_ai_capabilities() -> list[AICapabilitySpec]:
    """Return registered AI capabilities in stable order."""
    return [spec for _, spec in sorted(_CAPABILITIES.items(), key=lambda item: item[0])]


def get_ai_capability(capability_id: str) -> AICapabilitySpec:
    """Resolve one capability spec by id."""
    try:
        return _CAPABILITIES[capability_id]
    except KeyError as exc:
        raise KeyError(f"Unknown AI capability: {capability_id}") from exc


def execute_ai_capability(
    capability_id: str,
    *,
    cli_executor: CLIExecutor | None = None,
    profile_config: ProfileConfig | None = None,
    **kwargs: Any,
) -> AICapabilityResult:
    """Execute a registered AI capability through its current backend."""
    spec = get_ai_capability(capability_id)

    if spec.backend_family == AIBackendFamily.COPILOT_CLI:
        return _execute_copilot_capability(
            spec,
            cli_executor=cli_executor,
            profile_config=profile_config,
            **kwargs,
        )

    if capability_id == "ipfs.llm.generate":
        return _execute_ipfs_llm_generate(spec, **kwargs)
    if capability_id == "ipfs.embeddings.embed_text":
        return _execute_ipfs_embed_text(spec, **kwargs)
    if capability_id == "ipfs.embeddings.embed_texts":
        return _execute_ipfs_embed_texts(spec, **kwargs)
    if capability_id == "ipfs.retrieval.rank_texts":
        return _execute_ipfs_rank_texts(spec, **kwargs)
    if capability_id == "ipfs.content.add_bytes":
        return _execute_ipfs_add_bytes(spec, **kwargs)
    if capability_id == "ipfs.content.read_ai_output":
        return _execute_ipfs_read_ai_output(spec, profile_config=profile_config, **kwargs)
    if capability_id == "ipfs.accelerate.generate":
        return _execute_ipfs_accelerate_generate(spec, **kwargs)
    if capability_id == "ipfs.accelerate.embed":
        return _execute_ipfs_accelerate_embed(spec, **kwargs)
    if capability_id == "ipfs.kit.pin":
        return _execute_ipfs_kit_pin(spec, **kwargs)
    if capability_id == "ipfs.kit.unpin":
        return _execute_ipfs_kit_unpin(spec, **kwargs)
    if capability_id == "ipfs.accelerate.generate_and_store":
        return _execute_ipfs_accelerate_generate_and_store(spec, **kwargs)
    if capability_id == "github.pr.rag_summary":
        return _execute_github_pr_rag_summary(
            spec,
            profile_config=profile_config,
            **kwargs,
        )
    if capability_id == "github.pr.accelerated_summary":
        return _execute_github_pr_accelerated_summary(
            spec,
            profile_config=profile_config,
            **kwargs,
        )
    if capability_id == "github.check.failure_rag_explain":
        return _execute_github_check_failure_rag_explain(
            spec,
            profile_config=profile_config,
            **kwargs,
        )
    if capability_id == "github.check.accelerated_failure_explain":
        return _execute_github_check_accelerated_failure_explain(
            spec,
            profile_config=profile_config,
            **kwargs,
        )
    if capability_id == "github.check.find_similar_failures":
        return _execute_github_find_similar_failures(spec, **kwargs)

    raise NotImplementedError(f"No executor registered for AI capability: {capability_id}")


def execute_ai_request(
    request: AICapabilityRequest,
    *,
    cli_executor: CLIExecutor | None = None,
    profile_config: ProfileConfig | None = None,
) -> AICapabilityResult:
    """Execute a typed AI capability request."""
    merged_kwargs: dict[str, Any] = dict(request.inputs)
    merged_kwargs.update(request.options)
    failure_target = request.context.failure_target
    failure_target_type = request.context.failure_target_type

    if request.context.workflow_name:
        if failure_target and failure_target != request.context.workflow_name:
            raise ValueError("workflow_name conflicts with context.failure_target")
        if failure_target_type and failure_target_type != "workflow":
            raise ValueError("workflow_name conflicts with context.failure_target_type")
        failure_target = request.context.workflow_name
        failure_target_type = "workflow"

    if request.context.check_name:
        if failure_target and failure_target != request.context.check_name:
            raise ValueError("check_name conflicts with context.failure_target")
        if failure_target_type and failure_target_type != "check":
            raise ValueError("check_name conflicts with context.failure_target_type")
        failure_target = request.context.check_name
        failure_target_type = "check"

    if request.context.repo and "repo" not in merged_kwargs:
        merged_kwargs["repo"] = request.context.repo
    if request.context.pr_number is not None and "pr_number" not in merged_kwargs:
        merged_kwargs["pr_number"] = request.context.pr_number
    if failure_target and "failure_target" not in merged_kwargs:
        merged_kwargs["failure_target"] = failure_target
    if failure_target_type and "failure_target_type" not in merged_kwargs:
        merged_kwargs["failure_target_type"] = failure_target_type

    return execute_ai_capability(
        request.capability_id,
        cli_executor=cli_executor,
        profile_config=profile_config,
        **merged_kwargs,
    )


def _execute_copilot_capability(
    spec: AICapabilitySpec,
    *,
    cli_executor: CLIExecutor | None,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    adapter = CopilotCLIAdapter(executor=cli_executor)
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)

    if spec.capability_id == "copilot.pr.explain":
        output = adapter.explain_pr(kwargs["pr_number"], resolved_profile)
    elif spec.capability_id == "copilot.pr.diff_summary":
        output = adapter.summarize_diff(kwargs["pr_number"], resolved_profile)
    else:
        output = adapter.explain_failure(
            kwargs["pr_number"],
            resolved_profile,
            failure_target=kwargs.get("failure_target"),
            failure_target_type=kwargs.get("failure_target_type"),
        )

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=_resolve_copilot_execution_mode(output),
        ok=True,
        output=output,
        trace=output.get("trace", {}),
    )


def _execute_ipfs_llm_generate(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    generation_options = dict(kwargs.get("generation_options") or {})
    output = get_llm_router().generate_text(kwargs["prompt"], **generation_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "generate_text"},
    )


def _execute_ipfs_embed_text(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    embedding_options = dict(kwargs.get("embedding_options") or {})
    output = get_embeddings_router().embed_text(kwargs["text"], **embedding_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "embed_text"},
    )


def _execute_ipfs_embed_texts(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    embedding_options = dict(kwargs.get("embedding_options") or {})
    output = get_embeddings_router().embed_texts(kwargs["texts"], **embedding_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "embed_texts"},
    )


def _execute_ipfs_rank_texts(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    embedding_options = dict(kwargs.get("embedding_options") or {})
    query_text = str(kwargs["query_text"])
    candidates = [str(candidate) for candidate in kwargs["candidates"]]
    embeddings = get_embeddings_router().embed_texts([query_text, *candidates], **embedding_options)
    query_embedding = embeddings[0]
    candidate_embeddings = embeddings[1:]
    ranked_items = []

    for candidate, embedding in zip(candidates, candidate_embeddings, strict=False):
        ranked_items.append(
            {
                "text": candidate,
                "score": _cosine_similarity(query_embedding, embedding),
            }
        )

    ranked_items.sort(key=lambda item: item["score"], reverse=True)
    top_k = kwargs.get("top_k")
    if isinstance(top_k, int) and top_k > 0:
        ranked_items = ranked_items[:top_k]

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "query_text": query_text,
            "ranked_items": ranked_items,
            "embedding_dimensions": len(query_embedding),
        },
        trace={
            "provider": AIBackendFamily.IPFS_EMBEDDINGS_ROUTER.value,
            "operation": "embed_texts",
            "candidate_count": len(candidates),
        },
    )


def _execute_ipfs_add_bytes(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    ipfs_options = dict(kwargs.get("ipfs_options") or {})
    output = get_ipfs_router().add_bytes(kwargs["data"], **ipfs_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "add_bytes"},
    )


def _execute_ipfs_read_ai_output(
    spec: AICapabilitySpec,
    *,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)
    cid = kwargs["cid"]
    payload_bytes = get_ipfs_router().cat(cid)
    payload = json.loads(payload_bytes.decode("utf-8"))
    stored_payload = payload.get("payload", {})
    summary = str(stored_payload.get("summary") or "")
    headline = str(stored_payload.get("headline") or f"Stored AI output {cid}")
    spoken_text = resolved_profile.truncate_spoken_text(summary or headline)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output={
            "spoken_text": spoken_text,
            "headline": headline,
            "summary": summary,
            "cid": cid,
            "stored_capability_id": payload.get("capability_id"),
            "metadata": payload.get("metadata", {}),
            "payload": stored_payload,
            "trace": {
                "provider": spec.backend_family.value,
                "operation": "cat",
                "cid": cid,
            },
        },
        trace={"provider": spec.backend_family.value, "operation": "cat", "cid": cid},
    )


def _execute_ipfs_accelerate_generate(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    generation_options = dict(kwargs.get("generation_options") or {})
    output = get_ipfs_accelerate_adapter().generate(kwargs["prompt"], **generation_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "generate"},
    )


def _execute_ipfs_accelerate_embed(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    embedding_options = dict(kwargs.get("embedding_options") or {})
    output = get_ipfs_accelerate_adapter().embed(kwargs["texts"], **embedding_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "embed"},
    )


def _execute_ipfs_kit_pin(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    ipfs_options = dict(kwargs.get("ipfs_options") or {})
    output = get_ipfs_kit_adapter().pin(kwargs["cid"], **ipfs_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "pin"},
    )


def _execute_ipfs_kit_unpin(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    ipfs_options = dict(kwargs.get("ipfs_options") or {})
    output = get_ipfs_kit_adapter().unpin(kwargs["cid"], **ipfs_options)
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.DIRECT_IMPORT,
        ok=True,
        output=output,
        trace={"provider": spec.backend_family.value, "operation": "unpin"},
    )


def _execute_ipfs_accelerate_generate_and_store(
    spec: AICapabilitySpec,
    **kwargs: Any,
) -> AICapabilityResult:
    generation_options = dict(kwargs.get("generation_options") or {})
    ipfs_options = dict(kwargs.get("ipfs_options") or {})
    metadata = dict(kwargs.get("metadata") or {})

    generated = get_ipfs_accelerate_adapter().generate(kwargs["prompt"], **generation_options)
    payload = {
        "capability_id": spec.capability_id,
        "prompt": kwargs["prompt"],
        "output": generated,
        "metadata": metadata,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    cid = get_ipfs_router().add_bytes(payload_bytes, **ipfs_options)

    pin_result = None
    if kwargs.get("kit_pin"):
        pin_result = get_ipfs_kit_adapter().pin(cid, **ipfs_options)

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "prompt": kwargs["prompt"],
            "generated": generated,
            "cid": cid,
            "kit_pin": pin_result,
            "stored_bytes": len(payload_bytes),
            "trace": {
                "provider": spec.backend_family.value,
                "steps": {
                    "accelerate_generate": {
                        "provider": AIBackendFamily.IPFS_ACCELERATE.value,
                        "operation": "generate",
                    },
                    "ipfs_store": {
                        "provider": AIBackendFamily.IPFS_CONTENT_ROUTER.value,
                        "operation": "add_bytes",
                        "cid": cid,
                    },
                    **(
                        {
                            "kit_pin": {
                                "provider": AIBackendFamily.IPFS_KIT.value,
                                "operation": "pin",
                            }
                        }
                        if pin_result is not None
                        else {}
                    ),
                },
            },
        },
        trace={
            "provider": spec.backend_family.value,
            "cid": cid,
            "kit_pin": pin_result is not None,
        },
    )


def _execute_github_pr_rag_summary(
    spec: AICapabilitySpec,
    *,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)
    pr_number = kwargs["pr_number"]
    repo = kwargs.get("repo")
    embedding_options = dict(kwargs.get("embedding_options") or {})
    generation_options = dict(kwargs.get("generation_options") or {})

    pr_summary = GitHubCLIAdapter().summarize_pr(pr_number, resolved_profile)
    summary_text = pr_summary["spoken_text"]
    embeddings = get_embeddings_router().embed_text(summary_text, **embedding_options)

    prompt = (
        f"Summarize pull request #{pr_number}"
        f"{f' in {repo}' if repo else ''} for a voice-first developer assistant.\n"
        f"Base summary: {summary_text}\n"
        f"Embedding dimensions: {len(embeddings)}\n"
        "Return a concise augmented summary with risks and next action."
    )
    generated_summary = get_llm_router().generate_text(prompt, **generation_options)
    spoken_text = resolved_profile.truncate_spoken_text(generated_summary)
    persisted = _persist_composite_output_if_enabled(
        capability_id=spec.capability_id,
        payload={
            "headline": f"RAG summary for PR #{pr_number}",
            "summary": generated_summary,
            "repo": repo,
            "pr_number": pr_number,
            "source_summary": summary_text,
            "embedding_dimensions": len(embeddings),
        },
        metadata=_build_persisted_metadata(
            profile_config=resolved_profile,
            repo=repo,
            pr_number=pr_number,
        ),
        persist_output=kwargs.get("persist_output"),
        ipfs_options=kwargs.get("ipfs_options"),
    )

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "spoken_text": spoken_text,
            "headline": f"RAG summary for PR #{pr_number}",
            "summary": generated_summary,
            "repo": repo,
            "pr_number": pr_number,
            "source_summary": summary_text,
            "embedding_dimensions": len(embeddings),
            "ipfs_cid": persisted.get("cid"),
            "trace": {
                "provider": spec.backend_family.value,
                "repo": repo,
                "pr_number": pr_number,
                "ipfs_cid": persisted.get("cid"),
                "steps": {
                    "github_pr_summary": pr_summary["trace"],
                    "embeddings": {
                        "provider": AIBackendFamily.IPFS_EMBEDDINGS_ROUTER.value,
                        "operation": "embed_text",
                        "dimensions": len(embeddings),
                    },
                    "llm": {
                        "provider": AIBackendFamily.IPFS_LLM_ROUTER.value,
                        "operation": "generate_text",
                    },
                },
            },
        },
        trace={
            "provider": spec.backend_family.value,
            "repo": repo,
            "pr_number": pr_number,
        },
    )


def _execute_github_pr_accelerated_summary(
    spec: AICapabilitySpec,
    *,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)
    pr_number = kwargs["pr_number"]
    repo = kwargs.get("repo")
    embedding_options = dict(kwargs.get("embedding_options") or {})
    generation_options = dict(kwargs.get("generation_options") or {})

    pr_summary = GitHubCLIAdapter().summarize_pr(pr_number, resolved_profile)
    summary_text = pr_summary["spoken_text"]
    embeddings = get_embeddings_router().embed_text(summary_text, **embedding_options)

    prompt = (
        f"Summarize pull request #{pr_number}"
        f"{f' in {repo}' if repo else ''} for a voice-first developer assistant.\n"
        f"Base summary: {summary_text}\n"
        f"Embedding dimensions: {len(embeddings)}\n"
        "Return a concise augmented summary with risks and next action."
    )
    generated_summary = get_ipfs_accelerate_adapter().generate(prompt, **generation_options)
    if isinstance(generated_summary, dict):
        generated_text = str(
            generated_summary.get("text")
            or generated_summary.get("summary")
            or generated_summary.get("output")
            or generated_summary
        )
    else:
        generated_text = str(generated_summary)
    spoken_text = resolved_profile.truncate_spoken_text(generated_text)
    persisted = _persist_composite_output_if_enabled(
        capability_id=spec.capability_id,
        payload={
            "headline": f"Accelerated summary for PR #{pr_number}",
            "summary": generated_text,
            "repo": repo,
            "pr_number": pr_number,
            "source_summary": summary_text,
            "embedding_dimensions": len(embeddings),
        },
        metadata=_build_persisted_metadata(
            profile_config=resolved_profile,
            repo=repo,
            pr_number=pr_number,
        ),
        persist_output=kwargs.get("persist_output"),
        ipfs_options=kwargs.get("ipfs_options"),
    )

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "spoken_text": spoken_text,
            "headline": f"Accelerated summary for PR #{pr_number}",
            "summary": generated_text,
            "repo": repo,
            "pr_number": pr_number,
            "source_summary": summary_text,
            "embedding_dimensions": len(embeddings),
            "ipfs_cid": persisted.get("cid"),
            "trace": {
                "provider": spec.backend_family.value,
                "repo": repo,
                "pr_number": pr_number,
                "ipfs_cid": persisted.get("cid"),
                "steps": {
                    "github_pr_summary": pr_summary["trace"],
                    "embeddings": {
                        "provider": AIBackendFamily.IPFS_EMBEDDINGS_ROUTER.value,
                        "operation": "embed_text",
                        "dimensions": len(embeddings),
                    },
                    "accelerate_generate": {
                        "provider": AIBackendFamily.IPFS_ACCELERATE.value,
                        "operation": "generate",
                    },
                },
            },
        },
        trace={
            "provider": spec.backend_family.value,
            "repo": repo,
            "pr_number": pr_number,
        },
    )


def _execute_github_check_failure_rag_explain(
    spec: AICapabilitySpec,
    *,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)
    pr_number = kwargs["pr_number"]
    repo = kwargs.get("repo")
    failure_target = kwargs.get("failure_target")
    failure_target_type = kwargs.get("failure_target_type")
    github_provider = kwargs.get("github_provider")
    history_candidates = list(kwargs.get("history_candidates") or [])
    history_candidates.extend(_load_failure_history_candidates_from_cids(kwargs.get("history_cids")))
    embedding_options = dict(kwargs.get("embedding_options") or {})
    generation_options = dict(kwargs.get("generation_options") or {})

    checks = _fetch_pr_checks(github_provider, repo, pr_number)
    checks_context = _build_checks_context(
        checks=checks,
        pr_number=pr_number,
        failure_target=failure_target,
        failure_target_type=failure_target_type,
    )
    embeddings = get_embeddings_router().embed_text(checks_context, **embedding_options)
    similar_failures: list[dict[str, Any]] = []
    retrieval_trace: dict[str, Any] | None = None
    similar_failures_context = ""
    if history_candidates:
        similar_failure_result = _execute_github_find_similar_failures(
            get_ai_capability("github.check.find_similar_failures"),
            pr_number=pr_number,
            repo=repo,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
            github_provider=github_provider,
            history_candidates=history_candidates,
            embedding_options=embedding_options,
            top_k=kwargs.get("top_k"),
        )
        similar_failures = list(similar_failure_result.output.get("ranked_matches", []))
        retrieval_trace = similar_failure_result.trace
        if similar_failures:
            similar_failures_context = "Similar prior failures:\n" + "\n".join(
                f"- score={match['score']:.3f} repo={match.get('repo') or 'unknown'} "
                f"pr={match.get('pr_number') or 'unknown'} summary={match.get('summary') or ''}"
                for match in similar_failures
            )
    prompt = (
        f"Explain failing checks for pull request #{pr_number}"
        f"{f' in {repo}' if repo else ''} for a voice-first developer assistant.\n"
        f"Failure focus: {failure_target_type or 'checks'} {failure_target or 'overall'}\n"
        f"Checks context: {checks_context}\n"
        f"{similar_failures_context + chr(10) if similar_failures_context else ''}"
        f"Embedding dimensions: {len(embeddings)}\n"
        "Return a concise explanation, likely cause, and next debugging step."
    )
    generated_summary = get_llm_router().generate_text(prompt, **generation_options)
    spoken_text = resolved_profile.truncate_spoken_text(generated_summary)
    persisted = _persist_composite_output_if_enabled(
        capability_id=spec.capability_id,
        payload={
            "headline": f"Failure analysis for PR #{pr_number}",
            "summary": generated_summary,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
            "checks_context": checks_context,
            "related_failures": similar_failures,
            "embedding_dimensions": len(embeddings),
        },
        metadata=_build_persisted_metadata(
            profile_config=resolved_profile,
            repo=repo,
            pr_number=pr_number,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
        ),
        persist_output=kwargs.get("persist_output"),
        ipfs_options=kwargs.get("ipfs_options"),
    )

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "spoken_text": spoken_text,
            "headline": f"Failure analysis for PR #{pr_number}",
            "summary": generated_summary,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
            "checks_context": checks_context,
            "related_failures": similar_failures,
            "embedding_dimensions": len(embeddings),
            "ipfs_cid": persisted.get("cid"),
            "trace": {
                "provider": spec.backend_family.value,
                "repo": repo,
                "pr_number": pr_number,
                "failure_target": failure_target,
                "failure_target_type": failure_target_type,
                "ipfs_cid": persisted.get("cid"),
                "steps": {
                    "github_checks": {
                        "provider": "github_provider" if github_provider else "synthetic",
                        "count": len(checks),
                    },
                    "embeddings": {
                        "provider": AIBackendFamily.IPFS_EMBEDDINGS_ROUTER.value,
                        "operation": "embed_text",
                        "dimensions": len(embeddings),
                    },
                    "llm": {
                        "provider": AIBackendFamily.IPFS_LLM_ROUTER.value,
                        "operation": "generate_text",
                    },
                    **({"retrieval": retrieval_trace} if retrieval_trace else {}),
                },
            },
        },
        trace={
            "provider": spec.backend_family.value,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
        },
    )


def _execute_github_find_similar_failures(spec: AICapabilitySpec, **kwargs: Any) -> AICapabilityResult:
    pr_number = kwargs["pr_number"]
    repo = kwargs.get("repo")
    failure_target = kwargs.get("failure_target")
    failure_target_type = kwargs.get("failure_target_type")
    github_provider = kwargs.get("github_provider")
    history_candidates = list(kwargs.get("history_candidates") or [])
    history_candidates.extend(_load_failure_history_candidates_from_cids(kwargs.get("history_cids")))
    top_k = kwargs.get("top_k")

    checks = _fetch_pr_checks(github_provider, repo, pr_number)
    checks_context = _build_checks_context(
        checks=checks,
        pr_number=pr_number,
        failure_target=failure_target,
        failure_target_type=failure_target_type,
    )

    candidate_payloads = [_normalize_failure_history_candidate(candidate) for candidate in history_candidates]
    ranking = _execute_ipfs_rank_texts(
        get_ai_capability("ipfs.retrieval.rank_texts"),
        query_text=checks_context,
        candidates=[candidate["match_text"] for candidate in candidate_payloads],
        embedding_options=kwargs.get("embedding_options"),
        top_k=top_k,
    )

    ranked_lookup = {item["text"]: item["score"] for item in ranking.output["ranked_items"]}
    ranked_matches = []
    for candidate in candidate_payloads:
        match_text = candidate["match_text"]
        if match_text not in ranked_lookup:
            continue
        ranked_matches.append(
            {
                "score": ranked_lookup[match_text],
                "summary": candidate["summary"],
                "repo": candidate.get("repo"),
                "pr_number": candidate.get("pr_number"),
                "failure_target": candidate.get("failure_target"),
                "failure_target_type": candidate.get("failure_target_type"),
            }
        )

    ranked_matches.sort(key=lambda item: item["score"], reverse=True)

    trace = {
        "provider": spec.backend_family.value,
        "repo": repo,
        "pr_number": pr_number,
        "failure_target": failure_target,
        "failure_target_type": failure_target_type,
        "steps": {
            "github_checks": {
                "provider": "github_provider" if github_provider else "synthetic",
                "count": len(checks),
            },
            "retrieval": ranking.trace,
        },
    }

    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
            "checks_context": checks_context,
            "ranked_matches": ranked_matches,
            "embedding_dimensions": ranking.output["embedding_dimensions"],
            "trace": trace,
        },
        trace=trace,
    )


def _execute_github_check_accelerated_failure_explain(
    spec: AICapabilitySpec,
    *,
    profile_config: ProfileConfig | None,
    **kwargs: Any,
) -> AICapabilityResult:
    resolved_profile = profile_config or ProfileConfig.for_profile(Profile.DEFAULT)
    pr_number = kwargs["pr_number"]
    repo = kwargs.get("repo")
    failure_target = kwargs.get("failure_target")
    failure_target_type = kwargs.get("failure_target_type")
    github_provider = kwargs.get("github_provider")
    history_candidates = list(kwargs.get("history_candidates") or [])
    history_candidates.extend(_load_failure_history_candidates_from_cids(kwargs.get("history_cids")))
    embedding_options = dict(kwargs.get("embedding_options") or {})
    generation_options = dict(kwargs.get("generation_options") or {})

    checks = _fetch_pr_checks(github_provider, repo, pr_number)
    checks_context = _build_checks_context(
        checks=checks,
        pr_number=pr_number,
        failure_target=failure_target,
        failure_target_type=failure_target_type,
    )
    embeddings = get_embeddings_router().embed_text(checks_context, **embedding_options)
    similar_failures: list[dict[str, Any]] = []
    retrieval_trace: dict[str, Any] | None = None
    similar_failures_context = ""
    if history_candidates:
        similar_failure_result = _execute_github_find_similar_failures(
            get_ai_capability("github.check.find_similar_failures"),
            pr_number=pr_number,
            repo=repo,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
            github_provider=github_provider,
            history_candidates=history_candidates,
            embedding_options=embedding_options,
            top_k=kwargs.get("top_k"),
        )
        similar_failures = list(similar_failure_result.output.get("ranked_matches", []))
        retrieval_trace = similar_failure_result.trace
        if similar_failures:
            similar_failures_context = "Similar prior failures:\n" + "\n".join(
                f"- score={match['score']:.3f} repo={match.get('repo') or 'unknown'} "
                f"pr={match.get('pr_number') or 'unknown'} summary={match.get('summary') or ''}"
                for match in similar_failures
            )

    prompt = (
        f"Explain failing checks for pull request #{pr_number}"
        f"{f' in {repo}' if repo else ''} for a voice-first developer assistant.\n"
        f"Failure focus: {failure_target_type or 'checks'} {failure_target or 'overall'}\n"
        f"Checks context: {checks_context}\n"
        f"{similar_failures_context + chr(10) if similar_failures_context else ''}"
        f"Embedding dimensions: {len(embeddings)}\n"
        "Return a concise explanation, likely cause, and next debugging step."
    )
    generated_summary = get_ipfs_accelerate_adapter().generate(prompt, **generation_options)
    if isinstance(generated_summary, dict):
        generated_text = str(
            generated_summary.get("text")
            or generated_summary.get("summary")
            or generated_summary.get("output")
            or generated_summary
        )
    else:
        generated_text = str(generated_summary)
    spoken_text = resolved_profile.truncate_spoken_text(generated_text)
    persisted = _persist_composite_output_if_enabled(
        capability_id=spec.capability_id,
        payload={
            "headline": f"Accelerated failure analysis for PR #{pr_number}",
            "summary": generated_text,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
            "checks_context": checks_context,
            "related_failures": similar_failures,
            "embedding_dimensions": len(embeddings),
        },
        metadata=_build_persisted_metadata(
            profile_config=resolved_profile,
            repo=repo,
            pr_number=pr_number,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
        ),
        persist_output=kwargs.get("persist_output"),
        ipfs_options=kwargs.get("ipfs_options"),
    )
    return AICapabilityResult(
        capability_id=spec.capability_id,
        backend_family=spec.backend_family,
        execution_mode=AIExecutionMode.ORCHESTRATED,
        ok=True,
        output={
            "spoken_text": spoken_text,
            "headline": f"Accelerated failure analysis for PR #{pr_number}",
            "summary": generated_text,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
            "checks_context": checks_context,
            "related_failures": similar_failures,
            "embedding_dimensions": len(embeddings),
            "ipfs_cid": persisted.get("cid"),
            "trace": {
                "provider": spec.backend_family.value,
                "repo": repo,
                "pr_number": pr_number,
                "failure_target": failure_target,
                "failure_target_type": failure_target_type,
                "ipfs_cid": persisted.get("cid"),
                "steps": {
                    "github_checks": {
                        "provider": "github_provider" if github_provider else "synthetic",
                        "count": len(checks),
                    },
                    "embeddings": {
                        "provider": AIBackendFamily.IPFS_EMBEDDINGS_ROUTER.value,
                        "operation": "embed_text",
                        "dimensions": len(embeddings),
                    },
                    "accelerate_generate": {
                        "provider": AIBackendFamily.IPFS_ACCELERATE.value,
                        "operation": "generate",
                    },
                    **({"retrieval": retrieval_trace} if retrieval_trace else {}),
                },
            },
        },
        trace={
            "provider": spec.backend_family.value,
            "repo": repo,
            "pr_number": pr_number,
            "failure_target": failure_target,
            "failure_target_type": failure_target_type,
        },
    )


def _fetch_pr_checks(github_provider: Any, repo: str | None, pr_number: int) -> list[dict[str, Any]]:
    if github_provider is None or not repo:
        return []
    checks = github_provider.get_pr_checks(repo, pr_number)
    if isinstance(checks, list):
        return checks
    return []


def _build_checks_context(
    *,
    checks: list[dict[str, Any]],
    pr_number: int,
    failure_target: str | None,
    failure_target_type: str | None,
) -> str:
    if checks:
        matching_checks = checks
        if failure_target:
            target_lower = failure_target.lower()
            matching_checks = [
                check for check in checks if target_lower in str(check.get("name", "")).lower()
            ] or checks

        fragments = []
        for check in matching_checks:
            name = check.get("name", "unknown")
            status = check.get("status", "unknown")
            conclusion = check.get("conclusion", "unknown")
            fragments.append(f"{name}: status={status}, conclusion={conclusion}")
        return " ; ".join(fragments)

    target_label = failure_target or "overall failing checks"
    target_type_label = failure_target_type or "checks"
    return f"PR {pr_number} failure focus: {target_type_label} {target_label}"


def _normalize_failure_history_candidate(candidate: Any) -> dict[str, Any]:
    """Normalize a prior failure record into a retrieval-ready candidate shape."""
    if isinstance(candidate, str):
        return {
            "summary": candidate,
            "match_text": candidate,
            "repo": None,
            "pr_number": None,
            "failure_target": None,
            "failure_target_type": None,
        }

    if not isinstance(candidate, dict):
        rendered = str(candidate)
        return {
            "summary": rendered,
            "match_text": rendered,
            "repo": None,
            "pr_number": None,
            "failure_target": None,
            "failure_target_type": None,
        }

    summary = str(candidate.get("summary") or candidate.get("text") or "")
    repo = candidate.get("repo")
    pr_number = candidate.get("pr_number")
    failure_target = candidate.get("failure_target")
    failure_target_type = candidate.get("failure_target_type")
    match_text = " | ".join(
        value
        for value in [
            str(repo) if repo else "",
            f"PR {pr_number}" if pr_number is not None else "",
            f"{failure_target_type} {failure_target}".strip() if failure_target else "",
            summary,
        ]
        if value
    ) or summary
    return {
        "summary": summary,
        "match_text": match_text,
        "repo": repo,
        "pr_number": pr_number,
        "failure_target": failure_target,
        "failure_target_type": failure_target_type,
    }


def _load_failure_history_candidates_from_cids(history_cids: Any) -> list[dict[str, Any]]:
    """Load prior failure candidates from stored AI outputs by CID."""
    if not history_cids:
        return []

    loaded_candidates: list[dict[str, Any]] = []
    for cid in history_cids:
        if not isinstance(cid, str) or not cid.strip():
            continue
        payload_bytes = get_ipfs_router().cat(cid.strip())
        payload = json.loads(payload_bytes.decode("utf-8"))
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        stored_payload = payload.get("payload", {}) if isinstance(payload, dict) else {}
        loaded_candidates.append(
            {
                "summary": stored_payload.get("summary") or stored_payload.get("headline") or f"Stored output {cid}",
                "repo": metadata.get("repo") or stored_payload.get("repo"),
                "pr_number": metadata.get("pr_number") or stored_payload.get("pr_number"),
                "failure_target": metadata.get("failure_target") or stored_payload.get("failure_target"),
                "failure_target_type": metadata.get("failure_target_type")
                or stored_payload.get("failure_target_type"),
            }
        )
    return loaded_candidates


def _persist_composite_output_if_enabled(
    *,
    capability_id: str,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    persist_output: Any,
    ipfs_options: Any,
) -> dict[str, Any]:
    should_persist = _should_persist_composite_output(persist_output)
    if not should_persist:
        return {"persisted": False, "cid": None}

    resolved_ipfs_options = dict(ipfs_options or {})
    data = json.dumps(
        {
            "capability_id": capability_id,
            "metadata": metadata,
            "payload": payload,
        },
        sort_keys=True,
    ).encode("utf-8")
    cid = get_ipfs_router().add_bytes(data, **resolved_ipfs_options)
    return {"persisted": True, "cid": cid}


def _should_persist_composite_output(persist_output: Any) -> bool:
    if isinstance(persist_output, bool):
        return persist_output
    return os.getenv("HANDSFREE_AI_PERSIST_OUTPUTS_TO_IPFS", "false").lower() == "true"


def _build_persisted_metadata(
    *,
    profile_config: ProfileConfig,
    repo: str | None,
    pr_number: int | None,
    failure_target: str | None = None,
    failure_target_type: str | None = None,
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "profile": profile_config.profile.value,
        "repo": repo,
        "pr_number": pr_number,
        "failure_target": failure_target,
        "failure_target_type": failure_target_type,
        "schema_version": 1,
    }


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for two embedding vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=False))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _resolve_copilot_execution_mode(output: dict[str, Any]) -> AIExecutionMode:
    source = str(output.get("trace", {}).get("source", "")).lower()
    if source == "fixture":
        return AIExecutionMode.FIXTURE
    return AIExecutionMode.CLI_LIVE
