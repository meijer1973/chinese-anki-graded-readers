# Hindi Anki Starter Deck

This repository also stores an independent Hindi language-learning deck. It is not part of the Chinese vocabulary deck or the controlled-vocabulary graded-reader system. Its TSV, note type, templates, tags, options preset, setup code, reports, and live Anki deck are separate.

## Fixed Live Identifiers

- Deck: `Hindi`
- Note type: `Hindi Vocabulary`
- Options preset: `Hindi - 5 new cards`
- Templates: `Word Recognition`, `Sentence Recognition`
- Managed tags: `hindi`, `hindi::core_100`, and one normalized `pos::*` tag

The setup script deliberately offers no deck-name or note-type override. Only the AnkiConnect URL is configurable. The initial source of truth is `anki/hindi/hindi_core_100.tsv`; the setup script manages a note by its `Word` on the `Hindi Vocabulary` note type.

## Field Schema

The note type contains these fields in this exact order:

1. `Word`
2. `Pronunciation`
3. `Meaning`
4. `Part of Speech`
5. `Example`
6. `Example Pronunciation`
7. `Example Meaning`
8. `Source`
9. `Labels`
10. `Frequency Rank`
11. `Notes`

It has no `Production Card`, meaning-recall, reverse, English-to-Hindi, or other production-control field.

## Recognition Templates

`Word Recognition` shows only the Devanagari target word on its front. Its back supplies pronunciation, meaning, optional part of speech, a visually secondary example, and optional notes.

`Sentence Recognition` is conditional on `Example` and shows only the Hindi sentence on its front. Its back supplies sentence pronunciation and meaning, followed by a separated target-word section. Both Hindi fronts use `lang="hi"`.

These are the only templates. Production cards do not merely remain suspended: no production template exists, so the Hindi note type cannot generate a production card.

## Pronunciation Convention

The deck uses an IAST-influenced practical pronunciation system rather than strict transliteration or IPA:

- `ā`, `ī`, and `ū` mark long vowels.
- `ṭ`, `ḍ`, and `ṇ` mark retroflex consonants; `ṛ` represents the flap written ड़.
- Aspiration is explicit: `kh`, `gh`, `chh`, `jh`, `ṭh`, `ḍh`, `th`, `dh`, `ph`, and `bh`.
- A tilde on the pronounced vowel marks nasalization: `mẽ`, `maĩ`, `haĩ`, `kahā̃`.
- Normal Hindi schwa deletion is applied: करना `karnā`, पहले `pahle`, देखना `dekhnā`, रहना `rahnā`.
- श and ष are both `sh` in ordinary modern pronunciation; conjuncts follow the spoken sequence, as in कक्षा `kakshā`.
- Common demonstratives follow ordinary speech: यह `yeh` and वह `vo`.

The same conventions are used in word and sentence pronunciation fields. No audio, TTS, or IPA is included.

## Vocabulary Sources and Curation

