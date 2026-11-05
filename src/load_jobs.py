from pathlib import Path
from clean_jobs import parse_file
from db import (
    get_connection,
    loaded_file_names,
    record_loaded_file,
    replace_job_tags,
    upsert_job,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def list_raw_files() -> list[Path]:
    return sorted(RAW_DIR.glob("*.json"))

def load_file(cur, file: Path) -> tuple[int, int, int]:
    """Upsert every job in one snapshot and record the file in loaded_files.

    Returns (records seen, jobs loaded, records skipped as malformed).

    Each job's upsert and tag replacement run inside one savepoint, so a
    failure rolls back only that job, and never leaves a job row without its
    tags. A plain rollback here would also discard every earlier,
    still-uncommitted row from the same file.

    The loaded_files row is written in the same transaction as the jobs, so a
    file is recorded as loaded only if its rows were committed. A file with
    failed rows is still recorded, with jobs_loaded < jobs_seen; to load it
    again, delete its loaded_files row.
    """
    parsed = parse_file(file)
    for reason in parsed.skipped:
        print(f"Skipped malformed record - {reason}")

    loaded = 0

    for job in parsed.jobs:
        cur.execute("SAVEPOINT job_upsert")
        try:
            upsert_job(cur, job)
            replace_job_tags(cur, job["slug"], job["tags"])
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT job_upsert")
            print(f"Failed on {job['slug']}: {e}")
            continue
        cur.execute("RELEASE SAVEPOINT job_upsert")
        loaded += 1

    record_loaded_file(cur, parsed.meta, parsed.seen, loaded)
    return parsed.seen, loaded, len(parsed.skipped)

def main() -> None:
    connection = get_connection()
    cur = connection.cursor()
    total = 0
    successful = 0
    malformed = 0
    already_loaded = 0

    try:
        done = loaded_file_names(cur)

        for file in list_raw_files():
            if file.name in done:
                already_loaded += 1
                print(f"{file.name}: already loaded, skipped")
                continue

            seen, loaded, skipped = load_file(cur, file)
            connection.commit()
            total += seen
            successful += loaded
            malformed += skipped
            note = f", {skipped} skipped as malformed" if skipped else ""
            print(f"{file.name}: {loaded}/{seen} loaded{note}")
    finally:
        cur.close()
        connection.close()

    print(
        f"Done - {successful}/{total} jobs, {malformed} skipped as malformed, "
        f"{already_loaded} file(s) already loaded"
    )

if __name__ == "__main__":
    main()
