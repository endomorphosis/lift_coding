-- Add delivery tracking fields to notifications table

-- Add last_delivery_attempt timestamp
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS last_delivery_attempt TIMESTAMPTZ;

-- Add delivery_status field (pending, success, failed)
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_status TEXT DEFAULT 'pending';

-- Create index on delivery_status for monitoring/analytics
CREATE INDEX IF NOT EXISTS idx_notifications_delivery_status ON notifications(delivery_status, created_at DESC);
