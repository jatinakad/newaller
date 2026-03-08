-- Migration: Add structured_data JSON column to patient_reports table
-- Run this against your PostgreSQL database if the table already exists.
-- If you're creating the DB fresh, SQLAlchemy's create_all will handle it automatically.

ALTER TABLE patient_reports
ADD COLUMN IF NOT EXISTS structured_data JSONB;
