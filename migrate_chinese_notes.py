from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
SOURCE_TSV = ROOT / "anki_chinese_review.tsv"
BACKUP_TSV = ROOT / "chinese_notes_before_model_migration_backup.tsv"
REPORT_MD = ROOT / "chinese_notes_model_migration_report.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_QUERY = "deck:Default"
MODEL_NAME = "Chinese Vocabulary"

FIELDS = [
    "Word",
    "Pinyin",
    "Meaning",
    "Example",
    "Example Pinyin",
    "Example Meaning",
    "Source",
    "Sentence Card",
]

CARD_TEMPLATES = [
    {
        "Name": "Word Recognition",
        "Front": """
<div class="word">{{Word}}</div>
""".strip(),
        "Back": """
{{FrontSide}}
<hr id="answer">
<div class="pinyin">{{Pinyin}}</div>
<div class="meaning">{{Meaning}}</div>
{{#Example}}
<div class="example">{{Example}}</div>
<div class="example-pinyin">{{Example Pinyin}}</div>
<div class="example-meaning">{{Example Meaning}}</div>
{{/Example}}
""".strip(),
    },
    {
        "Name": "Meaning Recall",
        "Front": """
<div class="meaning prompt">{{Meaning}}</div>
{{#Example Meaning}}
<div class="example-meaning prompt">{{Example Meaning}}</div>
{{/Example Meaning}}
""".strip(),
        "Back": """
{{FrontSide}}
<hr id="answer">
<div class="word">{{Word}}</div>
<div class="pinyin">{{Pinyin}}</div>
{{#Example}}
<div class="example">{{Example}}</div>
<div class="example-pinyin">{{Example Pinyin}}</div>
{{/Example}}
""".strip(),
    },
]

CSS = """
.card {
    font-family: Arial, "Microsoft YaHei", sans-serif;
    font-size: 20px;
    line-height: 1.45;
    text-align: center;
    color: #111;
    background-color: #fff;
}
.word {
    font-size: 44px;
    line-height: 1.2;
    margin: 8px 0 12px;
}
.pinyin {
    color: #246;
    font-size: 22px;
    margin: 8px 0;
}
.meaning {
    max-width: 42rem;
    margin: 10px auto;
}
.example {
    font-size: 28px;
    margin: 18px 0 6px;
}
.example-pinyin {
    color: #555;
    font-size: 18px;
}
.example-meaning {
    color: #333;
    font-size: 18px;
    margin-top: 6px;
}
.prompt {
    margin-top: 16px;
}
""".strip()


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


def load_source_rows() -> dict[str, dict[str, str]]:
    with SOURCE_TSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    by_word: dict[str, dict[str, str]] = {}
    duplicates: set[str] = set()
    for row in rows:
        word = clean(row["Word"])
        if word in by_word:
            duplicates.add(word)
        by_word[word] = {key: clean(value) for key, value in row.items()}

    if duplicates:
        raise RuntimeError(f"Duplicate source words: {sorted(duplicates)[:10]}")
    return by_word


def get_field(fields: dict[str, Any], name: str) -> str:
    return clean(fields.get(name, {}).get("value", ""))


def load_anki_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def ensure_model() -> None:
    model_names = anki("modelNames")
    if MODEL_NAME in model_names:
        return

    anki(
        "createModel",
        {
            "modelName": MODEL_NAME,
            "inOrderFields": FIELDS,
            "cardTemplates": CARD_TEMPLATES,
            "css": CSS,
        },
    )


def source_tags(row: dict[str, str]) -> list[str]:
    tags = ["chinese_vocab", "has_example"]
    tags.extend(tag for tag in row.get("Tags", "").split() if tag)
    return sorted(set(tags))


