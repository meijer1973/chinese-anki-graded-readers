# EPUB-To-Graded-Reader Adaptation

This workflow converts an existing Chinese EPUB into a source-aligned graded reader. It is separate from original-fiction generation and Anki deck management.

The rule is:

```text
Diagnose first. Classify vocabulary second. Rewrite last.
```

Do not treat `98%` readable coverage as automatic validity. Repo-valid adapted manuscripts must still use the normal vocabulary layers, keep forbidden unknowns visible, stay within the configured per-chapter budget, and pass the normal 98% known-token / 2% approved non-core / 95% first-500 character-compound validation gates.

## Rights Gate

Classify the source before extraction:

| Source type | Allowed output |
|---|---|
| public domain, licensed, or your own text | full adapted graded reader can be tracked and exported |
| copyrighted text for private study | keep raw EPUB, extracted source, and derivative source units local/private |
| unclear rights | create analysis reports, vocabulary profiles, candidates, and plans only |

Raw EPUBs and extracted full source should live in ignored local paths:

```text
0. epubs for conversion/
adaptations/<slug>/source_private/
adaptations/<slug>/source_units/
```

The `0.` prefix marks user-managed local intake. Agents may read these folders when the user asks, but should not rename, delete, reorganize, or bulk-edit them.

Do not commit copyrighted source or derivative source units unless rights are explicit.

## Intake

Import an EPUB into stable source units:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/import_epub_for_adaptation.py `
  --epub "0. epubs for conversion/<file>.epub" `
  --slug <slug> `
  --rights-status private_study `
  --copy-source-private
```

The script writes:

```text
adaptations/<slug>/
  source_private/                 # ignored by Git
  source_units/                   # ignored by Git by default
  source_map.json
  adaptation_config.json
  adaptation_plan.md
  proper_noun_candidates.tsv
  stretch_candidates.tsv
```

Source units are roughly 800-1,500 Chinese tokens where possible. They are diagnostic work units, not final chapters.

## Baseline Vocabulary Profile

Profile the source before changing prose:

```powershell
python scripts/profile_adaptation_vocabulary.py `
  --adaptation adaptations/<slug> `
  --known data/known_words.txt `
  --personal-known data/learner_profiles/marcel/personal_known_words.txt `
  --known-character-compounds `
  --known-character-compound-limit 2100 `
  --general-fiction-pack data/stretch_packs/general_fiction_150.txt `
  --journalism-crime-pack data/stretch_packs/journalism_crime_50.txt
```

The report writes:

```text
adaptations/<slug>/vocabulary_profile_baseline.json
adaptations/<slug>/vocabulary_profile_baseline.md
adaptations/<slug>/proper_noun_candidates.tsv
adaptations/<slug>/stretch_candidates.tsv
```

It reports token-weighted coverage, layer counts, top unknown tokens by frequency and dispersion, unknown clusters, sentence-length risks, and a recommended adaptation level per unit.

By default the profiler separates Latin, pinyin, URL, and numeric-only tokens from Chinese vocabulary pressure. Pass `--include-non-hanzi-unknowns` when those tokens should count as source unknowns.

## Candidate Review

Review unknown words in this order:

| Class | Action |
|---|---|
| proper noun | add to `manuscripts/<slug>/proper_nouns.txt` |
| Marcel already knows it | add or confirm in the personal-known profile |
| reusable high-value word | add to a reviewed stretch pack |
| book-only but necessary | add to `manuscripts/<slug>/book_specific_words.txt` |
| replaceable hard word | replace or simplify in adaptation |

Do not add every unknown word as stretch. Stretch is a controlled learning layer, not a landfill.

## Minimal-Intervention Cascade

For every source unit, stop at the lowest level that reaches the readability target:

| Level | Operation |
|---:|---|
| 0 | classify proper nouns, personal-known words, and enabled high-frequency character compounds |
| 1 | approve high-value stretch or book-specific words |
| 2 | replace hard word with known synonym |
| 3 | simplify phrase |
| 4 | split or simplify sentence |
| 5 | rewrite paragraph while preserving source facts |
| 6 | condense or summarize only when required |

No reason, no change. Every change should answer a specific pressure: unknown above threshold, unknown cluster, unavailable idiom, too-long sentence, rare word with an easy known equivalent, or necessary recurring concept promoted to an approved layer.

## Manuscript Integration

Adapted output uses the normal repo manuscript convention:

```text
manuscripts/<adapted-slug>/
  novel_bible.md
  outline.md
  characters.md
  continuity_log.md
  adaptation_log.md
  book_specific_words.txt
  proper_nouns.txt
  stretch_word_exposure.md
  planning/
    chapter_01_vocab_plan.md
  chapters/
    chapter_01.zh-tok.txt
  quality/
    source_fidelity_report.md
```

Each chapter plan must include source units covered, target plot beats, proper nouns, stretch words introduced/repeated, risky unavailable concepts, expected coverage, and allowed adaptation level.

`adaptation_log.md` must record:

- source-unit IDs;
- intervention level used;
- changes made;
- rationale;
- facts preserved;
- facts removed or condensed.

Canonical chapter text remains space-tokenized Chinese.

## Fidelity Review

Before the normal quality gate, create:

```text
manuscripts/<slug>/quality/source_fidelity_report.md
```

It must check:

- major plot beats preserved;
- character motivations preserved;
- scene order and causality preserved;
- important facts not silently removed;
- invented additions not introduced;
- heavy rewrites marked and justified.

For adapted manuscripts, run:

```powershell
python scripts/run_quality_gate.py `
  --manuscript manuscripts/<slug> `
  --known data/known_words.txt `
  --personal-known data/learner_profiles/marcel/personal_known_words.txt `
  --known-character-compounds `
  --known-character-compound-limit 2100 `
  --require-source-fidelity
```

The source fidelity report must say:

```text
Fidelity decision: PASS
```

before `ready_for_epub` can be true in adaptation mode.

## Final Validation And EPUB

After adaptation is in the normal manuscript layout, use the existing validation and EPUB flow. Use the same vocabulary-layer arguments from profiling.

Prefer zero forbidden unknowns for final adapted EPUB candidates. The current repo budget allows up to 5 per chapter, but those unknowns must be intentional, useful, and visible in reports.
