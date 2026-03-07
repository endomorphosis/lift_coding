"""Tests for optional ipfs_datasets_py router adapters."""

import sys
from types import ModuleType

import pytest

from handsfree.ipfs_datasets_routers import (
    get_embeddings_router,
    get_ipfs_router,
    get_llm_router,
    reset_ipfs_datasets_router_caches,
)


def test_fallback_embeddings_router_when_dependency_missing():
    """Embeddings router should safely fall back when optional dependency is missing."""
    sys.modules.pop("ipfs_datasets_py.embeddings_router", None)
    reset_ipfs_datasets_router_caches()

    router = get_embeddings_router()

    with pytest.raises(NotImplementedError, match="install ipfs_datasets_py"):
        router.embed_text("hello")


def test_fallback_ipfs_router_when_dependency_missing():
    """IPFS router should safely fall back when optional dependency is missing."""
    sys.modules.pop("ipfs_datasets_py.ipfs_backend_router", None)
    reset_ipfs_datasets_router_caches()

    router = get_ipfs_router()

    with pytest.raises(NotImplementedError, match="install ipfs_datasets_py"):
        router.add_bytes(b"hello")


def test_fallback_llm_router_when_dependency_missing():
    """LLM router should safely fall back when optional dependency is missing."""
    sys.modules.pop("ipfs_datasets_py.llm_router", None)
    reset_ipfs_datasets_router_caches()

    router = get_llm_router()

    with pytest.raises(NotImplementedError, match="install ipfs_datasets_py"):
        router.generate_text("hello")


def test_delegates_to_embeddings_router_module(monkeypatch):
    """Embeddings adapter should delegate to ipfs_datasets_py embeddings_router."""
    module = ModuleType("ipfs_datasets_py.embeddings_router")
    module.embed_text = lambda text, **kwargs: [0.1, float(len(text))]
    module.embed_texts = lambda texts, **kwargs: [[float(len(text))] for text in texts]

    monkeypatch.setitem(sys.modules, "ipfs_datasets_py.embeddings_router", module)
    reset_ipfs_datasets_router_caches()

    router = get_embeddings_router()

    assert router.embed_text("abc") == [0.1, 3.0]
    assert router.embed_texts(["a", "ab"]) == [[1.0], [2.0]]


def test_delegates_to_ipfs_backend_router_module(monkeypatch):
    """IPFS adapter should delegate to ipfs_datasets_py ipfs_backend_router."""
    module = ModuleType("ipfs_datasets_py.ipfs_backend_router")
    module.add_bytes = lambda data, **kwargs: f"cid-{len(data)}"
    module.cat = lambda cid: f"payload:{cid}".encode()

    monkeypatch.setitem(sys.modules, "ipfs_datasets_py.ipfs_backend_router", module)
    reset_ipfs_datasets_router_caches()

    router = get_ipfs_router()

    assert router.add_bytes(b"abcd") == "cid-4"
    assert router.cat("cid-4") == b"payload:cid-4"


def test_delegates_to_llm_router_module(monkeypatch):
    """LLM adapter should delegate to ipfs_datasets_py llm_router."""
    module = ModuleType("ipfs_datasets_py.llm_router")
    module.generate_text = lambda prompt, **kwargs: f"generated:{prompt}"

    monkeypatch.setitem(sys.modules, "ipfs_datasets_py.llm_router", module)
    reset_ipfs_datasets_router_caches()

    router = get_llm_router()

    assert router.generate_text("hello") == "generated:hello"
