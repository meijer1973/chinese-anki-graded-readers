# LingQ word selection — 24 September 2026

Completed the user's word-only practice selection from `lingqs (19).csv`
(20 terms) and `lingqs (20).csv` (200 terms): 220 unique Chinese terms.
Only the term columns supplied the requested vocabulary. CSV meanings were
not imported. The phrase for 海里 informed sense selection; new examples are
original, complete sentences.

## Result

| Item | Count |
| --- | ---: |
| Requested terms | 220 |
| Existing notes reused | 86 |
| Existing word cards unsuspended | 83 |
| Existing word cards already active | 3 |
| Requested notes created | 134 |
| Requested word cards active after verification | 220 |
| Requested sentence cards suspended after verification | 220 |
| Previously active sentence cards suspended | 1 |
| Unstudied selected word cards shuffled | 219 |
| Additional character-closure notes, fully suspended | 8 |

The eight supporting characters are 廷、慕、枕、歧、琢、绯、羡、耽.
Both cards of each remain suspended because these characters were not selected
by the user. All 142 additions have reviewed meanings, pinyin, and original
examples. Forty-one example-pinyin overrides correct contextual readings,
neutral tones, or tone sandhi. Existing notes' study fields were preserved.

Source entries were appended at positions 4438–4579, preserving prior ranks.
The source now contains 4579 entries and has complete coverage of its 2244 Hanzi
as standalone character notes. The live inventory has 4777 unique Chinese notes
and 9554 cards, with zero duplicate words and no missing ranked-source words.

## Learning order and routing

Selected unstudied word cards were randomized within their character or word
category and mixed into the active queue. Other unstudied cards kept their
relative order. Final queues contain 276 active new character cards and 182
active new multi-character word cards. The reviewed selected card retained its
schedule. Existing Deck gathering, daily limits, and retention options were
preserved; this operation did not enable cross-category position gathering.

New cards were imported into Default, then routed through the reviewed native
Anki procedure: 12 word cards to `Default::Single characters` and 142 sentence
cards to `Default::Sentences`. Multi-character word cards remain in Default.
The 12 character cards include the eight fully suspended supporting notes.

A full collection package with Include media enabled was exported outside the
repository. Archive integrity and its empty media manifest passed verification.
The package restored successfully into a separate unsynced test profile. Trial
routing, a no-op repeat, and live routing all passed, preserving stored memory
state, scheduling, review history, content, and suspension. The live routing
check covered 9954 cards and 16743 review records across the entire collection.
Normal sync and final verification completed successfully.

Private snapshots, exact IDs, randomized order plans, backup hashes, and routing
manifests remain outside Git in the ignored local-results folder and external
backup directory. No private study history is included in this report.

## Validation and sources

- Guarded importer: reviewed all 142 rows, collection-wide absence check,
  `canAddNotes` preflight, and duplicate protection including child decks.
- Post-selection preservation check: 4635 existing Chinese notes and 9670
  pre-existing collection cards, permitting only the requested suspension and
  new-card position changes.
- `python build_anki_chinese.py`
- `python ensure_single_character_notes.py` — zero missing characters; no
  additional notes or global live scheduling changes needed.
- `python -m pytest tests/test_add_chinese_words_to_anki.py tests/test_chinese_subdecks.py -q`
  — 24 tests and 87 subtests passed; two pre-existing pypinyin deprecation warnings.
- `python scripts/export_current_anki_words.py` — two consistent read-only
  inventory reads; zero duplicates.
- `git diff --check` — passed.

Meanings and headword readings were checked against the repository's CC-CEDICT
data and curated for learner use. Polyphonic senses of 琢磨 were additionally
checked against [Han Dian](https://www.zdic.net/hans/琢磨), and 伺候 against
[Han Dian](https://zdic.net/hans/伺候). 海里 includes the ordinary compositional
reading “in the sea” as well as the dictionary sense “nautical mile.”
