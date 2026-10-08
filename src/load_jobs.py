from pathlib import Path
import json 

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

def listFiles():
    files = RAW_DIR.glob("*.json")

    for file in files:
        with open(file, "r") as f:
            data = json.load(f)

        fetched_at = data.get("_fetched_at")

        jobs = data.get("data", [])
        job_count = len(jobs)

        print(f"File: {file.name}")
        print(f"Fetched at: {fetched_at}")
        print(f"Jobs: {job_count}")

def main() -> None:
    from clean_jobs import parse_file
    from db import get_connection, upsert_job

    

if __name__ == "__main__":
    listFiles()