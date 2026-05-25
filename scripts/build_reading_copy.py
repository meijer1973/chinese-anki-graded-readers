from __future__ import annotations

import argparse
from pathlib import Path

try:
    from novel_tools import chapter_files, render_chapter_text
except ModuleNotFoundError:
    from scripts.novel_tools import chapter_files, render_chapter_text


def build_reading_copy(manuscript: str | Path, out_path: str | Path, *, title: str | None = None) -> dict:
    manuscript_path = Path(manuscript)
    chapters = chapter_files(manuscript_path / "chapters")
    output = Path(out_path)
    display_title = title or manuscript_path.name
    lines = [
        f"# {display_title}",
        "",
        "> Noncanonical review copy. Validate and edit `chapters/*.zh-tok.txt`, not this rendered file.",
        "",
    ]
    for index, chapter in enumerate(chapters, start=1):
        lines.extend([f"## Chapter {index}", ""])
        rendered = render_chapter_text(chapter.read_text(encoding="utf-8"), remove_spaces=True)
        lines.extend(rendered)
        lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"out_path": str(output), "chapter_count": len(chapters), "title": display_title}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a noncanonical natural Chinese reading copy for review.")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--title")
    args = parser.parse_args()

    report = build_reading_copy(args.manuscript, args.out, title=args.title)
    print("reading_copy={out_path} chapters={chapter_count}".format(**report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
