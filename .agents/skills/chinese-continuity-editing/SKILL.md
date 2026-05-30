---
name: chinese-continuity-editing
description: Maintain continuity for multi-chapter restricted-vocabulary Chinese fiction. Use when Codex needs to review chapters, update continuity_log.md, track characters, events, objects, settings, timeline, unresolved questions, or propose minimal continuity fixes.
---

# Chinese Continuity Editing

Read all existing manuscript planning files and prior chapters before judging continuity.

## Track

- character names and relationships
- promises, conflicts, secrets, and decisions
- locations and timeline
- important objects
- unresolved questions
- emotional changes
- vocabulary risks if fixes touch story text

## After Each Chapter

Update `manuscripts/<slug>/continuity_log.md` with:

- chapter summary
- new facts
- changed relationships
- open questions
- objects gained, lost, or moved
- timeline notes
- required setup for the next chapter

## After Each Accepted Series Story

For 林安 series manuscripts that have vocabulary validation PASS, lead quality decision PASS, and EPUB build success if applicable, update the living series memory package before the next story is planned.

Read:

- `manuscripts/<slug>/novel_bible.md`
- `manuscripts/<slug>/outline.md`
- `manuscripts/<slug>/continuity_log.md`
- `manuscripts/<slug>/quality/lead_quality_decision.md`
- `series/an-lin/series_bible.md`
- `series/an-lin/chronology.md`
- `series/an-lin/character_registry.md`
- `series/an-lin/mechanism_registry.md`
- `series/an-lin/open_threads.md`
- `series/an-lin/sequel_constraints.md`
- `series/an-lin/series_update_log.md`

Then update:

- `chronology.md` with case frame, fantasy mechanism, outcome, and arc movement;
- `character_registry.md` with durable character facts only;
- `mechanism_registry.md` with mechanism rule, cost, limits, evidence split, and relation to earlier mechanisms;
- `open_threads.md` with resolved and new threads;
- `series_bible.md` only when stable identity or current arc pressure changed;
- `series_update_log.md` with date, slug, changed files, rationale, and next-story warning.

Run `python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin` after the update.

## Contradiction Checks

Look for name changes, impossible event order, location drift, forgotten unresolved plot points, unexplained emotional resets, and objects that appear or disappear without reason.

If story text needs repair, suggest minimal edits in canonical space-tokenized Chinese and require vocabulary validation afterward.
