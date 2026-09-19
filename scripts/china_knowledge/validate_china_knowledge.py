from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.china_knowledge.config import (  # noqa: E402
    CATEGORIES,
    DEFAULT_GENERATED_IMPORT,
    DEFAULT_REPORTS_DIR,
    DEFAULT_SOURCES,
    DEFAULT_TSV,
    DIFFICULTIES,
    FIELDS,
)


DEFAULT_REPORT = DEFAULT_REPORTS_DIR / "data_validation_report.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTML_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
MEDIA_RE = re.compile(
    r"(?:\.(?:png|jpe?g|gif|webp|svg|mp3|ogg|wav|m4a)\b|\[sound:|<img\b|<audio\b|\btts\b)",
    re.IGNORECASE,
)
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
SOURCE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
TAG_RE = re.compile(r"^[a-z][a-z0-9_]*(?:::[a-z0-9_]+)+$")

PLAIN_TEXT_FIELDS = [field for field in FIELDS if field not in {"Source", "Tags"}]
REQUIRED_FIELDS = [
    "Knowledge ID",
    "Chinese Question",
    "English Question",
    "Chinese Answer",
    "English Answer",
    "Category",
    "Subcategory",
    "Difficulty",
    "Source",
    "Source Date",
    "Fact Checked",
]


class ChinaKnowledgeValidationError(RuntimeError):
    """Raised when the canonical China Knowledge dataset is not importable."""


def duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def normalized_question(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def split_tags(value: str) -> list[str]:
    """Accept canonical semicolons and Anki's conventional whitespace separator."""
    return [item for item in re.split(r"[;\s]+", value.strip()) if item]


def load_rows(tsv_path: Path = DEFAULT_TSV) -> tuple[list[dict[str, str]], list[str], list[str]]:
    findings: list[str] = []
    try:
        raw = tsv_path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return [], [], [f"TSV is not valid UTF-8: {exc}"]
    physical_lines = raw.splitlines()
    expected_tabs = len(FIELDS) - 1
    for line_number, line in enumerate(physical_lines, start=1):
        if line.count("\t") != expected_tabs:
            findings.append(
                f"line {line_number} has {line.count(chr(9))} tab separators; expected {expected_tabs}"
            )
    with tsv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = list(reader.fieldnames or [])
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                findings.append(f"row {row_number} contains extra tab-separated cells")
            rows.append(
                {
                    str(key): value if value is not None else ""
                    for key, value in row.items()
                    if key is not None
                }
            )
    return rows, header, findings


def load_sources(path: Path = DEFAULT_SOURCES) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, [f"source catalog is unreadable or invalid JSON: {exc}"]
    if document.get("schema_version") != 1:
        errors.append("source catalog schema_version must be 1")
    if not DATE_RE.fullmatch(str(document.get("access_date", ""))):
        errors.append("source catalog access_date must be an ISO date")
    sources = document.get("sources")
    if not isinstance(sources, dict) or not sources:
        errors.append("source catalog must contain a non-empty sources object")
        sources = {}
    for source_id, source in sources.items():
        if not SOURCE_ID_RE.fullmatch(str(source_id)):
            errors.append(f"invalid source ID {source_id!r}")
        if not isinstance(source, dict):
            errors.append(f"source {source_id!r} must be an object")
            continue
        for key in ("title", "organization", "url", "kind", "checked_on"):
            if not source.get(key):
                errors.append(f"source {source_id!r} is missing {key}")
        if source.get("checked_on") and not DATE_RE.fullmatch(str(source["checked_on"])):
            errors.append(f"source {source_id!r} checked_on is not an ISO date")
        if source.get("url") and not str(source["url"]).startswith("https://"):
            errors.append(f"source {source_id!r} URL must use https")
    return document, errors


def _near_duplicate_pairs(rows: list[dict[str, str]], field: str) -> list[dict[str, Any]]:
    normalized = [(row["Knowledge ID"], normalized_question(row.get(field, ""))) for row in rows]
    warnings: list[dict[str, Any]] = []
    for left_index, (left_id, left) in enumerate(normalized):
        if len(left) < 12:
            continue
        for right_id, right in normalized[left_index + 1 :]:
            if len(right) < 12 or left == right:
                continue
            length_ratio = min(len(left), len(right)) / max(len(left), len(right))
            if length_ratio < 0.82:
                continue
            ratio = SequenceMatcher(None, left, right).ratio()
            if ratio >= 0.94:
                warnings.append({"left": left_id, "right": right_id, "similarity": round(ratio, 3)})
    return warnings


def render_import_payload(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "knowledge_id": row["Knowledge ID"],
            "fields": {field: row.get(field, "") for field in FIELDS},
        }
        for row in sorted(rows, key=lambda item: item["Knowledge ID"])
    ]


