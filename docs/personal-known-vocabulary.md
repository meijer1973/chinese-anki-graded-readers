# Personal-Known Vocabulary

Personal-known words are a learner-profile layer for words Marcel already recognizes with low cognitive load, even when they are outside the current frequency-core list. Marcel personalized mode also has an auditable high-frequency character-compound layer for tokens made entirely from the first 500 ranked known characters.

Do not merge these words into `data/known_words.txt`. That file remains the first N ranked frequency entries from `High frequency words 0-10000.txt`. Personal-known words answer a different question: "Can this learner read this word comfortably?"

## Layers

Use these categories separately:

- core frequency known: `data/known_words.txt`
- personal known: `data/learner_profiles/marcel/personal_known_words.txt`
- high-frequency character compounds: `data/learner_profiles/marcel/high_frequency_characters.txt` with `--known-character-compound-limit 500`
- approved stretch packs: genre, setting, profession, business, journalism, and other reviewed packs
- book-specific words: `manuscripts/<slug>/book_specific_words.txt`
- proper nouns: `manuscripts/<slug>/proper_nouns.txt`

Public graded-reader mode uses core frequency words plus approved stretch words.

Marcel personalized mode uses core frequency words plus Marcel personal-known words, the optional top-500 high-frequency character-compound layer, plus approved stretch words.

## Marcel Profile Files

The current profile lives at:

```text
data/learner_profiles/marcel/
  personal_known_words.tsv
  personal_known_words.txt
  personal_known_words.metadata.json
  personal_known_exclusions.txt
  personal_known_audit.json
  high_frequency_characters.txt
```

Hand-edit `personal_known_words.tsv`. The validator reads the generated `.txt`. The ranked character file is a separate source; keep the default compound limit at 500 until a reviewed increase.

Required TSV columns:

```text
word	pinyin	meaning	source	status	reading_confidence	allow_in_personal_readers	notes
```

Allowed statuses:

- `known_active`: easy recognition, low load
- `known_passive`: recognized in context
- `learning`: still a learning target; use like stretch instead
- `uncertain`: not allowed yet

The sync script includes rows only when:

- `allow_in_personal_readers` is `yes`
- `status` is `known_active` or `known_passive`
- `reading_confidence` is at least `4`
- the word is not listed in `personal_known_exclusions.txt`
- the word is not already in the core known list

Core duplicates are deliberately excluded from `personal_known_words.txt`, because the validator should count them as core.

## Import And Sync

Bootstrap or refresh the TSV from LingQ CSV or one-word-per-line text exports:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/import_personal_known_words.py --sources "0. personal known words" --out data/learner_profiles/marcel/personal_known_words.tsv --status known_passive --reading-confidence 4 --allow yes
```

`0. personal known words/` is a user-managed local intake folder. Read it when importing user-provided lists, but do not reorganize or bulk-edit it unless the user asks.

After editing the TSV, regenerate the validator list and audit files:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/sync_personal_known_words.py --profile data/learner_profiles/marcel --core data/known_words.txt --stretch-pack data/stretch_packs/general_fiction_150.txt --stretch-pack data/stretch_packs/low_fantasy_150.txt --stretch-pack data/stretch_packs/shanghai_setting_150.txt --stretch-pack data/stretch_packs/professions_social_roles_100.txt --stretch-pack data/stretch_packs/urban_objects_100.txt --stretch-pack data/stretch_packs/journalism_crime_50.txt --stretch-pack data/stretch_packs/business_economics_150.txt
```

Inspect:

```powershell
Get-Content -LiteralPath data/learner_profiles/marcel/personal_known_audit.json -Encoding UTF8
```

## Validation

Use public mode by omitting `--personal-known` and `--known-character-compounds`.

Use Marcel personalized mode by adding:

```powershell
--personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 500
```

Example:

```powershell
python scripts/validate_book.py --known data/known_words.txt --personal-known data/learner_profiles/marcel/personal_known_words.txt --known-character-compounds --known-character-compound-limit 500 --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_150.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

The report distinguishes:

- `core_known_tokens`
- `personal_known_tokens`
- `high_frequency_character_compound_tokens`
- stretch-layer tokens
- `proper_noun_tokens`
- `forbidden_unknown_tokens`

Personal-known words and high-frequency character compounds are allowed in Marcel personalized mode, but they are not stretch words and do not count as core frequency coverage.

For Marcel personalized extensive reading, `personal_known_tokens` and `high_frequency_character_compound_tokens` count toward the 98% known-token floor. They do not count toward the 2% approved non-core/stretch ceiling.

## Policy

- Do not use rare personal-known words merely because they are available.
- Do not raise the high-frequency character-compound limit above 500 without a reviewed step.
- Prefer high-utility words that make the story clearer, more natural, or more emotionally precise.
- Keep `learning` words out of the personal-known allowlist until they are genuinely comfortable.
- For public graded readers, personal-known words do not count as generally known.
- Historical manuscript reports should keep the vocabulary profile they were generated under.
