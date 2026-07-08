"""Hallucinate App to mobile runtime handoff contract.

The helpers in this module are intentionally dependency-free so the integration
gate can validate the cross-repository contract without starting Electron,
React Native, DuckDB, or an IPFS daemon.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT = (
    "handsfree.hallucinate_app/mobile-search-handoff@0.1.0"
)
HALLUCINATE_APP_MOBILE_ACTION_ID = "mobile_hallucinate_app_search"
HALLUCINATE_APP_MOBILE_ROUTE = "hallucinate_app.mobile.search_handoff"
OBJECTIVE_ID = "VAIOS-G707"


def _stable_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _coerce_cids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if item]
    return [str(value)]


def build_mobile_search_handoff(
    *,
    query: str,
    filter: Mapping[str, Any] | None = None,
    cid: str | None = None,
    cids: list[str] | tuple[str, ...] | None = None,
    request_id: str | None = None,
    edge_session_id: str | None = None,
    libp2p_peer_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build the canonical Hallucinate App -> mobile search handoff envelope."""

    timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request_id = request_id or f"hallucinate-app-mobile-{hashlib.sha256(query.encode()).hexdigest()[:12]}"
    ipfs_cids = _coerce_cids(cids)
    if cid and cid not in ipfs_cids:
        ipfs_cids.insert(0, cid)

    handoff = {
        "schema": "hallucinate_app_mobile_content_search_handoff_v1",
        "objective_id": OBJECTIVE_ID,
        "interface_contract": HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        "runtime_handoff": "content-search-to-mobile-results",
        "query": query,
        "filter": dict(filter or {}),
        "ipfs_cids": ipfs_cids,
        "edge_session_id": edge_session_id,
        "libp2p_peer_id": libp2p_peer_id,
    }
    mobile_payload = {
        "type": HALLUCINATE_APP_MOBILE_ACTION_ID,
        "source_surface": "hallucinate_app.content_browser",
        "target_surface": "mobile.results",
        "request_id": request_id,
        "query": query,
        "filter": dict(filter or {}),
        "handoff": handoff,
    }
    control_plane = {
        "route": HALLUCINATE_APP_MOBILE_ROUTE,
        "requires_ack": True,
        "mediation_receipt_required": True,
    }
    receipt_material = {
        "contract": HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        "request_id": request_id,
        "handoff": handoff,
        "mobile_payload": mobile_payload,
    }
    receipt_digest = hashlib.sha256(_stable_json(receipt_material).encode("utf-8")).hexdigest()

    return {
        "profile": "swissknife.mcp++/event-envelope@0.1.0",
        "action_id": HALLUCINATE_APP_MOBILE_ACTION_ID,
        "event_type": "transport.handoff",
        "interface_contract": HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        "objective_id": OBJECTIVE_ID,
        "request_id": request_id,
        "timestamp": timestamp,
        "control_plane": control_plane,
        "handoff": handoff,
        "mobile_payload": mobile_payload,
        "mediation_receipt": {
            "receipt_type": "hallucinate_app_mobile_handoff",
            "receipt_cid": f"sha256:hallucinate-app-mobile:{receipt_digest}",
            "correlation_id": request_id,
            "accepted_interface_contract": HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
        },
        "receipt_cid": f"sha256:hallucinate-app-mobile:{receipt_digest}",
    }


def validate_mobile_search_handoff(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized mobile payload data or raise ValueError."""

    if envelope.get("interface_contract") != HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT:
        raise ValueError("unexpected Hallucinate App mobile interface contract")
    if envelope.get("action_id") != HALLUCINATE_APP_MOBILE_ACTION_ID:
        raise ValueError("unexpected Hallucinate App mobile action id")
    if envelope.get("event_type") != "transport.handoff":
        raise ValueError("Hallucinate App mobile handoff must use transport.handoff")

    mobile_payload = envelope.get("mobile_payload")
    if not isinstance(mobile_payload, Mapping):
        raise ValueError("missing mobile_payload object")
    if mobile_payload.get("type") != HALLUCINATE_APP_MOBILE_ACTION_ID:
        raise ValueError("mobile_payload.type does not match the action id")

    handoff = envelope.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("missing handoff object")
    if handoff.get("interface_contract") != HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT:
        raise ValueError("handoff interface contract does not match")
    if handoff.get("objective_id") != OBJECTIVE_ID:
        raise ValueError("handoff does not identify VAIOS-G707")

    return dict(mobile_payload)
