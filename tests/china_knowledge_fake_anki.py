from __future__ import annotations

import copy
import re
from typing import Any

from tests.spanish_fake_anki import FakeAnki as BaseFakeAnki


class FakeAnki(BaseFakeAnki):
    """In-memory AnkiConnect surface with three protected language decks."""

    def __init__(self) -> None:
        super().__init__()
        self.decks["Spanish"] = 3
        self.deck_config_ids["Spanish"] = 3
        self.configs[3] = {
            "id": 3,
            "name": "Spanish - 5 new cards",
            "mod": 300,
            "usn": 7,
            "new": {"perDay": 5, "order": 1, "delays": [1.0, 10.0]},
            "rev": {"perDay": 170, "bury": True},
            "lapse": {"delays": [10.0], "leechFails": 7},
            "newGatherPriority": 0,
            "newSortOrder": 1,
            "newMix": 0,
            "fsrsWeights": [1.3, 2.3],
        }
        self.models["Spanish Vocabulary"] = {
            "fields": ["Word", "IPA", "Meaning"],
            "templates": {
                "Word Recognition": {
                    "Front": '<div lang="es">{{Word}}</div>',
                    "Back": "{{FrontSide}} {{IPA}} {{Meaning}}",
                }
            },
            "css": ".card { color: #333; }",
        }
        self.notes[12] = {
            "noteId": 12,
            "modelName": "Spanish Vocabulary",
            "fields": {
                "Word": {"value": "hola", "order": 0},
                "IPA": {"value": "/ˈola/", "order": 1},
                "Meaning": {"value": "hello", "order": 2},
            },
            "tags": ["spanish_vocab"],
            "cards": [22],
            "deckName": "Spanish",
        }
        self.cards[22] = {
            "cardId": 22,
            "note": 12,
            "ord": 0,
            "queue": 0,
            "type": 0,
            "due": 1,
            "interval": 0,
            "factor": 2500,
            "reps": 0,
            "lapses": 0,
            "left": 0,
            "deckName": "Spanish",
        }
        self.next_deck_id = 4
        self.next_config_id = 4

    @staticmethod
    def _deck_from_query(query: str) -> str | None:
        quoted = re.search(r'deck:"([^"]+)"', query)
        if quoted:
            return quoted.group(1)
        plain = re.search(r"deck:([^\s]+)", query)
        return plain.group(1) if plain else None

    def _notes_for_query(self, query: str) -> list[int]:
        deck = self._deck_from_query(query)
        if deck is not None:
            return sorted(
                note_id
                for note_id, note in self.notes.items()
                if note["deckName"] == deck or note["deckName"].startswith(f"{deck}::")
            )
        note_match = re.search(r'note:"([^"]+)"', query)
        if note_match:
            model = note_match.group(1)
            return sorted(
                note_id for note_id, note in self.notes.items() if note["modelName"] == model
            )
        return []

    def _cards_for_query(self, query: str) -> list[int]:
        deck = self._deck_from_query(query)
        if deck is None:
            return []
        return sorted(
            card_id
            for card_id, card in self.cards.items()
            if card["deckName"] == deck or card["deckName"].startswith(f"{deck}::")
        )

    def _add_note(self, note: dict[str, Any]) -> int | None:
        model = self.models[note["modelName"]]
        identity_field = "Knowledge ID" if "Knowledge ID" in model["fields"] else model["fields"][0]
        identity = str(note["fields"].get(identity_field, ""))
        if any(
            existing["modelName"] == note["modelName"]
            and existing["deckName"] == note["deckName"]
            and existing["fields"].get(identity_field, {}).get("value") == identity
            for existing in self.notes.values()
        ):
            return None
        note_id = self.next_note_id
        self.next_note_id += 1
        fields = {
            field: {"value": str(note["fields"].get(field, "")), "order": index}
            for index, field in enumerate(model["fields"])
        }
        existing_due = [
            card["due"] for card in self.cards.values() if card["deckName"] == note["deckName"]
        ]
        due = max(existing_due, default=0) + 1
        card_ids: list[int] = []
        for ordinal, _template in enumerate(model["templates"]):
            card_id = self.next_card_id
            self.next_card_id += 1
            self.cards[card_id] = {
                "cardId": card_id,
                "note": note_id,
                "ord": ordinal,
                "queue": 0,
                "type": 0,
                "due": due,
                "interval": 0,
                "factor": 2500,
                "reps": 0,
                "lapses": 0,
                "left": 0,
                "deckName": note["deckName"],
            }
            card_ids.append(card_id)
        self.notes[note_id] = {
            "noteId": note_id,
            "modelName": note["modelName"],
            "fields": fields,
            "tags": sorted(set(note.get("tags", []))),
            "cards": card_ids,
            "deckName": note["deckName"],
        }
        return note_id

    def add_incompatible_china_note(self) -> None:
        self.decks["China Knowledge"] = self.next_deck_id
        self.next_deck_id += 1
        self.deck_config_ids["China Knowledge"] = 1
        self.models["Basic"] = {
            "fields": ["Front", "Back"],
            "templates": {"Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}},
            "css": "",
        }
        note_id = self.next_note_id
        self.next_note_id += 1
        card_id = self.next_card_id
        self.next_card_id += 1
        self.notes[note_id] = {
            "noteId": note_id,
            "modelName": "Basic",
            "fields": {
                "Front": {"value": "unrelated", "order": 0},
                "Back": {"value": "content", "order": 1},
            },
            "tags": [],
            "cards": [card_id],
            "deckName": "China Knowledge",
        }
        self.cards[card_id] = {
            "cardId": card_id,
            "note": note_id,
            "ord": 0,
            "queue": 0,
            "type": 0,
            "due": 1,
            "interval": 0,
            "factor": 2500,
            "reps": 0,
            "lapses": 0,
            "left": 0,
            "deckName": "China Knowledge",
        }

    def snapshot_protected(self) -> dict[str, Any]:
        return {
            "decks": {name: self.decks[name] for name in ("Default", "Hindi", "Spanish")},
            "configs": copy.deepcopy({key: self.configs[key] for key in (1, 2, 3)}),
            "models": copy.deepcopy(
                {
                    key: self.models[key]
                    for key in ("Chinese Vocabulary", "Hindi Vocabulary", "Spanish Vocabulary")
                }
            ),
            "notes": copy.deepcopy({key: self.notes[key] for key in (10, 11, 12)}),
            "cards": copy.deepcopy({key: self.cards[key] for key in (20, 21, 22)}),
        }
