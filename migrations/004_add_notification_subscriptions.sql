-- Add notification_subscriptions table for push notification delivery

CREATE TABLE IF NOT EXISTS notification_subscriptions (
  id                  UUID PRIMARY KEY,
  user_id             UUID NOT NULL,
  endpoint            TEXT NOT NULL,
  subscription_keys   JSON,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_subscriptions_user ON notification_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_subscriptions_endpoint ON notification_subscriptions(endpoint);
