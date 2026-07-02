from __future__ import annotations

import html
import json
import re
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWN_WORDS = ROOT / "data" / "known_words.txt"
DEFAULT_PUNCTUATION = ROOT / "data" / "punctuation_allowlist.txt"
DEFAULT_STRETCH_PACKS_DIR = ROOT / "data" / "stretch_packs"
DEFAULT_LEARNER_PROFILES_DIR = ROOT / "data" / "learner_profiles"
DEFAULT_MARCEL_PERSONAL_KNOWN_WORDS = DEFAULT_LEARNER_PROFILES_DIR / "marcel" / "personal_known_words.txt"
DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS = DEFAULT_LEARNER_PROFILES_DIR / "marcel" / "high_frequency_characters.txt"
DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT = 1000
DEFAULT_GENERAL_FICTION_PACK = DEFAULT_STRETCH_PACKS_DIR / "general_fiction_150.txt"
DEFAULT_FANTASY_PACK = DEFAULT_STRETCH_PACKS_DIR / "fantasy_232.txt"
DEFAULT_SHANGHAI_SETTING_PACK = DEFAULT_STRETCH_PACKS_DIR / "shanghai_setting_150.txt"
DEFAULT_PROFESSIONS_PACK = DEFAULT_STRETCH_PACKS_DIR / "professions_social_roles_100.txt"
DEFAULT_URBAN_OBJECTS_PACK = DEFAULT_STRETCH_PACKS_DIR / "urban_objects_100.txt"
DEFAULT_JOURNALISM_CRIME_PACK = DEFAULT_STRETCH_PACKS_DIR / "journalism_crime_50.txt"
DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER = 5
DEFAULT_MIN_KNOWN_TOKEN_PERCENT = 98.0
DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT = 2.0
DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT = 500
DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT = 95.0

DEFAULT_PUNCTUATION_CHARS = set(
    " \t\r\n"
    "，。！？、；：（）《》〈〉「」『』【】"
    "“”‘’…—－"
    ",.!?;:()[]{}<>\"'`"
)

HANZI_RE = re.compile(r"[\u3400-\u9fff]")
HANZI_CHAR_RE = re.compile(r"^[\u3400-\u9fff]$")
QUALITY_DECISION_FILE = "lead_quality_decision.md"

CORE_LAYER = "core_known"
PERSONAL_KNOWN_LAYER = "personal_known"
HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER = "high_frequency_character_compound"
GENERAL_FICTION_LAYER = "general_fiction_stretch"
GENRE_LAYER = "genre_stretch"
SETTING_LAYER = "setting_stretch"
PROFESSION_LAYER = "profession_stretch"
JOURNALISM_CRIME_LAYER = "journalism_crime_stretch"
BUSINESS_ECONOMICS_LAYER = "business_economics_stretch"
BOOK_SPECIFIC_LAYER = "book_specific_stretch"
PROPER_NOUN_LAYER = "proper_noun"

LAYER_TOKEN_FIELDS = {
    CORE_LAYER: "core_known_tokens",
    PERSONAL_KNOWN_LAYER: "personal_known_tokens",
    HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER: "high_frequency_character_compound_tokens",
    GENERAL_FICTION_LAYER: "general_fiction_stretch_tokens",
    GENRE_LAYER: "genre_stretch_tokens",
    SETTING_LAYER: "setting_stretch_tokens",
    PROFESSION_LAYER: "profession_stretch_tokens",
    JOURNALISM_CRIME_LAYER: "journalism_crime_stretch_tokens",
    BUSINESS_ECONOMICS_LAYER: "business_economics_stretch_tokens",
    BOOK_SPECIFIC_LAYER: "book_specific_stretch_tokens",
    PROPER_NOUN_LAYER: "proper_noun_tokens",
}

KNOWN_LAYERS = {
    CORE_LAYER,
    PERSONAL_KNOWN_LAYER,
    HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER,
}

