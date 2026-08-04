"""Implied superproject entry for UIR-002 MCP-IDL identity contract tests.

The authoritative suite and fixtures live under ``external/ipfs_datasets``.
This module loads that suite by file path so superproject discovery exercises
the same regressions without duplicating assertions.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATASETS_ROOT = _REPO_ROOT / "external" / "ipfs_datasets"
_ACCELERATE_ROOT = _REPO_ROOT / "external" / "ipfs_accelerate"
_SUITE_PATH = (
    _DATASETS_ROOT / "tests" / "unit" / "logic" / "ui_ux_ir" / "test_mcp_idl_identity_contract.py"
)

for _path in (_DATASETS_ROOT, _ACCELERATE_ROOT):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

_spec = importlib.util.spec_from_file_location(
    "uir002_mcp_idl_identity_contract_datasets",
    _SUITE_PATH,
)
assert _spec is not None and _spec.loader is not None
_datasets_suite = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_datasets_suite)

for _name in dir(_datasets_suite):
    if _name.startswith("test_") or _name in {"vectors"}:
        globals()[_name] = getattr(_datasets_suite, _name)


def test_implied_validation_entry_points_at_datasets_suite() -> None:
    """Ensure the implied path stays wired to the declared datasets suite."""

    assert _SUITE_PATH.is_file()
    assert hasattr(_datasets_suite, "test_golden_interface_cid_is_cidv1_raw_sha2_256_base32")
    assert Path(_datasets_suite.FIXTURE_PATH).is_file()
    assert Path(_datasets_suite.CONTRACT_DOC_PATH).is_file()