def write_import_payload(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(render_import_payload(rows), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_dataset(
    *,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
    expected_count: int | None = 400,
    category_targets: dict[str, int] | None = CATEGORIES,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    rows, header, raw_findings = load_rows(tsv_path)
    errors.extend(raw_findings)
    if header != FIELDS:
        errors.append(f"TSV columns must be exactly {FIELDS!r}; found {header!r}")
    if expected_count is not None and len(rows) != expected_count:
        errors.append(f"expected exactly {expected_count} rows, found {len(rows)}")

    source_document, source_errors = load_sources(sources_path)
    errors.extend(source_errors)
    source_catalog = source_document.get("sources", {}) if isinstance(source_document, dict) else {}

    missing_fields = Counter()
    invalid_ids: list[str] = []
    invalid_categories: list[str] = []
    invalid_difficulties: list[str] = []
    invalid_dates: list[str] = []
    missing_sources: list[str] = []
    invalid_source_ids: list[str] = []
    invalid_tags: list[str] = []
    html_findings: list[str] = []
    media_findings: list[str] = []
    normalization_findings: list[str] = []
    whitespace_findings: list[str] = []
    long_answers: list[str] = []
    long_explanations: list[str] = []
    bilingual_number_warnings: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        knowledge_id = row.get("Knowledge ID", "")
        for field in REQUIRED_FIELDS:
            if not row.get(field, ""):
                missing_fields[field] += 1
        for field in FIELDS:
            value = row.get(field, "")
            if value != value.strip():
                whitespace_findings.append(f"{knowledge_id or row_number}:{field}")
            if value != unicodedata.normalize("NFC", value):
                normalization_findings.append(f"{knowledge_id or row_number}:{field}")
            if "\t" in value or "\r" in value or "\n" in value:
                errors.append(f"row {row_number} field {field!r} contains a tab or newline")
        if not ID_RE.fullmatch(knowledge_id):
            invalid_ids.append(knowledge_id or f"row {row_number}")
        if row.get("Category") not in CATEGORIES:
            invalid_categories.append(knowledge_id)
        if row.get("Difficulty") not in DIFFICULTIES:
            invalid_difficulties.append(knowledge_id)
        for field in ("Source Date", "Fact Checked"):
            if not DATE_RE.fullmatch(row.get(field, "")):
                invalid_dates.append(f"{knowledge_id}:{field}")
        source_ids = split_semicolon(row.get("Source", ""))
        if not source_ids:
            missing_sources.append(knowledge_id)
        for source_id in source_ids:
            if source_id not in source_catalog:
                invalid_source_ids.append(f"{knowledge_id}:{source_id}")
        for tag in split_tags(row.get("Tags", "")):
            if not TAG_RE.fullmatch(tag):
                invalid_tags.append(f"{knowledge_id}:{tag}")
        for field in PLAIN_TEXT_FIELDS:
            value = row.get(field, "")
            if HTML_RE.search(value):
                html_findings.append(f"{knowledge_id}:{field}")
            if MEDIA_RE.search(value):
                media_findings.append(f"{knowledge_id}:{field}")

        zh_answer = row.get("Chinese Answer", "")
        en_answer = row.get("English Answer", "")
        if len(zh_answer) > 90 or len(en_answer.split()) > 45:
            long_answers.append(knowledge_id)
        if len(row.get("Chinese Explanation", "")) > 320 or len(row.get("English Explanation", "").split()) > 140:
            long_explanations.append(knowledge_id)
        for zh_field, en_field in (
            ("Chinese Question", "English Question"),
            ("Chinese Answer", "English Answer"),
        ):
            # Compare numeric values rather than formatting so an ISO date such as
            # 1949-10-01 matches the natural Chinese form 1949年10月1日.
            zh_numbers = {str(int(value)) for value in re.findall(r"\d+", row.get(zh_field, ""))}
            en_numbers = {str(int(value)) for value in re.findall(r"\d+", row.get(en_field, ""))}
            if zh_numbers != en_numbers:
                bilingual_number_warnings.append(f"{knowledge_id}:{zh_field}/{en_field}")

    duplicate_ids = duplicates(row.get("Knowledge ID", "") for row in rows)
    duplicate_zh_questions = duplicates(row.get("Chinese Question", "") for row in rows)
    duplicate_en_questions = duplicates(row.get("English Question", "") for row in rows)
    duplicate_bilingual_facts = duplicates(
        "\u241f".join(
            [
                normalized_question(row.get("Chinese Question", "")),
                normalized_question(row.get("English Question", "")),
                normalized_question(row.get("Chinese Answer", "")),
                normalized_question(row.get("English Answer", "")),
            ]
        )
        for row in rows
    )

    category_counts = Counter(row.get("Category", "") for row in rows)
    difficulty_counts = Counter(row.get("Difficulty", "") for row in rows)
    if category_targets is not None and dict(category_counts) != category_targets:
        errors.append(
            f"category distribution must be {category_targets!r}; found {dict(sorted(category_counts.items()))!r}"
        )
    if duplicate_ids:
        errors.append(f"duplicate Knowledge IDs: {duplicate_ids}")
    if duplicate_zh_questions:
        errors.append(f"duplicate Chinese questions: {duplicate_zh_questions}")
    if duplicate_en_questions:
        errors.append(f"duplicate English questions: {duplicate_en_questions}")
    if duplicate_bilingual_facts:
        errors.append("exact duplicate bilingual facts exist")
    if missing_fields:
        errors.append(f"required fields are empty: {dict(sorted(missing_fields.items()))}")
    if invalid_ids:
        errors.append(f"invalid Knowledge IDs: {invalid_ids[:20]}")
    if invalid_categories:
        errors.append(f"invalid categories on: {invalid_categories[:20]}")
    if invalid_difficulties:
        errors.append(f"invalid difficulties on: {invalid_difficulties[:20]}")
    if invalid_dates:
        errors.append(f"malformed dates: {invalid_dates[:20]}")
    if missing_sources:
        errors.append(f"missing sources on: {missing_sources[:20]}")
    if invalid_source_ids:
        errors.append(f"unknown source IDs: {invalid_source_ids[:20]}")
    if invalid_tags:
        errors.append(f"invalid tags: {invalid_tags[:20]}")
    if html_findings:
        errors.append(f"accidental HTML in plain-text fields: {html_findings[:20]}")
    if media_findings:
        errors.append(f"media/TTS references are disabled: {media_findings[:20]}")
    if whitespace_findings:
        errors.append(f"leading/trailing whitespace in {len(whitespace_findings)} fields")
    if normalization_findings:
        errors.append(f"non-NFC text in {len(normalization_findings)} fields")
    if long_answers:
        errors.append(f"unreasonably long short answers: {long_answers[:20]}")
    if long_explanations:
        errors.append(f"unreasonably long explanations: {long_explanations[:20]}")
    if bilingual_number_warnings:
        warnings.append(
            f"bilingual number mismatches need review: {bilingual_number_warnings[:20]}"
        )

    near_zh = _near_duplicate_pairs(rows, "Chinese Question")
    near_en = _near_duplicate_pairs(rows, "English Question")
    if near_zh or near_en:
        warnings.append(
            f"near-duplicate question pairs need review: zh={len(near_zh)}, en={len(near_en)}"
        )

    explanation_count = sum(
        1
        for row in rows
        if row.get("Chinese Explanation") and row.get("English Explanation")
    )
    time_sensitive_count = sum(
        1 for row in rows if any(tag.startswith("as_of::") for tag in split_tags(row.get("Tags", "")))
    )
    missing_source_date_count = sum(1 for row in rows if not row.get("Source Date"))
    return {
        "status": "PASS" if not errors else "FAIL",
        "tsv": str(tsv_path.resolve()),
        "sources": str(sources_path.resolve()),
        "total_notes": len(rows),
        "notes_per_category": dict(sorted(category_counts.items())),
        "notes_per_difficulty": dict(sorted(difficulty_counts.items())),
        "notes_with_bilingual_explanations": explanation_count,
        "time_sensitive_notes": time_sensitive_count,
        "notes_missing_source_dates": missing_source_date_count,
        "duplicate_warnings": {
            "duplicate_ids": duplicate_ids,
            "duplicate_chinese_questions": duplicate_zh_questions,
            "duplicate_english_questions": duplicate_en_questions,
            "near_duplicate_chinese": near_zh,
            "near_duplicate_english": near_en,
        },
        "bilingual_number_warnings": bilingual_number_warnings,
        "source_count": len(source_catalog),
        "validation_failure_count": len(errors),
        "warning_count": len(warnings),
        "warnings": warnings,
        "errors": errors,
    }


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_or_raise(
    *,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
    report_path: Path | None = DEFAULT_REPORT,
    expected_count: int | None = 400,
    category_targets: dict[str, int] | None = CATEGORIES,
) -> dict[str, Any]:
    report = validate_dataset(
        tsv_path=tsv_path,
        sources_path=sources_path,
        expected_count=expected_count,
        category_targets=category_targets,
    )
    if report_path is not None:
        write_report(report, report_path)
    if report["status"] != "PASS":
        raise ChinaKnowledgeValidationError("; ".join(report["errors"]))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the bilingual China Knowledge dataset.")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-import", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = validate_dataset(tsv_path=args.tsv, sources_path=args.sources)
    write_report(report, args.report)
    if report["status"] == "PASS" and args.write_import is not None:
        rows, _header, _findings = load_rows(args.tsv)
        write_import_payload(rows, args.write_import)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
