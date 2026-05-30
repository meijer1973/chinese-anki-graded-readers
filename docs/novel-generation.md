# Chinese Graded-Reader Novel Generation

This repo can support repeatable long-form Chinese fiction written with the active vocabulary policy: core known words plus optional learner-profile personal-known words, optional learner-profile high-frequency character compounds, and approved stretch layers.

Vocabulary validation is necessary, but it is not enough. A book that passes vocabulary validation but fails reader interest is a failed book.

For existing-source EPUB adaptation, use `docs/adaptation-workflow.md` before creating `manuscripts/<slug>/`. Adaptation is diagnostic first and source-aligned: profile the source, classify proper nouns and reusable vocabulary, then change only what is necessary.

## Vocabulary Source

The active machine-readable vocabulary file is:

```powershell
data/known_words.txt
```

It is generated from `word list chinese.txt`, which is one Chinese word or phrase per line in ranked order. The current graded-reader default is the first 1700 entries. This is separate from live Anki card scheduling policy.

Regenerate the active known list after the ranked list or known-word threshold changes:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/sync_known_words.py --limit 1700
```

For future expansion, change only the limit:

```powershell
python scripts/sync_known_words.py --limit 2000
python scripts/sync_known_words.py --limit 3000
python scripts/sync_known_words.py --limit 5000
```

Use `--limit 0` only when the whole ranked list should be considered known.

Inspect the active list:

```powershell
python scripts/load_known_words.py --known data/known_words.txt
```

## Reader Profiles

Use public mode when a book should represent only the frequency-core level plus approved stretch words.

Use Marcel personalized mode when the book is for Marcel and may use words he already recognizes outside the top 1700. The personal-known layer is generated from:

```text
data/learner_profiles/marcel/personal_known_words.tsv
```

into:

```text
data/learner_profiles/marcel/personal_known_words.txt
```

Regenerate the profile allowlist after editing the TSV:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/sync_personal_known_words.py --profile data/learner_profiles/marcel --core data/known_words.txt
```

Marcel personalized mode may also use a derived high-frequency character-compound layer from:

```text
data/learner_profiles/marcel/high_frequency_characters.txt
```

Enable it with `--known-character-compounds --known-character-compound-limit 300`. This starts conservatively with the first 300 ranked characters. Later increases should be small and reviewed.

Do not merge personal-known words or high-frequency character compounds into `data/known_words.txt`. Validation reports count `personal_known_tokens` and `high_frequency_character_compound_tokens` separately from `core_known_tokens` and stretch tokens.

## Manuscript Layout

Create each new project under:

```text
manuscripts/<project-slug>/
  creative_preflight.md
  novel_bible.md
  outline.md
  characters.md
  continuity_log.md
  vocabulary_report.json
  quality/
    vocabulary_usage_report.json
    repeated_phrase_report.json
    prose_variety_report.json
    literary_critic_report.md
    normal_reader_report.md
    lead_quality_decision.md
  chapters/
    chapter_01.zh-tok.txt
    chapter_01.validation.json
  epub/
    <project-slug>.epub
  reading_copy.md
```

The canonical chapter format is space-tokenized Chinese:

```text
我 看到 你 在 这里 。
```

The validator ignores punctuation and whitespace, then checks every remaining story token against the active vocabulary policy. Core words, approved learner-profile layers, approved stretch words, book-specific words, and listed proper nouns are allowed. A chapter may also keep up to 5 forbidden unknown tokens when they improve natural prose or carry a necessary idea; those tokens remain counted, line-reported, and reviewable. Do not rely on Chinese segmentation after the fact.

## Vocabulary Layers

The default strict mode uses only `data/known_words.txt`. The richer controlled mode allows:

