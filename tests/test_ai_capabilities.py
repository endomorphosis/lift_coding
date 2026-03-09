"""Tests for shared AI capability registry and execution."""

import json

from handsfree.ai import (
    AICapabilityResult,
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
    assert "ipfs.embeddings.embed_texts" in capability_ids
    assert "ipfs.retrieval.rank_texts" in capability_ids
    assert "ipfs.content.add_bytes" in capability_ids
    assert "ipfs.content.read_ai_output" in capability_ids
    assert "ipfs.accelerate.generate" in capability_ids
    assert "ipfs.accelerate.embed" in capability_ids
    assert "ipfs.accelerate.generate_and_store" in capability_ids
    assert "ipfs.kit.pin" in capability_ids
    assert "ipfs.kit.unpin" in capability_ids
    assert "github.pr.rag_summary" in capability_ids
    assert "github.pr.accelerated_summary" in capability_ids
    assert "github.check.failure_rag_explain" in capability_ids
    assert "github.check.accelerated_failure_explain" in capability_ids
    assert "github.check.find_similar_failures" in capability_ids


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


def test_execute_ai_request_normalizes_workflow_name(monkeypatch):
    """Shared AI execution should normalize workflow_name to failure target fields."""
    captured = {}

    def stub_execute_ai_capability(capability_id: str, **kwargs):
        captured["capability_id"] = capability_id
        captured["kwargs"] = kwargs
        return AICapabilityResult(
            capability_id=capability_id,
            backend_family=AIBackendFamily.COPILOT_CLI,
            execution_mode=AIExecutionMode.FIXTURE,
            ok=True,
            output={"spoken_text": "ok"},
        )

    monkeypatch.setattr("handsfree.ai.capabilities.execute_ai_capability", stub_execute_ai_capability)

    result = execute_ai_request(
        AICapabilityRequest(
            capability_id="copilot.pr.failure_explain",
            context=AIRequestContext(pr_number=123, workflow_name="CI Linux"),
        )
    )

    assert result.ok is True
    assert captured["kwargs"]["failure_target"] == "CI Linux"
    assert captured["kwargs"]["failure_target_type"] == "workflow"


def test_execute_ai_request_normalizes_check_name(monkeypatch):
    """Shared AI execution should normalize check_name to failure target fields."""
    captured = {}

    def stub_execute_ai_capability(capability_id: str, **kwargs):
        captured["capability_id"] = capability_id
        captured["kwargs"] = kwargs
        return AICapabilityResult(
            capability_id=capability_id,
            backend_family=AIBackendFamily.COPILOT_CLI,
            execution_mode=AIExecutionMode.FIXTURE,
            ok=True,
            output={"spoken_text": "ok"},
        )

    monkeypatch.setattr("handsfree.ai.capabilities.execute_ai_capability", stub_execute_ai_capability)

    result = execute_ai_request(
        AICapabilityRequest(
            capability_id="copilot.pr.failure_explain",
            context=AIRequestContext(pr_number=123, check_name="unit tests"),
        )
    )

    assert result.ok is True
    assert captured["kwargs"]["failure_target"] == "unit tests"
    assert captured["kwargs"]["failure_target_type"] == "check"


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


def test_execute_ipfs_embeddings_embed_texts_delegates_to_router(monkeypatch):
    """Batch embeddings capability should call embed_texts on the router."""

    class StubEmbeddingsRouter:
        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            return [[float(len(text)), float(kwargs["dimensions"])] for text in texts]

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )

    result = execute_ai_capability(
        "ipfs.embeddings.embed_texts",
        texts=["abc", "hello"],
        embedding_options={"dimensions": 4},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_EMBEDDINGS_ROUTER
    assert result.output == [[3.0, 4.0], [5.0, 4.0]]


def test_execute_ipfs_retrieval_rank_texts_ranks_candidates(monkeypatch):
    """Retrieval ranking should sort candidates by cosine similarity."""

    class StubEmbeddingsRouter:
        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            return [
                [1.0, 0.0],  # query
                [0.9, 0.1],  # candidate 1
                [0.1, 0.9],  # candidate 2
                [0.7, 0.2],  # candidate 3
            ]

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )

    result = execute_ai_capability(
        "ipfs.retrieval.rank_texts",
        query_text="fix import errors",
        candidates=["import setup failure", "ui copy tweak", "dependency install issue"],
        top_k=2,
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["query_text"] == "fix import errors"
    assert result.output["embedding_dimensions"] == 2
    assert [item["text"] for item in result.output["ranked_items"]] == [
        "import setup failure",
        "dependency install issue",
    ]
    assert result.output["ranked_items"][0]["score"] >= result.output["ranked_items"][1]["score"]


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


def test_execute_ipfs_accelerate_generate_delegates_to_adapter(monkeypatch):
    """Accelerate generation capability should call the validated adapter seam."""

    class StubAccelerateAdapter:
        def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
            return {"text": f"{prompt}|{kwargs['model_name']}"}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_accelerate_adapter",
        lambda: StubAccelerateAdapter(),
    )

    result = execute_ai_capability(
        "ipfs.accelerate.generate",
        prompt="summarize this",
        generation_options={"model_name": "llama3"},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_ACCELERATE
    assert result.output == {"text": "summarize this|llama3"}


def test_execute_ipfs_accelerate_embed_delegates_to_adapter(monkeypatch):
    """Accelerate embedding capability should call the validated adapter seam."""

    class StubAccelerateAdapter:
        def embed(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            dims = float(kwargs["dimensions"])
            return [[float(len(text)), dims] for text in texts]

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_accelerate_adapter",
        lambda: StubAccelerateAdapter(),
    )

    result = execute_ai_capability(
        "ipfs.accelerate.embed",
        texts=["abc", "hello"],
        embedding_options={"dimensions": 8},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_ACCELERATE
    assert result.output == [[3.0, 8.0], [5.0, 8.0]]


def test_execute_ipfs_kit_pin_delegates_to_adapter(monkeypatch):
    """IPFS Kit pin capability should call the validated adapter seam."""

    class StubKitAdapter:
        def pin(self, cid: str, **kwargs: object) -> dict[str, object]:
            return {"ok": True, "cid": cid, "pin_name": kwargs.get("name")}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_kit_adapter",
        lambda: StubKitAdapter(),
    )

    result = execute_ai_capability(
        "ipfs.kit.pin",
        cid="bafy123",
        ipfs_options={"name": "failure-analysis"},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_KIT
    assert result.output == {"ok": True, "cid": "bafy123", "pin_name": "failure-analysis"}


def test_execute_ipfs_kit_unpin_delegates_to_adapter(monkeypatch):
    """IPFS Kit unpin capability should call the validated adapter seam."""

    class StubKitAdapter:
        def unpin(self, cid: str, **kwargs: object) -> dict[str, object]:
            return {"ok": True, "cid": cid, "recursive": kwargs.get("recursive")}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_kit_adapter",
        lambda: StubKitAdapter(),
    )

    result = execute_ai_capability(
        "ipfs.kit.unpin",
        cid="bafy123",
        ipfs_options={"recursive": False},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.IPFS_KIT
    assert result.output == {"ok": True, "cid": "bafy123", "recursive": False}


def test_execute_ipfs_accelerate_generate_and_store(monkeypatch):
    """Composite accelerate/store capability should generate, store, and optionally pin."""

    class StubAccelerateAdapter:
        def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
            return {"text": f"{prompt}|{kwargs['model_name']}"}

    class StubIPFSRouter:
        def add_bytes(self, data: bytes, **kwargs: object) -> str:
            payload = json.loads(data.decode("utf-8"))
            assert payload["output"] == {"text": "summarize this|llama3"}
            assert kwargs["pin"] is False
            return "bafy-accelerated"

    class StubKitAdapter:
        def pin(self, cid: str, **kwargs: object) -> dict[str, object]:
            return {"ok": True, "cid": cid, "name": kwargs.get("name")}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_accelerate_adapter",
        lambda: StubAccelerateAdapter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_kit_adapter",
        lambda: StubKitAdapter(),
    )

    result = execute_ai_capability(
        "ipfs.accelerate.generate_and_store",
        prompt="summarize this",
        generation_options={"model_name": "llama3"},
        ipfs_options={"pin": False, "name": "accelerated-summary"},
        kit_pin=True,
        metadata={"repo": "owner/repo"},
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["generated"] == {"text": "summarize this|llama3"}
    assert result.output["cid"] == "bafy-accelerated"
    assert result.output["kit_pin"] == {
        "ok": True,
        "cid": "bafy-accelerated",
        "name": "accelerated-summary",
    }


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
    assert result.output["ipfs_cid"] is None


def test_execute_github_failure_rag_explain_with_github_checks(monkeypatch):
    """Composite failure analysis should use GitHub checks when available."""

    class StubGitHubProvider:
        def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, object]]:
            assert repo == "openai/example"
            assert pr_number == 124
            return [
                {"name": "CI Linux", "status": "completed", "conclusion": "failure"},
                {"name": "Lint", "status": "completed", "conclusion": "success"},
            ]

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            assert "CI Linux" in text
            assert kwargs["model"] == "minilm"
            return [0.1, 0.2]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            assert "CI Linux" in prompt
            assert "Embedding dimensions: 2" in prompt
            assert kwargs["model"] == "llama3"
            return "The CI Linux job is failing during setup. Check dependency installation."

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )

    result = execute_ai_capability(
        "github.check.failure_rag_explain",
        pr_number=124,
        repo="openai/example",
        failure_target="CI Linux",
        failure_target_type="workflow",
        github_provider=StubGitHubProvider(),
        embedding_options={"model": "minilm"},
        generation_options={"model": "llama3"},
    )

    assert result.ok is True
    assert result.backend_family == AIBackendFamily.COMPOSITE
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["failure_target"] == "CI Linux"
    assert result.output["embedding_dimensions"] == 2
    assert "dependency installation" in result.output["spoken_text"].lower()
    assert result.output["trace"]["steps"]["github_checks"]["provider"] == "github_provider"
    assert result.output["related_failures"] == []


