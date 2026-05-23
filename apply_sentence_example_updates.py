from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
SOURCE_TSV = ROOT / "anki_chinese_review.tsv"
BACKUP_TSV = ROOT / "sentence_examples_before_update_backup.tsv"
REPORT_MD = ROOT / "sentence_examples_update_report.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_QUERY = "deck:Default"

EXAMPLE_FIELDS = ["Example", "Example Pinyin", "Example Meaning", "Source"]


def clean(value: str) -> str:
    return (value or "").replace("\t", " ").strip()


def anki(action: str, params: dict[str, Any] | None = None) -> Any:
    payload = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params

    request = Request(
        ANKI_CONNECT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


def note_field(note: dict[str, Any], name: str) -> str:
    return clean(note.get("fields", {}).get(name, {}).get("value", ""))


def load_source_rows() -> dict[str, dict[str, str]]:
    with SOURCE_TSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    by_word: dict[str, dict[str, str]] = {}
    duplicates: set[str] = set()
    for row in rows:
        word = clean(row["Word"])
        if word in by_word:
            duplicates.add(word)
        by_word[word] = {
            "Example": clean(row["Example"]),
            "Example Pinyin": clean(row["Example Pinyin"]),
            "Example Meaning": clean(row["Example Meaning"]),
            "Source": clean(row["Tags"]),
        }

    if duplicates:
        raise RuntimeError(f"Duplicate source words: {sorted(duplicates)[:10]}")
    return by_word


def load_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def write_backup(notes: list[dict[str, Any]]) -> None:
    fieldnames = [
        "Note ID",
        "Word",
        "Old Example",
        "Old Example Pinyin",
        "Old Example Meaning",
        "Old Source",
        "Sentence Card",
        "Frequency Rank",
    ]

    rows = []
    for note in notes:
        rows.append(
            {
                "Note ID": str(note["noteId"]),
                "Word": note_field(note, "Word"),
                "Old Example": note_field(note, "Example"),
                "Old Example Pinyin": note_field(note, "Example Pinyin"),
                "Old Example Meaning": note_field(note, "Example Meaning"),
                "Old Source": note_field(note, "Source"),
                "Sentence Card": note_field(note, "Sentence Card"),
                "Frequency Rank": note_field(note, "Frequency Rank"),
            }
        )

    with BACKUP_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def apply_updates(notes: list[dict[str, Any]], source_by_word: dict[str, dict[str, str]]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    missing_source: list[str] = []
    changed_words: list[str] = []
    active_sentence_card_updates = 0

    for note in notes:
        word = note_field(note, "Word")
        source = source_by_word.get(word)
        if not source:
            missing_source.append(word)
            continue

        fields = {field: source[field] for field in EXAMPLE_FIELDS}
        if any(note_field(note, field) != value for field, value in fields.items()):
            changed_words.append(word)
            if note_field(note, "Sentence Card"):
                active_sentence_card_updates += 1
            actions.append(
                {
                    "action": "updateNoteFields",
                    "params": {"note": {"id": int(note["noteId"]), "fields": fields}},
                }
            )

    if missing_source:
        raise RuntimeError(f"Missing source rows for {len(missing_source)} notes: {missing_source[:10]}")

    for start in range(0, len(actions), 50):
        results = anki("multi", {"actions": actions[start : start + 50]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])

    return {
        "notes_seen": len(notes),
        "notes_updated": len(actions),
        "active_sentence_card_updates": active_sentence_card_updates,
        "changed_words_preview": changed_words[:20],
    }


def verify(source_by_word: dict[str, dict[str, str]]) -> dict[str, Any]:
    notes = load_notes()
    mismatches: list[str] = []
    for note in notes:
        word = note_field(note, "Word")
        source = source_by_word.get(word)
        if not source:
            mismatches.append(word)
            continue
        if any(note_field(note, field) != source[field] for field in EXAMPLE_FIELDS):
            mismatches.append(word)

    return {"mismatch_count": len(mismatches), "mismatches_preview": mismatches[:20]}


def write_report(result: dict[str, Any], verification: dict[str, Any]) -> None:
    lines = [
        "# Sentence Example Update Report",
        "",
        f"Notes seen: {result['notes_seen']}",
        f"Notes updated: {result['notes_updated']}",
        f"Active sentence-card notes updated: {result['active_sentence_card_updates']}",
        f"Post-update mismatches: {verification['mismatch_count']}",
        "",
        "Files:",
        f"- {BACKUP_TSV.name}: previous example fields before update",
        f"- {SOURCE_TSV.name}: rebuilt source examples",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    source_by_word = load_source_rows()
    notes = load_notes()
    write_backup(notes)
    result = apply_updates(notes, source_by_word)
    verification = verify(source_by_word)
    write_report(result, verification)
    print(json.dumps({**result, **verification}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