- core known words: `data/known_words.txt`
- learner-profile personal-known words: `data/learner_profiles/marcel/personal_known_words.txt`, enabled with `--personal-known` only for personalized readers
- learner-profile high-frequency character compounds: `data/learner_profiles/marcel/high_frequency_characters.txt`, enabled with `--known-character-compounds --known-character-compound-limit 300` only for personalized readers
- general fiction stretch words: `data/stretch_packs/general_fiction_100.txt`
- genre stretch words: `data/stretch_packs/low_fantasy_150.txt`
- setting stretch words: `data/stretch_packs/shanghai_setting_150.txt`
- profession/social-role stretch words: `data/stretch_packs/professions_social_roles_100.txt`
- urban object stretch words: `data/stretch_packs/urban_objects_100.txt`
- journalism/crime stretch words: `data/stretch_packs/journalism_crime_50.txt`
- business/economics stretch words: `data/stretch_packs/business_economics_60.txt`, passed as `--extra-pack` when a story needs concrete shops, money, prices, costs, customers, wages, risk, or simple market decisions
- manuscript `book_specific_words.txt`
- manuscript `proper_nouns.txt`

The rule is not random leakage. Personal-known words and high-frequency character compounds are recognized vocabulary for a named learner profile, not public core and not new stretch learning targets. Stretch words are approved learning targets. Proper nouns belong in `proper_nouns.txt` and do not count against the unknown-token budget. Each chapter may keep up to 5 forbidden unknown tokens, but the budget is breathing room, not a target. If a word appears in both core and another layer, the validator counts it as core. If a word appears in both personal-known and stretch, it counts as personal-known.

For the 林安 series, read `series/an-lin/series_bible.md`, `series/an-lin/character_registry.md`, `series/an-lin/chronology.md`, `series/an-lin/mechanism_registry.md`, `series/an-lin/open_threads.md`, `series/an-lin/recurring_locations.md`, `series/an-lin/recurring_objects.md`, `series/an-lin/sequel_constraints.md`, and `series/an-lin/series_update_log.md` before planning. 林安 is the journalist/crime-reporter protagonist in that continuity; do not reset her profession or ignore `manuscripts/shanghai-rain-gate-crime/`.

## Creative Preflight

Before token-level chapter planning, create `manuscripts/<slug>/creative_preflight.md`. Use `docs/creative-preflight.md` as the template.

The preflight compares 3-5 possible premises or scene strategies, rejects weak ideas, chooses the strongest story shape, names the reader question, and states the variation budget. This keeps the first vocabulary-feasible idea from becoming the final book by accident.

## Start a New Manuscript

1. Pick a slug, title, mode, premise, and intended reading experience.
2. Copy or adapt `configs/novel_generation.default.json`.
3. Ask Codex to create `creative_preflight.md`.
4. Ask Codex to use the planning skill:

```text
Use the chinese-graded-novel-planning skill to create a novel bible and outline for manuscripts/<slug>.
Use data/known_words.txt. Let chapter count and chapter length follow the story.
```

The planner should create:

- premise
- target reader level
- point of view
- main characters
- setting
- central conflict
- emotional arc
- chapter-by-chapter outline
- recurring phrases inside the known vocabulary
- risky concepts likely to cause vocabulary violations

For `low_fantasy_urban_shanghai`, the planner must also create selected vocabulary packs, book-specific stretch words, proper nouns, a setting map, recurring locations, character professions/social roles, fantasy rule, strange object or place, central mystery, stretch-word introduction schedule, and quality risks.

For 林安 journalist/crime stories, include the journalism/crime pack and make sure the outline has real story functions: interview, source verification, publication pressure, witness protection, suspect pressure, and a simple fantasy mechanism that changes the case.

For business/economics readers, pass `data/stretch_packs/business_economics_60.txt` with `--extra-pack`. Use it for concrete cases such as a shop under rent pressure, a customer choosing between products, a company deciding whether to hire, or a journalist explaining why a local business failed.

## Adapt An Existing EPUB

