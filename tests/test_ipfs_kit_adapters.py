"""Tests for optional ipfs_kit_py adapters."""

import sys
from types import ModuleType

import pytest

from handsfree.ipfs_kit_adapters import (
    get_ipfs_kit_adapter,
    reset_ipfs_kit_adapter_cache,
)


def test_fallback_kit_adapter_when_dependency_missing():
    """Kit adapter should safely fall back when optional dependency is missing."""
    sys.modules.pop("ipfs_kit_py", None)
    reset_ipfs_kit_adapter_cache()

    adapter = get_ipfs_kit_adapter()

    with pytest.raises(NotImplementedError, match="install ipfs_kit_py"):
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
