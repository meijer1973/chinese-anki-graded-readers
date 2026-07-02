# Agent Guide

This repository builds and maintains a Chinese vocabulary Anki deck. The main workflow is: keep the ranked word list and curated overrides clean, regenerate TSV exports, then optionally push selected fields into the live Anki collection through AnkiConnect.

It also contains a repo-local workflow for Chinese restricted-vocabulary graded-reader fiction. All Chinese creative output intended for graded readers must use the active vocabulary policy and remain mechanically auditable.

It also supports source-aligned EPUB-to-graded-reader adaptation. Adaptation is diagnostic first, minimally invasive second, and rewriting last. Do not treat 98% readable coverage as automatic repo validity: forbidden unknowns must remain visible and within the configured per-chapter budget, and proper nouns count only when explicitly listed.

## Restricted-Vocabulary Fiction Rules

1. Vocabulary validity is necessary but not sufficient.
2. Canonical manuscript text is space-tokenized Chinese, for example `我 看到 你 在 这里 。`
3. Extensive-reading validity requires at least 98% known-token coverage and at most 2% approved non-core tokens by default. Approved non-core tokens include stretch layers, book-specific words, and listed proper nouns.
4. Prefer the approved vocabulary layers; allow at most 5 reported forbidden unknown tokens per chapter for natural prose and necessary ideas, but unknowns still reduce known-token coverage.
5. Future novels must aim for narrative interest within the allowed vocabulary, not bland minimal correctness.
6. Check vocabulary after every chapter and save JSON validation reports.
7. Check continuity after every chapter and update `continuity_log.md`.
8. Keep `creative_preflight.md`, a novel bible, and an outline before drafting, unless using documented `discovery-with-control` mode.
9. Do not overwrite previous manuscripts unless explicitly instructed.
10. Every real manuscript must pass vocabulary validation, continuity review, literary critic review, normal reader review, and lead reviewer decision.
11. EPUB export must be generated only after the whole-book validator passes and `quality/lead_quality_decision.md` explicitly contains `Final decision: PASS`.

### Vocabulary Layers

The validator distinguishes these layers:

- core known words from `data/known_words.txt`
- learner-profile personal-known words, such as `data/learner_profiles/marcel/personal_known_words.txt`
- learner-profile high-frequency character compounds, such as Marcel's top 600 ranked characters in `data/learner_profiles/marcel/high_frequency_characters.txt`
- general fiction stretch words
- genre stretch words
- setting stretch words
- profession/social-role stretch words
- journalism/crime stretch words
- business/economics stretch words
- book-specific stretch words
- proper nouns
- forbidden unknown tokens

Do not move from controlled vocabulary to random leakage. The policy is `0 invisible unknown words`: every unknown is counted, reported, and reviewed, but each chapter may keep up to 5 forbidden unknown tokens when that preserves better prose or a necessary idea. Extensive reading is the default: validation fails when known-token coverage is below 98% or approved non-core token share is above 2%. Approved personal-known words are allowed only when the manuscript is explicitly built in a learner-profile mode such as Marcel personalized mode. Marcel personalized mode may also enable the auditable high-frequency character-compound layer with `--known-character-compounds --known-character-compound-limit 600`; this counts tokens made only from the first 600 ranked characters as `high_frequency_character_compound`, not as core, stretch, or invisible unknowns. Approved stretch words are allowed when they are listed in the configured pack, manuscript `book_specific_words.txt`, or manuscript `proper_nouns.txt`, but they must stay within the 2% approved non-core ceiling unless the user explicitly chooses a non-extensive-reading diagnostic mode. Proper nouns do not spend the five-token unknown budget when listed in `proper_nouns.txt`, but they count as approved non-core tokens for the 2% ceiling. If a token appears in both core and another layer, count it as core. If a token appears in personal-known and stretch, count it as personal-known.

### Personal-Known Learner Profiles

