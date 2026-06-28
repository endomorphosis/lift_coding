"""Optional adapters for endomorphosis/ipfs_accelerate_py.

The upstream package (v0.4.0) exposes:
- Main class: ``ipfs_accelerate_py.ipfs_accelerate.ipfs_accelerate_py``
  with ``.run_model()``, ``.infer()``, ``.get_capabilities()``, ``.call_tool()``
- Router: ``ipfs_accelerate_py.llm_router.generate_text(prompt, *, model_name, provider)``
- Embeddings: ``ipfs_accelerate_py.embed_texts``, ``ipfs_accelerate_py.embed_text``
- Singleton: ``ipfs_accelerate_py.get_instance(**kwargs)``

This adapter provides a stable interface for the handsfree backend.
"""

from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from typing import Any, Callable, NoReturn, Protocol

logger = logging.getLogger(__name__)
IPFS_ACCELERATE_CLI_COMMAND = "ipfs-accelerate"


class IPFSAccelerateAdapter(Protocol):
    """Acceleration-aware execution interface."""

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        """Run an accelerated generation workflow."""
        ...

    def embed(self, texts: list[str], **kwargs: Any) -> Any:
        """Run an accelerated embedding workflow."""
        ...

    def get_capabilities(self, **kwargs: Any) -> Any:
        """Return available hardware/model capabilities."""
        ...

    def run_model(self, model_name: str, inputs: Any, **kwargs: Any) -> Any:
        """Run inference on a specific model."""
        ...

    def status(self) -> dict[str, Any]:
        """Return runtime status including available backends."""
        ...

    # Extended methods matching actual MCP tool registrations
    def get_hardware_info(self, **kwargs: Any) -> Any:
        """Detailed hardware inventory (GPU, VRAM, compute capability)."""
        ...

    def search_models(self, query: str, **kwargs: Any) -> Any:
        """Search available models by query string."""
        ...

    def get_model_details(self, model_name: str, **kwargs: Any) -> Any:
        """Get detailed info about a specific model."""
        ...

    def list_models(self, **kwargs: Any) -> Any:
        """List all loaded/available models."""
        ...

    def get_endpoints(self, **kwargs: Any) -> Any:
        """List configured inference endpoints."""
        ...

    def get_performance_metrics(self, **kwargs: Any) -> Any:
        """Get server performance/telemetry metrics."""
        ...


class IPFSAccelerateUnavailableError(RuntimeError):
    """Raised when ipfs_accelerate_py is missing or has no usable adapter surface."""


class _UnavailableIPFSAccelerateAdapter:
    def _raise(self, method: str) -> NoReturn:
        raise IPFSAccelerateUnavailableError(
            f"ipfs_accelerate_py.{method} is unavailable: install ipfs_accelerate_py"
        )

    def generate(self, prompt: str, **kwargs: Any) -> NoReturn:
        self._raise("generate")

    def embed(self, texts: list[str], **kwargs: Any) -> NoReturn:
        self._raise("embed")

    def get_capabilities(self, **kwargs: Any) -> NoReturn:
        self._raise("get_capabilities")

    def run_model(self, model_name: str, inputs: Any, **kwargs: Any) -> NoReturn:
        self._raise("run_model")

    def status(self) -> dict[str, Any]:
        return {"available": False, "error": "ipfs_accelerate_py not installed"}


