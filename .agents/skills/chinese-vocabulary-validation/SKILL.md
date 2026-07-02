---
name: chinese-vocabulary-validation
description: Mechanically validate space-tokenized Chinese chapters or books against the known-word list. Use when Codex needs exact token compliance reports, JSON validation artifacts, unknown-token frequency counts, or EPUB preflight checks.
---

# Chinese Vocabulary Validation

Treat validation as mechanical and auditable. Near matches do not count. A token is counted by its exact layer when it is in core known words or an approved layer. Extensive-reading validation requires at least 98% known tokens, at most 2% approved non-core tokens, and at most 95% first-500 character-compound tokens by default. Approved non-core tokens include stretch layers, book-specific words, and listed proper nouns. Forbidden unknown tokens are allowed only up to the configured per-chapter budget, currently 5, and every one must be reported; they still reduce known-token coverage.

Before validating, state the vocabulary profile:

- Public mode: core known words plus approved stretch/book/proper-noun layers only.
- Marcel personalized mode: core known words plus `data/learner_profiles/marcel/personal_known_words.txt`, optional top-1000 high-frequency character compounds, plus approved stretch/book/proper-noun layers.

## Chapter Validation

Run:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json
```

The report includes total tokens, unique tokens, unknown-token count, unknown-token frequency, line numbers, and raw offending tokens.
The default forbidden-unknown budget is 5 tokens per chapter. Pass `--max-forbidden-unknown-tokens-per-chapter 0` for a strict zero-unknown audit.

For layered manuscripts, pass the configured packs:

```powershell
python scripts/validate_chapter.py --known data/known_words.txt --chapter manuscripts/<slug>/chapters/chapter_01.zh-tok.txt --out manuscripts/<slug>/chapters/chapter_01.validation.json --general-fiction-pack data/stretch_packs/general_fiction_150.txt --genre-pack data/stretch_packs/fantasy_232.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

## Book Validation

Run:

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json
```

Fail the workflow if any chapter has `forbidden_unknown_tokens_over_limit > 0`, `known_token_percent_allowed == false`, `stretch_token_percent_allowed == false`, or `easy_character_compound_token_percent_allowed == false`.

For layered reports, listed proper nouns count as the proper-noun layer and do not spend the forbidden-unknown budget.

For Marcel personalized readers, pass the learner-profile layer:

```powershell
--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 1000
```

The `--known-character-compounds` flag defaults to `data/learner_profiles/marcel/high_frequency_characters.txt`. It is a conservative, auditable Marcel-specific layer: top 1000 ranked characters now, with later increases made by changing only the limit.

Minimum difficulty is audited separately from the high-frequency character-compound layer. By default, validators count every token made only from the first 500 ranked characters in `data/learner_profiles/marcel/high_frequency_characters.txt` and fail when `easy_character_compound_token_percent` is above 95%.

For external Marcel-personalized drafting or quick token screening, prefer the compact bundle documented in `docs/external-agent-vocabulary.md`: `data/external_agent_vocab/high_frequency_characters_1000.txt`, `data/external_agent_vocab/known_words_minus_character_compounds.txt`, and `data/external_agent_vocab/master_stretch_words_non_core.txt`. Check high-frequency character compounds first, then compact known words, then compact non-core stretch words. Do not treat that bundle as the final report; run the validator scripts for authoritative JSON evidence.

## Parsing Contract

- Load known words from `data/known_words.txt`.
- In Marcel personalized mode, an optional derived layer may allow tokens made only from the top ranked characters in `data/learner_profiles/marcel/high_frequency_characters.txt`; use `--known-character-compounds --known-character-compound-limit 1000`.
- Parse canonical story text as whitespace-separated tokens.
- Strip allowlisted punctuation from tokens.
- Count every non-empty remaining token.
- Accidental unsegmented Chinese strings are unknown unless the whole string is an allowed token.
- Produce JSON reports and a concise human-readable summary.
- Count core known tokens, learner-profile personal-known tokens, general fiction stretch tokens, genre stretch tokens, setting stretch tokens, profession stretch tokens, book-specific stretch tokens, proper noun tokens, and forbidden unknown tokens.
- Count high-frequency character-compound tokens separately from core, personal-known, stretch, proper nouns, and forbidden unknowns.
- If a token appears in both core and a stretch pack, count it as core.
- If a token appears in both personal-known and a stretch pack, count it as personal-known.
- If a token is not in any exact word layer but every Hanzi character in it is within the enabled top-N ranked character set, count it as `high_frequency_character_compound`, not as an invisible unknown.
- Pass validation only when forbidden unknowns are at or below the configured per-chapter budget, known-token coverage is at least 98%, approved non-core/stretch-token share is at most 2%, and first-500 character-compound token share is at most 95%.
- Warn on too many new stretch words in one chapter, stretch words used only once, low core coverage, excessive stretch-token share, repeated phrase overuse, and narrow vocabulary.
- Do not forgive proper nouns unless they are listed in `proper_nouns.txt`.
