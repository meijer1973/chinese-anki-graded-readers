# Spanish Anki Starter Deck

This repository stores an independent Spanish language-learning deck alongside, but not inside, the Chinese and Hindi decks. Its TSV, note type, templates, tags, options preset, setup code, reports, and live Anki deck are separate.

## Fixed Live Identifiers

- Deck: `Spanish`
- Note type: `Spanish Vocabulary`
- Options preset: `Spanish - 5 new cards`
- Templates: `Word Recognition`, `Sentence Recognition`
- Managed tags: `spanish`, `spanish::core_100`, and one normalized `pos::*` tag

The setup script deliberately offers no deck-name, note-type, or options-preset override. Only the AnkiConnect URL and source-file paths are configurable. The source of truth is `anki/spanish/spanish_core_100.tsv`; a managed note is identified by its `Word` on the `Spanish Vocabulary` note type.

## Field Schema

The note type contains these fields in this exact order:

1. `Word`
2. `IPA`
3. `Meaning`
4. `Part of Speech`
5. `Lemma`
6. `Example`
7. `Example IPA`
8. `Example Meaning`
9. `Source`
10. `Labels`
11. `Frequency Rank`
12. `Notes`

`Source Rank` is retained in the 13-column TSV for provenance but is not copied into the live note model. Every TSV field is populated. In the live notes, `Lemma` is intentionally blank when it is identical to `Word`, allowing the templates to show the lemma only when it differs.

The schema has no production, recall, reverse, English-to-Spanish, or sentence-production field.

## Recognition Templates

`Word Recognition` shows only the Spanish surface form on its front. Its back supplies IPA, meaning, part of speech, a differing lemma when applicable, the example and connected-speech IPA, the translation, and notes.

`Sentence Recognition` is conditional on `Example` and shows only the Spanish sentence on its front. Its back supplies sentence IPA and meaning, followed by a separated target-word section with word IPA, meaning, differing lemma, part of speech, and notes.

Both fronts use `lang="es"`. Styling uses a mobile-friendly system font stack, responsive type sizes, and light/dark colors. There are no external fonts and no JavaScript.

These are the only templates. Production cards are not suspended: no production template exists, so the note type cannot generate a production card.

## IPA Convention

Word pronunciation is broad phonemic IPA between slashes. Sentence pronunciation is broad connected-speech IPA between square brackets.

The documented reference variety is modern educated neutral Spanish with seseo and yeísmo, chosen for broad international learner usefulness:

- `c` before `e/i` and `z` are /s/.
- `ll` and consonantal `y` are /ʝ/.
- Single intervocalic `r` is /ɾ/; trill `r/rr` is /r/.
- `j` and `g` before `e/i` are /x/.
- Sentence transcriptions include common intervocalic [β ð ɣ] and predictable nasal place assimilation.
- Narrow regional reductions, aspiration, and casual deletions are not imposed.

This is IPA, not a simplified learner respelling.

## Vocabulary Sources and Curation