Do not start by rewriting. First import and profile the EPUB:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/import_epub_for_adaptation.py --epub "0. epubs for conversion/<file>.epub" --slug <slug> --rights-status private_study --copy-source-private
python scripts/profile_adaptation_vocabulary.py --adaptation adaptations/<slug> --known data/known_words.txt --personal-known data/learner_profiles/marcel/personal_known_words.txt
```

Then review:

- `adaptations/<slug>/proper_noun_candidates.tsv`
- `adaptations/<slug>/stretch_candidates.tsv`
- `adaptations/<slug>/vocabulary_profile_baseline.json`

Only after rights and vocabulary policy are clear, create the normal manuscript folder. Add `adaptation_log.md` and `quality/source_fidelity_report.md`. For adapted manuscripts, run the quality gate with:

```powershell
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt --personal-known data/learner_profiles/marcel/personal_known_words.txt --require-source-fidelity
```

The fidelity report must contain `Fidelity decision: PASS` before the adaptation is ready for EPUB.

## Skills and Agent Roles

Repo-local skills live under `.agents/skills/`:

- `chinese-graded-novel-planning`
- `chinese-restricted-vocabulary-writing`
- `chinese-vocabulary-validation`
- `chinese-continuity-editing`
- `chinese-literary-critic`
- `chinese-normal-reader-review`
- `chinese-lead-quality-review`
- `chinese-prose-variety-polish`
- `chinese-source-aligned-adaptation`
- `epub-export`

Project-scoped role definitions live under `.codex/agents/`:

- `novel-planner`
- `chapter-writer`
- `vocabulary-auditor`
- `continuity-editor`
- `literary-critic`
- `normal-reader`
- `lead-quality-reviewer`
- `prose-variety-polisher`
- `source-adaptation-auditor`
- `epub-builder`

If the current Codex runtime does not auto-load these custom agents, use them as manual role prompts and rely on the skills plus scripts for enforcement.

## Writing Modes

## Story-First Size Policy

There is no default chapter count and no chapter word-count requirement.

- Let chapter breaks follow actual story turns.
- A short complete chapter is better than a padded chapter.
- Token totals and vocabulary coverage are diagnostics only.
- Do not expand a validated chapter just to hit length, coverage, or stretch-word targets.
- Add text only to fix a named story problem: unclear motivation, missing transition, weak conflict, confusing setting movement, underdeveloped emotional turn, or continuity gap.

Mode A: `outline-first`

- Create the full novel bible and chapter outline before drafting.
- Best default when the whole story shape is knowable before drafting.
- Human reviews the outline before chapter 1.

Mode B: `discovery-with-control`

- Start with premise, main characters, and ending direction.
- Plan only the next 1-2 chapters.
- Update the continuity log and validate after every chapter.
- Every 3 chapters, write a revised forward outline.
- Do not allow uncontrolled drift.

## Draft One Chapter

Ask Codex to write one chapter at a time:

```text
Use the chinese-restricted-vocabulary-writing skill to draft chapter 1 for manuscripts/<slug>.
Read novel_bible.md, outline.md, continuity_log.md, and data/known_words.txt first.
Write chapter 1 in canonical space-tokenized form. Stop when the scene is complete and the chapter has a meaningful change.
```

Before drafting each chapter, create:

```text
manuscripts/<slug>/planning/chapter_XX_vocab_plan.md
```

Include chapter purpose, scene goal, conflict, emotional turn, 30-80 known words that could naturally appear, and risky unavailable concepts to avoid.

For layered manuscripts, also include main locations, characters and roles, stretch words to introduce, stretch words to repeat from earlier chapters, expected later repetition, chapter hook, and end-of-chapter change.

For 林安 sequels, also include:

- case function: new clue, false lead, witness pressure, suspect pressure, or public reporting consequence
- journalist function: interview, verify, publish, protect source, or face legal/ethical risk
- fantasy function: impossible clue, altered memory, shadow gate, or supernatural cost
- learning function: 5-10 repeated stretch words from earlier chapters and normally 3-5 new stretch words at most

Save the result as:

```text
manuscripts/<slug>/chapters/chapter_01.zh-tok.txt
```

## Validate One Chapter

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
```

