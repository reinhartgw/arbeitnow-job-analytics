CREATE TABLE IF NOT EXISTS jobs (
    slug          TEXT PRIMARY KEY,
    company_name  TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    remote        BOOLEAN NOT NULL,
    url           TEXT NOT NULL,
    job_types     TEXT[],
    location      TEXT,
    language      TEXT,
    created_at    TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ NOT NULL
);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS language TEXT;

CREATE TABLE IF NOT EXISTS job_tags (
    slug TEXT NOT NULL REFERENCES jobs(slug) ON DELETE CASCADE,
    tag  TEXT NOT NULL,
    PRIMARY KEY (slug, tag)
);

-- Ledger of which raw snapshots have already been loaded, so load_jobs does
-- not re-parse the whole of data/raw on every run. Keyed by file name because
-- that is what the loader iterates; run_id groups the pages of one fetch.
CREATE TABLE IF NOT EXISTS loaded_files (
    file_name   TEXT PRIMARY KEY,
    run_id      TEXT,
    page        INTEGER,
    jobs_seen   INTEGER NOT NULL,
    jobs_loaded INTEGER NOT NULL,
    fetched_at  TIMESTAMPTZ,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS loaded_files_run_id_idx ON loaded_files (run_id);