The primary source is [SUBTLEX-ESP](https://biblio.ugent.be/publication/2001948), the Spanish film-and-television subtitle frequency database described by Cuetos, Glez-Nosti, Barbón, and Brysbaert (2011). The cross-check is the [FrequencyWords OpenSubtitles2018 Spanish list](https://github.com/hermitdave/FrequencyWords). The third independent source is [OpenSLR SLR21](https://www.openslr.org/21/), whose Spanish counts derive from Spanish Gigaword news text.

Curation reviewed a normalized 200-item working shortlist from the highest-frequency ranges. It removed numbers, punctuation-only items, abbreviations, names, case duplicates, encoding and processing artefacts, corpus markup, and narrow dialogue fillers. Exact surface forms were retained rather than collapsed to lemmas, including useful conjugations and accent contrasts such as `si/sí`, `tu/tú`, `que/qué`, `como/cómo`, and `cuando/cuándo`.

The final learner rank balances source frequency with beginner usefulness across function words, pronouns, prepositions, conjunctions, verb forms, infinitives, question words, adverbs, common nouns, adjectives, and greetings. Each TSV row records all three one-based source ranks, or `n/a` when a surface form is absent from a source.

All meanings, labels, grammatical notes, examples, translations, and IPA were written and reviewed for this deck. No example sentence was copied from a source corpus or dictionary. Exact download URLs, hashes, licenses or redistribution notes, rank semantics, and exclusions are recorded in `anki/spanish/spanish_core_100.sources.json`. The downloaded source archives are not stored in this repository.

## Data Validation

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/spanish/validate_spanish_core_100.py
```

The validator checks:

- exactly 100 data rows and 100 unique surface forms;
- ranks 1–100 exactly once;
- the exact 13-column schema and 12 tab separators per physical line;
- no empty fields or production-like columns;
- valid UTF-8 and NFC-normalized, trimmed text;
- one Spanish-letter surface token without digits;
- exact target-token occurrence in its example;
- unique original examples of 4–12 words;
- slash-delimited word IPA and square-bracket sentence IPA;
- at least three documented sources and complete provenance metadata.

It writes `anki/spanish/reports/data_validation_report.json`, including part-of-speech, label, sentence-length, duplicate, missing-field, and normalization summaries.

## Safe Live Commands

The default is a non-mutating dry run:

```powershell
python scripts/spanish/setup_spanish_anki.py
python scripts/spanish/setup_spanish_anki.py --dry-run
```

Apply only after reviewing the dry-run report:

```powershell
python scripts/spanish/setup_spanish_anki.py --apply
```

Inspect the final live state without mutation:

```powershell
python scripts/spanish/setup_spanish_anki.py --verify-only
```

The endpoint defaults to `http://127.0.0.1:8765`. A different URL can be supplied with `--anki-connect-url`.

If Anki or AnkiConnect is unavailable, data validation still works and the live command writes a blocked report. Start Anki, confirm AnkiConnect API version 6 is available, rerun dry-run, and then apply explicitly.

## Five New Cards Per Day

The script inspects the preset inherited by the new top-level `Spanish` deck, clones it to `Spanish - 5 new cards`, assigns the clone only to Spanish, and sets `new.perDay` to `5`. This means five new cards per day, not five notes. The complete starter collection contains 100 notes and 200 cards.

Other learning, relearning, lapse, review, FSRS, and burying settings are preserved. Spanish alone uses deck/ascending-position gathering and `Order gathered` sorting so every rank's Word Recognition card precedes its Sentence Recognition card. The maximum review-card limit is not changed.

## Idempotent Updates and Ordering

On a compatible existing install, changed TSV-backed fields update existing note IDs. Missing managed tags are added without replacing unrelated tags. Compatible cards and their review history are preserved. The script does not duplicate notes, cards, or templates.

Before field updates, existing managed notes are backed up locally to `anki/spanish/reports/spanish_managed_notes_before_update.tsv`.

New cards are ordered:

```text
rank 1 Word Recognition
rank 1 Sentence Recognition
rank 2 Word Recognition
rank 2 Sentence Recognition
...
```

AnkiConnect `reposition` is preferred. A guarded due-field fallback is used only when the installed AnkiConnect does not support repositioning. Reviewed cards are never repositioned.

## Chinese and Hindi Isolation

Before apply, the setup captures deterministic snapshots of both protected decks:

- deck IDs, note IDs, card IDs, fields, tags, and template ordinals;
- queue and review scheduling state;
- the `Chinese Vocabulary` and `Hindi Vocabulary` schemas, templates, and styling;
- the Default/Chinese and Hindi deck-options configurations.

The same snapshots are taken after apply. Apply passes only when each protected structured snapshot and SHA-256 hash is identical. Runtime guards reject mutations involving either protected deck, either protected note type, protected note/card IDs, or protected options configurations.

Mutating calls are whitelisted only for `Spanish`, `Spanish Vocabulary`, `Spanish - 5 new cards`, and registered Spanish IDs.

Reports under `anki/spanish/reports/` include validation, dry-run, apply, live verification, Chinese comparison, and Hindi comparison results. Full before/after snapshots and managed-note backups remain local because they contain personal collection IDs and scheduling state.

## Tests

Run the focused tests:

```powershell
python -m unittest tests.test_spanish_core_100 tests.test_spanish_anki_templates tests.test_spanish_anki_setup tests.test_spanish_anki_safety -v
```

They verify the 100-note/200-card contract, exactly two recognition templates, zero production templates/cards, the independent five-card preset, ordering, idempotence, compatible field updates without replacing cards, and unchanged Chinese and Hindi resources.

## Later Expansion

The current validator and installer intentionally enforce exactly 100 starter notes. Expansion should be a reviewed, versioned follow-up:

1. Add UTF-8 TSV rows with the same 13-column schema and unique study ranks.
2. Keep the documented IPA convention.
3. Supply an original 4–12-word example containing the exact surface form.
4. Update provenance for any new source or selection rule.
5. Intentionally update the expected count and tests.
6. Validate, dry-run, apply, and verify in that order.

If an incompatible `Spanish` deck, `Spanish Vocabulary` note type, extra template, unmanaged Spanish note, Spanish subdeck, or Spanish Vocabulary note outside the guarded deck exists, apply aborts without converting or deleting it.
