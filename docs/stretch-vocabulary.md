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
- Book-specific: `manuscripts/<slug>/book_specific_words.txt`
- Proper nouns: `manuscripts/<slug>/proper_nouns.txt`

Pack names are aspirational sizes. Starter packs are intentionally smaller than 100 or 150 when good entries are not ready. Add durable, reusable words rather than filler.

Proper nouns are the right place for character, place, and organization names. Listed proper nouns are counted as the proper-noun layer, not as forbidden unknowns.

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

Stretch words should be repeated enough to become learnable. Track them in `stretch_word_exposure.md`.

## Validation

Use layered validation:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

The report counts tokens by layer, forbidden unknowns, forbidden unknowns over the per-chapter limit, core coverage, stretch-token share, stretch words used once, stretch words by chapter, and new stretch words by chapter.

Use `--max-forbidden-unknown-tokens-per-chapter 0` only for a strict audit. The default is `5`, which is intended to prevent awkward forced rewrites while keeping unknown words visible.