Layered low-fantasy Shanghai validation:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

For Marcel personalized readers, add this option to chapter, book, report, quality-gate, and EPUB commands:

```powershell
--personal-known data/learner_profiles/marcel/personal_known_words.txt
```

The default forbidden-unknown budget is 5 tokens per chapter. Override it when needed:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --max-forbidden-unknown-tokens-per-chapter 5
```

Validation passes when the chapter stays at or below the configured forbidden-unknown budget, currently 5 tokens per chapter. Unknown tokens are still listed by line and frequency. Rewrite only the offending lines when the count is above budget, when the unknown is accidental, or when the sentence is unclear. Near matches do not count as known words.

## Continuity Pass

After each validated chapter, ask Codex:

```text
Use the chinese-continuity-editing skill to review chapter 1 and update manuscripts/<slug>/continuity_log.md.
Track characters, locations, objects, events, unresolved questions, and emotional changes.
```

Before writing the next chapter, Codex must read the continuity log.

Update `manuscripts/<slug>/stretch_word_exposure.md` after each chapter:

```markdown
| Word | Layer | First chapter | Target repetitions | Actual repetitions | Chapters used | Exposure status | Anki status |
|---|---|---:|---:|---:|---|---|---|
```

## Vocabulary Breadth

After each chapter or at least before whole-book review, run:

```powershell
python scripts/vocabulary_usage_report.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/vocabulary_usage_report.json
python scripts/repeated_phrase_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/repeated_phrase_report.json
python scripts/prose_variety_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/prose_variety_report.json
```

These reports provide evidence for reviewers. They do not make literary decisions.

Before planning a case-heavy story, run the plot affordance report to see whether the active vocabulary can support the premise:

```powershell
python scripts/plot_affordance_report.py --known data/known_words.txt --packs data/stretch_packs/general_fiction_100.txt data/stretch_packs/low_fantasy_150.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/professions_social_roles_100.txt data/stretch_packs/journalism_crime_50.txt --required 采访 文章 编辑 来源 嫌犯 证人 动机 --out manuscripts/<slug>/quality/plot_affordance_report.json
```

## Validate the Whole Book

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json
```

Layered manuscripts should pass the same pack arguments used for chapter validation.

The whole-book report aggregates chapter count, total tokens, unique used words, unknown-token frequencies, `core_known_tokens`, `personal_known_tokens`, stretch-layer counts, forbidden unknown tokens over the per-chapter limit, and per-chapter details.

Build a noncanonical reading copy for human rhythm review:

```powershell
python scripts/build_reading_copy.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/reading_copy.md
```

Do not edit the reading copy directly. Edit and validate `chapters/*.zh-tok.txt`.

To regenerate every chapter report plus the whole-book report:

```powershell
python scripts/generate_reports.py --manuscript manuscripts/<slug> --known data/known_words.txt
```

## Complete Marcel-Mode Command Set

Use the same `--personal-known` and known-character-compound options consistently from chapter validation through EPUB export:

