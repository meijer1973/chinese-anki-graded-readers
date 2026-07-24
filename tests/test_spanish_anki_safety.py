from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tests.spanish_fake_anki import FakeAnki
from scripts.spanish.anki_client import AnkiClient, MutationGuard, MutationSafetyError
from scripts.spanish.setup_spanish_anki import SpanishAnkiSetup, SpanishSetupError
from scripts.spanish.validate_spanish_core_100 import DEFAULT_TSV, load_rows


class SpanishAnkiSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, _header, _findings = load_rows(DEFAULT_TSV)

    def make_manager(self, fake: FakeAnki, path: Path) -> SpanishAnkiSetup:
        return SpanishAnkiSetup(
            client=AnkiClient(transport=fake),
            rows=copy.deepcopy(self.rows),
            reports_dir=path,
        )

    def test_incompatible_spanish_content_causes_safe_failure(self) -> None:
        fake = FakeAnki()
        fake.add_incompatible_spanish_note()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SpanishSetupError):
                self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual([], fake.mutation_calls)

    def test_chinese_snapshot_is_identical_before_and_after(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            manager = self.make_manager(fake, Path(tmp))
            before = manager.chinese_snapshot()
            report = manager.apply()
            after = manager.chinese_snapshot()
        self.assertEqual(before, after)
        self.assertTrue(report["chinese_safety_identical"])
        self.assertEqual(report["chinese_safety_before_sha256"], report["chinese_safety_after_sha256"])

    def test_hindi_snapshot_is_identical_before_and_after(self) -> None:
        fake = FakeAnki()
        with tempfile.TemporaryDirectory() as tmp:
            manager = self.make_manager(fake, Path(tmp))
            before = manager.hindi_snapshot()
            report = manager.apply()
            after = manager.hindi_snapshot()
        self.assertEqual(before, after)
        self.assertTrue(report["hindi_safety_identical"])
        self.assertEqual(
            report["hindi_safety_before_sha256"],
            report["hindi_safety_after_sha256"],
        )

    def test_any_attempted_chinese_or_hindi_mutation_fails_immediately(self) -> None:
        guard = MutationGuard(
            spanish_deck="Spanish",
            spanish_model="Spanish Vocabulary",
            spanish_preset="Spanish - 5 new cards",
            protected_decks={"Default", "Hindi"},
            protected_models={"Chinese Vocabulary", "Hindi Vocabulary"},
            protected_note_ids={10, 11},
            protected_card_ids={20, 21},
            protected_config_ids={1, 2},
            spanish_note_ids={1000},
            spanish_card_ids={2000},
            spanish_config_ids={3},
        )
        client = AnkiClient(transport=FakeAnki(), guard=guard)
        with self.assertRaises(MutationSafetyError):
            client.mutate("createDeck", {"deck": "Default"})
        with self.assertRaises(MutationSafetyError):
            client.mutate(
                "updateModelStyling",
                {"model": {"name": "Chinese Vocabulary", "css": "bad"}},
            )
        with self.assertRaises(MutationSafetyError):
            client.mutate("updateNoteFields", {"note": {"id": 10, "fields": {"Word": "bad"}}})
        with self.assertRaises(MutationSafetyError):
            client.mutate("reposition", {"cards": [20]})
        with self.assertRaises(MutationSafetyError):
            client.mutate("setDeckConfigId", {"decks": ["Spanish"], "configId": 1})
        with self.assertRaises(MutationSafetyError):
            client.mutate("updateNoteFields", {"note": {"id": 11, "fields": {"Word": "bad"}}})
        with self.assertRaises(MutationSafetyError):
            client.mutate("reposition", {"cards": [21]})
        with self.assertRaises(MutationSafetyError):
            client.mutate("setDeckConfigId", {"decks": ["Spanish"], "configId": 2})


if __name__ == "__main__":
    unittest.main()
