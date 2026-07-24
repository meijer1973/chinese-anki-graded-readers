from __future__ import annotations

import json
import unittest

from scripts.spanish.validate_spanish_core_100 import (
    DEFAULT_SOURCES,
    DEFAULT_TSV,
    REQUIRED_NONEMPTY_FIELDS,
    load_rows,
    validate_dataset,
)


class SpanishCore100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, cls.header, cls.raw_findings = load_rows(DEFAULT_TSV)

    def test_dataset_is_exactly_100_unique_valid_rows(self) -> None:
        report = validate_dataset(tsv_path=DEFAULT_TSV, sources_path=DEFAULT_SOURCES)
        self.assertEqual("PASS", report["status"], report["errors"])
        self.assertEqual(100, report["row_count"])
        self.assertEqual(100, report["unique_word_count"])
        self.assertTrue(
            all(4 <= int(length) <= 12 for length in report["sentence_length_distribution"])
        )

    def test_ranks_are_complete_and_unique(self) -> None:
        ranks = [int(row["Frequency Rank"]) for row in self.rows]
        self.assertEqual(list(range(1, 101)), sorted(ranks))

    def test_every_exact_word_occurs_in_its_example(self) -> None:
        missing = [row["Word"] for row in self.rows if row["Word"] not in row["Example"]]
        self.assertEqual([], missing)

    def test_required_ipa_meaning_and_example_fields_are_populated(self) -> None:
        for row in self.rows:
            for field in REQUIRED_NONEMPTY_FIELDS:
                self.assertTrue(row[field], f"{row['Word']} has empty {field}")

    def test_source_metadata_records_provenance_and_editorial_independence(self) -> None:
        metadata = json.loads(DEFAULT_SOURCES.read_text(encoding="utf-8"))
        self.assertEqual("2026-07-24", metadata["access_date"])
        self.assertIn("SUBTLEX-ESP", metadata["dataset_or_project_identifier"])
        self.assertEqual(3, len(metadata["sources"]))
        self.assertTrue(metadata["editorial_content_independently_written"])
        self.assertEqual(200, metadata["selection_procedure"]["candidate_count_reviewed"])
        self.assertGreaterEqual(len(metadata["selection_procedure"]["filters"]), 5)
        self.assertGreaterEqual(len(metadata["exclusions"]["classes"]), 5)


if __name__ == "__main__":
    unittest.main()
