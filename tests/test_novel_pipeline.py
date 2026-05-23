from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.novel_tools import (
    ROOT,
    build_epub,
    check_epub_structure,
    repeated_phrase_report,
    validate_book,
    validate_text,
    vocabulary_usage_report,
    write_json,
)
from scripts.run_quality_gate import init_quality_templates


class NovelPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.known = self.root / "known_words.txt"
        self.known.write_text("我\n你\n朋友\n看\n了\n在\n家里\n照片\n妈妈\n爸爸\n说\n好\n\n", encoding="utf-8")
        self.known_words = [line for line in self.known.read_text(encoding="utf-8").splitlines() if line]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def approve_quality(self, manuscript: Path) -> None:
        quality = manuscript / "quality"
        quality.mkdir(parents=True, exist_ok=True)
        (quality / "lead_quality_decision.md").write_text(
            "# Lead Quality Decision\n\nFinal decision: PASS\n",
            encoding="utf-8",
        )

    def test_allowed_single_character_chinese_word(self) -> None:
        report = validate_text("我 。", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["total_tokens"], 1)

    def test_allowed_multi_character_chinese_word(self) -> None:
        report = validate_text("朋友 在 家里 。", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["total_tokens"], 3)

    def test_unknown_chinese_word_detection(self) -> None:
        report = validate_text("猫 在 家里 。", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["unknown_token_frequency"], {"猫": 1})
        self.assertEqual(report["forbidden_unknown_tokens_over_limit"], 0)

    def test_punctuation_ignored(self) -> None:
        report = validate_text("我， 看 朋友!", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["total_tokens"], 3)

    def test_repeated_unknown_counts(self) -> None:
        report = validate_text("猫 猫 我", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["unknown_token_count"], 2)
        self.assertEqual(report["unknown_token_frequency"]["猫"], 2)

    def test_accidental_unsegmented_chinese_string_is_unknown(self) -> None:
        report = validate_text("我看你 。", self.known_words)
        self.assertTrue(report["valid"])
        self.assertEqual(report["unknown_token_frequency"], {"我看你": 1})

    def test_unknown_budget_failure_after_five_tokens(self) -> None:
        report = validate_text("猫 狗 鸟 鱼 马 龙 我", self.known_words)
        self.assertFalse(report["valid"])
        self.assertEqual(report["unknown_token_count"], 6)
        self.assertEqual(report["forbidden_unknown_tokens_over_limit"], 1)

    def test_chapter_validation_output_schema(self) -> None:
        report = validate_text("我 看 朋友 。", self.known_words)
        self.assertIn("valid", report)
        self.assertIn("total_tokens", report)
        self.assertIn("unique_token_count", report)
        self.assertIn("unknown_token_count", report)
        self.assertIn("violations", report)

    def test_book_validation_aggregation(self) -> None:
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 朋友 。\n", encoding="utf-8")
        (chapters / "chapter_02.zh-tok.txt").write_text("妈妈 说 好 。\n", encoding="utf-8")
        report = validate_book(chapters, self.known)
        self.assertTrue(report["valid"])
        self.assertEqual(report["chapter_count"], 2)
        self.assertEqual(report["total_tokens"], 6)
        self.assertEqual(report["unknown_token_count"], 0)

    def test_epub_file_exists_after_build(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 照片 。\n", encoding="utf-8")
        out = manuscript / "epub" / "sample.epub"
        self.approve_quality(manuscript)
        report = build_epub(manuscript, "Sample", out, known_path=self.known)
        self.assertTrue(out.exists())
        self.assertEqual(report["unknown_token_count"], 0)

    def test_epub_zip_structure_is_valid(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("爸爸 看 照片 。\n", encoding="utf-8")
        out = manuscript / "epub" / "sample.epub"
        self.approve_quality(manuscript)
        build_epub(manuscript, "Sample", out, known_path=self.known)
        structure = check_epub_structure(out)
        self.assertEqual(structure["first_entry"], "mimetype")
        self.assertEqual(structure["mimetype"], "application/epub+zip")
        self.assertTrue(structure["has_container"])
        self.assertTrue(structure["has_opf"])
        self.assertTrue(structure["has_nav"])
        self.assertTrue(structure["has_title_page"])
        self.assertEqual(structure["chapter_count"], 1)

    def test_failure_when_building_epub_from_invalid_manuscript(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("猫 狗 鸟 鱼 马 龙 看 照片 。\n", encoding="utf-8")
        out = manuscript / "epub" / "sample.epub"
        self.approve_quality(manuscript)
        with self.assertRaises(ValueError):
            build_epub(manuscript, "Sample", out, known_path=self.known)
        self.assertFalse(out.exists())

    def test_epub_refuses_manuscript_without_quality_approval(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 照片 。\n", encoding="utf-8")
        out = manuscript / "epub" / "sample.epub"
        with self.assertRaises(ValueError):
            build_epub(manuscript, "Sample", out, known_path=self.known)
        self.assertFalse(out.exists())

    def test_epub_succeeds_after_validation_and_quality_approval(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("妈妈 看 照片 。\n", encoding="utf-8")
        self.approve_quality(manuscript)
        out = manuscript / "epub" / "sample.epub"
        report = build_epub(manuscript, "Sample", out, known_path=self.known)
        self.assertTrue(out.exists())
        self.assertTrue(report["quality_approval"]["approved"])

    def test_json_report_can_be_written(self) -> None:
        report_path = self.root / "report.json"
        report = validate_text("我 看 朋友 。", self.known_words)
        write_json(report_path, report)
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(loaded["valid"])

    def test_vocabulary_usage_report_counts_unique_words(self) -> None:
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 朋友 。\n我 看 照片 。\n", encoding="utf-8")
        report = vocabulary_usage_report(chapters, self.known, min_chapter_unique_tokens=3)
        self.assertEqual(report["total_tokens"], 6)
        self.assertEqual(report["unique_token_count"], 4)
        self.assertEqual(report["unused_known_word_count"], len(self.known_words) - 4)

    def test_chapter_level_unique_token_counts_work(self) -> None:
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 朋友 。\n", encoding="utf-8")
        (chapters / "chapter_02.zh-tok.txt").write_text("妈妈 说 好 。\n", encoding="utf-8")
        report = vocabulary_usage_report(chapters, self.known, min_chapter_unique_tokens=3)
        counts = [chapter["unique_token_count"] for chapter in report["chapter_unique_token_counts"]]
        self.assertEqual(counts, [3, 3])

    def test_whole_book_known_list_coverage_percentage_works(self) -> None:
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "chapter_01.zh-tok.txt").write_text("我 你 朋友 看 了 在 。\n", encoding="utf-8")
        report = vocabulary_usage_report(chapters, self.known)
        self.assertEqual(report["known_word_coverage_percent"], 50.0)

    def test_repeated_phrase_detection_works(self) -> None:
        chapters = self.root / "chapters"
        chapters.mkdir()
        (chapters / "chapter_01.zh-tok.txt").write_text("我 看 照片 。\n我 看 照片 。\n我 看 照片 。\n", encoding="utf-8")
        report = repeated_phrase_report(chapters, min_count=3)
        phrases = {item["phrase"]: item["count"] for item in report["repeated_phrases"]}
        self.assertGreaterEqual(phrases["我 看"], 3)
        self.assertGreaterEqual(phrases["我 看 照片"], 3)

    def test_quality_directory_and_templates_are_created(self) -> None:
        quality = self.root / "manuscript" / "quality"
        init_quality_templates(quality)
        self.assertTrue((quality / "literary_critic_report.md").exists())
        self.assertTrue((quality / "normal_reader_report.md").exists())
        self.assertTrue((quality / "lead_quality_decision.md").exists())

    def test_deleted_bad_manuscripts_are_not_referenced_by_docs(self) -> None:
        docs = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "docs").glob("*.md"))
        forbidden = [
            "-".join(["hui", "jia", "de", "lu"]),
            "一个" + "长" + "故事",
            "long" + " reads",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, docs)

    def test_sample_pipeline_still_validates(self) -> None:
        sample = ROOT / "manuscripts" / "sample-known-words"
        report = validate_book(sample / "chapters", ROOT / "data" / "known_words.txt")
        self.assertTrue(report["valid"])
        self.assertEqual(report["unknown_token_count"], 0)


if __name__ == "__main__":
    unittest.main()
