from __future__ import annotations

import json
import unittest

from scripts.hindi.validate_hindi_core_100 import (
    DEFAULT_SOURCES,
    DEFAULT_TSV,
    REQUIRED_NONEMPTY_FIELDS,
    load_rows,
    validate_dataset,
)


class HindiCore100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, cls.header, cls.raw_findings = load_rows(DEFAULT_TSV)

    def test_dataset_is_exactly_100_unique_valid_rows(self) -> None:
        report = validate_dataset(tsv_path=DEFAULT_TSV, sources_path=DEFAULT_SOURCES)
        self.assertEqual("PASS", report["status"], report["errors"])
        self.assertEqual(100, report["row_count"])
        self.assertEqual(100, report["unique_word_count"])
        self.assertEqual({str(value) for value in range(4, 10)}, set(report["sentence_length_distribution"]))

    def test_ranks_are_complete_and_unique(self) -> None:
        ranks = [int(row["Frequency Rank"]) for row in self.rows]
        self.assertEqual(list(range(1, 101)), sorted(ranks))

    def test_every_exact_word_occurs_in_its_example(self) -> None:
        missing = [row["Word"] for row in self.rows if row["Word"] not in row["Example"]]
        self.assertEqual([], missing)

    def test_required_pronunciation_meaning_and_example_fields_are_populated(self) -> None:
        for row in self.rows:
            for field in REQUIRED_NONEMPTY_FIELDS:
                self.assertTrue(row[field], f"{row['Word']} has empty {field}")

    def test_source_metadata_records_provenance_and_editorial_independence(self) -> None:
        metadata = json.loads(DEFAULT_SOURCES.read_text(encoding="utf-8"))
        self.assertEqual("2026-07-22", metadata["access_date"])
        self.assertIn("OSF xfbhd", metadata["dataset_or_project_identifier"])
        self.assertTrue(metadata["editorial_content_independently_written"])
        self.assertGreaterEqual(len(metadata["selection_procedure"]), 6)
        self.assertGreaterEqual(len(metadata["exclusions"]), 8)


if __name__ == "__main__":
    unittest.main()
