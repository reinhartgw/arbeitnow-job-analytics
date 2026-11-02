import re
import html
import json

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
from langdetect import detect, LangDetectException, DetectorFactory

ARBEITNOW_FOOTER_RE = re.compile(r"Find (?:more English Speaking )?Jobs in .+? on Arbeitnow\.?\s*$")

# Matches the UTC stamp in both the current snapshot name
# (jobs_raw_20260922T070835Z_p01.json) and the older unpaged one.
RAW_STAMP_RE = re.compile(r"jobs_raw_(\d{8}T\d{6}Z)")
RAW_STAMP_FORMAT = "%Y%m%dT%H%M%SZ"

DetectorFactory.seed = 0

def strip_footer(text: str) -> str:
  return ARBEITNOW_FOOTER_RE.sub("", text).rstrip()

def resolve_fetched_at(file_path: Path, payload: dict) -> datetime:
  """Best available fetch time for a snapshot.

  Snapshots written before fetch_jobs started recording _fetched_at fall back
  to the stamp in the filename, which is when that page was written, and then
  to the file's mtime. Without this, every pre-existing snapshot raises
  KeyError on load.
  """
  recorded = payload.get("_fetched_at")
  if recorded:
    return datetime.fromisoformat(recorded)

  match = RAW_STAMP_RE.search(file_path.name)
  if match:
    return datetime.strptime(match.group(1), RAW_STAMP_FORMAT).replace(tzinfo=timezone.utc)

  return datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

def clean_job(job: dict, fetched_at: datetime) -> dict:
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
    "last_seen_at": fetched_at
  }

def parse_file(file_path: Path | str) -> list[dict]:
  file_path = Path(file_path)

  with open(file_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

  fetched_at = resolve_fetched_at(file_path, payload)
  jobs = payload.get("data", [])

  return [clean_job(job, fetched_at) for job in jobs]