Keep personal-known vocabulary separate from the ranked frequency list. `data/known_words.txt` remains frequency-core; `data/learner_profiles/marcel/personal_known_words.txt` is a generated validator allowlist for words Marcel already recognizes. `data/learner_profiles/marcel/high_frequency_characters.txt` is a ranked character source for the derived high-frequency character-compound layer; current default limit is 600 characters and later increases should be small reviewed steps. Hand-edit `data/learner_profiles/marcel/personal_known_words.tsv`, then regenerate the `.txt`, metadata, and audit files with `scripts/sync_personal_known_words.py`.

Use public mode for general graded readers: core known words plus approved stretch packs under the 98% known / 2% approved non-core default. Use Marcel personalized mode only when requested or when the project config says so: core known words plus `--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 600` plus approved stretch packs. Reports must keep `personal_known_tokens` and `high_frequency_character_compound_tokens` separate from core and stretch tokens; these personalized layers count toward known-token coverage for Marcel, not toward stretch load.

### External Agent Vocabulary Bundle

Remote writer agents drafting for Marcel personalized mode should start with `docs/external-agent-vocabulary.md` and the compact three-file bundle under `data/external_agent_vocab/`:

1. `high_frequency_characters_600.txt`
2. `known_words_minus_character_compounds.txt`
3. `master_stretch_words_non_core.txt`

For lightweight preflight, check tokens in that order: first high-frequency character compounds, then the compact known-word list, then the compact master non-core stretch list, then project-local `book_specific_words.txt` and `proper_nouns.txt`. This avoids making external agents download every individual stretch pack or re-check words already covered by the character-compound layer. Regenerate the bundle with `python scripts/build_external_agent_vocab_bundle.py` whenever `data/known_words.txt`, the character-compound limit, or reusable stretch packs change, then verify it with `python scripts/build_external_agent_vocab_bundle.py --check`. The compact bundle is for drafting and external screening; final repository validation still uses `scripts/validate_chapter.py`, `scripts/validate_book.py`, `scripts/run_quality_gate.py`, and `scripts/build_epub.py` with the configured full arguments.

Stretch packs should normally avoid duplicating core known words or Marcel's high-frequency character-compound layer. If a reusable public-mode genre term is essential despite that overlap, list it in `data/stretch_packs/known_character_compound_overlap_allowlist.json` with a rationale so future audits keep the exception visible.

### Creative Quality

Future novels should be ambitious inside the controlled vocabulary. Prefer scenes with a concrete situation, a character want, pressure or conflict, a change by the end of the scene, and a reason for the reader to continue. Avoid conservative, flat, repetitive fiction and repeated dialogue loops such as `我 不 知道`, `你 怎么 了`, or `我们 要 走` unless repetition serves the story.

Track vocabulary breadth, but treat breadth counts as diagnostics, not acceptance gates. The 98% known-token floor and 2% approved non-core ceiling are acceptance gates. Reports should include total tokens, unique used words, percentage of the known list used, top frequent words, repeated phrase warnings, chapter-level unique-token counts, and unused known words. There is no default chapter count and no chapter word-count requirement. Do not add text solely to satisfy length, vocabulary coverage, or stretch-word metrics.

Before vocabulary planning, create `manuscripts/<project-slug>/creative_preflight.md` with 3-5 premise or scene alternatives, rejected ideas, chosen story shape, reader question, main pressure, planned reversals, and variation budget. Future manuscripts should run `scripts/prose_variety_report.py` and use `docs/style-bank-controlled-chinese.md` plus the prose-variety polish skill when repeated visible frames remain.

### Fantasy / Shanghai Mode

Fantasy stories may choose their own scale and structure. Do not force a narrow fantasy subtype, fixed cast size, fixed location pattern, minimal magic system, or ban on epic scope. Large-scale worldbuilding, complex magic, political pressure, battles, monsters, and invented institutions are allowed when the story has enough approved vocabulary to make them readable and mechanically auditable.

