"""
We already confirmed slugs are unique WITHIN each single page/file.
This checks the other case: does the same slug appear across DIFFERENT
files? That would explain 800 upserts collapsing into fewer distinct
rows — ON CONFLICT doing its job, not a bug.
"""

import json
from collections import Counter
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    all_slugs = []

    for file in sorted(RAW_DIR.glob("*.json")):
        payload = json.loads(file.read_text())
        for job in payload.get("data", []):
            all_slugs.append((job["slug"], file.name))

    counts = Counter(slug for slug, _ in all_slugs)
    duplicates = {slug: n for slug, n in counts.items() if n > 1}

    print(f"Total job entries across all files: {len(all_slugs)}")
    print(f"Unique slugs: {len(counts)}")
    print(f"Duplicate slugs: {len(duplicates)}")

    if duplicates:
        print("\nWhich files each duplicate appeared in:")
        for slug in duplicates:
            files = [f for s, f in all_slugs if s == slug]
            print(f"  {slug}: {files}")


if __name__ == "__main__":
    main()