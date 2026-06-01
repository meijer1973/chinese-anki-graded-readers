# Import Note — 上海镜街案

Suggested repository path:

```text
manuscripts/shanghai-mirror-street-case/
```

Canonical validation command to rerun after import:

```powershell
python scripts/validate_book.py `
  --known data/known_words.txt `
  --personal-known data/learner_profiles/marcel/personal_known_words.txt `
  --known-character-compounds `
  --known-character-compound-limit 300 `
  --chapters manuscripts/shanghai-mirror-street-case/chapters `
  --out manuscripts/shanghai-mirror-street-case/vocabulary_report.json `
  --general-fiction-pack data/stretch_packs/general_fiction_100.txt `
  --genre-pack data/stretch_packs/low_fantasy_150.txt `
  --setting-pack data/stretch_packs/shanghai_setting_150.txt `
  --profession-pack data/stretch_packs/professions_social_roles_100.txt `
  --urban-objects-pack data/stretch_packs/urban_objects_100.txt `
  --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt `
  --extra-pack data/stretch_packs/business_economics_60.txt `
  --book-specific manuscripts/shanghai-mirror-street-case/book_specific_words.txt `
  --proper-nouns manuscripts/shanghai-mirror-street-case/proper_nouns.txt
```