Fantasy planning should still name the core story pressure, relevant setting logic, recurring roles or factions, important locations, and any fantasy mechanisms the reader must understand. Vocabulary limits are enforced by validation, not by a mandatory fantasy subtype.

### 林安 Series Continuity

For 林安 series work, read `series/an-lin/series_bible.md`, `series/an-lin/character_registry.md`, `series/an-lin/chronology.md`, `series/an-lin/mechanism_registry.md`, `series/an-lin/open_threads.md`, `series/an-lin/recurring_locations.md`, `series/an-lin/recurring_objects.md`, `series/an-lin/sequel_constraints.md`, and `series/an-lin/series_update_log.md` before planning. 林安 is the journalist/crime-reporter protagonist for this continuity, and 陈雨 is the recurring police contact. Do not reset 林安 into another profession or ignore the first series manuscript at `manuscripts/shanghai-rain-gate-crime/`.

Use `data/stretch_packs/journalism_crime_50.txt` for journalist/crime affordances such as interviews, sources, files, publication pressure, witnesses, suspects, motives, and source protection. Chapter vocabulary plans for this series must include case function, journalist function, fantasy function, and learning function.

After an accepted 林安 story reaches vocabulary validation PASS, lead quality decision PASS, and EPUB build success if applicable, update the living series memory package before planning the next story: `chronology.md`, `character_registry.md`, `mechanism_registry.md`, `open_threads.md`, `series_update_log.md`, and only update `series_bible.md` or `sequel_constraints.md` when stable arc pressure or hard constraints changed. Verify with `python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin`; add `--require-epub-build` when the EPUB should already exist.

### Stretch Words And Anki

Stretch words are review-first Anki candidates. Do not directly mutate the live Anki collection from the novel workflow. Use `scripts/export_stretch_words_for_anki.py` to create `anki/stretch_word_candidates.tsv`, review it, then follow the existing Anki workflows. Promote learned stretch words into a new known-word file with `scripts/promote_stretch_words.py`; do not rewrite historical manuscript reports.

Every stretch pack should have metadata for every word. Use `scripts/complete_stretch_pack_metadata.py` to fill missing starter metadata, then curate important entries by hand. If Anki notes already exist before stretch import, use `scripts/import_stretch_words_to_anki.py --mark-existing-stretch` after review to add stretch tags without overwriting study fields.

### EPUB-To-Graded-Reader Adaptation

Use `docs/adaptation-workflow.md` and the `chinese-source-aligned-adaptation` skill when converting an existing EPUB into a graded reader.

Rights gate first:

- public domain, licensed, or user-owned text: full adapted manuscript may be tracked and exported.
- copyrighted text for private study: keep raw EPUBs, extracted source, and derivative source units local/private unless the user explicitly confirms rights for publication.
- unclear rights: create only analysis reports, vocabulary profiles, candidate lists, and transformation plans.

Raw EPUBs and extracted source units belong under ignored local paths such as `adaptations/<slug>/source_private/`, `adaptations/<slug>/source_units/`, or `0. epubs for conversion/`. Do not commit them unless rights are explicit and the user asks.

Folders prefixed with `0.` are user-managed local intake folders, not agent-owned repository surfaces. Treat `0. Manuscripts from writer agent/`, `0. epubs for conversion/`, and `0. personal known words/` as places to read user-provided input from when requested, but do not reorganize, delete, rename, or bulk-edit them unless the user explicitly asks.

The adaptation workflow is:

1. import EPUB source units with `scripts/import_epub_for_adaptation.py`;
2. profile vocabulary with `scripts/profile_adaptation_vocabulary.py`;
3. review `proper_noun_candidates.tsv` and `stretch_candidates.tsv`;
4. create the normal `manuscripts/<slug>/` structure only after rights and vocabulary policy are clear;
5. keep `adaptation_log.md` with source-unit IDs, intervention levels, changes, and rationale;
6. add `quality/source_fidelity_report.md` and require `Fidelity decision: PASS` before final adapted EPUB approval.

