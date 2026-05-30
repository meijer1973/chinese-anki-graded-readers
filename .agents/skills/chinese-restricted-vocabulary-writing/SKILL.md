---
name: chinese-restricted-vocabulary-writing
description: Draft Chinese graded-reader chapters using only the active known-word list. Use when Codex needs to write or revise canonical space-tokenized Chinese chapter files, repair vocabulary violations, or continue a restricted-vocabulary manuscript.
---

# Chinese Restricted Vocabulary Writing

Write one chapter at a time. The canonical format is space-tokenized Chinese:

```text
我 看到 你 在 这里 。
```

## Before Writing

- Choose and state the vocabulary profile before drafting:
  - Public mode = core known words plus approved stretch/book/proper-noun layers only.
  - Marcel personalized mode = core known words plus `data/learner_profiles/marcel/personal_known_words.txt`, optional top-300 high-frequency character compounds, plus approved stretch/book/proper-noun layers.
- Read `data/known_words.txt`.
- If the project uses Marcel personalized mode, read `data/learner_profiles/marcel/personal_known_words.txt` and count those words as the `personal_known` layer, not as stretch.
- If Marcel personalized mode enables known-character compounds, use `data/learner_profiles/marcel/high_frequency_characters.txt` with limit 300 and keep those tokens separate as `high_frequency_character_compound`, not core or stretch.
- Read the configured approved stretch packs, manuscript `book_specific_words.txt`, and `proper_nouns.txt` when present.
- Read the manuscript `novel_bible.md`, `outline.md`, `characters.md`, and `continuity_log.md`.
- Read `creative_preflight.md` when present. Preserve the chosen story shape, reader question, and variation budget.
- Read `docs/style-bank-controlled-chinese.md` before drafting or polishing.
- For 林安 series chapters, also read `series/an-lin/series_bible.md`, `series/an-lin/character_registry.md`, `series/an-lin/chronology.md`, `series/an-lin/mechanism_registry.md`, `series/an-lin/open_threads.md`, `series/an-lin/recurring_locations.md`, `series/an-lin/recurring_objects.md`, `series/an-lin/sequel_constraints.md`, and `series/an-lin/series_update_log.md`.
- Confirm the target chapter file path and chapter outline. Do not use a token target as a quota.
- Create `manuscripts/<slug>/planning/chapter_XX_vocab_plan.md` before drafting.
- Do not begin with vocabulary feasibility alone. Confirm the scene want, pressure, reversal, and end change before choosing the token set.

The vocabulary plan must include chapter purpose, scene goal, conflict, emotional turn, main locations, characters and roles, 30-80 core or personal-known words that could naturally appear, stretch words to introduce, stretch words to repeat, risky unavailable concepts to avoid, chapter hook, and end-of-chapter change.

For 林安 sequels, the vocabulary plan must also include case function, journalist function, fantasy function, and learning function. Use 5-10 repeated stretch words from earlier chapters and normally 3-5 new stretch words at most.

## Drafting Rules

- Use only exact tokens from core known words and approved vocabulary layers. In Marcel personalized mode, personal-known words and enabled high-frequency character compounds are approved known vocabulary for that learner profile.
- Prefer approved vocabulary, but do not mangle natural sentences solely to force zero unknowns. Each chapter may keep up to 5 reported forbidden unknown tokens when they are useful, intentional, and not confusing.
- Use punctuation freely from `data/punctuation_allowlist.txt`.
- Use the known vocabulary actively and naturally.
- Keep sentences clear and useful for reading practice without becoming bland.
- Let the scene decide the chapter length. A shorter complete chapter is better than a padded chapter.
- Prefer concrete scenes over abstract explanation.
- Give each chapter a distinct function.
- Give each chapter at least one change: new information, decision, conflict, danger, relationship movement, misunderstanding, or discovery.
- Include action, emotion, memory, conflict, and scene movement; avoid dialogue-only filler.
- Avoid chapters where characters only talk in circles.
- Avoid repeating the same emotional beat.
- Avoid repeated dialogue loops unless the repetition is narratively justified.
- Avoid repeated `X 说` frames. Use action, silence, object handling, or reaction beats when they are clearer and still valid.
- Vary sentence openings and scene rhythm. A chapter should not sound like the previous chapter with names changed.
- Use available nouns, verbs, and adjectives more widely.
- Use approved stretch vocabulary actively and naturally.
- Use journalism/crime stretch vocabulary for real story actions: interviewing, confirming sources, checking files, protecting witnesses, publishing or withholding articles, following suspects, and comparing testimony.
- Use Shanghai/urban locations to create scene texture when that setting is configured.
- Use varied professions and social roles; avoid every scene depending on teachers, doctors, students, police, school, hospital, or home.
- Use low fantasy sparingly but meaningfully: one strange object, one secret place, one hidden rule, and a small danger are usually enough.
- Do not add paragraphs solely to increase word count, vocabulary breadth, or stretch-word repetition.
- Any expansion pass must name the story problem it fixes.
- Do not use pinyin, English, or near matches unless the exact token is explicitly allowed.
- If a needed concept is unavailable, simplify the sentence or adjust the plot.

## Vocabulary Expansion Pass

After the first draft, revise only for story quality and vocabulary validity:

- Find places where the same word is repeated too often.
- Replace or rewrite with other allowed words where natural.
- Add scene detail using allowed words only when it clarifies setting movement, motivation, conflict, or emotional change.
- Keep every token inside core, personal-known when configured, enabled high-frequency character compounds, or approved stretch layers.
- Run vocabulary validation after the expansion pass.

## After Drafting

Run:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
```

If unknown tokens appear, review them. Keep them only when the chapter remains within the configured budget and the word improves the story or learning experience. Rewrite offending lines when the unknown is accidental, confusing, or above budget. Save the validation JSON with the chapter.

For layered stretch manuscripts, include the configured pack arguments:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

For Marcel personalized mode, also include:

```powershell
--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 300
```

After each chapter, run vocabulary validation, repair forbidden unknowns that exceed the budget or weaken clarity, run vocabulary usage evidence, update `continuity_log.md`, update `stretch_word_exposure.md`, and check whether stretch words are being repeated enough to become learnable rather than decorative.

Before final review, run:

```powershell
python scripts/prose_variety_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/prose_variety_report.json
```

If the report flags repeated dialogue tags or repeated sentence frames, use the `chinese-prose-variety-polish` skill before lead approval.
