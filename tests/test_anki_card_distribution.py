from __future__ import annotations

import unittest

from scripts.anki_card_distribution import (
    NOTE_TYPE_SINGLE,
    STATUS_ACTIVE,
    ScheduleConfig,
    active_words_from_plan,
    audit_distribution,
    audit_learning_plan,
    audit_passes,
    build_learning_order_plan,
    is_multi_character_or_word_note,
    is_single_hanzi_note,
    plan_summary,
)


def normal_words(count: int) -> list[str]:
    return [f"词语{index}" for index in range(1, count + 1)]


def single_chars(count: int) -> list[str]:
    return [chr(0x4E00 + index) for index in range(count)]


class AnkiCardDistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ScheduleConfig()

    def test_classifier_distinguishes_single_hanzi_from_words(self) -> None:
        self.assertTrue(is_single_hanzi_note("我"))
        self.assertFalse(is_single_hanzi_note("朋友"))
        self.assertFalse(is_single_hanzi_note("A"))
        self.assertTrue(is_multi_character_or_word_note("朋友"))
        self.assertTrue(is_multi_character_or_word_note("A"))

    def test_fixture_a_mixed_word_list_has_no_clumping_problem(self) -> None:
        words = ["朋友", "我", "学校", "你", "今天", "他", "工作", "家里"]
        audit = audit_distribution(words)
        self.assertEqual(audit["longest_consecutive_single_character_run"]["length"], 1)
        self.assertFalse(audit["single_character_runs_over_threshold"])

    def test_fixture_b_tail_block_fails_before_and_passes_after_scheduling(self) -> None:
        chars = single_chars(50)
        words = normal_words(100) + chars
        before = audit_distribution(words)
        self.assertEqual(before["longest_consecutive_single_character_run"]["length"], 50)
        self.assertFalse(audit_passes(before))

        plan = build_learning_order_plan(words, self.config)
        after = audit_learning_plan(plan)
        summary = plan_summary(plan)

        self.assertTrue(audit_passes(after))
        self.assertEqual(summary["active_single_character_rows"], 50)
        self.assertEqual(summary["pending_single_character_rows"], 0)
        self.assertLessEqual(after["window_distribution"]["20"]["max_single_character_cards"], 10)

    def test_fixture_c_excess_characters_are_evenly_spread_without_suspension(self) -> None:
        chars = single_chars(20)
        words = normal_words(5) + chars
        plan = build_learning_order_plan(words, self.config)
        summary = plan_summary(plan)
        active_words = active_words_from_plan(plan)

        self.assertEqual(summary["active_single_character_rows"], 20)
        self.assertEqual(summary["pending_single_character_rows"], 0)
        self.assertIn(active_words[-1], chars)
        self.assertLess(audit_learning_plan(plan)["longest_consecutive_single_character_run"]["length"], 20)

    def test_fixture_d_frequency_rank_stays_separate_from_learning_order(self) -> None:
        words = ["词一", "词二", "甲", "词三", "乙", "词四", "词五", "丙"]
        plan = build_learning_order_plan(words, self.config)
        rows_by_word = {row["Word"]: row for row in plan}

        self.assertEqual(rows_by_word["甲"]["Source Rank"], "3")
        self.assertEqual(rows_by_word["甲"]["Frequency Rank Preserved"], "3")
        self.assertNotEqual(rows_by_word["甲"]["Learning Order"], rows_by_word["甲"]["Source Rank"])
        self.assertEqual(rows_by_word["乙"]["Scheduling Status"], STATUS_ACTIVE)
        self.assertEqual(rows_by_word["乙"]["Source Rank"], "5")
        self.assertTrue(rows_by_word["乙"]["Learning Order"])

    def test_plan_marks_single_rows_explicitly(self) -> None:
        plan = build_learning_order_plan(["词一", "词二", "词三", "甲"], self.config)
        single_rows = [row for row in plan if row["Note Type"] == NOTE_TYPE_SINGLE]
        self.assertEqual(len(single_rows), 1)
        self.assertEqual(single_rows[0]["Scheduling Status"], STATUS_ACTIVE)


if __name__ == "__main__":
    unittest.main()
