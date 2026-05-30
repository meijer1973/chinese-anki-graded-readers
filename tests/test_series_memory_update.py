from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_series_memory_update import build_series_memory_status


class SeriesMemoryUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manuscript = self.root / "manuscripts" / "sample-case"
        self.series = self.root / "series" / "an-lin"
        self.manuscript.mkdir(parents=True)
        (self.manuscript / "quality").mkdir()
        self.series.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_minimum_manuscript_files(self, *, lead_decision: str = "PASS") -> None:
        (self.manuscript / "novel_bible.md").write_text("# Bible\n", encoding="utf-8")
        (self.manuscript / "outline.md").write_text("# Outline\n", encoding="utf-8")
        (self.manuscript / "continuity_log.md").write_text("# Continuity\n", encoding="utf-8")
        (self.manuscript / "quality" / "lead_quality_decision.md").write_text(
            f"# Lead Quality Decision\n\nFinal decision: {lead_decision}\n",
            encoding="utf-8",
        )

    def write_minimum_series_files(self, *, mention_slug: bool = True) -> None:
        slug_text = "sample-case" if mention_slug else "other-case"
        (self.series / "series_bible.md").write_text("# Bible\n", encoding="utf-8")
        (self.series / "chronology.md").write_text(f"# Chronology\n\n- manuscripts/{slug_text}/\n", encoding="utf-8")
        (self.series / "character_registry.md").write_text("# Characters\n", encoding="utf-8")
        (self.series / "mechanism_registry.md").write_text("# Mechanisms\n", encoding="utf-8")
        (self.series / "open_threads.md").write_text("# Open Threads\n", encoding="utf-8")
        (self.series / "sequel_constraints.md").write_text("# Constraints\n", encoding="utf-8")
        (self.series / "series_update_log.md").write_text(
            f"# Update Log\n\n## 2026-05-30 - {slug_text}\n",
            encoding="utf-8",
        )

    def test_series_memory_update_passes_when_required_files_and_mentions_exist(self) -> None:
        self.write_minimum_manuscript_files()
        self.write_minimum_series_files()
        status = build_series_memory_status(self.manuscript, self.series)
        self.assertTrue(status["series_memory_update_complete"])
        self.assertEqual(status["blocking_reasons"], [])

    def test_series_memory_update_fails_without_update_log_entry(self) -> None:
        self.write_minimum_manuscript_files()
        self.write_minimum_series_files(mention_slug=False)
        status = build_series_memory_status(self.manuscript, self.series)
        self.assertFalse(status["series_memory_update_complete"])
        self.assertIn("chronology does not mention the manuscript", status["blocking_reasons"])
        self.assertIn("series_update_log does not mention the manuscript", status["blocking_reasons"])

    def test_series_memory_update_can_require_epub_build(self) -> None:
        self.write_minimum_manuscript_files()
        self.write_minimum_series_files()
        missing_epub = build_series_memory_status(self.manuscript, self.series, require_epub_build=True)
        self.assertFalse(missing_epub["series_memory_update_complete"])
        self.assertIn("EPUB build success was required but not found", missing_epub["blocking_reasons"])

        epub_dir = self.manuscript / "epub"
        epub_dir.mkdir()
        (epub_dir / "sample-case.epub").write_bytes(b"placeholder")
        present_epub = build_series_memory_status(self.manuscript, self.series, require_epub_build=True)
        self.assertTrue(present_epub["series_memory_update_complete"])


if __name__ == "__main__":
    unittest.main()
