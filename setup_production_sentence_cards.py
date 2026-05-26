from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
WORD_LIST = ROOT / "word list chinese.txt"
BACKUP_TSV = ROOT / "production_sentence_setup_backup.tsv"
REPORT_MD = ROOT / "production_sentence_setup_report.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DECK_QUERY = "deck:Default"
MODEL_NAME = "Chinese Vocabulary"

PRODUCTION_FIELD = "Production Card"
SENTENCE_FIELD = "Sentence Card"
RANK_FIELD = "Frequency Rank"

SENTENCE_TEMPLATE = {
    "Name": "Sentence Recognition",
    "Front": """
{{#Sentence Card}}
<div class="example sentence-front">{{Example}}</div>
{{/Sentence Card}}
""".strip(),
    "Back": """
{{FrontSide}}
<hr id="answer">
<div class="example-pinyin">{{Example Pinyin}}</div>
<div class="example-meaning">{{Example Meaning}}</div>
<div class="target-word">Target word: <span class="word-inline">{{Word}}</span></div>
<div class="pinyin">{{Pinyin}}</div>
<div class="meaning">{{Meaning}}</div>
""".strip(),
}

CSS_APPEND = """

.sentence-front {
    font-size: 32px;
}
.target-word {
    color: #444;
    font-size: 18px;
    margin-top: 18px;
}
.word-inline {
    color: #111;
    font-size: 24px;
    font-weight: 600;
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


def read_ranks() -> dict[str, int]:
    ranks: dict[str, int] = {}
    for index, line in enumerate(WORD_LIST.read_text(encoding="utf-8-sig").splitlines(), start=1):
        word = clean(line)
        if word and word not in ranks:
            ranks[word] = index
    return ranks


def note_field(note: dict[str, Any], name: str) -> str:
    return clean(note.get("fields", {}).get(name, {}).get("value", ""))


def is_stretch_note(note: dict[str, Any]) -> bool:
    source = note_field(note, "Source").lower()
    tags = {str(tag).lower() for tag in note.get("tags", [])}
    return source.startswith("stretch:") or "stretch_word" in tags


def load_notes() -> list[dict[str, Any]]:
    note_ids = anki("findNotes", {"query": DECK_QUERY})
    notes: list[dict[str, Any]] = []
    for start in range(0, len(note_ids), 250):
        notes.extend(anki("notesInfo", {"notes": note_ids[start : start + 250]}))
    notes.sort(key=lambda note: int(note["noteId"]))
    return notes


def load_cards() -> list[dict[str, Any]]:
    card_ids = anki("findCards", {"query": DECK_QUERY})
    cards: list[dict[str, Any]] = []
    for start in range(0, len(card_ids), 500):
        cards.extend(anki("cardsInfo", {"cards": card_ids[start : start + 500]}))
    return cards


def write_backup(notes: list[dict[str, Any]], cards: list[dict[str, Any]]) -> None:
    cards_by_note: dict[int, list[dict[str, Any]]] = {}
    for card in cards:
        cards_by_note.setdefault(int(card["note"]), []).append(card)

    fieldnames = [
        "Note ID",
        "Word",
        "Old Production Card",
        "Old Sentence Card",
        "Old Frequency Rank",
        "Card States",
    ]
    rows = []
    for note in notes:
        note_id = int(note["noteId"])
        card_states = []
        for card in sorted(cards_by_note.get(note_id, []), key=lambda item: int(item["ord"])):
            card_states.append(
                f"id={card['cardId']};ord={card['ord']};queue={card['queue']};type={card['type']}"
            )
        rows.append(
            {
                "Note ID": str(note_id),
                "Word": note_field(note, "Word"),
                "Old Production Card": note_field(note, PRODUCTION_FIELD),
                "Old Sentence Card": note_field(note, SENTENCE_FIELD),
                "Old Frequency Rank": note_field(note, RANK_FIELD),
                "Card States": " | ".join(card_states),
            }
        )

    with BACKUP_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def ensure_fields() -> None:
    fields = anki("modelFieldNames", {"modelName": MODEL_NAME})
    if PRODUCTION_FIELD not in fields:
        anki("modelFieldAdd", {"modelName": MODEL_NAME, "fieldName": PRODUCTION_FIELD, "index": 7})
    if RANK_FIELD not in anki("modelFieldNames", {"modelName": MODEL_NAME}):
        anki("modelFieldAdd", {"modelName": MODEL_NAME, "fieldName": RANK_FIELD, "index": 9})


def has_sentence_fields(note: dict[str, Any]) -> bool:
    return bool(note_field(note, "Example") and note_field(note, "Example Meaning"))


def update_note_flags(notes: list[dict[str, Any]], ranks: dict[str, int]) -> None:
    actions = []
    missing_words: list[str] = []

    for note in notes:
        word = note_field(note, "Word")
        rank = ranks.get(word)
        sentence_value = "yes" if has_sentence_fields(note) else ""
        if not rank:
            if is_stretch_note(note):
                actions.append(
                    {
                        "action": "updateNoteFields",
                        "params": {
                            "note": {
                                "id": int(note["noteId"]),
                                "fields": {
                                    RANK_FIELD: "",
                                    SENTENCE_FIELD: sentence_value,
                                },
                            }
                        },
                    }
                )
                continue
            missing_words.append(word)
            continue

        fields = {
            RANK_FIELD: str(rank),
            SENTENCE_FIELD: sentence_value,
        }
        actions.append(
            {
                "action": "updateNoteFields",
                "params": {"note": {"id": int(note["noteId"]), "fields": fields}},
            }
        )

    if missing_words:
        raise RuntimeError(f"Missing rank for {len(missing_words)} notes: {missing_words[:10]}")

    for start in range(0, len(actions), 50):
        results = anki("multi", {"actions": actions[start : start + 50]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])


def ensure_sentence_template() -> None:
    templates = anki("modelTemplates", {"modelName": MODEL_NAME})
    if SENTENCE_TEMPLATE["Name"] not in templates:
        anki("modelTemplateAdd", {"modelName": MODEL_NAME, "template": SENTENCE_TEMPLATE})
    else:
        # Keep it idempotent and allow template refinements.
        anki("updateModelTemplates", {"model": {"name": MODEL_NAME, "templates": {SENTENCE_TEMPLATE["Name"]: {"Front": SENTENCE_TEMPLATE["Front"], "Back": SENTENCE_TEMPLATE["Back"]}}}})

    styling = anki("modelStyling", {"modelName": MODEL_NAME})["css"]
    if ".sentence-front" not in styling:
        anki("updateModelStyling", {"model": {"name": MODEL_NAME, "css": styling.rstrip() + "\n" + CSS_APPEND + "\n"}})


def production_cards_to_suspend(cards: list[dict[str, Any]]) -> list[int]:
    return [int(card["cardId"]) for card in cards if int(card["ord"]) == 1 and int(card["queue"]) >= 0]


def sentence_cards_to_unsuspend(cards: list[dict[str, Any]]) -> list[int]:
    return [int(card["cardId"]) for card in cards if int(card["ord"]) == 2 and int(card["queue"]) < 0]


def suspend_cards(card_ids: list[int]) -> None:
    for start in range(0, len(card_ids), 500):
        anki("suspend", {"cards": card_ids[start : start + 500]})


def unsuspend_cards(card_ids: list[int]) -> None:
    for start in range(0, len(card_ids), 500):
        anki("unsuspend", {"cards": card_ids[start : start + 500]})


def verify() -> dict[str, Any]:
    notes = load_notes()
    cards = load_cards()
    field_counts = Counter()
    template_counts = Counter()
    active_by_ord = Counter()
    suspended_by_ord = Counter()

    for note in notes:
        if note_field(note, PRODUCTION_FIELD):
            field_counts["production_yes"] += 1
        if note_field(note, SENTENCE_FIELD):
            field_counts["sentence_yes"] += 1
        if note_field(note, RANK_FIELD):
            field_counts["ranked"] += 1
        if note_field(note, "Meaning"):
            field_counts["meaning"] += 1
        if note_field(note, "Example"):
            field_counts["example"] += 1
        if note_field(note, "Example Meaning"):
            field_counts["example_meaning"] += 1

    for card in cards:
        ord_value = int(card["ord"])
        template_counts[ord_value] += 1
        if int(card["queue"]) < 0:
            suspended_by_ord[ord_value] += 1
        else:
            active_by_ord[ord_value] += 1

    return {
        "notes": len(notes),
        "cards": len(cards),
        "production_field_yes": field_counts["production_yes"],
        "sentence_field_yes": field_counts["sentence_yes"],
        "ranked_notes": field_counts["ranked"],
        "notes_with_meaning": field_counts["meaning"],
        "notes_with_example": field_counts["example"],
        "notes_with_example_meaning": field_counts["example_meaning"],
        "card_counts_by_ord": dict(sorted(template_counts.items())),
        "active_counts_by_ord": dict(sorted(active_by_ord.items())),
        "suspended_counts_by_ord": dict(sorted(suspended_by_ord.items())),
    }


def write_report(result: dict[str, Any], suspended_count: int, unsuspended_sentence_count: int) -> None:
    lines = [
        "# Production And Sentence Card Setup Report",
        "",
        "Standard word-recognition meaning cards are active for every note unless manually suspended.",
        "Sentence cards are enabled for every note with `Example` and `Example Meaning` fields.",
        "Production / meaning-recall cards are suspended by this script.",
        f"Suspended production cards: {suspended_count}",
        f"Unsuspended sentence cards: {unsuspended_sentence_count}",
        "",
        f"Notes: {result['notes']}",
        f"Cards: {result['cards']}",
        f"Notes with Production Card = yes: {result['production_field_yes']}",
        f"Notes with Sentence Card = yes: {result['sentence_field_yes']}",
        f"Notes with Frequency Rank: {result['ranked_notes']}",
        f"Notes with Meaning: {result['notes_with_meaning']}",
        f"Notes with Example: {result['notes_with_example']}",
        f"Notes with Example Meaning: {result['notes_with_example_meaning']}",
        "",
        "Card counts by template ord:",
    ]
    for ord_value, count in result["card_counts_by_ord"].items():
        lines.append(f"- ord {ord_value}: {count}")
    lines.append("")
    lines.append("Active counts by template ord:")
    for ord_value, count in result["active_counts_by_ord"].items():
        lines.append(f"- ord {ord_value}: {count}")
    lines.append("")
    lines.append("Suspended counts by template ord:")
    for ord_value, count in result["suspended_counts_by_ord"].items():
        lines.append(f"- ord {ord_value}: {count}")
    lines.extend(["", f"Backup file: {BACKUP_TSV.name}"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> None:
    ranks = read_ranks()
    notes_before = load_notes()
    cards_before = load_cards()
    write_backup(notes_before, cards_before)

    ensure_fields()
    update_note_flags(notes_before, ranks)
    ensure_sentence_template()

    notes_after_template = load_notes()
    cards_after_template = load_cards()
    cards_to_suspend = production_cards_to_suspend(cards_after_template)
    suspend_cards(cards_to_suspend)
    cards_after_suspend = load_cards()
    sentence_cards_to_restore = sentence_cards_to_unsuspend(cards_after_suspend)
    unsuspend_cards(sentence_cards_to_restore)

    result = verify()
    write_report(result, suspended_count=len(cards_to_suspend), unsuspended_sentence_count=len(sentence_cards_to_restore))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