STRETCH_LAYERS = {
    GENERAL_FICTION_LAYER,
    GENRE_LAYER,
    SETTING_LAYER,
    PROFESSION_LAYER,
    JOURNALISM_CRIME_LAYER,
    BUSINESS_ECONOMICS_LAYER,
    BOOK_SPECIFIC_LAYER,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_known_words(path: str | Path = DEFAULT_KNOWN_WORDS) -> list[str]:
    known_path = Path(path)
    words: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(known_path.read_text(encoding="utf-8").splitlines(), start=1):
        word = raw_line.strip()
        if not word or word.startswith("#"):
            continue
        if word in seen:
            raise ValueError(f"Duplicate known word {word!r} in {known_path} line {line_number}")
        seen.add(word)
        words.append(word)
    if not words:
        raise ValueError(f"No known words found in {known_path}")
    return words


def load_optional_words(path: str | Path | None) -> list[str]:
    if not path:
        return []
    word_path = Path(path)
    if not word_path.exists():
        return []
    words: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(word_path.read_text(encoding="utf-8").splitlines(), start=1):
        word = raw_line.strip()
        if not word or word.startswith("#"):
            continue
        if word in seen:
            raise ValueError(f"Duplicate word {word!r} in {word_path} line {line_number}")
        seen.add(word)
        words.append(word)
    return words


def load_ranked_characters(
    path: str | Path | None,
    limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
) -> list[str]:
    if not path:
        return []
    if limit < 0:
        raise ValueError("Known-character compound limit must be 0 or greater.")
    character_path = Path(path)
    if not character_path.exists():
        return []
    characters: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(character_path.read_text(encoding="utf-8").splitlines(), start=1):
        character = raw_line.strip()
        if not character or character.startswith("#"):
            continue
        if not HANZI_CHAR_RE.match(character):
            raise ValueError(f"Expected one Hanzi character in {character_path} line {line_number}: {character!r}")
        if character in seen:
            raise ValueError(f"Duplicate ranked character {character!r} in {character_path} line {line_number}")
        seen.add(character)
        characters.append(character)
        if limit and len(characters) >= limit:
            break
    return characters


def infer_stretch_layer(path: str | Path) -> str:
    name = Path(path).stem.lower()
    if "general" in name or "fiction" in name:
        return GENERAL_FICTION_LAYER
    if "fantasy" in name or "genre" in name:
        return GENRE_LAYER
    if "profession" in name or "social" in name or "role" in name:
        return PROFESSION_LAYER
    if "journalism" in name or "crime" in name or "reporter" in name:
        return JOURNALISM_CRIME_LAYER
    if "business" in name or "economic" in name or "market" in name:
        return BUSINESS_ECONOMICS_LAYER
    if "setting" in name or "shanghai" in name or "urban" in name or "object" in name:
        return SETTING_LAYER
    return BOOK_SPECIFIC_LAYER


def load_layered_vocabulary(
    core_known_path: str | Path = DEFAULT_KNOWN_WORDS,
    *,
    general_fiction_pack: str | Path | None = None,
    personal_known_words_path: str | Path | None = None,
    known_character_compounds_path: str | Path | None = None,
    known_character_compound_limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    easy_character_compounds_path: str | Path | None = DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    easy_character_compound_limit: int = DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
    genre_pack: str | Path | None = None,
    setting_pack: str | Path | None = None,
    profession_pack: str | Path | None = None,
    journalism_crime_pack: str | Path | None = None,
    urban_objects_pack: str | Path | None = None,
    book_specific_words_path: str | Path | None = None,
    proper_nouns_path: str | Path | None = None,
    extra_packs: Iterable[str | Path] | None = None,
) -> dict:
    core_words = load_known_words(core_known_path)
    known_character_compound_characters = set(
        load_ranked_characters(known_character_compounds_path, known_character_compound_limit)
    )
    easy_character_compound_characters = set(
        load_ranked_characters(easy_character_compounds_path, easy_character_compound_limit)
    )
    token_layers: dict[str, str] = {}
    layer_words: dict[str, list[str]] = {layer: [] for layer in LAYER_TOKEN_FIELDS}
    duplicate_as_core: list[str] = []
    duplicate_as_earlier_layer: list[dict] = []

    for word in core_words:
        token_layers[word] = CORE_LAYER
        layer_words[CORE_LAYER].append(word)

    def add_words(words: Iterable[str], layer: str, source: str | Path | None = None) -> None:
        for word in words:
            existing = token_layers.get(word)
            if existing == CORE_LAYER:
                duplicate_as_core.append(word)
                continue
            if existing:
                duplicate_as_earlier_layer.append(
                    {"word": word, "kept_layer": existing, "ignored_layer": layer, "source": str(source or "")}
                )
                continue
            token_layers[word] = layer
            layer_words[layer].append(word)

    add_words(load_optional_words(personal_known_words_path), PERSONAL_KNOWN_LAYER, personal_known_words_path)
    add_words(load_optional_words(general_fiction_pack), GENERAL_FICTION_LAYER, general_fiction_pack)
    add_words(load_optional_words(genre_pack), GENRE_LAYER, genre_pack)
    add_words(load_optional_words(setting_pack), SETTING_LAYER, setting_pack)
    add_words(load_optional_words(profession_pack), PROFESSION_LAYER, profession_pack)
    add_words(load_optional_words(journalism_crime_pack), JOURNALISM_CRIME_LAYER, journalism_crime_pack)
    add_words(load_optional_words(urban_objects_pack), SETTING_LAYER, urban_objects_pack)
    add_words(load_optional_words(book_specific_words_path), BOOK_SPECIFIC_LAYER, book_specific_words_path)
    add_words(load_optional_words(proper_nouns_path), PROPER_NOUN_LAYER, proper_nouns_path)
    for pack in extra_packs or []:
        add_words(load_optional_words(pack), infer_stretch_layer(pack), pack)

    learner_profile_paths = [
        Path(path)
        for path in (personal_known_words_path, known_character_compounds_path)
        if path
    ]
    learner_profile_name = "marcel" if any("marcel" in path.parts for path in learner_profile_paths) else None
    personalized_layers_enabled = bool(personal_known_words_path or known_character_compounds_path)

    return {
        "core_known_path": str(Path(core_known_path)),
        "token_layers": token_layers,
        "known_character_compound_characters": known_character_compound_characters,
        "known_character_compounds_path": (
            str(Path(known_character_compounds_path)) if known_character_compounds_path else None
        ),
        "known_character_compound_limit": known_character_compound_limit,
        "known_character_compound_character_count": len(known_character_compound_characters),
        "easy_character_compounds_path": (
            str(Path(easy_character_compounds_path)) if easy_character_compounds_path else None
        ),
        "easy_character_compound_limit": easy_character_compound_limit,
        "easy_character_compound_character_count": len(easy_character_compound_characters),
        "easy_character_compound_characters": easy_character_compound_characters,
        "layer_words": {layer: sorted(set(words)) for layer, words in layer_words.items()},
        "known_word_count": len(core_words),
        "personal_known_word_count": len(set(layer_words[PERSONAL_KNOWN_LAYER])),
        "personal_known_words_path": str(Path(personal_known_words_path)) if personal_known_words_path else None,
        "vocabulary_profile": "personalized" if personalized_layers_enabled else "public",
        "learner_profile_name": learner_profile_name,
        "allowed_token_count": len(token_layers),
        "duplicate_as_core": sorted(set(duplicate_as_core)),
        "duplicate_as_earlier_layer": duplicate_as_earlier_layer,
    }


def load_punctuation(path: str | Path = DEFAULT_PUNCTUATION) -> set[str]:
    punctuation = set(DEFAULT_PUNCTUATION_CHARS)
    punctuation_path = Path(path)
    if punctuation_path.exists():
        for raw_line in punctuation_path.read_text(encoding="utf-8").splitlines():
            item = raw_line.strip("\ufeff")
            if not item or item.startswith("#"):
                continue
            punctuation.update(item)
    return punctuation


def normalize_token(raw_token: str, punctuation: set[str]) -> str:
    return "".join(char for char in raw_token if char not in punctuation)


def is_known_character_compound(token: str, known_characters: set[str]) -> bool:
    return bool(known_characters) and all(HANZI_CHAR_RE.match(char) and char in known_characters for char in token)


def classify_token_layer(
    token: str,
    token_layers: dict[str, str],
    known_character_compound_characters: set[str],
) -> str | None:
    return token_layers.get(token) or (
        HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER
        if is_known_character_compound(token, known_character_compound_characters)
        else None
    )


def iter_story_tokens(text: str, punctuation: set[str]) -> Iterable[tuple[int, str, str]]:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for raw_token in line.split():
            token = normalize_token(raw_token, punctuation)
            if token:
                yield line_number, raw_token, token


def validate_text(
    text: str,
    known_words: Iterable[str],
    *,
    punctuation: set[str] | None = None,
    vocabulary: dict | None = None,
    chapter_name: str | None = None,
    target_core_coverage_percent: float | None = None,
    min_known_token_percent: float | None = DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
    max_total_stretch_token_percent: float | None = DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
    max_easy_character_compound_token_percent: float | None = DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
    max_forbidden_unknown_tokens_per_chapter: int = DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
) -> dict:
    if vocabulary is None:
        allowed = set(known_words)
        token_layers = {word: CORE_LAYER for word in allowed}
        known_word_count = len(allowed)
        vocabulary = {
            "token_layers": token_layers,
            "known_word_count": known_word_count,
            "allowed_token_count": len(allowed),
            "known_character_compound_characters": set(),
            "easy_character_compound_characters": set(),
            "duplicate_as_core": [],
            "duplicate_as_earlier_layer": [],
        }
    else:
        token_layers = vocabulary["token_layers"]
        known_word_count = vocabulary.get("known_word_count", 0)
    known_character_compound_characters = vocabulary.get("known_character_compound_characters", set())
    easy_character_compound_characters = vocabulary.get("easy_character_compound_characters", set())
    punctuation = punctuation or load_punctuation()
    tokens: list[str] = []
    violations: list[dict] = []
    unknown_counter: Counter[str] = Counter()
    high_frequency_character_compound_counter: Counter[str] = Counter()
    easy_character_compound_counter: Counter[str] = Counter()
    layer_counts: Counter[str] = Counter()
    unique_by_layer: dict[str, set[str]] = {layer: set() for layer in LAYER_TOKEN_FIELDS}

    for line_number, raw_token, token in iter_story_tokens(text, punctuation):
        tokens.append(token)
        if is_known_character_compound(token, easy_character_compound_characters):
            easy_character_compound_counter[token] += 1
        layer = classify_token_layer(token, token_layers, known_character_compound_characters)
        if not layer:
            unknown_counter[token] += 1
            violations.append(
                {
                    "line": line_number,
                    "raw_token": raw_token,
                    "token": token,
                    "contains_hanzi": bool(HANZI_RE.search(token)),
                }
            )
            continue
        layer_counts[layer] += 1
        unique_by_layer.setdefault(layer, set()).add(token)
        if layer == HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER:
            high_frequency_character_compound_counter[token] += 1

    unique_tokens = sorted(set(tokens))
    total_tokens = len(tokens)
    stretch_counter: Counter[str] = Counter(token for token in tokens if token_layers.get(token) in STRETCH_LAYERS)
    approved_non_core_count = sum(layer_counts[layer] for layer in STRETCH_LAYERS | {PROPER_NOUN_LAYER})
    core_coverage_percent = (layer_counts[CORE_LAYER] / total_tokens * 100) if total_tokens else 0.0
    known_token_percent = (sum(layer_counts[layer] for layer in KNOWN_LAYERS) / total_tokens * 100) if total_tokens else 0.0
    stretch_token_percent = (approved_non_core_count / total_tokens * 100) if total_tokens else 0.0
    easy_character_compound_tokens = sum(easy_character_compound_counter.values())
    easy_character_compound_token_percent = (
        easy_character_compound_tokens / total_tokens * 100
    ) if total_tokens else 0.0
    warnings: list[dict] = []
    stretch_words_used_once = sorted(token for token, count in stretch_counter.items() if count == 1)
    if stretch_words_used_once:
        warnings.append(
            {
                "type": "stretch_words_used_once",
                "message": "Approved stretch words used only once should be reviewed for meaningful repetition.",
                "tokens": stretch_words_used_once,
            }
        )
    if target_core_coverage_percent is not None and core_coverage_percent < target_core_coverage_percent:
        warnings.append(
            {
                "type": "core_coverage_below_target",
                "target_percent": target_core_coverage_percent,
                "actual_percent": round(core_coverage_percent, 2),
            }
        )
    known_token_percent_allowed = min_known_token_percent is None or known_token_percent >= min_known_token_percent
    if not known_token_percent_allowed:
        warnings.append(
            {
                "type": "known_token_share_below_minimum",
                "minimum_percent": min_known_token_percent,
                "actual_percent": round(known_token_percent, 2),
            }
        )
    stretch_token_percent_allowed = (
        max_total_stretch_token_percent is None or stretch_token_percent <= max_total_stretch_token_percent
    )
    if max_total_stretch_token_percent is not None and stretch_token_percent > max_total_stretch_token_percent:
        warnings.append(
            {
                "type": "stretch_token_share_above_limit",
                "limit_percent": max_total_stretch_token_percent,
                "actual_percent": round(stretch_token_percent, 2),
            }
        )
    easy_character_compound_token_percent_allowed = (
        max_easy_character_compound_token_percent is None
        or easy_character_compound_token_percent <= max_easy_character_compound_token_percent
    )
    if (
        max_easy_character_compound_token_percent is not None
        and easy_character_compound_token_percent > max_easy_character_compound_token_percent
    ):
        warnings.append(
            {
                "type": "easy_character_compound_share_above_limit",
                "message": "Too much text is made only from the first ranked character-compound band.",
                "limit_percent": max_easy_character_compound_token_percent,
                "actual_percent": round(easy_character_compound_token_percent, 2),
                "easy_character_compound_limit": vocabulary.get(
                    "easy_character_compound_limit", DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT
                ),
            }
        )

    forbidden_unknown_count = sum(unknown_counter.values())
    unknowns_over_limit = max(0, forbidden_unknown_count - max_forbidden_unknown_tokens_per_chapter)
    if forbidden_unknown_count:
        warning_type = "forbidden_unknown_tokens_over_limit" if unknowns_over_limit else "forbidden_unknown_tokens_within_budget"
        warnings.append(
            {
                "type": warning_type,
                "message": (
                    "Forbidden unknown tokens remain and should be reviewed for learnability."
                    if not unknowns_over_limit
                    else "Forbidden unknown tokens exceed the configured per-chapter budget."
                ),
                "actual": forbidden_unknown_count,
                "limit": max_forbidden_unknown_tokens_per_chapter,
                "over_limit": unknowns_over_limit,
                "tokens": dict(sorted(unknown_counter.items())),
            }
        )
    long_high_frequency_character_compounds = sorted(
        token for token in high_frequency_character_compound_counter if len(token) > 4
    )
    if long_high_frequency_character_compounds:
        warnings.append(
            {
                "type": "long_high_frequency_character_compounds",
                "message": "Long derived character compounds should be reviewed for missing token spaces.",
                "tokens": long_high_frequency_character_compounds,
            }
        )

    result = {
        field: layer_counts[layer]
        for layer, field in LAYER_TOKEN_FIELDS.items()
    }
    result.update(
        {
            "forbidden_unknown_tokens": forbidden_unknown_count,
            "max_forbidden_unknown_tokens_per_chapter": max_forbidden_unknown_tokens_per_chapter,
            "forbidden_unknown_tokens_over_limit": unknowns_over_limit,
            "forbidden_unknown_tokens_allowed": unknowns_over_limit == 0,
            "core_coverage_percent": round(core_coverage_percent, 2),
            "known_token_percent": round(known_token_percent, 2),
            "min_known_token_percent": min_known_token_percent,
            "known_token_percent_allowed": known_token_percent_allowed,
            "stretch_token_percent": round(stretch_token_percent, 2),
            "max_total_stretch_token_percent": max_total_stretch_token_percent,
            "stretch_token_percent_allowed": stretch_token_percent_allowed,
            "easy_character_compound_tokens": easy_character_compound_tokens,
            "unique_easy_character_compounds_used": len(easy_character_compound_counter),
            "easy_character_compound_token_percent": round(easy_character_compound_token_percent, 2),
            "max_easy_character_compound_token_percent": max_easy_character_compound_token_percent,
            "easy_character_compound_token_percent_allowed": easy_character_compound_token_percent_allowed,
            "easy_character_compound_limit": vocabulary.get(
                "easy_character_compound_limit", DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT
            ),
            "easy_character_compound_character_count": vocabulary.get(
                "easy_character_compound_character_count", 0
            ),
            "easy_character_compounds_path": vocabulary.get("easy_character_compounds_path"),
            "unique_core_words_used": len(unique_by_layer[CORE_LAYER]),
            "unique_personal_known_words_used": len(unique_by_layer[PERSONAL_KNOWN_LAYER]),
            "unique_high_frequency_character_compounds_used": len(
                unique_by_layer[HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER]
            ),
            "unique_stretch_words_used": len(set().union(*(unique_by_layer[layer] for layer in STRETCH_LAYERS))),
            "unique_proper_nouns_used": len(unique_by_layer[PROPER_NOUN_LAYER]),
            "stretch_words_used_once": stretch_words_used_once,
            "stretch_words_by_chapter": {chapter_name: sorted(stretch_counter)} if chapter_name else {},
            "new_stretch_words_by_chapter": {chapter_name: sorted(stretch_counter)} if chapter_name else {},
            "high_frequency_character_compound_frequency": dict(
                sorted(high_frequency_character_compound_counter.items())
            ),
            "easy_character_compound_frequency": dict(sorted(easy_character_compound_counter.items())),
            "forbidden_unknown_token_frequency": dict(sorted(unknown_counter.items())),
            "warnings": warnings,
        }
    )
    valid = (
        unknowns_over_limit == 0
        and known_token_percent_allowed
        and stretch_token_percent_allowed
        and easy_character_compound_token_percent_allowed
    )
    result.update(
        {
            "valid": valid,
            "line_count": len(text.splitlines()),
            "total_tokens": total_tokens,
            "unique_token_count": len(unique_tokens),
            "unique_tokens": unique_tokens,
            "unknown_token_count": forbidden_unknown_count,
            "unknown_unique_count": len(unknown_counter),
            "unknown_token_frequency": dict(sorted(unknown_counter.items())),
            "violations": violations,
            "known_word_count": known_word_count,
            "personal_known_word_count": vocabulary.get("personal_known_word_count", 0),
            "personal_known_words_path": vocabulary.get("personal_known_words_path"),
            "known_character_compounds_path": vocabulary.get("known_character_compounds_path"),
            "known_character_compound_limit": vocabulary.get("known_character_compound_limit", 0),
            "known_character_compound_character_count": vocabulary.get(
                "known_character_compound_character_count", 0
            ),
            "vocabulary_profile": vocabulary.get("vocabulary_profile", "public"),
            "learner_profile_name": vocabulary.get("learner_profile_name"),
            "allowed_token_count": vocabulary.get("allowed_token_count", len(token_layers)),
            "duplicate_stretch_words_already_core": vocabulary.get("duplicate_as_core", []),
            "duplicate_stretch_words_ignored": vocabulary.get("duplicate_as_earlier_layer", []),
        }
    )
    return result


def validate_chapter(
    chapter_path: str | Path,
    known_path: str | Path = DEFAULT_KNOWN_WORDS,
    *,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    personal_known_words_path: str | Path | None = None,
    known_character_compounds_path: str | Path | None = None,
    known_character_compound_limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    easy_character_compounds_path: str | Path | None = DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    easy_character_compound_limit: int = DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
    general_fiction_pack: str | Path | None = None,
    genre_pack: str | Path | None = None,
    setting_pack: str | Path | None = None,
    profession_pack: str | Path | None = None,
    journalism_crime_pack: str | Path | None = None,
    urban_objects_pack: str | Path | None = None,
    book_specific_words_path: str | Path | None = None,
    proper_nouns_path: str | Path | None = None,
    extra_packs: Iterable[str | Path] | None = None,
    target_core_coverage_percent: float | None = None,
    min_known_token_percent: float | None = DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
    max_total_stretch_token_percent: float | None = DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
    max_easy_character_compound_token_percent: float | None = DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
    max_forbidden_unknown_tokens_per_chapter: int = DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
) -> dict:
    chapter = Path(chapter_path)
    known = Path(known_path)
    known_words = load_known_words(known)
    vocabulary = load_layered_vocabulary(
        known,
        personal_known_words_path=personal_known_words_path,
        known_character_compounds_path=known_character_compounds_path,
        known_character_compound_limit=known_character_compound_limit,
        easy_character_compounds_path=easy_character_compounds_path,
        easy_character_compound_limit=easy_character_compound_limit,
        general_fiction_pack=general_fiction_pack,
        genre_pack=genre_pack,
        setting_pack=setting_pack,
        profession_pack=profession_pack,
        journalism_crime_pack=journalism_crime_pack,
        urban_objects_pack=urban_objects_pack,
        book_specific_words_path=book_specific_words_path,
        proper_nouns_path=proper_nouns_path,
        extra_packs=extra_packs,
    )
    punctuation = load_punctuation(punctuation_path)
    report = validate_text(
        chapter.read_text(encoding="utf-8"),
        known_words,
        punctuation=punctuation,
        vocabulary=vocabulary,
        chapter_name=chapter.name,
        target_core_coverage_percent=target_core_coverage_percent,
        min_known_token_percent=min_known_token_percent,
        max_total_stretch_token_percent=max_total_stretch_token_percent,
        max_easy_character_compound_token_percent=max_easy_character_compound_token_percent,
        max_forbidden_unknown_tokens_per_chapter=max_forbidden_unknown_tokens_per_chapter,
    )
    report.update(
        {
            "schema_version": 6,
            "generated_at": utc_now(),
            "chapter_path": str(chapter),
            "known_words_path": str(known),
            "known_word_count": len(known_words),
            "personal_known_words_path": vocabulary.get("personal_known_words_path"),
            "personal_known_word_count": vocabulary.get("personal_known_word_count", 0),
            "known_character_compounds_path": vocabulary.get("known_character_compounds_path"),
            "known_character_compound_limit": vocabulary.get("known_character_compound_limit", 0),
            "known_character_compound_character_count": vocabulary.get(
                "known_character_compound_character_count", 0
            ),
            "easy_character_compounds_path": vocabulary.get("easy_character_compounds_path"),
            "easy_character_compound_limit": vocabulary.get("easy_character_compound_limit", 0),
            "easy_character_compound_character_count": vocabulary.get(
                "easy_character_compound_character_count", 0
            ),
            "vocabulary_profile": vocabulary.get("vocabulary_profile", "public"),
            "learner_profile_name": vocabulary.get("learner_profile_name"),
            "allowed_token_count": vocabulary["allowed_token_count"],
        }
    )
    return report


def write_json(path: str | Path, payload: dict) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chapter_files(chapters_dir: str | Path) -> list[Path]:
    chapters = sorted(Path(chapters_dir).glob("*.zh-tok.txt"))
    if not chapters:
        raise ValueError(f"No .zh-tok.txt chapter files found in {chapters_dir}")
    return chapters


def validate_book(
    chapters_dir: str | Path,
    known_path: str | Path = DEFAULT_KNOWN_WORDS,
    *,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    personal_known_words_path: str | Path | None = None,
    known_character_compounds_path: str | Path | None = None,
    known_character_compound_limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    easy_character_compounds_path: str | Path | None = DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    easy_character_compound_limit: int = DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
    general_fiction_pack: str | Path | None = None,
    genre_pack: str | Path | None = None,
    setting_pack: str | Path | None = None,
    profession_pack: str | Path | None = None,
    journalism_crime_pack: str | Path | None = None,
    urban_objects_pack: str | Path | None = None,
    book_specific_words_path: str | Path | None = None,
    proper_nouns_path: str | Path | None = None,
    extra_packs: Iterable[str | Path] | None = None,
    target_core_coverage_percent: float | None = None,
    min_known_token_percent: float | None = DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
    max_total_stretch_token_percent: float | None = DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
    max_easy_character_compound_token_percent: float | None = DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
    max_new_stretch_words_per_chapter: int | None = None,
    max_forbidden_unknown_tokens_per_chapter: int = DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
) -> dict:
    known_words = load_known_words(known_path)
    vocabulary = load_layered_vocabulary(
        known_path,
        personal_known_words_path=personal_known_words_path,
        known_character_compounds_path=known_character_compounds_path,
        known_character_compound_limit=known_character_compound_limit,
        easy_character_compounds_path=easy_character_compounds_path,
        easy_character_compound_limit=easy_character_compound_limit,
        general_fiction_pack=general_fiction_pack,
        genre_pack=genre_pack,
        setting_pack=setting_pack,
        profession_pack=profession_pack,
        journalism_crime_pack=journalism_crime_pack,
        urban_objects_pack=urban_objects_pack,
        book_specific_words_path=book_specific_words_path,
        proper_nouns_path=proper_nouns_path,
        extra_packs=extra_packs,
    )
    token_layers = vocabulary["token_layers"]
    known_character_compound_characters = vocabulary.get("known_character_compound_characters", set())
    punctuation = load_punctuation(punctuation_path)
    chapter_reports: list[dict] = []
    aggregate_unknown: Counter[str] = Counter()
    aggregate_high_frequency_character_compounds: Counter[str] = Counter()
    aggregate_easy_character_compounds: Counter[str] = Counter()
    aggregate_unique: set[str] = set()
    layer_counts: Counter[str] = Counter()
    stretch_counts: Counter[str] = Counter()
    stretch_words_by_chapter: dict[str, list[str]] = {}
    new_stretch_words_by_chapter: dict[str, list[str]] = {}
    seen_stretch_words: set[str] = set()
    total_tokens = 0
    warnings: list[dict] = []

    for chapter in chapter_files(chapters_dir):
        report = validate_text(
            chapter.read_text(encoding="utf-8"),
            known_words,
            punctuation=punctuation,
            vocabulary=vocabulary,
            chapter_name=chapter.name,
            target_core_coverage_percent=target_core_coverage_percent,
            min_known_token_percent=min_known_token_percent,
            max_total_stretch_token_percent=max_total_stretch_token_percent,
            max_easy_character_compound_token_percent=max_easy_character_compound_token_percent,
            max_forbidden_unknown_tokens_per_chapter=max_forbidden_unknown_tokens_per_chapter,
        )
        report.update({"chapter_path": str(chapter), "chapter_name": chapter.name})
        chapter_reports.append(report)
        total_tokens += report["total_tokens"]
        aggregate_unique.update(report["unique_tokens"])
        aggregate_unknown.update(report["unknown_token_frequency"])
        aggregate_high_frequency_character_compounds.update(report["high_frequency_character_compound_frequency"])
        aggregate_easy_character_compounds.update(report["easy_character_compound_frequency"])
        for layer, field in LAYER_TOKEN_FIELDS.items():
            layer_counts[layer] += report[field]
        chapter_stretch_words = sorted(
            token for token in report["unique_tokens"] if token_layers.get(token) in STRETCH_LAYERS
        )
        stretch_words_by_chapter[chapter.name] = chapter_stretch_words
        new_words = sorted(set(chapter_stretch_words) - seen_stretch_words)
        new_stretch_words_by_chapter[chapter.name] = new_words
        seen_stretch_words.update(chapter_stretch_words)
        for token in tokens_from_text(chapter.read_text(encoding="utf-8"), punctuation):
            if token_layers.get(token) in STRETCH_LAYERS:
                stretch_counts[token] += 1
        if max_new_stretch_words_per_chapter is not None and len(new_words) > max_new_stretch_words_per_chapter:
            warnings.append(
                {
                    "type": "too_many_new_stretch_words_in_chapter",
                    "chapter": chapter.name,
                    "target": max_new_stretch_words_per_chapter,
                    "actual": len(new_words),
                    "tokens": new_words,
                }
            )

    stretch_words_used_once = sorted(token for token, count in stretch_counts.items() if count == 1)
    if stretch_words_used_once:
        warnings.append(
            {
                "type": "stretch_words_used_once",
                "message": "Approved stretch words used only once should be reviewed for repetition or removal.",
                "tokens": stretch_words_used_once,
            }
        )
    approved_non_core_count = sum(layer_counts[layer] for layer in STRETCH_LAYERS | {PROPER_NOUN_LAYER})
    core_coverage_percent = (layer_counts[CORE_LAYER] / total_tokens * 100) if total_tokens else 0.0
    known_token_percent = (sum(layer_counts[layer] for layer in KNOWN_LAYERS) / total_tokens * 100) if total_tokens else 0.0
    stretch_token_percent = (approved_non_core_count / total_tokens * 100) if total_tokens else 0.0
    easy_character_compound_tokens = sum(aggregate_easy_character_compounds.values())
    easy_character_compound_token_percent = (
        easy_character_compound_tokens / total_tokens * 100
    ) if total_tokens else 0.0
    if target_core_coverage_percent is not None and core_coverage_percent < target_core_coverage_percent:
        warnings.append(
            {
                "type": "core_coverage_below_target",
                "target_percent": target_core_coverage_percent,
                "actual_percent": round(core_coverage_percent, 2),
            }
        )
    known_token_percent_allowed = min_known_token_percent is None or known_token_percent >= min_known_token_percent
    if not known_token_percent_allowed:
        warnings.append(
            {
                "type": "known_token_share_below_minimum",
                "minimum_percent": min_known_token_percent,
                "actual_percent": round(known_token_percent, 2),
            }
        )
    stretch_token_percent_allowed = (
        max_total_stretch_token_percent is None or stretch_token_percent <= max_total_stretch_token_percent
    )
    if max_total_stretch_token_percent is not None and stretch_token_percent > max_total_stretch_token_percent:
        warnings.append(
            {
                "type": "stretch_token_share_above_limit",
                "limit_percent": max_total_stretch_token_percent,
                "actual_percent": round(stretch_token_percent, 2),
            }
        )
    easy_character_compound_token_percent_allowed = (
        max_easy_character_compound_token_percent is None
        or easy_character_compound_token_percent <= max_easy_character_compound_token_percent
    )
    if (
        max_easy_character_compound_token_percent is not None
        and easy_character_compound_token_percent > max_easy_character_compound_token_percent
    ):
        warnings.append(
            {
                "type": "easy_character_compound_share_above_limit",
                "message": "Too much text is made only from the first ranked character-compound band.",
                "limit_percent": max_easy_character_compound_token_percent,
                "actual_percent": round(easy_character_compound_token_percent, 2),
                "easy_character_compound_limit": vocabulary.get(
                    "easy_character_compound_limit", DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT
                ),
            }
        )

    chapters_over_unknown_limit = [
        {
            "chapter_name": report["chapter_name"],
            "forbidden_unknown_tokens": report["forbidden_unknown_tokens"],
            "over_limit": report["forbidden_unknown_tokens_over_limit"],
        }
        for report in chapter_reports
        if report["forbidden_unknown_tokens_over_limit"] > 0
    ]
    forbidden_unknown_tokens_over_limit = sum(item["over_limit"] for item in chapters_over_unknown_limit)

    report = {
        "schema_version": 6,
        "generated_at": utc_now(),
        "valid": all(report["valid"] for report in chapter_reports)
        and known_token_percent_allowed
        and stretch_token_percent_allowed
        and easy_character_compound_token_percent_allowed,
        "known_words_path": str(Path(known_path)),
        "known_word_count": len(known_words),
        "personal_known_words_path": vocabulary.get("personal_known_words_path"),
        "personal_known_word_count": vocabulary.get("personal_known_word_count", 0),
        "known_character_compounds_path": vocabulary.get("known_character_compounds_path"),
        "known_character_compound_limit": vocabulary.get("known_character_compound_limit", 0),
        "known_character_compound_character_count": vocabulary.get("known_character_compound_character_count", 0),
        "easy_character_compounds_path": vocabulary.get("easy_character_compounds_path"),
        "easy_character_compound_limit": vocabulary.get("easy_character_compound_limit", 0),
        "easy_character_compound_character_count": vocabulary.get("easy_character_compound_character_count", 0),
        "vocabulary_profile": vocabulary.get("vocabulary_profile", "public"),
        "learner_profile_name": vocabulary.get("learner_profile_name"),
        "allowed_token_count": vocabulary["allowed_token_count"],
        "chapters_path": str(Path(chapters_dir)),
        "chapter_count": len(chapter_reports),
        "total_tokens": total_tokens,
        "unique_token_count": len(aggregate_unique),
        "unique_tokens": sorted(aggregate_unique),
        "unknown_token_count": sum(aggregate_unknown.values()),
        "unknown_unique_count": len(aggregate_unknown),
        "unknown_token_frequency": dict(sorted(aggregate_unknown.items())),
        "forbidden_unknown_tokens": sum(aggregate_unknown.values()),
        "max_forbidden_unknown_tokens_per_chapter": max_forbidden_unknown_tokens_per_chapter,
        "forbidden_unknown_tokens_over_limit": forbidden_unknown_tokens_over_limit,
        "forbidden_unknown_tokens_allowed": forbidden_unknown_tokens_over_limit == 0,
        "chapters_over_unknown_limit": chapters_over_unknown_limit,
        "forbidden_unknown_token_frequency": dict(sorted(aggregate_unknown.items())),
        "core_coverage_percent": round(core_coverage_percent, 2),
        "known_token_percent": round(known_token_percent, 2),
        "min_known_token_percent": min_known_token_percent,
        "known_token_percent_allowed": known_token_percent_allowed,
        "stretch_token_percent": round(stretch_token_percent, 2),
        "max_total_stretch_token_percent": max_total_stretch_token_percent,
        "stretch_token_percent_allowed": stretch_token_percent_allowed,
        "easy_character_compound_tokens": easy_character_compound_tokens,
        "unique_easy_character_compounds_used": len(aggregate_easy_character_compounds),
        "easy_character_compound_token_percent": round(easy_character_compound_token_percent, 2),
        "max_easy_character_compound_token_percent": max_easy_character_compound_token_percent,
        "easy_character_compound_token_percent_allowed": easy_character_compound_token_percent_allowed,
        "unique_core_words_used": len({token for token in aggregate_unique if token_layers.get(token) == CORE_LAYER}),
        "unique_personal_known_words_used": len(
            {token for token in aggregate_unique if token_layers.get(token) == PERSONAL_KNOWN_LAYER}
        ),
        "unique_high_frequency_character_compounds_used": len(
            {
                token
                for token in aggregate_unique
                if classify_token_layer(token, token_layers, known_character_compound_characters)
                == HIGH_FREQUENCY_CHARACTER_COMPOUND_LAYER
            }
        ),
        "unique_stretch_words_used": len({token for token in aggregate_unique if token_layers.get(token) in STRETCH_LAYERS}),
        "high_frequency_character_compound_frequency": dict(
            sorted(aggregate_high_frequency_character_compounds.items())
        ),
        "easy_character_compound_frequency": dict(sorted(aggregate_easy_character_compounds.items())),
        "stretch_words_used_once": stretch_words_used_once,
        "stretch_words_by_chapter": stretch_words_by_chapter,
        "new_stretch_words_by_chapter": new_stretch_words_by_chapter,
        "warnings": warnings,
        "chapters": chapter_reports,
    }
    report.update({field: layer_counts[layer] for layer, field in LAYER_TOKEN_FIELDS.items()})
    return report


def tokens_from_text(text: str, punctuation: set[str] | None = None) -> list[str]:
    punctuation = punctuation or load_punctuation()
    return [token for _, _, token in iter_story_tokens(text, punctuation)]


def chapter_token_reports(chapters_dir: str | Path, *, punctuation_path: str | Path = DEFAULT_PUNCTUATION) -> list[dict]:
    punctuation = load_punctuation(punctuation_path)
    reports = []
    for chapter in chapter_files(chapters_dir):
        tokens = tokens_from_text(chapter.read_text(encoding="utf-8"), punctuation)
        reports.append(
            {
                "chapter_name": chapter.name,
                "chapter_path": str(chapter),
                "total_tokens": len(tokens),
                "unique_token_count": len(set(tokens)),
                "tokens": tokens,
            }
        )
    return reports


def repeated_phrase_report(
    chapters_dir: str | Path,
    *,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    min_count: int = 3,
    max_items: int = 100,
) -> dict:
    phrase_counts: dict[int, Counter[tuple[str, ...]]] = {2: Counter(), 3: Counter(), 4: Counter()}
    phrase_chapters: dict[tuple[int, tuple[str, ...]], set[str]] = {}
    for chapter in chapter_token_reports(chapters_dir, punctuation_path=punctuation_path):
        tokens = chapter["tokens"]
        for size in (2, 3, 4):
            for index in range(0, max(0, len(tokens) - size + 1)):
                phrase = tuple(tokens[index : index + size])
                phrase_counts[size][phrase] += 1
                phrase_chapters.setdefault((size, phrase), set()).add(chapter["chapter_name"])

    repeated = []
    for size in (2, 3, 4):
        for phrase, count in phrase_counts[size].most_common():
            if count < min_count:
                continue
            warning_level = "high" if count >= 12 else "medium" if count >= 6 else "low"
            repeated.append(
                {
                    "phrase": " ".join(phrase),
                    "token_count": size,
                    "count": count,
                    "chapters": sorted(phrase_chapters[(size, phrase)]),
                    "warning_level": warning_level,
                }
            )
            if len(repeated) >= max_items:
                break
        if len(repeated) >= max_items:
            break

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "chapters_path": str(Path(chapters_dir)),
        "min_count": min_count,
        "repeated_phrases": repeated,
        "phrase_repetition_warning": any(item["warning_level"] in {"medium", "high"} for item in repeated),
    }


