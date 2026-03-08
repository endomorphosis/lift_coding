"""Adapters for ipfs_datasets_py router modules.

Provides lazy, optional integration with:
- ipfs_datasets_py.embeddings_router
- ipfs_datasets_py.ipfs_backend_router (ipfs_router compatibility)
- ipfs_datasets_py.llm_router

When ipfs_datasets_py is unavailable, safe fallback stubs are returned.
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any, NoReturn, Protocol

logger = logging.getLogger(__name__)


class EmbeddingsRouter(Protocol):
    """Embeddings router interface."""

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        """Return embedding vector for one text."""
        ...

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Return embedding vectors for multiple texts."""
        ...


class IPFSRouter(Protocol):
    """IPFS router interface."""

    def add_bytes(self, data: bytes, **kwargs: Any) -> str:
        """Store bytes and return CID."""
        ...

    def cat(self, cid: str) -> bytes:
        """Load bytes from CID."""
        ...


class LLMRouter(Protocol):
    """LLM router interface."""

    def generate_text(self, prompt: str, **kwargs: Any) -> str:
        """Generate text for prompt."""
        ...


class _UnavailableRouter:
    def __init__(self, router_name: str) -> None:
        self._router_name = router_name

    def _raise(self, method: str) -> NoReturn:
        raise NotImplementedError(
            f"{self._router_name}.{method} is unavailable: install ipfs_datasets_py"
        )


class _UnavailableEmbeddingsRouter(_UnavailableRouter):
    def __init__(self) -> None:
        super().__init__("embeddings_router")

    def embed_text(self, text: str, **kwargs: Any) -> NoReturn:
        self._raise("embed_text")

    def embed_texts(self, texts: list[str], **kwargs: Any) -> NoReturn:
        self._raise("embed_texts")


class _UnavailableIPFSRouter(_UnavailableRouter):
    def __init__(self) -> None:
        super().__init__("ipfs_router")

    def add_bytes(self, data: bytes, **kwargs: Any) -> NoReturn:
        self._raise("add_bytes")

    def cat(self, cid: str) -> NoReturn:
        self._raise("cat")


class _UnavailableLLMRouter(_UnavailableRouter):
    def __init__(self) -> None:
        super().__init__("llm_router")

    def generate_text(self, prompt: str, **kwargs: Any) -> NoReturn:
        self._raise("generate_text")


class _EmbeddingsRouterAdapter:
    def __init__(self, module: Any) -> None:
        self._module = module

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self._module.embed_text(text, **kwargs)

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return self._module.embed_texts(texts, **kwargs)


class _IPFSRouterAdapter:
    def __init__(self, module: Any) -> None:
        self._module = module

    def add_bytes(self, data: bytes, **kwargs: Any) -> str:
        return self._module.add_bytes(data, **kwargs)

    def cat(self, cid: str) -> bytes:
        return self._module.cat(cid)


class _LLMRouterAdapter:
    def __init__(self, module: Any) -> None:
        self._module = module

    def generate_text(self, prompt: str, **kwargs: Any) -> str:
        return self._module.generate_text(prompt, **kwargs)


def _import_router_module(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        logger.debug("Optional router import failed for %s: %s", module_name, exc)
        return None


@lru_cache(maxsize=1)
def get_embeddings_router() -> EmbeddingsRouter:
    """Get embeddings router adapter with safe fallback."""
    module = _import_router_module("ipfs_datasets_py.embeddings_router")
    if module is None:
        return _UnavailableEmbeddingsRouter()
    return _EmbeddingsRouterAdapter(module)


@lru_cache(maxsize=1)
def get_ipfs_router() -> IPFSRouter:
    """Get IPFS router adapter with safe fallback.

    Uses ipfs_backend_router from ipfs_datasets_py as the IPFS router source.
    """
    module = _import_router_module("ipfs_datasets_py.ipfs_backend_router")
    if module is None:
        return _UnavailableIPFSRouter()
    return _IPFSRouterAdapter(module)


@lru_cache(maxsize=1)
def get_llm_router() -> LLMRouter:
    """Get LLM router adapter with safe fallback."""
    module = _import_router_module("ipfs_datasets_py.llm_router")
    if module is None:
        return _UnavailableLLMRouter()
    return _LLMRouterAdapter(module)


def reset_ipfs_datasets_router_caches() -> None:
    """Reset cached router adapters (primarily for tests)."""
    get_embeddings_router.cache_clear()
    get_ipfs_router.cache_clear()
    get_llm_router.cache_clear()
