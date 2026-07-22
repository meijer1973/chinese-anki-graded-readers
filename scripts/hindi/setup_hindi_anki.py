from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hindi.anki_client import (  # noqa: E402
    ANKI_CONNECT_URL,
    AnkiClient,
    AnkiConnectError,
    MutationGuard,
    MutationSafetyError,
    Transport,
)
from scripts.hindi.validate_hindi_core_100 import (  # noqa: E402
    DEFAULT_REPORT as DATA_VALIDATION_REPORT,
    DEFAULT_SOURCES,
    DEFAULT_TSV,
    load_rows,
    validate_or_raise,
)


DECK_NAME = "Hindi"
MODEL_NAME = "Hindi Vocabulary"
OPTIONS_PRESET_NAME = "Hindi - 5 new cards"
WORD_TEMPLATE_NAME = "Word Recognition"
SENTENCE_TEMPLATE_NAME = "Sentence Recognition"
STANDARD_TAGS = {"hindi", "hindi::core_100"}

CHINESE_DECK_NAME = "Default"
CHINESE_DECK_QUERY = "deck:Default"
CHINESE_MODEL_NAME = "Chinese Vocabulary"

REPORTS_DIR = ROOT / "anki" / "hindi" / "reports"
DRY_RUN_REPORT = REPORTS_DIR / "hindi_anki_dry_run.json"
APPLY_REPORT = REPORTS_DIR / "hindi_anki_apply_report.json"
VERIFICATION_REPORT = REPORTS_DIR / "hindi_anki_verification.json"
CHINESE_SAFETY_BEFORE = REPORTS_DIR / "chinese_safety_before.json"
CHINESE_SAFETY_AFTER = REPORTS_DIR / "chinese_safety_after.json"
CHINESE_SAFETY_COMPARISON = REPORTS_DIR / "chinese_safety_comparison.json"
HINDI_BACKUP_TSV = REPORTS_DIR / "hindi_managed_notes_before_update.tsv"

FIELDS = [
    "Word",
    "Pronunciation",
    "Meaning",
    "Part of Speech",
    "Example",
    "Example Pronunciation",
    "Example Meaning",
    "Source",
    "Labels",
    "Frequency Rank",
    "Notes",
]

WORD_FRONT = """
<main class="hindi-card word-card">
  <div class="word" lang="hi">{{Word}}</div>
</main>
""".strip()

WORD_BACK = """
{{FrontSide}}
<hr id="answer">
<section class="answer-primary">
  <div class="pronunciation">{{Pronunciation}}</div>
  <div class="meaning">{{Meaning}}</div>
  {{#Part of Speech}}<div class="part-of-speech">{{Part of Speech}}</div>{{/Part of Speech}}
</section>
{{#Example}}
<section class="example-section">
  <div class="example" lang="hi">{{Example}}</div>
  <div class="example-pronunciation">{{Example Pronunciation}}</div>
  <div class="example-meaning">{{Example Meaning}}</div>
</section>
{{/Example}}
{{#Notes}}<div class="notes">{{Notes}}</div>{{/Notes}}
""".strip()

SENTENCE_FRONT = """
{{#Example}}
<main class="hindi-card sentence-card">
  <div class="example sentence-front" lang="hi">{{Example}}</div>
</main>
{{/Example}}
""".strip()

SENTENCE_BACK = """
{{FrontSide}}
<hr id="answer">
<section class="sentence-answer">
  <div class="example-pronunciation">{{Example Pronunciation}}</div>
  <div class="example-meaning">{{Example Meaning}}</div>
</section>
<section class="target-word-section">
  <div class="section-label">Target word</div>
  <div class="target-word" lang="hi">{{Word}}</div>
  <div class="pronunciation">{{Pronunciation}}</div>
  <div class="meaning">{{Meaning}}</div>
  {{#Part of Speech}}<div class="part-of-speech">{{Part of Speech}}</div>{{/Part of Speech}}
  {{#Notes}}<div class="notes">{{Notes}}</div>{{/Notes}}
</section>
""".strip()

CARD_TEMPLATES = [
    {"Name": WORD_TEMPLATE_NAME, "Front": WORD_FRONT, "Back": WORD_BACK},
    {"Name": SENTENCE_TEMPLATE_NAME, "Front": SENTENCE_FRONT, "Back": SENTENCE_BACK},
]

