from pathlib import Path
from clean_jobs import parse_file
from db import get_connection, upsert_job

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def list_raw_files() -> list[Path]:
    return sorted(RAW_DIR.glob("*.json"))

def main() -> None:
    connection = get_connection()
    cur = connection.cursor()
    total = 0
    successful = 0

    try:
        for file in list_raw_files():
            jobs = parse_file(file)
            for job in jobs:
                total += 1
                try:
                    upsert_job(cur, job)
                    successful += 1
                except Exception as e:
                    print(f"Failed on {job['slug']}: {e}")
                    connection.rollback()
                    continue
            connection.commit()
            print(f"{file.name}: {len(jobs)} processed")
    finally:
        cur.close()
        connection.close()

    print(f"Done - {successful}/{total} jobs")

if __name__ == "__main__":
    main()