def write_backup(notes: list[dict[str, Any]]) -> None:
    fieldnames = [
        "Note ID",
        "Old Model",
        "Old Word",
        "Old Pinyin",
        "Old Meaning",
        "Old Tags",
        "Old Cards",
    ]
    rows = []
    for note in notes:
        fields = note.get("fields", {})
        rows.append(
            {
                "Note ID": str(note["noteId"]),
                "Old Model": note.get("modelName", ""),
                "Old Word": get_field(fields, "Front"),
                "Old Pinyin": get_field(fields, "Back"),
                "Old Meaning": get_field(fields, "Add Reverse"),
                "Old Tags": " ".join(note.get("tags", [])),
                "Old Cards": " ".join(str(card) for card in note.get("cards", [])),
            }
        )

    with BACKUP_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def migrate_notes(notes: list[dict[str, Any]], source_by_word: dict[str, dict[str, str]]) -> None:
    actions = []
    missing_source: list[str] = []

    for note in notes:
        old_fields = note.get("fields", {})
        word = get_field(old_fields, "Front") or get_field(old_fields, "Word")
        source = source_by_word.get(word)
        if not source:
            missing_source.append(word)
            continue

        # Keep the already-reviewed meaning currently in Anki.
        current_meaning = get_field(old_fields, "Add Reverse") or get_field(old_fields, "Meaning")
        current_pinyin = get_field(old_fields, "Back") or get_field(old_fields, "Pinyin")

        fields = {
            "Word": word,
            "Pinyin": current_pinyin or source["Pinyin"],
            "Meaning": current_meaning or source["Meaning"],
            "Example": source["Example"],
            "Example Pinyin": source["Example Pinyin"],
            "Example Meaning": source["Example Meaning"],
            "Source": source["Tags"],
            "Sentence Card": "",
        }
        actions.append(
            {
                "action": "updateNoteModel",
                "params": {
                    "note": {
                        "id": int(note["noteId"]),
                        "modelName": MODEL_NAME,
                        "fields": fields,
                        "tags": source_tags(source),
                    }
                },
            }
        )

    if missing_source:
        raise RuntimeError(f"Missing source rows for {len(missing_source)} notes: {missing_source[:10]}")

    for start in range(0, len(actions), 50):
        results = anki("multi", {"actions": actions[start : start + 50]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])


def verify(source_by_word: dict[str, dict[str, str]]) -> dict[str, Any]:
    notes = load_anki_notes()
    migrated = 0
    with_examples = 0
    mismatches: list[str] = []

    for note in notes:
        if note.get("modelName") == MODEL_NAME:
            migrated += 1
        fields = note.get("fields", {})
        word = get_field(fields, "Word")
        source = source_by_word.get(word)
        if get_field(fields, "Example"):
            with_examples += 1
        if source and (
            get_field(fields, "Example") != source["Example"]
            or get_field(fields, "Example Pinyin") != source["Example Pinyin"]
            or get_field(fields, "Example Meaning") != source["Example Meaning"]
        ):
            mismatches.append(word)

    cards = anki("findCards", {"query": DECK_QUERY})
    return {
        "notes": len(notes),
        "cards": len(cards),
        "migrated": migrated,
        "with_examples": with_examples,
        "mismatches": mismatches,
    }


def write_report(result: dict[str, Any]) -> None:
    lines = [
        "# Chinese Notes Model Migration Report",
        "",
        f"Model: {MODEL_NAME}",
        f"Notes in deck: {result['notes']}",
        f"Cards in deck: {result['cards']}",
        f"Notes on new model: {result['migrated']}",
        f"Notes with example field populated: {result['with_examples']}",
        f"Sentence field mismatches: {len(result['mismatches'])}",
        "",
        "Fields:",
    ]
    lines.extend(f"- {field}" for field in FIELDS)
    lines.extend(
        [
            "",
            "Created card templates:",
            "- Word Recognition",
            "- Meaning Recall",
            "",
            "The Sentence Card field is intentionally blank for now. It gives us a clean switch to add sentence cards later without losing the sentence data already stored on each note.",
            "",
            f"Backup file: {BACKUP_TSV.name}",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> None:
    source_by_word = load_source_rows()
    notes = load_anki_notes()
    write_backup(notes)
    ensure_model()
    migrate_notes(notes, source_by_word)
    result = verify(source_by_word)
    write_report(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