CSS = """
.card {
  box-sizing: border-box;
  margin: 0;
  padding: 24px 18px;
  color: #171717;
  background: #ffffff;
  font-family: "Kohinoor Devanagari", "Noto Sans Devanagari", "Nirmala UI", "Mangal", system-ui, sans-serif;
  font-size: 20px;
  line-height: 1.55;
  text-align: center;
}
.hindi-card,
.answer-primary,
.example-section,
.sentence-answer,
.target-word-section,
.notes {
  width: min(100%, 44rem);
  margin-left: auto;
  margin-right: auto;
}
.word {
  margin: 0.2em 0;
  font-size: clamp(44px, 12vw, 52px);
  font-weight: 600;
  line-height: 1.25;
}
.sentence-front {
  margin: 0.35em auto;
  font-size: clamp(30px, 8vw, 36px);
  font-weight: 500;
  line-height: 1.5;
}
#answer {
  width: min(100%, 36rem);
  margin: 24px auto 20px;
  border: 0;
  border-top: 1px solid #d6d6d6;
}
.pronunciation,
.example-pronunciation {
  color: #315b78;
  font-size: clamp(20px, 5vw, 23px);
  line-height: 1.45;
}
.meaning,
.example-meaning {
  margin-top: 6px;
  font-size: clamp(19px, 4.8vw, 22px);
  line-height: 1.45;
}
.part-of-speech,
.section-label {
  margin-top: 8px;
  color: #6a6a6a;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.example-section,
.target-word-section {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #e5e5e5;
}
.example-section .example {
  color: #333333;
  font-size: 27px;
  line-height: 1.5;
}
.example-section .example-pronunciation,
.example-section .example-meaning {
  color: #666666;
  font-size: 18px;
}
.target-word {
  margin-top: 4px;
  font-size: 32px;
  font-weight: 600;
  line-height: 1.35;
}
.notes {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 8px;
  color: #535353;
  background: #f4f4f4;
  font-size: 16px;
  line-height: 1.45;
}
.nightMode .card,
.card.nightMode {
  color: #f0f0f0;
  background: #202124;
}
.nightMode #answer,
.nightMode .example-section,
.nightMode .target-word-section {
  border-color: #4b4d50;
}
.nightMode .pronunciation,
.nightMode .example-pronunciation {
  color: #9ec8e6;
}
.nightMode .meaning,
.nightMode .example-meaning,
.nightMode .example-section .example {
  color: #e2e2e2;
}
.nightMode .part-of-speech,
.nightMode .section-label {
  color: #b7b7b7;
}
.nightMode .notes {
  color: #dddddd;
  background: #303236;
}
@media (max-width: 480px) {
  .card { padding: 18px 12px; }
  .example-section { margin-top: 18px; padding-top: 14px; }
}
""".strip()

PRODUCTION_LIKE_RE = re.compile(r"production|recall|reverse|english\s+to\s+hindi", re.IGNORECASE)


