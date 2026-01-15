-- Add allow_comment column to repo_policies table
-- DuckDB doesn't support ALTER TABLE ADD COLUMN with NOT NULL constraints
-- So we add without the constraint first, update existing rows, then we can't add the constraint
-- For new databases, the initial schema already has this column

ALTER TABLE repo_policies ADD COLUMN IF NOT EXISTS allow_comment BOOLEAN DEFAULT true;

-- Update any existing rows to have the default value
UPDATE repo_policies SET allow_comment = true WHERE allow_comment IS NULL;

