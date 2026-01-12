-- DuckDB schema (initial, evolve with migrations)

CREATE TABLE IF NOT EXISTS users (
  id              UUID PRIMARY KEY,
  email           TEXT UNIQUE,
  display_name    TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- GitHub App installations (or OAuth connections)
CREATE TABLE IF NOT EXISTS github_connections (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  installation_id BIGINT,
  token_ref       TEXT, -- reference to secret manager (do not store tokens directly)
  scopes          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repo_policies (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  repo_full_name  TEXT NOT NULL, -- owner/name
  allow_merge     BOOLEAN NOT NULL DEFAULT false,
  allow_rerun     BOOLEAN NOT NULL DEFAULT true,
  allow_request_review BOOLEAN NOT NULL DEFAULT true,
  require_confirmation BOOLEAN NOT NULL DEFAULT true,
  require_checks_green  BOOLEAN NOT NULL DEFAULT true,
  required_approvals    INT NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, repo_full_name)
);

-- Commands (inputs + parsed intents)
CREATE TABLE IF NOT EXISTS commands (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  profile         TEXT NOT NULL DEFAULT 'default',
  input_type      TEXT NOT NULL, -- text/audio
  transcript      TEXT,          -- store only if allowed by privacy mode
  intent_name     TEXT,
  intent_confidence REAL,
  entities        JSONB,
  status          TEXT NOT NULL, -- ok/needs_confirmation/error
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pending actions requiring confirmation
CREATE TABLE IF NOT EXISTS pending_actions (
  token           TEXT PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  summary         TEXT NOT NULL,
  action_type     TEXT NOT NULL,
  action_payload  JSONB NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Side-effect action audit log
CREATE TABLE IF NOT EXISTS action_logs (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action_type     TEXT NOT NULL,
  target          TEXT,
  request         JSONB,
  result          JSONB,
  ok              BOOLEAN NOT NULL,
  idempotency_key TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Webhook event store (for replay/debug)
CREATE TABLE IF NOT EXISTS webhook_events (
  id              UUID PRIMARY KEY,
  source          TEXT NOT NULL, -- github
  event_type      TEXT,
  delivery_id     TEXT,
  signature_ok    BOOLEAN NOT NULL DEFAULT false,
  payload         JSONB,
  received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent tasks
CREATE TABLE IF NOT EXISTS agent_tasks (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider        TEXT NOT NULL, -- copilot/custom
  repo_full_name  TEXT,
  issue_number    INT,
  pr_number       INT,
  instruction     TEXT,
  status          TEXT NOT NULL, -- created/running/needs_input/completed/failed
  last_update     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_commands_user_created ON commands(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_created ON action_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_events_received ON webhook_events(received_at DESC);
