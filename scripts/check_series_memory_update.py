from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from novel_tools import write_json
except ModuleNotFoundError:
    from scripts.novel_tools import write_json


REQUIRED_MANUSCRIPT_FILES = [
    "novel_bible.md",
    "outline.md",
    "continuity_log.md",
    "quality/lead_quality_decision.md",
]

REQUIRED_SERIES_FILES = [
    "series_bible.md",
    "chronology.md",
    "character_registry.md",
    "mechanism_registry.md",
    "open_threads.md",
    "sequel_constraints.md",
    "series_update_log.md",
]

LEAD_PASS_RE = re.compile(r"(?im)^\s*(final\s+decision|decision)\s*:\s*PASS\s*$|^\s*PASS\s*$")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _relative_missing(root: Path, relative_paths: list[str]) -> list[str]:
    return [str(root / relative_path) for relative_path in relative_paths if not (root / relative_path).exists()]


def lead_quality_passed(manuscript: Path) -> bool:
    return bool(LEAD_PASS_RE.search(_read_text(manuscript / "quality" / "lead_quality_decision.md")))


def chronology_mentions_manuscript(series_dir: Path, manuscript: Path) -> bool:
    text = _read_text(series_dir / "chronology.md")
    slug = manuscript.name
    normalized_path = f"manuscripts/{slug}".replace("\\", "/")
    return slug in text or normalized_path in text


def update_log_mentions_manuscript(series_dir: Path, manuscript: Path) -> bool:
    text = _read_text(series_dir / "series_update_log.md")
    slug = manuscript.name
    normalized_path = f"manuscripts/{slug}".replace("\\", "/")
    return slug in text or normalized_path in text


def epub_build_succeeded(manuscript: Path) -> bool:
    epub_dir = manuscript / "epub"
    report_path = epub_dir / "build_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        structure = report.get("epub_structure", {})
        if structure.get("exists") and structure.get("has_container") and structure.get("has_opf"):
            return True
        epub_path = report.get("epub_path")
        if epub_path and Path(epub_path).exists():
            return True
    return epub_dir.exists() and any(epub_dir.glob("*.epub"))


def build_series_memory_status(
    manuscript: str | Path,
    series_dir: str | Path,
    *,
    require_epub_build: bool = False,
) -> dict:
    manuscript_path = Path(manuscript)
    series_path = Path(series_dir)
    missing_manuscript_files = _relative_missing(manuscript_path, REQUIRED_MANUSCRIPT_FILES)
    missing_series_files = _relative_missing(series_path, REQUIRED_SERIES_FILES)
    lead_pass = lead_quality_passed(manuscript_path)
    chronology_updated = chronology_mentions_manuscript(series_path, manuscript_path)
    update_log_updated = update_log_mentions_manuscript(series_path, manuscript_path)
    epub_ok = epub_build_succeeded(manuscript_path) if require_epub_build else None

    blocking_reasons: list[str] = []
    if missing_manuscript_files:
        blocking_reasons.append("missing required manuscript files")
    if missing_series_files:
        blocking_reasons.append("missing required series memory files")
    if not lead_pass:
        blocking_reasons.append("lead quality decision is not PASS")
    if not chronology_updated:
        blocking_reasons.append("chronology does not mention the manuscript")
    if not update_log_updated:
        blocking_reasons.append("series_update_log does not mention the manuscript")
    if require_epub_build and not epub_ok:
        blocking_reasons.append("EPUB build success was required but not found")

    return {
        "schema_version": 1,
        "manuscript_path": str(manuscript_path),
        "manuscript_slug": manuscript_path.name,
        "series_dir": str(series_path),
        "required_manuscript_files": REQUIRED_MANUSCRIPT_FILES,
        "required_series_files": REQUIRED_SERIES_FILES,
        "missing_manuscript_files": missing_manuscript_files,
        "missing_series_files": missing_series_files,
        "lead_quality_passed": lead_pass,
        "chronology_mentions_manuscript": chronology_updated,
        "series_update_log_mentions_manuscript": update_log_updated,
        "require_epub_build": require_epub_build,
        "epub_build_succeeded": epub_ok,
        "series_memory_update_complete": not blocking_reasons,
        "blocking_reasons": blocking_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that an accepted story updated the living series memory package.")
    parser.add_argument("--manuscript", required=True, help="Path to manuscripts/<slug>.")
    parser.add_argument("--series-dir", default="series/an-lin", help="Path to the living series memory directory.")
    parser.add_argument(
        "--require-epub-build",
        action="store_true",
        help="Require an EPUB build report or EPUB file before the series memory update can pass.",
    )
    parser.add_argument("--out", help="Optional JSON status report path.")
    args = parser.parse_args()

    status = build_series_memory_status(
        args.manuscript,
        args.series_dir,
        require_epub_build=args.require_epub_build,
    )
    if args.out:
        write_json(args.out, status)
    print(
        "series_memory_update_complete={complete} manuscript={slug} "
        "lead_quality_passed={lead} chronology_updated={chronology} "
        "update_log_updated={update_log} blocking_reasons={reasons}".format(
            complete=status["series_memory_update_complete"],
            slug=status["manuscript_slug"],
            lead=status["lead_quality_passed"],
            chronology=status["chronology_mentions_manuscript"],
            update_log=status["series_update_log_mentions_manuscript"],
            reasons="; ".join(status["blocking_reasons"]) or "none",
        )
    )
    return 0 if status["series_memory_update_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
