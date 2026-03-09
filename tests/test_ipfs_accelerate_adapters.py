"""Tests for optional ipfs_accelerate_py adapters."""

import sys
from types import ModuleType

import pytest

from handsfree.ipfs_accelerate_adapters import (
    get_ipfs_accelerate_adapter,
    reset_ipfs_accelerate_adapter_cache,
)


def test_fallback_accelerate_adapter_when_dependency_missing():
    """Accelerate adapter should safely fall back when optional dependency is missing."""
    sys.modules.pop("ipfs_accelerate_py", None)
    reset_ipfs_accelerate_adapter_cache()

    adapter = get_ipfs_accelerate_adapter()

    with pytest.raises(NotImplementedError, match="install ipfs_accelerate_py"):
        adapter.generate("hello")


def test_delegates_to_canonical_accelerate_modules(monkeypatch):
    """Accelerate adapter should prefer canonical upstream router modules."""
    root_module = ModuleType("ipfs_accelerate_py")
    llm_router = ModuleType("ipfs_accelerate_py.llm_router")
    embeddings_router = ModuleType("ipfs_accelerate_py.embeddings_router")

    def generate_text(prompt, **kwargs):
        return {"text": f"generated:{prompt}", "options": kwargs}

    def embed_texts(texts, **kwargs):
        return [[float(len(text))] for text in texts]

    llm_router.generate_text = generate_text
    embeddings_router.embed_texts = embed_texts

    monkeypatch.setitem(sys.modules, "ipfs_accelerate_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_accelerate_py.llm_router", llm_router)
    monkeypatch.setitem(sys.modules, "ipfs_accelerate_py.embeddings_router", embeddings_router)
    reset_ipfs_accelerate_adapter_cache()

    adapter = get_ipfs_accelerate_adapter()

    assert adapter.generate("hello") == {"text": "generated:hello", "options": {}}
    assert adapter.embed(["a", "ab"]) == [[1.0], [2.0]]


def test_delegates_to_legacy_top_level_helpers(monkeypatch):
    """Accelerate adapter should keep compatibility with top-level helper mocks."""
    module = ModuleType("ipfs_accelerate_py")

    def generate(prompt, **kwargs):
        return {"text": f"legacy:{prompt}", "options": kwargs}

    def embed(texts, **kwargs):
        return {"vectors": [[float(len(text))] for text in texts], "options": kwargs}

    module.generate = generate
    module.embed = embed

    monkeypatch.setitem(sys.modules, "ipfs_accelerate_py", module)
    reset_ipfs_accelerate_adapter_cache()

    adapter = get_ipfs_accelerate_adapter()

    assert adapter.generate("hello") == {"text": "legacy:hello", "options": {}}
    assert adapter.embed(["a", "ab"]) == {
        "vectors": [[1.0], [2.0]],
        "options": {},
    }
