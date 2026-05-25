# Agent Guide

This repository builds and maintains a Chinese vocabulary Anki deck. The main workflow is: keep the ranked word list and curated overrides clean, regenerate TSV exports, then optionally push selected fields into the live Anki collection through AnkiConnect.

It also contains a repo-local workflow for Chinese restricted-vocabulary graded-reader fiction. All Chinese creative output intended for graded readers must use the active vocabulary policy and remain mechanically auditable.

## Restricted-Vocabulary Fiction Rules

1. Vocabulary validity is necessary but not sufficient.
2. Canonical manuscript text is space-tokenized Chinese, for example `我 看到 你 在 这里 。`
3. Prefer the approved vocabulary layers; allow at most 5 reported forbidden unknown tokens per chapter for natural prose and necessary ideas.
4. Future novels must aim for narrative interest within the allowed vocabulary, not bland minimal correctness.
5. Check vocabulary after every chapter and save JSON validation reports.
6. Check continuity after every chapter and update `continuity_log.md`.
7. Keep a novel bible and outline before drafting, unless using documented `discovery-with-control` mode.
8. Do not overwrite previous manuscripts unless explicitly instructed.
9. Every real manuscript must pass vocabulary validation, continuity review, literary critic review, normal reader review, and lead reviewer decision.
10. EPUB export must be generated only after the whole-book validator passes and `quality/lead_quality_decision.md` explicitly contains `Final decision: PASS`.

### Vocabulary Layers

The validator distinguishes these layers:

- core known words from `data/known_words.txt`
- general fiction stretch words
- genre stretch words
- setting stretch words
- profession/social-role stretch words
- journalism/crime stretch words
- business/economics stretch words
- book-specific stretch words
- proper nouns
- forbidden unknown tokens

Do not move from controlled vocabulary to random leakage. The policy is `0 invisible unknown words`: every unknown is counted, reported, and reviewed, but each chapter may keep up to 5 forbidden unknown tokens when that preserves better prose or a necessary idea. Approved stretch words are allowed when they are listed in the configured pack, manuscript `book_specific_words.txt`, or manuscript `proper_nouns.txt`. Proper nouns do not spend the five-token unknown budget when listed in `proper_nouns.txt`. If a token appears in both core and stretch, count it as core.

### Creative Quality

Future novels should be ambitious inside the controlled vocabulary. Prefer scenes with a concrete situation, a character want, pressure or conflict, a change by the end of the scene, and a reason for the reader to continue. Avoid conservative, flat, repetitive fiction and repeated dialogue loops such as `我 不 知道`, `你 怎么 了`, or `我们 要 走` unless repetition serves the story.

Track vocabulary breadth, but treat counts as diagnostics, not acceptance gates. Reports should include total tokens, unique used words, percentage of the known list used, top frequent words, repeated phrase warnings, chapter-level unique-token counts, and unused known words. There is no default chapter count and no chapter word-count requirement. Do not add text solely to satisfy length, vocabulary coverage, or stretch-word metrics.

### Low Fantasy / Shanghai Mode

For `low_fantasy_urban_shanghai`, prefer easy low fantasy: normal city life plus one impossible thing. Use one strange object, one secret place, one hidden rule, one small danger, one mystery, a small cast, repeated locations, and clear emotional stakes. Avoid large invented worlds, kingdoms, races, battle-heavy plots, lore dumps, complicated politics, many monsters, and vocabulary that appears once and disappears.

Every real novel in this mode should include at least 3 distinct professions or social roles, at least 4 recurring non-home/non-school/non-hospital locations, at least 2 characters whose role affects the plot, and at least 1 location that changes meaning over the story.

### 林安 Series Continuity

For 林安 series work, read `series/an-lin/series_bible.md`, `series/an-lin/character_registry.md`, `series/an-lin/chronology.md`, and `series/an-lin/sequel_constraints.md` before planning. 林安 is the journalist/crime-reporter protagonist for this continuity, and 陈雨 is the recurring police contact. Do not reset 林安 into another profession or ignore the first series manuscript at `manuscripts/shanghai-rain-gate-crime/`.

Use `data/stretch_packs/journalism_crime_50.txt` for journalist/crime affordances such as interviews, sources, files, publication pressure, witnesses, suspects, motives, and source protection. Chapter vocabulary plans for this series must include case function, journalist function, fantasy function, and learning function.

### Stretch Words And Anki

Stretch words are review-first Anki candidates. Do not directly mutate the live Anki collection from the novel workflow. Use `scripts/export_stretch_words_for_anki.py` to create `anki/stretch_word_candidates.tsv`, review it, then follow the existing Anki workflows. Promote learned stretch words into a new known-word file with `scripts/promote_stretch_words.py`; do not rewrite historical manuscript reports.

