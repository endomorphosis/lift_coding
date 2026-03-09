"""Optional adapters for endomorphosis/ipfs_accelerate_py.

The upstream package exposes stable package families and CLI entry points, but
its direct-import API is not concentrated on the top-level package. Prefer the
canonical router modules first and only fall back to top-level helpers for
compatibility with local mocks or older layouts.
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any, Callable, NoReturn, Protocol

logger = logging.getLogger(__name__)


class IPFSAccelerateAdapter(Protocol):
    """Acceleration-aware execution interface."""

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        """Run an accelerated generation workflow."""
        ...

    def embed(self, texts: list[str], **kwargs: Any) -> Any:
        """Run an accelerated embedding workflow."""
        ...


class _UnavailableIPFSAccelerateAdapter:
    def _raise(self, method: str) -> NoReturn:
        raise NotImplementedError(
            f"ipfs_accelerate_py.{method} is unavailable: install ipfs_accelerate_py"
        )

    def generate(self, prompt: str, **kwargs: Any) -> NoReturn:
        self._raise("generate")

    def embed(self, texts: list[str], **kwargs: Any) -> NoReturn:
        self._raise("embed")


class _IPFSAccelerateModuleAdapter:
    def __init__(self, root_module: Any) -> None:
        self._root_module = root_module

    def _resolve(self, *targets: tuple[str, str]) -> Callable[..., Any]:
        for module_name, attr_name in targets:
            try:
                module = importlib.import_module(module_name)
                candidate = getattr(module, attr_name, None)
                if callable(candidate):
                    return candidate
            except Exception:
                continue

        raise NotImplementedError(
            "ipfs_accelerate_py canonical direct-import surface is unavailable. "
            "Expected one of: "
            "`ipfs_accelerate_py.llm_router.generate_text`, "
            "`ipfs_accelerate_py.embeddings_router.embed_texts`, "
            "or compatible top-level helpers."
        )

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        generate_fn = self._resolve(
            ("ipfs_accelerate_py.llm_router", "generate_text"),
            ("ipfs_accelerate_py", "generate"),
        )
        return generate_fn(prompt, **kwargs)

    def embed(self, texts: list[str], **kwargs: Any) -> Any:
        embed_fn = self._resolve(
            ("ipfs_accelerate_py.embeddings_router", "embed_texts"),
            ("ipfs_accelerate_py", "embed"),
        )
        return embed_fn(texts, **kwargs)


def _import_accelerate_module() -> Any | None:
    try:
        return importlib.import_module("ipfs_accelerate_py")
    except Exception as exc:
        logger.debug("Optional accelerate import failed for ipfs_accelerate_py: %s", exc)
        return None


@lru_cache(maxsize=1)
def get_ipfs_accelerate_adapter() -> IPFSAccelerateAdapter:
    """Get an ipfs_accelerate_py adapter with safe fallback."""
    module = _import_accelerate_module()
    if module is None:
        return _UnavailableIPFSAccelerateAdapter()
    return _IPFSAccelerateModuleAdapter(module)


def reset_ipfs_accelerate_adapter_cache() -> None:
    """Reset cached accelerate adapter (primarily for tests)."""
    get_ipfs_accelerate_adapter.cache_clear()
