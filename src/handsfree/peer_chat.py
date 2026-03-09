"""In-memory peer chat session service for Bluetooth/libp2p bring-up."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time
from uuid import uuid4
from typing import Any

from handsfree.db.peer_chat import (
    list_peer_chat_messages,
    list_recent_peer_chat_conversations,
    store_peer_chat_message,
)


@dataclass(slots=True)
class PeerChatMessage:
    """Normalized chat message stored for a peer conversation."""

    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str
    timestamp_ms: int


@dataclass(slots=True)
class OutboxMessage:
    """Queued outbound chat message awaiting handset delivery acknowledgement."""

    outbox_message_id: str
    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str
    timestamp_ms: int
    leased_until_ms: int | None = None


@dataclass(slots=True)
class PeerChatHandsetSession:
    """Observed handset polling session for dev peer chat relay."""

    peer_id: str
    display_name: str | None
    last_seen_ms: int
    last_fetch_ms: int | None = None
    last_ack_ms: int | None = None


def build_conversation_id(peer_id: str, sender_peer_id: str) -> str:
    """Create a stable two-party conversation id."""
    participants = sorted({peer_id, sender_peer_id})
    return f"chat:{':'.join(participants)}"


class PeerChatSessionService:
    """Tracks in-memory chat conversations for dev and local transport bring-up."""

    ACTIVE_HANDSET_THRESHOLD_MS = 15000
    STALE_HANDSET_THRESHOLD_MS = 60000
    ACTIVE_LEASE_MS = 5000
    STALE_LEASE_MS = 15000
    OFFLINE_LEASE_MS = 60000
    ACTIVE_POLL_MS = 4000
    STALE_POLL_MS = 10000
    OFFLINE_POLL_MS = 30000
    SUPPORTED_PRIORITIES = {"normal", "urgent"}

    def __init__(self, db_conn_factory: Any | None = None) -> None:
        self._db_conn_factory = db_conn_factory
        self._messages: dict[str, list[PeerChatMessage]] = {}
        self._outbox: dict[str, list[OutboxMessage]] = {}
        self._handset_sessions: dict[str, PeerChatHandsetSession] = {}
        self._now_ms_factory = lambda: int(time() * 1000)

    def ingest_chat_payload(self, peer_id: str, payload: dict[str, Any]) -> PeerChatMessage:
        sender_peer_id = str(payload.get("sender_peer_id") or peer_id)
        conversation_id = str(
            payload.get("conversation_id") or build_conversation_id(peer_id, sender_peer_id)
        )
        timestamp_ms = int(payload.get("timestamp_ms") or 0)
        if timestamp_ms <= 0:
            raise ValueError("Chat payload timestamp_ms must be a positive integer")
        text = str(payload.get("text") or "")
        if not text:
            raise ValueError("Chat payload text must be a non-empty string")
        priority = str(payload.get("priority") or "normal").lower()
        if priority not in self.SUPPORTED_PRIORITIES:
            raise ValueError("Chat payload priority must be 'normal' or 'urgent'")

        message = PeerChatMessage(
            conversation_id=conversation_id,
            peer_id=peer_id,
            sender_peer_id=sender_peer_id,
            text=text,
            priority=priority,
            timestamp_ms=timestamp_ms,
        )
        if self._db_conn_factory is not None:
            try:
                conn = self._db_conn_factory()
                store_peer_chat_message(
                    conn=conn,
                    conversation_id=conversation_id,
                    peer_id=peer_id,
                    sender_peer_id=sender_peer_id,
                    text=text,
                    priority=priority,
                    timestamp_ms=timestamp_ms,
                )
            except Exception:
                pass
        self._messages.setdefault(conversation_id, []).append(message)
        return message

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        if self._db_conn_factory is not None:
            try:
                conn = self._db_conn_factory()
                return [
                    {
                        "conversation_id": item.conversation_id,
                        "peer_id": item.peer_id,
                        "sender_peer_id": item.sender_peer_id,
                        "text": item.text,
                        "priority": item.priority,
                        "timestamp_ms": item.timestamp_ms,
                    }
                    for item in list_peer_chat_messages(conn, conversation_id)
                ]
            except Exception:
                pass
        return [asdict(item) for item in self._messages.get(conversation_id, [])]

    def list_recent_conversations(self, limit: int = 20) -> list[dict[str, Any]]:
        if self._db_conn_factory is not None:
            try:
                conn = self._db_conn_factory()
                return [
                    {
                        "conversation_id": item.conversation_id,
                        "peer_id": item.peer_id,
                        "sender_peer_id": item.sender_peer_id,
                        "last_text": item.last_text,
                        "last_timestamp_ms": item.last_timestamp_ms,
                        "message_count": item.message_count,
                    }
                    for item in list_recent_peer_chat_conversations(conn, limit)
                ]
            except Exception:
                pass

        conversations: dict[str, dict[str, Any]] = {}
        for items in self._messages.values():
            for item in items:
                existing = conversations.get(item.conversation_id)
                if existing is None or item.timestamp_ms >= existing["last_timestamp_ms"]:
                    conversations[item.conversation_id] = {
                        "conversation_id": item.conversation_id,
                        "peer_id": item.peer_id,
                        "sender_peer_id": item.sender_peer_id,
                        "last_text": item.text,
                        "priority": item.priority,
                        "last_timestamp_ms": item.timestamp_ms,
                        "message_count": len(items),
                    }
        return sorted(
            conversations.values(),
            key=lambda item: item["last_timestamp_ms"],
            reverse=True,
        )[:limit]

    def queue_outbound_message(
        self,
        recipient_peer_id: str,
        sender_peer_id: str,
        conversation_id: str,
        text: str,
        priority: str,
        timestamp_ms: int,
    ) -> dict[str, Any]:
        resolved_priority = str(priority or "normal").lower()
        if resolved_priority not in self.SUPPORTED_PRIORITIES:
            raise ValueError("Outbound message priority must be 'normal' or 'urgent'")
        message = OutboxMessage(
            outbox_message_id=f"outbox-{uuid4().hex}",
            conversation_id=conversation_id,
            peer_id=recipient_peer_id,
            sender_peer_id=sender_peer_id,
            text=text,
            priority=resolved_priority,
            timestamp_ms=timestamp_ms,
        )
        self._outbox.setdefault(recipient_peer_id, []).append(message)
        return asdict(message)

    def fetch_outbound_messages(
        self,
        peer_id: str,
        lease_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        current = self._outbox.get(peer_id, [])
        if not current:
            return []

        now_ms = self._now_ms_factory()
        policy = self.get_handset_delivery_policy(peer_id)
        resolved_lease_ms = policy["recommended_lease_ms"]
        if lease_ms is not None:
            resolved_lease_ms = max(0, lease_ms)
        deliverable: list[OutboxMessage] = []
        for item in current:
            if item.leased_until_ms is not None and item.leased_until_ms > now_ms:
                continue
            if policy["delivery_mode"] == "hold" and item.priority != "urgent":
                continue
            deliverable.append(item)

        if policy["delivery_mode"] == "short_retry":
            deliverable.sort(key=lambda item: item.timestamp_ms)
        else:
            deliverable.sort(key=lambda item: (0 if item.priority == "urgent" else 1, item.timestamp_ms))

        visible: list[dict[str, Any]] = []
        for item in deliverable:
            item.leased_until_ms = now_ms + resolved_lease_ms
            visible.append(asdict(item))
        return visible

    def summarize_outbound_messages(self, peer_id: str) -> dict[str, int]:
        current = self._outbox.get(peer_id, [])
        if not current:
            return {
                "queued_total": 0,
                "queued_urgent": 0,
                "queued_normal": 0,
                "deliverable_now": 0,
                "held_now": 0,
            }

        now_ms = self._now_ms_factory()
        policy = self.get_handset_delivery_policy(peer_id)
        queued_urgent = sum(1 for item in current if item.priority == "urgent")
        queued_normal = sum(1 for item in current if item.priority == "normal")
        deliverable_now = 0
        held_now = 0
        for item in current:
            if item.leased_until_ms is not None and item.leased_until_ms > now_ms:
                held_now += 1
                continue
            if policy["delivery_mode"] == "hold" and item.priority != "urgent":
                held_now += 1
                continue
            deliverable_now += 1

        return {
            "queued_total": len(current),
            "queued_urgent": queued_urgent,
            "queued_normal": queued_normal,
            "deliverable_now": deliverable_now,
            "held_now": held_now,
        }

    def preview_outbound_messages(self, peer_id: str) -> list[dict[str, Any]]:
        current = self._outbox.get(peer_id, [])
        if not current:
            return []

        now_ms = self._now_ms_factory()
        policy = self.get_handset_delivery_policy(peer_id)
        preview: list[dict[str, Any]] = []
        for item in current:
            state = "deliverable"
            hold_reason = None
            if item.leased_until_ms is not None and item.leased_until_ms > now_ms:
                state = "leased"
                hold_reason = "lease_active"
            elif policy["delivery_mode"] == "hold" and item.priority != "urgent":
                state = "held_by_policy"
                hold_reason = "offline_normal_priority"

            payload = asdict(item)
            payload["state"] = state
            payload["hold_reason"] = hold_reason
            preview.append(payload)

        preview.sort(
            key=lambda item: (
                0 if item["state"] == "deliverable" else 1,
                0 if item["priority"] == "urgent" else 1,
                item["timestamp_ms"],
            )
        )
        return preview

    def acknowledge_outbound_messages(
        self,
        peer_id: str,
        outbox_message_ids: list[str],
    ) -> list[str]:
        if not outbox_message_ids:
            return []
        current = self._outbox.get(peer_id, [])
        if not current:
            return []

        pending_ids = set(outbox_message_ids)
        remaining: list[OutboxMessage] = []
        acked: list[str] = []
        for item in current:
            if item.outbox_message_id in pending_ids:
                acked.append(item.outbox_message_id)
            else:
                remaining.append(item)

        if remaining:
            self._outbox[peer_id] = remaining
        else:
            self._outbox.pop(peer_id, None)
        return acked

    def release_outbound_leases(
        self,
        peer_id: str,
        outbox_message_ids: list[str],
    ) -> list[str]:
        if not outbox_message_ids:
            return []
        current = self._outbox.get(peer_id, [])
        if not current:
            return []

        pending_ids = set(outbox_message_ids)
        released: list[str] = []
        for item in current:
            if item.outbox_message_id not in pending_ids:
                continue
            if item.leased_until_ms is not None:
                item.leased_until_ms = None
                released.append(item.outbox_message_id)
        return released

    def promote_outbound_messages(
        self,
        peer_id: str,
        outbox_message_ids: list[str],
    ) -> list[str]:
        if not outbox_message_ids:
            return []
        current = self._outbox.get(peer_id, [])
        if not current:
            return []

        pending_ids = set(outbox_message_ids)
        promoted: list[str] = []
        for item in current:
            if item.outbox_message_id not in pending_ids:
                continue
            if item.priority != "urgent":
                item.priority = "urgent"
                promoted.append(item.outbox_message_id)
        return promoted

    def record_handset_heartbeat(
        self,
        peer_id: str,
        display_name: str | None = None,
        *,
        fetched_outbox: bool = False,
        acknowledged_outbox: bool = False,
    ) -> dict[str, Any]:
        now_ms = self._now_ms_factory()
        session = self._handset_sessions.get(peer_id)
        if session is None:
            session = PeerChatHandsetSession(
                peer_id=peer_id,
                display_name=display_name,
                last_seen_ms=now_ms,
            )
            self._handset_sessions[peer_id] = session

        session.last_seen_ms = now_ms
        if display_name:
            session.display_name = display_name
        if fetched_outbox:
            session.last_fetch_ms = now_ms
        if acknowledged_outbox:
            session.last_ack_ms = now_ms
        return self._serialize_handset_session(session, now_ms=now_ms)

    def get_handset_session(self, peer_id: str) -> dict[str, Any] | None:
        session = self._handset_sessions.get(peer_id)
        if session is None:
            return None
        return self._serialize_handset_session(session)

    def get_handset_delivery_policy(self, peer_id: str) -> dict[str, Any]:
        session = self._handset_sessions.get(peer_id)
        status = "active"
        if session is not None:
            last_seen_age_ms = max(0, self._now_ms_factory() - session.last_seen_ms)
            if last_seen_age_ms <= self.ACTIVE_HANDSET_THRESHOLD_MS:
                status = "active"
            elif last_seen_age_ms <= self.STALE_HANDSET_THRESHOLD_MS:
                status = "stale"
            else:
                status = "offline"
        if status == "active":
            return {
                "delivery_mode": "short_retry",
                "recommended_lease_ms": self.ACTIVE_LEASE_MS,
                "recommended_poll_ms": self.ACTIVE_POLL_MS,
            }
        if status == "stale":
            return {
                "delivery_mode": "long_retry",
                "recommended_lease_ms": self.STALE_LEASE_MS,
                "recommended_poll_ms": self.STALE_POLL_MS,
            }
        return {
            "delivery_mode": "hold",
            "recommended_lease_ms": self.OFFLINE_LEASE_MS,
            "recommended_poll_ms": self.OFFLINE_POLL_MS,
        }

    def _serialize_handset_session(
        self,
        session: PeerChatHandsetSession,
        *,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        current_ms = self._now_ms_factory() if now_ms is None else now_ms
        last_seen_age_ms = max(0, current_ms - session.last_seen_ms)
        if last_seen_age_ms <= self.ACTIVE_HANDSET_THRESHOLD_MS:
            status = "active"
        elif last_seen_age_ms <= self.STALE_HANDSET_THRESHOLD_MS:
            status = "stale"
        else:
            status = "offline"

        payload = asdict(session)
        payload["status"] = status
        payload["last_seen_age_ms"] = last_seen_age_ms
        payload.update(self.get_handset_delivery_policy(session.peer_id))
        return payload
