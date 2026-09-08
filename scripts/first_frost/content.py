from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "anki" / "first_frost" / "first_frost_pilot_notes.tsv"

REQUIRED_COLUMNS = (
    "Word",
    "Pinyin",
    "Meaning",
    "Example",
    "Example Pinyin",
    "Example Meaning",
    "Source",
    "Production Card",
    "Sentence Card",
    "Frequency Rank",
    "Tags",
    "Pilot Priority",
    "Usage Note",
    "Input File",
    "Input Row",
)


class FirstFrostContentError(RuntimeError):
    """Raised when the reviewed pilot content is malformed."""


def clean(value: str | None) -> str:
    return (value or "").replace("\t", " ").strip()


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise FirstFrostContentError(f"Missing manifest columns: {missing}")
        return [{key: clean(value) for key, value in row.items()} for row in reader]


def manifest_by_word(path: Path = MANIFEST_PATH) -> dict[str, dict[str, str]]:
    rows = load_manifest(path)
    by_word: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    for row in rows:
        word = row["Word"]
        if word in by_word:
            duplicates.append(word)
        by_word[word] = row
    if duplicates:
        raise FirstFrostContentError(f"Duplicate manifest words: {sorted(set(duplicates))}")
    return by_word


def install_sentence_overrides(
    sentence_overrides: dict[str, tuple[str, str]],
    pinyin_overrides: dict[str, str],
    path: Path = MANIFEST_PATH,
) -> None:
    """Make the reviewed examples authoritative for normal TSV rebuilds."""
    for row in load_manifest(path):
        sentence_overrides[row["Word"]] = (row["Example"], row["Example Meaning"])
        pinyin_overrides[row["Example"]] = row["Example Pinyin"]
