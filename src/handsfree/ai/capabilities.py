"""Shared AI capability registry and execution helpers."""

from __future__ import annotations

from typing import Any

from handsfree.cli import CLIExecutor, CopilotCLIAdapter, GitHubCLIAdapter
from handsfree.commands.profiles import Profile, ProfileConfig
from handsfree.ipfs_datasets_routers import (
    get_embeddings_router,
    get_ipfs_router,
    get_llm_router,
)

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
        optional_inputs=("repo", "profile_config", "generation_options", "embedding_options"),
        tags=("github", "ipfs", "embeddings", "llm", "rag", "pull_request"),
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
    if capability_id == "ipfs.content.add_bytes":
        return _execute_ipfs_add_bytes(spec, **kwargs)
    if capability_id == "github.pr.rag_summary":
        return _execute_github_pr_rag_summary(
            spec,
            profile_config=profile_config,
            **kwargs,
        )

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

    if request.context.repo and "repo" not in merged_kwargs:
        merged_kwargs["repo"] = request.context.repo
    if request.context.pr_number is not None and "pr_number" not in merged_kwargs:
        merged_kwargs["pr_number"] = request.context.pr_number
    if request.context.failure_target and "failure_target" not in merged_kwargs:
        merged_kwargs["failure_target"] = request.context.failure_target
    if request.context.failure_target_type and "failure_target_type" not in merged_kwargs:
        merged_kwargs["failure_target_type"] = request.context.failure_target_type

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
            "trace": {
                "provider": spec.backend_family.value,
                "repo": repo,
                "pr_number": pr_number,
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


def _resolve_copilot_execution_mode(output: dict[str, Any]) -> AIExecutionMode:
    source = str(output.get("trace", {}).get("source", "")).lower()
    if source == "fixture":
        return AIExecutionMode.FIXTURE
    return AIExecutionMode.CLI_LIVE
