import copy
import unittest

from scripts.chinese_card_categories import classify, in_deck_scope, target_text
from scripts.reorganize_chinese_subdecks import TABLES, make_plan, read_table, verify_change


WORD = {"name": "Word Recognition", "ord": 0, "qfmt": "<div>{{Word}}</div>", "afmt": "{{Example}}"}
SENTENCE = {"name": "Sentence Recognition", "ord": 1, "qfmt": "{{#Sentence Card}}{{Example}}{{/Sentence Card}}"}


def snapshot():
    s = {"tables": {t: {"columns": ["id", "value"], "rows": []} for t in TABLES},
         "decks": [{"id": 1, "name": "Default", "dyn": 0, "conf": 1},
                   {"id": 2, "name": "Other", "dyn": 0, "conf": 2}],
         "presets": [{"id": 1, "newGatherPriority": 0}, {"id": 2, "newGatherPriority": 0}],
         "models": [{"id": 10, "name": "Chinese Vocabulary",
                     "flds": [{"name": f} for f in ("Word", "Example", "Sentence Card")],
                     "tmpls": [WORD, SENTENCE]}], "media": {}, "global_options": {"fsrs": True}}
    s["tables"]["notes"] = {"columns": ["id", "mid", "flds"],
                            "rows": [[11, 10, "字\x1f我写了一个字。\x1fyes"],
                                     [12, 10, "词语\x1f这个词语很常用。\x1fyes"]]}
    s["tables"]["cards"] = {
        "columns": ["id", "nid", "did", "odid", "ord", "queue", "due", "ivl", "data", "mod", "usn"],
        "rows": [[101, 11, 1, 0, 0, -1, 99, 0, '{"s":1.234}', 1, 1],
                 [102, 11, 1, 0, 1, -2, 12, 20, '{"d":5.67}', 1, 1],
                 [103, 12, 1, 0, 0, 2, 20, 50, '{}', 1, 1],
                 [104, 12, 2, 0, 1, 0, 6, 0, '{}', 1, 1]]}
    return s


def moved_snapshot(before):
    after = copy.deepcopy(before)
    after["decks"] += [{"id": 3, "name": "Default::Single characters", "conf": 1, "dyn": 0, "desiredRetention": 95},
                       {"id": 4, "name": "Default::Sentences", "conf": 1, "dyn": 0, "desiredRetention": 80},
                       {"id": 5, "name": "Default::Multi-character words", "conf": 1, "dyn": 0, "desiredRetention": 90}]
    after["tables"]["cards"]["rows"][0][2] = 3
    after["tables"]["cards"]["rows"][1][2] = 4
    after["tables"]["cards"]["rows"][2][2] = 5
    return after


class CategoriesTest(unittest.TestCase):
    def test_word_with_back_example_is_not_sentence(self):
        self.assertEqual(classify("Chinese Vocabulary", WORD, {"Word": "字"})[0], "single")
        self.assertEqual(classify("Chinese Vocabulary", WORD, {"Word": "词语"})[0], "multi")

    def test_markup_whitespace_entities_and_extended_han(self):
        for word in (" <b>字</b> ", "&#23383;", "𠮷", "<style>x</style>字"):
            self.assertEqual(classify("Chinese Vocabulary", WORD, {"Word": word})[0], "single")
        self.assertEqual(target_text(" 字<br>词 "), "字 词")

    def test_ambiguous_annotations_alternatives_and_cloze_stay(self):
        for word in ("字 zì", "汉/漢", "", "A", "字 词"):
            self.assertEqual(classify("Chinese Vocabulary", WORD, {"Word": word})[0], "ambiguous")
        self.assertEqual(classify("Cloze", {"qfmt": "{{cloze:Text}}"}, {"Word": "字"})[0], "ambiguous")
        self.assertEqual(classify("Chinese Vocabulary", {**WORD, "qfmt": "{{Word}}{{Example}}"}, {"Word": "字"})[0], "ambiguous")

    def test_sentence_requires_actual_front_and_enabled_content(self):
        fields = {"Word": "字", "Example": "我写了一个字。", "Sentence Card": "yes"}
        self.assertEqual(classify("Chinese Vocabulary", SENTENCE, fields)[0], "sentence")
        self.assertEqual(classify("Chinese Vocabulary", SENTENCE, {**fields, "Sentence Card": ""})[0], "ambiguous")
        self.assertEqual(classify("Chinese Vocabulary", {**SENTENCE, "qfmt": "{{Word}}"}, fields)[0], "ambiguous")

    def test_scope_is_delimited_and_includes_nested_decks(self):
        self.assertTrue(in_deck_scope("Default"))
        self.assertTrue(in_deck_scope("Default::Sentences::Nested"))
        self.assertFalse(in_deck_scope("DefaultOther"))
        self.assertFalse(in_deck_scope("Other::Default"))


