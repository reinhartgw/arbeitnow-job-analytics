from pathlib import Path
from clean_jobs import parse_file
from db import get_connection, upsert_job

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def list_raw_files() -> list[Path]:
    return sorted(RAW_DIR.glob("*.json"))

def load_file(cur, file: Path) -> tuple[int, int]:
    """Upsert every job in one snapshot. Returns (jobs seen, jobs loaded).

    Each upsert runs inside its own savepoint, so a failing row rolls back
    only itself. A plain rollback here would also discard every earlier,
    still-uncommitted row from the same file.
    """
    jobs = parse_file(file)
    loaded = 0

    for job in jobs:
        cur.execute("SAVEPOINT job_upsert")
        try:
            upsert_job(cur, job)
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT job_upsert")
            print(f"Failed on {job['slug']}: {e}")
            continue
        cur.execute("RELEASE SAVEPOINT job_upsert")
        loaded += 1

    return len(jobs), loaded

def main() -> None:
    connection = get_connection()
    cur = connection.cursor()
    total = 0
    successful = 0

    try:
        for file in list_raw_files():
            seen, loaded = load_file(cur, file)
            connection.commit()
            total += seen
            successful += loaded
            print(f"{file.name}: {loaded}/{seen} loaded")
    finally:
        cur.close()
        connection.close()

    print(f"Done - {successful}/{total} jobs")

if __name__ == "__main__":
    main()
