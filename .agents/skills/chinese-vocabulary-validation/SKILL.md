---
name: chinese-vocabulary-validation
description: Mechanically validate space-tokenized Chinese chapters or books against the known-word list. Use when Codex needs exact token compliance reports, JSON validation artifacts, unknown-token frequency counts, or EPUB preflight checks.
---

# Chinese Vocabulary Validation

Treat validation as mechanical and auditable. Near matches do not count. A token is counted by its exact layer when it is in core known words or an approved layer. Forbidden unknown tokens are allowed only up to the configured per-chapter budget, currently 5, and every one must be reported.

## Chapter Validation

Run:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
```

The report includes total tokens, unique tokens, unknown-token count, unknown-token frequency, line numbers, and raw offending tokens.
The default forbidden-unknown budget is 5 tokens per chapter. Pass `--max-forbidden-unknown-tokens-per-chapter 0` for a strict zero-unknown audit.

For layered manuscripts, pass the configured packs:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

## Book Validation

Run:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json
```

Fail the workflow if any chapter has `forbidden_unknown_tokens_over_limit > 0`.

For layered reports, listed proper nouns count as the proper-noun layer and do not spend the forbidden-unknown budget.

## Parsing Contract

- Load known words from `data/known_words.txt`.
- Parse canonical story text as whitespace-separated tokens.
- Strip allowlisted punctuation from tokens.
- Count every non-empty remaining token.
- Accidental unsegmented Chinese strings are unknown unless the whole string is an allowed token.
- Produce JSON reports and a concise human-readable summary.
- Count core known tokens, general fiction stretch tokens, genre stretch tokens, setting stretch tokens, profession stretch tokens, book-specific stretch tokens, proper noun tokens, and forbidden unknown tokens.
- If a token appears in both core and a stretch pack, count it as core.
- Pass validation only when forbidden unknowns are at or below the configured per-chapter budget.
- Warn on too many new stretch words in one chapter, stretch words used only once, low core coverage, excessive stretch-token share, repeated phrase overuse, and narrow vocabulary.
- Do not forgive proper nouns unless they are listed in `proper_nouns.txt`.