Every stretch pack should have metadata for every word. Use `scripts/complete_stretch_pack_metadata.py` to fill missing starter metadata, then curate important entries by hand. If Anki notes already exist before stretch import, use `scripts/import_stretch_words_to_anki.py --mark-existing-stretch` after review to add stretch tags without overwriting study fields.

## Repository Map

- `word list chinese.txt` is the ranked source list. One Chinese word or phrase per line. The line order is the frequency rank used by later scripts.
- `build_anki_chinese.py` enriches the word list with pinyin, meanings, and example sentences, then writes TSV files. It does not edit Anki.
- `sentence_example_overrides.py` contains curated example sentences and pinyin fixes. Prefer editing this file when improving sentence quality.
- `apply_meaning_cleanup_updates.py` contains the current meaning cleanup rules and concise meaning overrides. It can update live Anki meaning fields through AnkiConnect.
- `add_missing_single_character_notes.py` appends proposed missing single-character notes to the source word list, rebuilds TSVs, adds the notes to Anki, and reruns card flag setup.
- `ensure_single_character_notes.py` enforces the standing character-closure policy after word-list edits.
- `anki_chinese_review.tsv` is the regenerated TSV with a header for human review.
- `anki_chinese_import.tsv` is the regenerated TSV without a header for Anki import.
- `data/` contains compressed source datasets used by the builder: CC-CEDICT and Tatoeba Mandarin-English exports.
- `downloads/`, `SUBTLEX-CH-CHR/`, and `SUBTLEX-CH-WF/` are source/reference data directories.
- `data/known_words.txt` is the active machine-readable known-word list for restricted-vocabulary fiction. It is generated from the ranked source list by `scripts/sync_known_words.py`.
- `series/an-lin/` contains the series-level bible and continuity constraints for the 林安 journalist urban-fantasy crime series.
- `data/stretch_packs/journalism_crime_50.txt` contains reviewed journalism/crime stretch words for 林安-style crime reporting stories.
- `data/stretch_packs/business_economics_60.txt` contains reviewed business/economics stretch words for concrete shops, money, prices, customers, costs, risk, and simple market-decision stories. Pass it with `--extra-pack`.
- `configs/novel_generation.default.json` is the default configuration template for graded-reader novel projects.
- `AGENT_GITHUB_ENTRY.md`, `RESEARCH_AGENT_MAP.md`, `RESEARCH_AGENT_PROMPT.md`, and `repo_manifest.json` are the GitHub-facing machine-readable/research-agent entry points.
- `reports/github-agent-index.md`, `reports/github-agent-index.json`, and `reports/url-index.md` are generated inventories for remote agents; refresh them with `python scripts/build_agent_index.py`.
- `manuscripts/<project-slug>/` contains novel bibles, outlines, canonical tokenized chapters, validation reports, continuity logs, and EPUB exports.
- `scripts/load_known_words.py`, `scripts/validate_chapter.py`, `scripts/validate_book.py`, `scripts/generate_reports.py`, `scripts/vocabulary_usage_report.py`, `scripts/repeated_phrase_report.py`, `scripts/run_quality_gate.py`, and `scripts/build_epub.py` inspect, validate, review-prep, report, and export restricted-vocabulary manuscripts.
- `.agents/skills/` and `.codex/agents/` contain repo-local Codex workflows and role definitions for novel planning, chapter writing, validation, continuity editing, literary review, reader review, lead quality review, and EPUB export.

## Anki Collection

The live collection scripts assume:

- AnkiConnect URL: `http://127.0.0.1:8765`
- Deck query: `deck:Default`
- Note model: `Chinese Vocabulary`
- Fields: `Word`, `Pinyin`, `Meaning`, `Example`, `Example Pinyin`, `Example Meaning`, `Source`, `Production Card`, `Sentence Card`, `Frequency Rank`

Current card policy from the latest report:

- Production cards enabled for ranks `1-1000`.
- Sentence cards enabled for ranks `1-1000`.
- Production cards above rank `1000` are suspended.

## Chinese Graded-Reader Novel Generation

All Chinese creative output intended for graded readers must follow these rules:

