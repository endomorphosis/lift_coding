-- Migration: Add idempotency_keys table for persistent idempotency handling

-- Idempotency keys table for exactly-once semantics
-- Links to audit log entries to provide ground truth
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key             TEXT PRIMARY KEY,
  user_id         UUID NOT NULL,
  endpoint        TEXT NOT NULL,
  response_data   JSON NOT NULL,
  audit_log_id    UUID,  -- Link to audit log entry (if applicable)
  expires_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (audit_log_id) REFERENCES action_logs(id)
);

-- Index for efficient cleanup of expired keys
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires ON idempotency_keys(expires_at);

-- Index for user-specific queries
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_user ON idempotency_keys(user_id, created_at DESC);
