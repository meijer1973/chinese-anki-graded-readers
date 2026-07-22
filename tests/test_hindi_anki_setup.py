from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from hindi_fake_anki import FakeAnki
from scripts.hindi.anki_client import AnkiClient
from scripts.hindi.setup_hindi_anki import (
    DECK_NAME,
    MODEL_NAME,
    OPTIONS_PRESET_NAME,
    HindiAnkiSetup,
)
from scripts.hindi.validate_hindi_core_100 import DEFAULT_TSV, load_rows


class HindiAnkiSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, _header, _findings = load_rows(DEFAULT_TSV)

    def make_manager(self, fake: FakeAnki, reports_dir: Path) -> HindiAnkiSetup:
        return HindiAnkiSetup(
            client=AnkiClient(transport=fake),
            rows=copy.deepcopy(self.rows),
            reports_dir=reports_dir,
        )

    def test_dry_run_performs_no_mutations(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).dry_run()
        self.assertEqual("PASS", report["status"])
        self.assertEqual(0, report["mutations_performed"])
        self.assertEqual([], fake.mutation_calls)

    def test_apply_creates_exact_counts_and_targets_hindi_only(self) -> None:
        fake = FakeAnki()
        original_chinese_note = copy.deepcopy(fake.notes[10])
        original_chinese_card = copy.deepcopy(fake.cards[20])
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual("PASS", report["status"])
        verification = report["verification"]
        self.assertEqual(100, verification["managed_note_count"])
        self.assertEqual(100, verification["word_recognition_cards"])
        self.assertEqual(100, verification["sentence_recognition_cards"])
        self.assertEqual(200, verification["total_cards"])
        self.assertEqual(0, verification["production_cards"])
        self.assertEqual(original_chinese_note, fake.notes[10])
        self.assertEqual(original_chinese_card, fake.cards[20])
        self.assertIn(DECK_NAME, fake.decks)
        self.assertIn(MODEL_NAME, fake.models)

    def test_second_apply_creates_no_duplicates(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            first = self.make_manager(fake, Path(tmp)).apply()
            note_ids = sorted(note_id for note_id, note in fake.notes.items() if note["deckName"] == DECK_NAME)
            card_ids = sorted(card_id for card_id, card in fake.cards.items() if card["deckName"] == DECK_NAME)
            second = self.make_manager(fake, Path(tmp)).apply()
            note_ids_after = sorted(note_id for note_id, note in fake.notes.items() if note["deckName"] == DECK_NAME)
            card_ids_after = sorted(card_id for card_id, card in fake.cards.items() if card["deckName"] == DECK_NAME)
        self.assertEqual(100, first["verification"]["managed_note_count"])
        self.assertEqual(0, second["note_changes"]["added"])
        self.assertEqual(note_ids, note_ids_after)
        self.assertEqual(card_ids, card_ids_after)

    def test_existing_compatible_note_updates_fields_without_replacing_cards(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            self.make_manager(fake, Path(tmp)).apply()
            hindi_notes = [note for note in fake.notes.values() if note["deckName"] == DECK_NAME]
            target = next(note for note in hindi_notes if note["fields"]["Word"]["value"] == "पानी")
            original_note_id = target["noteId"]
            original_card_ids = list(target["cards"])
            target["fields"]["Pronunciation"]["value"] = "wrong"
            reviewed_card = fake.cards[original_card_ids[0]]
            reviewed_card.update({"type": 2, "queue": 2, "reps": 7, "interval": 12})
            report = self.make_manager(fake, Path(tmp)).apply()
        updated = fake.notes[original_note_id]
        self.assertEqual("pānī", updated["fields"]["Pronunciation"]["value"])
        self.assertEqual(original_card_ids, updated["cards"])
        self.assertEqual(7, fake.cards[original_card_ids[0]]["reps"])
        self.assertEqual(12, fake.cards[original_card_ids[0]]["interval"])
        self.assertEqual(1, report["note_changes"]["updated"])

    def test_options_preset_is_cloned_with_only_required_behavior_changes(self) -> None:
        fake = FakeAnki()
        default_before = copy.deepcopy(fake.configs[1])
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).apply()
        hindi_config_id = fake.deck_config_ids[DECK_NAME]
        hindi = fake.configs[hindi_config_id]
        self.assertNotEqual(1, hindi_config_id)
        self.assertEqual(OPTIONS_PRESET_NAME, hindi["name"])
        self.assertEqual(5, hindi["new"]["perDay"])
        self.assertEqual(1, hindi["newSortOrder"])
        self.assertEqual(0, hindi["newGatherPriority"])
        self.assertEqual(default_before, fake.configs[1])
        self.assertEqual(default_before["new"]["order"], hindi["new"]["order"])
        self.assertEqual(default_before["rev"], hindi["rev"])
        self.assertEqual(default_before["lapse"], hindi["lapse"])
        self.assertEqual(["new.perDay", "newSortOrder"], report["hindi_only_option_keys_changed"])

    def test_card_order_is_deterministic_by_rank_then_template(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).apply()
        self.assertTrue(report["verification"]["card_order_ok"])
        cards = [card for card in fake.cards.values() if card["deckName"] == DECK_NAME]
        ordered = sorted(cards, key=lambda card: (card["due"], card["cardId"]))
        self.assertEqual([0, 1, 0, 1, 0, 1], [card["ord"] for card in ordered[:6]])


if __name__ == "__main__":
    unittest.main()