def test_execute_github_failure_rag_explain_without_github_provider(monkeypatch):
    """Composite failure analysis should still run with synthetic context only."""

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            assert "PR 123 failure focus" in text
            return [0.1]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            assert "overall failing checks" in prompt
            return "Likely a general CI issue. Start with the first failing check."

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )

    result = execute_ai_capability(
        "github.check.failure_rag_explain",
        pr_number=123,
    )

    assert result.ok is True
    assert result.output["checks_context"] == "PR 123 failure focus: checks overall failing checks"
    assert result.output["trace"]["steps"]["github_checks"]["provider"] == "synthetic"


def test_execute_github_failure_rag_explain_includes_similar_failures(monkeypatch):
    """Failure analysis should incorporate ranked prior failures when provided."""

    class StubGitHubProvider:
        def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, object]]:
            return [
                {"name": "CI Linux", "status": "completed", "conclusion": "failure"},
            ]

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            assert "CI Linux" in text
            return [0.1, 0.2]

        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            assert "CI Linux" in texts[0]
            return [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.1, 0.9],
            ]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            assert "Similar prior failures" in prompt
            assert "Dependency install failed during CI Linux setup." in prompt
            return "This looks similar to a prior CI Linux dependency setup failure."

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )

    result = execute_ai_capability(
        "github.check.failure_rag_explain",
        pr_number=125,
        repo="openai/example",
        failure_target="CI Linux",
        failure_target_type="workflow",
        github_provider=StubGitHubProvider(),
        history_candidates=[
            {
                "summary": "Dependency install failed during CI Linux setup.",
                "repo": "openai/example",
                "pr_number": 101,
                "failure_target": "CI Linux",
                "failure_target_type": "workflow",
            },
            {
                "summary": "A UI snapshot changed unexpectedly.",
                "repo": "openai/example",
                "pr_number": 99,
                "failure_target": "Visual tests",
                "failure_target_type": "check",
            },
        ],
        top_k=1,
    )

    assert result.ok is True
    assert len(result.output["related_failures"]) == 1
    assert result.output["related_failures"][0]["pr_number"] == 101
    assert "similar to a prior" in result.output["spoken_text"].lower()
    assert result.output["trace"]["steps"]["retrieval"]["steps"]["github_checks"]["provider"] == "github_provider"


