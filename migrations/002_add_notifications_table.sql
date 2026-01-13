-- Add notifications table for user-facing notifications

CREATE TABLE IF NOT EXISTS notifications (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL,
  event_type      TEXT NOT NULL,
  message         TEXT NOT NULL,
  metadata        JSON,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC);
