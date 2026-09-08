from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from html import unescape
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.first_frost.content import MANIFEST_PATH, clean, load_manifest  # noqa: E402
from scripts.first_frost.validate_first_frost_pilot import validate_manifest  # noqa: E402


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
MODEL_NAME = "Chinese Vocabulary"
MODEL_QUERY = 'note:"Chinese Vocabulary"'
DECK_NAME = "Default"

REQUIRED_FIELDS = (
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
)
REQUIRED_TEMPLATES = ("Word Recognition", "Sentence Recognition")
PILOT_TAG = "pilot_first_frost_01"
PRIORITY_TAG_PREFIX = "pilot_first_frost_priority_"
SOURCE_SEPARATOR = " | "
BACKUP_PATH = ROOT / "first_frost_pilot_before_apply_backup.tsv"
REPORT_DIR = ROOT / "anki" / "first_frost" / "reports"

SUPPORT_ROWS = (
    {
        "Word": "勉",
        "Pinyin": "miǎn",
        "Meaning": "to exert oneself; to strive; to encourage",
        "Example": "他勉励自己继续努力。",
        "Example Pinyin": "Tā miǎnlì zìjǐ jìxù nǔlì.",
        "Example Meaning": "He encouraged himself to keep working hard.",
        "Source": "character-closure:First Frost reading-vocabulary pilot",
        "Tags": "chinese_vocab single_character_note character_gap_fill source_first_frost_support book_first_frost",
    },
    {
        "Word": "慎",
        "Pinyin": "shèn",
        "Meaning": "careful; cautious",
        "Example": "做这个决定要慎重。",
        "Example Pinyin": "Zuò zhège juédìng yào shènzhòng.",
        "Example Meaning": "This decision needs to be made carefully.",
        "Source": "character-closure:First Frost reading-vocabulary pilot",
        "Tags": "chinese_vocab single_character_note character_gap_fill source_first_frost_support book_first_frost",
    },
    {
        "Word": "谨",
        "Pinyin": "jǐn",
        "Meaning": "careful; cautious; solemn",
        "Example": "他说话一向很谨慎。",
        "Example Pinyin": "Tā shuōhuà yīxiàng hěn jǐnshèn.",
        "Example Meaning": "He is always very careful in what he says.",
        "Source": "character-closure:First Frost reading-vocabulary pilot",
        "Tags": "chinese_vocab single_character_note character_gap_fill source_first_frost_support book_first_frost",
    },
)

SCHEDULE_KEYS = (
    "type",
    "queue",
    "due",
    "interval",
    "factor",
    "reps",
    "lapses",
    "left",
    "odue",
    "odid",
)


class FirstFrostPilotError(RuntimeError):
    """Raised when a guarded pilot precondition or verification fails."""


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
        raise FirstFrostPilotError(data["error"])
    return data.get("result")


