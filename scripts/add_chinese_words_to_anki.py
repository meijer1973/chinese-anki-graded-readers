from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
WORD_LIST = ROOT / "word list chinese.txt"
SOURCE_TSV = ROOT / "anki_chinese_review.tsv"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_NAME = "Default"
DECK_QUERY = "deck:Default"
MODEL_NAME = "Chinese Vocabulary"

REQUIRED_SOURCE_FIELDS = [
    "Word",
    "Pinyin",
    "Meaning",
    "Example",
    "Example Pinyin",
    "Example Meaning",
    "Tags",
]

REQUIRED_MODEL_FIELDS = [
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
]

REQUIRED_TEMPLATES = {"Word Recognition", "Sentence Recognition"}


class ChineseWordImportError(RuntimeError):
    pass


def clean(value: str | None) -> str:
    return (value or "").replace("\t", " ").strip()


def anki_request(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    url: str = ANKI_CONNECT_URL,
) -> Any:
    payload: dict[str, Any] = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("error"):
        raise ChineseWordImportError(data["error"])
    return data.get("result")


def load_ranked_words(path: Path = WORD_LIST) -> dict[str, int]:
    ranks: dict[str, int] = {}
    duplicate_details: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        word = clean(raw_line)
        if not word:
            continue
        if word in ranks:
            duplicate_details.append(f"{word!r} on source ranks {ranks[word]} and {line_number}")
            continue
        ranks[word] = line_number
    if duplicate_details:
        raise ChineseWordImportError(
            f"Duplicate words in {path}: " + "; ".join(duplicate_details[:20])
        )
    return ranks


def load_source_rows(path: Path = SOURCE_TSV) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing_columns = [field for field in REQUIRED_SOURCE_FIELDS if field not in (reader.fieldnames or [])]
        if missing_columns:
            raise ChineseWordImportError(f"Missing columns in {path}: {missing_columns}")
        rows = [
            {key: clean(value) for key, value in row.items()}
            for row in reader
        ]

    by_word: dict[str, dict[str, str]] = {}
    duplicate_words: set[str] = set()
    for row in rows:
        word = row["Word"]
        if not word:
            continue
        if word in by_word:
            duplicate_words.add(word)
        by_word[word] = row
    if duplicate_words:
        raise ChineseWordImportError(
            f"Duplicate words in {path}: {sorted(duplicate_words)[:20]}"
        )
    return by_word


def note_field(note: dict[str, Any], field_name: str) -> str:
    return clean(note.get("fields", {}).get(field_name, {}).get("value", ""))


