"""Optional adapters for endomorphosis/ipfs_kit_py.

Prefer canonical package modules over top-level shortcuts. The upstream package
has a broad surface area, so this adapter intentionally probes a small set of
validated import paths first and falls back to older top-level helpers only
when they are explicitly available.
"""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any, NoReturn, Protocol

logger = logging.getLogger(__name__)
IPFS_KIT_CLI_COMMAND = "ipfs-kit"
PACKAGE_DATASET_MANIFEST_SCHEMA = "handsfree.ipfs_kit.package_dataset.v1"


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


class IPFSKitUnavailableError(RuntimeError):
    """Raised when ipfs_kit_py is missing or has no usable adapter surface."""


class _UnavailableIPFSKitAdapter:
    def _raise(self, method: str) -> NoReturn:
        raise IPFSKitUnavailableError(
            f"ipfs_kit_py.{method} is unavailable: install ipfs_kit_py"
        )

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

    def _resolve_backend_callable(
        self,
        backend: Any,
        *paths: tuple[str, ...],
    ) -> Callable[..., Any] | None:
        for root in (backend, getattr(backend, "client", None)):
            if root is None:
                continue
            for path in paths:
                candidate = root
                for attr_name in path:
                    candidate = getattr(candidate, attr_name, None)
                    if candidate is None:
                        break
                if callable(candidate):
                    return candidate
        return None

    def _resolve_callable(self, *targets: tuple[str, str]) -> Callable[..., Any] | None:
        for module_name, attr_name in targets:
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError as exc:
                root_package = module_name.partition(".")[0]
                if exc.name not in {root_package, module_name}:
                    raise
                logger.debug(
                    "Optional kit callable module unavailable for %s.%s: %s",
                    module_name,
                    attr_name,
                    exc,
                )
                continue
            candidate = getattr(module, attr_name, None)
            if callable(candidate):
                return candidate
        return None

    def _get_backend(self) -> Any:
        module_name = "ipfs_kit_py.ipfs_backend"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name not in {"ipfs_kit_py", module_name}:
                raise
            logger.debug("Optional kit backend unavailable for %s: %s", module_name, exc)
        else:
            factory = getattr(module, "get_instance", None)
            if callable(factory):
                return factory()
        raise IPFSKitUnavailableError(
            "ipfs_kit_py.ipfs_backend.get_instance is unavailable"
        )

    def _get_high_level_api(self) -> Any | None:
        api_factory = self._resolve_callable(
            ("ipfs_kit_py.high_level_api", "IPFSSimpleAPI")
        )
        if api_factory is None:
            return None
        api = api_factory()
        if getattr(api, "available", True) is False:
            logger.debug("Optional kit high-level API is unavailable")
            return None
        return api

    def _dataset_manifest(
        self,
        items: list[dict[str, Any]],
        metadata: Any | None,
    ) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "schema": PACKAGE_DATASET_MANIFEST_SCHEMA,
            "items": items,
        }
        if metadata is not None:
            manifest["metadata"] = metadata
        return manifest

    def _store_dataset_manifest(
        self,
        target: Any,
        manifest: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        add_json = getattr(target, "add_json", None)
        if callable(add_json):
            return add_json(manifest, **kwargs)

        payload = json.dumps(
            manifest,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        add_bytes = getattr(target, "add_bytes", None)
        if callable(add_bytes):
            return add_bytes(payload.encode("utf-8"), **kwargs)

        add_str = getattr(target, "add_str", None)
        if callable(add_str):
            return add_str(payload, **kwargs)

        add = getattr(target, "add", None)
        if callable(add):
            return add(payload.encode("utf-8"), **kwargs)

        return None

    def add_bytes(self, data: bytes, **kwargs: Any) -> Any:
        add_fn = self._resolve_callable(("ipfs_kit_py", "add_bytes"))
        try:
            if add_fn is not None:
                return add_fn(data, **kwargs)
        except NotImplementedError as exc:
            logger.debug("ipfs_kit_py.add_bytes direct callable unavailable: %s", exc)
        backend = self._get_backend()
        add_bytes = getattr(backend, "add_bytes", None)
        if callable(add_bytes):
            return add_bytes(data, **kwargs)
        add_str = getattr(backend, "add_str", None)
        if callable(add_str):
            return add_str(data.decode("utf-8", errors="replace"), **kwargs)
        raise IPFSKitUnavailableError(
            "ipfs_kit_py add_bytes is unavailable: backend exposes neither "
            "add_bytes nor add_str"
        )

    def cat(self, cid: str, **kwargs: Any) -> Any:
        cat_fn = self._resolve_callable(("ipfs_kit_py", "cat"))
        try:
            if cat_fn is not None:
                return cat_fn(cid, **kwargs)
        except NotImplementedError as exc:
            logger.debug("ipfs_kit_py.cat direct callable unavailable: %s", exc)
        backend = self._get_backend()
        cat_fn = getattr(backend, "cat", None)
        if callable(cat_fn):
            return cat_fn(cid, **kwargs)
        get_fn = getattr(backend, "get", None)
        if callable(get_fn):
            return get_fn(cid, **kwargs)
        raise IPFSKitUnavailableError(
            "ipfs_kit_py cat is unavailable: backend exposes neither cat nor get"
        )

    def pin(self, cid: str, **kwargs: Any) -> Any:
        pin_fn = self._resolve_callable(("ipfs_kit_py", "pin"))
        try:
            if pin_fn is not None:
                return pin_fn(cid, **kwargs)
        except NotImplementedError as exc:
            logger.debug("ipfs_kit_py.pin direct callable unavailable: %s", exc)
        backend = self._get_backend()
        return backend.pin_add(cid, **kwargs)

    def unpin(self, cid: str, **kwargs: Any) -> Any:
        unpin_fn = self._resolve_callable(("ipfs_kit_py", "unpin"))
        try:
            if unpin_fn is not None:
                return unpin_fn(cid, **kwargs)
        except NotImplementedError as exc:
            logger.debug("ipfs_kit_py.unpin direct callable unavailable: %s", exc)
        backend = self._get_backend()
        return backend.pin_rm(cid, **kwargs)

    def resolve(self, cid: str, **kwargs: Any) -> Any:
        resolve_fn = self._resolve_callable(("ipfs_kit_py", "resolve"))
        try:
            if resolve_fn is not None:
                return resolve_fn(cid, **kwargs)
        except NotImplementedError as exc:
            logger.debug("ipfs_kit_py.resolve direct callable unavailable: %s", exc)
        try:
            backend = self._get_backend()
        except IPFSKitUnavailableError as exc:
            logger.debug("ipfs_kit_py resolve backend unavailable: %s", exc)
        else:
            backend_resolve = self._resolve_backend_callable(
                backend,
                ("resolve",),
                ("dag_resolve",),
                ("ipfs_dag_resolve",),
                ("ipfs_object_stat",),
                ("object_stat",),
                ("object", "stat"),
                ("dag_get",),
                ("ipfs_dag_get",),
                ("dag", "get"),
                ("name_resolve",),
                ("ipfs_name_resolve",),
                ("name", "resolve"),
            )
            if backend_resolve is not None:
                return backend_resolve(cid, **kwargs)
        try:
            simple_api = self._get_simple_api()
        except IPFSKitUnavailableError as exc:
            raise IPFSKitUnavailableError(
                "ipfs_kit_py resolve is unavailable: backend exposes no CID, DAG, "
                "or name resolver, and IPFSSimpleAPI is unavailable"
            ) from exc
        simple_resolve = getattr(simple_api, "resolve", None)
        if callable(simple_resolve):
            return simple_resolve(cid, **kwargs)
        raise IPFSKitUnavailableError(
            "ipfs_kit_py resolve is unavailable: backend exposes no CID, DAG, "
            "or name resolver, and IPFSSimpleAPI exposes no resolve"
        )

    def _get_simple_api(self) -> Any:
        module_name = "ipfs_kit_py.high_level_api"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name not in {"ipfs_kit_py", module_name}:
                raise
            logger.debug(
                "Optional kit high-level API unavailable for %s: %s",
                module_name,
                exc,
            )
        else:
            factory = getattr(module, "IPFSSimpleAPI", None)
            if callable(factory):
                return factory()
        raise IPFSKitUnavailableError(
            "ipfs_kit_py.high_level_api.IPFSSimpleAPI is unavailable"
        )

    def package_dataset(self, items: list[dict[str, Any]], **kwargs: Any) -> Any:
        package_fn = getattr(self._root_module, "package_dataset", None)
        try:
            if callable(package_fn):
                return package_fn(items, **kwargs)
        except NotImplementedError as exc:
            logger.debug(
                "ipfs_kit_py.package_dataset direct callable unavailable: %s",
                exc,
            )

        storage_options = dict(kwargs)
        metadata = storage_options.pop("metadata", None)
        manifest = self._dataset_manifest(items, metadata)

        api = self._get_high_level_api()
        if api is not None:
            api_package_fn = getattr(api, "package_dataset", None)
            try:
                if callable(api_package_fn):
                    return api_package_fn(items, **kwargs)
            except NotImplementedError as exc:
                logger.debug(
                    "ipfs_kit_py.high_level_api.package_dataset unavailable: %s",
                    exc,
                )
            result = self._store_dataset_manifest(api, manifest, **storage_options)
            if result is not None:
                return result

        backend = self._get_backend()
        backend_package_fn = getattr(backend, "package_dataset", None)
        if callable(backend_package_fn):
            return backend_package_fn(items, **kwargs)
        result = self._store_dataset_manifest(backend, manifest, **storage_options)
        if result is not None:
            return result
        raise IPFSKitUnavailableError(
            "ipfs_kit_py package_dataset is unavailable: backend exposes neither "
            "package_dataset, add_json, add_bytes, add_str nor add"
        )


def _import_kit_module() -> Any | None:
    module_name = "ipfs_kit_py"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        logger.debug("Optional kit root package unavailable for %s: %s", module_name, exc)
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


def get_ipfs_kit_cli_command() -> str:
    """Return the validated CLI command name for local IPFS Kit execution."""
    return IPFS_KIT_CLI_COMMAND
