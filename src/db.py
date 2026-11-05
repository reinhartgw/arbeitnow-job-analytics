import os

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv() 

DB_URL = os.environ.get("SUPABASE_DB_URL")

def get_connection() -> psycopg2.extensions.connection:
    if not DB_URL:
        raise RuntimeError(
            "SUPABASE_DB_URL not found."
        )

    return psycopg2.connect(DB_URL)

def upsert_job(cur, job: dict) -> None:
  query = """
    INSERT INTO jobs (slug, company_name, title, description, remote, url, job_types, location, language, created_at, first_seen_at, last_seen_at)
    VALUES (%(slug)s, %(company_name)s, %(title)s, %(description)s, %(remote)s, %(url)s, %(job_types)s, %(location)s, %(language)s, %(created_at)s, %(last_seen_at)s, %(last_seen_at)s)
    ON CONFLICT (slug) DO UPDATE SET 
      company_name = EXCLUDED.company_name,
      title        = EXCLUDED.title,
      description  = EXCLUDED.description,
      remote       = EXCLUDED.remote,
      url          = EXCLUDED.url,
      job_types    = EXCLUDED.job_types,
      location     = EXCLUDED.location,
      language     = EXCLUDED.language,
      last_seen_at = GREATEST(jobs.last_seen_at, EXCLUDED.last_seen_at);
  """
  cur.execute(query, job)

def replace_job_tags(cur, slug: str, tags: list[str] | None) -> None:
  """Make job_tags mirror the tags the API currently reports for this slug.

  Delete-then-insert rather than insert-only, so a tag dropped upstream also
  disappears here. Must run in the same transaction as the jobs upsert,
  otherwise a failure can leave a job row with stale or missing tags.
  """
  cur.execute("DELETE FROM job_tags WHERE slug = %s", (slug,))

  # Arbeitnow tags are free text and occasionally repeat within one job, which
  # would collide on the (slug, tag) primary key.
  cleaned = sorted({tag.strip() for tag in (tags or []) if tag and tag.strip()})
  if not cleaned:
    return

  execute_values(
    cur,
    "INSERT INTO job_tags (slug, tag) VALUES %s ON CONFLICT DO NOTHING",
    [(slug, tag) for tag in cleaned],
  )

def loaded_file_names(cur) -> set[str]:
  """Snapshot file names already recorded as loaded."""
  cur.execute("SELECT file_name FROM loaded_files")
  return {row[0] for row in cur.fetchall()}

def record_loaded_file(cur, meta: dict, jobs_seen: int, jobs_loaded: int) -> None:
  query = """
    INSERT INTO loaded_files (file_name, run_id, page, jobs_seen, jobs_loaded, fetched_at)
    VALUES (%(file_name)s, %(run_id)s, %(page)s, %(jobs_seen)s, %(jobs_loaded)s, %(fetched_at)s)
    ON CONFLICT (file_name) DO UPDATE SET
      run_id      = EXCLUDED.run_id,
      page        = EXCLUDED.page,
      jobs_seen   = EXCLUDED.jobs_seen,
      jobs_loaded = EXCLUDED.jobs_loaded,
      fetched_at  = EXCLUDED.fetched_at,
      loaded_at   = now();
  """
  cur.execute(query, {**meta, "jobs_seen": jobs_seen, "jobs_loaded": jobs_loaded})
