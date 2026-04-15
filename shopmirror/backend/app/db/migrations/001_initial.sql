CREATE TABLE analysis_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_url       VARCHAR(512) NOT NULL,
  store_domain    VARCHAR(256),
  has_token       BOOLEAN DEFAULT FALSE,
  status          VARCHAR(32) DEFAULT 'queued',
  -- status values: queued | ingesting | auditing | simulating | complete | failed | awaiting_approval
  progress_step   VARCHAR(256),
  progress_pct    INTEGER DEFAULT 0,
  report_json     JSONB,
  fix_plan_json   JSONB,
  error_message   TEXT,
  created_at      TIMESTAMP DEFAULT NOW(),
  completed_at    TIMESTAMP
);

CREATE TABLE fix_backups (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          UUID REFERENCES analysis_jobs(id),
  fix_id          VARCHAR(64) NOT NULL,
  product_id      VARCHAR(128),
  field_type      VARCHAR(64),
  -- field_type values: title | product_type | metafield | alt_text
  field_key       VARCHAR(128),
  original_value  TEXT,
  new_value       TEXT,
  shopify_gid     VARCHAR(256),
  applied_at      TIMESTAMP DEFAULT NOW(),
  rolled_back     BOOLEAN DEFAULT FALSE
);
