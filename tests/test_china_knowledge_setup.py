from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.china_knowledge.anki_client import AnkiClient
from scripts.china_knowledge.config import DECK_NAME, MODEL_NAME, OPTIONS_PRESET_NAME
from scripts.china_knowledge.setup_china_knowledge_anki import ChinaKnowledgeAnkiSetup
from scripts.china_knowledge.validate_china_knowledge import DEFAULT_TSV, load_rows
from tests.china_knowledge_fake_anki import FakeAnki


class ChinaKnowledgeSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, _header, _findings = load_rows(DEFAULT_TSV)

    def make_manager(self, fake: FakeAnki, path: Path) -> ChinaKnowledgeAnkiSetup:
        return ChinaKnowledgeAnkiSetup(
            client=AnkiClient(transport=fake),
            rows=copy.deepcopy(self.rows),
            reports_dir=path,
        )

    def test_offline_preview_and_live_dry_run_perform_no_mutations(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            manager = self.make_manager(fake, Path(tmp))
            offline = manager.offline_preview()
            dry_run = manager.dry_run()
        self.assertEqual(400, offline["would_create"])
        self.assertEqual(400, dry_run["plan"]["would_create"])
        self.assertEqual(0, dry_run["mutations_performed"])
        self.assertEqual([], fake.mutation_calls)

    def test_apply_creates_exactly_400_notes_and_cards(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual("PASS", report["status"])
        verification = report["verification"]
        self.assertEqual(400, verification["source_note_count"])
        self.assertEqual(400, verification["live_source_note_count"])
        self.assertEqual(400, verification["source_card_count"])
        self.assertTrue(verification["one_card_per_source_note"])
        self.assertEqual(1, verification["template_count"])
        self.assertEqual(5, verification["new_cards_per_day"])
        self.assertEqual(OPTIONS_PRESET_NAME, verification["options_preset"])
        self.assertIn(DECK_NAME, fake.decks)
        self.assertIn(MODEL_NAME, fake.models)

    def test_second_apply_is_idempotent(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            self.make_manager(fake, Path(tmp)).apply()
            notes_before = sorted(
                note_id for note_id, note in fake.notes.items() if note["deckName"] == DECK_NAME
            )
            cards_before = sorted(
                card_id for card_id, card in fake.cards.items() if card["deckName"] == DECK_NAME
            )
            second = self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual(0, second["note_changes"]["created"])
        self.assertEqual(0, second["note_changes"]["updated"])
        self.assertEqual(400, second["note_changes"]["skipped_unchanged"])
        self.assertEqual(
            notes_before,
            sorted(note_id for note_id, note in fake.notes.items() if note["deckName"] == DECK_NAME),
        )
        self.assertEqual(
            cards_before,
            sorted(card_id for card_id, card in fake.cards.items() if card["deckName"] == DECK_NAME),
        )

    def test_stable_id_update_preserves_card_history(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            self.make_manager(fake, Path(tmp)).apply()
            target = next(
                note
                for note in fake.notes.values()
                if note["deckName"] == DECK_NAME
                and note["fields"]["Knowledge ID"]["value"] == "geo-overview-001"
            )
            note_id = target["noteId"]
            card_id = target["cards"][0]
            target["fields"]["Chinese Explanation"]["value"] = "过期内容"
            fake.cards[card_id].update({"type": 2, "queue": 2, "reps": 9, "interval": 17})
            report = self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual(1, report["note_changes"]["updated"])
        self.assertEqual(note_id, fake.notes[note_id]["noteId"])
        self.assertEqual([card_id], fake.notes[note_id]["cards"])
        self.assertEqual(9, fake.cards[card_id]["reps"])
        self.assertEqual(17, fake.cards[card_id]["interval"])

    def test_dedicated_options_clone_changes_only_name_id_and_new_limit(self) -> None:
        fake = FakeAnki()
        inherited = copy.deepcopy(fake.configs[1])
        with tempfile.TemporaryDirectory() as tmp:
            self.make_manager(fake, Path(tmp)).apply()
        target_id = fake.deck_config_ids[DECK_NAME]
        target = copy.deepcopy(fake.configs[target_id])
        self.assertNotIn(target_id, {1, 2, 3})
        self.assertEqual(OPTIONS_PRESET_NAME, target["name"])
        self.assertEqual(5, target["new"]["perDay"])
        target["id"] = inherited["id"]
        target["name"] = inherited["name"]
        target["new"]["perDay"] = inherited["new"]["perDay"]
        self.assertEqual(inherited, target)


if __name__ == "__main__":
    unittest.main()
