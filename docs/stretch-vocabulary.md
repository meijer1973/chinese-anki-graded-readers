# Stretch Vocabulary

The old workflow allowed only core known words. That remains available, but some genres need a small controlled expansion. The new rule is:

```text
0 invisible unknown words, approved stretch words allowed, up to 5 reported forbidden unknown tokens per chapter.
```

Do not use random unknown words. Prefer tokens from approved layers. A chapter may keep a few unknown tokens as learning friction when they are useful, but they are always counted and reviewed.

## Layers

- Core known words: `data/known_words.txt`
- General fiction: `data/stretch_packs/general_fiction_100.txt`
- Low fantasy: `data/stretch_packs/low_fantasy_150.txt`
- Shanghai setting: `data/stretch_packs/shanghai_setting_150.txt`
- Professions/social roles: `data/stretch_packs/professions_social_roles_100.txt`
- Urban objects: `data/stretch_packs/urban_objects_100.txt`
- Journalism/crime: `data/stretch_packs/journalism_crime_50.txt`
- Book-specific: `manuscripts/<slug>/book_specific_words.txt`
- Proper nouns: `manuscripts/<slug>/proper_nouns.txt`

Pack names are aspirational sizes. Starter packs are intentionally smaller than 100 or 150 when good entries are not ready. Add durable, reusable words rather than filler.

Proper nouns are the right place for character, place, and organization names. Listed proper nouns are counted as the proper-noun layer, not as forbidden unknowns.

## Journalism / Crime Pack

Use `journalism_crime_50.txt` for 林安-style stories where the protagonist is a journalist or crime reporter. It adds durable terms such as `采访`, `报道`, `文章`, `编辑`, `来源`, `文件`, `案件`, `嫌犯`, `证人`, `动机`, `警察局`, `跟踪`, `观察`, `确认`, and `保密`.

This pack should make scenes possible, not merely decorate them. A chapter using it should show at least one real journalism or crime function: interviewing, confirming a source, protecting a witness, deciding whether to publish, following a suspect, comparing testimony, or checking files.

For the 林安 series, read `series/an-lin/series_bible.md` before planning. 林安 is the journalist protagonist in that continuity.

## Low Fantasy / Shanghai Use

Use easy low fantasy:

- one strange object
- one secret place
- one hidden rule
- one small danger
- one mystery
- normal Shanghai life plus a small fantasy layer
- small cast and repeated locations

Avoid epic fantasy scale, many invented names, many monsters, complicated politics, and one-off magical terms.

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

Stretch words should be repeated enough to become learnable. Track them in `stretch_word_exposure.md` with target repetitions, actual repetitions, chapters used, exposure status, and Anki status.

## Validation

Use layered validation:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

The report counts tokens by layer, forbidden unknowns, forbidden unknowns over the per-chapter limit, core coverage, stretch-token share, stretch words used once, stretch words by chapter, and new stretch words by chapter.

Use `scripts/plot_affordance_report.py` before planning a case-heavy premise:

```powershell
python scripts/plot_affordance_report.py --known data/known_words.txt --packs data/stretch_packs/general_fiction_100.txt data/stretch_packs/low_fantasy_150.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/journalism_crime_50.txt --required 采访 文章 编辑 来源 嫌犯 证人 动机 --out manuscripts/<slug>/quality/plot_affordance_report.json
```

This report classifies the available vocabulary into story affordance categories such as action verbs, crime nouns, evidence nouns, journalism nouns, movement/location words, conflict verbs, fantasy mechanism words, and dialogue alternatives. It is planning evidence, not an acceptance gate.

Use `--max-forbidden-unknown-tokens-per-chapter 0` only for a strict audit. The default is `5`, which is intended to prevent awkward forced rewrites while keeping unknown words visible.
