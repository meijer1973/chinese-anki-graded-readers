from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.export_stretch_words_for_anki import FIELDS, export_candidates
from scripts.novel_tools import (
    GENERAL_FICTION_LAYER,
    GENRE_LAYER,
    PROFESSION_LAYER,
    ROOT,
    SETTING_LAYER,
    build_epub,
    check_epub_structure,
    load_layered_vocabulary,
    validate_book,
    validate_text,
)


class StretchVocabularyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.known = self.root / "known_words.txt"
        self.known.write_text("我\n你\n在\n看\n是\n了\n说\n好\n\n", encoding="utf-8")
        self.general = self.root / "general.txt"
        self.genre = self.root / "low_fantasy.txt"
        self.setting = self.root / "shanghai_setting.txt"
        self.profession = self.root / "professions.txt"
        self.urban = self.root / "urban_objects.txt"
        self.general.write_text("沉默\n我\n", encoding="utf-8")
        self.genre.write_text("魔法\n", encoding="utf-8")
        self.setting.write_text("上海\n", encoding="utf-8")
        self.profession.write_text("快递员\n", encoding="utf-8")
        self.urban.write_text("地图\n", encoding="utf-8")
        self.proper = self.root / "proper_nouns.txt"
        self.proper.write_text("林安\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def chapters_dir(self, *chapter_texts: str) -> Path:
        chapters = self.root / "chapters"
        chapters.mkdir(exist_ok=True)
        for index, text in enumerate(chapter_texts, start=1):
            (chapters / f"chapter_{index:02d}.zh-tok.txt").write_text(text, encoding="utf-8")
        return chapters

    def layered_kwargs(self) -> dict:
        return {
            "general_fiction_pack": self.general,
            "genre_pack": self.genre,
            "setting_pack": self.setting,
            "profession_pack": self.profession,
            "urban_objects_pack": self.urban,
            "proper_nouns_path": self.proper,
        }

    def approve_quality(self, manuscript: Path) -> None:
        quality = manuscript / "quality"
        quality.mkdir(parents=True, exist_ok=True)
        (quality / "lead_quality_decision.md").write_text("Final decision: PASS\n", encoding="utf-8")

    def test_core_only_validation_passes(self) -> None:
        report = validate_text("我 在 看 你 。", ["我", "在", "看", "你"])
        self.assertTrue(report["valid"])
        self.assertEqual(report["forbidden_unknown_tokens"], 0)

    def test_approved_stretch_word_passes(self) -> None:
        chapters = self.chapters_dir("我 看 魔法 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertTrue(report["valid"])
        self.assertEqual(report["genre_stretch_tokens"], 1)

    def test_forbidden_unknown_word_fails(self) -> None:
        chapters = self.chapters_dir("我 看 龙 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertTrue(report["valid"])
        self.assertEqual(report["forbidden_unknown_tokens"], 1)
        self.assertEqual(report["forbidden_unknown_tokens_over_limit"], 0)

    def test_forbidden_unknown_word_over_budget_fails(self) -> None:
        chapters = self.chapters_dir("我 看 龙 猫 狗 鸟 鱼 马 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertFalse(report["valid"])
        self.assertEqual(report["forbidden_unknown_tokens"], 6)
        self.assertEqual(report["forbidden_unknown_tokens_over_limit"], 1)

    def test_same_token_in_core_and_stretch_counts_as_core(self) -> None:
        chapters = self.chapters_dir("我 看 你 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertEqual(report["core_known_tokens"], 3)
        self.assertEqual(report["general_fiction_stretch_tokens"], 0)

    def test_proper_noun_passes_only_when_listed(self) -> None:
        chapters = self.chapters_dir("林安 看 你 。\n")
        allowed = validate_book(chapters, self.known, **self.layered_kwargs())
        blocked = validate_book(chapters, self.known)
        self.assertTrue(allowed["valid"])
        self.assertEqual(allowed["proper_noun_tokens"], 1)
        self.assertTrue(blocked["valid"])
        self.assertEqual(blocked["proper_noun_tokens"], 0)
        self.assertEqual(blocked["forbidden_unknown_tokens"], 1)

    def test_shanghai_setting_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", setting_pack=ROOT / "data" / "stretch_packs" / "shanghai_setting_150.txt")
        self.assertEqual(vocab["token_layers"]["上海"], SETTING_LAYER)

    def test_low_fantasy_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", genre_pack=ROOT / "data" / "stretch_packs" / "low_fantasy_150.txt")
        self.assertEqual(vocab["token_layers"]["魔法"], GENRE_LAYER)

    def test_profession_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", profession_pack=ROOT / "data" / "stretch_packs" / "professions_social_roles_100.txt")
        self.assertEqual(vocab["token_layers"]["快递员"], PROFESSION_LAYER)

    def test_layer_counts_are_correct(self) -> None:
        chapters = self.chapters_dir("林安 是 快递员 。\n我 在 上海 看 魔法 。\n你 沉默 了 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertEqual(report["core_known_tokens"], 6)
        self.assertEqual(report["general_fiction_stretch_tokens"], 1)
        self.assertEqual(report["genre_stretch_tokens"], 1)
        self.assertEqual(report["setting_stretch_tokens"], 1)
        self.assertEqual(report["profession_stretch_tokens"], 1)
        self.assertEqual(report["proper_noun_tokens"], 1)

    def test_stretch_token_percentage_is_calculated(self) -> None:
        chapters = self.chapters_dir("林安 是 快递员 。\n我 在 上海 看 魔法 。\n你 沉默 了 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertAlmostEqual(report["stretch_token_percent"], 45.45, places=2)

    def test_new_stretch_words_per_chapter_are_counted(self) -> None:
        chapters = self.chapters_dir("我 看 魔法 。\n", "我 在 上海 看 魔法 。\n你 沉默 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertEqual(report["new_stretch_words_by_chapter"]["chapter_01.zh-tok.txt"], ["魔法"])
        self.assertEqual(report["new_stretch_words_by_chapter"]["chapter_02.zh-tok.txt"], ["上海", "沉默"])

    def test_stretch_words_used_once_are_warned(self) -> None:
        chapters = self.chapters_dir("我 看 魔法 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertIn("魔法", report["stretch_words_used_once"])
        self.assertTrue(any(warning["type"] == "stretch_words_used_once" for warning in report["warnings"]))

    def test_anki_candidate_export_excludes_known_core_words(self) -> None:
        out = self.root / "candidates.tsv"
        report = export_candidates([self.general], core_path=self.known, out_path=out)
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual([row["Hanzi"] for row in rows], ["沉默"])
        self.assertEqual(report["excluded_core_count"], 1)

    def test_anki_candidate_export_avoids_duplicates(self) -> None:
        dup = self.root / "duplicate.txt"
        dup.write_text("魔法\n沉默\n", encoding="utf-8")
        out = self.root / "candidates.tsv"
        export_candidates([self.genre, dup, self.general], core_path=self.known, out_path=out)
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual([row["Hanzi"] for row in rows].count("魔法"), 1)

    def test_anki_candidate_export_includes_required_fields(self) -> None:
        out = self.root / "candidates.tsv"
        export_candidates([self.genre], core_path=self.known, out_path=out)
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual(set(rows[0]), set(FIELDS))

    def test_layered_epub_requires_validation_and_quality_approval(self) -> None:
        manuscript = self.root / "manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text("林安 看 魔法 。\n", encoding="utf-8")
        out = manuscript / "epub" / "sample.epub"
        with self.assertRaises(ValueError):
            build_epub(manuscript, "Sample", out, known_path=self.known, **self.layered_kwargs())

        self.approve_quality(manuscript)
        report = build_epub(manuscript, "Sample", out, known_path=self.known, **self.layered_kwargs())
        self.assertTrue(out.exists())
        self.assertEqual(report["unknown_token_count"], 0)
        self.assertEqual(check_epub_structure(out)["chapter_count"], 1)


if __name__ == "__main__":
    unittest.main()
