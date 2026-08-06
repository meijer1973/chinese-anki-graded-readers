from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DECK_NAME = "China Knowledge"
MODEL_NAME = "China Knowledge Bilingual"
OPTIONS_PRESET_NAME = "China Knowledge - 5 new cards"
TEMPLATE_NAME = "Knowledge Recognition"
NEW_CARDS_PER_DAY = 5

DATA_DIR = ROOT / "anki" / "china_knowledge"
DEFAULT_TSV = DATA_DIR / "china_knowledge_400.tsv"
DEFAULT_SOURCES = DATA_DIR / "china_knowledge.sources.json"
DEFAULT_REPORTS_DIR = DATA_DIR / "reports"
DEFAULT_GENERATED_IMPORT = DATA_DIR / "generated" / "china_knowledge_import.json"

FIELDS = [
    "Knowledge ID",
    "Chinese Question",
    "English Question",
    "Chinese Answer",
    "English Answer",
    "Chinese Explanation",
    "English Explanation",
    "Category",
    "Subcategory",
    "Era",
    "Region",
    "Difficulty",
    "Source",
    "Source Date",
    "Fact Checked",
    "Tags",
]

CATEGORIES = {
    "geography": 65,
    "history": 90,
    "government": 35,
    "economy": 55,
    "society": 40,
    "culture": 45,
    "language": 25,
    "science_technology_environment": 45,
}

DIFFICULTIES = {"foundation", "intermediate", "advanced"}

STANDARD_TAG = "china_knowledge"

PROTECTED_RESOURCES = (
    ("Default", "Chinese Vocabulary"),
    ("Hindi", "Hindi Vocabulary"),
    ("Spanish", "Spanish Vocabulary"),
)
