-- Add repo_subscriptions table for webhook user mapping
-- This allows determining which users should receive notifications for webhook events
-- from specific repositories based on their GitHub installation/connection

CREATE TABLE IF NOT EXISTS repo_subscriptions (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL,
  repo_full_name  TEXT NOT NULL, -- owner/name format (e.g., "testorg/testrepo")
  installation_id BIGINT,        -- GitHub App installation ID (null for non-app connections)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, repo_full_name, installation_id)
);

CREATE INDEX IF NOT EXISTS idx_repo_subscriptions_repo ON repo_subscriptions(repo_full_name);
CREATE INDEX IF NOT EXISTS idx_repo_subscriptions_installation ON repo_subscriptions(installation_id);