def test_execute_github_failure_rag_explain_can_load_history_from_cids(monkeypatch):
    """Failure analysis should load related failures from stored CID records."""

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [0.1, 0.2]

        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            return [
                [1.0, 0.0],
                [0.9, 0.1],
            ]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            assert "Stored failure summary." in prompt
            return "This matches a stored failure record."

    class StubIPFSRouter:
        def cat(self, cid: str) -> bytes:
            assert cid == "bafy-history-1"
            return (
                b'{"capability_id":"github.check.failure_rag_explain",'
                b'"metadata":{"repo":"openai/example","pr_number":101,"failure_target":"CI Linux","failure_target_type":"workflow"},'
                b'"payload":{"summary":"Stored failure summary."}}'
            )

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability(
        "github.check.failure_rag_explain",
        pr_number=125,
        history_cids=["bafy-history-1"],
    )

    assert result.ok is True
    assert len(result.output["related_failures"]) == 1
    assert result.output["related_failures"][0]["pr_number"] == 101
    assert "stored failure record" in result.output["spoken_text"].lower()


def test_execute_github_find_similar_failures_ranks_history_candidates(monkeypatch):
    """Similar failure lookup should rank prior incidents against current failure context."""

    class StubGitHubProvider:
        def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, object]]:
            assert repo == "openai/example"
            assert pr_number == 125
            return [
                {"name": "CI Linux", "status": "completed", "conclusion": "failure"},
                {"name": "Lint", "status": "completed", "conclusion": "success"},
            ]

    class StubEmbeddingsRouter:
        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            assert "CI Linux" in texts[0]
            return [
                [1.0, 0.0],  # query
                [0.9, 0.1],  # similar candidate
                [0.1, 0.9],  # less similar candidate
            ]

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )

    result = execute_ai_capability(
        "github.check.find_similar_failures",
        pr_number=125,
        repo="openai/example",
        failure_target="CI Linux",
        failure_target_type="workflow",
        github_provider=StubGitHubProvider(),
        history_candidates=[
            {
                "summary": "Dependency install failed during CI Linux setup.",
                "repo": "openai/example",
                "pr_number": 101,
                "failure_target": "CI Linux",
                "failure_target_type": "workflow",
            },
            {
                "summary": "A UI snapshot changed unexpectedly.",
                "repo": "openai/example",
                "pr_number": 99,
                "failure_target": "Visual tests",
                "failure_target_type": "check",
            },
        ],
        top_k=1,
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["checks_context"].startswith("CI Linux")
    assert result.output["embedding_dimensions"] == 2
    assert len(result.output["ranked_matches"]) == 1
    assert result.output["ranked_matches"][0]["pr_number"] == 101
    assert result.output["ranked_matches"][0]["failure_target"] == "CI Linux"
    assert result.output["trace"]["steps"]["github_checks"]["provider"] == "github_provider"


def test_execute_github_find_similar_failures_can_load_history_from_cids(monkeypatch):
    """Similar-failure lookup should load prior incidents from stored CID records."""

    class StubEmbeddingsRouter:
        def embed_texts(self, texts: list[str], **kwargs: object) -> list[list[float]]:
            return [
                [1.0, 0.0],
                [0.9, 0.1],
            ]

    class StubIPFSRouter:
        def cat(self, cid: str) -> bytes:
            assert cid == "bafy-history-1"
            return (
                b'{"capability_id":"github.check.failure_rag_explain",'
                b'"metadata":{"repo":"openai/example","pr_number":101,"failure_target":"CI Linux","failure_target_type":"workflow"},'
                b'"payload":{"summary":"Stored failure summary."}}'
            )

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability(
        "github.check.find_similar_failures",
        pr_number=125,
        history_cids=["bafy-history-1"],
    )

    assert result.ok is True
    assert len(result.output["ranked_matches"]) == 1
    assert result.output["ranked_matches"][0]["pr_number"] == 101
    assert result.output["ranked_matches"][0]["summary"] == "Stored failure summary."


def test_execute_github_pr_rag_summary_can_persist_to_ipfs(monkeypatch):
    """Composite PR summaries should optionally persist their output to IPFS."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    captured: dict[str, object] = {}

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [0.1, 0.2]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            return "Persisted summary"

    class StubIPFSRouter:
        def add_bytes(self, data: bytes, **kwargs: object) -> str:
            payload = json.loads(data.decode("utf-8"))
            captured["payload"] = payload
            assert payload["capability_id"] == "github.pr.rag_summary"
            assert kwargs["pin"] is True
            return "bafy-summary"

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability(
        "github.pr.rag_summary",
        pr_number=123,
        persist_output=True,
        ipfs_options={"pin": True},
    )

    assert result.ok is True
    assert result.output["ipfs_cid"] == "bafy-summary"
    assert result.output["trace"]["ipfs_cid"] == "bafy-summary"
    assert captured["payload"]["metadata"]["profile"] == "default"
    assert captured["payload"]["metadata"]["pr_number"] == 123
    assert "created_at" in captured["payload"]["metadata"]


def test_execute_github_pr_accelerated_summary(monkeypatch):
    """Accelerated PR summaries should use ipfs_accelerate for synthesis."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [float(len(text)), float(kwargs["dimensions"])]

    class StubAccelerateAdapter:
        def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
            assert "pull request #123" in prompt
            return {"text": f"accelerated-summary:{kwargs['model']}"}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_accelerate_adapter",
        lambda: StubAccelerateAdapter(),
    )

    result = execute_ai_capability(
        "github.pr.accelerated_summary",
        pr_number=123,
        repo="openai/example",
        embedding_options={"dimensions": 256},
        generation_options={"model": "llama3"},
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["summary"] == "accelerated-summary:llama3"
    assert result.output["pr_number"] == 123
    assert (
        result.output["trace"]["steps"]["accelerate_generate"]["provider"]
        == AIBackendFamily.IPFS_ACCELERATE.value
    )


def test_execute_github_failure_rag_explain_can_persist_to_ipfs_via_env(monkeypatch):
    """Composite failure analysis should respect the IPFS persistence env flag."""
    monkeypatch.setenv("HANDSFREE_AI_PERSIST_OUTPUTS_TO_IPFS", "true")
    captured: dict[str, object] = {}

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [0.1]

    class StubLLMRouter:
        def generate_text(self, prompt: str, **kwargs: object) -> str:
            return "Persisted failure analysis"

    class StubIPFSRouter:
        def add_bytes(self, data: bytes, **kwargs: object) -> str:
            payload = json.loads(data.decode("utf-8"))
            captured["payload"] = payload
            assert payload["capability_id"] == "github.check.failure_rag_explain"
            return "bafy-failure"

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_llm_router",
        lambda: StubLLMRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability(
        "github.check.failure_rag_explain",
        pr_number=123,
    )

    assert result.ok is True
    assert result.output["ipfs_cid"] == "bafy-failure"


def test_execute_github_accelerated_failure_explain(monkeypatch):
    """Accelerated failure analysis should use ipfs_accelerate for synthesis."""

    class StubEmbeddingsRouter:
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            return [float(len(text)), float(kwargs["dimensions"])]

    class StubAccelerateAdapter:
        def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
            assert "CI Linux" in prompt
            return {"text": f"accelerated:{kwargs['model_name']}"}

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_embeddings_router",
        lambda: StubEmbeddingsRouter(),
    )
    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_accelerate_adapter",
        lambda: StubAccelerateAdapter(),
    )

    result = execute_ai_capability(
        "github.check.accelerated_failure_explain",
        pr_number=124,
        repo="openai/example",
        failure_target="CI Linux",
        failure_target_type="workflow",
        embedding_options={"dimensions": 256},
        generation_options={"model_name": "llama3"},
    )

    assert result.ok is True
    assert result.execution_mode == AIExecutionMode.ORCHESTRATED
    assert result.output["summary"] == "accelerated:llama3"
    assert result.output["failure_target"] == "CI Linux"
    assert (
        result.output["trace"]["steps"]["accelerate_generate"]["provider"]
        == AIBackendFamily.IPFS_ACCELERATE.value
    )


