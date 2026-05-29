from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import build_anki_chinese
import setup_production_sentence_cards
from scripts.schedule_anki_learning_order import run_learning_order_scheduler


ROOT = Path(__file__).resolve().parent
WORD_LIST = ROOT / "word list chinese.txt"
PROPOSAL_TSV = ROOT / "missing_single_character_notes_proposal.tsv"
SOURCE_TSV = ROOT / "anki_chinese_review.tsv"
WORD_LIST_BACKUP = ROOT / "word_list_before_single_character_notes_backup.txt"
APPLIED_TSV = ROOT / "single_character_notes_added.tsv"
REPORT_MD = ROOT / "single_character_notes_add_report.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_NAME = "Default"
DECK_QUERY = "deck:Default"
MODEL_NAME = "Chinese Vocabulary"


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


def load_proposal_rows() -> list[dict[str, str]]:
    with PROPOSAL_TSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle, delimiter="\t")]
    if not rows:
        raise RuntimeError(f"No proposal rows found in {PROPOSAL_TSV.name}")
    return rows


def read_words() -> list[str]:
    return [line.strip() for line in WORD_LIST.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def append_words_to_source(proposed_chars: list[str]) -> tuple[list[str], list[str]]:
    words = read_words()
    existing = set(words)
    to_append = [char for char in proposed_chars if char not in existing]

    if not to_append:
        return words, []

    if not WORD_LIST_BACKUP.exists():
        WORD_LIST_BACKUP.write_text(WORD_LIST.read_text(encoding="utf-8-sig"), encoding="utf-8")

    updated_words = words + to_append
    WORD_LIST.write_text("\n".join(updated_words) + "\n", encoding="utf-8")
    return updated_words, to_append


def ranks_by_word(words: list[str]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for rank, word in enumerate(words, start=1):
        ranks.setdefault(word, rank)
    return ranks


def load_source_rows() -> dict[str, dict[str, str]]:
    with SOURCE_TSV.open(encoding="utf-8", newline="") as handle:
        return {
            clean(row["Word"]): {key: clean(value) for key, value in row.items()}
            for row in csv.DictReader(handle, delimiter="\t")
        }


def load_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    return notes


def source_tags(source_row: dict[str, str], priority: str) -> list[str]:
    tags = {
        "chinese_vocab",
        "has_example",
        "single_character_note",
        "character_gap_fill",
        f"character_priority_{priority}",
    }
    tags.update(tag for tag in source_row.get("Tags", "").split() if tag)
    return sorted(tags)


def anki_note(source_row: dict[str, str], rank: int, priority: str) -> dict[str, Any]:
    fields = {
        "Word": source_row["Word"],
        "Pinyin": source_row["Pinyin"],
        "Meaning": source_row["Meaning"],
        "Example": source_row["Example"],
        "Example Pinyin": source_row["Example Pinyin"],
        "Example Meaning": source_row["Example Meaning"],
        "Source": source_row["Tags"],
        "Production Card": "",
        "Sentence Card": "",
        "Frequency Rank": str(rank),
    }
    missing_fields = [field for field, value in fields.items() if field not in {"Production Card", "Sentence Card"} and not value]
    if missing_fields:
        raise RuntimeError(f"{source_row['Word']} has blank required fields: {missing_fields}")

    if " generated" in f" {source_row['Tags']}":
        raise RuntimeError(f"{source_row['Word']} would use a generated placeholder example")

    return {
        "deckName": DECK_NAME,
        "modelName": MODEL_NAME,
        "fields": fields,
        "tags": source_tags(source_row, priority),
        "options": {"allowDuplicate": False, "duplicateScope": "deck", "duplicateScopeOptions": {"deckName": DECK_NAME}},
    }


def add_notes(proposal_rows: list[dict[str, str]], ranks: dict[str, int], source_by_word: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    existing_words = {note_field(note, "Word") for note in load_notes()}
    notes_to_add: list[dict[str, Any]] = []
    add_metadata: list[dict[str, str]] = []

    for row in proposal_rows:
        char = row["Character"]
        if char in existing_words:
            continue
        source_row = source_by_word.get(char)
        if not source_row:
            raise RuntimeError(f"Missing rebuilt source TSV row for {char}")
        rank = ranks.get(char)
        if not rank:
            raise RuntimeError(f"Missing frequency rank for {char}")

        notes_to_add.append(anki_note(source_row, rank, row["Priority"]))
        add_metadata.append(
            {
                "Character": char,
                "Pinyin": source_row["Pinyin"],
                "Meaning": source_row["Meaning"],
                "Priority": row["Priority"],
                "Frequency Rank": str(rank),
                "First Deck Word": row["First Word"],
                "First Deck Word Rank": row["First Rank"],
                "Example": source_row["Example"],
                "Example Meaning": source_row["Example Meaning"],
            }
        )

    added_note_ids: list[int] = []
    for start in range(0, len(notes_to_add), 50):
        result = anki("addNotes", {"notes": notes_to_add[start : start + 50]})
        if len(result) != len(notes_to_add[start : start + 50]):
            raise RuntimeError("Unexpected addNotes result length")
        if any(note_id is None for note_id in result):
            failed = [add_metadata[start + index]["Character"] for index, note_id in enumerate(result) if note_id is None]
            raise RuntimeError(f"Anki refused to add notes: {failed[:20]}")
        added_note_ids.extend(int(note_id) for note_id in result)

    for row, note_id in zip(add_metadata, added_note_ids):
        row["Note ID"] = str(note_id)
    return add_metadata


def write_applied(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "Note ID",
        "Character",
        "Pinyin",
        "Meaning",
        "Priority",
        "Frequency Rank",
        "First Deck Word",
        "First Deck Word Rank",
        "Example",
        "Example Meaning",
    ]
    with APPLIED_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def verify(proposed_chars: list[str]) -> dict[str, Any]:
    notes = load_notes()
    words = {note_field(note, "Word") for note in notes}
    missing = [char for char in proposed_chars if char not in words]
    added_notes = [note for note in notes if note_field(note, "Word") in set(proposed_chars)]
    blank_required = []
    for note in added_notes:
        for field in ["Word", "Pinyin", "Meaning", "Example", "Example Pinyin", "Example Meaning", "Source", "Frequency Rank"]:
            if not note_field(note, field):
                blank_required.append(f"{note_field(note, 'Word')}:{field}")

    cards = anki("findCards", {"query": DECK_QUERY})
    return {
        "notes": len(notes),
        "cards": len(cards),
        "proposed_chars": len(proposed_chars),
        "proposed_missing_after_add": len(missing),
        "blank_required_fields": blank_required[:20],
        "added_or_existing_single_chars": len(added_notes),
    }


def write_report(
    proposal_rows: list[dict[str, str]],
    appended_chars: list[str],
    added_rows: list[dict[str, str]],
    verification: dict[str, Any],
    scheduler_result: dict[str, Any],
) -> None:
    priority_counts: dict[str, int] = {}
    for row in added_rows:
        priority_counts[row["Priority"]] = priority_counts.get(row["Priority"], 0) + 1

    lines = [
        "# Single Character Notes Add Report",
        "",
        f"Proposed characters: {len(proposal_rows)}",
        f"Characters appended to word list: {len(appended_chars)}",
        f"Notes added to Anki: {len(added_rows)}",
        f"Live notes after add: {verification['notes']}",
        f"Live cards after add/setup: {verification['cards']}",
        f"Proposed characters missing after add: {verification['proposed_missing_after_add']}",
        f"Added/existing proposed character notes found: {verification['added_or_existing_single_chars']}",
        "",
        "Added note priorities:",
    ]
    for priority in ["high", "medium", "low"]:
        lines.append(f"- {priority}: {priority_counts.get(priority, 0)}")
    lines.extend(
        [
            "",
            "Files:",
            f"- {WORD_LIST_BACKUP.name}: source word-list backup before append",
            f"- {APPLIED_TSV.name}: added note IDs and fields",
            f"- {SOURCE_TSV.name}: rebuilt TSV source data",
            f"- anki/learning_order_plan.tsv: generated learning-order plan",
            f"- single_character_distribution_report.md: before/after character distribution report",
        ]
    )
    scheduler_summary = scheduler_result["summary"]
    anki_scheduler = scheduler_result.get("anki_result", {})
    lines.extend(
        [
            "",
            "Learning order scheduling:",
            f"- active learning-order rows: {scheduler_summary['active_rows']}",
            f"- live new normal notes available: {anki_scheduler.get('new_normal_notes', 0)}",
            f"- live single-character notes included: {anki_scheduler.get('released_single_character_notes', 0)}",
            f"- Chinese-to-English cards unsuspended this run: {anki_scheduler.get('cn_to_en_cards_unsuspended', 0)}",
            f"- suspended Chinese-to-English new cards remaining: {anki_scheduler.get('cn_to_en_new_cards_still_suspended', 0)}",
        ]
    )
    if verification["blank_required_fields"]:
        lines.extend(["", "Blank required fields found:", *[f"- {item}" for item in verification["blank_required_fields"]]])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    proposal_rows = load_proposal_rows()
    proposed_chars = [row["Character"] for row in proposal_rows]

    words_after_append, appended_chars = append_words_to_source(proposed_chars)
    build_anki_chinese.main()

    ranks = ranks_by_word(words_after_append)
    source_by_word = load_source_rows()
    added_rows = add_notes(proposal_rows, ranks, source_by_word)
    write_applied(added_rows)

    setup_production_sentence_cards.main()
    scheduler_result = run_learning_order_scheduler(apply_anki=True)
    verification = verify(proposed_chars)
    write_report(proposal_rows, appended_chars, added_rows, verification, scheduler_result)
    print(
        json.dumps(
            {
                **verification,
                "appended_chars": len(appended_chars),
                "notes_added": len(added_rows),
                "learning_order_summary": scheduler_result["summary"],
                "anki_scheduler": scheduler_result.get("anki_result", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