class HindiSetupError(RuntimeError):
    """Raised when the live Hindi resources are incompatible or incomplete."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def chunks(values: list[int], size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def note_field(note: dict[str, Any], name: str) -> str:
    return str(note.get("fields", {}).get(name, {}).get("value", "")).strip()


def normalized_pos_tag(part_of_speech: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", part_of_speech.casefold()).strip("_")
    return f"pos::{normalized}"


def template_mapping() -> dict[str, dict[str, str]]:
    return {
        template["Name"]: {"Front": template["Front"], "Back": template["Back"]}
        for template in CARD_TEMPLATES
    }


class HindiAnkiSetup:
    def __init__(
        self,
        *,
        client: AnkiClient,
        rows: list[dict[str, str]],
        reports_dir: Path = REPORTS_DIR,
    ) -> None:
        self.client = client
        self.rows = sorted(rows, key=lambda row: int(row["Frequency Rank"]))
        self.rows_by_word = {row["Word"]: row for row in self.rows}
        self.reports_dir = reports_dir
        self.hindi_only_option_changes: list[str] = []
        self.queue_order_method = ""

    def notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        for batch in chunks([int(value) for value in note_ids], 250):
            if batch:
                notes.extend(self.client.read("notesInfo", {"notes": batch}))
        return sorted(notes, key=lambda item: int(item["noteId"]))

    def cards_info(self, card_ids: list[int]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for batch in chunks([int(value) for value in card_ids], 500):
            if batch:
                cards.extend(self.client.read("cardsInfo", {"cards": batch}))
        return sorted(cards, key=lambda item: int(item["cardId"]))

    def find_notes(self, query: str) -> list[dict[str, Any]]:
        return self.notes_info([int(value) for value in self.client.read("findNotes", {"query": query})])

    def find_cards(self, query: str) -> list[dict[str, Any]]:
        return self.cards_info([int(value) for value in self.client.read("findCards", {"query": query})])

    def chinese_snapshot(self) -> dict[str, Any]:
        notes = self.find_notes(CHINESE_DECK_QUERY)
        cards = self.find_cards(CHINESE_DECK_QUERY)
        model_names = set(self.client.read("modelNames"))
        if CHINESE_MODEL_NAME in model_names:
            chinese_model = {
                "exists": True,
                "fields": self.client.read("modelFieldNames", {"modelName": CHINESE_MODEL_NAME}),
                "templates": self.client.read("modelTemplates", {"modelName": CHINESE_MODEL_NAME}),
                "styling": self.client.read("modelStyling", {"modelName": CHINESE_MODEL_NAME}),
            }
        else:
            chinese_model = {"exists": False, "fields": [], "templates": {}, "styling": {}}

        normalized_notes = []
        for note in notes:
            normalized_notes.append(
                {
                    "note_id": int(note["noteId"]),
                    "model_name": note.get("modelName", ""),
                    "fields": {
                        name: {
                            "order": int(field.get("order", 0)),
                            "value": str(field.get("value", "")),
                        }
                        for name, field in sorted(note.get("fields", {}).items())
                    },
                    "tags": sorted(str(tag) for tag in note.get("tags", [])),
                    "card_ids": sorted(int(card_id) for card_id in note.get("cards", [])),
                }
            )

        scheduling_keys = [
            "cardId",
            "note",
            "ord",
            "queue",
            "type",
            "due",
            "interval",
            "factor",
            "reps",
            "lapses",
            "left",
        ]
        normalized_cards = [
            {key: card.get(key) for key in scheduling_keys if key in card}
            for card in sorted(cards, key=lambda item: int(item["cardId"]))
        ]
        return {
            "deck": CHINESE_DECK_NAME,
            "deck_query": CHINESE_DECK_QUERY,
            "deck_id": int(self.client.read("deckNamesAndIds").get(CHINESE_DECK_NAME, -1)),
            "note_ids": [int(note["noteId"]) for note in notes],
            "card_ids": [int(card["cardId"]) for card in cards],
            "notes": normalized_notes,
            "cards": normalized_cards,
            "note_type": chinese_model,
            "deck_config": self.client.read("getDeckConfig", {"deck": CHINESE_DECK_NAME}),
        }

    @staticmethod
    def snapshot_document(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {"sha256": sha256_json(snapshot), "snapshot": snapshot}

    def install_guard(self, chinese_snapshot: dict[str, Any]) -> MutationGuard:
        config = chinese_snapshot.get("deck_config") or {}
        guard = MutationGuard(
            hindi_deck=DECK_NAME,
            hindi_model=MODEL_NAME,
            hindi_preset=OPTIONS_PRESET_NAME,
            protected_deck=CHINESE_DECK_NAME,
            protected_model=CHINESE_MODEL_NAME,
            protected_note_ids={int(value) for value in chinese_snapshot.get("note_ids", [])},
            protected_card_ids={int(value) for value in chinese_snapshot.get("card_ids", [])},
            protected_config_ids={int(config["id"])} if config.get("id") is not None else set(),
        )
        self.client.guard = guard
        return guard

    def inspect_hindi(self) -> dict[str, Any]:
        deck_names_and_ids = self.client.read("deckNamesAndIds")
        deck_names = set(deck_names_and_ids)
        model_names = set(self.client.read("modelNames"))
        deck_exists = DECK_NAME in deck_names
        model_exists = MODEL_NAME in model_names
        subdecks = sorted(name for name in deck_names if name.startswith(f"{DECK_NAME}::"))
        notes = self.find_notes(f"deck:{DECK_NAME}") if deck_exists else []
        cards = self.find_cards(f"deck:{DECK_NAME}") if deck_exists else []
        model_notes = self.find_notes(f'note:"{MODEL_NAME}"') if model_exists else []
        config = self.client.read("getDeckConfig", {"deck": DECK_NAME}) if deck_exists else None
        fields = self.client.read("modelFieldNames", {"modelName": MODEL_NAME}) if model_exists else []
        templates = self.client.read("modelTemplates", {"modelName": MODEL_NAME}) if model_exists else {}
        styling = self.client.read("modelStyling", {"modelName": MODEL_NAME}) if model_exists else {}
        return {
            "deck_exists": deck_exists,
            "deck_id": int(deck_names_and_ids[DECK_NAME]) if deck_exists else None,
            "model_exists": model_exists,
            "subdecks": subdecks,
            "notes": notes,
            "cards": cards,
            "model_notes": model_notes,
            "config": config,
            "fields": fields,
            "templates": templates,
            "styling": styling,
        }

    def assert_compatible(self, state: dict[str, Any]) -> None:
        problems: list[str] = []
        if state["subdecks"]:
            problems.append(f"Hindi subdecks are not managed by this setup: {state['subdecks']}")
        if state["model_exists"]:
            if state["fields"] != FIELDS:
                problems.append(f"existing Hindi Vocabulary fields are incompatible: {state['fields']}")
            if set(state["templates"]) != {WORD_TEMPLATE_NAME, SENTENCE_TEMPLATE_NAME}:
                problems.append(
                    "existing Hindi Vocabulary must have exactly Word Recognition and Sentence Recognition templates"
                )

        deck_note_ids = {int(note["noteId"]) for note in state["notes"]}
        model_note_ids = {int(note["noteId"]) for note in state["model_notes"]}
        outside_deck = model_note_ids - deck_note_ids
        if outside_deck:
            problems.append(f"Hindi Vocabulary notes exist outside deck Hindi: {sorted(outside_deck)[:10]}")

        seen_words: set[str] = set()
        for note in state["notes"]:
            note_id = int(note["noteId"])
            if note.get("modelName") != MODEL_NAME:
                problems.append(f"deck Hindi contains note {note_id} on unrelated type {note.get('modelName')!r}")
                continue
            word = note_field(note, "Word")
            if word not in self.rows_by_word:
                problems.append(f"deck Hindi contains unmanaged word {word!r} on note {note_id}")
            if word in seen_words:
                problems.append(f"deck Hindi contains duplicate managed word {word!r}")
            seen_words.add(word)

        if state["cards"] and not state["model_exists"]:
            problems.append("deck Hindi contains cards but Hindi Vocabulary does not exist")
        if problems:
            raise HindiSetupError("; ".join(problems))

    def row_fields(self, row: dict[str, str]) -> dict[str, str]:
        return {field: row[field] for field in FIELDS}

    def required_tags(self, row: dict[str, str]) -> set[str]:
        return STANDARD_TAGS | {normalized_pos_tag(row["Part of Speech"])}

    def plan(self, state: dict[str, Any], chinese_snapshot: dict[str, Any]) -> dict[str, Any]:
        self.assert_compatible(state)
        existing_by_word = {note_field(note, "Word"): note for note in state["notes"]}
        add_words = [row["Word"] for row in self.rows if row["Word"] not in existing_by_word]
        update_words = []
        tag_words = []
        for row in self.rows:
            note = existing_by_word.get(row["Word"])
            if note is None:
                continue
            if any(note_field(note, field) != value for field, value in self.row_fields(row).items()):
                update_words.append(row["Word"])
            if not self.required_tags(row).issubset(set(note.get("tags", []))):
                tag_words.append(row["Word"])

        inherited_config = state["config"] or chinese_snapshot["deck_config"]
        inherited_config_id = int(inherited_config["id"])
        needs_clone = (
            state["config"] is None
            or inherited_config.get("name") != OPTIONS_PRESET_NAME
            or inherited_config_id == int(chinese_snapshot["deck_config"]["id"])
        )
        option_changes = []
        if int(inherited_config.get("new", {}).get("perDay", -1)) != 5:
            option_changes.append("new.perDay")
        if int(inherited_config.get("newGatherPriority", -1)) != 0:
            option_changes.append("newGatherPriority")
        if int(inherited_config.get("newSortOrder", -1)) != 1:
            option_changes.append("newSortOrder")

        templates_need_update = state["model_exists"] and state["templates"] != template_mapping()
        styling_need_update = state["model_exists"] and state["styling"].get("css", "") != CSS
        return {
            "deck": DECK_NAME,
            "note_type": MODEL_NAME,
            "options_preset": OPTIONS_PRESET_NAME,
            "proposed_mutations": {
                "create_deck": not state["deck_exists"],
                "create_note_type": not state["model_exists"],
                "update_templates": templates_need_update,
                "update_styling": styling_need_update,
                "clone_options_preset": needs_clone,
                "assign_options_preset_to": [DECK_NAME] if needs_clone else [],
                "hindi_only_option_keys_to_change": option_changes,
                "add_note_count": len(add_words),
                "add_words": add_words,
                "update_note_count": len(update_words),
                "update_words": update_words,
                "add_missing_tags_note_count": len(tag_words),
                "reposition_new_cards_in_rank_template_order": True,
            },
            "expected_final_counts": {
                "notes": 100,
                WORD_TEMPLATE_NAME: 100,
                SENTENCE_TEMPLATE_NAME: 100,
                "cards": 200,
                "templates": 2,
                "production_like_templates": 0,
                "production_cards": 0,
                "new_cards_per_day": 5,
            },
            "inherited_config_id": inherited_config_id,
            "protected_default_config_id": int(chinese_snapshot["deck_config"]["id"]),
        }

    def dry_run(self) -> dict[str, Any]:
        mutation_count_before = len(self.client.mutation_log)
        chinese_snapshot = self.chinese_snapshot()
        state = self.inspect_hindi()
        plan = self.plan(state, chinese_snapshot)
        mutation_count_after = len(self.client.mutation_log)
        report = {
            "status": "PASS",
            "mode": "dry-run",
            "anki_connect_version": self.client.read("version"),
            "mutations_performed": mutation_count_after - mutation_count_before,
            "chinese_safety_sha256": sha256_json(chinese_snapshot),
            "current_hindi_state": {
                "deck_exists": state["deck_exists"],
                "note_type_exists": state["model_exists"],
                "note_count": len(state["notes"]),
                "card_count": len(state["cards"]),
                "config": state["config"],
            },
            **plan,
        }
        if report["mutations_performed"] != 0:
            raise HindiSetupError("dry-run performed a mutation")
        write_json(self.reports_dir / DRY_RUN_REPORT.name, report)
        return report

    def ensure_deck(self, state: dict[str, Any]) -> None:
        if not state["deck_exists"]:
            deck_id = self.client.mutate("createDeck", {"deck": DECK_NAME})
            if not deck_id:
                raise HindiSetupError("AnkiConnect did not create deck Hindi")

    def ensure_model(self, state: dict[str, Any]) -> None:
        if not state["model_exists"]:
            result = self.client.mutate(
                "createModel",
                {
                    "modelName": MODEL_NAME,
                    "inOrderFields": FIELDS,
                    "cardTemplates": CARD_TEMPLATES,
                    "css": CSS,
                },
            )
            if not result:
                raise HindiSetupError("AnkiConnect did not create Hindi Vocabulary")
            return
        if state["templates"] != template_mapping():
            self.client.mutate(
                "updateModelTemplates",
                {"model": {"name": MODEL_NAME, "templates": template_mapping()}},
            )
        if state["styling"].get("css", "") != CSS:
            self.client.mutate("updateModelStyling", {"model": {"name": MODEL_NAME, "css": CSS}})

    def ensure_options(self, default_config_before: dict[str, Any]) -> dict[str, Any]:
        if self.client.guard is None:
            raise HindiSetupError("mutation guard is missing")
        inherited = self.client.read("getDeckConfig", {"deck": DECK_NAME})
        if not inherited:
            raise HindiSetupError("could not inspect the options preset inherited by deck Hindi")
        inherited_id = int(inherited["id"])
        protected_id = int(default_config_before["id"])

        if inherited.get("name") == OPTIONS_PRESET_NAME and inherited_id != protected_id:
            hindi_config_id = inherited_id
            self.client.guard.register_hindi_config(hindi_config_id)
        else:
            cloned = self.client.mutate(
                "cloneDeckConfigId",
                {"name": OPTIONS_PRESET_NAME, "cloneFrom": inherited_id},
            )
            if cloned is False or cloned is None:
                raise HindiSetupError(
                    "AnkiConnect cannot safely clone an independent Hindi options preset; apply aborted"
                )
            hindi_config_id = int(cloned)
            if hindi_config_id == protected_id:
                raise HindiSetupError("cloned Hindi preset unexpectedly reused the protected Default preset")
            self.client.guard.register_hindi_config(hindi_config_id)
            assigned = self.client.mutate(
                "setDeckConfigId",
                {"decks": [DECK_NAME], "configId": hindi_config_id},
            )
            if assigned is not True:
                raise HindiSetupError("failed to assign the cloned options preset only to deck Hindi")

        config = self.client.read("getDeckConfig", {"deck": DECK_NAME})
        if int(config["id"]) != hindi_config_id or config.get("name") != OPTIONS_PRESET_NAME:
            raise HindiSetupError("Hindi did not retain the independently cloned options preset")

        updated = copy.deepcopy(config)
        changed: list[str] = []
        if "new" not in updated or "perDay" not in updated["new"]:
            raise HindiSetupError("installed Anki options do not expose new.perDay safely")
        if int(updated["new"]["perDay"]) != 5:
            updated["new"]["perDay"] = 5
            changed.append("new.perDay")
        if int(updated.get("newGatherPriority", -1)) != 0:
            updated["newGatherPriority"] = 0
            changed.append("newGatherPriority")
        if int(updated.get("newSortOrder", -1)) != 1:
            updated["newSortOrder"] = 1
            changed.append("newSortOrder")

        if changed:
            saved = self.client.mutate("saveDeckConfig", {"config": updated})
            if saved is not True:
                raise HindiSetupError("failed to save the independent Hindi options preset")
        self.hindi_only_option_changes = changed

        final = self.client.read("getDeckConfig", {"deck": DECK_NAME})
        if int(final["id"]) == protected_id:
            raise HindiSetupError("Hindi still shares the protected Default options preset")
        if final.get("name") != OPTIONS_PRESET_NAME or int(final["new"]["perDay"]) != 5:
            raise HindiSetupError("Hindi preset verification failed")
        if int(final.get("newGatherPriority", -1)) != 0 or int(final.get("newSortOrder", -1)) != 1:
            raise HindiSetupError("Hindi new-card display order is not deterministic")
        current_default = self.client.read("getDeckConfig", {"deck": CHINESE_DECK_NAME})
        if current_default != default_config_before:
            raise HindiSetupError("Default/Chinese options changed while creating the Hindi preset")
        return final

    def write_hindi_backup(self, notes: list[dict[str, Any]]) -> None:
        if not notes:
            return
        path = self.reports_dir / HINDI_BACKUP_TSV.name
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["Note ID", *FIELDS, "Tags"]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for note in notes:
                writer.writerow(
                    {
                        "Note ID": str(note["noteId"]),
                        **{field: note_field(note, field) for field in FIELDS},
                        "Tags": " ".join(sorted(str(tag) for tag in note.get("tags", []))),
                    }
                )

    def ensure_notes(self, existing_notes: list[dict[str, Any]]) -> dict[str, int]:
        if self.client.guard is None:
            raise HindiSetupError("mutation guard is missing")
        self.write_hindi_backup(existing_notes)
        self.client.guard.register_hindi_notes({int(note["noteId"]) for note in existing_notes})
        existing_by_word = {note_field(note, "Word"): note for note in existing_notes}

        update_actions = []
        for row in self.rows:
            note = existing_by_word.get(row["Word"])
            if note is None:
                continue
            expected_fields = self.row_fields(row)
            changed_fields = {
                field: expected
                for field, expected in expected_fields.items()
                if note_field(note, field) != expected
            }
            if changed_fields:
                update_actions.append(
                    {
                        "action": "updateNoteFields",
                        "params": {"note": {"id": int(note["noteId"]), "fields": changed_fields}},
                    }
                )
        for start in range(0, len(update_actions), 50):
            results = self.client.mutate("multi", {"actions": update_actions[start : start + 50]})
            for result in results:
                if isinstance(result, dict) and result.get("error"):
                    raise HindiSetupError(f"Hindi field update failed: {result['error']}")

        missing_rows = [row for row in self.rows if row["Word"] not in existing_by_word]
        added_ids: list[int] = []
        if missing_rows:
            notes = []
            for row in missing_rows:
                notes.append(
                    {
                        "deckName": DECK_NAME,
                        "modelName": MODEL_NAME,
                        "fields": self.row_fields(row),
                        "tags": sorted(self.required_tags(row)),
                        "options": {
                            "allowDuplicate": False,
                            "duplicateScope": "deck",
                            "duplicateScopeOptions": {
                                "deckName": DECK_NAME,
                                "checkChildren": False,
                                "checkAllModels": False,
                            },
                        },
                    }
                )
            results = self.client.mutate("addNotes", {"notes": notes})
            if len(results) != len(notes) or any(result is None for result in results):
                raise HindiSetupError(f"addNotes did not create all Hindi notes: {results}")
            added_ids = [int(result) for result in results]
            self.client.guard.register_hindi_notes(added_ids)

        current_notes = self.find_notes(f"deck:{DECK_NAME}")
        self.client.guard.register_hindi_notes({int(note["noteId"]) for note in current_notes})
        tag_groups: dict[str, list[int]] = defaultdict(list)
        for note in current_notes:
            row = self.rows_by_word.get(note_field(note, "Word"))
            if row is None:
                raise HindiSetupError("an unmanaged Hindi note appeared during apply")
            missing_tags = self.required_tags(row) - set(note.get("tags", []))
            if missing_tags:
                tag_groups[" ".join(sorted(missing_tags))].append(int(note["noteId"]))
        for tags, note_ids in sorted(tag_groups.items()):
            self.client.mutate("addTags", {"notes": note_ids, "tags": tags})

        return {
            "added": len(added_ids),
            "updated": len(update_actions),
            "tagged": sum(len(values) for values in tag_groups.values()),
        }

    def expected_card_order(self, notes: list[dict[str, Any]], cards: list[dict[str, Any]]) -> list[int]:
        notes_by_word = {note_field(note, "Word"): note for note in notes}
        cards_by_note: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for card in cards:
            cards_by_note[int(card["note"])].append(card)
        ordered: list[int] = []
        for row in self.rows:
            note = notes_by_word.get(row["Word"])
            if note is None:
                continue
            note_cards = sorted(cards_by_note[int(note["noteId"])], key=lambda card: int(card["ord"]))
            for card in note_cards:
                if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) >= 0:
                    ordered.append(int(card["cardId"]))
        return ordered

    @staticmethod
    def current_new_card_order(cards: list[dict[str, Any]]) -> list[int]:
        new_cards = [
            card
            for card in cards
            if int(card.get("type", -1)) == 0 and int(card.get("queue", -1)) >= 0
        ]
        return [
            int(card["cardId"])
            for card in sorted(new_cards, key=lambda card: (int(card.get("due", 0)), int(card["cardId"])))
        ]

    def ensure_card_order(self) -> dict[str, Any]:
        if self.client.guard is None:
            raise HindiSetupError("mutation guard is missing")
        notes = self.find_notes(f"deck:{DECK_NAME}")
        cards = self.find_cards(f"deck:{DECK_NAME}")
        self.client.guard.register_hindi_notes({int(note["noteId"]) for note in notes})
        self.client.guard.register_hindi_cards({int(card["cardId"]) for card in cards})
        expected = self.expected_card_order(notes, cards)
        current = self.current_new_card_order(cards)
        if current == expected:
            self.queue_order_method = "already-correct"
            return {"repositioned": 0, "method": self.queue_order_method}
        try:
            self.client.mutate(
                "reposition",
                {
                    "cards": expected,
                    "startingFrom": 1,
                    "step": 1,
                    "randomize": False,
                    "shiftPosition": True,
                },
            )
            self.queue_order_method = "reposition"
        except AnkiConnectError as exc:
            for due, card_id in enumerate(expected, start=1):
                result = self.client.mutate(
                    "setSpecificValueOfCard",
                    {"card": card_id, "keys": ["due"], "newValues": [due]},
                )
                if not result or result[0] is not True:
                    raise HindiSetupError(f"due-field order fallback failed for card {card_id}: {result}") from exc
            self.queue_order_method = "setSpecificValueOfCard:due"

        after = self.find_cards(f"deck:{DECK_NAME}")
        if self.current_new_card_order(after) != expected:
            raise HindiSetupError("Hindi new-card order did not match Frequency Rank and template order")
        return {"repositioned": len(expected), "method": self.queue_order_method}

    def verify_live(self) -> dict[str, Any]:
        state = self.inspect_hindi()
        errors: list[str] = []
        if not state["deck_exists"]:
            errors.append("deck Hindi does not exist")
        if not state["model_exists"]:
            errors.append("note type Hindi Vocabulary does not exist")
        template_names = list(state["templates"])
        if template_names != [WORD_TEMPLATE_NAME, SENTENCE_TEMPLATE_NAME] and set(template_names) != {
            WORD_TEMPLATE_NAME,
            SENTENCE_TEMPLATE_NAME,
        }:
            errors.append(f"template names are not exact: {template_names}")
        if len(template_names) != 2:
            errors.append(f"template count is {len(template_names)}, expected 2")
        if state["fields"] != FIELDS:
            errors.append(f"field schema is incompatible: {state['fields']}")

        production_like_templates = []
        for name, template in state["templates"].items():
            haystack = " ".join([name, str(template.get("Front", "")), str(template.get("Back", ""))])
            if PRODUCTION_LIKE_RE.search(haystack):
                production_like_templates.append(name)
        if production_like_templates:
            errors.append(f"production-like templates exist: {production_like_templates}")

        notes = state["notes"]
        cards = state["cards"]
        notes_by_word = {note_field(note, "Word"): note for note in notes}
        if len(notes) != 100:
            errors.append(f"managed note count is {len(notes)}, expected 100")
        if len(notes_by_word) != 100 or set(notes_by_word) != set(self.rows_by_word):
            errors.append("live Hindi words do not match the 100 TSV source words")
        if any(note.get("modelName") != MODEL_NAME for note in notes):
            errors.append("deck Hindi contains a note on another note type")

        required_field_counts = {
            field: sum(1 for note in notes if note_field(note, field))
            for field in [
                "Pronunciation",
                "Meaning",
                "Example",
                "Example Pronunciation",
                "Example Meaning",
                "Labels",
                "Frequency Rank",
            ]
        }
        for field, count in required_field_counts.items():
            if count != 100:
                errors.append(f"only {count} notes have {field}")

        ranks = sorted(
            int(note_field(note, "Frequency Rank"))
            for note in notes
            if note_field(note, "Frequency Rank").isdigit()
        )
        if ranks != list(range(1, 101)):
            errors.append("live Frequency Rank values are not exactly 1 through 100")

        notes_with_standard_tags = sum(
            1 for note in notes if STANDARD_TAGS.issubset(set(note.get("tags", [])))
        )
        notes_with_pos_tag = sum(
            1 for note in notes if any(str(tag).startswith("pos::") for tag in note.get("tags", []))
        )
        if notes_with_standard_tags != 100:
            errors.append("not every Hindi note has both standard Hindi tags")
        if notes_with_pos_tag != 100:
            errors.append("not every Hindi note has a normalized part-of-speech tag")

        counts_by_ord = Counter(int(card.get("ord", -1)) for card in cards)
        word_cards = counts_by_ord[0]
        sentence_cards = counts_by_ord[1]
        production_cards = sum(count for ord_value, count in counts_by_ord.items() if ord_value not in {0, 1})
        if word_cards != 100:
            errors.append(f"Word Recognition card count is {word_cards}, expected 100")
        if sentence_cards != 100:
            errors.append(f"Sentence Recognition card count is {sentence_cards}, expected 100")
        if len(cards) != 200:
            errors.append(f"total card count is {len(cards)}, expected 200")
        if production_cards != 0:
            errors.append(f"production/other card count is {production_cards}, expected 0")

        config = state["config"] or {}
        default_config = self.client.read("getDeckConfig", {"deck": CHINESE_DECK_NAME})
        if not config:
            errors.append("Hindi options preset is unavailable")
        else:
            if config.get("name") != OPTIONS_PRESET_NAME:
                errors.append(f"Hindi preset name is {config.get('name')!r}")
            if int(config.get("id", -1)) == int(default_config.get("id", -1)):
                errors.append("Hindi shares the Default/Chinese options preset")
            if int(config.get("new", {}).get("perDay", -1)) != 5:
                errors.append("Hindi new cards/day is not 5")
            if int(config.get("newGatherPriority", -1)) != 0:
                errors.append("Hindi new-card gather order is not deck/ascending-position order")
            if int(config.get("newSortOrder", -1)) != 1:
                errors.append("Hindi new-card sort order is not order gathered")

        expected_order = self.expected_card_order(notes, cards)
        current_order = self.current_new_card_order(cards)
        card_order_ok = expected_order == current_order
        if not card_order_ok:
            errors.append("new cards are not ordered rank 1 word, rank 1 sentence, rank 2 word, rank 2 sentence")

        report = {
            "status": "PASS" if not errors else "FAIL",
            "deck": DECK_NAME,
            "deck_exists": state["deck_exists"],
            "note_type": MODEL_NAME,
            "note_type_exists": state["model_exists"],
            "field_names": state["fields"],
            "template_names": template_names,
            "template_count": len(template_names),
            "production_like_templates": production_like_templates,
            "production_like_template_count": len(production_like_templates),
            "managed_note_count": len(notes),
            "word_recognition_cards": word_cards,
            "sentence_recognition_cards": sentence_cards,
            "total_cards": len(cards),
            "production_cards": production_cards,
            "required_field_counts": required_field_counts,
            "notes_with_standard_tags": notes_with_standard_tags,
            "notes_with_pos_tag": notes_with_pos_tag,
            "rank_values_complete": ranks == list(range(1, 101)),
            "options_preset": config.get("name"),
            "options_config_id": config.get("id"),
            "default_config_id": default_config.get("id"),
            "separate_options_preset": bool(config)
            and int(config.get("id", -1)) != int(default_config.get("id", -1)),
            "new_cards_per_day": config.get("new", {}).get("perDay") if config else None,
            "new_gather_priority": config.get("newGatherPriority") if config else None,
            "new_sort_order": config.get("newSortOrder") if config else None,
            "card_order_ok": card_order_ok,
            "new_card_count_in_order_check": len(expected_order),
            "errors": errors,
        }
        return report

    def apply(self) -> dict[str, Any]:
        before = self.chinese_snapshot()
        before_doc = self.snapshot_document(before)
        write_json(self.reports_dir / CHINESE_SAFETY_BEFORE.name, before_doc)
        guard = self.install_guard(before)
        report: dict[str, Any] = {
            "status": "FAIL",
            "mode": "apply",
            "deck": DECK_NAME,
            "note_type": MODEL_NAME,
            "options_preset": OPTIONS_PRESET_NAME,
            "chinese_safety_before_sha256": before_doc["sha256"],
        }
        try:
            state = self.inspect_hindi()
            self.assert_compatible(state)
            guard.register_hindi_notes({int(note["noteId"]) for note in state["notes"]})
            guard.register_hindi_cards({int(card["cardId"]) for card in state["cards"]})
            plan = self.plan(state, before)
            self.ensure_deck(state)
            self.ensure_model(state)
            final_config = self.ensure_options(before["deck_config"])
            note_result = self.ensure_notes(state["notes"])
            order_result = self.ensure_card_order()

            after = self.chinese_snapshot()
            after_doc = self.snapshot_document(after)
            write_json(self.reports_dir / CHINESE_SAFETY_AFTER.name, after_doc)
            comparison = {
                "before_sha256": before_doc["sha256"],
                "after_sha256": after_doc["sha256"],
                "identical": before_doc["sha256"] == after_doc["sha256"],
                "structured_equal": before == after,
                "differing_top_level_keys": sorted(
                    key for key in set(before) | set(after) if before.get(key) != after.get(key)
                ),
            }
            write_json(self.reports_dir / CHINESE_SAFETY_COMPARISON.name, comparison)
            if not comparison["identical"] or not comparison["structured_equal"]:
                raise HindiSetupError("Chinese snapshot changed during Hindi apply")

            verification = self.verify_live()
            write_json(self.reports_dir / VERIFICATION_REPORT.name, verification)
            if verification["status"] != "PASS":
                raise HindiSetupError("; ".join(verification["errors"]))

            report.update(
                {
                    "status": "PASS",
                    "plan": plan,
                    "note_changes": note_result,
                    "card_order": order_result,
                    "hindi_only_option_keys_changed": self.hindi_only_option_changes,
                    "options_config_id": final_config["id"],
                    "new_cards_per_day": final_config["new"]["perDay"],
                    "chinese_safety_after_sha256": after_doc["sha256"],
                    "chinese_safety_identical": True,
                    "verification": verification,
                    "mutation_log": self.client.mutation_log,
                }
            )
        except Exception as exc:
            report["error"] = str(exc)
            try:
                after = self.chinese_snapshot()
                after_doc = self.snapshot_document(after)
                write_json(self.reports_dir / CHINESE_SAFETY_AFTER.name, after_doc)
                comparison = {
                    "before_sha256": before_doc["sha256"],
                    "after_sha256": after_doc["sha256"],
                    "identical": before_doc["sha256"] == after_doc["sha256"],
                    "structured_equal": before == after,
                    "differing_top_level_keys": sorted(
                        key for key in set(before) | set(after) if before.get(key) != after.get(key)
                    ),
                }
                write_json(self.reports_dir / CHINESE_SAFETY_COMPARISON.name, comparison)
                report["chinese_safety_after_sha256"] = after_doc["sha256"]
                report["chinese_safety_identical"] = comparison["identical"]
            except Exception as snapshot_exc:
                report["after_snapshot_error"] = str(snapshot_exc)
            report["mutation_log"] = self.client.mutation_log
            write_json(self.reports_dir / APPLY_REPORT.name, report)
            raise
        write_json(self.reports_dir / APPLY_REPORT.name, report)
        return report

    def verify_only(self) -> dict[str, Any]:
        report = self.verify_live()
        report["mode"] = "verify-only"
        write_json(self.reports_dir / VERIFICATION_REPORT.name, report)
        if report["status"] != "PASS":
            raise HindiSetupError("; ".join(report["errors"]))
        return report


def load_validated_rows(
    *,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
    validation_report: Path = DATA_VALIDATION_REPORT,
) -> list[dict[str, str]]:
    validate_or_raise(
        tsv_path=tsv_path,
        sources_path=sources_path,
        report_path=validation_report,
    )
    rows, _header, _findings = load_rows(tsv_path)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely create, update, or verify the isolated Hindi Core 100 Anki deck."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="Inspect and report proposed Hindi-only changes (default).")
    modes.add_argument("--apply", action="store_true", help="Apply guarded Hindi-only mutations.")
    modes.add_argument("--verify-only", action="store_true", help="Inspect the existing live Hindi resources without mutation.")
    parser.add_argument("--anki-connect-url", default=ANKI_CONNECT_URL)
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    return parser.parse_args()


def run(
    *,
    mode: str,
    url: str = ANKI_CONNECT_URL,
    transport: Transport | None = None,
    tsv_path: Path = DEFAULT_TSV,
    sources_path: Path = DEFAULT_SOURCES,
    reports_dir: Path = REPORTS_DIR,
) -> dict[str, Any]:
    rows = load_validated_rows(
        tsv_path=tsv_path,
        sources_path=sources_path,
        validation_report=reports_dir / DATA_VALIDATION_REPORT.name,
    )
    manager = HindiAnkiSetup(
        client=AnkiClient(url=url, transport=transport),
        rows=rows,
        reports_dir=reports_dir,
    )
    if mode == "apply":
        return manager.apply()
    if mode == "verify-only":
        return manager.verify_only()
    return manager.dry_run()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    mode = "apply" if args.apply else "verify-only" if args.verify_only else "dry-run"
    try:
        report = run(
            mode=mode,
            url=args.anki_connect_url,
            tsv_path=args.tsv,
            sources_path=args.sources,
        )
    except (AnkiConnectError, HindiSetupError, MutationSafetyError, OSError, ValueError) as exc:
        error_report = {"status": "BLOCKED" if isinstance(exc, AnkiConnectError) else "FAIL", "mode": mode, "error": str(exc)}
        report_path = DRY_RUN_REPORT if mode == "dry-run" else APPLY_REPORT if mode == "apply" else VERIFICATION_REPORT
        if not report_path.exists() or mode != "apply":
            write_json(report_path, error_report)
        print(json.dumps(error_report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2 if isinstance(exc, AnkiConnectError) else 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
