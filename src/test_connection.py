import os

import psycopg2
from dotenv import load_dotenv

load_dotenv() 

DB_URL = os.environ.get("SUPABASE_DB_URL")


def main() -> None:
    if not DB_URL:
        raise RuntimeError(
            "SUPABASE_DB_URL not found."
        )

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]

    print("Connected successfully.")
    print("Postgres version:", version)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