1. Generate story text from the active known-word list in `data/known_words.txt`.
2. The canonical draft format is space-tokenized Chinese, for example `我 看到 你 在 这里 。`.
3. Prefer exact known, stretch, book-specific, or proper-noun tokens. A chapter may retain up to 5 forbidden unknown tokens when they are useful and auditable; do not use the budget as a target.
4. Check vocabulary after every chapter with `scripts/validate_chapter.py`.
5. Check continuity after every chapter and update `continuity_log.md`.
6. Keep a `novel_bible.md` before drafting starts.
7. Save validation reports as JSON beside chapters and at whole-book level.
8. Do not overwrite previous manuscripts unless explicitly instructed. Create a new `manuscripts/<project-slug>/` folder or ask before replacing files.
9. EPUB export must be generated only after `scripts/validate_book.py` passes with no chapter above the configured forbidden-unknown budget and `quality/lead_quality_decision.md` explicitly says `Final decision: PASS`.
10. Keep tokenized `.zh-tok.txt` source files as the auditable source of truth even if EPUB display text removes spaces.

Creative quality rules:

1. Vocabulary validity is necessary but not sufficient.
2. A chapter with zero unknown tokens can still fail quality review.
3. Do not write overly conservative, flat, or repetitive fiction.
4. Future novels must aim for narrative interest within the allowed vocabulary.
5. Prefer scenes with a concrete situation, a character want, pressure or conflict, a change by the end, and some reason for the reader to continue.
6. Use more of the available known-word list where natural.
7. Track vocabulary breadth.
8. Avoid using the same small group of words for the entire book.
9. Avoid repeated dialogue loops such as `我 不 知道`, `你 怎么 了`, and `我们 要 走` unless the repetition is narratively justified.
10. Do not accept a manuscript only because the validator passes.
11. Every real manuscript must pass vocabulary validation, continuity review, literary critic review, normal reader review, and lead reviewer decision.

Vocabulary-breadth reports are required for real manuscripts. Reports must include total word-token count, unique used words, percentage of known-word list used, top 25 most frequent tokens, repeated phrase warnings, chapter-level unique-token counts, whole-book unique-token count, and unused known words.

Story-shape policy:

- Start with a good story, then let chapter count and chapter length follow the story.
- A short complete chapter is acceptable.
- A book may have as many chapters as the story needs.
- Do not inflate chapters after validation to hit a token count.
- Do not add unused city, role, fantasy, or object words merely to improve metrics.
- Do not rewrite natural sentences mechanically just to force the unknown-token count to zero when the chapter is within the five-token budget.
- Expansion is allowed only when it fixes a named story problem: unclear motivation, missing transition, weak conflict, confusing setting movement, underdeveloped emotional turn, or unresolved continuity.
- Padding for word count, vocabulary breadth, stretch exposure, or chapter count is a quality failure.

The top 20 tokens and repeated phrase warnings trigger review, not automatic failure.

