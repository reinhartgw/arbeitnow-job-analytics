import os

import psycopg2
from dotenv import load_dotenv

load_dotenv() 

DB_URL = os.environ.get("SUPABASE_DB_URL")

# Test Imports
from load_jobs import RAW_DIR
from clean_jobs import parse_file

def get_connection() -> psycopg2.extensions.connection:
    if not DB_URL:
        raise RuntimeError(
            "SUPABASE_DB_URL not found."
        )

    return psycopg2.connect(DB_URL)

def upsert_job(cur, job: dict) -> None:
  query = """
    INSERT INTO jobs (slug, company_name, title, description, remote, url, job_types, location, created_at, first_seen_at, last_seen_at)
    VALUES (%(slug)s, %(company_name)s, %(title)s, %(description)s, %(remote)s, %(url)s, %(job_types)s, %(location)s, %(created_at)s, %(last_seen_at)s, %(last_seen_at)s)
    ON CONFLICT (slug) DO UPDATE SET last_seen_at = GREATEST(jobs.last_seen_at, EXCLUDED.last_seen_at);
  """
  cur.execute(query, job)


def main() -> None:
    test_file = next(RAW_DIR.glob("*.json"))
    test_job = parse_file(test_file)[0]
    
    connection = get_connection()
    cur = connection.cursor()

    upsert_job(cur, test_job)
    connection.commit()

    cur.close()
    connection.close()

    print(f"Upserted: {test_job['slug']}")

if __name__ == "__main__":
    main()