def sentence_token_reports(chapters_dir: str | Path, *, punctuation_path: str | Path = DEFAULT_PUNCTUATION) -> list[dict]:
    punctuation = load_punctuation(punctuation_path)
    sentence_endings = set("。！？!?")
    reports = []
    for chapter in chapter_files(chapters_dir):
        sentences = []
        current: list[str] = []
        for raw_token in chapter.read_text(encoding="utf-8").split():
            token = normalize_token(raw_token, punctuation)
            if token:
                current.append(token)
            if any(char in sentence_endings for char in raw_token) and current:
                sentences.append(current)
                current = []
        if current:
            sentences.append(current)
        reports.append({"chapter_name": chapter.name, "chapter_path": str(chapter), "sentences": sentences})
    return reports


def prose_variety_report(
    chapters_dir: str | Path,
    *,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    dialogue_tag_warning_count: int = 10,
    phrase_warning_count: int = 8,
    sentence_frame_warning_count: int = 5,
    max_items: int = 50,
) -> dict:
    sentence_reports = sentence_token_reports(chapters_dir, punctuation_path=punctuation_path)
    phrase_counts: dict[int, Counter[tuple[str, ...]]] = {2: Counter(), 3: Counter(), 4: Counter()}
    dialogue_tags: Counter[str] = Counter()
    sentence_openings: Counter[str] = Counter()
    sentence_endings: Counter[str] = Counter()
    risk_frames = {
        ("我", "不", "知道"),
        ("你", "怎么", "了"),
        ("我们", "要", "走"),
        ("看", "着"),
        ("想", "到"),
    }
    risk_frame_counts: Counter[str] = Counter()
    total_sentences = 0
    total_tokens = 0

    for chapter in sentence_reports:
        for tokens in chapter["sentences"]:
            total_sentences += 1
            total_tokens += len(tokens)
            if tokens:
                sentence_openings[" ".join(tokens[: min(3, len(tokens))])] += 1
                sentence_endings[" ".join(tokens[-min(3, len(tokens)) :])] += 1
            for index, token in enumerate(tokens):
                if token == "说" and index > 0:
                    dialogue_tags[f"{tokens[index - 1]} 说"] += 1
            for size in (2, 3, 4):
                for index in range(0, max(0, len(tokens) - size + 1)):
                    phrase = tuple(tokens[index : index + size])
                    phrase_counts[size][phrase] += 1
                    if phrase in risk_frames:
                        risk_frame_counts[" ".join(phrase)] += 1

    repeated_phrases = []
    for size in (2, 3, 4):
        for phrase, count in phrase_counts[size].most_common():
            if count < phrase_warning_count:
                continue
            repeated_phrases.append({"phrase": " ".join(phrase), "token_count": size, "count": count})
            if len(repeated_phrases) >= max_items:
                break
        if len(repeated_phrases) >= max_items:
            break

    repeated_dialogue_tags = [
        {"frame": frame, "count": count}
        for frame, count in dialogue_tags.most_common(max_items)
        if count >= dialogue_tag_warning_count
    ]
    repeated_openings = [
        {"frame": frame, "count": count}
        for frame, count in sentence_openings.most_common(max_items)
        if count >= sentence_frame_warning_count
    ]
    repeated_endings = [
        {"frame": frame, "count": count}
        for frame, count in sentence_endings.most_common(max_items)
        if count >= sentence_frame_warning_count
    ]
    visible_risk_frames = [
        {"frame": frame, "count": count}
        for frame, count in risk_frame_counts.most_common(max_items)
        if count >= sentence_frame_warning_count
    ]
    warnings = []
    if repeated_dialogue_tags:
        warnings.append(
            {
                "type": "repeated_dialogue_tags",
                "message": "Visible X 说 repetition should trigger a prose-variety polish pass.",
                "items": repeated_dialogue_tags,
            }
        )
    if repeated_phrases:
        warnings.append(
            {
                "type": "repeated_phrase_frames",
                "message": "High-count repeated phrase frames should be reviewed for mechanical rhythm.",
                "items": repeated_phrases[:10],
            }
        )
    if repeated_openings or repeated_endings:
        warnings.append(
            {
                "type": "repeated_sentence_frames",
                "message": "Repeated sentence openings or endings can make chapters feel formulaic.",
                "openings": repeated_openings[:10],
                "endings": repeated_endings[:10],
            }
        )
    if visible_risk_frames:
        warnings.append(
            {
                "type": "known_risk_frames",
                "message": "Common flat frames appear often enough to require review.",
                "items": visible_risk_frames,
            }
        )

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "chapters_path": str(Path(chapters_dir)),
        "chapter_count": len(sentence_reports),
        "sentence_count": total_sentences,
        "total_tokens": total_tokens,
        "dialogue_tag_warning_count": dialogue_tag_warning_count,
        "phrase_warning_count": phrase_warning_count,
        "sentence_frame_warning_count": sentence_frame_warning_count,
        "top_dialogue_tags": [{"frame": frame, "count": count} for frame, count in dialogue_tags.most_common(25)],
        "repeated_dialogue_tags": repeated_dialogue_tags,
        "repeated_phrase_frames": repeated_phrases,
        "repeated_sentence_openings": repeated_openings,
        "repeated_sentence_endings": repeated_endings,
        "known_risk_frames": visible_risk_frames,
        "warnings": warnings,
        "style_revision_required": bool(warnings),
        "counts_are_revision_evidence_not_final_literary_judgment": True,
    }


