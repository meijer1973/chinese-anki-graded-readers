from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.china_knowledge.anki_client import (  # noqa: E402
    ANKI_CONNECT_URL,
    AnkiClient,
    AnkiConnectError,
    MutationGuard,
    MutationSafetyError,
    Transport,
)
from scripts.china_knowledge.config import (  # noqa: E402
    DECK_NAME,
    DEFAULT_REPORTS_DIR,
    DEFAULT_SOURCES,
    DEFAULT_TSV,
    FIELDS,
    MODEL_NAME,
    NEW_CARDS_PER_DAY,
    OPTIONS_PRESET_NAME,
    PROTECTED_RESOURCES,
    STANDARD_TAG,
    TEMPLATE_NAME,
)
from scripts.china_knowledge.validate_china_knowledge import (  # noqa: E402
    DEFAULT_REPORT as DATA_VALIDATION_REPORT,
    load_rows,
    split_tags,
    validate_or_raise,
)


DRY_RUN_REPORT = DEFAULT_REPORTS_DIR / "china_knowledge_anki_dry_run.json"
OFFLINE_PREVIEW_REPORT = DEFAULT_REPORTS_DIR / "china_knowledge_offline_preview.json"
APPLY_REPORT = DEFAULT_REPORTS_DIR / "china_knowledge_anki_apply_report.json"
VERIFICATION_REPORT = DEFAULT_REPORTS_DIR / "china_knowledge_anki_verification.json"
BACKUP_TSV = DEFAULT_REPORTS_DIR / "china_knowledge_managed_notes_before_update.tsv"

FRONT = """
<main class="knowledge-card">
  {{#Category}}<div class="category">{{Category}}</div>{{/Category}}
  <div class="question-zh" lang="zh-Hans">{{Chinese Question}}</div>
  <div class="question-en" lang="en">{{English Question}}</div>
</main>
""".strip()

BACK = """
{{FrontSide}}
<hr id="answer">
<section class="answer-block">
  <div class="answer-zh" lang="zh-Hans">{{Chinese Answer}}</div>
  <div class="answer-en" lang="en">{{English Answer}}</div>
</section>
{{#Chinese Explanation}}
<section class="explanation-block">
  <div class="explanation-zh" lang="zh-Hans">{{Chinese Explanation}}</div>
  <div class="explanation-en" lang="en">{{English Explanation}}</div>
</section>
{{/Chinese Explanation}}
<footer class="metadata">
  <span>{{Category}}</span>{{#Era}}<span>{{Era}}</span>{{/Era}}{{#Region}}<span>{{Region}}</span>{{/Region}}
  <details><summary>Sources</summary><div>{{Source}} · {{Source Date}}</div></details>
</footer>
""".strip()

CARD_TEMPLATES = [{"Name": TEMPLATE_NAME, "Front": FRONT, "Back": BACK}]

