from __future__ import annotations

import argparse
from pathlib import Path

try:
    from novel_tools import (
        DEFAULT_KNOWN_WORDS,
        DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
        DEFAULT_PUNCTUATION,
        chapter_files,
        quality_approval_status,
        repeated_phrase_report,
        validate_book,
        vocabulary_usage_report,
        write_json,
    )
except ModuleNotFoundError:
    from scripts.novel_tools import (
        DEFAULT_KNOWN_WORDS,
        DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
        DEFAULT_PUNCTUATION,
        chapter_files,
        quality_approval_status,
        repeated_phrase_report,
        validate_book,
        vocabulary_usage_report,
        write_json,
    )


def write_if_missing(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(text.rstrip() + "\n", encoding="utf-8")


def init_quality_templates(quality_dir: Path) -> None:
    write_if_missing(
        quality_dir / "literary_critic_report.md",
        """# Literary Critic Report

Score: PENDING
Recommendation: PENDING

## Top 5 Strengths

## Top 10 Problems

## Chapter Notes

## Specific Polish Recommendations

Too conservative: PENDING
Too repetitive: PENDING
Vocabulary use artificially narrow: PENDING
Fantasy/setting stretch vocabulary useful: PENDING
Professions/social roles meaningful: PENDING
""",
    )
    write_if_missing(
        quality_dir / "normal_reader_report.md",
        """# Normal Reader Report

Score: PENDING
Recommendation: PENDING

## Boredom Points

## Confusing Points

## Favorite Moments

## Least Interesting Chapters

Would continue after chapter 1: PENDING
Would finish the book: PENDING
City felt alive: PENDING
Stretch words too hard: PENDING
""",
    )
    write_if_missing(
        quality_dir / "lead_quality_decision.md",
        """# Lead Quality Decision

Final decision: PENDING

## Required Next Action

## Reasons

## Blocking Issues

## Non-Blocking Issues

Polish allowed: PENDING
Complete rebuild required: PENDING
Stretch vocabulary status: PENDING
Unknown-token budget status: PENDING
EPUB build allowed: PENDING

## Instructions For Next Writer Agent
""",
    )


def expected_vocab_plan_path(manuscript: Path, chapter: Path) -> Path:
    stem = chapter.name.replace(".zh-tok.txt", "")
    chapter_number = stem.replace("chapter_", "")
    return manuscript / "planning" / f"chapter_{chapter_number}_vocab_plan.md"


def chapter_planning_status(manuscript: Path) -> dict:
    chapters = chapter_files(manuscript / "chapters")
    expected = [expected_vocab_plan_path(manuscript, chapter) for chapter in chapters]
    missing = [path for path in expected if not path.exists()]
    return {
        "planning_files_present": not missing,
        "expected_planning_file_count": len(expected),
        "planning_file_count": len(expected) - len(missing),
        "missing_chapter_planning_files": [str(path) for path in missing],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create quality evidence artifacts for a manuscript.")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--general-fiction-pack")
    parser.add_argument("--genre-pack")
    parser.add_argument("--setting-pack")
    parser.add_argument("--profession-pack")
    parser.add_argument("--journalism-crime-pack")
    parser.add_argument("--urban-objects-pack")
    parser.add_argument("--book-specific")
    parser.add_argument("--proper-nouns")
    parser.add_argument("--extra-pack", action="append", default=[])
    parser.add_argument(
        "--max-forbidden-unknown-tokens-per-chapter",
        type=int,
        default=DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    )
    args = parser.parse_args()

    manuscript = Path(args.manuscript)
    chapters = manuscript / "chapters"
    quality = manuscript / "quality"
    quality.mkdir(parents=True, exist_ok=True)

    validation = validate_book(
        chapters,
        args.known,
        punctuation_path=args.punctuation,
        general_fiction_pack=args.general_fiction_pack,
        genre_pack=args.genre_pack,
        setting_pack=args.setting_pack,
        profession_pack=args.profession_pack,
        journalism_crime_pack=args.journalism_crime_pack,
        urban_objects_pack=args.urban_objects_pack,
        book_specific_words_path=args.book_specific,
        proper_nouns_path=args.proper_nouns,
        extra_packs=args.extra_pack,
        max_forbidden_unknown_tokens_per_chapter=args.max_forbidden_unknown_tokens_per_chapter,
    )
    write_json(manuscript / "vocabulary_report.json", validation)
    usage = vocabulary_usage_report(chapters, args.known, punctuation_path=args.punctuation)
    write_json(quality / "vocabulary_usage_report.json", usage)
    phrases = repeated_phrase_report(chapters, punctuation_path=args.punctuation)
    write_json(quality / "repeated_phrase_report.json", phrases)
    init_quality_templates(quality)
    status = quality_approval_status(manuscript)
    planning_status = chapter_planning_status(manuscript)
    summary = {
        "valid_vocabulary": validation["valid"],
        "unknown_token_count": validation["unknown_token_count"],
        "forbidden_unknown_tokens": validation.get("forbidden_unknown_tokens", validation["unknown_token_count"]),
        "forbidden_unknown_tokens_over_limit": validation.get("forbidden_unknown_tokens_over_limit", 0),
        "max_forbidden_unknown_tokens_per_chapter": validation.get(
            "max_forbidden_unknown_tokens_per_chapter",
            args.max_forbidden_unknown_tokens_per_chapter,
        ),
        "stretch_token_percent": validation.get("stretch_token_percent", 0),
        **planning_status,
        "quality_approval": status,
        "ready_for_epub": validation["valid"] and status["approved"] and planning_status["planning_files_present"],
    }
    write_json(quality / "quality_gate_summary.json", summary)
    print(
        "valid_vocabulary={valid_vocabulary} unknown_tokens={unknown_token_count} "
        "planning_files_present={planning} quality_approved={approved} ready_for_epub={ready}".format(
            valid_vocabulary=summary["valid_vocabulary"],
            unknown_token_count=summary["unknown_token_count"],
            planning=summary["planning_files_present"],
            approved=status["approved"],
            ready=summary["ready_for_epub"],
        )
    )
    return 0 if summary["valid_vocabulary"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
