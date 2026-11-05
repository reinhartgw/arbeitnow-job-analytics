import re
import html
import json

from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from langdetect import detect, LangDetectException, DetectorFactory

ARBEITNOW_FOOTER_RE = re.compile(r"Find (?:more English Speaking )?Jobs in .+? on Arbeitnow\.?\s*$")

# Matches the UTC stamp in both the current snapshot name
# (jobs_raw_20260922T070835Z_p01.json) and the older unpaged one.
RAW_STAMP_RE = re.compile(r"jobs_raw_(\d{8}T\d{6}Z)")
RAW_STAMP_FORMAT = "%Y%m%dT%H%M%SZ"

DetectorFactory.seed = 0

# What a malformed record raises inside clean_job: a missing field (KeyError),
# a null or wrongly typed field (TypeError), or an unusable timestamp
# (ValueError, OverflowError, OSError).
CLEAN_ERRORS = (KeyError, TypeError, ValueError, OverflowError, OSError)

@dataclass
class ParsedSnapshot:
  jobs: list[dict]
  skipped: list[str]  # one "<slug>: <error>" line per record that couldn't be cleaned
  file_name: str
  run_id: str | None
  page: int | None
  fetched_at: datetime

  @property
  def seen(self) -> int:
    return len(self.jobs) + len(self.skipped)

  @property
  def meta(self) -> dict:
    """The fields db.record_loaded_file expects."""
    return {
      "file_name": self.file_name,
      "run_id": self.run_id,
      "page": self.page,
      "fetched_at": self.fetched_at,
    }

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

def resolve_run_id(file_path: Path, payload: dict) -> str | None:
  """The run a snapshot belongs to: _run_id if recorded, else the filename
  stamp. Each legacy snapshot was written with its own stamp, so it becomes
  its own one-page run."""
  recorded = payload.get("_run_id")
  if recorded:
    return recorded

  match = RAW_STAMP_RE.search(file_path.name)
  return match.group(1) if match else None

def clean_job(job: dict, fetched_at: datetime) -> dict:
  decoded = html.unescape(job["description"])
  description = BeautifulSoup(decoded, "html.parser").get_text()
  description = strip_footer(description)  # remove the Arbeitnow footer from the description

  try:
    language = detect(description) if description.strip() else None
  except LangDetectException:
    language = None

  tags = job["tags"]
  if tags is not None and not isinstance(tags, list):
    raise TypeError(f"tags is {type(tags).__name__}, expected a list")

  return {
    "slug": job["slug"],
    "company_name": job["company_name"],
    "title": job["title"],
    "description": description,
    "remote": job["remote"],
    "url": job["url"],
    "job_types": job["job_types"],
    "tags": tags,
    "location": job["location"],
    "language": language,
    "created_at": datetime.fromtimestamp(job["created_at"], tz=timezone.utc),
    "last_seen_at": fetched_at
  }

def parse_file(file_path: Path | str) -> ParsedSnapshot:
  """Clean every record in one snapshot.

  A record that can't be cleaned is skipped and reported rather than raised,
  so one bad record doesn't stop the rest of the file, or the whole load.
  """
  file_path = Path(file_path)

  with open(file_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

  fetched_at = resolve_fetched_at(file_path, payload)
  jobs: list[dict] = []
  skipped: list[str] = []

  for record in payload.get("data", []):
    try:
      jobs.append(clean_job(record, fetched_at))
    except CLEAN_ERRORS as e:
      slug = record.get("slug", "<no slug>") if isinstance(record, dict) else "<not an object>"
      skipped.append(f"{slug}: {type(e).__name__} {e}")

  return ParsedSnapshot(
    jobs=jobs,
    skipped=skipped,
    file_name=file_path.name,
    run_id=resolve_run_id(file_path, payload),
    page=payload.get("_page"),
    fetched_at=fetched_at,
  )