def vocabulary_usage_report(
    chapters_dir: str | Path,
    known_path: str | Path = DEFAULT_KNOWN_WORDS,
    *,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    min_chapter_unique_tokens: int = 0,
    target_coverage_percent: float = 0.0,
    warn_top_20_share_above_percent: float = 45.0,
) -> dict:
    known_words = load_known_words(known_path)
    known_set = set(known_words)
    chapter_reports = chapter_token_reports(chapters_dir, punctuation_path=punctuation_path)
    all_tokens: list[str] = []
    chapter_summaries = []
    for chapter in chapter_reports:
        tokens = chapter["tokens"]
        unique_count = len(set(tokens))
        all_tokens.extend(tokens)
        chapter_summaries.append(
            {
                "chapter_name": chapter["chapter_name"],
                "chapter_path": chapter["chapter_path"],
                "total_tokens": chapter["total_tokens"],
                "unique_token_count": unique_count,
                "unique_target": min_chapter_unique_tokens,
                "narrow_vocabulary_warning": min_chapter_unique_tokens > 0 and unique_count < min_chapter_unique_tokens,
            }
        )

    counts = Counter(all_tokens)
    unique_tokens = set(all_tokens)
    top_20_total = sum(count for _, count in counts.most_common(20))
    top_20_share = (top_20_total / len(all_tokens) * 100) if all_tokens else 0.0
    coverage = (len(unique_tokens & known_set) / len(known_words) * 100) if known_words else 0.0
    phrase_report = repeated_phrase_report(chapters_dir, punctuation_path=punctuation_path)

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "known_words_path": str(Path(known_path)),
        "known_word_count": len(known_words),
        "chapters_path": str(Path(chapters_dir)),
        "chapter_count": len(chapter_reports),
        "total_tokens": len(all_tokens),
        "unique_token_count": len(unique_tokens),
        "known_word_coverage_percent": round(coverage, 2),
        "target_whole_book_known_word_coverage_percent": target_coverage_percent,
        "top_20_token_share_percent": round(top_20_share, 2),
        "warn_if_top_20_token_share_above_percent": warn_top_20_share_above_percent,
        "top_25_tokens": [{"token": token, "count": count} for token, count in counts.most_common(25)],
        "top_25_non_punctuation_tokens": [{"token": token, "count": count} for token, count in counts.most_common(25)],
        "chapter_unique_token_counts": chapter_summaries,
        "whole_book_unique_token_count": len(unique_tokens),
        "unused_known_words": [word for word in known_words if word not in unique_tokens],
        "unused_known_word_count": len([word for word in known_words if word not in unique_tokens]),
        "overused_token_warnings": [
            {"token": token, "count": count}
            for token, count in counts.most_common(20)
            if len(all_tokens) and (count / len(all_tokens) * 100) >= 5
        ],
        "narrow_vocabulary_warning": target_coverage_percent > 0 and coverage < target_coverage_percent,
        "top_20_dominance_warning": top_20_share > warn_top_20_share_above_percent,
        "repeated_phrase_warning": phrase_report["phrase_repetition_warning"],
        "quality_targets_are_advisory": True,
        "counts_are_diagnostics_not_acceptance_gates": True,
        "padding_for_counts_is_quality_failure": True,
    }


