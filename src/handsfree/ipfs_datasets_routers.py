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


class IPFSDatasetsRouterUnavailableError(RuntimeError):
    """Raised when ipfs_datasets_py is missing or a router cannot be used."""


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
        raise IPFSDatasetsRouterUnavailableError(
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
    except ModuleNotFoundError as exc:
        root_package = module_name.partition(".")[0]
        if exc.name not in {root_package, module_name}:
            raise
        logger.debug(
            "Optional router module unavailable for %s: %s",
            module_name,
            exc,
        )
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
    get_datasets_router.cache_clear()


# --------------------------------------------------------------------------- #
# Extended: Dataset operations router (search, list, vector store)
# --------------------------------------------------------------------------- #


class DatasetsRouter(Protocol):
    """Dataset operations router interface (load, list, search)."""

    def list_datasets(self, **kwargs: Any) -> list[Any]:
        """List available datasets."""
        ...

    def load_dataset(self, name: str, **kwargs: Any) -> Any:
        """Load a dataset by name or CID."""
        ...

    def search_datasets(self, query: str, **kwargs: Any) -> list[Any]:
        """Search datasets by query."""
        ...


class _UnavailableDatasetsRouter(_UnavailableRouter):
    def __init__(self) -> None:
        super().__init__("datasets_router")

    def list_datasets(self, **kwargs: Any) -> NoReturn:
        self._raise("list_datasets")

    def load_dataset(self, name: str, **kwargs: Any) -> NoReturn:
        self._raise("load_dataset")

    def search_datasets(self, query: str, **kwargs: Any) -> NoReturn:
        self._raise("search_datasets")


class _DatasetsRouterAdapter:
    """Adapter wrapping the ipfs_datasets_py dataset tools."""

    def __init__(self, module: Any) -> None:
        self._module = module

    def list_datasets(self, **kwargs: Any) -> list[Any]:
        fn = getattr(self._module, "list_datasets", None)
        if callable(fn):
            return fn(**kwargs)
        # Fallback: try tool registry
        try:
            from ipfs_datasets_py.mcp_server.tool_registry import get_tool_registry
            registry = get_tool_registry()
            fn = registry.get("list_datasets")
            if callable(fn):
                return fn(**kwargs)
        except Exception:
            pass
        return []

    def load_dataset(self, name: str, **kwargs: Any) -> Any:
        fn = getattr(self._module, "load_dataset", None)
        if callable(fn):
            return fn(name, **kwargs)
        return {"name": name, "status": "not_loaded"}

    def search_datasets(self, query: str, **kwargs: Any) -> list[Any]:
        fn = getattr(self._module, "search_datasets", None) or getattr(
            self._module, "search", None
        )
        if callable(fn):
            return fn(query, **kwargs)
        return []


@lru_cache(maxsize=1)
def get_datasets_router() -> DatasetsRouter:
    """Get datasets operations router with safe fallback."""
    # Try multiple possible module paths
    for module_name in [
        "ipfs_datasets_py.datasets_router",
        "ipfs_datasets_py.mcp_server.tools.dataset_tools.dataset_tools",
        "ipfs_datasets_py.ipfs_datasets",
    ]:
        module = _import_router_module(module_name)
        if module is not None:
            return _DatasetsRouterAdapter(module)
    return _UnavailableDatasetsRouter()
