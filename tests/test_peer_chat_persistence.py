"""Tests for peer chat persistence."""

import pytest

from handsfree.db.connection import init_db
from handsfree.db.peer_chat import list_peer_chat_messages, store_peer_chat_message
from handsfree.peer_chat import PeerChatSessionService


def test_peer_chat_message_persists_in_memory_db():
    conn = init_db(":memory:")

    store_peer_chat_message(
        conn=conn,
        conversation_id="chat:test-persist",
        peer_id="12D3KooWpeerA",
        sender_peer_id="12D3KooWpeerB",
        text="hello persistence",
        priority="urgent",
        timestamp_ms=1234,
    )

    messages = list_peer_chat_messages(conn, "chat:test-persist")

    assert len(messages) == 1
    assert messages[0].conversation_id == "chat:test-persist"
    assert messages[0].peer_id == "12D3KooWpeerA"
    assert messages[0].sender_peer_id == "12D3KooWpeerB"
    assert messages[0].text == "hello persistence"
    assert messages[0].priority == "urgent"
    assert messages[0].timestamp_ms == 1234


def test_peer_chat_list_messages_falls_back_for_persistence_errors():
    conversation_id = "chat:test-fallback"

    def unavailable_db():
        raise OSError("peer chat db unavailable")

    service = PeerChatSessionService(db_conn_factory=unavailable_db)
    service.ingest_chat_payload(
        "12D3KooWpeerA",
        {
            "conversation_id": conversation_id,
            "sender_peer_id": "12D3KooWpeerB",
            "text": "fallback hello",
            "priority": "normal",
            "timestamp_ms": 5678,
        },
    )

    assert service.list_messages(conversation_id) == [
        {
            "conversation_id": conversation_id,
            "peer_id": "12D3KooWpeerA",
            "sender_peer_id": "12D3KooWpeerB",
            "text": "fallback hello",
            "priority": "normal",
            "timestamp_ms": 5678,
            "task_snapshot": None,
        }
    ]


def test_peer_chat_list_messages_propagates_unexpected_errors():
    def broken_db_factory():
        raise RuntimeError("unexpected peer chat failure")

    service = PeerChatSessionService(db_conn_factory=broken_db_factory)

    with pytest.raises(RuntimeError, match="unexpected peer chat failure"):
        service.list_messages("chat:test-propagate")


def test_peer_chat_recent_conversations_falls_back_for_persistence_errors():
    conversation_id = "chat:test-recent-fallback"

    def unavailable_db():
        raise OSError("peer chat db unavailable")

    service = PeerChatSessionService(db_conn_factory=unavailable_db)
    service.ingest_chat_payload(
        "12D3KooWpeerA",
        {
            "conversation_id": conversation_id,
            "sender_peer_id": "12D3KooWpeerB",
            "text": "recent fallback hello",
            "priority": "urgent",
            "timestamp_ms": 6789,
        },
    )

    assert service.list_recent_conversations() == [
        {
            "conversation_id": conversation_id,
            "peer_id": "12D3KooWpeerA",
            "sender_peer_id": "12D3KooWpeerB",
            "last_text": "recent fallback hello",
            "priority": "urgent",
            "last_timestamp_ms": 6789,
            "message_count": 1,
            "task_snapshot": None,
        }
    ]


def test_peer_chat_recent_conversations_propagates_unexpected_errors():
    def broken_db_factory():
        raise RuntimeError("unexpected peer chat failure")

    service = PeerChatSessionService(db_conn_factory=broken_db_factory)

    with pytest.raises(RuntimeError, match="unexpected peer chat failure"):
        service.list_recent_conversations()
