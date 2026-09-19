# First Frost reading-vocabulary pilot

This pilot uses the existing `Default` deck and `Chinese Vocabulary` note type. Its tracked content source is [`anki/first_frost/first_frost_pilot_notes.tsv`](../anki/first_frost/first_frost_pilot_notes.tsv). The source intake under `0. files/` is user-managed and is not required at runtime.

## Guardrails

- Search for duplicates across the entire `Chinese Vocabulary` note type, not only one deck.
- Reuse the single matching note and preserve its `Frequency Rank`, production flag, existing tags, and existing `Source` provenance.
- Apply the reviewed word pinyin, meaning, example, sentence pinyin, and translation. `盛` keeps the pilot's `chéng` reading first while retaining the valid `shèng` reading and sense.
- Add source and pilot tags without removing tags already on the note.
- Keep exactly the existing `Word Recognition` and `Sentence Recognition` templates. Do not add production cards.
- Never alter a reviewed or learning card's queue, due date, interval, ease, repetitions, or lapses.
- Unsuspend only unseen pilot recognition cards. Prioritize those unseen cards ahead of the active generic new-card queue.
- Keep priority persistent through tags of the form `pilot_first_frost_priority_NNN`; the global learning-order scheduler builds one complete queue with tagged priority cards first and assigns collision-free positions, including in the due-field fallback. It reads the queue back and fails if membership, order, or position uniqueness is wrong.
- Keep the unranked support characters `勉`, `慎`, and `谨` separate from the 60-note pilot. Their six unseen cards remain suspended.

## Commands

Run the manifest validator and read-only live preflight first:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/first_frost/validate_first_frost_pilot.py
python scripts/first_frost/setup_first_frost_pilot.py
```

Apply only after the dry run passes. The command writes `first_frost_pilot_before_apply_backup.tsv` before the first live mutation:

```powershell
python scripts/first_frost/setup_first_frost_pilot.py --apply
```

Verify the live cohort and then rerun the dry run to confirm content idempotence:

```powershell
python scripts/first_frost/setup_first_frost_pilot.py --verify-only
python scripts/first_frost/setup_first_frost_pilot.py
```

Normal `build_anki_chinese.py` rebuilds import the reviewed pilot examples and exact sentence pinyin from the tracked manifest. `apply_sentence_example_updates.py` merges pilot provenance instead of replacing an existing `Source` value.

Every application also writes a timestamped `*_backup.tsv` beside the original
backup before mutating Anki. Review-schedule and protected-field preservation are
checked against this fresh per-run snapshot, including cards learned since the
initial installation. The original backup remains unchanged for historical
counts and recovery. Apply reports identify both `backup` and `this_run_backup`.
These backups remain local/ignored. `--verify-only` checks current cohort content,
card shape, and priority; it does not compare today's schedules to installation
day or claim that no study has happened. Its preservation-check flags are false.

## Applied result

The September 8, 2026 application reused and updated 29 pilot notes and created 31. This produced the intended cohort of 60 word-recognition and 60 sentence-recognition cards: 58 cards were reused, 62 were newly created, and no production cards were created. Fifty-six existing unseen cards were unsuspended; together with the 62 new cards, 118 unseen pilot cards became accessible. The two previously reviewed `原谅` cards retained their scheduling state.

The installed AnkiConnect did not expose `reposition`, so the guarded fallback wrote due positions only on the 118 unseen pilot cards. Verification confirmed they are in pilot priority order ahead of the active generic new-card queue. It also confirmed 60 exact sentence round trips, all 120 rendered recognition-card previews, no duplicate notes, no unresolved pronunciation or sense conflicts, and six suspended support-character cards.
