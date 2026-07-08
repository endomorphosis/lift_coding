"""Contract helpers for hallucinate_app to mobile search handoffs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT = (
    "handsfree.hallucinate_app/mobile-search-handoff@0.1.0"
)
HALLUCINATE_APP_MOBILE_ACTION_ID = "mobile_hallucinate_app_search"
HALLUCINATE_APP_MOBILE_EVENT = "hallucinate_app:mobile-search-handoff"
HALLUCINATE_APP_MOBILE_SOURCE_SURFACE = "hallucinate_app.content_browser"
HALLUCINATE_APP_MOBILE_TARGET_SURFACE = "mobile.results"
MCP_PLUS_PLUS_ENVELOPE_PROFILE = "swissknife.mcp++/event-envelope@0.1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class HallucinateAppMobileSearchHandoff:
    """Importable envelope shared by hallucinate_app and the mobile client."""

    contract: str = HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT
    action_id: str = HALLUCINATE_APP_MOBILE_ACTION_ID
    event: str = HALLUCINATE_APP_MOBILE_EVENT
    version: str = "0.1.0"
    source_surface: str = HALLUCINATE_APP_MOBILE_SOURCE_SURFACE
    target_surface: str = HALLUCINATE_APP_MOBILE_TARGET_SURFACE
    request_id: str = ""
    query: str = ""
    filters: dict[str, Any] = field(default_factory=dict)
    result_limit: int = 20
    cid: str | None = None
    path: str | None = None
    timestamp: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        mobile_payload = {
            "type": self.action_id,
            "contract": self.contract,
            "request_id": self.request_id,
            "query": self.query,
            "filters": self.filters,
            "result_limit": self.result_limit,
            "cid": self.cid,
            "path": self.path,
            "source_surface": self.source_surface,
            "target_surface": self.target_surface,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
        return {
            "contract": self.contract,
            "profile": MCP_PLUS_PLUS_ENVELOPE_PROFILE,
            "event_type": "transport.handoff",
            "action_id": self.action_id,
            "event": self.event,
            "version": self.version,
            "request_id": self.request_id,
            "correlation_id": self.request_id,
            "source_surface": self.source_surface,
            "target_surface": self.target_surface,
            "payload": {
                "query": self.query,
                "filters": self.filters,
                "cid": self.cid,
                "path": self.path,
            },
            "handoff": {
                "ipfs_cids": [self.cid] if self.cid else [],
                "libp2p_peer_id": None,
                "libp2p_session_id": None,
                "mcp_plus_plus_profile": MCP_PLUS_PLUS_ENVELOPE_PROFILE,
            },
            "control_plane": {
                "route": "hallucinate_app.mobile.search_handoff",
                "operation": self.action_id,
            },
            "policy": {
                "outcome": "allow",
                "source": self.source_surface,
            },
            "receipts": [],
            "mobile_payload": mobile_payload,
        }

    @property
    def receipt_cid(self) -> str:
        digest = hashlib.sha256(_stable_json(self.to_payload()).encode("utf-8")).hexdigest()
        return f"sha256:hallucinate-app-mobile:{digest}"


def build_mobile_search_handoff(
    *,
    query: str,
    filters: dict[str, Any] | None = None,
    request_id: str | None = None,
    result_limit: int = 20,
    cid: str | None = None,
    path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a validated hallucinate_app search handoff payload for mobile."""

    normalized_query = str(query or "").strip()
    normalized_filters = filters or {}
    if not normalized_query and not normalized_filters and not cid and not path:
        raise ValueError("mobile search handoff requires a query, filters, cid, or path")

    seed = _stable_json(
        {
            "query": normalized_query,
            "filters": normalized_filters,
            "cid": cid,
            "path": path,
            "metadata": metadata or {},
        }
    )
    stable_request_id = request_id or (
        "hallucinate-app-mobile-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    )
    envelope = HallucinateAppMobileSearchHandoff(
        request_id=stable_request_id,
        query=normalized_query,
        filters=normalized_filters,
        result_limit=int(result_limit),
        cid=cid,
        path=path,
        metadata=metadata or {},
    )
    payload = envelope.to_payload()
    payload["receipt_cid"] = envelope.receipt_cid
    return payload


def validate_mobile_search_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the normalized mobile payload or raise ValueError."""

    if not isinstance(payload, dict):
        raise ValueError("handoff payload must be an object")
    mobile_payload = payload.get("mobile_payload")
    if not isinstance(mobile_payload, dict):
        mobile_payload = payload
    contract = mobile_payload.get("contract") or payload.get("contract")
    action_id = mobile_payload.get("type") or payload.get("action_id")
    if contract != HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT:
        raise ValueError(f"unexpected hallucinate_app mobile contract: {contract!r}")
    if action_id != HALLUCINATE_APP_MOBILE_ACTION_ID:
        raise ValueError(f"unexpected hallucinate_app mobile action: {action_id!r}")
    if not any(mobile_payload.get(key) for key in ("query", "filters", "cid", "path")):
        raise ValueError("handoff payload has no search criteria")
    return mobile_payload
