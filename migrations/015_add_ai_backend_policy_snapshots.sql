CREATE TABLE IF NOT EXISTS ai_backend_policy_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    summary_backend TEXT NOT NULL,
    failure_backend TEXT NOT NULL,
    github_auth_source TEXT,
    github_live_mode_requested BOOLEAN NOT NULL DEFAULT FALSE,
    ai_execute_logs INTEGER NOT NULL,
    policy_applied_count INTEGER NOT NULL,
    remap_counts JSON,
    top_capabilities JSON,
    top_remaps JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_backend_policy_snapshots_user_created
ON ai_backend_policy_snapshots(user_id, created_at DESC);
