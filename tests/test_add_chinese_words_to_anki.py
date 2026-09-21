from __future__ import annotations

import csv
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_anki_chinese
import setup_production_sentence_cards as card_setup
from scripts.add_chinese_words_to_anki import (
    ChineseWordImportError,
    add_words,
    load_ranked_words,
    load_source_rows,
    make_note,
    plan_additions,
    validate_model,
)


def source_row(word: str = "新词") -> dict[str, str]:
    return {
        "Word": word,
        "Pinyin": "xin1 ci2",
        "Meaning": "new word",
        "Example": "这是一个新词。",
        "Example Pinyin": "zhe4 shi4 yi2 ge5 xin1 ci2.",
        "Example Meaning": "This is a new word.",
        "Tags": "chinese cedict manual",
    }


class AddChineseWordsToAnkiTests(unittest.TestCase):
    def test_september_20_character_batch_has_persistent_reviewed_content(self) -> None:
        from apply_meaning_cleanup_updates import MEANING_OVERRIDES, cleaned_meaning
        from sentence_example_overrides import SENTENCE_EXAMPLE_OVERRIDES, SENTENCE_PINYIN_OVERRIDES

        targets = "叠叹氓蹭瞪闺丫咧娇屈槽啪慨憋抄啧嘻夕汪稚皱兮卦媳嫖暑柳樱讪凑嘱坑愁扶拧柱柿畅瘸盼筷兼匆厘厮吭呲呸咆咐哗哮嗓娼寒彤恍悟悻拽摞斜歪洒漆癖秃耿脊腮衷蹑阑阔鸽伺侃"
        self.assertEqual(77, len(set(targets)))
        words = build_anki_chinese.read_words()
        for word in targets:
            with self.subTest(word=word):
                self.assertEqual(1, words.count(word))
                example, translation = SENTENCE_EXAMPLE_OVERRIDES[word]
                self.assertIn(word, example)
                self.assertTrue(translation)
                pinyin = SENTENCE_PINYIN_OVERRIDES[example]
                self.assertEqual(pinyin, build_anki_chinese.generated_pinyin(example))
                self.assertEqual(len(re.findall(r"[\u3400-\u9fff]", example)),
                                 len(re.findall(r"[a-zA-ZüÜ:]+[1-5]", pinyin)))
                self.assertEqual(MEANING_OVERRIDES[word], cleaned_meaning(word, "Needs review"))
        for word, expected in {
            "氓": "mang2", "咧": "lie3", "拧": "ning3", "吭": "keng1",
            "呲": "zi1", "哗": "hua1", "拽": "zhuai4", "伺": "ci4 hou5",
            "彤": "hong2 tong1 tong1", "咐": "fen1 fu5",
        }.items():
            with self.subTest(context_reading=word):
                self.assertIn(expected, SENTENCE_PINYIN_OVERRIDES[SENTENCE_EXAMPLE_OVERRIDES[word][0]])

    def test_requested_characters_have_persistent_reviewed_fields(self) -> None:
        from apply_meaning_cleanup_updates import cleaned_meaning
        from sentence_example_overrides import SENTENCE_EXAMPLE_OVERRIDES, SENTENCE_PINYIN_OVERRIDES

        words = build_anki_chinese.read_words()
        for word in "郝眯哄迅颠悠寝锅":
            self.assertEqual(1, words.count(word))
            example, translation = SENTENCE_EXAMPLE_OVERRIDES[word]
            self.assertIn(word, example)
            self.assertTrue(translation)
            self.assertEqual(SENTENCE_PINYIN_OVERRIDES[example], build_anki_chinese.generated_pinyin(example))
            self.assertNotEqual("Needs review", cleaned_meaning(word, "Needs review"))
        self.assertEqual("Hao (Chinese family name)", cleaned_meaning("郝", "ancient place name; surname Hao"))
        self.assertIn("mi1", build_anki_chinese.generated_pinyin(SENTENCE_EXAMPLE_OVERRIDES["眯"][0]))
        self.assertIn("hong3", build_anki_chinese.generated_pinyin(SENTENCE_EXAMPLE_OVERRIDES["哄"][0]))

    def test_ranked_word_loader_rejects_duplicate_source_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "words.txt"
            path.write_text("你好\n新词\n你好\n", encoding="utf-8")
            with self.assertRaisesRegex(ChineseWordImportError, "Duplicate words"):
                load_ranked_words(path)

    def test_builder_also_rejects_duplicate_source_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "words.txt"
            path.write_text("你好\n新词\n你好\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Duplicate words"):
                build_anki_chinese.read_words(path)

    def test_source_tsv_loader_rejects_duplicate_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review.tsv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(source_row()), delimiter="\t")
                writer.writeheader()
                writer.writerow(source_row())
                writer.writerow(source_row())
            with self.assertRaisesRegex(ChineseWordImportError, "Duplicate words"):
                load_source_rows(path)

    def test_existing_live_word_is_not_planned_for_addition(self) -> None:
        existing = {
            "新词": [
                {
                    "noteId": 123,
                    "fields": {"Word": {"value": "新词"}},
                }
            ]
        }
        notes, already_present = plan_additions(
            ["新词"],
            {"新词": 20},
            {"新词": source_row()},
            existing,
        )
        self.assertEqual([], notes)
        self.assertEqual(["新词"], already_present)

    def test_duplicate_live_notes_are_a_hard_error(self) -> None:
        existing = {
            "新词": [
                {"noteId": 123, "fields": {"Word": {"value": "新词"}}},
                {"noteId": 456, "fields": {"Word": {"value": "新词"}}},
            ]
        }
        with self.assertRaisesRegex(ChineseWordImportError, "2 notes"):
            plan_additions(
                ["新词"],
                {"新词": 20},
                {"新词": source_row()},
                existing,
            )

    def test_note_enables_only_recognition_content_and_disallows_duplicates(self) -> None:
        note = make_note(source_row(), 20)
        self.assertEqual("yes", note["fields"]["Sentence Card"])
        self.assertEqual("", note["fields"]["Production Card"])
        self.assertEqual("20", note["fields"]["Frequency Rank"])
        self.assertFalse(note["options"]["allowDuplicate"])
        self.assertTrue(note["options"]["duplicateScopeOptions"]["checkChildren"])

    def test_model_validation_rejects_meaning_recall_template(self) -> None:
        def fake_anki(action: str, params: dict | None = None):
            if action == "modelNames":
                return ["Chinese Vocabulary"]
            if action == "modelFieldNames":
                return [
                    "Word",
                    "Pinyin",
                    "Meaning",
                    "Example",
                    "Example Pinyin",
                    "Example Meaning",
                    "Source",
                    "Production Card",
                    "Sentence Card",
                    "Frequency Rank",
                ]
            if action == "modelTemplates":
                return {
                    "Word Recognition": {},
                    "Meaning Recall": {},
                    "Sentence Recognition": {},
                }
            raise AssertionError(action)

        with self.assertRaisesRegex(ChineseWordImportError, "unwanted templates"):
            validate_model(fake_anki)

    def test_dry_run_uses_anki_can_add_notes_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            word_list = root / "words.txt"
            source_tsv = root / "review.tsv"
            word_list.write_text("新词\n", encoding="utf-8")
            with source_tsv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(source_row()), delimiter="\t")
                writer.writeheader()
                writer.writerow(source_row())

            calls: list[str] = []

            def fake_anki(action: str, params: dict | None = None):
                calls.append(action)
                if action == "modelNames":
                    return ["Chinese Vocabulary"]
                if action == "modelFieldNames":
                    return [
                        "Word",
                        "Pinyin",
                        "Meaning",
                        "Example",
                        "Example Pinyin",
                        "Example Meaning",
                        "Source",
                        "Production Card",
                        "Sentence Card",
                        "Frequency Rank",
                    ]
                if action == "modelTemplates":
                    return {"Word Recognition": {}, "Sentence Recognition": {}}
                if action == "findNotes":
                    return []
                if action == "canAddNotes":
                    return [True]
                raise AssertionError(action)

            report = add_words(
                ["新词"],
                apply=False,
                word_list=word_list,
                source_tsv=source_tsv,
                call_anki=fake_anki,
            )

        self.assertEqual(["新词"], report["would_add"])
        self.assertIn("canAddNotes", calls)
        self.assertNotIn("addNotes", calls)

    def test_setup_removes_meaning_recall_template(self) -> None:
        calls: list[tuple[str, dict | None]] = []

        def fake_anki(action: str, params: dict | None = None):
            calls.append((action, params))
            if action == "modelTemplates":
                return {
                    "Word Recognition": {},
                    "Meaning Recall": {},
                    "Sentence Recognition": {},
                }
            if action == "modelTemplateRemove":
                return None
            raise AssertionError(action)

        with patch.object(card_setup, "anki", side_effect=fake_anki):
            self.assertTrue(card_setup.remove_meaning_recall_template())

        self.assertIn(
            (
                "modelTemplateRemove",
                {
                    "modelName": "Chinese Vocabulary",
                    "templateName": "Meaning Recall",
                },
            ),
            calls,
        )

    def test_recognition_ordinals_follow_two_template_model(self) -> None:
        with patch.object(
            card_setup,
            "anki",
            return_value={"Word Recognition": {}, "Sentence Recognition": {}},
        ):
            self.assertEqual({0, 1}, card_setup.recognition_template_ords())


if __name__ == "__main__":
    unittest.main()
