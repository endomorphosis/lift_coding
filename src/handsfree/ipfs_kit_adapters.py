"""Optional adapters for endomorphosis/ipfs_kit_py.

The upstream package exposes its main class at ``ipfs_kit_py.ipfs_kit.ipfs_kit``
with methods like ``.ipfs_add()``, ``.ipfs_cat()``, ``.ipfs_pin_add()``, and
``.ipfs_pin_rm()``.  Backend configuration is via
``ipfs_kit_py.backend_config.initialize_backend_config()`` and
``get_backend_statuses()``.

This adapter wraps those real interfaces behind a stable protocol so the rest of
the handsfree codebase can call IPFS operations without caring whether ipfs_kit_py
is installed.
"""

from __future__ import annotations

import importlib
import json
import logging
import tempfile
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
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

    def get_backend_statuses(self) -> dict[str, Any]:
        """Return current backend availability/health map."""
        ...

    # Extended methods matching actual ipfs_kit_py MCP server tools
    def list_pins(self, **kwargs: Any) -> Any:
        """List all pinned CIDs."""
        ...

    def stat(self, cid: str, **kwargs: Any) -> Any:
        """Get object statistics for a CID."""
        ...

    def dag_get(self, cid: str, **kwargs: Any) -> Any:
        """Get a DAG node by CID."""
        ...

    def dag_put(self, data: Any, **kwargs: Any) -> Any:
        """Store a DAG node, return CID."""
        ...

    def name_publish(self, cid: str, **kwargs: Any) -> Any:
        """Publish CID to IPNS."""
        ...

    def name_resolve(self, name: str, **kwargs: Any) -> Any:
        """Resolve an IPNS name to CID."""
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

    def get_backend_statuses(self) -> dict[str, Any]:
        return {}


class _IPFSKitModuleAdapter:
    """Adapter that wraps the real ipfs_kit_py.ipfs_kit.ipfs_kit class."""

    def __init__(self, root_module: Any) -> None:
        self._root_module = root_module
        self._kit_instance: Any | None = None

    def _get_kit_instance(self) -> Any:
        """Get or create the ipfs_kit singleton (leecher role, no auto-start)."""
        if self._kit_instance is not None:
            return self._kit_instance

        # Try ipfs_kit_py.ipfs_kit.ipfs_kit.create() first
        try:
            kit_module = importlib.import_module("ipfs_kit_py.ipfs_kit")
            kit_cls = getattr(kit_module, "ipfs_kit", None)
            if kit_cls is not None:
                self._kit_instance = kit_cls.create(
                    role="leecher", auto_start_daemons=False
                )
                return self._kit_instance
        except Exception as exc:
            logger.debug("ipfs_kit_py.ipfs_kit.ipfs_kit.create() failed: %s", exc)

        # Fallback: try instantiation with metadata dict
        try:
            kit_module = importlib.import_module("ipfs_kit_py.ipfs_kit")
            kit_cls = getattr(kit_module, "ipfs_kit", None)
            if kit_cls is not None:
                self._kit_instance = kit_cls(metadata={"role": "leecher"})
                return self._kit_instance
        except Exception as exc:
            logger.debug("ipfs_kit_py.ipfs_kit.ipfs_kit() fallback failed: %s", exc)

        raise IPFSKitUnavailableError(
            "ipfs_kit_py.ipfs_kit.ipfs_kit is unavailable or failed to initialize"
        )

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

    def add_bytes(self, data: bytes, **kwargs: Any) -> Any:
        """Write bytes to a temp file and call ipfs_add on the kit instance."""
        kit = self._get_kit_instance()

        # The real API is ipfs_add(file_path) - write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(data)
            tmp_path = f.name

        try:
            result = kit.ipfs_add(tmp_path, **kwargs)
            return result
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    def cat(self, cid: str, **kwargs: Any) -> Any:
        """Read content by CID via ipfs_cat."""
        kit = self._get_kit_instance()
        return kit.ipfs_cat(cid, **kwargs)

    def pin(self, cid: str, **kwargs: Any) -> Any:
        """Pin content by CID."""
        kit = self._get_kit_instance()
        return kit.ipfs_pin_add(cid, **kwargs)

    def unpin(self, cid: str, **kwargs: Any) -> Any:
        """Unpin content by CID."""
        kit = self._get_kit_instance()
        return kit.ipfs_pin_rm(cid, **kwargs)

    def resolve(self, cid: str, **kwargs: Any) -> Any:
        """Resolve CID metadata. Falls back to ipfs_cat if no dedicated resolver."""
        kit = self._get_kit_instance()

        # Try dedicated resolve methods
        for method_name in ("ipfs_resolve", "ipfs_dag_get", "ipfs_object_stat"):
            resolver = getattr(kit, method_name, None)
            if callable(resolver):
                try:
                    return resolver(cid, **kwargs)
                except Exception:
                    continue

        # Fallback: return basic metadata from cat
        try:
            content = kit.ipfs_cat(cid, **kwargs)
            return {"cid": cid, "size": len(content) if content else 0}
        except Exception as exc:
            raise IPFSKitUnavailableError(
                f"ipfs_kit_py resolve failed for CID {cid}: {exc}"
            ) from exc

    def package_dataset(self, items: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Package a dataset manifest and store it via IPFS add."""
        storage_options = dict(kwargs)
        metadata = storage_options.pop("metadata", None)
        manifest = self._dataset_manifest(items, metadata)

        payload = json.dumps(
            manifest,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return self.add_bytes(payload, **storage_options)

    def get_backend_statuses(self) -> dict[str, Any]:
        """Return backend health from ipfs_kit_py.backend_config."""
        try:
            backend_config = importlib.import_module("ipfs_kit_py.backend_config")
            get_statuses = getattr(backend_config, "get_backend_statuses", None)
            if callable(get_statuses):
                return get_statuses()
        except Exception as exc:
            logger.debug("ipfs_kit_py.backend_config.get_backend_statuses failed: %s", exc)
        return {}

    def list_pins(self, **kwargs: Any) -> Any:
        """List all pinned CIDs."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_pin_ls", None) or getattr(kit, "ipfs_pin_list", None)
        if callable(fn):
            return fn(**kwargs)
        return {"pins": []}

    def stat(self, cid: str, **kwargs: Any) -> Any:
        """Get object statistics for a CID."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_object_stat", None) or getattr(kit, "ipfs_stat", None)
        if callable(fn):
            return fn(cid, **kwargs)
        return {"cid": cid, "stat": None}

    def dag_get(self, cid: str, **kwargs: Any) -> Any:
        """Get a DAG node by CID."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_dag_get", None)
        if callable(fn):
            return fn(cid, **kwargs)
        return {"cid": cid, "dag": None}

    def dag_put(self, data: Any, **kwargs: Any) -> Any:
        """Store a DAG node, return CID."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_dag_put", None)
        if callable(fn):
            return fn(data, **kwargs)
        raise IPFSKitUnavailableError("ipfs_dag_put not available on kit instance")

    def name_publish(self, cid: str, **kwargs: Any) -> Any:
        """Publish CID to IPNS."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_name_publish", None)
        if callable(fn):
            return fn(cid, **kwargs)
        raise IPFSKitUnavailableError("ipfs_name_publish not available on kit instance")

    def name_resolve(self, name: str, **kwargs: Any) -> Any:
        """Resolve an IPNS name to CID."""
        kit = self._get_kit_instance()
        fn = getattr(kit, "ipfs_name_resolve", None)
        if callable(fn):
            return fn(name, **kwargs)
        raise IPFSKitUnavailableError("ipfs_name_resolve not available on kit instance")


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
