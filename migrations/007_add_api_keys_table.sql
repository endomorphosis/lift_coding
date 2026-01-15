-- API keys table for API key authentication
-- Keys are stored as hashes (never plaintext) for security

CREATE TABLE IF NOT EXISTS api_keys (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL,
  key_hash        TEXT NOT NULL,
  label           TEXT,           -- User-friendly description (e.g., "Mobile app", "CI/CD")
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at      TIMESTAMPTZ,    -- NULL = active, non-NULL = revoked
  last_used_at    TIMESTAMPTZ     -- Track usage for analytics/security
);

-- Index for fast lookup by hash during authentication
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- Index for listing user's keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id, created_at DESC);