CSS = """
.card {
  box-sizing: border-box;
  margin: 0;
  padding: 22px 16px 28px;
  color: #17202a;
  background: #ffffff;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  font-size: 19px;
  line-height: 1.55;
  text-align: left;
}
.knowledge-card,
.answer-block,
.explanation-block,
.metadata {
  width: min(100%, 44rem);
  margin-left: auto;
  margin-right: auto;
}
.category {
  margin-bottom: 12px;
  color: #65717d;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.question-zh {
  font-size: clamp(29px, 7.5vw, 38px);
  font-weight: 650;
  line-height: 1.42;
}
.question-en {
  margin-top: 12px;
  color: #56616c;
  font-size: clamp(18px, 4.7vw, 22px);
  line-height: 1.48;
}
#answer {
  width: min(100%, 36rem);
  margin: 24px auto 20px;
  border: 0;
  border-top: 1px solid #d7dde2;
}
.answer-zh {
  color: #8b2e2e;
  font-size: clamp(27px, 6.8vw, 34px);
  font-weight: 650;
  line-height: 1.4;
}
.answer-en {
  margin-top: 8px;
  font-size: clamp(19px, 4.9vw, 23px);
  font-weight: 600;
}
.explanation-block {
  margin-top: 20px;
  padding-top: 17px;
  border-top: 1px solid #e5e8eb;
}
.explanation-zh { font-size: 21px; line-height: 1.62; }
.explanation-en { margin-top: 10px; color: #4f5963; font-size: 17px; line-height: 1.58; }
.metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 12px;
  margin-top: 24px;
  color: #737d86;
  font-size: 13px;
}
.metadata details { flex-basis: 100%; margin-top: 3px; }
.metadata summary { cursor: pointer; }
.metadata details div { margin-top: 5px; overflow-wrap: anywhere; }
.nightMode .card,
.card.nightMode { color: #edf0f2; background: #202124; }
.nightMode .question-en,
.nightMode .explanation-en { color: #c4c9ce; }
.nightMode .answer-zh { color: #ffaaaa; }
.nightMode #answer,
.nightMode .explanation-block { border-color: #4c5156; }
.nightMode .category,
.nightMode .metadata { color: #aeb5bb; }
@media (max-width: 480px) {
  .card { padding: 18px 12px 24px; }
  .explanation-block { margin-top: 17px; padding-top: 14px; }
}
""".strip()

MEDIA_OR_TTS_RE = re.compile(r"\[sound:|<img\b|<audio\b|\btts\b", re.IGNORECASE)