def quality_decision_path(manuscript_dir: str | Path) -> Path:
    return Path(manuscript_dir) / "quality" / QUALITY_DECISION_FILE


def quality_approval_status(manuscript_dir: str | Path) -> dict:
    decision = quality_decision_path(manuscript_dir)
    if not decision.exists():
        return {
            "approved": False,
            "decision_path": str(decision),
            "decision": "MISSING",
            "reason": "Lead quality decision file is missing.",
        }
    text = decision.read_text(encoding="utf-8")
    approved = bool(
        re.search(r"(?im)^\s*(final\s+decision|decision)\s*:\s*PASS\s*$", text)
        or re.search(r"(?im)^\s*PASS\s*$", text)
    )
    match = re.search(r"(?im)^\s*(?:final\s+decision|decision)\s*:\s*([A-Z_]+)\s*$", text)
    return {
        "approved": approved,
        "decision_path": str(decision),
        "decision": match.group(1) if match else ("PASS" if approved else "UNRECOGNIZED"),
        "reason": "Lead quality decision must explicitly be PASS." if not approved else "Approved by lead quality decision.",
    }


def ensure_quality_approval(manuscript_dir: str | Path) -> dict:
    status = quality_approval_status(manuscript_dir)
    if not status["approved"]:
        raise ValueError(f"Cannot build EPUB before lead quality approval: {status['reason']}")
    return status