Use the minimal-intervention cascade: classify proper nouns and personal-known words, approve high-value stretch or book-specific words, replace only genuinely hard words, simplify only when necessary, and rewrite or condense only when lower-impact steps cannot meet the readability target. No reason, no change.

## Repository Map

- `word list chinese.txt` is the ranked Anki deck source list. One Chinese word or phrase per line. The line order is the frequency rank used by Anki deck scripts.
- `High frequency words 0-10000.txt` is the ranked graded-reader source list. One Chinese word or phrase per line. `scripts/sync_known_words.py` uses this file, not the Anki deck source, to generate `data/known_words.txt`.
- `build_anki_chinese.py` enriches the word list with pinyin, meanings, and example sentences, then writes TSV files. It does not edit Anki.
- `sentence_example_overrides.py` contains curated example sentences and pinyin fixes. Prefer editing this file when improving sentence quality.
- `apply_meaning_cleanup_updates.py` contains the current meaning cleanup rules and concise meaning overrides. It can update live Anki meaning fields through AnkiConnect.
- `add_missing_single_character_notes.py` appends proposed missing single-character notes to the source word list, rebuilds TSVs, adds the notes to Anki, and reruns card flag setup.
- `ensure_single_character_notes.py` enforces the standing character-closure policy after word-list edits.
- `scripts/audit_anki_card_distribution.py` audits single-character clumping in the ranked source list.
- `scripts/schedule_anki_learning_order.py` writes `anki/learning_order_plan.tsv` and sets live new-card due order so single-character and multi-character Chinese-to-English cards stay mixed.
- `anki_chinese_review.tsv` is the regenerated TSV with a header for human review.
- `anki_chinese_import.tsv` is the regenerated TSV without a header for Anki import.
- `data/` contains compressed source datasets used by the builder: CC-CEDICT and Tatoeba Mandarin-English exports.
- `downloads/`, `SUBTLEX-CH-CHR/`, and `SUBTLEX-CH-WF/` are source/reference data directories.
- `data/known_words.txt` is the active machine-readable known-word list for restricted-vocabulary fiction. It is generated from `High frequency words 0-10000.txt` by `scripts/sync_known_words.py`.
- `data/learner_profiles/marcel/` contains Marcel's personal-known learner profile. Use `personal_known_words.tsv` as the editable source and `personal_known_words.txt` as the generated validator layer.
- `data/learner_profiles/marcel/high_frequency_characters.txt` contains Marcel's ranked known-character source for the optional `--known-character-compounds` layer; current default limit is 600.
- `data/external_agent_vocab/` contains the generated compact three-file vocabulary bundle for remote Marcel-personalized drafting: top-600 high-frequency characters, known words with character-compound-covered terms removed, and a master non-core stretch list.
- `data/stretch_packs/fantasy_232.txt` contains reviewed reusable fantasy stretch words for urban fantasy, high fantasy, sword-sect/cultivation stories, politics, battles, monsters, magic mechanisms, and invented institutions. Use it with `--genre-pack`.
- `data/stretch_packs/known_character_compound_overlap_allowlist.json` documents rare public-mode stretch-pack terms that intentionally overlap Marcel's optional high-frequency character-compound layer.
- `series/an-lin/` contains the living series memory package for the 林安 journalist urban-fantasy crime series: bible, chronology, character registry, mechanism registry, open threads, recurring objects/locations, sequel constraints, and update log.
- `data/stretch_packs/journalism_crime_50.txt` contains reviewed journalism/crime stretch words for 林安-style crime reporting stories.
- `data/stretch_packs/business_economics_150.txt` contains reviewed business/economics stretch words for concrete shops, money, prices, customers, costs, risk, and simple market-decision stories. Pass it with `--extra-pack`.
- `configs/novel_generation.default.json` is the default configuration template for graded-reader novel projects.
- `AGENT_GITHUB_ENTRY.md`, `RESEARCH_AGENT_MAP.md`, `RESEARCH_AGENT_PROMPT.md`, and `repo_manifest.json` are the GitHub-facing machine-readable/research-agent entry points.
- `reports/github-agent-index.md`, `reports/github-agent-index.json`, and `reports/url-index.md` are generated inventories for remote agents; refresh them with `python scripts/build_agent_index.py`.
- `manuscripts/<project-slug>/` contains novel bibles, outlines, canonical tokenized chapters, validation reports, continuity logs, and EPUB exports.
- `scripts/load_known_words.py`, `scripts/sync_personal_known_words.py`, `scripts/import_personal_known_words.py`, `scripts/build_external_agent_vocab_bundle.py`, `scripts/validate_chapter.py`, `scripts/validate_book.py`, `scripts/generate_reports.py`, `scripts/vocabulary_usage_report.py`, `scripts/repeated_phrase_report.py`, `scripts/run_quality_gate.py`, `scripts/check_series_memory_update.py`, and `scripts/build_epub.py` inspect, validate, review-prep, report, verify series-memory updates, and export restricted-vocabulary manuscripts.
- `scripts/import_epub_for_adaptation.py`, `scripts/profile_adaptation_vocabulary.py`, and `scripts/adaptation_tools.py` support source-aligned EPUB intake and vocabulary-pressure diagnostics before any graded-reader adaptation is drafted.
- `scripts/prose_variety_report.py` reports repeated dialogue tags, repeated sentence frames, and other style-polish risks. `scripts/build_reading_copy.py` creates noncanonical natural-text review copies.
- `.agents/skills/` and `.codex/agents/` contain repo-local Codex workflows and role definitions for novel planning, chapter writing, validation, continuity editing, literary review, reader review, lead quality review, and EPUB export.

