from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.export_stretch_words_for_anki import FIELDS, export_candidates
from scripts.novel_tools import (
    BUSINESS_ECONOMICS_LAYER,
    DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    GENERAL_FICTION_LAYER,
    GENRE_LAYER,
    JOURNALISM_CRIME_LAYER,
    PERSONAL_KNOWN_LAYER,
    PROFESSION_LAYER,
    ROOT,
    SETTING_LAYER,
    build_epub,
    check_epub_structure,
    is_known_character_compound,
    load_known_words,
    load_layered_vocabulary,
    load_optional_words,
    load_ranked_characters,
    validate_book,
    validate_text,
)
from scripts.sync_personal_known_words import sync_personal_known_words


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
        self.journalism = self.root / "journalism_crime.txt"
        self.urban = self.root / "urban_objects.txt"
        self.personal = self.root / "personal_known_words.txt"
        self.high_frequency_characters = self.root / "high_frequency_characters.txt"
        self.general.write_text("沉默\n我\n", encoding="utf-8")
        self.genre.write_text("魔法\n", encoding="utf-8")
        self.setting.write_text("上海\n", encoding="utf-8")
        self.profession.write_text("快递员\n", encoding="utf-8")
        self.journalism.write_text("采访\n", encoding="utf-8")
        self.urban.write_text("地图\n", encoding="utf-8")
        self.personal.write_text("犹豫\n沉默\n", encoding="utf-8")
        self.high_frequency_characters.write_text("旧\n城\n门\n我\n看\n你\n", encoding="utf-8")
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

    def test_default_known_character_compound_limit_is_500(self) -> None:
        self.assertEqual(DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT, 500)

    def layered_kwargs(self) -> dict:
        return {
            "general_fiction_pack": self.general,
            "genre_pack": self.genre,
            "setting_pack": self.setting,
            "profession_pack": self.profession,
            "journalism_crime_pack": self.journalism,
            "urban_objects_pack": self.urban,
            "proper_nouns_path": self.proper,
            "min_known_token_percent": 0,
            "max_total_stretch_token_percent": 100,
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

    def test_personal_known_word_validates_as_separate_layer(self) -> None:
        chapters = self.chapters_dir("我 犹豫 了 。\n")
        report = validate_book(chapters, self.known, personal_known_words_path=self.personal)
        self.assertTrue(report["valid"])
        self.assertEqual(report["personal_known_tokens"], 1)
        self.assertEqual(report["unique_personal_known_words_used"], 1)
        self.assertEqual(report["forbidden_unknown_tokens"], 0)

    def test_personal_known_word_is_unknown_without_profile(self) -> None:
        chapters = self.chapters_dir("我 犹豫 了 。\n")
        report = validate_book(chapters, self.known)
        self.assertFalse(report["valid"])
        self.assertEqual(report["personal_known_tokens"], 0)
        self.assertEqual(report["forbidden_unknown_tokens"], 1)
        self.assertFalse(report["known_token_percent_allowed"])

    def test_known_character_compound_layer_is_audited_separately(self) -> None:
        chapters = self.chapters_dir("旧城门 看 你 。\n")
        report = validate_book(
            chapters,
            self.known,
            known_character_compounds_path=self.high_frequency_characters,
            known_character_compound_limit=3,
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["vocabulary_profile"], "personalized")
        self.assertEqual(report["forbidden_unknown_tokens"], 0)
        self.assertEqual(report["high_frequency_character_compound_tokens"], 1)
        self.assertEqual(report["unique_high_frequency_character_compounds_used"], 1)
        self.assertEqual(report["high_frequency_character_compound_frequency"], {"旧城门": 1})

    def test_known_character_compound_limit_is_enforced(self) -> None:
        chapters = self.chapters_dir("旧城门 看 你 。\n")
        report = validate_book(
            chapters,
            self.known,
            known_character_compounds_path=self.high_frequency_characters,
            known_character_compound_limit=2,
        )
        self.assertFalse(report["valid"])
        self.assertEqual(report["high_frequency_character_compound_tokens"], 0)
        self.assertEqual(report["forbidden_unknown_tokens"], 1)
        self.assertFalse(report["known_token_percent_allowed"])

    def test_known_character_compound_layer_does_not_override_exact_core_words(self) -> None:
        vocab = load_layered_vocabulary(
            self.known,
            known_character_compounds_path=self.high_frequency_characters,
        )
        report = validate_text("我 看 你 。", load_known_words(self.known), vocabulary=vocab)
        self.assertEqual(vocab["token_layers"]["看"], "core_known")
        self.assertEqual(report["core_known_tokens"], 3)
        self.assertEqual(report["high_frequency_character_compound_tokens"], 0)

    def test_same_token_in_core_and_personal_counts_as_core(self) -> None:
        personal = self.root / "personal_core_overlap.txt"
        personal.write_text("我\n犹豫\n", encoding="utf-8")
        chapters = self.chapters_dir("我 犹豫 了 。\n")
        report = validate_book(chapters, self.known, personal_known_words_path=personal)
        self.assertEqual(report["core_known_tokens"], 2)
        self.assertEqual(report["personal_known_tokens"], 1)

    def test_same_token_in_personal_and_stretch_counts_as_personal(self) -> None:
        chapters = self.chapters_dir("你 沉默 了 。\n")
        report = validate_book(
            chapters,
            self.known,
            personal_known_words_path=self.personal,
            general_fiction_pack=self.general,
        )
        self.assertEqual(report["personal_known_tokens"], 1)
        self.assertEqual(report["general_fiction_stretch_tokens"], 0)
        vocab = load_layered_vocabulary(
            self.known,
            personal_known_words_path=self.personal,
            general_fiction_pack=self.general,
        )
        self.assertEqual(vocab["token_layers"]["沉默"], PERSONAL_KNOWN_LAYER)

    def test_proper_noun_passes_only_when_listed(self) -> None:
        chapters = self.chapters_dir("林安 看 你 。\n")
        allowed = validate_book(chapters, self.known, **self.layered_kwargs())
        blocked = validate_book(chapters, self.known)
        self.assertTrue(allowed["valid"])
        self.assertEqual(allowed["proper_noun_tokens"], 1)
        self.assertFalse(blocked["valid"])
        self.assertEqual(blocked["proper_noun_tokens"], 0)
        self.assertEqual(blocked["forbidden_unknown_tokens"], 1)

    def test_shanghai_setting_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", setting_pack=ROOT / "data" / "stretch_packs" / "shanghai_setting_150.txt")
        self.assertEqual(vocab["token_layers"]["外滩"], SETTING_LAYER)

    def test_low_fantasy_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", genre_pack=ROOT / "data" / "stretch_packs" / "low_fantasy_150.txt")
        self.assertEqual(vocab["token_layers"]["魔术"], GENRE_LAYER)

    def test_low_fantasy_pack_has_150_non_core_words(self) -> None:
        fantasy_pack = ROOT / "data" / "stretch_packs" / "low_fantasy_150.txt"
        fantasy_words = load_optional_words(fantasy_pack)
        core_words = set(load_known_words(ROOT / "data" / "known_words.txt"))
        other_words: set[str] = set()
        for pack in (ROOT / "data" / "stretch_packs").glob("*.txt"):
            if pack != fantasy_pack:
                other_words.update(load_optional_words(pack))
        self.assertEqual(len(fantasy_words), 150)
        self.assertEqual(len(set(fantasy_words)), 150)
        self.assertFalse(set(fantasy_words) & core_words)
        self.assertFalse(set(fantasy_words) & other_words)

    def test_profession_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", profession_pack=ROOT / "data" / "stretch_packs" / "professions_social_roles_100.txt")
        self.assertEqual(vocab["token_layers"]["快递员"], PROFESSION_LAYER)

    def test_journalism_crime_pack_is_loaded(self) -> None:
        vocab = load_layered_vocabulary(ROOT / "data" / "known_words.txt", journalism_crime_pack=ROOT / "data" / "stretch_packs" / "journalism_crime_50.txt")
        self.assertEqual(vocab["token_layers"]["侦查"], JOURNALISM_CRIME_LAYER)

    def test_business_economics_pack_is_loaded_as_extra_pack(self) -> None:
        vocab = load_layered_vocabulary(
            ROOT / "data" / "known_words.txt",
            extra_packs=[ROOT / "data" / "stretch_packs" / "business_economics_150.txt"],
        )
        self.assertEqual(vocab["token_layers"]["利润"], BUSINESS_ECONOMICS_LAYER)

    def test_business_economics_pack_has_no_core_or_prior_pack_duplicates(self) -> None:
        business_pack = ROOT / "data" / "stretch_packs" / "business_economics_150.txt"
        business_words = set(load_optional_words(business_pack))
        core_words = set(load_known_words(ROOT / "data" / "known_words.txt"))
        prior_words: set[str] = set()
        for pack in (ROOT / "data" / "stretch_packs").glob("*.txt"):
            if pack != business_pack:
                prior_words.update(load_optional_words(pack))
        self.assertFalse(business_words & core_words)
        self.assertFalse(business_words & prior_words)

    def test_stretch_packs_match_targets_without_known_layer_duplicates(self) -> None:
        stretch_dir = ROOT / "data" / "stretch_packs"
        core_words = set(load_known_words(ROOT / "data" / "known_words.txt"))
        high_frequency_characters = set(
            load_ranked_characters(
                ROOT / "data" / "learner_profiles" / "marcel" / "high_frequency_characters.txt",
                DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
            )
        )
        seen: dict[str, str] = {}

        for pack in sorted(stretch_dir.glob("*.txt")):
            words = load_optional_words(pack)
            target = int(pack.stem.rsplit("_", 1)[-1])
            duplicate_words = sorted(word for word in set(words) if words.count(word) > 1)
            core_duplicates = sorted(set(words) & core_words)
            character_compound_duplicates = sorted(
                word for word in words if is_known_character_compound(word, high_frequency_characters)
            )
            cross_pack_duplicates = sorted(
                f"{word} in {pack.name} and {seen[word]}" for word in words if word in seen
            )

            self.assertEqual(len(words), target, pack.name)
            self.assertFalse(duplicate_words, pack.name)
            self.assertFalse(core_duplicates, pack.name)
            self.assertFalse(character_compound_duplicates, pack.name)
            self.assertFalse(cross_pack_duplicates, pack.name)

            for word in words:
                seen[word] = pack.name

    def test_general_fiction_pack_has_150_non_core_words(self) -> None:
        general_pack = ROOT / "data" / "stretch_packs" / "general_fiction_150.txt"
        general_words = load_optional_words(general_pack)
        core_words = set(load_known_words(ROOT / "data" / "known_words.txt"))
        other_words: set[str] = set()
        for pack in (ROOT / "data" / "stretch_packs").glob("*.txt"):
            if pack != general_pack:
                other_words.update(load_optional_words(pack))
        self.assertEqual(len(general_words), 150)
        self.assertEqual(len(set(general_words)), 150)
        self.assertFalse(set(general_words) & core_words)
        self.assertFalse(set(general_words) & other_words)

    def test_business_economics_sample_token_validates_with_extra_pack(self) -> None:
        chapters = self.chapters_dir("利润 会 影响 生意 。\n")
        report = validate_book(
            chapters,
            ROOT / "data" / "known_words.txt",
            extra_packs=[ROOT / "data" / "stretch_packs" / "business_economics_150.txt"],
            min_known_token_percent=0,
            max_total_stretch_token_percent=100,
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["business_economics_stretch_tokens"], 1)

    def test_business_economics_extra_pack_counts_as_stretch(self) -> None:
        chapters = self.chapters_dir("利润 会 影响 生意 。\n")
        report = validate_book(
            chapters,
            ROOT / "data" / "known_words.txt",
            extra_packs=[ROOT / "data" / "stretch_packs" / "business_economics_150.txt"],
            min_known_token_percent=0,
            max_total_stretch_token_percent=100,
        )
        self.assertGreater(report["stretch_token_percent"], 0)

    def test_default_policy_blocks_high_stretch_share(self) -> None:
        chapters = self.chapters_dir("我 看 魔法 。\n")
        report = validate_book(chapters, self.known, genre_pack=self.genre)
        self.assertFalse(report["valid"])
        self.assertEqual(report["max_total_stretch_token_percent"], 2.0)
        self.assertFalse(report["stretch_token_percent_allowed"])
        self.assertTrue(any(warning["type"] == "stretch_token_share_above_limit" for warning in report["warnings"]))

    def test_default_policy_allows_two_percent_stretch_share(self) -> None:
        chapters = self.chapters_dir(" ".join(["我"] * 49 + ["魔法"]) + " 。\n")
        report = validate_book(chapters, self.known, genre_pack=self.genre)
        self.assertTrue(report["valid"])
        self.assertEqual(report["known_token_percent"], 98.0)
        self.assertEqual(report["stretch_token_percent"], 2.0)

    def test_layer_counts_are_correct(self) -> None:
        chapters = self.chapters_dir("林安 是 快递员 。\n我 在 上海 看 魔法 。\n你 沉默 了 。\n林安 采访 你 。\n")
        report = validate_book(chapters, self.known, **self.layered_kwargs())
        self.assertEqual(report["core_known_tokens"], 7)
        self.assertEqual(report["general_fiction_stretch_tokens"], 1)
        self.assertEqual(report["genre_stretch_tokens"], 1)
        self.assertEqual(report["setting_stretch_tokens"], 1)
        self.assertEqual(report["profession_stretch_tokens"], 1)
        self.assertEqual(report["journalism_crime_stretch_tokens"], 1)
        self.assertEqual(report["proper_noun_tokens"], 2)

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

    def test_anki_candidate_export_includes_business_economics_pack(self) -> None:
        out = self.root / "business_candidates.tsv"
        export_candidates(
            [ROOT / "data" / "stretch_packs" / "business_economics_150.txt"],
            core_path=ROOT / "data" / "known_words.txt",
            metadata_dir=ROOT / "data" / "stretch_packs" / "metadata",
            out_path=out,
        )
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        words = {row["Hanzi"] for row in rows}
        self.assertIn("利润", words)
        self.assertIn("开价", words)
        self.assertTrue(all(row["Pack"] == "business_economics_150" for row in rows))
        self.assertTrue(all(row["Layer"] == BUSINESS_ECONOMICS_LAYER for row in rows))

    def test_personal_known_sync_generates_allowed_profile_words(self) -> None:
        profile = self.root / "profile"
        profile.mkdir()
        tsv = profile / "personal_known_words.tsv"
        tsv.write_text(
            "\t".join(
                [
                    "word",
                    "pinyin",
                    "meaning",
                    "source",
                    "status",
                    "reading_confidence",
                    "allow_in_personal_readers",
                    "notes",
                ]
            )
            + "\n"
            + "犹豫\tyou2 yu4\thesitate\tmanual\tknown_passive\t4\tyes\t\n"
            + "学习\txue2 xi2\tstudy\tmanual\tlearning\t5\tyes\t\n"
            + "低\tdi1\tlow\tmanual\tknown_active\t3\tyes\t\n"
            + "我\two3\tI\tmanual\tknown_active\t5\tyes\t\n"
            + "沉默\tchen2 mo4\tsilent\tmanual\tknown_active\t5\tno\t\n",
            encoding="utf-8",
        )
        (profile / "personal_known_exclusions.txt").write_text("不用\n", encoding="utf-8")
        report = sync_personal_known_words(profile_dir=profile, core_path=self.known)
        words = load_optional_words(profile / "personal_known_words.txt")
        self.assertEqual(words, ["犹豫"])
        self.assertEqual(report["generated_personal_known_word_count"], 1)
        self.assertEqual(report["excluded_by_status_count"], 1)
        self.assertEqual(report["excluded_by_confidence_count"], 1)
        self.assertEqual(report["excluded_by_flag_count"], 1)
        self.assertEqual(report["core_duplicate_count"], 1)

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

    def test_epub_cli_uses_personal_known_profile_when_supplied(self) -> None:
        personal_path = ROOT / "data" / "learner_profiles" / "marcel" / "personal_known_words.txt"
        personal_token = "分散"
        self.assertIn(personal_token, load_optional_words(personal_path))
        self.assertNotIn(personal_token, load_known_words(ROOT / "data" / "known_words.txt"))

        manuscript = self.root / "personal_manuscript"
        chapters = manuscript / "chapters"
        chapters.mkdir(parents=True)
        (chapters / "chapter_01.zh-tok.txt").write_text(f"我 看 {personal_token} 。\n", encoding="utf-8")
        self.approve_quality(manuscript)

        public_report_path = manuscript / "epub" / "public_report.json"
        subprocess.run(
            [
                sys.executable,
                "scripts/build_epub.py",
                "--manuscript",
                str(manuscript),
                "--title",
                "Personal Test",
                "--out",
                str(manuscript / "epub" / "public.epub"),
                "--known",
                str(ROOT / "data" / "known_words.txt"),
                "--min-known-token-percent",
                "0",
                "--report",
                str(public_report_path),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        public_report = json.loads(public_report_path.read_text(encoding="utf-8"))
        self.assertEqual(public_report["vocabulary_profile"], "public")
        self.assertEqual(public_report["unknown_token_count"], 1)
        self.assertEqual(public_report["personal_known_tokens"], 0)

        personal_report_path = manuscript / "epub" / "personal_report.json"
        subprocess.run(
            [
                sys.executable,
                "scripts/build_epub.py",
                "--manuscript",
                str(manuscript),
                "--title",
                "Personal Test",
                "--out",
                str(manuscript / "epub" / "personal.epub"),
                "--known",
                str(ROOT / "data" / "known_words.txt"),
                "--personal-known",
                str(personal_path),
                "--report",
                str(personal_report_path),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        personal_report = json.loads(personal_report_path.read_text(encoding="utf-8"))
        self.assertEqual(personal_report["vocabulary_profile"], "personalized")
        self.assertEqual(personal_report["learner_profile_name"], "marcel")
        self.assertEqual(personal_report["unknown_token_count"], 0)
        self.assertEqual(personal_report["personal_known_tokens"], 1)


if __name__ == "__main__":
    unittest.main()