```powershell
$personal = "data/learner_profiles/marcel/personal_known_words.txt"

python scripts/validate_chapter.py --known data/known_words.txt --personal-known $personal --known-character-compounds --known-character-compound-limit 300 --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt

python scripts/validate_book.py --known data/known_words.txt --personal-known $personal --known-character-compounds --known-character-compound-limit 300 --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt

python scripts/generate_reports.py --manuscript manuscripts/<slug> --known data/known_words.txt --personal-known $personal --known-character-compounds --known-character-compound-limit 300 --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt

python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt --personal-known $personal --known-character-compounds --known-character-compound-limit 300 --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt

python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json --personal-known $personal --known-character-compounds --known-character-compound-limit 300 --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

## Build EPUB

Do not build the EPUB after validation alone. Run the quality gate first:

```powershell
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt
```

Then run the reviews:

The quality gate also checks that every `chapter_XX.zh-tok.txt` has a matching `planning/chapter_XX_vocab_plan.md`. Missing planning files make `quality_gate_summary.json` report `ready_for_epub: false` until the plans are added.

1. Literary critic review writes `quality/literary_critic_report.md`.
2. Normal reader review writes `quality/normal_reader_report.md`.
3. Prose-variety polish repairs repeated visible frames when `prose_variety_report.json` requires it.
4. Lead reviewer writes `quality/lead_quality_decision.md`.

The lead decision must explicitly say:

```text
Final decision: PASS
```

Build only after whole-book validation passes and the lead reviewer approves:

```powershell
python scripts/build_epub.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/epub/<slug>.epub --report manuscripts/<slug>/epub/build_report.json
```

The EPUB builder runs whole-book validation and checks lead quality approval again before writing. By default it removes token spaces for display readability and includes a validation appendix explaining that the canonical source is the `.zh-tok.txt` files.

## Post-Story Series Memory Update

For series manuscripts, do not rely on memory after a book is accepted. Use `docs/series-memory.md`.

After a 林安 manuscript reaches vocabulary validation PASS, lead quality decision PASS, and EPUB build success if applicable, update the living series memory package before planning the next story:

1. Add a concise accepted-story entry to `series/an-lin/chronology.md`.
2. Add only durable character facts to `series/an-lin/character_registry.md`.
3. Record fantasy mechanism rules, costs, limits, evidence split, and relationship to earlier mechanisms in `series/an-lin/mechanism_registry.md`.
4. Close resolved questions and add useful sequel seeds in `series/an-lin/open_threads.md`.
5. Update `series/an-lin/series_bible.md` only if stable identity or arc pressure changed.
6. Update `series/an-lin/sequel_constraints.md` only if the next writer needs a new hard rule.
7. Append an audit entry to `series/an-lin/series_update_log.md`.

Verify the update:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin
```

Add `--require-epub-build` when the EPUB should already exist. The next 林安 story may not begin planning until the previous accepted story passes this check.

## Improved Workflow

1. Load active known-word list.
2. Choose vocabulary profile: public mode or Marcel personalized mode.
3. Create creative preflight with alternatives and a variation budget.
4. Create novel bible.
5. Create outline.
6. Check that the outline is interesting enough before drafting.
7. Draft one chapter.
8. Validate vocabulary.
9. Repair unknown tokens only when they are accidental, unclear, or above the per-chapter budget.
10. Update continuity.
11. Track vocabulary breadth.
12. Repeat chapter by chapter.
13. Run whole-book validation.
14. Run vocabulary usage, repeated phrase, and prose variety reports.
15. Build a noncanonical reading copy.
16. Run literary critic review.
17. Run normal reader review.
18. Run prose-variety polish when needed.
19. Lead reviewer decides: pass, polish, partial rewrite, or complete rebuild.
20. Build EPUB only after lead reviewer approves.
21. For series manuscripts, update and verify the living series memory package before planning the next book.

For `low_fantasy_urban_shanghai`, the outline and reviews should check that the story feels like a normal person in Shanghai discovering one impossible thing. Avoid epic scale, lore dumps, many monsters, and stretch words used once as decoration.

## Review the Final Report

The final Codex response for a generated book must include:

- output file path
- chapter count
- total word-token count
- unique used words
- vocabulary profile, personal-known token count, and high-frequency character-compound token count when used
- unknown-token count
- forbidden unknown tokens over the configured per-chapter limit
- validation command run
- quality review decision
- whether EPUB build succeeded

## Repair Tips

- If an unknown token appears, first decide whether it is useful. Keep it only when the chapter remains within budget and the word improves the story or learning experience.
- If an unknown token is accidental or above budget, replace the whole token with an exact known, stretch, book-specific, or listed proper-noun token.
- If an accidental unsegmented string appears, add spaces between known words.
- If a plot requires too many missing nouns, simplify the plot in the outline instead of fighting the vocabulary.
- Keep the validated `.zh-tok.txt` files as the source of truth even when EPUB display removes spaces.
