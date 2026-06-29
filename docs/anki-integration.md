# Anki Integration For Stretch Words

Stretch words must flow into Anki safely. The novel workflow does not directly mutate the live Anki collection.

Personal-known words are different from stretch words. They live under `data/learner_profiles/marcel/` and are allowed for Marcel-personalized readers because they are already recognized. Do not export the personal-known profile as new stretch cards unless a separate review says those words need Anki work.

## Existing Deck

The repo already assumes:

- AnkiConnect URL: `http://127.0.0.1:8765`
- Note model: `Chinese Vocabulary`
- Main fields: `Word`, `Pinyin`, `Meaning`, `Example`, `Example Pinyin`, `Example Meaning`, `Source`, `Production Card`, `Sentence Card`, `Frequency Rank`

See `anki/anki_field_schema.md` for the stretch candidate field mapping.

## New-Card Learning Order

`word list chinese.txt` remains the frequency-ranked source list for the Anki deck. Graded-reader core known words are generated separately from `High frequency words 0-10000.txt`. Do not hand-mix appended single-character closure notes into the Anki source list unless the frequency-rank meaning is explicitly redesigned.

Single-character coverage and study order are handled separately:

```powershell
python scripts/audit_anki_card_distribution.py
python scripts/schedule_anki_learning_order.py
```

The scheduler writes `anki/learning_order_plan.tsv` and `single_character_distribution_report.md`. It keeps Chinese-to-English cards unsuspended, then sets new-card due order so single-character and multi-character notes are interleaved as evenly as the available queue allows. `Frequency Rank` continues to mean the source-list rank; learning order is a generated plan, not a replacement rank.

## Export Candidates

Create a review TSV:

```powershell
python scripts/export_stretch_words_for_anki.py --packs data/stretch_packs/general_fiction_150.txt data/stretch_packs/fantasy_200.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/professions_social_roles_100.txt data/stretch_packs/urban_objects_100.txt data/stretch_packs/journalism_crime_50.txt data/stretch_packs/business_economics_150.txt --metadata data/stretch_packs/metadata --existing-anki anki/existing_words.txt --out anki/stretch_word_candidates.tsv --report anki/stretch_word_import_log.json
```

The export:

- excludes core known words
- excludes existing Anki words when `anki/existing_words.txt` is available
- avoids duplicates across packs
- includes metadata when present
- marks each row as `candidate`

Review candidates before import. Use the existing Anki scripts only after review.

Add `--dry-run` to collect counts and missing-metadata warnings without writing the candidate TSV.

After review and explicit user approval, import through AnkiConnect:

```powershell
python scripts/import_stretch_words_to_anki.py --candidates anki/stretch_word_candidates.tsv --dry-run
python scripts/import_stretch_words_to_anki.py --candidates anki/stretch_word_candidates.tsv
python scripts/import_stretch_words_to_anki.py --candidates anki/stretch_word_candidates.tsv --mark-existing-stretch --dry-run
python scripts/import_stretch_words_to_anki.py --candidates anki/stretch_word_candidates.tsv --mark-existing-stretch
python scripts/import_stretch_words_to_anki.py --candidates anki/stretch_word_candidates.tsv --verify-only
```

The import script skips words already present in the configured Anki deck and suspends production cards for newly added stretch notes. `--mark-existing-stretch` adds stretch tags to candidate words that already existed in Anki without overwriting their study fields. It writes local import logs and review TSVs under `anki/`.

## Complete Metadata

Every stretch pack should have metadata for every word. Complete or refresh generated starter metadata with:

```powershell
python scripts/complete_stretch_pack_metadata.py --packs data/stretch_packs/general_fiction_150.txt data/stretch_packs/fantasy_200.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/professions_social_roles_100.txt data/stretch_packs/urban_objects_100.txt data/stretch_packs/journalism_crime_50.txt data/stretch_packs/business_economics_150.txt
```

The script preserves existing curated metadata and fills missing entries with generated pinyin, CEDICT/fallback English, simple example sentences, story affordance notes, difficulty notes, and recommended repetition counts. Generated entries are starter metadata and can be curated later.

## Status Tracking

Use these statuses:

- `candidate`
- `approved`
- `exported`
- `imported`
- `active in Anki`
- `suspended`
- `learned`
- `promoted to core known list`

## Promotion To Core

When words are learned, create a reviewed list and write a new known-word file:

```powershell
python scripts/promote_stretch_words.py --approved anki/learned_stretch_words.txt --core data/known_words.txt --stretch-packs data/stretch_packs --out data/known_words.updated.txt --audit anki/stretch_word_promotion_audit.json
```

Do not rewrite historical manuscript reports. Future books can use the updated known list as core.

Add `--dry-run` to preview promotion without writing the updated known-word file.
