from __future__ import annotations

import copy
import re
from typing import Any


MUTATING_ACTIONS = {
    "createDeck",
    "createModel",
    "updateModelTemplates",
    "updateModelStyling",
    "cloneDeckConfigId",
    "setDeckConfigId",
    "saveDeckConfig",
    "addNote",
    "addNotes",
    "updateNoteFields",
    "addTags",
    "removeTags",
    "reposition",
    "setSpecificValueOfCard",
    "multi",
}


class FakeAnki:
    def __init__(self) -> None:
        self.mutation_calls: list[tuple[str, dict[str, Any]]] = []
        self.decks = {"Default": 1, "Hindi": 2}
        self.deck_config_ids = {"Default": 1, "Hindi": 2}
        self.configs = {
            1: {
                "id": 1,
                "name": "Default",
                "mod": 100,
                "usn": 5,
                "new": {"perDay": 20, "order": 1, "delays": [1.0, 10.0]},
                "rev": {"perDay": 200, "bury": False},
                "lapse": {"delays": [10.0], "leechFails": 8},
                "newGatherPriority": 0,
                "newSortOrder": 0,
                "newMix": 0,
                "fsrsWeights": [1.0, 2.0],
            },
            2: {
                "id": 2,
                "name": "Hindi - 5 new cards",
                "mod": 200,
                "usn": 6,
                "new": {"perDay": 5, "order": 1, "delays": [1.0, 10.0]},
                "rev": {"perDay": 180, "bury": True},
                "lapse": {"delays": [10.0], "leechFails": 7},
                "newGatherPriority": 0,
                "newSortOrder": 1,
                "newMix": 0,
                "fsrsWeights": [1.2, 2.2],
            }
        }
        self.models = {
            "Chinese Vocabulary": {
                "fields": ["Word", "Pinyin"],
                "templates": {
                    "Word Recognition": {
                        "Front": "<div>{{Word}}</div>",
                        "Back": "{{FrontSide}} {{Pinyin}}",
                    }
                },
                "css": ".card { color: black; }",
            },
            "Hindi Vocabulary": {
                "fields": ["Word", "Pronunciation", "Meaning"],
                "templates": {
                    "Word Recognition": {
                        "Front": "<div>{{Word}}</div>",
                        "Back": "{{FrontSide}} {{Pronunciation}}",
                    },
                    "Sentence Recognition": {
                        "Front": "<div>{{Word}}</div>",
                        "Back": "{{FrontSide}} {{Meaning}}",
                    },
                },
                "css": ".card { color: #222; }",
            }
        }
        self.notes: dict[int, dict[str, Any]] = {
            10: {
                "noteId": 10,
                "modelName": "Chinese Vocabulary",
                "fields": {
                    "Word": {"value": "你好", "order": 0},
                    "Pinyin": {"value": "nǐ hǎo", "order": 1},
                },
                "tags": ["chinese_vocab"],
                "cards": [20],
                "deckName": "Default",
            },
            11: {
                "noteId": 11,
                "modelName": "Hindi Vocabulary",
                "fields": {
                    "Word": {"value": "नमस्ते", "order": 0},
                    "Pronunciation": {"value": "namaste", "order": 1},
                    "Meaning": {"value": "hello", "order": 2},
                },
                "tags": ["hindi"],
                "cards": [21],
                "deckName": "Hindi",
            }
        }
        self.cards: dict[int, dict[str, Any]] = {
            20: {
                "cardId": 20,
                "note": 10,
                "ord": 0,
                "queue": 0,
                "type": 0,
                "due": 1,
                "interval": 0,
                "factor": 2500,
                "reps": 0,
                "lapses": 0,
                "left": 0,
                "deckName": "Default",
            },
            21: {
                "cardId": 21,
                "note": 11,
                "ord": 0,
                "queue": 0,
                "type": 0,
                "due": 1,
                "interval": 0,
                "factor": 2500,
                "reps": 0,
                "lapses": 0,
                "left": 0,
                "deckName": "Hindi",
            }
        }
        self.next_deck_id = 3
        self.next_config_id = 3
        self.next_note_id = 1000
        self.next_card_id = 2000

    def _record(self, action: str, params: dict[str, Any]) -> None:
        if action in MUTATING_ACTIONS:
            self.mutation_calls.append((action, copy.deepcopy(params)))

    def _notes_for_query(self, query: str) -> list[int]:
        deck_match = re.search(r"deck:([^\s]+)", query)
        if deck_match:
            deck = deck_match.group(1).strip('"')
            return sorted(
                note_id
                for note_id, note in self.notes.items()
                if note["deckName"] == deck or note["deckName"].startswith(f"{deck}::")
            )
        note_match = re.search(r'note:"([^"]+)"', query)
        if note_match:
            model = note_match.group(1)
            return sorted(note_id for note_id, note in self.notes.items() if note["modelName"] == model)
        return []

    def _cards_for_query(self, query: str) -> list[int]:
        deck_match = re.search(r"deck:([^\s]+)", query)
        if not deck_match:
            return []
        deck = deck_match.group(1).strip('"')
        return sorted(
            card_id
            for card_id, card in self.cards.items()
            if card["deckName"] == deck or card["deckName"].startswith(f"{deck}::")
        )

    def _add_note(self, note: dict[str, Any]) -> int | None:
        word = str(note["fields"].get("Word", ""))
        if any(
            existing["modelName"] == note["modelName"]
            and existing["deckName"] == note["deckName"]
            and existing["fields"].get("Word", {}).get("value") == word
            for existing in self.notes.values()
        ):
            return None
        note_id = self.next_note_id
        self.next_note_id += 1
        model = self.models[note["modelName"]]
        fields = {
            field: {"value": str(note["fields"].get(field, "")), "order": index}
            for index, field in enumerate(model["fields"])
        }
        card_ids = []
        existing_due = [card["due"] for card in self.cards.values() if card["deckName"] == note["deckName"]]
        due = max(existing_due, default=0) + 1
        for ord_value, _template_name in enumerate(model["templates"]):
            card_id = self.next_card_id
            self.next_card_id += 1
            self.cards[card_id] = {
                "cardId": card_id,
                "note": note_id,
                "ord": ord_value,
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

    def add_incompatible_spanish_note(self) -> None:
        self.decks["Spanish"] = self.next_deck_id
        self.next_deck_id += 1
        self.deck_config_ids["Spanish"] = 1
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
            "deckName": "Spanish",
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
            "deckName": "Spanish",
        }

    def __call__(self, action: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        self._record(action, params)
        if action == "version":
            return 6
        if action == "deckNamesAndIds":
            return copy.deepcopy(self.decks)
        if action == "modelNames":
            return list(self.models)
        if action == "modelFieldNames":
            return list(self.models[params["modelName"]]["fields"])
        if action == "modelTemplates":
            return copy.deepcopy(self.models[params["modelName"]]["templates"])
        if action == "modelStyling":
            return {"css": self.models[params["modelName"]]["css"]}
        if action == "findNotes":
            return self._notes_for_query(params["query"])
        if action == "notesInfo":
            return [copy.deepcopy(self.notes[int(note_id)]) for note_id in params["notes"]]
        if action == "findCards":
            return self._cards_for_query(params["query"])
        if action == "cardsInfo":
            return [copy.deepcopy(self.cards[int(card_id)]) for card_id in params["cards"]]
        if action == "getDeckConfig":
            deck = params["deck"]
            if deck not in self.deck_config_ids:
                return False
            return copy.deepcopy(self.configs[self.deck_config_ids[deck]])
        if action == "createDeck":
            deck = params["deck"]
            if deck not in self.decks:
                self.decks[deck] = self.next_deck_id
                self.next_deck_id += 1
                self.deck_config_ids[deck] = 1
            return self.decks[deck]
        if action == "createModel":
            self.models[params["modelName"]] = {
                "fields": list(params["inOrderFields"]),
                "templates": {
                    template["Name"]: {"Front": template["Front"], "Back": template["Back"]}
                    for template in params["cardTemplates"]
                },
                "css": params.get("css", ""),
            }
            return True
        if action == "updateModelTemplates":
            model = params["model"]
            self.models[model["name"]]["templates"] = copy.deepcopy(model["templates"])
            return None
        if action == "updateModelStyling":
            model = params["model"]
            self.models[model["name"]]["css"] = model["css"]
            return None
        if action == "cloneDeckConfigId":
            for config_id, config in self.configs.items():
                if config["name"] == params["name"]:
                    return config_id
            config_id = self.next_config_id
            self.next_config_id += 1
            config = copy.deepcopy(self.configs[int(params.get("cloneFrom", 1))])
            config["id"] = config_id
            config["name"] = params["name"]
            self.configs[config_id] = config
            return config_id
        if action == "setDeckConfigId":
            config_id = int(params["configId"])
            if config_id not in self.configs:
                return False
            for deck in params["decks"]:
                if deck not in self.decks:
                    return False
                self.deck_config_ids[deck] = config_id
            return True
        if action == "saveDeckConfig":
            config = copy.deepcopy(params["config"])
            config_id = int(config["id"])
            if config_id not in self.configs:
                return False
            config["id"] = config_id
            self.configs[config_id] = config
            return True
        if action == "addNotes":
            return [self._add_note(note) for note in params["notes"]]
        if action == "addNote":
            return self._add_note(params["note"])
        if action == "updateNoteFields":
            note = params["note"]
            stored = self.notes[int(note["id"])]
            for field, value in note["fields"].items():
                stored["fields"][field]["value"] = str(value)
            return None
        if action == "addTags":
            tags = str(params["tags"]).split()
            for note_id in params["notes"]:
                self.notes[int(note_id)]["tags"] = sorted(
                    set(self.notes[int(note_id)]["tags"]) | set(tags)
                )
            return None
        if action == "removeTags":
            tags = set(str(params["tags"]).split())
            for note_id in params["notes"]:
                self.notes[int(note_id)]["tags"] = sorted(
                    set(self.notes[int(note_id)]["tags"]) - tags
                )
            return None
        if action == "multi":
            results = []
            for nested in params["actions"]:
                try:
                    results.append(
                        {"result": self(nested["action"], nested.get("params")), "error": None}
                    )
                except Exception as exc:  # pragma: no cover - test helper failure path
                    results.append({"result": None, "error": str(exc)})
            return results
        if action == "reposition":
            for due, card_id in enumerate(
                params["cards"], start=int(params.get("startingFrom", 1))
            ):
                self.cards[int(card_id)]["due"] = due
            return True
        if action == "setSpecificValueOfCard":
            card = self.cards[int(params["card"])]
            for key, value in zip(params["keys"], params["newValues"]):
                card[key] = value
            return [True]
        raise AssertionError(f"unsupported fake Anki action: {action}")
