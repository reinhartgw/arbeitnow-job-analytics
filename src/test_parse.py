"""
Pure local test: does BeautifulSoup actually strip HTML from a real
description field? No Supabase, no insert, no upsert logic involved —
just reads one raw file and prints before/after.
"""

import html
import json
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    test_file = next(RAW_DIR.glob("*.json"))
    payload = json.loads(test_file.read_text())
    job = payload["data"][0]

    print(f"Testing slug: {job['slug']}\n")

    raw_description = job["description"]

    # the raw text contains HTML-ESCAPED tags (literal "&lt;p&gt;"), not real
    # ones — unescape first so there's actual markup for BeautifulSoup to parse
    decoded = html.unescape(raw_description)
    cleaned = BeautifulSoup(decoded, "html.parser").get_text()

    print("RAW (first 300 chars):")
    print(raw_description[:300])
    print("\n" + "=" * 60 + "\n")
    print("CLEANED (first 300 chars):")
    print(cleaned[:300])


if __name__ == "__main__":
    main()