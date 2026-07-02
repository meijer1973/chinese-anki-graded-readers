# Stretch Vocabulary

The old workflow allowed only core known words. That remains available, but some genres need a small controlled expansion. The new rule is:

```text
0 invisible unknown words, at least 98% known tokens, at most 2% approved non-core tokens, at most 95% first-500 character-compound tokens, up to 5 reported forbidden unknown tokens per chapter.
```

Do not use random unknown words. Prefer exact known tokens. Stretch, book-specific, and proper-noun tokens are allowed only as a small controlled load. A chapter may keep a few unknown tokens as learning friction when they are useful, but they are always counted, reviewed, and included in the known-token percentage.

## Layers

- Core known words: `data/known_words.txt`
- Personal known words: `data/learner_profiles/marcel/personal_known_words.txt`, enabled only with `--personal-known`
- High-frequency character compounds: `data/learner_profiles/marcel/high_frequency_characters.txt`, enabled only for Marcel personalized readers with `--known-character-compounds --known-character-compound-limit 1000`
- General fiction: `data/stretch_packs/general_fiction_150.txt`
- Fantasy: `data/stretch_packs/fantasy_232.txt`
- Shanghai setting: `data/stretch_packs/shanghai_setting_150.txt`
- Professions/social roles: `data/stretch_packs/professions_social_roles_100.txt`
- Urban objects: `data/stretch_packs/urban_objects_100.txt`
- Journalism/crime: `data/stretch_packs/journalism_crime_50.txt`
- Business/economics: `data/stretch_packs/business_economics_150.txt`
- Book-specific: `manuscripts/<slug>/book_specific_words.txt`
- Proper nouns: `manuscripts/<slug>/proper_nouns.txt`

Pack names are maintained target sizes for reusable public-mode story affordances. With larger Marcel personalized layers, individual pack files may contain words that are now core known words or high-frequency character compounds for Marcel; the validator counts those earlier layers first. The strict non-core/non-compound surface for remote Marcel-personalized drafting is `data/external_agent_vocab/master_stretch_words_non_core.txt`, generated from all packs after removing words already covered by core known words or the character-compound layer.

Proper nouns are the right place for character, place, and organization names. Listed proper nouns are counted as the proper-noun layer, not as forbidden unknowns. They still count as approved non-core tokens for the 2% extensive-reading ceiling.

Personal-known words and high-frequency character compounds are not stretch words. They are vocabulary a named learner already recognizes and should be tracked under `personal_known_tokens` or `high_frequency_character_compound_tokens`, not as new learning targets. See `docs/personal-known-vocabulary.md`.

## External Agent Master List

Remote Marcel-personalized writer agents do not need to download every individual stretch pack just to do a first-pass token screen. Use `docs/external-agent-vocabulary.md` and `data/external_agent_vocab/master_stretch_words_non_core.txt`, which is generated from all reusable stretch packs after removing words already covered by the active known-word list or the top-1000 high-frequency character-compound layer.

The compact master list is for drafting and lightweight screening. Official validation still passes the relevant individual stretch packs, `book_specific_words.txt`, and `proper_nouns.txt` to the repo validators so layer counts and final reports remain auditable. After any known-word or character-compound limit increase, regenerate the bundle and run `python scripts/build_external_agent_vocab_bundle.py --check`.

## General Fiction Pack

Use `general_fiction_150.txt` for reusable fiction craft vocabulary: memory, hesitation, emotional pressure, dialogue movement, small actions, body-language cues, and ordinary scene texture.

This pack is intentionally genre-neutral. It should help a writer vary scenes without reaching immediately for a specialized topic pack. Good uses include showing a character hesitate, look away, speak quietly, remember something, misread another person, or notice a room/window/sound detail. Do not use these words as random decoration; each word should make a sentence more natural or a scene easier to follow.

## Journalism / Crime Pack

Use `journalism_crime_50.txt` for 林安-style stories where the protagonist is a journalist or crime reporter. It adds durable terms such as `采访`, `逮`, `针对`, `幸存者`, `编辑`, `来源`, `查出`, `法院`, `直播`, `调查局`, `当事人`, `救护车`, `参议员`, and `局长`.

