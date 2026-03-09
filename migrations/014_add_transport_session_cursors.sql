CREATE TABLE IF NOT EXISTS transport_session_cursors (
    peer_id TEXT PRIMARY KEY,
    peer_ref TEXT NOT NULL,
    session_id TEXT NOT NULL,
    resume_token TEXT NOT NULL,
    capabilities_json TEXT NOT NULL DEFAULT '[]',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
