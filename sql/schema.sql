CREATE TABLE IF NOT EXISTS jobs (
    slug          TEXT PRIMARY KEY,
    company_name  TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    remote        BOOLEAN NOT NULL,
    url           TEXT NOT NULL,
    job_types     TEXT[],
    location      TEXT,
    created_at    TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS job_tags (
    slug TEXT NOT NULL REFERENCES jobs(slug) ON DELETE CASCADE,
    tag  TEXT NOT NULL,
    PRIMARY KEY (slug, tag)
);