class MigrationTest(unittest.TestCase):
    def test_card_level_siblings_suspension_burial_and_other_deck(self):
        plan = make_plan(snapshot())
        self.assertEqual(plan["counts"], {"single": 1, "sentence": 1, "multi": 1})
        self.assertEqual(plan["moves"], {"single": 1, "sentence": 1, "multi": 1})
        self.assertEqual(plan["suspended"], {"single": 1})
        self.assertEqual(plan["buried"], 1)
        self.assertEqual(plan["rows"][0]["note_id"], plan["rows"][1]["note_id"])

    def test_third_subdeck_moves_only_remaining_parent_word_cards(self):
        before = moved_snapshot(snapshot())
        before["decks"] = [d for d in before["decks"] if d["id"] != 5]
        before["tables"]["cards"]["rows"][2][2] = 1
        plan = make_plan(before)
        self.assertEqual(plan["moves"], {"multi": 1})
        self.assertEqual([r["card_id"] for r in plan["rows"] if r["move"]], [103])
        after = copy.deepcopy(before)
        after["decks"].append({"id": 5, "name": "Default::Multi-character words", "conf": 1,
                               "dyn": 0, "desiredRetention": 90})
        after["tables"]["cards"]["rows"][2][2] = 5
        verify_change(before, after, plan, {d["name"]: d["id"] for d in after["decks"]})
        self.assertFalse(any(row[2] == 1 for row in after["tables"]["cards"]["rows"]))
        self.assertEqual(make_plan(after)["moves"], {})

    def test_filtered_home_membership_is_detected_but_not_moved(self):
        before = snapshot()
        before["tables"]["cards"]["rows"][0][2:4] = [2, 1]
        row = make_plan(before)["rows"][0]
        self.assertEqual(row["category"], "ambiguous")
        self.assertFalse(row["move"])

    def test_different_source_preset_requires_review(self):
        before = snapshot()
        before["decks"].append({"id": 3, "name": "Default::Special", "dyn": 0, "conf": 3})
        before["tables"]["cards"]["rows"][0][2] = 3
        row = make_plan(before)["rows"][0]
        self.assertEqual(row["category"], "ambiguous")
        self.assertFalse(row["move"])

    def test_migration_is_idempotent(self):
        before = snapshot()
        after = moved_snapshot(before)
        verify_change(before, after, make_plan(before), {d["name"]: d["id"] for d in after["decks"]})
        self.assertEqual(make_plan(after)["moves"], {})

    def test_memory_due_flags_and_suspension_changes_are_rejected(self):
        before = snapshot()
        for row_index in (0, 2):
            for index, value in [(5, 1), (6, 100), (7, 21), (8, '{"s":1.235}')]:
                with self.subTest(card=row_index, field=index):
                    after = moved_snapshot(before)
                    after["tables"]["cards"]["rows"][row_index][index] = value
                    with self.assertRaisesRegex(RuntimeError, "Card state"):
                        verify_change(before, after, make_plan(before), {d["name"]: d["id"] for d in after["decks"]})

    def test_history_content_and_other_settings_are_rejected(self):
        before = snapshot()
        for table in ("notes", "revlog", "templates"):
            after = moved_snapshot(before)
            after["tables"][table]["rows"].append([999, "damage"])
            with self.assertRaises(RuntimeError):
                verify_change(before, after, make_plan(before), {d["name"]: d["id"] for d in after["decks"]})
        after = moved_snapshot(before)
        after["presets"][1]["newGatherPriority"] = 1
        with self.assertRaisesRegex(RuntimeError, "Preset"):
            verify_change(before, after, make_plan(before), {d["name"]: d["id"] for d in after["decks"]})

    def test_native_bridge_blobs_match_sqlite_bytes(self):
        def rows(blob):
            return lambda sql: [(0, "id", "INTEGER"), (1, "config", "BLOB")] if sql.startswith("pragma") else [[1, blob]]
        self.assertEqual(read_table(rows(b"abc"), "fields"), read_table(rows([97, 98, 99]), "fields"))


if __name__ == "__main__":
    unittest.main()
