-- Migration: Add oauth_states table for CSRF protection

-- OAuth state table for CSRF protection during OAuth flow
-- States are short-lived (10 min TTL) and consumed on first use
CREATE TABLE IF NOT EXISTS oauth_states (
  state           TEXT PRIMARY KEY,
  user_id         UUID NOT NULL,
  scopes          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,
  consumed_at     TIMESTAMPTZ
);

-- Index for efficient cleanup of expired states
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);

-- Index for user-specific queries
CREATE INDEX IF NOT EXISTS idx_oauth_states_user ON oauth_states(user_id, created_at DESC);
