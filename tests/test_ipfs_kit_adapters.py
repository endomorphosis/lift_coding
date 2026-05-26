"""Tests for optional ipfs_kit_py adapters."""

import sys
from types import ModuleType

import pytest

import handsfree.ipfs_kit_adapters as adapters
from handsfree.ipfs_kit_adapters import (
    IPFSKitUnavailableError,
    get_ipfs_kit_adapter,
    reset_ipfs_kit_adapter_cache,
)


def test_fallback_kit_adapter_when_dependency_missing(monkeypatch):
    """Kit adapter should safely fall back when optional dependency is missing."""
    monkeypatch.delitem(sys.modules, "ipfs_kit_py", raising=False)
    monkeypatch.setattr(adapters, "_import_kit_module", lambda: None)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    with pytest.raises(IPFSKitUnavailableError, match="install ipfs_kit_py"):
        adapter.pin("bafy123")


def test_delegates_to_kit_module(monkeypatch):
    """Kit adapter should delegate to ipfs_kit_py."""
    module = ModuleType("ipfs_kit_py")

    def pin(cid, **kwargs):
        return {"ok": True, "cid": cid, "options": kwargs}

    def unpin(cid, **kwargs):
        return {"ok": True, "cid": cid, "options": kwargs}

    def resolve(cid, **kwargs):
        return {"cid": cid, "resolved": True, "options": kwargs}

    def package_dataset(items, **kwargs):
        return {"count": len(items), "options": kwargs}

    module.pin = pin
    module.unpin = unpin
    module.resolve = resolve
    module.package_dataset = package_dataset

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    assert adapter.pin("bafy123") == {"ok": True, "cid": "bafy123", "options": {}}
    assert adapter.unpin("bafy123") == {"ok": True, "cid": "bafy123", "options": {}}
    assert adapter.resolve("bafy123") == {"cid": "bafy123", "resolved": True, "options": {}}
    assert adapter.package_dataset([{"cid": "bafy123"}]) == {"count": 1, "options": {}}


def test_delegates_to_canonical_ipfs_backend(monkeypatch):
    """Kit adapter should use the canonical backend module for pin operations."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    class FakeBackend:
        def pin_add(self, cid, **kwargs):
            return {"backend": "pin_add", "cid": cid, "options": kwargs}

        def pin_rm(self, cid, **kwargs):
            return {"backend": "pin_rm", "cid": cid, "options": kwargs}

    backend_module.get_instance = lambda: FakeBackend()

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    assert adapter.pin("bafy123") == {
        "backend": "pin_add",
        "cid": "bafy123",
        "options": {},
    }
    assert adapter.unpin("bafy123") == {
        "backend": "pin_rm",
        "cid": "bafy123",
        "options": {},
    }


def test_content_operations_fall_back_to_canonical_ipfs_backend(monkeypatch):
    """Missing direct content helpers should use the canonical backend module."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    class FakeBackend:
        def add_bytes(self, data, **kwargs):
            return {"backend": "add_bytes", "data": data, "options": kwargs}

        def cat(self, cid, **kwargs):
            return {"backend": "cat", "cid": cid, "options": kwargs}

    backend_module.get_instance = lambda: FakeBackend()

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    assert adapter.add_bytes(b"payload", pin=True) == {
        "backend": "add_bytes",
        "data": b"payload",
        "options": {"pin": True},
    }
    assert adapter.cat("bafy123", timeout=10) == {
        "backend": "cat",
        "cid": "bafy123",
        "options": {"timeout": 10},
    }


def test_resolve_falls_back_to_canonical_ipfs_backend(monkeypatch):
    """Missing direct resolve helper should use canonical backend CID metadata."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    class FakeBackend:
        def ipfs_object_stat(self, cid, **kwargs):
            return {"backend": "ipfs_object_stat", "cid": cid, "options": kwargs}

    backend_module.get_instance = lambda: FakeBackend()

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    assert adapter.resolve("bafy123", timeout=10) == {
        "backend": "ipfs_object_stat",
        "cid": "bafy123",
        "options": {"timeout": 10},
    }


def test_missing_backend_factory_raises_unavailable_error(monkeypatch):
    """Missing canonical backend factory should use the adapter unavailable error."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    with pytest.raises(
        IPFSKitUnavailableError,
        match="ipfs_kit_py.ipfs_backend.get_instance is unavailable",
    ):
        adapter.pin("bafy123")


def test_add_bytes_without_backend_helpers_raises_unavailable_error(monkeypatch):
    """Missing backend content helpers should use the adapter unavailable error."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    class FakeBackend:
        pass

    backend_module.get_instance = lambda: FakeBackend()

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    with pytest.raises(
        IPFSKitUnavailableError,
        match="backend exposes neither add_bytes nor add_str",
    ):
        adapter.add_bytes(b"payload")


def test_backend_factory_errors_are_not_swallowed(monkeypatch):
    """Backend construction failures should surface with their original cause."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    def get_instance():
        raise RuntimeError("backend init failed")

    backend_module.get_instance = get_instance

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    monkeypatch.setitem(sys.modules, "ipfs_kit_py.ipfs_backend", backend_module)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    with pytest.raises(RuntimeError, match="backend init failed"):
        adapter.pin("bafy123")


def test_direct_callable_import_errors_are_not_swallowed(monkeypatch):
    """Broken installed direct-import surfaces should fail before backend fallback."""
    root_module = ModuleType("ipfs_kit_py")
    backend_module = ModuleType("ipfs_kit_py.ipfs_backend")

    class FakeBackend:
        def pin_add(self, cid, **kwargs):
            return {"backend": "pin_add", "cid": cid, "options": kwargs}

    backend_module.get_instance = lambda: FakeBackend()

    monkeypatch.setitem(sys.modules, "ipfs_kit_py", root_module)
    reset_ipfs_kit_adapter_cache()
    adapter = get_ipfs_kit_adapter()

    original_import_module = adapters.importlib.import_module

    def import_module(module_name):
        if module_name == "ipfs_kit_py":
            raise RuntimeError("direct import failed")
        if module_name == "ipfs_kit_py.ipfs_backend":
            return backend_module
        return original_import_module(module_name)

    monkeypatch.setattr(adapters.importlib, "import_module", import_module)

    with pytest.raises(RuntimeError, match="direct import failed"):
        adapter.pin("bafy123")
