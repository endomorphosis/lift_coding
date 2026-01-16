-- Add platform field to notification_subscriptions for APNS/FCM support

ALTER TABLE notification_subscriptions 
ADD COLUMN IF NOT EXISTS platform VARCHAR(20) DEFAULT 'webpush';

-- Create index on platform for efficient filtering
CREATE INDEX IF NOT EXISTS idx_notification_subscriptions_platform ON notification_subscriptions(platform);

-- Update existing records to have 'webpush' platform (already default but explicit)
UPDATE notification_subscriptions SET platform = 'webpush' WHERE platform IS NULL;