## Anki Collection

The live collection scripts assume:

- AnkiConnect URL: `http://127.0.0.1:8765`
- Deck query: `deck:Default`
- Note model: `Chinese Vocabulary`
- Fields: `Word`, `Pinyin`, `Meaning`, `Example`, `Example Pinyin`, `Example Meaning`, `Source`, `Production Card`, `Sentence Card`, `Frequency Rank`

Current card policy from the latest report:

- Standard word-recognition meaning cards are active for every deck note.
- Sentence cards are active for every deck note with `Example` and `Example Meaning` fields.
- Production / meaning-recall cards remain available in the model but are suspended by the setup script.

## Chinese Graded-Reader Novel Generation

All Chinese creative output intended for graded readers must follow these rules:

1. Generate story text from the active known-word list in `data/known_words.txt`.
2. The canonical draft format is space-tokenized Chinese, for example `我 看到 你 在 这里 。`.
3. Prefer exact known tokens. Stretch, book-specific, and proper-noun tokens are allowed only inside the default 2% approved non-core ceiling. A chapter may retain up to 5 forbidden unknown tokens when they are useful and auditable, but unknowns still reduce the 98% known-token coverage; do not use the budget as a target.
4. Check vocabulary after every chapter with `scripts/validate_chapter.py`.
5. Check continuity after every chapter and update `continuity_log.md`.
6. Keep a `novel_bible.md` before drafting starts.
7. Save validation reports as JSON beside chapters and at whole-book level.
8. Do not overwrite previous manuscripts unless explicitly instructed. Create a new `manuscripts/<project-slug>/` folder or ask before replacing files.
9. EPUB export must be generated only after `scripts/validate_book.py` passes with no chapter above the configured forbidden-unknown budget, known-token coverage at or above 98%, approved non-core token share at or below 2%, and `quality/lead_quality_decision.md` explicitly says `Final decision: PASS`.
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
- Do not rewrite natural sentences mechanically just to force the unknown-token count to zero when the chapter is still above 98% known-token coverage and within the five-token budget.
- Expansion is allowed only when it fixes a named story problem: unclear motivation, missing transition, weak conflict, confusing setting movement, underdeveloped emotional turn, or unresolved continuity.
- Padding for word count, vocabulary breadth, stretch exposure, or chapter count is a quality failure.

