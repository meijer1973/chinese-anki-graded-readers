from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.china_knowledge.config import CATEGORIES, DEFAULT_SOURCES, DEFAULT_TSV, FIELDS
from scripts.china_knowledge.validate_china_knowledge import (
    load_rows,
    render_import_payload,
    validate_dataset,
)


FIXTURE = Path(__file__).parent / "fixtures" / "china_knowledge_sample.tsv"


class ChinaKnowledgeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, cls.header, cls.raw_findings = load_rows(DEFAULT_TSV)

    def test_full_dataset_is_exactly_400_clean_rows(self) -> None:
        report = validate_dataset(tsv_path=DEFAULT_TSV, sources_path=DEFAULT_SOURCES)
        self.assertEqual("PASS", report["status"], report["errors"])
        self.assertEqual([], report["warnings"])
        self.assertEqual(400, report["total_notes"])
        self.assertEqual(CATEGORIES, report["notes_per_category"])
        self.assertEqual(400, report["notes_with_bilingual_explanations"])
        self.assertEqual(0, report["notes_missing_source_dates"])
        self.assertEqual(16, report["time_sensitive_notes"])

    def test_schema_ids_and_bilingual_fields_are_complete(self) -> None:
        self.assertEqual(FIELDS, self.header)
        self.assertEqual([], self.raw_findings)
        ids = [row["Knowledge ID"] for row in self.rows]
        self.assertEqual(400, len(set(ids)))
        for row in self.rows:
            for field in (
                "Chinese Question",
                "English Question",
                "Chinese Answer",
                "English Answer",
                "Chinese Explanation",
                "English Explanation",
            ):
                self.assertTrue(row[field], f"{row['Knowledge ID']} lacks {field}")

    def test_representative_fixture_covers_every_category(self) -> None:
        report = validate_dataset(
            tsv_path=FIXTURE,
            sources_path=DEFAULT_SOURCES,
            expected_count=16,
            category_targets={category: 2 for category in sorted(CATEGORIES)},
        )
        self.assertEqual("PASS", report["status"], report["errors"])
        self.assertEqual([], report["warnings"])

    def test_import_payload_is_deterministic_and_preserves_all_fields(self) -> None:
        forward = render_import_payload(self.rows)
        reverse = render_import_payload(list(reversed(self.rows)))
        self.assertEqual(forward, reverse)
        self.assertEqual(sorted(row["Knowledge ID"] for row in self.rows), [item["knowledge_id"] for item in forward])
        self.assertTrue(all(list(item["fields"]) == FIELDS for item in forward))

    def test_duplicate_id_is_a_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            duplicate = Path(tmp) / "duplicate.tsv"
            lines = FIXTURE.read_text(encoding="utf-8").splitlines()
            duplicate.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")
            report = validate_dataset(
                tsv_path=duplicate,
                sources_path=DEFAULT_SOURCES,
                expected_count=None,
                category_targets=None,
            )
        self.assertEqual("FAIL", report["status"])
        self.assertTrue(any("duplicate Knowledge IDs" in error for error in report["errors"]))

    def test_source_catalog_has_https_provenance(self) -> None:
        document = json.loads(DEFAULT_SOURCES.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(document["sources"]), 35)
        self.assertTrue(document["editorial_policy"])
        for source_id, source in document["sources"].items():
            self.assertTrue(source["url"].startswith("https://"), source_id)
            self.assertEqual("2026-08-06", source["checked_on"], source_id)


if __name__ == "__main__":
    unittest.main()