def render_tokenized_line(line: str, *, remove_spaces: bool = True) -> str:
    if remove_spaces:
        return "".join(line.split())
    return " ".join(line.split())


def render_chapter_text(text: str, *, remove_spaces: bool = True) -> list[str]:
    return [render_tokenized_line(line, remove_spaces=remove_spaces) for line in text.splitlines() if line.strip()]


def _xhtml(title: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN" lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
{body}
</body>
</html>
"""


def _nav_xhtml(title: str, chapter_count: int, include_appendix: bool) -> str:
    items = ['<li><a href="title_page.xhtml">Title Page</a></li>']
    items.extend(f'<li><a href="chapter_{index:02d}.xhtml">Chapter {index}</a></li>' for index in range(1, chapter_count + 1))
    if include_appendix:
        items.append('<li><a href="appendix.xhtml">Validation Appendix</a></li>')
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en" lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<nav epub:type="toc" id="toc">
  <h1>{html.escape(title)}</h1>
  <ol>
    {''.join(items)}
  </ol>
</nav>
</body>
</html>
"""


def build_epub(
    manuscript_dir: str | Path,
    title: str,
    out_path: str | Path,
    *,
    known_path: str | Path = DEFAULT_KNOWN_WORDS,
    punctuation_path: str | Path = DEFAULT_PUNCTUATION,
    personal_known_words_path: str | Path | None = None,
    known_character_compounds_path: str | Path | None = None,
    known_character_compound_limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    easy_character_compounds_path: str | Path | None = DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    easy_character_compound_limit: int = DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
    general_fiction_pack: str | Path | None = None,
    genre_pack: str | Path | None = None,
    setting_pack: str | Path | None = None,
    profession_pack: str | Path | None = None,
    journalism_crime_pack: str | Path | None = None,
    urban_objects_pack: str | Path | None = None,
    book_specific_words_path: str | Path | None = None,
    proper_nouns_path: str | Path | None = None,
    extra_packs: Iterable[str | Path] | None = None,
    min_known_token_percent: float | None = DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
    max_total_stretch_token_percent: float | None = DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
    max_easy_character_compound_token_percent: float | None = DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
    max_forbidden_unknown_tokens_per_chapter: int = DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    remove_spaces: bool = True,
    include_validation_appendix: bool = True,
    require_quality_approval: bool = True,
) -> dict:
    manuscript = Path(manuscript_dir)
    chapters_dir = manuscript / "chapters"
    validation = validate_book(
        chapters_dir,
        known_path,
        punctuation_path=punctuation_path,
        personal_known_words_path=personal_known_words_path,
        known_character_compounds_path=known_character_compounds_path,
        known_character_compound_limit=known_character_compound_limit,
        easy_character_compounds_path=easy_character_compounds_path,
        easy_character_compound_limit=easy_character_compound_limit,
        general_fiction_pack=general_fiction_pack,
        genre_pack=genre_pack,
        setting_pack=setting_pack,
        profession_pack=profession_pack,
        journalism_crime_pack=journalism_crime_pack,
        urban_objects_pack=urban_objects_pack,
        book_specific_words_path=book_specific_words_path,
        proper_nouns_path=proper_nouns_path,
        extra_packs=extra_packs,
        min_known_token_percent=min_known_token_percent,
        max_total_stretch_token_percent=max_total_stretch_token_percent,
        max_easy_character_compound_token_percent=max_easy_character_compound_token_percent,
        max_forbidden_unknown_tokens_per_chapter=max_forbidden_unknown_tokens_per_chapter,
    )
    if not validation["valid"]:
        reasons = []
        if validation["forbidden_unknown_tokens_over_limit"]:
            reasons.append(
                f"{validation['forbidden_unknown_tokens_over_limit']} forbidden unknown token(s) over the "
                f"per-chapter limit of {validation['max_forbidden_unknown_tokens_per_chapter']}"
            )
        if not validation.get("known_token_percent_allowed", True):
            reasons.append(
                f"known-token share {validation['known_token_percent']}% below "
                f"{validation['min_known_token_percent']}%"
            )
        if not validation.get("stretch_token_percent_allowed", True):
            reasons.append(
                f"approved non-core token share {validation['stretch_token_percent']}% above "
                f"{validation['max_total_stretch_token_percent']}%"
            )
        if not validation.get("easy_character_compound_token_percent_allowed", True):
            reasons.append(
                f"first-{validation['easy_character_compound_limit']} character-compound token share "
                f"{validation['easy_character_compound_token_percent']}% above "
                f"{validation['max_easy_character_compound_token_percent']}%"
            )
        if not reasons:
            reasons.append("see vocabulary_report.json warnings")
        raise ValueError(
            "Cannot build EPUB because vocabulary validation failed: " + "; ".join(reasons)
        )
    quality_status = ensure_quality_approval(manuscript) if require_quality_approval else quality_approval_status(manuscript)

    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    chapters = chapter_files(chapters_dir)
    book_id = f"urn:uuid:{uuid.uuid4()}"
    modified = utc_now()

    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
        '<item id="title_page" href="title_page.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine = ['<itemref idref="title_page"/>']
    for index in range(1, len(chapters) + 1):
        manifest.append(f'<item id="chapter_{index:02d}" href="chapter_{index:02d}.xhtml" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="chapter_{index:02d}"/>')
    if include_validation_appendix:
        manifest.append('<item id="appendix" href="appendix.xhtml" media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="appendix"/>')

    content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{book_id}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:language>zh-CN</dc:language>
    <meta property="dcterms:modified">{modified}</meta>
  </metadata>
  <manifest>{''.join(manifest)}</manifest>
  <spine>{''.join(spine)}</spine>
</package>
"""
    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    css = """
body { font-family: serif; line-height: 1.8; margin: 5%; }
h1, h2 { font-family: sans-serif; line-height: 1.3; }
p { margin: 0 0 1em 0; }
code { font-family: monospace; }
"""

    with zipfile.ZipFile(output, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, "application/epub+zip")
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/style.css", css)
        zf.writestr("OEBPS/nav.xhtml", _nav_xhtml(title, len(chapters), include_validation_appendix))
        zf.writestr("OEBPS/title_page.xhtml", _xhtml(title, f"<h1>{html.escape(title)}</h1>"))

        for index, chapter in enumerate(chapters, start=1):
            rendered_lines = render_chapter_text(chapter.read_text(encoding="utf-8"), remove_spaces=remove_spaces)
            paragraphs = "\n".join(f"<p>{html.escape(line)}</p>" for line in rendered_lines)
            body = f"<h1>{html.escape(title)}</h1>\n<h2>Chapter {index}</h2>\n{paragraphs}" if index == 1 else f"<h2>Chapter {index}</h2>\n{paragraphs}"
            zf.writestr(f"OEBPS/chapter_{index:02d}.xhtml", _xhtml(f"{title} - Chapter {index}", body))

        if include_validation_appendix:
            appendix = f"""
<h1>Validation Appendix</h1>
<p>Canonical validation was run on the space-tokenized .zh-tok.txt source files.</p>
<p>Total word tokens: <code>{validation['total_tokens']}</code></p>
<p>Unique used words: <code>{validation['unique_token_count']}</code></p>
<p>Core known tokens: <code>{validation['core_known_tokens']}</code></p>
<p>Vocabulary profile: <code>{validation.get('vocabulary_profile', 'public')}</code></p>
<p>Personal known tokens: <code>{validation.get('personal_known_tokens', 0)}</code></p>
<p>High-frequency character-compound tokens: <code>{validation.get('high_frequency_character_compound_tokens', 0)}</code></p>
<p>First-{validation.get('easy_character_compound_limit', 0)} character-compound token percent: <code>{validation.get('easy_character_compound_token_percent', 0)}</code></p>
<p>Maximum first-{validation.get('easy_character_compound_limit', 0)} character-compound token percent: <code>{validation.get('max_easy_character_compound_token_percent')}</code></p>
<p>Known-token percent: <code>{validation['known_token_percent']}</code></p>
<p>Minimum known-token percent: <code>{validation['min_known_token_percent']}</code></p>
<p>Stretch-token percent: <code>{validation['stretch_token_percent']}</code></p>
<p>Maximum approved non-core token percent: <code>{validation['max_total_stretch_token_percent']}</code></p>
<p>Unknown-token count: <code>{validation['unknown_token_count']}</code></p>
<p>Allowed forbidden unknown tokens per chapter: <code>{validation['max_forbidden_unknown_tokens_per_chapter']}</code></p>
<p>Forbidden unknown tokens over limit: <code>{validation['forbidden_unknown_tokens_over_limit']}</code></p>
"""
            zf.writestr("OEBPS/appendix.xhtml", _xhtml("Validation Appendix", appendix))

    return {
        "epub_path": str(output),
        "valid": True,
        "chapter_count": validation["chapter_count"],
        "total_tokens": validation["total_tokens"],
        "unique_token_count": validation["unique_token_count"],
        "core_known_tokens": validation["core_known_tokens"],
        "vocabulary_profile": validation.get("vocabulary_profile", "public"),
        "known_token_percent": validation.get("known_token_percent", 0),
        "min_known_token_percent": validation.get("min_known_token_percent"),
        "known_token_percent_allowed": validation.get("known_token_percent_allowed", True),
        "stretch_token_percent": validation.get("stretch_token_percent", 0),
        "max_total_stretch_token_percent": validation.get("max_total_stretch_token_percent"),
        "stretch_token_percent_allowed": validation.get("stretch_token_percent_allowed", True),
        "learner_profile_name": validation.get("learner_profile_name"),
        "personal_known_tokens": validation.get("personal_known_tokens", 0),
        "personal_known_word_count": validation.get("personal_known_word_count", 0),
        "unique_personal_known_words_used": validation.get("unique_personal_known_words_used", 0),
        "known_character_compounds_path": validation.get("known_character_compounds_path"),
        "known_character_compound_limit": validation.get("known_character_compound_limit", 0),
        "known_character_compound_character_count": validation.get("known_character_compound_character_count", 0),
        "easy_character_compounds_path": validation.get("easy_character_compounds_path"),
        "easy_character_compound_limit": validation.get("easy_character_compound_limit", 0),
        "easy_character_compound_character_count": validation.get("easy_character_compound_character_count", 0),
        "easy_character_compound_tokens": validation.get("easy_character_compound_tokens", 0),
        "unique_easy_character_compounds_used": validation.get("unique_easy_character_compounds_used", 0),
        "easy_character_compound_token_percent": validation.get("easy_character_compound_token_percent", 0),
        "max_easy_character_compound_token_percent": validation.get("max_easy_character_compound_token_percent"),
        "easy_character_compound_token_percent_allowed": validation.get(
            "easy_character_compound_token_percent_allowed", True
        ),
        "high_frequency_character_compound_tokens": validation.get(
            "high_frequency_character_compound_tokens", 0
        ),
        "unique_high_frequency_character_compounds_used": validation.get(
            "unique_high_frequency_character_compounds_used", 0
        ),
        "unknown_token_count": validation["unknown_token_count"],
        "forbidden_unknown_tokens_over_limit": validation["forbidden_unknown_tokens_over_limit"],
        "max_forbidden_unknown_tokens_per_chapter": validation["max_forbidden_unknown_tokens_per_chapter"],
        "quality_approval": quality_status,
        "built_at": utc_now(),
    }


def check_epub_structure(path: str | Path) -> dict:
    epub = Path(path)
    with zipfile.ZipFile(epub) as zf:
        names = zf.namelist()
        return {
            "path": str(epub),
            "exists": epub.exists(),
            "first_entry": names[0] if names else None,
            "mimetype": zf.read("mimetype").decode("ascii") if "mimetype" in names else None,
            "has_container": "META-INF/container.xml" in names,
            "has_opf": "OEBPS/content.opf" in names,
            "has_nav": "OEBPS/nav.xhtml" in names,
            "has_title_page": "OEBPS/title_page.xhtml" in names,
            "chapter_count": len([name for name in names if name.startswith("OEBPS/chapter_") and name.endswith(".xhtml")]),
        }
