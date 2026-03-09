"""Optional adapters for endomorphosis/ipfs_kit_py.

Prefer canonical package modules over top-level shortcuts. The upstream package
has a broad surface area, so this adapter intentionally probes a small set of
validated import paths first and falls back to older top-level helpers only
when they are explicitly available.
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any, Callable, NoReturn, Protocol

logger = logging.getLogger(__name__)


class IPFSKitAdapter(Protocol):
    """Higher-level IPFS lifecycle interface."""

    def add_bytes(self, data: bytes, **kwargs: Any) -> Any:
        """Add bytes to IPFS and return content metadata."""
        ...

    def cat(self, cid: str, **kwargs: Any) -> Any:
        """Read bytes or text content by CID."""
        ...

    def pin(self, cid: str, **kwargs: Any) -> Any:
        """Pin content by CID."""
        ...

    def unpin(self, cid: str, **kwargs: Any) -> Any:
        """Unpin content by CID."""
        ...

    def resolve(self, cid: str, **kwargs: Any) -> Any:
        """Resolve content metadata by CID."""
        ...

    def package_dataset(self, items: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Package a content bundle or dataset manifest."""
        ...


class _UnavailableIPFSKitAdapter:
    def _raise(self, method: str) -> NoReturn:
        raise NotImplementedError(f"ipfs_kit_py.{method} is unavailable: install ipfs_kit_py")

    def add_bytes(self, data: bytes, **kwargs: Any) -> NoReturn:
        self._raise("add_bytes")

    def cat(self, cid: str, **kwargs: Any) -> NoReturn:
        self._raise("cat")

    def pin(self, cid: str, **kwargs: Any) -> NoReturn:
        self._raise("pin")

    def unpin(self, cid: str, **kwargs: Any) -> NoReturn:
        self._raise("unpin")

    def resolve(self, cid: str, **kwargs: Any) -> NoReturn:
        self._raise("resolve")

    def package_dataset(self, items: list[dict[str, Any]], **kwargs: Any) -> NoReturn:
        self._raise("package_dataset")


class _IPFSKitModuleAdapter:
    def __init__(self, root_module: Any) -> None:
        self._root_module = root_module

    def _resolve_callable(self, *targets: tuple[str, str]) -> Callable[..., Any]:
        for module_name, attr_name in targets:
            try:
                module = importlib.import_module(module_name)
                candidate = getattr(module, attr_name, None)
                if callable(candidate):
                    return candidate
            except Exception:
                continue
        raise NotImplementedError(
            "ipfs_kit_py callable is unavailable on the validated direct-import surface"
        )

    def _get_backend(self) -> Any:
        try:
            module = importlib.import_module("ipfs_kit_py.ipfs_backend")
            factory = getattr(module, "get_instance", None)
            if callable(factory):
                return factory()
        except Exception:
            pass
        raise NotImplementedError(
            "ipfs_kit_py.ipfs_backend.get_instance is unavailable"
        )

    def add_bytes(self, data: bytes, **kwargs: Any) -> Any:
        try:
            add_fn = self._resolve_callable(("ipfs_kit_py", "add_bytes"))
            return add_fn(data, **kwargs)
        except NotImplementedError:
            backend = self._get_backend()
            add_bytes = getattr(backend, "add_bytes", None)
            if callable(add_bytes):
                return add_bytes(data, **kwargs)
            add_str = getattr(backend, "add_str", None)
            if callable(add_str):
                return add_str(data.decode("utf-8", errors="replace"), **kwargs)
            raise NotImplementedError(
                "ipfs_kit_py add_bytes is not exposed through a stable direct-import seam yet"
            )

    def cat(self, cid: str, **kwargs: Any) -> Any:
        try:
            cat_fn = self._resolve_callable(("ipfs_kit_py", "cat"))
            return cat_fn(cid, **kwargs)
        except NotImplementedError:
            backend = self._get_backend()
            cat_fn = getattr(backend, "cat", None)
            if callable(cat_fn):
                return cat_fn(cid, **kwargs)
            raise NotImplementedError(
                "ipfs_kit_py cat is not exposed through a stable direct-import seam yet"
            )

    def pin(self, cid: str, **kwargs: Any) -> Any:
        try:
            pin_fn = self._resolve_callable(("ipfs_kit_py", "pin"))
            return pin_fn(cid, **kwargs)
        except NotImplementedError:
            backend = self._get_backend()
            return backend.pin_add(cid, **kwargs)

    def unpin(self, cid: str, **kwargs: Any) -> Any:
        try:
            unpin_fn = self._resolve_callable(("ipfs_kit_py", "unpin"))
            return unpin_fn(cid, **kwargs)
        except NotImplementedError:
            backend = self._get_backend()
            return backend.pin_rm(cid, **kwargs)

    def resolve(self, cid: str, **kwargs: Any) -> Any:
        try:
            resolve_fn = self._resolve_callable(("ipfs_kit_py", "resolve"))
            return resolve_fn(cid, **kwargs)
        except NotImplementedError:
            raise NotImplementedError(
                "ipfs_kit_py resolve is not exposed through a stable direct-import seam yet"
            )

    def package_dataset(self, items: list[dict[str, Any]], **kwargs: Any) -> Any:
        package_fn = getattr(self._root_module, "package_dataset", None)
        if callable(package_fn):
            return package_fn(items, **kwargs)
        raise NotImplementedError(
            "ipfs_kit_py package_dataset is not exposed through a stable direct-import seam yet"
        )


def _import_kit_module() -> Any | None:
    try:
        return importlib.import_module("ipfs_kit_py")
    except Exception as exc:
        logger.debug("Optional kit import failed for ipfs_kit_py: %s", exc)
        return None


@lru_cache(maxsize=1)
def get_ipfs_kit_adapter() -> IPFSKitAdapter:
    """Get an ipfs_kit_py adapter with safe fallback."""
    module = _import_kit_module()
    if module is None:
        return _UnavailableIPFSKitAdapter()
    return _IPFSKitModuleAdapter(module)


def reset_ipfs_kit_adapter_cache() -> None:
    """Reset cached kit adapter (primarily for tests)."""
    get_ipfs_kit_adapter.cache_clear()
