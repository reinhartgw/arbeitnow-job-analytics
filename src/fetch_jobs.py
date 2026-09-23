import json, time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

import requests

API_URL = "https://www.arbeitnow.com/api/job-board-api"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
MAX_PAGES = 5

def fetch(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # blow up loudly if the API didn't return 200
    return response.json()

@dataclass
class JobListing:
    slug: str
    company_name: str
    title: str
    description: str
    remote: bool
    url: str
    tags: list[str]
    job_types: list[str]
    location: str
    created_at: int 

def main() -> None:    
    jobListings: list[JobListing] = []
    next_url = API_URL
    pages_fetched = 0
    out_path = None
 
    while next_url and pages_fetched < MAX_PAGES:
        if pages_fetched > 0:
            time.sleep(5)
        
        try:
            payload = fetch(next_url)
        except requests.exceptions.RequestException as e:
            print(f"Fetch failed on page {pages_fetched + 1}: {e}")
            break

        jobs = payload.get("data", [])

        for job in jobs:
            # jobListings.append(JobListing(
            #     job["slug"], job["company_name"], job["title"], 
            #     job["description"], job["remote"], job["url"], 
            #     job["tags"], job["job_types"], job["location"], job["created_at"]))
            jobListings.append(JobListing(**job))
        
        pages_fetched += 1
        payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = RAW_DIR / f"jobs_raw_{stamp}.json"
        out_path.write_text(json.dumps(payload, indent=2))

        links = payload.get("links", {})
        next_url = links.get("next")

    print("Total Job Listings: ", len(jobListings))
    if jobListings:
        print("Example 1: ", jobListings[1])

    # # save the whole raw response, timestamped, so you have a real snapshot
    # # to design your tables against (and a fixture for testing later)
    
    print(f"\nSaved raw response to {out_path}")


if __name__ == "__main__":
    main()
