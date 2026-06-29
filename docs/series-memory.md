# Series Memory Workflow

Series continuity needs two layers:

- per-manuscript continuity in `manuscripts/<slug>/continuity_log.md`;
- living series memory under `series/<series-slug>/`.

The manuscript log tracks what happened inside the current book. The series memory tracks only durable facts that future books must inherit.

## Series Memory Package

For the 林安 series, the active package is:

```text
series/an-lin/
  series_bible.md
  chronology.md
  character_registry.md
  mechanism_registry.md
  open_threads.md
  recurring_locations.md
  recurring_objects.md
  sequel_constraints.md
  series_update_log.md
```

For the 断剑山门 / Broken Sword Gate series, the active package is:

```text
series/broken-sword-gate/
  series_bible.md
  chronology.md
  character_registry.md
  mechanism_registry.md
  open_threads.md
  recurring_locations.md
  recurring_objects.md
  sequel_constraints.md
  series_update_log.md
```

Use the files this way:

- `series_bible.md`: stable promise, protagonist, genre, and current arc pressure.
- `chronology.md`: concise accepted-story summaries.
- `character_registry.md`: durable character roles, relationship changes, and continuity locks.
- `mechanism_registry.md`: fantasy mechanisms, rules, costs, limits, evidence split, and status.
- `open_threads.md`: unresolved questions, future seeds, and recently closed threads.
- `recurring_locations.md`: reusable location types and location-continuity guidance.
- `recurring_objects.md`: reusable object vocabulary checklist.
- `sequel_constraints.md`: hard rules for the next writer.
- `series_update_log.md`: append-only audit of post-story memory updates.

## Post-Story Update Gate

After a series manuscript reaches:

- vocabulary validation PASS;
- lead quality decision PASS;
- EPUB build success, when EPUB export applies;

run a continuity update pass before planning the next story.

Read:

- `manuscripts/<slug>/novel_bible.md`
- `manuscripts/<slug>/outline.md`
- `manuscripts/<slug>/continuity_log.md`
- `manuscripts/<slug>/quality/lead_quality_decision.md`
- the current series memory package

Then update:

1. `chronology.md`: add a concise accepted-story entry with case frame, mechanism, outcome, and arc movement.
2. `character_registry.md`: add only durable character facts and recurring-function changes.
3. `mechanism_registry.md`: record the mechanism, rule, cost, limits, evidence split, and relationship to earlier mechanisms.
4. `open_threads.md`: close resolved questions and add sequel seeds.
5. `series_bible.md`: update only if stable identity or current arc pressure changed.
6. `sequel_constraints.md`: update only if the next writer needs a new hard rule.
7. `series_update_log.md`: append date, manuscript slug, changed files, rationale, and next-story warning.

Do not turn the bible into a dumping ground. If a fact matters only to one book, leave it in that manuscript's continuity log.

## Verification

Run:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin
```

Add `--require-epub-build` when the accepted story should already have an EPUB build report or EPUB file:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin --require-epub-build
```

The checker confirms that required manuscript and series files exist, the lead decision is PASS, `chronology.md` mentions the manuscript, and `series_update_log.md` contains the manuscript slug.

The next story may not begin planning until this check passes for the previous accepted story.
