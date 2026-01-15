-- Add columns for notification throttling and deduplication

-- Add priority field for throttling (1=low, 5=high)
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 3;

-- Add dedupe_key for deduplication (hash of event_type + repo + target)
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dedupe_key TEXT;

-- Add profile for tracking which profile was active when notification was created
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS profile TEXT DEFAULT 'default';

-- Create index on dedupe_key for fast lookups
CREATE INDEX IF NOT EXISTS idx_notifications_dedupe_key ON notifications(dedupe_key, created_at DESC);

-- Create index on priority for filtering
CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications(user_id, priority);
