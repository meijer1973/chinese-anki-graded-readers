from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_anki_chinese
from apply_meaning_cleanup_updates import cleaned_meaning


ANKI_DIR = ROOT / "anki"
DEFAULT_CANDIDATES = ANKI_DIR / "stretch_word_candidates.tsv"
ADDED_TSV = ANKI_DIR / "stretch_words_added_to_anki.tsv"
IMPORT_LOG = ANKI_DIR / "stretch_word_import_log.json"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_NAME = "Default"
DECK_QUERY = "deck:Default"
MODEL_NAME = "Chinese Vocabulary"

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


def clean(value: str | None) -> str:
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


def load_candidates(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle, delimiter="\t")]
    by_word: dict[str, dict[str, str]] = {}
    for row in rows:
        word = row.get("Hanzi", "")
        if not word:
            continue
        by_word.setdefault(word, row)
    return list(by_word.values())


def note_field(note: dict[str, Any], name: str) -> str:
    return clean(note.get("fields", {}).get(name, {}).get("value", ""))


def load_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def ensure_model_fields() -> None:
    model_names = anki("modelNames")
    if MODEL_NAME not in model_names:
        raise RuntimeError(f"Anki model {MODEL_NAME!r} does not exist. Run the repository model migration first.")
    fields = anki("modelFieldNames", {"modelName": MODEL_NAME})
    for field in REQUIRED_MODEL_FIELDS:
        if field not in fields:
            anki("modelFieldAdd", {"modelName": MODEL_NAME, "fieldName": field})
            fields = anki("modelFieldNames", {"modelName": MODEL_NAME})


def source_tags(row: dict[str, str], example_source: str, meaning_source: str) -> list[str]:
    pack = row.get("Pack", "stretch").replace(" ", "_")
    layer = row.get("Layer", "stretch").replace(" ", "_")
    return sorted(
        {
            "chinese_vocab",
            "stretch_word",
            "stretch_candidate",
            f"stretch_pack_{pack}",
            f"stretch_layer_{layer}",
            f"meaning_{meaning_source}",
            f"example_{example_source}",
        }
    )


def enrich_candidate(
    row: dict[str, str],
    entries_by_word: dict[str, list[build_anki_chinese.CedictEntry]],
    example_records: list[tuple[int, str, str, str]],
    char_index: dict[str, list[int]],
) -> dict[str, str]:
    word = row["Hanzi"]
    entries = entries_by_word.get(word, [])

    pinyin = row.get("Pinyin") or (build_anki_chinese.entry_pinyin(entries) if entries else build_anki_chinese.generated_pinyin(word))
    if row.get("English"):
        meaning = row["English"]
        meaning_source = "metadata"
    elif entries:
        meaning = build_anki_chinese.concise_definitions(entries)
        meaning_source = "cedict"
    else:
        meaning = build_anki_chinese.fallback_meaning(word, entries_by_word)
        meaning_source = "needs_review"
    meaning = cleaned_meaning(word, meaning)

    if row.get("ExampleSentenceZhNatural"):
        example = clean(row["ExampleSentenceZhNatural"])
        example_pinyin = build_anki_chinese.generated_pinyin(example)
        example_meaning = row.get("ExampleSentenceEnglish") or f'Example for "{word}".'
        example_source = "metadata"
    else:
        found = build_anki_chinese.find_example(word, example_records, char_index)
        example = found.chinese
        example_pinyin = found.pinyin
        example_meaning = found.english
        example_source = found.source

    source = f"stretch:{row.get('Pack', '')}:{row.get('Layer', '')}; meaning={meaning_source}; example={example_source}"
    return {
        "Word": word,
        "Pinyin": pinyin,
        "Meaning": meaning or "Needs review",
        "Example": example,
        "Example Pinyin": example_pinyin,
        "Example Meaning": example_meaning,
        "Source": source,
        "Production Card": "",
        "Sentence Card": "",
        "Frequency Rank": "",
        "Pack": row.get("Pack", ""),
        "Layer": row.get("Layer", ""),
        "Status": "imported",
        "Meaning Source": meaning_source,
        "Example Source": example_source,
    }


def make_note(fields: dict[str, str], tags: list[str]) -> dict[str, Any]:
    return {
        "deckName": DECK_NAME,
        "modelName": MODEL_NAME,
        "fields": {field: fields[field] for field in REQUIRED_MODEL_FIELDS},
        "tags": tags,
        "options": {"allowDuplicate": False, "duplicateScope": "deck", "duplicateScopeOptions": {"deckName": DECK_NAME}},
    }


