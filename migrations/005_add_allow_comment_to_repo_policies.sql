-- Add allow_comment column to repo_policies table

ALTER TABLE repo_policies ADD COLUMN IF NOT EXISTS allow_comment BOOLEAN NOT NULL DEFAULT true;
