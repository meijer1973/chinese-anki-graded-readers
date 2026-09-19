from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = ROOT / "anki" / "hindi" / "hindi_core_100.tsv"
DEFAULT_SOURCES = ROOT / "anki" / "hindi" / "hindi_core_100.sources.json"
DEFAULT_REPORT = ROOT / "anki" / "hindi" / "reports" / "data_validation_report.json"

EXPECTED_COLUMNS = [
    "Frequency Rank",
    "Word",
    "Pronunciation",
    "Meaning",
    "Part of Speech",
    "Example",
    "Example Pronunciation",
    "Example Meaning",
    "Source",
    "Source Rank",
    "Labels",
    "Notes",
]

REQUIRED_NONEMPTY_FIELDS = [
    "Word",
    "Pronunciation",
    "Meaning",
    "Part of Speech",
    "Example",
    "Example Pronunciation",
    "Example Meaning",
    "Source",
    "Labels",
]

REQUIRED_PROVENANCE_FIELDS = [
    "source_title",
    "dataset_or_project_identifier",
    "source_organization_or_authors",
    "access_date",
    "source_license_or_redistribution_terms",
    "selection_procedure",
    "exclusions",
    "conflicting_rankings",
    "romanization_convention",
    "independent_content_confirmation",
]

PRODUCTION_COLUMN_PATTERNS = (
    "production",
    "recall",
    "reverse",
    "english to hindi",
    "sentence production",
)

DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")


class HindiDataValidationError(RuntimeError):
    """Raised when the Hindi starter dataset fails its mechanical contract."""


def _duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if value and count > 1)


def _walk_strings(value: Any, path: str = "metadata") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")


def load_rows(tsv_path: Path = DEFAULT_TSV) -> tuple[list[dict[str, str]], list[str], list[str]]:
    raw = tsv_path.read_text(encoding="utf-8-sig")
    physical_lines = raw.splitlines()
    raw_findings: list[str] = []
    expected_tabs = len(EXPECTED_COLUMNS) - 1

    if len(physical_lines) != 101:
        raw_findings.append(f"expected 101 physical lines including the header, found {len(physical_lines)}")
    for line_number, line in enumerate(physical_lines, start=1):
        tab_count = line.count("\t")
        if tab_count != expected_tabs:
            raw_findings.append(
                f"line {line_number} has {tab_count} tab separators; expected {expected_tabs}"
            )

    with tsv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = list(reader.fieldnames or [])
        rows = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raw_findings.append(f"row {row_number} contains extra tab-separated cells")
            normalized_row = {str(key): value if value is not None else "" for key, value in row.items() if key is not None}
            rows.append(normalized_row)
    return rows, header, raw_findings


