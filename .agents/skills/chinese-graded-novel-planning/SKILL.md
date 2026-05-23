---
name: chinese-graded-novel-planning
description: Plan complete Chinese graded-reader novels under a restricted known-word list. Use when Codex needs to create a novel bible, outline, character plan, setting, conflict, emotional arc, chapter plan, or feasibility assessment before drafting space-tokenized Chinese fiction.
---

# Chinese Graded Novel Planning

Plan before drafting. Read `data/known_words.txt` first, then inspect any project config, selected stretch packs, proper nouns, book-specific words, and existing manuscript files.

## Required Outputs

Create or update these files under `manuscripts/<project-slug>/`:

- `novel_bible.md`
- `outline.md`
- `characters.md`
- `continuity_log.md` with initial open questions and continuity anchors
- `book_specific_words.txt` when the story needs approved recurring terms
- `proper_nouns.txt` for character, place, and organization names
- `stretch_word_exposure.md` with a header row

## Planning Rules

- Infer what plots are possible from the available vocabulary.
- Prefer emotionally coherent plots with real pressure, choices, reversals, and curiosity over concepts that require unavailable words.
- For about 1000 known words, domestic drama, school life, workplace, travel, friendship, family, mystery-lite, and small-town conflict are viable, but they still need tension and chapter hooks.
- For larger lists, allow more complex genres only when the needed nouns, verbs, and abstract terms are present.
- Avoid plots requiring many unavailable legal, technical, medical, political, or epic-fantasy terms unless those exact tokens exist in core or approved stretch layers.
- Do not force a chapter count. Let chapter breaks follow the story's natural turns.
- Do not plan to a chapter word-count requirement. Chapter length is a story-shape decision, not a quota.
- Prefer the smallest chapter count that gives the premise, conflict, reversal, and ending enough room.
- If the config uses `low_fantasy_urban_shanghai`, plan easy low fantasy: normal Shanghai life plus one impossible thing.
- Prefer one strange object, one secret place, one hidden rule, one small danger, one mystery, a small cast, repeated locations, repeated magical terms, and clear emotional stakes.
- Avoid large invented worlds, kingdoms, races, large magic systems, lore dumps, complicated politics, many monsters, battle-heavy plots, and vocabulary that appears once and disappears.
- Include at least 3 distinct professions or social roles, at least 4 recurring locations beyond school/hospital/home, at least 2 characters whose role affects plot behavior, and at least 1 location that changes meaning over the story.

## Bible Contents

Include:

- premise
- target reader level
- proposed chapter breaks with a story reason for each break
- point of view
- main characters and relationships
- setting
- central conflict
- emotional arc
- chapter-by-chapter outline
- recurring phrases that are inside the known vocabulary
- risky concepts that may tempt the writer to use unavailable words
- chapter-level changes and hooks
- likely vocabulary breadth opportunities
- selected vocabulary packs
- book-specific stretch words
- proper noun list
- setting map and recurring locations
- character professions or social roles
- fantasy rule
- strange object or strange place
- central mystery
- stretch-word introduction schedule
- quality risks

Reject outline ideas that are only safe, flat, or repetitive. Vocabulary limits are a constraint, not an excuse for dull scenes.

For Shanghai low fantasy, the premise must be concrete and charged. It should feel like "a normal person in Shanghai discovers one impossible thing," not an epic fantasy frame. The final premise must be expressible using core words plus approved stretch vocabulary.

## Discovery Mode

For `discovery-with-control`, create premise, characters, ending direction, and only the next 1-2 chapter outlines. Require a revised forward outline every 3 chapters.