def suspend_production_cards(note_ids: list[int]) -> int:
    card_ids: list[int] = []
    for start in range(0, len(note_ids), 100):
        notes = anki("notesInfo", {"notes": note_ids[start : start + 100]})
        cards = []
        for note in notes:
            cards.extend(note.get("cards", []))
        if not cards:
            continue
        card_info = anki("cardsInfo", {"cards": cards})
        card_ids.extend(int(card["cardId"]) for card in card_info if int(card.get("ord", -1)) == 1)
    for start in range(0, len(card_ids), 500):
        anki("suspend", {"cards": card_ids[start : start + 500]})
    return len(card_ids)


def write_added(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "Note ID",
        "Word",
        "Pinyin",
        "Meaning",
        "Pack",
        "Layer",
        "Meaning Source",
        "Example Source",
        "Example",
        "Example Meaning",
        "Source",
        "Status",
    ]
    ADDED_TSV.parent.mkdir(parents=True, exist_ok=True)
    with ADDED_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_import_ready(rows: list[dict[str, str]]) -> None:
    target = ANKI_DIR / "stretch_word_import_ready.tsv"
    fieldnames = [
        "Hanzi",
        "Pinyin",
        "English",
        "PartOfSpeech",
        "Pack",
        "Layer",
        "Priority",
        "SourceBook",
        "FirstChapter",
        "ExampleSentenceZhTok",
        "ExampleSentenceZhNatural",
        "ExampleSentenceEnglish",
        "Status",
        "Notes",
    ]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Hanzi": row["Word"],
                    "Pinyin": row["Pinyin"],
                    "English": row["Meaning"],
                    "PartOfSpeech": "",
                    "Pack": row["Pack"],
                    "Layer": row["Layer"],
                    "Priority": "",
                    "SourceBook": "",
                    "FirstChapter": "",
                    "ExampleSentenceZhTok": "",
                    "ExampleSentenceZhNatural": row["Example"],
                    "ExampleSentenceEnglish": row["Example Meaning"],
                    "Status": row["Status"],
                    "Notes": row["Source"],
                }
            )


