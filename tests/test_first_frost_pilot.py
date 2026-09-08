from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from apply_sentence_example_updates import source_fields_for_note
from sentence_example_overrides import SENTENCE_EXAMPLE_OVERRIDES, SENTENCE_PINYIN_OVERRIDES
from scripts.anki_priority import priority_from_tags, priority_new_card_ids
from scripts.first_frost.content import MANIFEST_PATH, load_manifest
from scripts.first_frost.setup_first_frost_pilot import (
    REQUIRED_FIELDS,
    SUPPORT_ROWS,
    FirstFrostPilotError,
    apply_pilot,
    build_plan,
    desired_pilot_fields,
    merge_source,
)
from scripts.first_frost.validate_first_frost_pilot import validate_manifest


class FakeAnki:
    def __init__(self, *, duplicate_word: str | None = None, reviewed_word: str | None = None) -> None:
        self.notes: dict[int, dict[str, Any]] = {}
        self.cards: dict[int, dict[str, Any]] = {}
        self.next_note_id = 1000
        self.next_card_id = 5000
        self.mutations: list[str] = []
        if duplicate_word:
            self._seed_note(duplicate_word)
            self._seed_note(duplicate_word)
        if reviewed_word:
            note_id = self._seed_note(reviewed_word)
            for card_id in self.notes[note_id]["cards"]:
                self.cards[card_id].update(
                    {
                        "type": 2,
                        "queue": 2,
                        "due": 100 + self.cards[card_id]["ord"],
                        "interval": 9,
                        "factor": 2500,
                        "reps": 4,
                    }
                )

    def _seed_note(self, word: str) -> int:
        note_id = self.next_note_id
        self.next_note_id += 1
        fields = {field: {"value": ""} for field in REQUIRED_FIELDS}
        fields["Word"] = {"value": word}
        fields["Pinyin"] = {"value": "old"}
        fields["Meaning"] = {"value": "old"}
        fields["Source"] = {"value": "existing-source"}
        fields["Frequency Rank"] = {"value": "912"}
        fields["Sentence Card"] = {"value": "yes"}
        card_ids: list[int] = []
        for card_ord in (0, 1):
            card_id = self.next_card_id
            self.next_card_id += 1
            card_ids.append(card_id)
            self.cards[card_id] = self._card(card_id, note_id, card_ord)
        self.notes[note_id] = {
            "noteId": note_id,
            "modelName": "Chinese Vocabulary",
            "fields": fields,
            "tags": ["existing-tag"],
            "cards": card_ids,
        }
        return note_id

    @staticmethod
    def _card(card_id: int, note_id: int, card_ord: int) -> dict[str, Any]:
        return {
            "cardId": card_id,
            "note": note_id,
            "ord": card_ord,
            "type": 0,
            "queue": 0,
            "due": card_id,
            "interval": 0,
            "factor": 0,
            "reps": 0,
            "lapses": 0,
            "left": 0,
            "odue": 0,
            "odid": 0,
            "deckName": "Default",
        }

    def __call__(self, action: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        if action == "modelNames":
            return ["Chinese Vocabulary"]
        if action == "modelFieldNames":
            return list(REQUIRED_FIELDS)
        if action == "modelTemplates":
            return {"Word Recognition": {}, "Sentence Recognition": {}}
        if action == "findNotes":
            return sorted(self.notes)
        if action == "notesInfo":
            return [copy.deepcopy(self.notes[int(note_id)]) for note_id in params["notes"]]
        if action == "cardsInfo":
            rendered = []
            for card_id in params["cards"]:
                card = copy.deepcopy(self.cards[int(card_id)])
                fields = self.notes[int(card["note"])]["fields"]
                value = lambda name: fields.get(name, {}).get("value", "")
                if int(card["ord"]) == 0:
                    card["question"] = value("Word")
                    card["answer"] = value("Pinyin") + value("Meaning")
                else:
                    card["question"] = value("Example")
                    card["answer"] = value("Example Pinyin") + value("Example Meaning")
                rendered.append(card)
            return rendered
        if action == "canAddNotes":
            existing = {note["fields"]["Word"]["value"] for note in self.notes.values()}
            return [note["fields"]["Word"] not in existing for note in params["notes"]]

        self.mutations.append(action)
        if action == "updateNoteFields":
            note_data = params["note"]
            note = self.notes[int(note_data["id"])]
            for name, value in note_data["fields"].items():
                note["fields"][name] = {"value": value}
            return None
        if action == "addTags":
            additions = params["tags"].split()
            for note_id in params["notes"]:
                self.notes[int(note_id)]["tags"] = sorted(
                    set(self.notes[int(note_id)]["tags"]) | set(additions)
                )
            return None
        if action == "addNotes":
            added: list[int] = []
            for payload in params["notes"]:
                note_id = self.next_note_id
                self.next_note_id += 1
                card_ids: list[int] = []
                for card_ord in (0, 1):
                    card_id = self.next_card_id
                    self.next_card_id += 1
                    card_ids.append(card_id)
                    self.cards[card_id] = self._card(card_id, note_id, card_ord)
                self.notes[note_id] = {
                    "noteId": note_id,
                    "modelName": payload["modelName"],
                    "fields": {
                        name: {"value": value}
                        for name, value in payload["fields"].items()
                    },
                    "tags": list(payload["tags"]),
                    "cards": card_ids,
                }
                added.append(note_id)
            return added
        if action in {"suspend", "unsuspend"}:
            for card_id in params["cards"]:
                self.cards[int(card_id)]["queue"] = -1 if action == "suspend" else 0
            return None
        if action == "reposition":
            selected = [int(value) for value in params["cards"]]
            selected_set = set(selected)
            shift = len(selected)
            for card_id, card in self.cards.items():
                if card_id not in selected_set and card["type"] == 0 and card["queue"] >= 0:
                    card["due"] += shift
            for index, card_id in enumerate(selected):
                self.cards[card_id]["due"] = int(params["startingFrom"]) + index
            return None
        if action == "multi":
            results = []
            for nested in params["actions"]:
                if nested["action"] != "setSpecificValueOfCard":
                    raise AssertionError(f"Unexpected nested action: {nested['action']}")
                nested_params = nested["params"]
                card = self.cards[int(nested_params["card"])]
                for key, value in zip(nested_params["keys"], nested_params["newValues"]):
                    card[key] = value
                results.append({"result": None, "error": None})
            return results
        raise AssertionError(f"Unexpected Anki action: {action}")


def test_reviewed_manifest_is_complete_and_unique() -> None:
    report = validate_manifest(MANIFEST_PATH)
    assert report["status"] == "PASS"
    assert report["row_count"] == 60
    assert report["unique_word_count"] == 60


def test_all_reviewed_examples_are_installed_as_rebuild_overrides() -> None:
    for row in load_manifest():
        assert SENTENCE_EXAMPLE_OVERRIDES[row["Word"]] == (
            row["Example"],
            row["Example Meaning"],
        )
        assert SENTENCE_PINYIN_OVERRIDES[row["Example"]] == row["Example Pinyin"]


def test_normal_example_apply_preserves_pilot_provenance() -> None:
    row = load_manifest()[0]
    note = {
        "fields": {
            "Word": {"value": row["Word"]},
            "Source": {"value": "existing-source"},
        }
    }
    source = {
        "Example": row["Example"],
        "Example Pinyin": row["Example Pinyin"],
        "Example Meaning": row["Example Meaning"],
        "Source": "chinese cedict manual",
    }
    fields = source_fields_for_note(note, source)
    assert fields["Source"] == f"existing-source | {row['Source']}"


def test_source_merge_is_additive_and_idempotent() -> None:
    assert merge_source("existing", "pilot") == "existing | pilot"
    assert merge_source("existing | pilot", "pilot") == "existing | pilot"


def test_sheng_keeps_reviewed_usage_and_valid_second_reading() -> None:
    sheng = next(row for row in load_manifest() if row["Word"] == "盛")
    fields = desired_pilot_fields(sheng)
    assert fields["Pinyin"] == "chéng; shèng"
    assert "serve" in fields["Meaning"]
    assert "flourishing" in fields["Meaning"]
    assert "盛了一碗汤" in fields["Example"]


def test_persistent_priority_tags_only_select_active_unseen_cards() -> None:
    notes = [
        {"noteId": 1, "tags": ["pilot_first_frost_priority_010"]},
        {"noteId": 2, "tags": ["pilot_first_frost_priority_002"]},
        {"noteId": 3, "tags": ["unrelated"]},
    ]
    cards = {
        1: [
            {"cardId": 11, "ord": 1, "type": 0, "queue": 0},
            {"cardId": 10, "ord": 0, "type": 0, "queue": 0},
        ],
        2: [
            {"cardId": 20, "ord": 0, "type": 0, "queue": 0},
            {"cardId": 21, "ord": 1, "type": 2, "queue": 2},
            {"cardId": 22, "ord": 1, "type": 0, "queue": -1},
        ],
        3: [{"cardId": 30, "ord": 0, "type": 0, "queue": 0}],
    }
    assert priority_from_tags(notes[1]["tags"]) == 2
    assert priority_new_card_ids(notes, cards, active_card_ords={0, 1}) == [20, 10, 11]


def test_dry_run_is_read_only_and_plans_60_plus_support() -> None:
    fake = FakeAnki()
    plan, _ = build_plan(manifest_path=MANIFEST_PATH, call_anki=fake)
    assert fake.mutations == []
    assert plan["target_notes_to_create"] == 60
    assert plan["target_cards_to_create"] == 120
    assert plan["support_notes_to_create"] == len(SUPPORT_ROWS)


def test_model_wide_duplicate_conflict_stops_before_mutation() -> None:
    fake = FakeAnki(duplicate_word="舍不得")
    with pytest.raises(FirstFrostPilotError, match="Duplicate live notes"):
        build_plan(manifest_path=MANIFEST_PATH, call_anki=fake)
    assert fake.mutations == []


def test_apply_preserves_review_schedule_and_verifies_cohort(tmp_path: Path) -> None:
    fake = FakeAnki(reviewed_word="原谅")
    before = {
        card_id: copy.deepcopy(card)
        for card_id, card in fake.cards.items()
        if card["note"] == 1000
    }
    report = apply_pilot(
        manifest_path=MANIFEST_PATH,
        backup_path=tmp_path / "backup.tsv",
        call_anki=fake,
    )
    assert report["status"] == "PASS"
    assert report["reused_target_notes"] == 1
    assert report["new_target_notes"] == 59
    assert report["verification"]["word_recognition_cards"] == 60
    assert report["verification"]["sentence_recognition_cards"] == 60
    assert report["verification"]["production_cards"] == 0
    assert report["verification"]["support_unseen_cards_suspended"] == 6
    for card_id, old in before.items():
        for key in ("type", "queue", "due", "interval", "factor", "reps"):
            assert fake.cards[card_id][key] == old[key]
