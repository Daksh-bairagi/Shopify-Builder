-- Migration 002: add script_tag_id to fix_backups for Script Tags rollback support
-- Run after 001_initial.sql

ALTER TABLE fix_backups
  ADD COLUMN IF NOT EXISTS script_tag_id VARCHAR(256);

-- Update field_type documentation — now includes 'taxonomy' and 'script_tag'
COMMENT ON COLUMN fix_backups.field_type IS
  'title | product_type | metafield | alt_text | taxonomy | script_tag';
