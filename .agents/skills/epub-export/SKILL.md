---
name: epub-export
description: Export validated restricted-vocabulary Chinese manuscripts to EPUB. Use when Codex needs to build an EPUB from a manuscript project folder, run whole-book validation first, include validation statistics, or check EPUB zip structure.
---

# EPUB Export

Build EPUBs only after whole-book vocabulary validation passes under the configured per-chapter forbidden-unknown budget, the 98% known-token floor, the 2% approved non-core ceiling, the 95% first-500 character-compound ceiling, and `quality/lead_quality_decision.md` explicitly says `Final decision: PASS`.

For adapted manuscripts, also require `quality/source_fidelity_report.md` with `Fidelity decision: PASS` and run the quality gate with `--require-source-fidelity` before export.

## Public Graded-Reader Command

```powershell
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json
```

## Marcel Personalized Command

```powershell
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json --personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 2100
```

Add the same stretch pack arguments used during validation, such as `--journalism-crime-pack data/stretch_packs/journalism_crime_50.txt`, `--genre-pack`, `--setting-pack`, `--profession-pack`, `--urban-objects-pack`, `--book-specific`, `--proper-nouns`, and any `--extra-pack`.

The builder runs validation and quality approval checks again before writing. It refuses to export when a chapter exceeds the forbidden-unknown budget, the manuscript exceeds the first-500 character-compound ceiling, or lead quality approval is missing. The build report includes `vocabulary_profile`, `personal_known_tokens`, `unique_personal_known_words_used`, high-frequency character-compound counts when a learner profile uses them, and `easy_character_compound_token_percent`.

## Output Rules

- Build from validated `.zh-tok.txt` chapter files.
- Save under `manuscripts/<project-slug>/epub/`.
- Include proper chapter entries, a title page/table of contents structure, chapters, and the validation appendix by default.
- Display text may remove token spaces for readability, but the `.zh-tok.txt` source remains canonical.
- Run the EPUB structural check and report path, chapter count, total tokens, unique words, vocabulary profile, personal-known token count and high-frequency character-compound token count when used, first-500 character-compound percentage, unknown tokens, lead quality decision, and build status.
- Format the final delivery with `docs/completion-response-template.md`: delivered title and files first, then the metrics table, content summary, package contents, and limitations.
- Do not export or report a rough or intermediate draft as a completed book. If prose quality, validation, lead approval, or EPUB structure is incomplete, report the blocker instead.
