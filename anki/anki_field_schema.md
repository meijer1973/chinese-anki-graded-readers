# Stretch Word Anki Field Schema

This repository already manages the live Anki model `Chinese Vocabulary` with these fields:

```text
Word
Pinyin
Meaning
Example
Example Pinyin
Example Meaning
Source
Production Card
Sentence Card
Frequency Rank
```

Stretch words are exported for review before import. Do not mutate the live Anki collection directly from the novel-generation workflow.

## Candidate TSV Fields

`scripts/export_stretch_words_for_anki.py` writes:

```text
Hanzi
Pinyin
English
PartOfSpeech
Pack
Layer
Priority
SourceBook
FirstChapter
ExampleSentenceZhTok
ExampleSentenceZhNatural
ExampleSentenceEnglish
Status
Notes
```

## Mapping To Existing Model

- `Hanzi` -> `Word`
- `Pinyin` -> `Pinyin`
- `English` -> `Meaning`
- `ExampleSentenceZhNatural` -> `Example`
- `ExampleSentenceEnglish` -> `Example Meaning`
- `Pack`, `Layer`, `Priority`, `SourceBook`, `FirstChapter`, `Status`, and `Notes` -> review-only metadata unless a future migration adds fields.
- `Source` should identify the pack and optional source book, such as `stretch:low_fantasy_150`.
- `Frequency Rank` should remain blank until the word is promoted into the ranked core list.

When metadata includes `story_affordance`, `difficulty_note`, or `recommended_repetition_count`, the export script folds those values into `Notes` so the reviewer can see why the word exists and how often it should recur.

## Status Values

- `candidate`
- `approved`
- `exported`
- `imported`
- `active in Anki`
- `suspended`
- `learned`
- `promoted to core known list`

Use dry-run/review files first. Existing note IDs are not changed by this workflow.