Default workflow:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/sync_known_words.py --limit 1100
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json
```

For future known-word expansion, regenerate `data/known_words.txt` with a larger `--limit` such as `2000`, `3000`, or `5000`; the validators and manuscript layout do not change.

When completing a novel-generation task, the final response must report:

- output file path
- chapter count
- total word-token count
- unique used words
- unknown-token count
- forbidden unknown tokens over the configured per-chapter limit
- validation command run
- quality review decision
- whether EPUB build succeeded

## Generated vs Hand-Edited Files

Hand-edit these:

- `word list chinese.txt`
- `sentence_example_overrides.py`
- Script logic in `*.py`
- novel planning files in `manuscripts/<project-slug>/`

Usually do not hand-edit these, because scripts regenerate them:

- `anki_chinese_review.tsv`
- `anki_chinese_import.tsv`
- `enrichment_report.txt`
- `meaning_field_suggestions.tsv`
- `meaning_field_suggestions_summary.md`
- `data/known_words.txt`
- `data/known_words.metadata.json`
- `manuscripts/<project-slug>/**/*.validation.json`
- `manuscripts/<project-slug>/vocabulary_report.json`
- `manuscripts/<project-slug>/quality/vocabulary_usage_report.json`
- `manuscripts/<project-slug>/quality/repeated_phrase_report.json`
- `manuscripts/<project-slug>/quality/quality_gate_summary.json`

Generated but tracked for accepted manuscripts:

- `manuscripts/<project-slug>/epub/*.epub`
- `manuscripts/<project-slug>/epub/build_report.json`

Backup/report artifacts are useful history and should not be deleted casually:

- `*_backup.tsv`
- `*_report.md`
- `meaning_field_applied_updates.tsv`

## Common Workflows

Rebuild TSV exports after changing the word list or examples:

```powershell
$env:PYTHONIOENCODING='utf-8'
python build_anki_chinese.py
```

After adding or editing words in `word list chinese.txt`, enforce single-character coverage:

```powershell
$env:PYTHONIOENCODING='utf-8'
python ensure_single_character_notes.py
```

Policy: every Hanzi character used in any multi-character deck word must also exist as its own single-character note. This script scans the current word list, appends missing characters to the end of `word list chinese.txt`, rebuilds TSVs, adds the new character notes to Anki, and reruns `setup_production_sentence_cards.py`. If coverage is already complete, it only writes a report and adds nothing.

Apply rebuilt sentence/example fields to the live Anki notes:

```powershell
$env:PYTHONIOENCODING='utf-8'
python apply_sentence_example_updates.py
```

This updates only `Example`, `Example Pinyin`, `Example Meaning`, and `Source`. It writes `sentence_examples_before_update_backup.tsv` first and reports to `sentence_examples_update_report.md`.

Add proposed missing single-character notes:

```powershell
$env:PYTHONIOENCODING='utf-8'
python add_missing_single_character_notes.py
```

This uses `missing_single_character_notes_proposal.tsv`, appends missing characters to `word list chinese.txt`, rebuilds TSVs, adds notes to Anki, and reruns `setup_production_sentence_cards.py`. It writes `word_list_before_single_character_notes_backup.txt`, `single_character_notes_added.tsv`, and `single_character_notes_add_report.md`.

Apply surname/Taiwan-specific/long-meaning cleanup to the live Anki notes:

```powershell
$env:PYTHONIOENCODING='utf-8'
python apply_meaning_cleanup_updates.py
```

This updates only `Meaning`. It writes `meaning_cleanup_before_update_backup.tsv`, `meaning_cleanup_applied_updates.tsv`, and `meaning_cleanup_update_report.md`.

Create or update the Anki note model from TSV data:

```powershell
$env:PYTHONIOENCODING='utf-8'
python migrate_chinese_notes.py
```

This mutates the live Anki collection. Use with care; it can change models, fields, tags, and example fields.

Set production/sentence card flags and card suspension policy:

```powershell
$env:PYTHONIOENCODING='utf-8'
python setup_production_sentence_cards.py
```

This mutates the live Anki collection. It also manages the `Sentence Recognition` template and card suspension state.

Generate meaning-field review suggestions:

```powershell
$env:PYTHONIOENCODING='utf-8'
python suggest_meaning_edits.py
```

This is read-only against Anki and writes review files locally.

## Sentence Quality Notes

For example sentence improvements:

- Prefer short, common, everyday phrases.
- Avoid examples that are just the target word, or the target word with particles/interjections around it.
- Avoid tiny translations such as `Hi.`, `OK?`, `No.`, `Thanks!`, unless the target word specifically needs that.
- Keep English translations literal enough for study, but natural.
- If generated pinyin is wrong for a polyphonic word, add the sentence to `SENTENCE_PINYIN_OVERRIDES`.

The builder already rejects many low-value Tatoeba examples with tiny text or tiny translations, and normalizes basic Chinese punctuation on sourced examples. Curated examples in `sentence_example_overrides.py` take priority over Tatoeba.

For meaning cleanup:

- Surname-only senses are intentionally removed from meanings.
- Taiwan-specific pronunciation notes and regional-only senses are intentionally removed.
- Keep meanings concise enough for review; the current cleanup target is under 130 characters and fewer than six semicolon-separated senses.

For word-list additions:

- Always run `ensure_single_character_notes.py` after adding a multi-character word.
- Missing component characters are added as normal notes, not as a separate model.
- If a new character would receive a generated placeholder sentence, add a curated example in `sentence_example_overrides.py` and rerun.

## Validation

Fast syntax check:

```powershell
python -m py_compile build_anki_chinese.py sentence_example_overrides.py apply_sentence_example_updates.py apply_meaning_cleanup_updates.py add_missing_single_character_notes.py ensure_single_character_notes.py migrate_chinese_notes.py setup_production_sentence_cards.py suggest_meaning_edits.py
```

After rebuilding, inspect the report:

```powershell
Get-Content -LiteralPath 'enrichment_report.txt' -Encoding UTF8
```

After applying Anki updates, inspect:

```powershell
Get-Content -LiteralPath 'sentence_examples_update_report.md' -Encoding UTF8
```

## Encoding Notes

Chinese text is UTF-8. In PowerShell, always use `-Encoding UTF8` when reading files, and set `$env:PYTHONIOENCODING='utf-8'` before Python scripts that print Chinese. Without this, output can look like mojibake even when the files are fine.

## Dependencies

The builder imports:

- `jieba`
- `opencc`
- `pypinyin`

If a script fails on imports, install the missing package in the active Python environment before changing code.

## Local State Notes

This checkout is a Git repository with `main` tracking `origin/main`. Use normal `git status`, `git diff`, and small reviewable commits. Generated/local artifacts are ignored by `.gitignore`.
