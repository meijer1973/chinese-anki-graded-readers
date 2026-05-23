---
name: epub-export
description: Export validated restricted-vocabulary Chinese manuscripts to EPUB. Use when Codex needs to build an EPUB from a manuscript project folder, run whole-book validation first, include validation statistics, or check EPUB zip structure.
---

# EPUB Export

Build EPUBs only after whole-book vocabulary validation passes under the configured per-chapter forbidden-unknown budget and `quality/lead_quality_decision.md` explicitly says `Final decision: PASS`.

## Command

```powershell
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json
```

The builder runs validation and quality approval checks again before writing. It refuses to export when a chapter exceeds the forbidden-unknown budget or lead quality approval is missing.

## Output Rules

- Build from validated `.zh-tok.txt` chapter files.
- Save under `manuscripts/<project-slug>/epub/`.
- Include a title page/table of contents structure, chapters, and the validation appendix by default.
- Display text may remove token spaces for readability, but the `.zh-tok.txt` source remains canonical.
- Run the EPUB structural check and report path, chapter count, total tokens, unique words, unknown tokens, lead quality decision, and build status.
