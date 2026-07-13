"""Regression tests for the XPH-101 normative specification gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_mcplusplus_profile_h_spec.py"
CHAPTER = ROOT / "Mcp-Plus-Plus/docs/spec/x402-payments.md"
REGISTRY = ROOT / "Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md"


def _module():
    spec = importlib.util.spec_from_file_location("profile_h_spec_gate", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _texts() -> tuple[str, str]:
    return CHAPTER.read_text(encoding="utf-8"), REGISTRY.read_text(encoding="utf-8")


def test_repository_profile_h_spec_is_valid() -> None:
    assert _module().validate(*_texts()) == []


def test_libp2p_cannot_be_claimed_as_upstream_x402() -> None:
    chapter, registry = _texts()
    chapter = chapter.replace("not upstream x402 HTTP", "upstream x402 HTTP", 1)
    registry = registry.replace("MUST NOT be represented as upstream x402 HTTP conformance", "is upstream x402 HTTP conformance", 1)
    failures = _module().validate(chapter, registry)
    assert any("upstream x402 and MCP++" in failure for failure in failures)
    assert any("libp2p/upstream distinction" in failure for failure in failures)


def test_stable_error_cannot_be_removed() -> None:
    chapter, registry = _texts()
    chapter = chapter.replace("`H_RECONCILIATION_REQUIRED`", "`REMOVED_RECONCILIATION_REQUIRED`")
    failures = _module().validate(chapter, registry)
    assert any("missing stable errors" in failure for failure in failures)


def test_profile_composition_cannot_be_removed() -> None:
    chapter, registry = _texts()
    chapter = chapter.replace("**G (scheduling):**", "**Scheduling:**")
    failures = _module().validate(chapter, registry)
    assert "composition rule missing for Profile G" in failures
