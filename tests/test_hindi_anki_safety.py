from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from hindi_fake_anki import FakeAnki
from scripts.hindi.anki_client import AnkiClient, MutationGuard, MutationSafetyError
from scripts.hindi.setup_hindi_anki import HindiAnkiSetup, HindiSetupError
from scripts.hindi.validate_hindi_core_100 import DEFAULT_TSV, load_rows


class HindiAnkiSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, _header, _findings = load_rows(DEFAULT_TSV)

    def make_manager(self, fake: FakeAnki, path: Path) -> HindiAnkiSetup:
        return HindiAnkiSetup(
            client=AnkiClient(transport=fake),
            rows=copy.deepcopy(self.rows),
            reports_dir=path,
        )

    def test_incompatible_hindi_content_causes_safe_failure(self) -> None:
        fake = FakeAnki()
        fake.add_incompatible_hindi_note()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(HindiSetupError):
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

    def test_any_attempted_chinese_mutation_fails_immediately(self) -> None:
        guard = MutationGuard(
            hindi_deck="Hindi",
            hindi_model="Hindi Vocabulary",
            hindi_preset="Hindi - 5 new cards",
            protected_deck="Default",
            protected_model="Chinese Vocabulary",
            protected_note_ids={10},
            protected_card_ids={20},
            protected_config_ids={1},
            hindi_note_ids={1000},
            hindi_card_ids={2000},
            hindi_config_ids={2},
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
            client.mutate("setDeckConfigId", {"decks": ["Hindi"], "configId": 1})


if __name__ == "__main__":
    unittest.main()
