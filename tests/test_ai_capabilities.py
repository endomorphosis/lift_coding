"""Tests for shared AI capability registry and execution."""

from handsfree.ai import (
    AICapabilityRequest,
    AIBackendFamily,
    AIExecutionMode,
    AIRequestContext,
    execute_ai_capability,
    execute_ai_request,
    get_ai_capability,
    list_ai_capabilities,
)


def test_list_ai_capabilities_includes_copilot_and_ipfs_entries():
    """Capability registry should expose both Copilot and ipfs_datasets entries."""
    capability_ids = [spec.capability_id for spec in list_ai_capabilities()]

    assert "copilot.pr.explain" in capability_ids
    assert "ipfs.llm.generate" in capability_ids
    assert "ipfs.embeddings.embed_text" in capability_ids
    assert "ipfs.content.add_bytes" in capability_ids
    assert "github.pr.rag_summary" in capability_ids


def test_get_ai_capability_returns_metadata_for_ipfs_llm():
    """One capability lookup should expose normalized metadata."""
    spec = get_ai_capability("ipfs.llm.generate")

    assert spec.backend_family == AIBackendFamily.IPFS_LLM_ROUTER
    assert spec.execution_modes == (
        AIExecutionMode.DIRECT_IMPORT,
        AIExecutionMode.MCP_REMOTE,
    )
    assert spec.required_inputs == ("prompt",)


def test_execute_copilot_capability_uses_fixture_mode(monkeypatch):
    """Copilot capabilities should normalize fixture-backed CLI execution."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    result = execute_ai_capability("copilot.pr.explain", pr_number=123)

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.FIXTURE
    assert result.backend_family == AIBackendFamily.COPILOT_CLI
    assert "profile-aware routing" in result.output["spoken_text"].lower()


def test_execute_ipfs_llm_generate_delegates_to_router(monkeypatch):
    """LLM capability should call the direct-import router."""

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            return f"{prompt}|{kwargs['model']}"

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )

    result = execute_ai_capability(
        "ipfs.llm.generate",
        prompt="summarize this",
        generation_options={"model": "llama3"},
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.DIRECT_IMPORT
    assert result.output == "summarize this|llama3"


def test_execute_ipfs_embeddings_delegates_to_router(monkeypatch):
    """Embeddings capability should call the direct-import router."""

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [float(len(text)), float(kwargs["dimensions"])]

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )

    result = execute_ai_capability(
        "ipfs.embeddings.embed_text",
        text="abc",
        embedding_options={"dimensions": 4},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_EMBEDDINGS_ROUTER
    assert result.output == [3.0, 4.0]


def test_execute_ipfs_content_add_bytes_delegates_to_router(monkeypatch):
    """IPFS content capability should call the direct-import router."""

    class StubIPFSRouter:
        def add_bytes(self, data: bytes, **kwargs: object) -> str:
            return f"cid-{len(data)}-{kwargs['pin']}"

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability(
        "ipfs.content.add_bytes",
        data=b"payload",
        ipfs_options={"pin": True},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_CONTENT_ROUTER
    assert result.output == "cid-7-True"


def test_execute_ai_request_merges_context_into_kwargs(monkeypatch):
    """Typed requests should project shared context into executor kwargs."""
    captured: dict[str, object] = {}

    def stub_execute_ai_capability(capability_id: str, **kwargs: object):
        captured["capability_id"] = capability_id
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(
        "handsfree.ai.capabilities.execute_ai_capability",
        stub_execute_ai_capability,
    )

    request = AICapabilityRequest(
        capability_id="copilot.pr.failure_explain",
        context=AIRequestContext(
            repo="owner/repo",
            pr_number=123,
            failure_target="CI Linux",
            failure_target_type="workflow",
        ),
    )

    result = execute_ai_request(request)

    assert result == "ok"
    assert captured["capability_id"] == "copilot.pr.failure_explain"
    assert captured["kwargs"]["repo"] == "owner/repo"
    assert captured["kwargs"]["pr_number"] == 123
    assert captured["kwargs"]["failure_target"] == "CI Linux"
    assert captured["kwargs"]["failure_target_type"] == "workflow"


def test_execute_github_pr_rag_summary_orchestrates_multiple_backends(monkeypatch):
    """Composite PR summary should combine GitHub, embeddings, and LLM routing."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            assert "Add command system" in text
            assert kwargs["model"] == "minilm"
            return [0.1, 0.2, 0.3, 0.4]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            assert "pull request #123" in prompt.lower()
            assert "Embedding dimensions: 4" in prompt
            assert kwargs["model"] == "llama3"
            return "Augmented summary with risks and next action."

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )

    result = execute_ai_capability(
        "github.pr.rag_summary",
        pr_number=123,
        repo="openai/example",
        embedding_options={"model": "minilm"},
        generation_options={"model": "llama3"},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.COMPOSITE
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["repo"] == "openai/example"
    assert result.output["embedding_dimensions"] == 4
    assert "Augmented summary" in result.output["spoken_text"]
    assert result.output["trace"]["steps"]["github_pr_summary"]["provider"] == "github_cli"