This pack should make scenes possible, not merely decorate them. A chapter using it should show at least one real journalism or crime function: interviewing, confirming a source, protecting a witness, deciding whether to publish, following a suspect, comparing testimony, or checking files.

For the 林安 series, read the full `series/an-lin/` memory package and `docs/series-memory.md` before planning. 林安 is the journalist protagonist in that continuity.

## Function-Pack Priority

Future stretch packs should not only add nouns. Prioritize story-affordance words that change how scenes move:

- dialogue actions: answer, refuse, admit, interrupt, explain, hide, reveal
- scene motion: turn, step back, follow, avoid, reach, open, close
- emotion gradients: uneasy, relieved, ashamed, stubborn, doubtful, tired
- sensory setting: wet, cold, bright, dark, noisy, quiet, narrow, empty, heavy
- social pressure: promise, duty, blame, expectation, debt, trust
- causality and contrast: although, therefore, instead, almost, unless, otherwise, however

Do not add a function pack until entries are reviewed for usefulness, metadata, and Anki flow. The goal is prose movement and scene pressure, not random difficulty.

## Business / Economics Pack

Use `business_economics_150.txt` for nonfiction or case-based stories about shops, companies, money, customers, prices, costs, wages, banks, risk, and simple market decisions.

This pack is for concrete business/economic situations, not dense textbook exposition. Prefer scenes where a character must choose, pay, sell, hire, borrow, compare, lose money, gain trust, or understand why a business problem happened.

Pass this reusable pack with `--extra-pack`:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --extra-pack data/stretch_packs/business_economics_150.txt
```

## Fantasy / Shanghai Use

The `fantasy_232.txt` pack is a reusable fantasy vocabulary layer; it does not force a specific story shape.

Fantasy stories may use low, high, urban, epic, mystery, political, battle, creature-focused, or hybrid structures. Cast size, setting pattern, magic-system complexity, and scope are planning choices, not repo-wide rules.

The control point is vocabulary, not fantasy scale. Magic systems, invented places, factions, monsters, politics, and battles are allowed when the needed words are in core, personal-known, stretch, book-specific, or proper-noun layers and are introduced clearly enough for the reader.

## Chapter Planning

Before each chapter, create `manuscripts/<slug>/planning/chapter_XX_vocab_plan.md` with:

- chapter purpose
- scene goal
- conflict
- emotional turn
- main locations
- characters and roles
- core known words to reuse
- stretch words to introduce
- stretch words to repeat
- risky unavailable concepts to avoid
- chapter hook
- end-of-chapter change
- case function
- journalist function
- fantasy function
- learning function

Stretch words should be repeated enough to become learnable, but the whole manuscript must remain extensive-reading friendly. Track them in `stretch_word_exposure.md` with target repetitions, actual repetitions, chapters used, exposure status, and Anki status, while keeping total approved non-core token share at or below 2%.

## Validation

Use layered validation:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_150.txt --genre-pack data/stretch_packs/fantasy_232.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

Add `--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 1000` for Marcel personalized readers. Omit those flags for public graded-reader mode.

The report counts tokens by layer, forbidden unknowns, forbidden unknowns over the per-chapter limit, known-token coverage, personal-known token use, high-frequency character-compound token use, first-500 character-compound token share, approved non-core/stretch-token share, stretch words used once, stretch words by chapter, and new stretch words by chapter. Default validation fails below 98% known tokens, above 2% approved non-core tokens, or above 95% first-500 character-compound tokens.

Use `scripts/plot_affordance_report.py` before planning a case-heavy premise:

```powershell
python scripts/plot_affordance_report.py --known data/known_words.txt --packs data/stretch_packs/general_fiction_150.txt data/stretch_packs/fantasy_232.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/journalism_crime_50.txt --required 采访 编辑 来源 查出 法院 当事人 局长 --out manuscripts/<slug>/quality/plot_affordance_report.json
```

This report classifies the available vocabulary into story affordance categories such as action verbs, crime nouns, evidence nouns, journalism nouns, movement/location words, conflict verbs, fantasy mechanism words, and dialogue alternatives. It is planning evidence, not an acceptance gate.

Use `--max-forbidden-unknown-tokens-per-chapter 0` only for a strict audit. The default is `5`, which is intended to prevent awkward forced rewrites while keeping unknown words visible.