class _IPFSAccelerateModuleAdapter:
    def __init__(self, root_module: Any) -> None:
        self._root_module = root_module
        self._instance: Any | None = None

    def _get_instance(self) -> Any | None:
        """Get the singleton ipfs_accelerate_py instance."""
        if self._instance is not None:
            return self._instance

        get_inst = getattr(self._root_module, "get_instance", None)
        if callable(get_inst):
            try:
                self._instance = get_inst()
                return self._instance
            except Exception as exc:
                logger.debug("ipfs_accelerate_py.get_instance() failed: %s", exc)
        return None

    def _resolve(self, *targets: tuple[str, str]) -> Callable[..., Any]:
        for module_name, attr_name in targets:
            try:
                module = importlib.import_module(module_name)
                candidate = getattr(module, attr_name, None)
                if callable(candidate):
                    return candidate
            except Exception:
                continue

        raise IPFSAccelerateUnavailableError(
            "ipfs_accelerate_py canonical direct-import surface is unavailable. "
            "Expected one of: "
            "`ipfs_accelerate_py.llm_router.generate_text`, "
            "`ipfs_accelerate_py.embeddings_router.embed_texts`, "
            "or compatible top-level helpers."
        )

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        generate_fn = self._resolve(
            ("ipfs_accelerate_py.llm_router", "generate_text"),
            ("ipfs_accelerate_py", "generate_text"),
        )
        return generate_fn(prompt, **kwargs)

    def embed(self, texts: list[str], **kwargs: Any) -> Any:
        embed_fn = self._resolve(
            ("ipfs_accelerate_py.embeddings_router", "embed_texts"),
            ("ipfs_accelerate_py", "embed_texts"),
        )
        return embed_fn(texts, **kwargs)

    def get_capabilities(self, **kwargs: Any) -> Any:
        instance = self._get_instance()
        if instance is not None:
            get_caps = getattr(instance, "get_capabilities", None)
            if callable(get_caps):
                return get_caps(**kwargs)

        # Fallback: check top-level export
        get_caps = getattr(self._root_module, "get_capabilities", None)
        if callable(get_caps):
            return get_caps(**kwargs)

        return {
            "available": True,
            "webnn_webgpu_available": getattr(
                self._root_module, "webnn_webgpu_available", False
            ),
            "model_manager_available": getattr(
                self._root_module, "model_manager_available", False
            ),
            "llm_router_available": getattr(
                self._root_module, "llm_router_available", False
            ),
            "embeddings_router_available": getattr(
                self._root_module, "embeddings_router_available", False
            ),
        }

    def run_model(self, model_name: str, inputs: Any, **kwargs: Any) -> Any:
        instance = self._get_instance()
        if instance is not None:
            run_fn = getattr(instance, "run_model", None)
            if callable(run_fn):
                return run_fn(model_name, inputs, **kwargs)

        raise IPFSAccelerateUnavailableError(
            "ipfs_accelerate_py.run_model requires an initialized instance"
        )

    def status(self) -> dict[str, Any]:
        result: dict[str, Any] = {"available": True}
        instance = self._get_instance()
        if instance is not None:
            status_fn = getattr(instance, "status", None)
            if callable(status_fn):
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result["instance_status"] = "async_status_available"
                    else:
                        result["instance_status"] = loop.run_until_complete(status_fn())
                except Exception as exc:
                    result["instance_status_error"] = str(exc)
        result["webnn_webgpu_available"] = getattr(
            self._root_module, "webnn_webgpu_available", False
        )
        result["llm_router_available"] = getattr(
            self._root_module, "llm_router_available", False
        )
        result["embeddings_router_available"] = getattr(
            self._root_module, "embeddings_router_available", False
        )
        return result

    def get_hardware_info(self, **kwargs: Any) -> Any:
        """Detailed hardware inventory from MCP hardware tools."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "get_hardware_info", None)
            if callable(fn):
                return fn(**kwargs)
        # Fallback: derive from capabilities
        caps = self.get_capabilities(**kwargs)
        return {
            "gpu": caps.get("gpu") or caps.get("device"),
            "vram": caps.get("vram") or caps.get("memory"),
            "compute_capability": caps.get("compute_capability"),
            "cpu_count": caps.get("cpu_count"),
            "backends": caps.get("backends") or caps.get("supported_backends") or [],
            "quantization_formats": caps.get("quantization_formats") or [],
            "platform": caps.get("platform"),
        }

    def search_models(self, query: str, **kwargs: Any) -> Any:
        """Search models via MCP model tools."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "search_models", None)
            if callable(fn):
                return fn(query, **kwargs)
        # Try direct module function
        try:
            mod = importlib.import_module("ipfs_accelerate_py.mcp.tools.models")
            fn = getattr(mod, "search_models", None)
            if callable(fn):
                return fn(query=query, **kwargs)
        except Exception:
            pass
        return {"models": [], "query": query}

    def get_model_details(self, model_name: str, **kwargs: Any) -> Any:
        """Get model details via MCP model tools."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "get_model_details", None)
            if callable(fn):
                return fn(model_name, **kwargs)
        return {"model_name": model_name, "details": None}

    def list_models(self, **kwargs: Any) -> Any:
        """List available models."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "list_models", None) or getattr(
                instance, "get_model_list", None
            )
            if callable(fn):
                return fn(**kwargs)
        caps = self.get_capabilities()
        return caps.get("models") or caps.get("loaded_models") or []

    def get_endpoints(self, **kwargs: Any) -> Any:
        """List configured inference endpoints."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "get_endpoints", None)
            if callable(fn):
                return fn(**kwargs)
        return {"endpoints": []}

    def get_performance_metrics(self, **kwargs: Any) -> Any:
        """Get server performance/telemetry metrics."""
        instance = self._get_instance()
        if instance is not None:
            fn = getattr(instance, "get_performance_metrics", None)
            if callable(fn):
                return fn(**kwargs)
        return {"metrics": {}}


def _import_accelerate_module() -> Any | None:
    try:
        return importlib.import_module("ipfs_accelerate_py")
    except ModuleNotFoundError as exc:
        if exc.name != "ipfs_accelerate_py":
            raise
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


def get_ipfs_accelerate_cli_command() -> str:
    """Return the validated CLI command name for local accelerate execution."""
    return IPFS_ACCELERATE_CLI_COMMAND