def chunked(values: list[int], size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def note_field(note: dict[str, Any], name: str) -> str:
    return clean(note.get("fields", {}).get(name, {}).get("value", ""))


def note_tags(note: dict[str, Any]) -> set[str]:
    return {clean(str(tag)) for tag in note.get("tags", []) if clean(str(tag))}


def merge_source(existing: str, addition: str) -> str:
    existing = clean(existing)
    addition = clean(addition)
    if not existing:
        return addition
    if not addition or addition in [clean(part) for part in existing.split(SOURCE_SEPARATOR)]:
        return existing
    return f"{existing}{SOURCE_SEPARATOR}{addition}"


def desired_pilot_fields(row: dict[str, str], existing_note: dict[str, Any] | None = None) -> dict[str, str]:
    pinyin = row["Pinyin"]
    meaning = row["Meaning"]
    # The reviewed pilot usage is chéng. Keep the valid shèng reading/sense visible too.
    if row["Word"] == "盛":
        pinyin = "chéng; shèng"
        meaning = f"{row['Meaning']} | shèng: flourishing; prosperous"
    existing_source = note_field(existing_note, "Source") if existing_note else ""
    return {
        "Pinyin": pinyin,
        "Meaning": meaning,
        "Example": row["Example"],
        "Example Pinyin": row["Example Pinyin"],
        "Example Meaning": row["Example Meaning"],
        "Source": merge_source(existing_source, row["Source"]),
        "Sentence Card": "yes",
    }


def desired_support_fields(row: dict[str, str], existing_note: dict[str, Any] | None = None) -> dict[str, str]:
    existing_source = note_field(existing_note, "Source") if existing_note else ""
    fields = {
        "Pinyin": row["Pinyin"],
        "Meaning": row["Meaning"],
        "Example": row["Example"],
        "Example Pinyin": row["Example Pinyin"],
        "Example Meaning": row["Example Meaning"],
        "Source": merge_source(existing_source, row["Source"]),
        "Sentence Card": "yes",
    }
    if existing_note:
        # Existing support notes are tagged, but their established study content is not replaced.
        for name in ("Pinyin", "Meaning", "Example", "Example Pinyin", "Example Meaning"):
            fields[name] = note_field(existing_note, name)
    return fields


def pilot_tags(row: dict[str, str]) -> set[str]:
    priority = int(row["Pilot Priority"])
    return {
        *row["Tags"].split(),
        "has_example",
        f"{PRIORITY_TAG_PREFIX}{priority:03d}",
    }


def support_tags(row: dict[str, str]) -> set[str]:
    return {*row["Tags"].split(), "has_example"}


def load_live_state(call_anki: Callable[[str, dict[str, Any] | None], Any]) -> dict[str, Any]:
    model_names = call_anki("modelNames", None)
    if MODEL_NAME not in model_names:
        raise FirstFrostPilotError(f"Missing note type {MODEL_NAME!r}")
    fields = call_anki("modelFieldNames", {"modelName": MODEL_NAME})
    missing_fields = [field for field in REQUIRED_FIELDS if field not in fields]
    if missing_fields:
        raise FirstFrostPilotError(f"{MODEL_NAME!r} is missing fields: {missing_fields}")
    templates = call_anki("modelTemplates", {"modelName": MODEL_NAME})
    template_names = list(templates)
    if template_names != list(REQUIRED_TEMPLATES):
        raise FirstFrostPilotError(
            f"Expected templates {list(REQUIRED_TEMPLATES)}, found {template_names}; refusing a model-wide change"
        )

    note_ids = [int(value) for value in call_anki("findNotes", {"query": MODEL_QUERY})]
    notes: list[dict[str, Any]] = []
    for batch in chunked(note_ids, 250):
        notes.extend(call_anki("notesInfo", {"notes": batch}))
    card_ids = [int(card_id) for note in notes for card_id in note.get("cards", [])]
    cards: list[dict[str, Any]] = []
    for batch in chunked(card_ids, 500):
        cards.extend(call_anki("cardsInfo", {"cards": batch}))
    return {
        "fields": fields,
        "templates": template_names,
        "notes": notes,
        "cards": cards,
    }


def group_notes(notes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for note in notes:
        word = note_field(note, "Word")
        if word:
            grouped[word].append(note)
    return dict(grouped)


def group_cards(cards: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        grouped[int(card["note"])].append(card)
    return dict(grouped)


def new_note_payload(
    row: dict[str, str],
    *,
    support: bool,
) -> dict[str, Any]:
    desired = desired_support_fields(row) if support else desired_pilot_fields(row)
    fields = {
        "Word": row["Word"],
        **desired,
        "Production Card": "",
        "Frequency Rank": "",
    }
    tags = support_tags(row) if support else pilot_tags(row)
    return {
        "deckName": DECK_NAME,
        "modelName": MODEL_NAME,
        "fields": fields,
        "tags": sorted(tags),
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {"deckName": DECK_NAME},
        },
    }


def card_schedule(card: dict[str, Any]) -> dict[str, int]:
    return {key: int(card.get(key, 0) or 0) for key in SCHEDULE_KEYS}


def reviewed_schedule_snapshot(cards: list[dict[str, Any]]) -> dict[int, dict[str, int]]:
    return {
        int(card["cardId"]): card_schedule(card)
        for card in cards
        if int(card.get("type", 0)) != 0
    }


def priority_card_ids(
    manifest_rows: list[dict[str, str]],
    notes_by_word: dict[str, list[dict[str, Any]]],
    cards_by_note: dict[int, list[dict[str, Any]]],
    *,
    include_suspended: bool,
) -> list[int]:
    ordered: list[tuple[int, int, int]] = []
    for row in manifest_rows:
        notes = notes_by_word.get(row["Word"], [])
        if len(notes) != 1:
            continue
        for card in cards_by_note.get(int(notes[0]["noteId"]), []):
            card_type = int(card.get("type", -1))
            queue = int(card.get("queue", -1))
            card_ord = int(card.get("ord", -1))
            if card_ord not in (0, 1) or card_type != 0:
                continue
            if include_suspended or queue >= 0:
                ordered.append((int(row["Pilot Priority"]), card_ord, int(card["cardId"])))
    return [card_id for _, _, card_id in sorted(ordered)]


def priority_is_correct(
    manifest_rows: list[dict[str, str]],
    notes_by_word: dict[str, list[dict[str, Any]]],
    cards_by_note: dict[int, list[dict[str, Any]]],
    all_cards: list[dict[str, Any]],
) -> bool:
    expected = priority_card_ids(
        manifest_rows,
        notes_by_word,
        cards_by_note,
        include_suspended=False,
    )
    if not expected:
        return False
    by_id = {int(card["cardId"]): card for card in all_cards}
    actual = sorted(expected, key=lambda card_id: (int(by_id[card_id].get("due", 0)), card_id))
    if actual != expected:
        return False
    generic_active_new = [
        card
        for card in all_cards
        if int(card.get("type", -1)) == 0
        and int(card.get("queue", -1)) >= 0
        and int(card["cardId"]) not in set(expected)
    ]
    if generic_active_new:
        return max(int(by_id[card_id].get("due", 0)) for card_id in expected) < min(
            int(card.get("due", 0)) for card in generic_active_new
        )
    return True


def build_plan(
    *,
    manifest_path: Path,
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation = validate_manifest(manifest_path)
    if validation["status"] != "PASS":
        raise FirstFrostPilotError("Manifest validation failed: " + "; ".join(validation["errors"]))
    rows = load_manifest(manifest_path)
    state = load_live_state(call_anki)
    notes_by_word = group_notes(state["notes"])
    cards_by_note = group_cards(state["cards"])
    target_words = {row["Word"] for row in rows}
    support_words = {row["Word"] for row in SUPPORT_ROWS}
    duplicate_conflicts = {
        word: [int(note["noteId"]) for note in notes_by_word.get(word, [])]
        for word in sorted(target_words | support_words)
        if len(notes_by_word.get(word, [])) > 1
    }
    if duplicate_conflicts:
        raise FirstFrostPilotError(f"Duplicate live notes in {MODEL_NAME}: {duplicate_conflicts}")

    updates: list[dict[str, Any]] = []
    target_additions: list[dict[str, Any]] = []
    support_additions: list[dict[str, Any]] = []
    reused_words: list[str] = []
    support_reused_words: list[str] = []
    existing_target_card_count = 0
    existing_card_shape_conflicts: list[dict[str, Any]] = []
    existing_deck_conflicts: list[dict[str, Any]] = []

    for row in rows:
        existing = notes_by_word.get(row["Word"], [])
        if not existing:
            target_additions.append(new_note_payload(row, support=False))
            continue
        note = existing[0]
        reused_words.append(row["Word"])
        note_id = int(note["noteId"])
        cards = cards_by_note.get(note_id, [])
        existing_target_card_count += len(cards)
        ords = sorted(int(card.get("ord", -1)) for card in cards)
        if ords != [0, 1]:
            existing_card_shape_conflicts.append({"word": row["Word"], "card_ords": ords})
        decks = sorted({clean(str(card.get("deckName", ""))) for card in cards})
        if decks != [DECK_NAME]:
            existing_deck_conflicts.append({"word": row["Word"], "decks": decks})
        desired_fields = desired_pilot_fields(row, note)
        missing_tags = pilot_tags(row) - note_tags(note)
        changed_fields = {
            name: value
            for name, value in desired_fields.items()
            if note_field(note, name) != value
        }
        if changed_fields or missing_tags:
            updates.append(
                {
                    "kind": "pilot",
                    "word": row["Word"],
                    "note_id": note_id,
                    "fields": changed_fields,
                    "tags": sorted(missing_tags),
                }
            )

    for row in SUPPORT_ROWS:
        existing = notes_by_word.get(row["Word"], [])
        if not existing:
            support_additions.append(new_note_payload(row, support=True))
            continue
        note = existing[0]
        support_reused_words.append(row["Word"])
        desired_fields = desired_support_fields(row, note)
        missing_tags = support_tags(row) - note_tags(note)
        changed_fields = {
            name: value
            for name, value in desired_fields.items()
            if note_field(note, name) != value
        }
        if changed_fields or missing_tags:
            updates.append(
                {
                    "kind": "support",
                    "word": row["Word"],
                    "note_id": int(note["noteId"]),
                    "fields": changed_fields,
                    "tags": sorted(missing_tags),
                }
            )

    additions = target_additions + support_additions
    if additions:
        can_add = call_anki("canAddNotes", {"notes": additions})
        if not isinstance(can_add, list) or len(can_add) != len(additions):
            raise FirstFrostPilotError("Anki returned an invalid canAddNotes response")
        refused = [additions[index]["fields"]["Word"] for index, allowed in enumerate(can_add) if not allowed]
        if refused:
            raise FirstFrostPilotError(f"Anki duplicate preflight refused: {refused}")

    existing_target_notes = [notes_by_word[word][0] for word in reused_words]
    existing_target_ids = {int(note["noteId"]) for note in existing_target_notes}
    existing_target_cards = [card for card in state["cards"] if int(card["note"]) in existing_target_ids]
    unseen_target_cards = sum(1 for card in existing_target_cards if int(card.get("type", -1)) == 0)
    suspended_unseen_target_cards = sum(
        1
        for card in existing_target_cards
        if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) == -1
    )
    reviewed_target_cards = sum(1 for card in existing_target_cards if int(card.get("type", -1)) != 0)

    plan = {
        "status": "PASS" if not existing_card_shape_conflicts and not existing_deck_conflicts else "ERROR",
        "mode": "dry-run",
        "manifest_validation": validation,
        "model": MODEL_NAME,
        "deck": DECK_NAME,
        "target_notes": 60,
        "reused_target_notes": len(reused_words),
        "reused_target_words": reused_words,
        "target_notes_to_update": sum(1 for update in updates if update["kind"] == "pilot"),
        "target_notes_to_create": len(target_additions),
        "existing_target_cards": existing_target_card_count,
        "target_cards_to_create": len(target_additions) * 2,
        "reviewed_target_cards_preserved": reviewed_target_cards,
        "unseen_target_cards_after_apply": unseen_target_cards + len(target_additions) * 2,
        "target_cards_to_unsuspend": suspended_unseen_target_cards,
        "new_target_cards_created_accessible": len(target_additions) * 2,
        "target_cards_newly_accessible": suspended_unseen_target_cards + len(target_additions) * 2,
        "target_cards_to_prioritize": unseen_target_cards + len(target_additions) * 2,
        "support_notes_to_create": len(support_additions),
        "support_notes_reused": len(support_reused_words),
        "support_cards_to_create_suspended": len(support_additions) * 2,
        "support_words": [row["Word"] for row in SUPPORT_ROWS],
        "duplicate_conflicts": duplicate_conflicts,
        "card_shape_conflicts": existing_card_shape_conflicts,
        "deck_conflicts": existing_deck_conflicts,
        "pronunciation_resolutions": ["盛: pilot chéng retained first; valid shèng reading preserved"],
        "sense_resolutions": ["盛: serve/ladle pilot sense retained; flourishing/prosperous shèng sense preserved"],
        "unresolved_pronunciation_conflicts": [],
        "unresolved_sense_conflicts": [],
        "priority_already_correct": priority_is_correct(rows, notes_by_word, cards_by_note, state["cards"]),
        "duplicate_protection": {
            "manifest_unique": True,
            "model_wide_target_unique": True,
            "anki_can_add_notes_preflight": True,
            "anki_allow_duplicate": False,
        },
    }
    if existing_card_shape_conflicts:
        raise FirstFrostPilotError(f"Existing target card shape conflicts: {existing_card_shape_conflicts}")
    if existing_deck_conflicts:
        raise FirstFrostPilotError(f"Existing target deck conflicts: {existing_deck_conflicts}")
    internal = {
        "rows": rows,
        "state": state,
        "notes_by_word": notes_by_word,
        "cards_by_note": cards_by_note,
        "updates": updates,
        "target_additions": target_additions,
        "support_additions": support_additions,
        "reviewed_schedule_before": reviewed_schedule_snapshot(existing_target_cards),
    }
    return plan, internal


def write_backup(
    path: Path,
    notes: list[dict[str, Any]],
    cards_by_note: dict[int, list[dict[str, Any]]],
    target_words: set[str],
    support_words: set[str],
) -> None:
    fields = [
        "Note ID",
        "Kind",
        *REQUIRED_FIELDS,
        "Tags JSON",
        "Cards JSON",
    ]
    rows: list[dict[str, str]] = []
    for note in notes:
        word = note_field(note, "Word")
        if word not in target_words | support_words:
            continue
        note_id = int(note["noteId"])
        rows.append(
            {
                "Note ID": str(note_id),
                "Kind": "pilot" if word in target_words else "support",
                **{field: note_field(note, field) for field in REQUIRED_FIELDS},
                "Tags JSON": json.dumps(sorted(note_tags(note)), ensure_ascii=False),
                "Cards JSON": json.dumps(
                    [
                        {
                            "cardId": int(card["cardId"]),
                            "ord": int(card.get("ord", -1)),
                            **card_schedule(card),
                        }
                        for card in sorted(cards_by_note.get(note_id, []), key=lambda item: int(item.get("ord", -1)))
                    ],
                    ensure_ascii=False,
                ),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def reviewed_schedule_from_backup(path: Path) -> dict[int, dict[str, int]]:
    if not path.exists():
        return {}
    snapshot: dict[int, dict[str, int]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            for card in json.loads(row["Cards JSON"] or "[]"):
                if int(card.get("type", 0)) != 0:
                    snapshot[int(card["cardId"])] = {
                        key: int(card.get(key, 0) or 0) for key in SCHEDULE_KEYS
                    }
    return snapshot


def protected_note_state_from_backup(path: Path) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    protected: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            protected[int(row["Note ID"])] = {
                "Word": row["Word"],
                "Production Card": row["Production Card"],
                "Frequency Rank": row["Frequency Rank"],
                "Source": row["Source"],
                "tags": set(json.loads(row["Tags JSON"] or "[]")),
            }
    return protected


def backup_baseline_stats(path: Path, manifest_rows: list[dict[str, str]]) -> dict[str, int]:
    by_word = {row["Word"]: row for row in manifest_rows}
    stats = {
        "target_notes": 0,
        "target_notes_needing_update": 0,
        "target_cards": 0,
        "target_unseen_suspended_cards": 0,
        "target_reviewed_cards": 0,
        "support_notes": 0,
        "support_cards": 0,
    }
    if not path.exists():
        return stats
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for backup_row in csv.DictReader(handle, delimiter="\t"):
            cards = json.loads(backup_row["Cards JSON"] or "[]")
            if backup_row["Kind"] == "support":
                stats["support_notes"] += 1
                stats["support_cards"] += len(cards)
                continue
            stats["target_notes"] += 1
            stats["target_cards"] += len(cards)
            stats["target_unseen_suspended_cards"] += sum(
                1
                for card in cards
                if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) == -1
            )
            stats["target_reviewed_cards"] += sum(
                1 for card in cards if int(card.get("type", -1)) != 0
            )
            manifest_row = by_word.get(backup_row["Word"])
            if not manifest_row:
                continue
            fake_note = {
                "fields": {
                    field: {"value": backup_row.get(field, "")}
                    for field in REQUIRED_FIELDS
                },
                "tags": json.loads(backup_row["Tags JSON"] or "[]"),
            }
            desired = desired_pilot_fields(manifest_row, fake_note)
            if (
                any(note_field(fake_note, field) != value for field, value in desired.items())
                or not pilot_tags(manifest_row).issubset(note_tags(fake_note))
            ):
                stats["target_notes_needing_update"] += 1
    return stats


def set_new_card_due_order(
    card_ids: list[int],
    call_anki: Callable[[str, dict[str, Any] | None], Any],
    *,
    starting_from: int = 0,
) -> None:
    actions = [
        {
            "action": "setSpecificValueOfCard",
            "params": {
                "card": card_id,
                "keys": ["due"],
                "newValues": [starting_from + index],
            },
        }
        for index, card_id in enumerate(card_ids)
    ]
    for start in range(0, len(actions), 100):
        results = call_anki("multi", {"actions": actions[start : start + 100]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise FirstFrostPilotError(result["error"])


def update_notes(
    updates: list[dict[str, Any]],
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> None:
    for update in updates:
        if update["fields"]:
            call_anki(
                "updateNoteFields",
                {"note": {"id": update["note_id"], "fields": update["fields"]}},
            )
        if update["tags"]:
            call_anki(
                "addTags",
                {"notes": [update["note_id"]], "tags": " ".join(update["tags"])},
            )


def add_notes(
    payloads: list[dict[str, Any]],
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> list[int]:
    added: list[int] = []
    for start in range(0, len(payloads), 50):
        batch = payloads[start : start + 50]
        result = call_anki("addNotes", {"notes": batch})
        if not isinstance(result, list) or len(result) != len(batch) or any(value is None for value in result):
            raise FirstFrostPilotError("Anki refused one or more preflighted notes during addNotes")
        added.extend(int(value) for value in result)
    return added


def mutate_card_batch(
    action: str,
    card_ids: list[int],
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> None:
    for batch in chunked(card_ids, 500):
        call_anki(action, {"cards": batch})


def verify_live(
    *,
    manifest_path: Path,
    call_anki: Callable[[str, dict[str, Any] | None], Any],
    reviewed_schedule_before: dict[int, dict[str, int]] | None = None,
    protected_note_before: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = load_manifest(manifest_path)
    state = load_live_state(call_anki)
    notes_by_word = group_notes(state["notes"])
    cards_by_note = group_cards(state["cards"])
    errors: list[str] = []
    target_note_ids: set[int] = set()
    word_cards = 0
    sentence_cards = 0
    production_cards = 0
    unseen_active = 0
    reviewed_cards = 0
    exact_example_round_trips = 0
    rendered_preview_checks = 0
    rendered_preview_mismatches: list[str] = []

    for row in rows:
        notes = notes_by_word.get(row["Word"], [])
        if len(notes) != 1:
            errors.append(f"{row['Word']}: expected one note, found {len(notes)}")
            continue
        note = notes[0]
        note_id = int(note["noteId"])
        target_note_ids.add(note_id)
        desired = desired_pilot_fields(row, note)
        for field, expected in desired.items():
            if note_field(note, field) != expected:
                errors.append(f"{row['Word']}: {field} did not round-trip exactly")
        if all(
            note_field(note, field) == row[field]
            for field in ("Example", "Example Pinyin", "Example Meaning")
        ):
            exact_example_round_trips += 1
        missing_tags = pilot_tags(row) - note_tags(note)
        if missing_tags:
            errors.append(f"{row['Word']}: missing tags {sorted(missing_tags)}")
        cards = cards_by_note.get(note_id, [])
        for card in cards:
            card_ord = int(card.get("ord", -1))
            question = unescape(str(card.get("question", "")))
            answer = unescape(str(card.get("answer", "")))
            if card_ord == 0:
                word_cards += 1
                rendered_preview_checks += 1
                if row["Word"] not in question or desired["Pinyin"] not in answer or desired["Meaning"] not in answer:
                    rendered_preview_mismatches.append(f"{row['Word']}: Word Recognition render")
            elif card_ord == 1:
                sentence_cards += 1
                rendered_preview_checks += 1
                if (
                    row["Example"] not in question
                    or row["Example Pinyin"] not in answer
                    or row["Example Meaning"] not in answer
                ):
                    rendered_preview_mismatches.append(f"{row['Word']}: Sentence Recognition render")
            else:
                production_cards += 1
            if clean(str(card.get("deckName", ""))) != DECK_NAME:
                errors.append(f"{row['Word']}: recognition card is outside {DECK_NAME}")
            if int(card.get("type", -1)) == 0:
                if int(card.get("queue", -1)) < 0:
                    errors.append(f"{row['Word']}: unseen recognition card remains inaccessible")
                else:
                    unseen_active += 1
            else:
                reviewed_cards += 1

    support_note_ids: set[int] = set()
    support_cards = 0
    support_unseen_suspended = 0
    for row in SUPPORT_ROWS:
        notes = notes_by_word.get(row["Word"], [])
        if len(notes) != 1:
            errors.append(f"Support {row['Word']}: expected one note, found {len(notes)}")
            continue
        note = notes[0]
        support_note_ids.add(int(note["noteId"]))
        if not support_tags(row).issubset(note_tags(note)):
            errors.append(f"Support {row['Word']}: missing support tags")
        for card in cards_by_note.get(int(note["noteId"]), []):
            support_cards += 1
            if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) == -1:
                support_unseen_suspended += 1

    schedule_mismatches: list[int] = []
    if reviewed_schedule_before is not None:
        cards_by_id = {int(card["cardId"]): card for card in state["cards"]}
        for card_id, before in reviewed_schedule_before.items():
            current = cards_by_id.get(card_id)
            if current is None or card_schedule(current) != before:
                schedule_mismatches.append(card_id)
        if schedule_mismatches:
            errors.append(f"Reviewed card schedules changed for {len(schedule_mismatches)} cards")

    protected_field_mismatches: list[int] = []
    source_provenance_mismatches: list[int] = []
    removed_existing_tags: list[int] = []
    if protected_note_before is not None:
        notes_by_id = {int(note["noteId"]): note for note in state["notes"]}
        for note_id, before in protected_note_before.items():
            current = notes_by_id.get(note_id)
            if current is None:
                protected_field_mismatches.append(note_id)
                continue
            if any(
                note_field(current, field) != before[field]
                for field in ("Word", "Production Card", "Frequency Rank")
            ):
                protected_field_mismatches.append(note_id)
            old_source = clean(before["Source"])
            if old_source and old_source not in note_field(current, "Source"):
                source_provenance_mismatches.append(note_id)
            if not set(before["tags"]).issubset(note_tags(current)):
                removed_existing_tags.append(note_id)
        if protected_field_mismatches:
            errors.append(f"Protected note fields changed for {len(protected_field_mismatches)} notes")
        if source_provenance_mismatches:
            errors.append(f"Existing Source provenance was lost for {len(source_provenance_mismatches)} notes")
        if removed_existing_tags:
            errors.append(f"Existing tags were removed from {len(removed_existing_tags)} notes")

    priority_ok = priority_is_correct(rows, notes_by_word, cards_by_note, state["cards"])
    if not priority_ok:
        errors.append("Unseen pilot cards are not ahead of the active generic new-card queue in pilot order")

    if word_cards != 60:
        errors.append(f"Expected 60 Word Recognition cards, found {word_cards}")
    if sentence_cards != 60:
        errors.append(f"Expected 60 Sentence Recognition cards, found {sentence_cards}")
    if production_cards:
        errors.append(f"Expected 0 production cards, found {production_cards}")
    if exact_example_round_trips != 60:
        errors.append(f"Expected 60 exact example round-trips, found {exact_example_round_trips}")
    if rendered_preview_mismatches:
        errors.append(f"Rendered card preview mismatches: {rendered_preview_mismatches[:10]}")

    return {
        "status": "PASS" if not errors else "ERROR",
        "target_notes": len(target_note_ids),
        "word_recognition_cards": word_cards,
        "sentence_recognition_cards": sentence_cards,
        "production_cards": production_cards,
        "unseen_pilot_cards_active": unseen_active,
        "reviewed_pilot_cards_preserved": reviewed_cards,
        "exact_example_round_trips": exact_example_round_trips,
        "rendered_card_preview_checks": rendered_preview_checks,
        "rendered_card_preview_mismatch_count": len(rendered_preview_mismatches),
        "pilot_priority_correct": priority_ok,
        "reviewed_schedule_mismatch_count": len(schedule_mismatches),
        "protected_note_field_mismatch_count": len(protected_field_mismatches),
        "source_provenance_mismatch_count": len(source_provenance_mismatches),
        "notes_with_removed_existing_tags": len(removed_existing_tags),
        "support_notes": len(support_note_ids),
        "support_cards": support_cards,
        "support_unseen_cards_suspended": support_unseen_suspended,
        "duplicate_conflicts": {
            row["Word"]: len(notes_by_word.get(row["Word"], []))
            for row in rows
            if len(notes_by_word.get(row["Word"], [])) != 1
        },
        "unresolved_pronunciation_conflicts": [],
        "unresolved_sense_conflicts": [],
        "errors": errors,
    }


def apply_pilot(
    *,
    manifest_path: Path,
    backup_path: Path,
    call_anki: Callable[[str, dict[str, Any] | None], Any],
) -> dict[str, Any]:
    plan, internal = build_plan(manifest_path=manifest_path, call_anki=call_anki)
    target_words = {row["Word"] for row in internal["rows"]}
    support_words = {row["Word"] for row in SUPPORT_ROWS}
    backup_already_existed = backup_path.exists()
    if not backup_already_existed:
        write_backup(
            backup_path,
            internal["state"]["notes"],
            internal["cards_by_note"],
            target_words,
            support_words,
        )
    original_reviewed_schedule = reviewed_schedule_from_backup(backup_path)

    update_notes(internal["updates"], call_anki)
    added_target_ids = add_notes(internal["target_additions"], call_anki)
    added_support_ids = add_notes(internal["support_additions"], call_anki)

    state = load_live_state(call_anki)
    notes_by_word = group_notes(state["notes"])
    cards_by_note = group_cards(state["cards"])
    target_note_ids = {
        int(notes_by_word[row["Word"]][0]["noteId"])
        for row in internal["rows"]
        if len(notes_by_word.get(row["Word"], [])) == 1
    }
    support_note_ids = {
        int(notes_by_word[row["Word"]][0]["noteId"])
        for row in SUPPORT_ROWS
        if len(notes_by_word.get(row["Word"], [])) == 1
    }
    target_cards = [card for card in state["cards"] if int(card["note"]) in target_note_ids]
    support_cards = [card for card in state["cards"] if int(card["note"]) in support_note_ids]

    target_to_unsuspend = [
        int(card["cardId"])
        for card in target_cards
        if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) == -1
    ]
    mutate_card_batch("unsuspend", target_to_unsuspend, call_anki)
    support_to_suspend = [
        int(card["cardId"])
        for card in support_cards
        if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) >= 0
    ]
    mutate_card_batch("suspend", support_to_suspend, call_anki)

    state = load_live_state(call_anki)
    notes_by_word = group_notes(state["notes"])
    cards_by_note = group_cards(state["cards"])
    reposition_ids = [] if plan["priority_already_correct"] else priority_card_ids(
        internal["rows"],
        notes_by_word,
        cards_by_note,
        include_suspended=False,
    )
    queue_order_method = "already-correct" if not reposition_ids else "none"
    reposition_warning = ""
    if reposition_ids:
        try:
            call_anki(
                "reposition",
                {
                    "cards": reposition_ids,
                    "startingFrom": 0,
                    "step": 1,
                    "randomize": False,
                    "shiftPosition": True,
                },
            )
            queue_order_method = "reposition"
        except FirstFrostPilotError as exc:
            set_new_card_due_order(reposition_ids, call_anki)
            queue_order_method = "setSpecificValueOfCard:due"
            reposition_warning = f"reposition unsupported; used due-field fallback ({exc})"

    verification = verify_live(
        manifest_path=manifest_path,
        call_anki=call_anki,
        reviewed_schedule_before=original_reviewed_schedule or internal["reviewed_schedule_before"],
        protected_note_before=protected_note_state_from_backup(backup_path),
    )
    if verification["status"] != "PASS":
        raise FirstFrostPilotError("Post-apply verification failed: " + "; ".join(verification["errors"]))

    baseline = backup_baseline_stats(backup_path, internal["rows"])
    cumulative_new_target_notes = verification["target_notes"] - baseline["target_notes"]
    cumulative_new_target_cards = (
        verification["word_recognition_cards"]
        + verification["sentence_recognition_cards"]
        - baseline["target_cards"]
    )
    cumulative_new_support_notes = verification["support_notes"] - baseline["support_notes"]
    cumulative_new_support_cards = verification["support_cards"] - baseline["support_cards"]

    return {
        "status": "PASS",
        "mode": "apply",
        "backup": str(backup_path),
        "backup_reused_from_initial_apply": backup_already_existed,
        "reused_target_notes": baseline["target_notes"],
        "updated_reused_target_notes": baseline["target_notes_needing_update"],
        "new_target_notes": cumulative_new_target_notes,
        "reused_target_cards": baseline["target_cards"],
        "new_target_cards": cumulative_new_target_cards,
        "target_cards_unsuspended": baseline["target_unseen_suspended_cards"],
        "target_cards_created_accessible": cumulative_new_target_cards,
        "target_cards_newly_accessible": (
            baseline["target_unseen_suspended_cards"] + cumulative_new_target_cards
        ),
        "target_cards_repositioned": len(reposition_ids),
        "target_cards_confirmed_in_priority_order": verification["unseen_pilot_cards_active"],
        "queue_order_method": queue_order_method,
        "queue_order_warning": reposition_warning,
        "new_support_notes": cumulative_new_support_notes,
        "new_support_cards": cumulative_new_support_cards,
        "support_cards_suspended": verification["support_unseen_cards_suspended"],
        "this_run": {
            "updated_notes": len(internal["updates"]),
            "added_target_notes": len(added_target_ids),
            "added_support_notes": len(added_support_ids),
            "unsuspended_target_cards": len(target_to_unsuspend),
            "suspended_support_cards": len(support_to_suspend),
            "repositioned_target_cards": len(reposition_ids),
        },
        "unresolved_duplicate_conflicts": [],
        "unresolved_pronunciation_conflicts": [],
        "unresolved_sense_conflicts": [],
        "verification": verification,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run, apply, or verify the target-scoped First Frost reading-vocabulary pilot."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Back up and apply the preflighted pilot changes.")
    mode.add_argument("--verify-only", action="store_true", help="Verify the already-applied live pilot.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--backup", type=Path, default=BACKUP_PATH)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--anki-connect-url", default=ANKI_CONNECT_URL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    def call_anki(action: str, params: dict[str, Any] | None = None) -> Any:
        return anki_request(action, params, url=args.anki_connect_url)

    try:
        if args.verify_only:
            report = verify_live(
                manifest_path=args.manifest,
                call_anki=call_anki,
                reviewed_schedule_before=reviewed_schedule_from_backup(args.backup),
                protected_note_before=protected_note_state_from_backup(args.backup),
            )
            default_report = REPORT_DIR / "first_frost_pilot_verification.json"
        elif args.apply:
            report = apply_pilot(
                manifest_path=args.manifest,
                backup_path=args.backup,
                call_anki=call_anki,
            )
            default_report = REPORT_DIR / "first_frost_pilot_apply_report.json"
        else:
            report, _ = build_plan(manifest_path=args.manifest, call_anki=call_anki)
            default_report = REPORT_DIR / "first_frost_pilot_dry_run.json"
    except (FirstFrostPilotError, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    write_report(args.report or default_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