The top 20 tokens and repeated phrase warnings trigger review, not automatic failure.

Default workflow:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/sync_known_words.py --limit 3500
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json
```

For accepted 林安 series manuscripts, update `series/an-lin/` after the EPUB step and verify before the next story:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin --require-epub-build
```

For Marcel personalized mode, add `--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 600` to validation, quality-gate, report-generation, and EPUB commands.

For future known-word expansion, regenerate `data/known_words.txt` from `High frequency words 0-10000.txt` with a larger `--limit` such as `4000` or `5000`; the validators and manuscript layout do not change.

When completing a novel-generation task, the final response must report:

- output file path
- chapter count
- total word-token count
- unique used words
- vocabulary profile, personal-known token count, and high-frequency character-compound token count when used
- known-token percentage
- approved non-core/stretch-token percentage
- unknown-token count
- forbidden unknown tokens over the configured per-chapter limit
- validation command run
- quality review decision
- whether EPUB build succeeded

Use `docs/completion-response-template.md` for the final response format when delivering a completed book, EPUB, source package, or validation-ready manuscript. Put output links or paths first, then a compact validation metrics table, then content summary, source/factual notes when relevant, package contents, and limitations.

A completed book delivery must be final-quality prose, not a rough or intermediate draft. It must include proper chapterized source under `manuscripts/<project-slug>/chapters/chapter_XX.zh-tok.txt`; when EPUB output is requested or appropriate, build it with `scripts/build_epub.py`, pass the EPUB structural check, and include real chapter structure, table of contents, and validation appendix.

## Generated vs Hand-Edited Files

Hand-edit these:

- `word list chinese.txt`
- `High frequency words 0-10000.txt`
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
- `data/external_agent_vocab/*.txt`
- `data/external_agent_vocab/metadata.json`
- `manuscripts/<project-slug>/**/*.validation.json`
- `manuscripts/<project-slug>/vocabulary_report.json`
- `manuscripts/<project-slug>/quality/vocabulary_usage_report.json`
- `manuscripts/<project-slug>/quality/repeated_phrase_report.json`
- `manuscripts/<project-slug>/quality/prose_variety_report.json`
- `manuscripts/<project-slug>/quality/quality_gate_summary.json`
- `manuscripts/<project-slug>/reading_copy.md`

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

Single-character closure does not define study order. Keep `word list chinese.txt` as the frequency-ranked source list, then use the generated learning-order scheduler to prevent a long run of isolated character cards:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/audit_anki_card_distribution.py
python scripts/schedule_anki_learning_order.py
```

The scheduler writes `anki/learning_order_plan.tsv` with separate `Source Rank` and `Learning Order` columns, and writes `single_character_distribution_report.md`. Chinese-to-English cards stay unsuspended; the scheduler changes new-card order rather than using suspension to solve clumping.

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

## Remote Agent Publishing Policy

Remote writer and research agents often work from GitHub, not this local checkout. After completing any accepted work that changes tracked repository files, commit the reviewable change set and push the active branch to `origin` before reporting the task as done.

Use this as the default finish step:

```powershell
git status --short
git add -A
git commit -m "<concise change summary>"
git push origin <current-branch>
```

Exceptions:

- The user explicitly asks not to commit or push.
- The work is exploratory, rejected, or intentionally left uncommitted.
- Validation has failed and the change should not be published yet.
- The remote has diverged, credentials fail, or pushing would require resolving an external Git state; in that case, report the blocker and exact local commit status.

For GitHub-facing workflow, map, script, skill, manuscript convention, or agent-prompt changes, unpushed changes are not done because remote agents will keep reading stale instructions.
