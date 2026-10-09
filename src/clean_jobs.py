import re
import html
import json

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
from langdetect import detect, LangDetectException, DetectorFactory

ARBEITNOW_FOOTER_RE = re.compile(r"Find (?:more English Speaking )?Jobs in .+? on Arbeitnow\.?\s*$")
DetectorFactory.seed = 0

def strip_footer(text: str) -> str:
  return ARBEITNOW_FOOTER_RE.sub("", text).rstrip()

def clean_job(job: dict, fetched_at: str) -> dict:
  decoded = html.unescape(job["description"])
  description = BeautifulSoup(decoded, "html.parser").get_text()
  description = strip_footer(description)  # remove the Arbeitnow footer from the description

  try:
    language = detect(description) if description.strip() else None
  except LangDetectException:
    language = None

  return {
    "slug": job["slug"],
    "company_name": job["company_name"],
    "title": job["title"],
    "description": description,
    "remote": job["remote"],
    "url": job["url"],
    "job_types": job["job_types"],
    "location": job["location"],
    "language": language,
    "created_at": datetime.fromtimestamp(job["created_at"], tz=timezone.utc),
    "last_seen_at": datetime.fromisoformat(fetched_at)
  }

def parse_file(file_path: Path) -> list[dict]:
  with open(file_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

  fetched_at = payload["_fetched_at"]
  jobs = payload.get("data", [])

  return [clean_job(job, fetched_at) for job in jobs]

def main():
  jobs = parse_file("data/raw/jobs_raw_20260923T064604Z.json")

  for job in jobs:
    print(job)

if __name__ == "__main__":
  main()