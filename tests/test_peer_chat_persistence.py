"""Tests for peer chat persistence."""

from handsfree.db.connection import init_db
from handsfree.db.peer_chat import list_peer_chat_messages, store_peer_chat_message


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
