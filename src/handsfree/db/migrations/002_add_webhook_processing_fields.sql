-- Migration: Add webhook processing outcome fields
-- Adds fields to track processing status and failures for webhook events

ALTER TABLE webhook_events ADD COLUMN IF NOT EXISTS processed_ok BOOLEAN DEFAULT NULL;
ALTER TABLE webhook_events ADD COLUMN IF NOT EXISTS processing_error TEXT DEFAULT NULL;
ALTER TABLE webhook_events ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ DEFAULT NULL;

-- Index for querying by processing status
CREATE INDEX IF NOT EXISTS idx_webhook_events_processing_status 
  ON webhook_events(processed_ok, processed_at);
