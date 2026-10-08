import json
from collections import Counter
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        print("No raw files found.")
        return

    any_dupes = False
    for file in files:
        payload = json.loads(file.read_text())
        slugs = [job["slug"] for job in payload.get("data", [])]
        counts = Counter(slugs)
        dupes = {s: n for s, n in counts.items() if n > 1}

        status = "OK" if not dupes else f"DUPLICATES FOUND: {dupes}"
        print(f"{file.name}: {len(slugs)} jobs, {len(counts)} unique -> {status}")

        if dupes:
            any_dupes = True

    print("\nResult:", "slug is safe as a primary key" if not any_dupes else "slug collided within a page — needs a different key")


if __name__ == "__main__":
    main()