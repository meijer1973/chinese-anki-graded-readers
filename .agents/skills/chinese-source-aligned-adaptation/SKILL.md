---
name: chinese-source-aligned-adaptation
description: Adapt existing Chinese EPUB or source text into a controlled-vocabulary graded reader. Use when Codex needs to import an EPUB, profile source vocabulary, propose proper nouns or stretch words, preserve source fidelity, or create a minimally changed adapted manuscript.
---

# Chinese Source-Aligned Adaptation

Use this skill for EPUB-to-graded-reader adaptation. Do not use it for original fiction from scratch.

## Core Rule

Diagnose first, classify vocabulary second, rewrite last.

Do not treat 98% readable coverage as repo validity. A final adapted manuscript must still validate under the repo vocabulary layers and stay within the configured per-chapter forbidden-unknown budget.

## Rights Gate

Before extracting or adapting, classify the source:

- `public_domain`, `licensed`, or `own_text`: full adapted manuscript may be tracked and exported.
- `private_study`: keep raw EPUB, extracted source, and derivative source units local/private.
- `unclear`: create analysis reports and transformation plans only.

Never commit raw copyrighted EPUBs or full extracted copyrighted source. Source intake paths are ignored by Git by default.

## Intake

Run:

```powershell
python scripts/import_epub_for_adaptation.py --epub "<file>.epub" --slug <slug> --rights-status private_study --copy-source-private
```

This creates:

- `adaptations/<slug>/source_map.json`
- `adaptations/<slug>/adaptation_config.json`
- `adaptations/<slug>/adaptation_plan.md`
- ignored source units under `adaptations/<slug>/source_units/`

## Baseline Profile

Run:

```powershell
python scripts/profile_adaptation_vocabulary.py --adaptation adaptations/<slug> --known data/known_words.txt
```

Add the same `--personal-known`, `--known-character-compounds` when Marcel personalized mode uses it, stretch-pack, `--book-specific`, and `--proper-nouns` arguments expected for the target reader profile.

Review:

- `vocabulary_profile_baseline.json`
- `proper_noun_candidates.tsv`
- `stretch_candidates.tsv`

## Candidate Decisions

Classify unknowns in this order:

- proper noun -> `manuscripts/<slug>/proper_nouns.txt`
- known to Marcel -> learner profile, not stretch
- reusable high-value word -> reviewed stretch pack
- book-only necessary term -> `book_specific_words.txt`
- replaceable hard word -> rewrite or substitute

Do not dump every unknown into stretch or book-specific words.

## Minimal-Intervention Cascade

For each source unit, stop at the lowest level that reaches the target:

1. classify proper nouns, personal-known words, and enabled high-frequency character compounds
2. approve high-value stretch or book-specific words
3. replace hard word with a known synonym
4. simplify phrase
5. split or simplify sentence
6. rewrite paragraph while preserving source facts
7. condense or summarize only when required

No reason, no change.

## Manuscript Integration

Adapted output must use the normal manuscript layout:

- `chapters/*.zh-tok.txt` as canonical tokenized Chinese
- `planning/chapter_XX_vocab_plan.md`
- `adaptation_log.md`
- `book_specific_words.txt`
- `proper_nouns.txt`
- `quality/source_fidelity_report.md`

Each chapter plan must list source units covered, target plot beats, proper nouns, stretch words, risky concepts, expected coverage, and allowed adaptation level.

`adaptation_log.md` must record source-unit IDs, intervention level, changes made, and rationale.

## Fidelity Gate

Before EPUB export, create `quality/source_fidelity_report.md` and require:

```text
Fidelity decision: PASS
```

Run:

```powershell
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt --require-source-fidelity
```

Then proceed through the normal validation, literary critic, normal reader, lead decision, and EPUB workflow.
