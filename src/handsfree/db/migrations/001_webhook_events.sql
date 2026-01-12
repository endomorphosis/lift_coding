-- Initial migration: webhook_events table
-- This table stores raw webhook events from GitHub for replay protection and debugging

CREATE TABLE IF NOT EXISTS webhook_events (
  id              UUID PRIMARY KEY,
  source          TEXT NOT NULL, -- github
  event_type      TEXT,
  delivery_id     TEXT NOT NULL, -- Required for replay protection
  signature_ok    BOOLEAN NOT NULL DEFAULT false,
  payload         JSON,
  received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for replay protection by delivery_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_events_delivery_id 
  ON webhook_events(delivery_id);

-- Index for querying by received_at
CREATE INDEX IF NOT EXISTS idx_webhook_events_received 
  ON webhook_events(received_at DESC);