def import_stretch_words(candidate_path: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    candidates = load_candidates(candidate_path)
    existing_notes = load_notes()
    existing_words = {note_field(note, "Word") or note_field(note, "Front") for note in existing_notes}

    entries_by_word = build_anki_chinese.parse_cedict()
    example_records, char_index = build_anki_chinese.build_examples()

    enriched: list[dict[str, str]] = []
    skipped_existing: list[str] = []
    for row in candidates:
        word = row["Hanzi"]
        if word in existing_words:
            skipped_existing.append(word)
            continue
        enriched.append(enrich_candidate(row, entries_by_word, example_records, char_index))

    notes = [
        make_note(fields, source_tags({"Pack": fields["Pack"], "Layer": fields["Layer"]}, fields["Example Source"], fields["Meaning Source"]))
        for fields in enriched
    ]
    added_rows: list[dict[str, str]] = []
    added_note_ids: list[int] = []

    if not dry_run and notes:
        ensure_model_fields()
        for start in range(0, len(notes), 50):
            batch = notes[start : start + 50]
            result = anki("addNotes", {"notes": batch})
            if len(result) != len(batch):
                raise RuntimeError("Unexpected addNotes result length")
            failed = [enriched[start + index]["Word"] for index, note_id in enumerate(result) if note_id is None]
            if failed:
                raise RuntimeError(f"Anki refused to add notes: {failed[:20]}")
            for index, note_id in enumerate(result):
                row = dict(enriched[start + index])
                row["Note ID"] = str(note_id)
                added_rows.append(row)
                added_note_ids.append(int(note_id))

    suspended_production_cards = 0 if dry_run else suspend_production_cards(added_note_ids)
    if not dry_run:
        write_added(added_rows)
        write_import_ready(added_rows)

    meaning_sources: dict[str, int] = {}
    example_sources: dict[str, int] = {}
    for row in enriched:
        meaning_sources[row["Meaning Source"]] = meaning_sources.get(row["Meaning Source"], 0) + 1
        example_sources[row["Example Source"]] = example_sources.get(row["Example Source"], 0) + 1

    report = {
        "candidate_path": str(Path(candidate_path)),
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "already_in_anki_count": len(skipped_existing),
        "to_add_count": len(enriched),
        "added_count": len(added_rows),
        "suspended_production_cards": suspended_production_cards,
        "meaning_sources": meaning_sources,
        "example_sources": example_sources,
        "skipped_existing": skipped_existing,
        "added_tsv": str(ADDED_TSV),
    }
    if not dry_run:
        IMPORT_LOG.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def verify_candidates(candidate_path: str | Path, *, write_files: bool = True) -> dict[str, Any]:
    candidates = load_candidates(candidate_path)
    candidate_words = [row["Hanzi"] for row in candidates]
    notes = load_notes()
    notes_by_word = {note_field(note, "Word") or note_field(note, "Front"): note for note in notes}
    present = [word for word in candidate_words if word in notes_by_word]
    missing = [word for word in candidate_words if word not in notes_by_word]
    stretch_marked = []
    note_ids = []
    for word in present:
        note = notes_by_word[word]
        note_ids.append(int(note["noteId"]))
        source = note_field(note, "Source").lower()
        tags = {str(tag).lower() for tag in note.get("tags", [])}
        if source.startswith("stretch:") or "stretch_word" in tags:
            stretch_marked.append(word)

    production_cards = []
    if note_ids:
        for start in range(0, len(note_ids), 100):
            batch_notes = anki("notesInfo", {"notes": note_ids[start : start + 100]})
            card_ids = []
            for note in batch_notes:
                card_ids.extend(note.get("cards", []))
            if card_ids:
                production_cards.extend(
                    card for card in anki("cardsInfo", {"cards": card_ids}) if int(card.get("ord", -1)) == 1
                )

    suspended_production = [card for card in production_cards if int(card.get("queue", 0)) < 0]
    active_production = [card for card in production_cards if int(card.get("queue", 0)) >= 0]
    report = {
        "candidate_path": str(Path(candidate_path)),
        "candidate_count": len(candidate_words),
        "present_in_anki_count": len(present),
        "missing_from_anki_count": len(missing),
        "stretch_marked_count": len(stretch_marked),
        "preexisting_or_unmarked_count": len(present) - len(stretch_marked),
        "production_cards_found": len(production_cards),
        "production_cards_suspended": len(suspended_production),
        "production_cards_active": len(active_production),
        "missing_from_anki": missing,
        "note": "Words already present before stretch import may not carry stretch_word tags.",
    }

    if write_files:
        IMPORT_LOG.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        added_rows = []
        rows_by_word = {row["Hanzi"]: row for row in candidates}
        for word in stretch_marked:
            note = notes_by_word[word]
            source = note_field(note, "Source")
            candidate = rows_by_word.get(word, {})
            added_rows.append(
                {
                    "Note ID": str(note["noteId"]),
                    "Word": word,
                    "Pinyin": note_field(note, "Pinyin"),
                    "Meaning": note_field(note, "Meaning"),
                    "Pack": candidate.get("Pack", ""),
                    "Layer": candidate.get("Layer", ""),
                    "Meaning Source": source.split("meaning=", 1)[1].split(";", 1)[0] if "meaning=" in source else "",
                    "Example Source": source.split("example=", 1)[1].split(";", 1)[0] if "example=" in source else "",
                    "Example": note_field(note, "Example"),
                    "Example Meaning": note_field(note, "Example Meaning"),
                    "Source": source,
                    "Status": "active in Anki",
                }
            )
        write_added(added_rows)
        ready_path = ANKI_DIR / "stretch_word_import_ready.tsv"
        fieldnames = [
            "Hanzi",
            "Pinyin",
            "English",
            "PartOfSpeech",
            "Pack",
            "Layer",
            "Priority",
            "SourceBook",
            "FirstChapter",
            "ExampleSentenceZhTok",
            "ExampleSentenceZhNatural",
            "ExampleSentenceEnglish",
            "Status",
            "Notes",
        ]
        with ready_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in candidates:
                row = dict(row)
                row["Status"] = "active in Anki" if row["Hanzi"] in present else "candidate"
                writer.writerow({field: row.get(field, "") for field in fieldnames})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reviewed stretch-word candidates into the live Anki deck.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    report = verify_candidates(args.candidates) if args.verify_only else import_stretch_words(args.candidates, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
