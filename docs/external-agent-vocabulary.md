# External Agent Vocabulary Bundle

External writer agents that only need to draft or preflight Marcel-personalized graded-reader text should start with the compact three-file vocabulary bundle in `data/external_agent_vocab/`.

The current high-frequency character-compound limit is 1000; `high_frequency_characters_1000.txt` is the expected character file.

Fetch these three files first:

1. `data/external_agent_vocab/high_frequency_characters_1000.txt`
2. `data/external_agent_vocab/known_words_minus_character_compounds.txt`
3. `data/external_agent_vocab/master_stretch_words_non_core.txt`

Use this screening order:

1. Split canonical Chinese story text on spaces and strip allowlisted punctuation.
2. Check whether every Hanzi character in the token appears in `high_frequency_characters_1000.txt`. If yes, classify the token as `high_frequency_character_compound`.
3. If not, exact-match the token against `known_words_minus_character_compounds.txt`.
4. If not, exact-match the token against `master_stretch_words_non_core.txt`.
5. If not, exact-match project-local `book_specific_words.txt` and `proper_nouns.txt` when present.
6. Otherwise report the token as a forbidden unknown.

This keeps external downloads small and avoids checking the same token against both the high-frequency character-compound layer and the known-word or stretch-word lists.

Also track minimum difficulty while drafting. Count every token whose Hanzi characters all appear in the first 500 lines of `high_frequency_characters_1000.txt`; this is `easy_character_compound_token_percent` in repository validation. The hard ceiling is **95%**. As a soft target only, use some compact known words from the upper 50% of the active known-word baseline and some character compounds that need characters from the upper 50% of the enabled character-compound band when they fit the story naturally.

The compact bundle is a drafting and lightweight screening surface. Final manuscript reports remain authoritative only when generated with the repository validators, for example:

```powershell
python scripts/validate_book.py --known data/known_words.txt --personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 1000 --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_150.txt --genre-pack data/stretch_packs/fantasy_232.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --extra-pack data/stretch_packs/business_economics_150.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

Regenerate the bundle whenever `data/known_words.txt`, the high-frequency character limit, or any reusable stretch pack changes:

```powershell
python scripts/build_external_agent_vocab_bundle.py
python scripts/build_external_agent_vocab_bundle.py --check
```

The generator also writes `data/external_agent_vocab/metadata.json`, including source paths, counts, removed overlaps, and duplicate stretch entries.
