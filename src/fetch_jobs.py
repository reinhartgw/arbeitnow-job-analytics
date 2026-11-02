import json
import time
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

import requests

from models import JobListing

API_URL = "https://www.arbeitnow.com/api/job-board-api"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
MAX_PAGES = 5
PAGE_DELAY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 10

MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 2
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Field names we actually model. Anything else the API sends is recorded in the
# raw snapshot but ignored when building JobListing objects.
JOB_FIELDS = {f.name for f in fields(JobListing)}


def describe(error: Exception) -> str:
    """Readable label for an exception. Timeouts stringify to '', so fall back
    to the class name rather than logging empty parentheses."""
    return str(error) or type(error).__name__


def retry_delay(attempt: int, error: Exception) -> float:
    """Exponential backoff, but honour Retry-After when the server sends one."""
    backoff = float(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    response = getattr(error, "response", None)
    if response is not None:
        header = response.headers.get("Retry-After")
        if header:
            try:
                # Never retry sooner than our own backoff.
                return max(float(header), backoff)
            except ValueError:
                pass  # Retry-After may be an HTTP date; backoff is good enough

    return backoff


def fetch(url: str) -> dict:
    """GET one page, retrying transient failures with exponential backoff.

    Connection errors, timeouts, truncated JSON, 429 and 5xx are retried.
    Any other 4xx fails immediately - a retry won't change the answer.
    Raises the last error once attempts are exhausted.
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)

            if response.status_code in RETRYABLE_STATUS:
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason}", response=response
                )

            response.raise_for_status()  # non-retryable 4xx stops here
            return response.json()

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status not in RETRYABLE_STATUS:
                raise
            last_error = e

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.JSONDecodeError,
        ) as e:
            last_error = e

        if attempt < MAX_ATTEMPTS:
            delay = retry_delay(attempt, last_error)
            print(
                f"  attempt {attempt}/{MAX_ATTEMPTS} failed "
                f"({describe(last_error)}) - retrying in {delay:.0f}s"
            )
            time.sleep(delay)

    raise last_error


def to_listing(job: dict) -> JobListing:
    """Build a JobListing from an API record.

    Unknown keys are dropped rather than raising, so a new upstream field
    doesn't abort the run. Genuinely missing fields are still an error.
    """
    known = {key: value for key, value in job.items() if key in JOB_FIELDS}

    missing = JOB_FIELDS - known.keys()
    if missing:
        slug = job.get("slug", "<no slug>")
        raise ValueError(f"{slug}: missing field(s) {sorted(missing)}")

    return JobListing(**known)


def main() -> None:
    # One stamp for the whole run, so every page of this run shares a prefix
    # and two pages written in the same second can't overwrite each other.
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    listings: list[JobListing] = []
    saved_paths: list[Path] = []
    unmodelled_fields: set[str] = set()
    skipped = 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    next_url = API_URL
    pages_fetched = 0

    while next_url and pages_fetched < MAX_PAGES:
        if pages_fetched > 0:
            time.sleep(PAGE_DELAY_SECONDS)

        try:
            payload = fetch(next_url)
        except requests.exceptions.RequestException as e:
            # Pages already saved stay on disk; the run just stops short.
            print(f"Giving up on page {pages_fetched + 1}: {describe(e)}")
            break

        pages_fetched += 1
        jobs = payload.get("data", [])

        for job in jobs:
            unmodelled_fields.update(job.keys() - JOB_FIELDS)
            try:
                listings.append(to_listing(job))
            except ValueError as e:
                skipped += 1
                print(f"Skipped malformed record - {e}")

        # Save the raw response untouched apart from provenance keys, so it
        # stays a faithful snapshot and a usable test fixture.
        payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()
        payload["_run_id"] = run_id
        payload["_page"] = pages_fetched

        out_path = RAW_DIR / f"jobs_raw_{run_id}_p{pages_fetched:02d}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        saved_paths.append(out_path)

        next_url = payload.get("links", {}).get("next")

    print(f"\nRun {run_id}: {len(listings)} listings from {pages_fetched} page(s)")

    if skipped:
        print(f"Skipped {skipped} malformed record(s)")

    if unmodelled_fields:
        print(
            "API sent field(s) not in models.JobListing: "
            f"{sorted(unmodelled_fields)}"
        )

    if listings:
        print(f"Example: {listings[0]}")

    if saved_paths:
        print(f"Saved {len(saved_paths)} snapshot(s):")
        for path in saved_paths:
            print(f"  {path.name}")
    else:
        print("No snapshots written.")


if __name__ == "__main__":
    main()
