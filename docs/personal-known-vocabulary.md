# Personal-Known Vocabulary

Personal-known words are a learner-profile layer for words Marcel already recognizes with low cognitive load, even when they are outside the current frequency-core list.

Do not merge these words into `data/known_words.txt`. That file remains the first N ranked frequency entries from `word list chinese.txt`. Personal-known words answer a different question: "Can this learner read this word comfortably?"

## Layers

Use these categories separately:

- core frequency known: `data/known_words.txt`
- personal known: `data/learner_profiles/marcel/personal_known_words.txt`
- approved stretch packs: genre, setting, profession, business, journalism, and other reviewed packs
- book-specific words: `manuscripts/<slug>/book_specific_words.txt`
- proper nouns: `manuscripts/<slug>/proper_nouns.txt`

Public graded-reader mode uses core frequency words plus approved stretch words.

Marcel personalized mode uses core frequency words plus Marcel personal-known words plus approved stretch words.

## Marcel Profile Files

The current profile lives at:

```text
data/learner_profiles/marcel/
  personal_known_words.tsv
  personal_known_words.txt
  personal_known_words.metadata.json
  personal_known_exclusions.txt
  personal_known_audit.json
```

Hand-edit `personal_known_words.tsv`. The validator reads the generated `.txt`.

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
python scripts/sync_personal_known_words.py --profile data/learner_profiles/marcel --core data/known_words.txt --stretch-pack data/stretch_packs/general_fiction_100.txt --stretch-pack data/stretch_packs/low_fantasy_150.txt --stretch-pack data/stretch_packs/shanghai_setting_150.txt --stretch-pack data/stretch_packs/professions_social_roles_100.txt --stretch-pack data/stretch_packs/urban_objects_100.txt --stretch-pack data/stretch_packs/journalism_crime_50.txt --stretch-pack data/stretch_packs/business_economics_60.txt
```

Inspect:

```powershell
Get-Content -LiteralPath data/learner_profiles/marcel/personal_known_audit.json -Encoding UTF8
```

## Validation

Use public mode by omitting `--personal-known`.

Use Marcel personalized mode by adding:

```powershell
--personal-known data/learner_profiles/marcel/personal_known_words.txt
```

Example:

```powershell
python scripts/validate_book.py --known data/known_words.txt --personal-known data/learner_profiles/marcel/personal_known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --genre-pack data/stretch_packs/low_fantasy_150.txt --setting-pack data/stretch_packs/shanghai_setting_150.txt --profession-pack data/stretch_packs/professions_social_roles_100.txt --urban-objects-pack data/stretch_packs/urban_objects_100.txt --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt --book-specific manuscripts/<slug>/book_specific_words.txt --proper-nouns manuscripts/<slug>/proper_nouns.txt
```

The report distinguishes:

- `core_known_tokens`
- `personal_known_tokens`
- stretch-layer tokens
- `proper_noun_tokens`
- `forbidden_unknown_tokens`

Personal-known words are allowed, but they are not stretch words and do not count as core frequency coverage.

## Policy

- Do not use rare personal-known words merely because they are available.
- Prefer high-utility words that make the story clearer, more natural, or more emotionally precise.
- Keep `learning` words out of the personal-known allowlist until they are genuinely comfortable.
- For public graded readers, personal-known words do not count as generally known.
- Historical manuscript reports should keep the vocabulary profile they were generated under.