def load_live_notes(call_anki: Callable[[str, dict[str, Any] | None], Any]) -> list[dict[str, Any]]:
    note_ids = call_anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(call_anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def live_notes_by_word(notes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_word: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for note in notes:
        word = note_field(note, "Word") or note_field(note, "Front")
        if word:
            by_word[word].append(note)
    return dict(by_word)


def validate_model(call_anki: Callable[[str, dict[str, Any] | None], Any]) -> None:
    model_names = call_anki("modelNames", None)
    if MODEL_NAME not in model_names:
        raise ChineseWordImportError(
            f"Anki note type {MODEL_NAME!r} does not exist. Run migrate_chinese_notes.py first."
        )

    fields = call_anki("modelFieldNames", {"modelName": MODEL_NAME})
    missing_fields = [field for field in REQUIRED_MODEL_FIELDS if field not in fields]
    if missing_fields:
        raise ChineseWordImportError(
            f"Anki note type {MODEL_NAME!r} is missing fields: {missing_fields}"
        )

    templates = set(call_anki("modelTemplates", {"modelName": MODEL_NAME}))
    missing_templates = sorted(REQUIRED_TEMPLATES - templates)
    unwanted_templates = sorted(templates - REQUIRED_TEMPLATES)
    if missing_templates or unwanted_templates:
        details: list[str] = []
        if missing_templates:
            details.append(f"missing templates {missing_templates}")
        if unwanted_templates:
            details.append(f"unwanted templates {unwanted_templates}")
        raise ChineseWordImportError(
            f"Anki note type {MODEL_NAME!r} has an incompatible template set ({'; '.join(details)}). "
            "Run setup_production_sentence_cards.py before adding words."
        )


def validate_requested_words(words: list[str]) -> list[str]:
    cleaned_words = [clean(word) for word in words if clean(word)]
    duplicates = sorted({word for word in cleaned_words if cleaned_words.count(word) > 1})
    if duplicates:
        raise ChineseWordImportError(f"Words requested more than once: {duplicates}")
    if not cleaned_words:
        raise ChineseWordImportError("At least one nonblank --word value is required")
    return cleaned_words


def validate_source_row(word: str, row: dict[str, str]) -> None:
    blank_fields = [field for field in REQUIRED_SOURCE_FIELDS if not row.get(field)]
    if blank_fields:
        raise ChineseWordImportError(f"{word!r} has blank source fields: {blank_fields}")
    tags = set(row["Tags"].split())
    if "needs_meaning_review" in tags or row["Meaning"].lower() == "needs review":
        raise ChineseWordImportError(f"{word!r} still needs meaning review")
    if "generated" in tags:
        raise ChineseWordImportError(
            f"{word!r} still uses a generated placeholder example; add a curated sentence override first"
        )


def make_note(row: dict[str, str], rank: int) -> dict[str, Any]:
    sentence_enabled = "yes" if row["Example"] and row["Example Meaning"] else ""
    fields = {
        "Word": row["Word"],
        "Pinyin": row["Pinyin"],
        "Meaning": row["Meaning"],
        "Example": row["Example"],
        "Example Pinyin": row["Example Pinyin"],
        "Example Meaning": row["Example Meaning"],
        "Source": row["Tags"],
        "Production Card": "",
        "Sentence Card": sentence_enabled,
        "Frequency Rank": str(rank),
    }
    tags = sorted({"chinese_vocab", "has_example", *row["Tags"].split()})
    return {
        "deckName": DECK_NAME,
        "modelName": MODEL_NAME,
        "fields": fields,
        "tags": tags,
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {"deckName": DECK_NAME},
        },
    }


def plan_additions(
    requested_words: list[str],
    ranks: dict[str, int],
    source_rows: dict[str, dict[str, str]],
    existing_by_word: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    notes_to_add: list[dict[str, Any]] = []
    already_present: list[str] = []
    for word in requested_words:
        if word not in ranks:
            raise ChineseWordImportError(f"{word!r} is not in {WORD_LIST.name}")
        row = source_rows.get(word)
        if not row:
            raise ChineseWordImportError(
                f"{word!r} is missing from {SOURCE_TSV.name}; rebuild with build_anki_chinese.py"
            )
        validate_source_row(word, row)

        existing = existing_by_word.get(word, [])
        if len(existing) > 1:
            note_ids = [int(note["noteId"]) for note in existing]
            raise ChineseWordImportError(
                f"Live deck already contains {len(existing)} notes for {word!r}: {note_ids}"
            )
        if existing:
            already_present.append(word)
            continue
        notes_to_add.append(make_note(row, ranks[word]))
    return notes_to_add, already_present


def add_words(
    requested_words: list[str],
    *,
    apply: bool,
    word_list: Path = WORD_LIST,
    source_tsv: Path = SOURCE_TSV,
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> dict[str, Any]:
    words = validate_requested_words(requested_words)
    ranks = load_ranked_words(word_list)
    source_rows = load_source_rows(source_tsv)
    validate_model(call_anki)
    existing_before = live_notes_by_word(load_live_notes(call_anki))
    notes_to_add, already_present = plan_additions(words, ranks, source_rows, existing_before)

    added_note_ids: list[int] = []
    if notes_to_add:
        can_add = call_anki("canAddNotes", {"notes": notes_to_add})
        if not isinstance(can_add, list) or len(can_add) != len(notes_to_add):
            raise ChineseWordImportError("Anki returned an invalid canAddNotes result")
        refused_words = [
            notes_to_add[index]["fields"]["Word"]
            for index, allowed in enumerate(can_add)
            if not allowed
        ]
        if refused_words:
            raise ChineseWordImportError(
                f"Anki preflight refused these notes before mutation: {refused_words}"
            )

    if apply and notes_to_add:
        for start in range(0, len(notes_to_add), 50):
            batch = notes_to_add[start : start + 50]
            result = call_anki("addNotes", {"notes": batch})
            if not isinstance(result, list) or len(result) != len(batch):
                raise ChineseWordImportError("Anki returned an invalid addNotes result")
            if any(note_id is None for note_id in result):
                failed_words = [
                    batch[index]["fields"]["Word"]
                    for index, note_id in enumerate(result)
                    if note_id is None
                ]
                raise ChineseWordImportError(f"Anki refused to add notes: {failed_words}")
            added_note_ids.extend(int(note_id) for note_id in result)

        existing_after = live_notes_by_word(load_live_notes(call_anki))
        for note in notes_to_add:
            word = note["fields"]["Word"]
            count = len(existing_after.get(word, []))
            if count != 1:
                raise ChineseWordImportError(
                    f"Post-add verification found {count} live notes for {word!r}; expected exactly one"
                )

    return {
        "mode": "apply" if apply else "dry-run",
        "requested_words": words,
        "already_in_deck": already_present,
        "would_add": [note["fields"]["Word"] for note in notes_to_add],
        "added_note_ids": added_note_ids,
        "added_count": len(added_note_ids),
        "duplicate_protection": {
            "source_word_list_unique": True,
            "source_tsv_unique": True,
            "live_requested_words_unique": True,
            "anki_can_add_notes_preflight": True,
            "anki_allow_duplicate": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely add selected, reviewed Chinese vocabulary rows to Anki. Dry-run is the default."
    )
    parser.add_argument("--word", action="append", required=True, help="Word to check/add; repeat for multiple words.")
    parser.add_argument("--apply", action="store_true", help="Add missing words after all preflight checks pass.")
    parser.add_argument("--word-list", type=Path, default=WORD_LIST)
    parser.add_argument("--source-tsv", type=Path, default=SOURCE_TSV)
    parser.add_argument("--anki-connect-url", default=ANKI_CONNECT_URL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    def call_anki(action: str, params: dict[str, Any] | None = None) -> Any:
        return anki_request(action, params, url=args.anki_connect_url)

    try:
        report = add_words(
            args.word,
            apply=args.apply,
            word_list=args.word_list,
            source_tsv=args.source_tsv,
            call_anki=call_anki,
        )
    except ChineseWordImportError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"status": "PASS", **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
