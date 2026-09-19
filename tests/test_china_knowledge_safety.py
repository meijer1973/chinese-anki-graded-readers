from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.china_knowledge.anki_client import (
    AnkiClient,
    MutationGuard,
    MutationSafetyError,
)
from scripts.china_knowledge.setup_china_knowledge_anki import (
    ChinaKnowledgeAnkiSetup,
    ChinaKnowledgeSetupError,
)
from scripts.china_knowledge.validate_china_knowledge import DEFAULT_TSV, load_rows
from tests.china_knowledge_fake_anki import FakeAnki


class ChinaKnowledgeSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, _header, _findings = load_rows(DEFAULT_TSV)

    def make_manager(self, fake: FakeAnki, path: Path) -> ChinaKnowledgeAnkiSetup:
        return ChinaKnowledgeAnkiSetup(
            client=AnkiClient(transport=fake),
            rows=copy.deepcopy(self.rows),
            reports_dir=path,
        )

    def test_default_hindi_and_spanish_resources_are_byte_for_byte_equivalent(self) -> None:
        fake = FakeAnki()
        before = fake.snapshot_protected()
        with tempfile.TemporaryDirectory() as tmp:
            report = self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual(before, fake.snapshot_protected())
        self.assertTrue(all(item["identical"] for item in report["protected_comparisons"].values()))

    def test_incompatible_target_deck_aborts_before_mutation(self) -> None:
        fake = FakeAnki()
        fake.add_incompatible_china_note()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ChinaKnowledgeSetupError):
                self.make_manager(fake, Path(tmp)).apply()
        self.assertEqual([], fake.mutation_calls)

    def test_guard_rejects_mutations_outside_target_namespace(self) -> None:
        guard = MutationGuard(
            target_deck="China Knowledge",
            target_model="China Knowledge Bilingual",
            target_preset="China Knowledge - 5 new cards",
            protected_note_ids={10, 11, 12},
            protected_card_ids={20, 21, 22},
            protected_config_ids={1, 2, 3},
            target_note_ids={1000},
            target_config_ids={4},
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
            client.mutate(
                "updateNoteFields",
                {"note": {"id": 10, "fields": {"Word": "bad"}}},
            )
        with self.assertRaises(MutationSafetyError):
            client.mutate("setDeckConfigId", {"decks": ["China Knowledge"], "configId": 1})


if __name__ == "__main__":
    unittest.main()
