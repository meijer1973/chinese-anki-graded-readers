# Chinese Anki And Graded Reader Tools

This repository maintains a Chinese vocabulary Anki deck and a controlled-vocabulary fiction pipeline for generating auditable Chinese graded-reader stories.

## Main Workflows

- Build Anki TSV exports from `word list chinese.txt` with `build_anki_chinese.py`.
- Keep Anki new-card order mixed with `scripts/audit_anki_card_distribution.py` and `scripts/schedule_anki_learning_order.py`.
- Keep curated sentence and pinyin fixes in `sentence_example_overrides.py`.
- Maintain the active known-word file in `data/known_words.txt`.
- Maintain learner-profile personal-known vocabulary under `data/learner_profiles/marcel/` for Marcel-personalized readers.
- Generate restricted-vocabulary Chinese manuscripts under `manuscripts/<slug>/`.
- Adapt existing Chinese EPUBs into source-aligned graded readers through `docs/adaptation-workflow.md`, `scripts/import_epub_for_adaptation.py`, and `scripts/profile_adaptation_vocabulary.py`.
- Use `creative_preflight.md` and the controlled Chinese style bank before token-level chapter planning.
- Plan 林安 journalist/crime sequels from `series/an-lin/` and `data/stretch_packs/journalism_crime_50.txt`.
- Update and verify 林安 series memory with `docs/series-memory.md` and `scripts/check_series_memory_update.py` after each accepted series story.
- Validate tokenized chapters with `scripts/validate_chapter.py` and `scripts/validate_book.py`.
- Run quality review with `scripts/run_quality_gate.py`.
- Build EPUB files with `scripts/build_epub.py` after validation and lead approval.

The 林安 series currently includes `manuscripts/shanghai-rain-gate-crime/` (`上海雨票案`), `manuscripts/shanghai-spirit-lamp-case/` (`上海灵灯案`), `manuscripts/shanghai-shadow-bridge-case/` (`上海影子桥案`), `manuscripts/shanghai-midnight-ringtone-case/` (`上海零点铃声案`), `manuscripts/shanghai-still-water-list-case-revised/` (`上海静水名单案`), `manuscripts/shanghai-lost-property-locker-case/` (`上海失物柜案`), `manuscripts/shanghai-silent-archive-case/` (`上海无声档案案`), and `manuscripts/shanghai-old-city-gate-case/` (`上海旧城门案`). Series continuity for its journalist protagonist lives in `series/an-lin/`.

Standalone nonfiction includes `manuscripts/small-shop-survival-economics/` (`小店怎么活下来`), a public-mode business/economics graded reader about how a small Shanghai shop survives.

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
- `docs/personal-known-vocabulary.md`
- `docs/adaptation-workflow.md`
- `docs/creative-preflight.md`
- `docs/style-bank-controlled-chinese.md`
- `docs/stretch-vocabulary.md`
- `docs/quality-review.md`
- `docs/series-memory.md`
- `AGENTS.md`

## Anki Pipeline

The live Anki collection is not mutated by ordinary exports. Scripts that update Anki through AnkiConnect are documented in `AGENTS.md`.

Generated import files, live-collection backups, local downloads, and old trial manuscripts are intentionally ignored by Git.

Local intake folders prefixed with `0.` are user-managed input areas. Agents should read them only when requested and should not reorganize or bulk-edit them.

## Validation

Run the test suite:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests
```
