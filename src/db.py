import os

import psycopg2
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
