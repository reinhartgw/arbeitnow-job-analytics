from models import JobListing
from bs4 import BeautifulSoup
import datetime
import json
from datetime import datetime, timezone

def clean_job(job: dict, fetched_at: str) -> dict:
  soup = BeautifulSoup(job["description"], "html.parser").get_text()

  return {
    "slug": job["slug"],
    "company_name": job["company_name"],
    "title": job["title"],
    "description": soup,
    "remote": job["remote"],
    "url": job["url"],
    "job_types": job["job_types"],
    "location": job["location"],
    "created_at": datetime.fromtimestamp(job["created_at"], tz=timezone.utc),
    "_last_seen_at": datetime.fromisoformat(fetched_at)
  }

def parse_file(file_path: str) -> list[dict]:
  with open(file_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

  last_seen_at = payload["_last_seen_at"]
  jobs = payload.get("data", [])

  return [clean_job(job, last_seen_at) for job in jobs]

def main():
  jobs = parse_file("data/raw/jobs_raw_20260923T064604Z.json")

  for job in jobs:
    print(job)

if __name__ == "__main__":
  main()