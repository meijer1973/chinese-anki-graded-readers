# Chinese Anki And Graded Reader Tools

This repository maintains a Chinese vocabulary Anki deck and a controlled-vocabulary fiction pipeline for generating auditable Chinese graded-reader stories.

## Main Workflows

- Build Anki TSV exports from `word list chinese.txt` with `build_anki_chinese.py`.
- Keep curated sentence and pinyin fixes in `sentence_example_overrides.py`.
- Maintain the active known-word file in `data/known_words.txt`.
- Generate restricted-vocabulary Chinese manuscripts under `manuscripts/<slug>/`.
- Validate tokenized chapters with `scripts/validate_chapter.py` and `scripts/validate_book.py`.
- Run quality review with `scripts/run_quality_gate.py`.
- Build EPUB files with `scripts/build_epub.py` after validation and lead approval.

The first series manuscript is `manuscripts/shanghai-rain-gate-crime/` (`上海雨票案`).

## Machine-Readable Entry Points

Remote agents should start with:

- `AGENT_GITHUB_ENTRY.md`
- `RESEARCH_AGENT_MAP.md`
- `RESEARCH_AGENT_PROMPT.md`
- `repo_manifest.json`
- `reports/url-index.md`
- `reports/github-agent-index.md`

Refresh generated indexes with:

```powershell
python scripts/build_agent_index.py
```

See `docs/machine-readable-repository.md`.

## Novel Pipeline

The canonical story source is space-tokenized Chinese:

```text
我 看到 你 在 这里 。
```

The validator checks core known words, approved stretch packs, book-specific words, proper nouns, and a small per-chapter unknown-token budget. See:

- `docs/novel-generation.md`
- `docs/stretch-vocabulary.md`
- `docs/quality-review.md`
- `AGENTS.md`

## Anki Pipeline

The live Anki collection is not mutated by ordinary exports. Scripts that update Anki through AnkiConnect are documented in `AGENTS.md`.

Generated import files, live-collection backups, local downloads, and old trial manuscripts are intentionally ignored by Git.

## Validation

Run the test suite:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests
```