def test_execute_ipfs_read_ai_output(monkeypatch):
    """Stored AI outputs should be readable by CID."""

    class StubIPFSRouter:
        def cat(self, cid: str) -> bytes:
            assert cid == "bafy-summary"
            return (
                b'{"capability_id":"github.pr.rag_summary","payload":{"headline":"Stored summary",'
                b'"summary":"Recovered summary text.","repo":"openai/example"}}'
            )

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability("ipfs.content.read_ai_output", cid="bafy-summary")

    assert result.ok is True
    assert result.output["cid"] == "bafy-summary"
    assert result.output["stored_capability_id"] == "github.pr.rag_summary"
    assert result.output["headline"] == "Stored summary"
    assert result.output["metadata"] == {}
    assert "Recovered summary text" in result.output["spoken_text"]


def test_execute_ipfs_read_ai_output_exposes_persisted_metadata(monkeypatch):
    """Readback should surface persisted metadata when present."""

    class StubIPFSRouter:
        def cat(self, cid: str) -> bytes:
            return (
                b'{"capability_id":"github.check.failure_rag_explain",'
                b'"metadata":{"profile":"default","pr_number":124,"repo":"openai/example"},'
                b'"payload":{"headline":"Stored failure analysis","summary":"Recovered failure summary."}}'
            )

    monkeypatch.setattr(
        "handsfree.ai.capabilities.get_ipfs_router",
        lambda: StubIPFSRouter(),
    )

    result = execute_ai_capability("ipfs.content.read_ai_output", cid="bafy-failure")

    assert result.ok is True
    assert result.output["metadata"]["profile"] == "default"
    assert result.output["metadata"]["pr_number"] == 124
    assert result.output["metadata"]["repo"] == "openai/example"
