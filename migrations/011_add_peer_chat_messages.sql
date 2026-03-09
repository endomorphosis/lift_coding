CREATE TABLE IF NOT EXISTS peer_chat_messages (
  id              UUID PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  peer_id         TEXT NOT NULL,
  sender_peer_id  TEXT NOT NULL,
  text            TEXT NOT NULL,
  timestamp_ms    BIGINT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_peer_chat_messages_conversation_timestamp
ON peer_chat_messages(conversation_id, timestamp_ms);
