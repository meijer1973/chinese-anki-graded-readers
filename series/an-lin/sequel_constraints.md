# 林安 Sequel Constraints

## Must Keep

- 林安 is a journalist / crime reporter.
- 陈雨 is a recurring police contact.
- The genre is urban fantasy crime, not epic fantasy.
- Each book should have a Shanghai crime case plus one impossible low-fantasy mechanism.
- The fantasy should be small, repeated, and emotionally relevant.
- The story should use journalism actions: interview, confirm, protect a source, write or publish, and face pressure.
- Planning must begin from the current living series memory package, including `chronology.md`, `character_registry.md`, `mechanism_registry.md`, `open_threads.md`, and `series_update_log.md`.

## Must Avoid

- Do not restart 林安 as a different profession.
- Do not ignore `manuscripts/shanghai-rain-gate-crime/`.
- Do not add many invented places, races, monsters, kingdoms, or lore systems.
- Do not let supporting characters only sit and explain.
- Do not use Shanghai place names as decoration only.
- Do not introduce stretch words once and then abandon them.

## Required Planning Additions For Sequel Chapters

Each chapter vocabulary plan must include:

- case function: new clue, false lead, witness pressure, suspect pressure, or public reporting consequence
- journalist function: interview, verify, publish, protect source, or face legal/ethical risk
- fantasy function: impossible clue, altered memory, shadow gate, or supernatural cost
- learning function: 5-10 repeated stretch words from earlier chapters and normally 3-5 new stretch words at most

## Required Book-Level Variation Budget

Before drafting, `creative_preflight.md` must state at least three deliberate differences from the previous 林安 story:

- investigation structure
- emotional wound
- antagonist pressure
- fantasy mechanism
- location ecosystem
- moral dilemma
- narrative rhythm
- ending type

Continuity is not a formula. The next book should keep 林安, 陈雨, Shanghai, journalism pressure, and one small impossible mechanism, but it should not simply repeat crime, strange object, memory cost, and publication choice in the same rhythm.

After `上海镜街案`, the next 林安 story should treat `明日报` as the active arc clue. It should not reopen 旧城门 or 镜街 from zero, and it should not repeat the same reputation-contract / edited-public-face case structure unless the variation budget gives a strong reason.

## Required Pre-Planning Memory Check

Before planning the next 林安 manuscript, confirm that the previous accepted story has:

- a concise `chronology.md` entry;
- durable character changes added to `character_registry.md`, if any;
- mechanism rules, costs, and limits captured in `mechanism_registry.md`;
- resolved and new unresolved questions reflected in `open_threads.md`;
- an audit entry in `series_update_log.md`.

Use:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<previous-slug> --series-dir series/an-lin
```

If the checker fails, update the series memory package before creating the next `creative_preflight.md`.
