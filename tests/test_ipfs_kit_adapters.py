"""Tests for optional ipfs_kit_py adapters.

These tests verify the adapter correctly wraps the real ipfs_kit_py API:
- ipfs_kit_py.ipfs_kit.ipfs_kit.create(role="leecher") for the main class
- .ipfs_add(path), .ipfs_cat(cid), .ipfs_pin_add(cid), .ipfs_pin_rm(cid)
- ipfs_kit_py.backend_config.get_backend_statuses() for health checks
"""

import json
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

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


def test_unavailable_adapter_get_backend_statuses():
    """Unavailable adapter should return empty dict for backend statuses."""
    from handsfree.ipfs_kit_adapters import _UnavailableIPFSKitAdapter

    adapter = _UnavailableIPFSKitAdapter()
    assert adapter.get_backend_statuses() == {}


def test_module_adapter_delegates_to_ipfs_kit_class():
    """Kit adapter should use ipfs_kit_py.ipfs_kit.ipfs_kit class methods."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    # Mock the ipfs_kit class
    mock_kit_instance = MagicMock()
    mock_kit_instance.ipfs_cat.return_value = b"hello world"
    mock_kit_instance.ipfs_pin_add.return_value = {"Pins": ["bafy123"]}
    mock_kit_instance.ipfs_pin_rm.return_value = {"Pins": ["bafy123"]}

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.return_value = mock_kit_instance
    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        # cat delegates to ipfs_cat
        result = adapter.cat("bafy123")
        assert result == b"hello world"
        mock_kit_instance.ipfs_cat.assert_called_once_with("bafy123")

        # pin delegates to ipfs_pin_add
        result = adapter.pin("bafy123")
        mock_kit_instance.ipfs_pin_add.assert_called_once_with("bafy123")

        # unpin delegates to ipfs_pin_rm
        result = adapter.unpin("bafy123")
        mock_kit_instance.ipfs_pin_rm.assert_called_once_with("bafy123")


def test_module_adapter_add_bytes_uses_temp_file():
    """add_bytes should write to temp file and call ipfs_add."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_kit_instance = MagicMock()
    mock_kit_instance.ipfs_add.return_value = {"Hash": "QmNewCID", "Name": "file.bin"}

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.return_value = mock_kit_instance
    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        result = adapter.add_bytes(b"test payload")
        assert result == {"Hash": "QmNewCID", "Name": "file.bin"}
        mock_kit_instance.ipfs_add.assert_called_once()
        # Verify path was passed (temp file)
        call_args = mock_kit_instance.ipfs_add.call_args
        assert call_args[0][0].endswith(".bin")


def test_module_adapter_resolve_tries_multiple_methods():
    """resolve should try ipfs_resolve, ipfs_dag_get, then fall back to ipfs_cat."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_kit_instance = MagicMock(spec=[])  # no methods by default
    mock_kit_instance.ipfs_cat = MagicMock(return_value=b"data")
    # Simulate no ipfs_resolve or ipfs_dag_get

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.return_value = mock_kit_instance
    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        result = adapter.resolve("bafy123")
        assert result == {"cid": "bafy123", "size": 4}


def test_module_adapter_package_dataset_stores_manifest():
    """package_dataset should serialize and store a manifest via add_bytes."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_kit_instance = MagicMock()
    mock_kit_instance.ipfs_add.return_value = {"Hash": "QmManifestCID"}

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.return_value = mock_kit_instance
    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        result = adapter.package_dataset(
            [{"cid": "bafy123"}], metadata={"name": "test"}
        )
        assert result == {"Hash": "QmManifestCID"}
        mock_kit_instance.ipfs_add.assert_called_once()


def test_module_adapter_get_backend_statuses():
    """get_backend_statuses should delegate to ipfs_kit_py.backend_config."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_config = MagicMock()
    mock_config.get_backend_statuses.return_value = {
        "kubo": {"exists": True, "enabled": True, "has_credentials": True}
    }

    with patch("importlib.import_module", return_value=mock_config):
        result = adapter.get_backend_statuses()
        assert result == {"kubo": {"exists": True, "enabled": True, "has_credentials": True}}


def test_kit_create_failure_falls_back_to_constructor():
    """If create() fails, adapter should try direct construction."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_kit_instance = MagicMock()
    mock_kit_instance.ipfs_cat.return_value = b"fallback"

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.side_effect = Exception("create failed")
    mock_kit_cls.return_value = mock_kit_instance

    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        result = adapter.cat("bafy123")
        assert result == b"fallback"
        mock_kit_cls.assert_called_once_with(metadata={"role": "leecher"})


def test_kit_all_init_paths_fail_raises_unavailable():
    """If both create() and constructor fail, should raise IPFSKitUnavailableError."""
    from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

    mock_root = MagicMock()
    adapter = _IPFSKitModuleAdapter(mock_root)

    mock_kit_cls = MagicMock()
    mock_kit_cls.create.side_effect = Exception("create failed")
    mock_kit_cls.side_effect = Exception("init failed")

    mock_kit_module = MagicMock()
    mock_kit_module.ipfs_kit = mock_kit_cls

    with patch("importlib.import_module", return_value=mock_kit_module):
        with pytest.raises(IPFSKitUnavailableError, match="failed to initialize"):
            adapter.cat("bafy123")