class ChinaKnowledgeSetupError(RuntimeError):
    """Raised when live resources are incompatible or verification fails."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def chunks(values: list[int], size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def note_field(note: dict[str, Any], name: str) -> str:
    return str(note.get("fields", {}).get(name, {}).get("value", "")).strip()


def normalized_tag(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return normalized


def template_mapping() -> dict[str, dict[str, str]]:
    return {TEMPLATE_NAME: {"Front": FRONT, "Back": BACK}}


class ChinaKnowledgeAnkiSetup:
    def __init__(
        self,
        *,
        client: AnkiClient,
        rows: list[dict[str, str]],
        reports_dir: Path = DEFAULT_REPORTS_DIR,
    ) -> None:
        self.client = client
        self.rows = sorted(rows, key=lambda row: row["Knowledge ID"])
        self.rows_by_id = {row["Knowledge ID"]: row for row in self.rows}
        self.reports_dir = reports_dir

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

    def protected_snapshot(self, deck_name: str, model_name: str) -> dict[str, Any]:
        deck_names = self.client.read("deckNamesAndIds")
        model_names = set(self.client.read("modelNames"))
        deck_exists = deck_name in deck_names
        model_exists = model_name in model_names
        notes = self.find_notes(f'deck:"{deck_name}"') if deck_exists else []
        cards = self.find_cards(f'deck:"{deck_name}"') if deck_exists else []
        if model_exists:
            model = {
                "exists": True,
                "fields": self.client.read("modelFieldNames", {"modelName": model_name}),
                "templates": self.client.read("modelTemplates", {"modelName": model_name}),
                "styling": self.client.read("modelStyling", {"modelName": model_name}),
            }
        else:
            model = {"exists": False, "fields": [], "templates": {}, "styling": {}}
        normalized_notes = [
            {
                "note_id": int(note["noteId"]),
                "model_name": note.get("modelName", ""),
                "fields": {
                    name: {"order": int(field.get("order", 0)), "value": str(field.get("value", ""))}
                    for name, field in sorted(note.get("fields", {}).items())
                },
                "tags": sorted(str(tag) for tag in note.get("tags", [])),
                "card_ids": sorted(int(card_id) for card_id in note.get("cards", [])),
            }
            for note in notes
        ]
        scheduling_keys = (
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
        )
        normalized_cards = [
            {key: card.get(key) for key in scheduling_keys if key in card}
            for card in cards
        ]
        return {
            "deck": deck_name,
            "deck_exists": deck_exists,
            "deck_id": int(deck_names.get(deck_name, -1)),
            "note_ids": [int(note["noteId"]) for note in notes],
            "card_ids": [int(card["cardId"]) for card in cards],
            "notes": normalized_notes,
            "cards": normalized_cards,
            "note_type": model,
            "deck_config": self.client.read("getDeckConfig", {"deck": deck_name}) if deck_exists else None,
        }

    def protected_snapshots(self) -> dict[str, dict[str, Any]]:
        return {
            deck: self.protected_snapshot(deck, model)
            for deck, model in PROTECTED_RESOURCES
        }

    def install_guard(self, snapshots: dict[str, dict[str, Any]]) -> MutationGuard:
        guard = MutationGuard(
            target_deck=DECK_NAME,
            target_model=MODEL_NAME,
            target_preset=OPTIONS_PRESET_NAME,
            protected_note_ids={
                int(note_id)
                for snapshot in snapshots.values()
                for note_id in snapshot.get("note_ids", [])
            },
            protected_card_ids={
                int(card_id)
                for snapshot in snapshots.values()
                for card_id in snapshot.get("card_ids", [])
            },
            protected_config_ids={
                int(snapshot["deck_config"]["id"])
                for snapshot in snapshots.values()
                if isinstance(snapshot.get("deck_config"), dict)
                and snapshot["deck_config"].get("id") is not None
            },
        )
        self.client.guard = guard
        return guard

    def inspect_target(self) -> dict[str, Any]:
        deck_names = self.client.read("deckNamesAndIds")
        model_names = set(self.client.read("modelNames"))
        deck_exists = DECK_NAME in deck_names
        model_exists = MODEL_NAME in model_names
        subdecks = sorted(name for name in deck_names if name.startswith(f"{DECK_NAME}::"))
        notes = self.find_notes(f'deck:"{DECK_NAME}"') if deck_exists else []
        cards = self.find_cards(f'deck:"{DECK_NAME}"') if deck_exists else []
        model_notes = self.find_notes(f'note:"{MODEL_NAME}"') if model_exists else []
        return {
            "deck_exists": deck_exists,
            "deck_id": int(deck_names[DECK_NAME]) if deck_exists else None,
            "model_exists": model_exists,
            "subdecks": subdecks,
            "notes": notes,
            "cards": cards,
            "model_notes": model_notes,
            "config": self.client.read("getDeckConfig", {"deck": DECK_NAME}) if deck_exists else None,
            "fields": self.client.read("modelFieldNames", {"modelName": MODEL_NAME}) if model_exists else [],
            "templates": self.client.read("modelTemplates", {"modelName": MODEL_NAME}) if model_exists else {},
            "styling": self.client.read("modelStyling", {"modelName": MODEL_NAME}) if model_exists else {},
        }

    def all_deck_configs(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for deck_name in self.client.read("deckNamesAndIds"):
            config = self.client.read("getDeckConfig", {"deck": deck_name})
            if isinstance(config, dict):
                result[deck_name] = config
        return result

    def assert_compatible(self, state: dict[str, Any]) -> None:
        problems: list[str] = []
        if state["subdecks"]:
            problems.append(f"subdecks are outside this installer's scope: {state['subdecks']}")
        if state["model_exists"]:
            if state["fields"] != FIELDS:
                problems.append(f"existing note fields are incompatible: {state['fields']}")
            if set(state["templates"]) != {TEMPLATE_NAME}:
                problems.append(f"the note type must have exactly one {TEMPLATE_NAME!r} template")
        deck_note_ids = {int(note["noteId"]) for note in state["notes"]}
        model_note_ids = {int(note["noteId"]) for note in state["model_notes"]}
        outside = model_note_ids - deck_note_ids
        if outside:
            problems.append(f"guarded note-type notes exist outside the guarded deck: {sorted(outside)[:10]}")
        seen_ids: set[str] = set()
        for note in state["notes"]:
            note_id = int(note["noteId"])
            if note.get("modelName") != MODEL_NAME:
                problems.append(f"guarded deck contains unrelated note {note_id}")
                continue
            knowledge_id = note_field(note, "Knowledge ID")
            if not knowledge_id:
                problems.append(f"guarded note {note_id} has no Knowledge ID")
            elif knowledge_id in seen_ids:
                problems.append(f"duplicate live Knowledge ID {knowledge_id!r}")
            seen_ids.add(knowledge_id)
        if problems:
            raise ChinaKnowledgeSetupError("; ".join(problems))

    def row_fields(self, row: dict[str, str]) -> dict[str, str]:
        return {field: row.get(field, "") for field in FIELDS}

    def required_tags(self, row: dict[str, str]) -> set[str]:
        tags = {
            STANDARD_TAG,
            f"{STANDARD_TAG}::{normalized_tag(row['Category'])}",
            f"difficulty::{normalized_tag(row['Difficulty'])}",
        }
        if row.get("Era"):
            tags.add(f"era::{normalized_tag(row['Era'])}")
        if row.get("Region"):
            tags.add(f"region::{normalized_tag(row['Region'])}")
        for tag in split_tags(row.get("Tags", "")):
            if tag:
                tags.add(tag)
        return tags

    def plan(self, state: dict[str, Any], protected: dict[str, dict[str, Any]]) -> dict[str, Any]:
        self.assert_compatible(state)
        existing_by_id = {note_field(note, "Knowledge ID"): note for note in state["notes"]}
        create_ids: list[str] = []
        field_update_ids: list[str] = []
        tag_update_ids: list[str] = []
        unchanged_ids: list[str] = []
        for row in self.rows:
            knowledge_id = row["Knowledge ID"]
            note = existing_by_id.get(knowledge_id)
            if note is None:
                create_ids.append(knowledge_id)
                continue
            fields_changed = any(
                note_field(note, field) != value
                for field, value in self.row_fields(row).items()
            )
            tags_changed = not self.required_tags(row).issubset(set(note.get("tags", [])))
            if fields_changed:
                field_update_ids.append(knowledge_id)
            if tags_changed:
                tag_update_ids.append(knowledge_id)
            if not fields_changed and not tags_changed:
                unchanged_ids.append(knowledge_id)

        protected_config_ids = {
            int(snapshot["deck_config"]["id"])
            for snapshot in protected.values()
            if isinstance(snapshot.get("deck_config"), dict)
        }
        inherited = state["config"]
        if not isinstance(inherited, dict):
            inherited = next(
                (
                    snapshot["deck_config"]
                    for snapshot in protected.values()
                    if isinstance(snapshot.get("deck_config"), dict)
                ),
                None,
            )
        if not isinstance(inherited, dict):
            raise ChinaKnowledgeSetupError("no options preset is available to clone")
        config_id = int(inherited["id"])
        needs_option_clone = (
            state["config"] is None
            or inherited.get("name") != OPTIONS_PRESET_NAME
            or config_id in protected_config_ids
        )
        update_union = sorted(set(field_update_ids) | set(tag_update_ids))
        return {
            "deck": DECK_NAME,
            "note_type": MODEL_NAME,
            "source_note_count": len(self.rows),
            "would_create": len(create_ids),
            "would_update": len(update_union),
            "would_skip_unchanged": len(unchanged_ids),
            "would_reject": 0,
            "create_ids": create_ids,
            "field_update_ids": field_update_ids,
            "tag_update_ids": tag_update_ids,
            "unchanged_ids": unchanged_ids,
            "out_of_source_live_ids": sorted(set(existing_by_id) - set(self.rows_by_id)),
            "create_deck": not state["deck_exists"],
            "create_note_type": not state["model_exists"],
            "update_template": state["model_exists"] and state["templates"] != template_mapping(),
            "update_styling": state["model_exists"] and state["styling"].get("css", "") != CSS,
            "clone_options_preset": needs_option_clone,
            "set_new_cards_per_day": int(inherited.get("new", {}).get("perDay", -1)) != NEW_CARDS_PER_DAY,
            "active_template_count": 1,
            "expected_new_cards_from_source": len(self.rows),
            "deletions": 0,
        }

    def offline_preview(self) -> dict[str, Any]:
        report = {
            "status": "PASS",
            "mode": "offline-preview",
            "assumption": "target deck and note type do not yet exist; live Anki was not queried",
            "deck": DECK_NAME,
            "note_type": MODEL_NAME,
            "options_preset": OPTIONS_PRESET_NAME,
            "would_create": len(self.rows),
            "would_update": 0,
            "would_skip_unchanged": 0,
            "would_reject": 0,
            "active_template_count": 1,
            "expected_card_count": len(self.rows),
            "new_cards_per_day": NEW_CARDS_PER_DAY,
            "mutations_performed": 0,
        }
        write_json(self.reports_dir / OFFLINE_PREVIEW_REPORT.name, report)
        return report

    def dry_run(self) -> dict[str, Any]:
        protected = self.protected_snapshots()
        state = self.inspect_target()
        plan = self.plan(state, protected)
        report = {
            "status": "PASS",
            "mode": "dry-run",
            "plan": plan,
            "protected_snapshot_sha256": {
                deck: sha256_json(snapshot) for deck, snapshot in protected.items()
            },
            "mutations_performed": len(self.client.mutation_log),
        }
        write_json(self.reports_dir / DRY_RUN_REPORT.name, report)
        return report

    def ensure_deck_and_model(self, state: dict[str, Any]) -> None:
        if not state["deck_exists"]:
            self.client.mutate("createDeck", {"deck": DECK_NAME})
        if not state["model_exists"]:
            self.client.mutate(
                "createModel",
                {
                    "modelName": MODEL_NAME,
                    "inOrderFields": FIELDS,
                    "css": CSS,
                    "isCloze": False,
                    "cardTemplates": CARD_TEMPLATES,
                },
            )
        else:
            if state["templates"] != template_mapping():
                self.client.mutate(
                    "updateModelTemplates",
                    {"model": {"name": MODEL_NAME, "templates": template_mapping()}},
                )
            if state["styling"].get("css", "") != CSS:
                self.client.mutate(
                    "updateModelStyling",
                    {"model": {"name": MODEL_NAME, "css": CSS}},
                )

    def ensure_options(self, protected: dict[str, dict[str, Any]]) -> dict[str, Any]:
        all_configs = self.all_deck_configs()
        target_config = all_configs.get(DECK_NAME)
        protected_ids = {
            int(snapshot["deck_config"]["id"])
            for snapshot in protected.values()
            if isinstance(snapshot.get("deck_config"), dict)
        }
        if target_config is None:
            raise ChinaKnowledgeSetupError("new deck did not inherit an options preset")
        target_config_id = int(target_config["id"])
        needs_clone = (
            target_config.get("name") != OPTIONS_PRESET_NAME
            or target_config_id in protected_ids
        )
        if needs_clone:
            conflicting_decks = [
                deck
                for deck, config in all_configs.items()
                if deck != DECK_NAME and config.get("name") == OPTIONS_PRESET_NAME
            ]
            if conflicting_decks:
                raise ChinaKnowledgeSetupError(
                    f"options preset name is already used by other decks: {conflicting_decks}"
                )
            config_id = int(
                self.client.mutate(
                    "cloneDeckConfigId",
                    {"name": OPTIONS_PRESET_NAME, "cloneFrom": target_config_id},
                )
            )
            assert self.client.guard is not None
            self.client.guard.register_target_config(config_id)
            if self.client.mutate(
                "setDeckConfigId",
                {"decks": [DECK_NAME], "configId": config_id},
            ) is not True:
                raise ChinaKnowledgeSetupError("failed to assign the dedicated options preset")
            config = self.client.read("getDeckConfig", {"deck": DECK_NAME})
        else:
            config = target_config
            assert self.client.guard is not None
            self.client.guard.register_target_config(int(config["id"]))
            shared = [
                deck
                for deck, other in all_configs.items()
                if deck != DECK_NAME and int(other.get("id", -1)) == int(config["id"])
            ]
            if shared:
                raise ChinaKnowledgeSetupError(f"dedicated options preset is shared by: {shared}")
        updated = copy.deepcopy(config)
        updated.setdefault("new", {})["perDay"] = NEW_CARDS_PER_DAY
        updated["name"] = OPTIONS_PRESET_NAME
        if updated != config:
            if self.client.mutate("saveDeckConfig", {"config": updated}) is not True:
                raise ChinaKnowledgeSetupError("failed to save the dedicated options preset")
        return self.client.read("getDeckConfig", {"deck": DECK_NAME})

    def write_backup(self, notes: list[dict[str, Any]]) -> None:
        if not notes:
            return
        path = self.reports_dir / BACKUP_TSV.name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["Anki Note ID", *FIELDS, "Anki Tags"],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            for note in sorted(notes, key=lambda item: note_field(item, "Knowledge ID")):
                writer.writerow(
                    {
                        "Anki Note ID": int(note["noteId"]),
                        **{field: note_field(note, field) for field in FIELDS},
                        "Anki Tags": " ".join(sorted(str(tag) for tag in note.get("tags", []))),
                    }
                )

    def ensure_notes(self, existing_notes: list[dict[str, Any]]) -> dict[str, Any]:
        existing_by_id = {note_field(note, "Knowledge ID"): note for note in existing_notes}
        self.write_backup(
            [note for knowledge_id, note in existing_by_id.items() if knowledge_id in self.rows_by_id]
        )
        created_ids: list[str] = []
        updated_ids: list[str] = []
        unchanged_ids: list[str] = []
        for row in self.rows:
            knowledge_id = row["Knowledge ID"]
            note = existing_by_id.get(knowledge_id)
            if note is None:
                continue
            changed = False
            desired_fields = self.row_fields(row)
            if any(note_field(note, field) != value for field, value in desired_fields.items()):
                self.client.mutate(
                    "updateNoteFields",
                    {"note": {"id": int(note["noteId"]), "fields": desired_fields}},
                )
                changed = True
            missing_tags = self.required_tags(row) - set(note.get("tags", []))
            if missing_tags:
                self.client.mutate(
                    "addTags",
                    {"notes": [int(note["noteId"])], "tags": " ".join(sorted(missing_tags))},
                )
                changed = True
            (updated_ids if changed else unchanged_ids).append(knowledge_id)

        new_rows = [row for row in self.rows if row["Knowledge ID"] not in existing_by_id]
        if new_rows:
            results = self.client.mutate(
                "addNotes",
                {
                    "notes": [
                        {
                            "deckName": DECK_NAME,
                            "modelName": MODEL_NAME,
                            "fields": self.row_fields(row),
                            "tags": sorted(self.required_tags(row)),
                            "options": {"allowDuplicate": False},
                        }
                        for row in new_rows
                    ]
                },
            )
            if len(results) != len(new_rows) or any(value is None for value in results):
                raise ChinaKnowledgeSetupError("addNotes did not create every requested note")
            created_ids = [row["Knowledge ID"] for row in new_rows]
            assert self.client.guard is not None
            self.client.guard.register_target_notes({int(value) for value in results})
        return {
            "created": len(created_ids),
            "updated": len(updated_ids),
            "skipped_unchanged": len(unchanged_ids),
            "rejected": 0,
            "created_ids": created_ids,
            "updated_ids": updated_ids,
            "unchanged_ids": unchanged_ids,
            "deleted": 0,
        }

    def verify_live(self) -> dict[str, Any]:
        state = self.inspect_target()
        errors: list[str] = []
        if not state["deck_exists"]:
            errors.append("dedicated deck does not exist")
        if not state["model_exists"]:
            errors.append("dedicated note type does not exist")
        if state["fields"] != FIELDS:
            errors.append("live field schema differs from the canonical schema")
        if set(state["templates"]) != {TEMPLATE_NAME} or len(state["templates"]) != 1:
            errors.append("live note type must have exactly one Knowledge Recognition template")
        template_text = canonical_json(state["templates"]) + str(state["styling"].get("css", ""))
        if MEDIA_OR_TTS_RE.search(template_text):
            errors.append("template or styling contains media/TTS rendering")
        notes_by_id = {note_field(note, "Knowledge ID"): note for note in state["notes"]}
        missing_ids = sorted(set(self.rows_by_id) - set(notes_by_id))
        if missing_ids:
            errors.append(f"source notes missing from live deck: {missing_ids[:10]}")
        mismatched_ids = [
            knowledge_id
            for knowledge_id, row in self.rows_by_id.items()
            if knowledge_id in notes_by_id
            and any(
                note_field(notes_by_id[knowledge_id], field) != value
                for field, value in self.row_fields(row).items()
            )
        ]
        if mismatched_ids:
            errors.append(f"live fields differ from source: {mismatched_ids[:10]}")
        source_note_ids = {
            int(notes_by_id[knowledge_id]["noteId"])
            for knowledge_id in self.rows_by_id
            if knowledge_id in notes_by_id
        }
        cards_by_note = Counter(int(card["note"]) for card in state["cards"])
        wrong_card_counts = sorted(
            note_id for note_id in source_note_ids if cards_by_note[note_id] != 1
        )
        if wrong_card_counts:
            errors.append(f"source notes without exactly one card: {wrong_card_counts[:10]}")
        source_cards = [card for card in state["cards"] if int(card["note"]) in source_note_ids]
        if any(int(card.get("ord", -1)) != 0 for card in source_cards):
            errors.append("a source note has a non-recognition template ordinal")
        config = state["config"] or {}
        if config.get("name") != OPTIONS_PRESET_NAME:
            errors.append("dedicated options preset is not assigned")
        if int(config.get("new", {}).get("perDay", -1)) != NEW_CARDS_PER_DAY:
            errors.append("new cards/day is not 5")
        protected_ids = {
            int(value["id"])
            for deck, _model in PROTECTED_RESOURCES
            for value in [self.client.read("getDeckConfig", {"deck": deck})]
            if isinstance(value, dict)
        }
        if config and int(config.get("id", -1)) in protected_ids:
            errors.append("dedicated deck shares a protected options preset")
        return {
            "status": "PASS" if not errors else "FAIL",
            "deck": DECK_NAME,
            "note_type": MODEL_NAME,
            "field_names": state["fields"],
            "template_names": list(state["templates"]),
            "template_count": len(state["templates"]),
            "source_note_count": len(self.rows),
            "live_note_count": len(state["notes"]),
            "live_source_note_count": len(source_note_ids),
            "out_of_source_live_note_count": len(set(notes_by_id) - set(self.rows_by_id)),
            "source_card_count": len(source_cards),
            "one_card_per_source_note": not wrong_card_counts,
            "new_cards_per_day": config.get("new", {}).get("perDay") if config else None,
            "options_preset": config.get("name"),
            "media_or_tts_rendering": bool(MEDIA_OR_TTS_RE.search(template_text)),
            "errors": errors,
        }

    def apply(self) -> dict[str, Any]:
        protected_before = self.protected_snapshots()
        guard = self.install_guard(protected_before)
        state = self.inspect_target()
        self.assert_compatible(state)
        guard.register_target_notes({int(note["noteId"]) for note in state["notes"]})
        plan = self.plan(state, protected_before)
        report: dict[str, Any] = {
            "status": "FAIL",
            "mode": "apply",
            "plan": plan,
            "protected_before_sha256": {
                deck: sha256_json(snapshot) for deck, snapshot in protected_before.items()
            },
        }
        try:
            self.ensure_deck_and_model(state)
            options = self.ensure_options(protected_before)
            note_changes = self.ensure_notes(state["notes"])
            protected_after = self.protected_snapshots()
            comparisons = {
                deck: {
                    "before_sha256": sha256_json(protected_before[deck]),
                    "after_sha256": sha256_json(protected_after[deck]),
                    "identical": protected_before[deck] == protected_after[deck],
                }
                for deck in protected_before
            }
            changed_protected = [deck for deck, item in comparisons.items() if not item["identical"]]
            if changed_protected:
                raise ChinaKnowledgeSetupError(
                    f"protected resources changed during apply: {changed_protected}"
                )
            verification = self.verify_live()
            if verification["status"] != "PASS":
                raise ChinaKnowledgeSetupError("; ".join(verification["errors"]))
            write_json(self.reports_dir / VERIFICATION_REPORT.name, verification)
            report.update(
                {
                    "status": "PASS",
                    "note_changes": note_changes,
                    "options_config_id": options.get("id"),
                    "new_cards_per_day": options.get("new", {}).get("perDay"),
                    "protected_comparisons": comparisons,
                    "verification": verification,
                    "mutation_log": self.client.mutation_log,
                }
            )
        except Exception as exc:
            report["error"] = str(exc)
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
            raise ChinaKnowledgeSetupError("; ".join(report["errors"]))
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
        description="Safely preview, create, update, or verify the isolated China Knowledge deck."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="Read live Anki and report proposed changes (default).")
    modes.add_argument("--offline-preview", action="store_true", help="Validate and preview an empty-deck install without contacting Anki.")
    modes.add_argument("--apply", action="store_true", help="Apply guarded China-Knowledge-only mutations.")
    modes.add_argument("--verify-only", action="store_true", help="Inspect the existing live resources without mutation.")
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
    reports_dir: Path = DEFAULT_REPORTS_DIR,
) -> dict[str, Any]:
    rows = load_validated_rows(
        tsv_path=tsv_path,
        sources_path=sources_path,
        validation_report=reports_dir / DATA_VALIDATION_REPORT.name,
    )
    manager = ChinaKnowledgeAnkiSetup(
        client=AnkiClient(url=url, transport=transport),
        rows=rows,
        reports_dir=reports_dir,
    )
    if mode == "offline-preview":
        return manager.offline_preview()
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
    mode = (
        "offline-preview"
        if args.offline_preview
        else "apply"
        if args.apply
        else "verify-only"
        if args.verify_only
        else "dry-run"
    )
    try:
        report = run(
            mode=mode,
            url=args.anki_connect_url,
            tsv_path=args.tsv,
            sources_path=args.sources,
        )
    except (
        AnkiConnectError,
        ChinaKnowledgeSetupError,
        MutationSafetyError,
        OSError,
        ValueError,
    ) as exc:
        report = {
            "status": "BLOCKED" if isinstance(exc, AnkiConnectError) else "FAIL",
            "mode": mode,
            "error": str(exc),
        }
        report_path = (
            OFFLINE_PREVIEW_REPORT
            if mode == "offline-preview"
            else APPLY_REPORT
            if mode == "apply"
            else VERIFICATION_REPORT
            if mode == "verify-only"
            else DRY_RUN_REPORT
        )
        if not report_path.exists() or mode != "apply":
            write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2 if isinstance(exc, AnkiConnectError) else 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