The primary frequency source is [Shabd: A Psycholinguistic Database for Hindi](https://osf.io/xfbhd/) (OSF `xfbhd`, DOI `10.3758/s13428-021-01625-2`). The OSF project marks its data CC0 1.0 Universal. The official Shabd v1.1 archive provides the frequency-sorted 96,122-form list used for source ranks.

The independent comparison uses the public Hindi tourism and health word-frequency files on the [IIIT Hyderabad LTRC KCIS resource page](https://ltrc.iiit.ac.in/showfile.php?filename=downloads%2Fkolhi%2F). That page did not state redistribution terms for the frequency files at access time, so the deck records only frequency/rank comparisons and copies no IIIT editorial material.

Curation began by reviewing Shabd's first 300 raw frequency entries. Punctuation, numeral tokens, encoding and web artifacts, dates, processing markers, names, named entities, duplicates, and highly news-specific vocabulary were removed. Plausible forms were compared across both IIIT domains. The final learner rank preserves common grammatical surface forms while balancing pronouns, question words, verbs and useful inflections, modifiers, and everyday nouns. Essential beginner forms underrepresented by newspaper data were selected from lower source ranks and retain those ranks in the TSV.

All glosses, usage notes, pronunciations, Hindi examples, example pronunciations, and translations were written or curated for this deck. Detailed provenance and the conflict-resolution policy live in `anki/hindi/hindi_core_100.sources.json`.

## Data Validation

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/hindi/validate_hindi_core_100.py
```

The validator checks the exact 100-row/100-word/rank 1–100 contract, required fields, Devanagari, exact target occurrence, unique examples, physical TSV structure, NFC normalization, whitespace, forbidden production columns, source metadata, and the 3–10-word example target. It writes `anki/hindi/reports/data_validation_report.json` with part-of-speech, label, sentence-length, duplicate, missing-field, and normalization summaries.

## Safe Live Commands

The default is a non-mutating dry run:

```powershell
python scripts/hindi/setup_hindi_anki.py
python scripts/hindi/setup_hindi_anki.py --dry-run
```

Apply only after reviewing the dry-run report:

```powershell
python scripts/hindi/setup_hindi_anki.py --apply
```

Inspect the final live state without mutation:

```powershell
python scripts/hindi/setup_hindi_anki.py --verify-only
```

The local endpoint defaults to `http://127.0.0.1:8765`. A different URL can be supplied with `--anki-connect-url`; deck and note-type identities cannot be overridden.

If Anki or AnkiConnect is unavailable, validation still works and the live command writes a blocked report. Start Anki, confirm AnkiConnect API version 6 is available, rerun dry-run, then apply explicitly.

## Five Cards Per Day

The script inspects the preset inherited by the new top-level `Hindi` deck, clones it to `Hindi - 5 new cards`, assigns the clone only to Hindi, and sets `new.perDay` to `5`. This means five new cards per day, not five notes. Because each note has two recognition cards, the complete collection still contains 100 notes and 200 cards.

Other learning, relearning, lapse, review, FSRS, and burying settings are preserved. For deterministic display, Hindi alone uses deck/ascending-position gathering and `Order gathered` sorting. The latter is required so each rank's Word Recognition card can immediately precede its Sentence Recognition card. The maximum review-card limit is not changed.

## Idempotent Updates and Ordering

On a compatible existing install, the script updates changed TSV-backed fields on the existing note IDs, adds missing managed tags without replacing unrelated tags, and preserves compatible cards and their review history. It does not duplicate notes, cards, or templates. Existing managed notes are backed up to `anki/hindi/reports/hindi_managed_notes_before_update.tsv` before field updates.

New cards are ordered by `Frequency Rank`, with template order inside each rank:

```text
rank 1 Word Recognition
rank 1 Sentence Recognition
rank 2 Word Recognition
rank 2 Sentence Recognition
...
```

AnkiConnect `reposition` is preferred. A guarded due-field fallback is used only when the installed AnkiConnect does not support repositioning. Reviewed cards are never repositioned.

## Chinese Isolation and Safety Snapshots

Before apply, the setup captures the current `deck:Default` note IDs, card IDs, fields, tags, template ordinals, queue/scheduling state, `Chinese Vocabulary` schema/templates/styling, and Default options configuration. It writes a deterministic JSON snapshot and SHA-256 digest. The same snapshot is taken after apply.

Apply passes only when the structured snapshots and hashes are identical. Runtime guards reject mutations involving `Default`, `Chinese Vocabulary`, protected Chinese note/card IDs, or the protected Default configuration ID. Mutating calls are whitelisted for only `Hindi`, `Hindi Vocabulary`, `Hindi - 5 new cards`, and registered Hindi IDs.

Reports are written under `anki/hindi/reports/`, including dry-run, apply, verification, and Chinese before/after/comparison files.
The full Chinese before/after snapshots and the compatible-note backup remain local because they contain personal collection IDs and scheduling state. Their comparison hashes and non-sensitive validation/setup summaries can be tracked safely.

## Adding Later Hindi Notes

1. Add a new UTF-8 TSV row using the same 12-column schema and assign the next unique study rank.
2. Keep the word and sentence pronunciation systems consistent.
3. Supply an original natural example containing the exact target form.
4. Update provenance if a new frequency source or selection rule is introduced.
5. Extend the dataset validator's expected count only as an intentional versioned change; do not silently weaken the Core 100 contract.
6. Run validation and dry-run before apply.

The current script intentionally enforces exactly 100 starter notes. Expansion should be a reviewed follow-up change with explicit count/version updates and new tests.

If an incompatible `Hindi` deck, `Hindi Vocabulary` note type, extra template, unmanaged Hindi note, Hindi subdeck, or Hindi Vocabulary note outside the guarded deck already exists, apply aborts without converting or deleting it. Resolve the name/content conflict manually or move the unrelated resource to an explicitly different identity, then rerun dry-run.
