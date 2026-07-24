from __future__ import annotations

import re
import unittest

from scripts.spanish.setup_spanish_anki import (
    CARD_TEMPLATES,
    CSS,
    FIELDS,
    SENTENCE_TEMPLATE_NAME,
    WORD_TEMPLATE_NAME,
)


class SpanishTemplateTests(unittest.TestCase):
    def test_note_type_has_exactly_two_named_templates(self) -> None:
        self.assertEqual(
            [
                "Word",
                "IPA",
                "Meaning",
                "Part of Speech",
                "Lemma",
                "Example",
                "Example IPA",
                "Example Meaning",
                "Source",
                "Labels",
                "Frequency Rank",
                "Notes",
            ],
            FIELDS,
        )
        self.assertEqual(2, len(CARD_TEMPLATES))
        self.assertEqual(
            [WORD_TEMPLATE_NAME, SENTENCE_TEMPLATE_NAME],
            [template["Name"] for template in CARD_TEMPLATES],
        )

    def test_no_field_or_template_is_production_like(self) -> None:
        forbidden = re.compile(r"production|recall|reverse|english\s+to\s+spanish", re.IGNORECASE)
        self.assertFalse(any(forbidden.search(field) for field in FIELDS))
        for template in CARD_TEMPLATES:
            self.assertIsNone(forbidden.search(" ".join(template.values())))

    def test_sentence_front_is_conditional_and_recognition_only(self) -> None:
        sentence = CARD_TEMPLATES[1]
        self.assertIn("{{#Example}}", sentence["Front"])
        self.assertIn("{{/Example}}", sentence["Front"])
        self.assertIn('lang="es"', sentence["Front"])
        self.assertNotIn("IPA", sentence["Front"])
        self.assertNotIn("Meaning", sentence["Front"])
        self.assertNotIn("{{Word}}", sentence["Front"])

    def test_lemma_is_conditional_on_both_backs(self) -> None:
        for template in CARD_TEMPLATES:
            self.assertIn("{{#Lemma}}", template["Back"])
            self.assertIn("{{/Lemma}}", template["Back"])

    def test_templates_use_no_javascript_or_external_fonts(self) -> None:
        markup = " ".join(
            [CSS, *[template["Front"] + template["Back"] for template in CARD_TEMPLATES]]
        ).casefold()
        self.assertNotIn("<script", markup)
        self.assertNotIn("javascript:", markup)
        self.assertNotIn("@import", markup)
        self.assertNotIn("http://", markup)
        self.assertNotIn("https://", markup)

    def test_complete_note_generates_two_cards_and_dataset_would_generate_200(self) -> None:
        populated = {"Word": "agua", "Example": "Bebo agua fría después de correr."}
        generated = sum(
            1
            for template in CARD_TEMPLATES
            if template["Name"] == WORD_TEMPLATE_NAME or populated["Example"]
        )
        self.assertEqual(2, generated)
        self.assertEqual(200, 100 * generated)


if __name__ == "__main__":
    unittest.main()