def validate_dataset(
    *,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
) -> dict[str, Any]:
    errors: list[str] = []
    normalization_findings: list[str] = []
    whitespace_findings: list[str] = []
    rows, header, raw_findings = load_rows(tsv_path)
    errors.extend(raw_findings)

    if header != EXPECTED_COLUMNS:
        errors.append(f"TSV columns must be exactly {EXPECTED_COLUMNS!r}; found {header!r}")

    forbidden_columns = [
        column
        for column in header
        if any(pattern in column.casefold() for pattern in PRODUCTION_COLUMN_PATTERNS)
    ]
    if forbidden_columns:
        errors.append(f"production-card columns are forbidden: {forbidden_columns}")

    if len(rows) != 100:
        errors.append(f"expected exactly 100 TSV rows, found {len(rows)}")

    missing_field_counts = Counter()
    invalid_devanagari_words: list[str] = []
    invalid_devanagari_examples: list[str] = []
    target_missing_from_example: list[str] = []
    suspicious_latin_only: list[str] = []
    rank_values: list[int] = []
    invalid_ranks: list[str] = []
    sentence_lengths = Counter()
    sentence_length_outliers: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=2):
        for field in EXPECTED_COLUMNS:
            value = row.get(field, "")
            if "\t" in value or "\r" in value or "\n" in value:
                errors.append(f"row {index} field {field!r} contains an embedded tab or newline")
            if value != value.strip():
                whitespace_findings.append(f"row {index} field {field!r}")
            if value != unicodedata.normalize("NFC", value):
                normalization_findings.append(f"row {index} field {field!r}")

        for field in REQUIRED_NONEMPTY_FIELDS:
            if not row.get(field, ""):
                missing_field_counts[field] += 1

        word = row.get("Word", "")
        example = row.get("Example", "")
        if not DEVANAGARI_RE.search(word):
            invalid_devanagari_words.append(word or f"row {index}")
            if word and word.isascii():
                suspicious_latin_only.append(word)
        if not DEVANAGARI_RE.search(example):
            invalid_devanagari_examples.append(word or f"row {index}")
        if word and word not in example:
            target_missing_from_example.append(word)

        raw_rank = row.get("Frequency Rank", "")
        try:
            rank_values.append(int(raw_rank))
        except ValueError:
            invalid_ranks.append(raw_rank or f"row {index}")

        sentence_length = len(example.rstrip("।?!").split()) if example else 0
        sentence_lengths[sentence_length] += 1
        if sentence_length < 3 or sentence_length > 10:
            sentence_length_outliers.append({"word": word, "length": sentence_length})

    duplicate_words = _duplicates(row.get("Word", "") for row in rows)
    duplicate_examples = _duplicates(row.get("Example", "") for row in rows)

    if len({row.get("Word", "") for row in rows}) != 100:
        errors.append(
            f"expected exactly 100 unique Words, found {len({row.get('Word', '') for row in rows})}"
        )
    if duplicate_words:
        errors.append(f"duplicate Words: {duplicate_words}")
    if duplicate_examples:
        errors.append(f"duplicate example sentences: {duplicate_examples}")
    if invalid_ranks:
        errors.append(f"non-integer Frequency Rank values: {invalid_ranks}")
    if sorted(rank_values) != list(range(1, 101)):
        errors.append("Frequency Rank must contain every integer from 1 through 100 exactly once")
    if missing_field_counts:
        errors.append(f"required fields are empty: {dict(sorted(missing_field_counts.items()))}")
    if invalid_devanagari_words:
        errors.append(f"Words without Devanagari: {invalid_devanagari_words}")
    if invalid_devanagari_examples:
        errors.append(f"Examples without Devanagari: {invalid_devanagari_examples}")
    if target_missing_from_example:
        errors.append(f"exact target Word missing from Example: {target_missing_from_example}")
    if suspicious_latin_only:
        errors.append(f"suspicious Latin-only Hindi entries: {suspicious_latin_only}")
    if whitespace_findings:
        errors.append(f"leading/trailing whitespace found in {len(whitespace_findings)} fields")
    if normalization_findings:
        errors.append(f"non-NFC text found in {len(normalization_findings)} fields")
    if sentence_length_outliers:
        errors.append(f"example sentences outside the 3-10-word target: {sentence_length_outliers}")

    metadata: dict[str, Any] = {}
    metadata_missing_fields: list[str] = []
    metadata_normalization_findings: list[str] = []
    if not sources_path.exists():
        errors.append(f"source metadata JSON does not exist: {sources_path}")
    else:
        try:
            metadata = json.loads(sources_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"source metadata JSON is invalid: {exc}")
        else:
            metadata_missing_fields = [
                field for field in REQUIRED_PROVENANCE_FIELDS if not metadata.get(field)
            ]
            if metadata_missing_fields:
                errors.append(f"source metadata is missing required provenance fields: {metadata_missing_fields}")
            if metadata.get("access_date") != "2026-07-22":
                errors.append("source metadata access_date must be 2026-07-22")
            if metadata.get("editorial_content_independently_written") is not True:
                errors.append("source metadata must confirm independently written editorial content")
            for path, value in _walk_strings(metadata):
                if value != unicodedata.normalize("NFC", value):
                    metadata_normalization_findings.append(path)
            if metadata_normalization_findings:
                errors.append(
                    "non-NFC text found in source metadata: "
                    + ", ".join(metadata_normalization_findings[:10])
                )

    part_of_speech_distribution = Counter(row.get("Part of Speech", "") for row in rows)
    label_distribution = Counter()
    for row in rows:
        for label in row.get("Labels", "").split(";"):
            clean_label = label.strip()
            if clean_label:
                label_distribution[clean_label] += 1

    report = {
        "status": "PASS" if not errors else "FAIL",
        "tsv": str(tsv_path.resolve()),
        "sources": str(sources_path.resolve()),
        "row_count": len(rows),
        "unique_word_count": len({row.get("Word", "") for row in rows}),
        "rank_count": len(rank_values),
        "rank_min": min(rank_values) if rank_values else None,
        "rank_max": max(rank_values) if rank_values else None,
        "part_of_speech_distribution": dict(sorted(part_of_speech_distribution.items())),
        "label_distribution": dict(sorted(label_distribution.items())),
        "sentence_length_distribution": {
            str(length): count for length, count in sorted(sentence_lengths.items())
        },
        "sentence_length_outliers": sentence_length_outliers,
        "missing_field_counts": dict(sorted(missing_field_counts.items())),
        "duplicate_counts": {
            "words": len(duplicate_words),
            "examples": len(duplicate_examples),
        },
        "duplicates": {
            "words": duplicate_words,
            "examples": duplicate_examples,
        },
        "normalization_findings": {
            "tsv_non_nfc_fields": normalization_findings,
            "metadata_non_nfc_strings": metadata_normalization_findings,
            "leading_or_trailing_whitespace_fields": whitespace_findings,
        },
        "forbidden_columns": forbidden_columns,
        "metadata_missing_fields": metadata_missing_fields,
        "errors": errors,
    }
    return report


def write_report(report: dict[str, Any], report_path: Path = DEFAULT_REPORT) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_or_raise(
    *,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
    report_path: Path | None = DEFAULT_REPORT,
) -> dict[str, Any]:
    report = validate_dataset(tsv_path=tsv_path, sources_path=sources_path)
    if report_path is not None:
        write_report(report, report_path)
    if report["status"] != "PASS":
        raise HindiDataValidationError("; ".join(report["errors"]))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the isolated Hindi Core 100 TSV.")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = validate_dataset(tsv_path=args.tsv, sources_path=args.sources)
    write_report(report, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
