CREATE TABLE IF NOT EXISTS ai_history_index (
  id                  UUID PRIMARY KEY,
  user_id             UUID NOT NULL,
  capability_id       TEXT NOT NULL,
  repo                TEXT,
  pr_number           INT,
  failure_target      TEXT,
  failure_target_type TEXT,
  ipfs_cid            TEXT NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_history_index_lookup
  ON ai_history_index(user_id, capability_id, repo, failure_target_type, failure_target, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_history_index_cid
  ON ai_history_index(user_id, ipfs_cid);
