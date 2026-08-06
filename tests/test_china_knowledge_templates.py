from __future__ import annotations

import re
import unittest

from scripts.china_knowledge.config import FIELDS, TEMPLATE_NAME
from scripts.china_knowledge.setup_china_knowledge_anki import CARD_TEMPLATES, CSS


class ChinaKnowledgeTemplateTests(unittest.TestCase):
    def test_note_type_has_one_recognition_template(self) -> None:
        self.assertEqual(16, len(FIELDS))
        self.assertEqual(1, len(CARD_TEMPLATES))
        self.assertEqual(TEMPLATE_NAME, CARD_TEMPLATES[0]["Name"])

    def test_front_is_bilingual_with_chinese_prominent_first(self) -> None:
        front = CARD_TEMPLATES[0]["Front"]
        self.assertLess(front.index("{{Chinese Question}}"), front.index("{{English Question}}"))
        self.assertIn('lang="zh-Hans"', front)
        self.assertIn('lang="en"', front)
        self.assertNotIn("Answer", front)
        self.assertNotIn("Explanation", front)

    def test_back_contains_bilingual_answers_explanations_and_sources(self) -> None:
        back = CARD_TEMPLATES[0]["Back"]
        for field in (
            "Chinese Answer",
            "English Answer",
            "Chinese Explanation",
            "English Explanation",
            "Source",
            "Source Date",
        ):
            self.assertIn("{{" + field + "}}", back)

    def test_templates_render_no_media_tts_scripts_or_remote_assets(self) -> None:
        markup = " ".join(
            [CSS, *[template["Front"] + template["Back"] for template in CARD_TEMPLATES]]
        ).casefold()
        self.assertIsNone(re.search(r"\[sound:|<img\b|<audio\b|\btts\b", markup))
        self.assertNotIn("<script", markup)
        self.assertNotIn("javascript:", markup)
        self.assertNotIn("@import", markup)
        self.assertNotIn("http://", markup)
        self.assertNotIn("https://", markup)

    def test_css_has_mobile_and_dark_mode_rules(self) -> None:
        self.assertIn("@media (max-width: 480px)", CSS)
        self.assertIn(".nightMode", CSS)
        self.assertIn("clamp(", CSS)


if __name__ == "__main__":
    unittest.main()
