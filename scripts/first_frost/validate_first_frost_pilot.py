from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.first_frost.content import MANIFEST_PATH, REQUIRED_COLUMNS, load_manifest


EXPECTED_COUNT = 60
REQUIRED_TAGS = {
    "chinese_vocab",
    "source_lingq",
    "reading_novel",
    "genre_romance",
    "book_first_frost",
    "pilot_first_frost_01",
}
REQUIRED_CONSTRUCTIONS = {
    "哪怕": ("哪怕", "也"),
    "不但": ("不但", "还"),
}


def validate_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    rows = load_manifest(path)
    errors: list[str] = []
    warnings: list[str] = []
    words = [row["Word"] for row in rows]

    if len(rows) != EXPECTED_COUNT:
        errors.append(f"Expected {EXPECTED_COUNT} rows, found {len(rows)}")
    duplicates = sorted({word for word in words if words.count(word) > 1})
    if duplicates:
        errors.append(f"Duplicate words: {duplicates}")

    priorities: list[int] = []
    for row_number, row in enumerate(rows, start=2):
        word = row["Word"] or f"row {row_number}"
        required_content = (
            "Word",
            "Pinyin",
            "Meaning",
            "Example",
            "Example Pinyin",
            "Example Meaning",
            "Source",
            "Tags",
            "Pilot Priority",
            "Usage Note",
            "Input File",
            "Input Row",
        )
        blank = [field for field in required_content if not row[field]]
        if blank:
            errors.append(f"{word}: blank required fields {blank}")
        if row["Production Card"]:
            errors.append(f"{word}: Production Card must be blank")
        if row["Sentence Card"].lower() != "yes":
            errors.append(f"{word}: Sentence Card must be yes")
        if row["Frequency Rank"]:
            errors.append(f"{word}: manifest Frequency Rank must be blank")

        tags = set(row["Tags"].split())
        missing_tags = sorted(REQUIRED_TAGS - tags)
        if missing_tags:
            errors.append(f"{word}: missing required tags {missing_tags}")
        if word and word not in row["Example"]:
            errors.append(f"{word}: example does not contain the target")

        try:
            priorities.append(int(row["Pilot Priority"]))
        except ValueError:
            errors.append(f"{word}: invalid Pilot Priority {row['Pilot Priority']!r}")

    if sorted(priorities) != list(range(1, EXPECTED_COUNT + 1)):
        errors.append("Pilot Priority must contain each integer from 1 through 60 exactly once")

    by_word = {row["Word"]: row for row in rows}
    for word, fragments in REQUIRED_CONSTRUCTIONS.items():
        example = by_word.get(word, {}).get("Example", "")
        if not all(fragment in example for fragment in fragments):
            errors.append(f"{word}: reviewed example must preserve {' / '.join(fragments)}")

    sheng = by_word.get("盛")
    if not sheng:
        errors.append("Missing 盛 sense-check row")
    else:
        if not sheng["Pinyin"].startswith("chéng"):
            errors.append("盛: pilot reading must lead with chéng")
        if "盛" not in sheng["Example"] or "汤" not in sheng["Example"]:
            errors.append("盛: example must demonstrate the chéng serve/ladle sense")

    return {
        "status": "PASS" if not errors else "ERROR",
        "manifest": str(path),
        "columns": list(REQUIRED_COLUMNS),
        "row_count": len(rows),
        "unique_word_count": len(set(words)),
        "priority_min": min(priorities) if priorities else None,
        "priority_max": max(priorities) if priorities else None,
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the reviewed First Frost 60-word pilot manifest.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_manifest(args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
