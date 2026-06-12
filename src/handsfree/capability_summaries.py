"""Voice and display summary formatters for virtual AI OS capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def format_embedding(result: Mapping[str, Any]) -> str:
    """Summarize embedding output for compact voice/display surfaces."""
    return _format_status_summary(result, "Embedding ready")


def format_ipfs_pin(result: Mapping[str, Any]) -> str:
    """Summarize IPFS pin results."""
    summary = _first_text(result, "summary")
    if summary:
        return summary
    cid = _first_text(result, "cid", "result_cid")
    status = _first_text(result, "pin_status", "status")
    return _join_summary("IPFS pin", cid, status)


def format_workflow(result: Mapping[str, Any]) -> str:
    """Summarize accelerate workflow results."""
    return _format_status_summary(result, "Workflow updated")


def format_agentic_fetch(result: Mapping[str, Any]) -> str:
    """Summarize agentic fetch results."""
    return _format_status_summary(result, "Fetch updated")


def format_dataset_discovery(result: Mapping[str, Any]) -> str:
    """Summarize dataset discovery results."""
    summary = _first_text(result, "summary")
    if summary:
        return summary
    count = _first_text(result, "dataset_count", "source_count")
    query = _first_text(result, "query")
    return _join_summary("Dataset discovery", count, query)


def format_storage(result: Mapping[str, Any]) -> str:
    """Summarize storage and package results."""
    return _format_status_summary(result, "Storage updated")


def format_llm_generation(result: Mapping[str, Any]) -> str:
    """Summarize LLM generation and revision results."""
    summary = _first_text(result, "summary")
    if summary:
        return summary
    model = _first_text(result, "model")
    status = _first_text(result, "status")
    return _join_summary("LLM generation", model, status)


def format_ui_render_session(result: Mapping[str, Any]) -> str:
    """Summarize UI render session results."""
    summary = _first_text(result, "summary")
    if summary:
        return summary
    surface = _first_text(result, "surface")
    session_id = _first_text(result, "render_session_id")
    return _join_summary("UI render session", surface, session_id)


def format_device_render_transport(result: Mapping[str, Any]) -> str:
    """Summarize device render transport results."""
    summary = _first_text(result, "summary")
    if summary:
        return summary
    edge_id = _first_text(result, "edge_id", "edge_session_id")
    status = _first_text(result, "status")
    return _join_summary("Device render transport", edge_id, status)


def _format_status_summary(result: Mapping[str, Any], fallback: str) -> str:
    summary = _first_text(result, "summary")
    if summary:
        return summary
    status = _first_text(result, "status")
    return _join_summary(fallback, status)


def _first_text(result: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = result.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _join_summary(label: str, *parts: str | None) -> str:
    suffix = " ".join(part for part in parts if part)
    if not suffix:
        return label
    return f"{label}: {suffix}"


__all__ = [
    "format_agentic_fetch",
    "format_dataset_discovery",
    "format_device_render_transport",
    "format_embedding",
    "format_ipfs_pin",
    "format_llm_generation",
    "format_storage",
    "format_ui_render_session",
    "format_workflow",
]
