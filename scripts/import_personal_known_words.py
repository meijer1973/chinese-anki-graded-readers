from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_anki_chinese


FIELDS = [
    "word",
    "pinyin",
    "meaning",
    "source",
    "status",
    "reading_confidence",
    "allow_in_personal_readers",
    "notes",
]


def source_files(paths: list[str | Path]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(item for item in path.rglob("*") if item.suffix.lower() in {".csv", ".txt", ".md"}))
        elif path.exists():
            files.append(path)
    return files


def clean_word(value: str) -> str:
    return value.strip().strip("\ufeff")


def read_csv_terms(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            word = clean_word(row.get("term", ""))
            if not word:
                continue
            rows.append(
                {
                    "word": word,
                    "phrase": row.get("phrase", "").strip(),
                    "meaning": row.get("meaning1", "").strip(),
                    "source": path.name,
                }
            )
    return rows


def read_text_terms(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        for raw_word in line.split():
            word = clean_word(raw_word)
            if not word or word.startswith("#"):
                continue
            rows.append({"word": word, "phrase": "", "meaning": "", "source": path.name})
    return rows


def load_source_rows(paths: list[str | Path]) -> list[dict]:
    rows: list[dict] = []
    for path in source_files(paths):
        if path.suffix.lower() == ".csv":
            rows.extend(read_csv_terms(path))
        elif path.suffix.lower() in {".txt", ".md"}:
            rows.extend(read_text_terms(path))
    return rows


def cedict_meaning(word: str, entries_by_word: dict) -> str:
    entries = entries_by_word.get(word, [])
    if entries:
        return build_anki_chinese.concise_definitions(entries)
    return ""


def build_rows(
    source_rows: list[dict],
    *,
    default_status: str,
    default_confidence: int,
    default_allow: str,
) -> tuple[list[dict], dict]:
    entries_by_word = build_anki_chinese.parse_cedict()
    grouped: dict[str, list[dict]] = defaultdict(list)
    skipped_whitespace: list[str] = []
    for row in source_rows:
        word = row["word"]
        if any(char.isspace() for char in word):
            skipped_whitespace.append(word)
            continue
        grouped[word].append(row)

    output_rows: list[dict] = []
    for word in sorted(grouped):
        sources = sorted({row["source"] for row in grouped[word] if row.get("source")})
        fallback_meaning = next((row["meaning"] for row in grouped[word] if row.get("meaning")), "")
        output_rows.append(
            {
                "word": word,
                "pinyin": build_anki_chinese.generated_pinyin(word),
                "meaning": cedict_meaning(word, entries_by_word) or fallback_meaning,
                "source": "; ".join(sources),
                "status": default_status,
                "reading_confidence": str(default_confidence),
                "allow_in_personal_readers": default_allow,
                "notes": "Imported as a personal-known candidate; review status/confidence before broad use.",
            }
        )

    report = {
        "source_row_count": len(source_rows),
        "unique_word_count": len(output_rows),
        "skipped_whitespace_count": len(skipped_whitespace),
        "skipped_whitespace": skipped_whitespace,
    }
    return output_rows, report


def write_tsv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_existing_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} is missing required column(s): {', '.join(missing)}")
        return [{field: row.get(field, "") for field in FIELDS} for row in reader if row.get("word", "").strip()]


def merge_rows(existing_rows: list[dict], imported_rows: list[dict]) -> tuple[list[dict], dict]:
    merged_by_word: dict[str, dict] = {}
    for row in existing_rows:
        word = clean_word(row["word"])
        if not word:
            continue
        normalized = {field: row.get(field, "") for field in FIELDS}
        normalized["word"] = word
        merged_by_word[word] = normalized

    added_words: list[str] = []
    updated_words: list[str] = []
    for row in imported_rows:
        word = clean_word(row["word"])
        if not word:
            continue
        if word not in merged_by_word:
            merged_by_word[word] = row
            added_words.append(word)
            continue

        existing = merged_by_word[word]
        existing_sources = {item.strip() for item in existing.get("source", "").split(";") if item.strip()}
        incoming_sources = {item.strip() for item in row.get("source", "").split(";") if item.strip()}
        combined_sources = sorted(existing_sources | incoming_sources)
        if combined_sources and combined_sources != sorted(existing_sources):
            existing["source"] = "; ".join(combined_sources)
            updated_words.append(word)
        if not existing.get("meaning") and row.get("meaning"):
            existing["meaning"] = row["meaning"]
        if not existing.get("pinyin") and row.get("pinyin"):
            existing["pinyin"] = row["pinyin"]

    merged_rows = [merged_by_word[word] for word in sorted(merged_by_word)]
    report = {
        "existing_word_count": len({row["word"] for row in existing_rows if row.get("word", "").strip()}),
        "imported_unique_word_count": len({row["word"] for row in imported_rows if row.get("word", "").strip()}),
        "merged_word_count": len(merged_rows),
        "added_word_count": len(added_words),
        "updated_source_count": len(set(updated_words)),
        "added_words": sorted(set(added_words)),
        "updated_source_words": sorted(set(updated_words)),
    }
    return merged_rows, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a learner-profile personal-known TSV from CSV/TXT exports.")
    parser.add_argument("--sources", nargs="+", required=True, help="Files or directories containing LingQ CSV or one-word-per-line TXT exports.")
    parser.add_argument("--out", required=True, help="Output personal_known_words.tsv path.")
    parser.add_argument("--merge-existing", action="store_true", help="Merge imported words into an existing TSV instead of replacing it.")
    parser.add_argument("--status", default="known_passive", choices=["known_active", "known_passive", "learning", "uncertain"])
    parser.add_argument("--reading-confidence", type=int, default=4)
    parser.add_argument("--allow", default="yes", choices=["yes", "no"])
    args = parser.parse_args()

    imported_rows, report = build_rows(
        load_source_rows(args.sources),
        default_status=args.status,
        default_confidence=args.reading_confidence,
        default_allow=args.allow,
    )
    if args.merge_existing:
        rows, merge_report = merge_rows(read_existing_tsv(Path(args.out)), imported_rows)
        report.update(merge_report)
    else:
        rows = imported_rows
    write_tsv(Path(args.out), rows)
    format_report = {
        **report,
        "out": args.out,
        "added_word_count": report.get("added_word_count", len(rows)),
        "updated_source_count": report.get("updated_source_count", 0),
        "merged_word_count": report.get("merged_word_count", len(rows)),
    }
    print(
        "wrote={out} source_rows={source_row_count} unique_words={unique_word_count} "
        "skipped_whitespace={skipped_whitespace_count} added={added_word_count} "
        "updated_sources={updated_source_count} merged_words={merged_word_count}".format(**format_report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
