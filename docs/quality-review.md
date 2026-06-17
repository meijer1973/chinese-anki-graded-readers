# Quality Review

Vocabulary validation proves that the text uses known tokens. It does not prove that the book is good.

Every real manuscript needs these artifacts under `manuscripts/<project-slug>/quality/`:

- `vocabulary_usage_report.json`
- `repeated_phrase_report.json`
- `prose_variety_report.json`
- `literary_critic_report.md`
- `normal_reader_report.md`
- `lead_quality_decision.md`

The lead decision is the final manuscript status.

Adapted manuscripts also need:

- `source_fidelity_report.md`

Run `scripts/run_quality_gate.py --require-source-fidelity` for adaptations. The report must contain `Fidelity decision: PASS` before `ready_for_epub` can be true in adaptation mode.

Every new real manuscript should also have `manuscripts/<project-slug>/creative_preflight.md` before chapter vocabulary plans begin. Historical manuscripts may lack this file, but new public-quality work should not.

For planning-heavy manuscripts, `scripts/run_quality_gate.py` also checks that every chapter has `planning/chapter_XX_vocab_plan.md`. Missing planning files are reported in `quality_gate_summary.json` and should block EPUB readiness until fixed.

## Evidence Scripts

Run the whole quality evidence setup:

```powershell
python scripts/run_quality_gate.py --manuscript manuscripts/<slug> --known data/known_words.txt
```

Run reports individually:

```powershell
python scripts/vocabulary_usage_report.py --known data/known_words.txt --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/vocabulary_usage_report.json
python scripts/repeated_phrase_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/repeated_phrase_report.json
python scripts/prose_variety_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/prose_variety_report.json
python scripts/plot_affordance_report.py --known data/known_words.txt --packs data/stretch_packs/general_fiction_100.txt data/stretch_packs/low_fantasy_150.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/journalism_crime_50.txt --required 采访 文章 编辑 来源 嫌犯 作证 动机 --out manuscripts/<slug>/quality/plot_affordance_report.json
```

The reports include token totals, unique-token counts, known-list coverage percentage, chapter-level unique-token counts, unused known words, overused token warnings, and repeated phrase warnings.

Layered validation reports also include core known tokens, personal-known tokens when a learner profile is configured, high-frequency character-compound tokens when enabled, stretch tokens by layer, proper noun tokens, forbidden unknown tokens, forbidden unknowns over the per-chapter budget, known-token percent, the 98% known-token gate, approved non-core/stretch-token percent, the 2% approved non-core gate, stretch words used once, stretch words by chapter, and new stretch words by chapter.

When a manuscript uses Marcel personalized mode, reviewers should treat `personal_known_tokens` and `high_frequency_character_compound_tokens` as low-load known vocabulary for Marcel, not as public-level core vocabulary and not as stretch learning load.

The plot affordance report classifies available words by story function. It helps a planner see whether a premise has enough vocabulary for action, crime, evidence, journalism, setting movement, conflict, fantasy mechanism, and dialogue variety.

The prose variety report checks visible craft risks such as repeated `X 说` frames, repeated sentence openings or endings, repeated phrase frames, and known flat patterns. It is revision evidence, not final literary judgment. A manuscript with style warnings should receive a prose-variety polish pass before public-quality approval.

## Story-First Targets

Token totals, unique-token counts, known-list coverage, and stretch-word exposure are evidence for review. The extensive-reading thresholds are acceptance gates: at least 98% known tokens and at most 2% approved non-core tokens.

- Do not reject a strong chapter because it is short.
- Do not accept a padded chapter because it has more tokens.
- Do not add scenes, city words, stretch words, or repeated explanation merely to improve metrics.
- Top-token dominance, repeated phrases, low coverage, or stretch words used once should trigger review.
- Expansion is allowed only when it fixes a specific story problem.

Padding for length, vocabulary breadth, stretch exposure, or chapter count is a quality failure.

## Review Order

1. Run vocabulary validation and review any unknown tokens, even when they are within budget.
2. For adapted manuscripts, run source fidelity review before normal quality approval.
3. Run continuity review.
4. Run vocabulary usage and repeated phrase reports.
5. Run prose-variety evidence and create a natural reading copy when the manuscript is ready for review:

```powershell
python scripts/build_reading_copy.py --manuscript manuscripts/<slug> --title "<title>" --out manuscripts/<slug>/reading_copy.md
```

6. Literary critic writes `literary_critic_report.md`.
7. Normal reader writes `normal_reader_report.md`.
8. Prose-variety polisher repairs local rhythm issues when needed.
9. Lead reviewer writes `lead_quality_decision.md`.

## Source Fidelity Review

Use this only for EPUB/source adaptations. It checks whether simplification preserved the source rather than merely creating plausible new prose.

`quality/source_fidelity_report.md` must check:

- major plot beats preserved;
- character motivations preserved;
- scene order and causality preserved;
- removed facts listed;
- invented additions listed;
- heavy rewrites justified by vocabulary or readability pressure.

The adapted manuscript is not ready for EPUB in adaptation mode until the report says:

```text
Fidelity decision: PASS
```

## Lead Decisions

Use one of:

- `PASS`
- `POLISH`
- `PARTIAL_REWRITE`
- `COMPLETE_REBUILD`

Recommend baseline `PASS` only if vocabulary validation has no chapter above the configured forbidden-unknown budget, currently 5 tokens, known-token coverage is at least 98%, approved non-core token share is at most 2%, continuity has no serious contradictions, literary critic score is at least 7, normal reader score is at least 7, and no chapter is clearly filler or padded. Unknowns within budget should still be intentional, useful, and not confusing.

Recommend public-quality approval only if literary critic score is at least 8, normal reader score is at least 8, repeated style warnings have been polished or explicitly waived, and the lead reviewer can name why the manuscript is strong within the controlled vocabulary rather than merely acceptable under constraints.

Recommend `POLISH` for local issues in an otherwise usable manuscript.

Recommend `PARTIAL_REWRITE` when some chapters work and several need substantial rewriting.

Recommend `COMPLETE_REBUILD` when the core premise is dull, the book is repetitive, vocabulary use is severely narrow, the normal reader would not continue, or the manuscript feels like a validation exercise rather than a story.

EPUB export is blocked unless `lead_quality_decision.md` explicitly contains:

```text
Final decision: PASS
```

For public series releases, also include:

```text
Public-quality status: PASS
```

## Series Memory Follow-Up

After a series manuscript is accepted, run the post-story memory update before planning the next book. For 林安, use `docs/series-memory.md` and update:

- `series/an-lin/chronology.md`
- `series/an-lin/character_registry.md`
- `series/an-lin/mechanism_registry.md`
- `series/an-lin/open_threads.md`
- `series/an-lin/series_update_log.md`
- `series/an-lin/series_bible.md` or `series/an-lin/sequel_constraints.md` only when stable arc pressure or hard constraints changed

Verify:

```powershell
python scripts/check_series_memory_update.py --manuscript manuscripts/<slug> --series-dir series/an-lin
```

Use `--require-epub-build` when the accepted story should already have an EPUB artifact. This check is a gate for the next series plan, not a replacement for manuscript quality review.

## Stretch-Vocabulary Review

For low-fantasy Shanghai manuscripts, reviewers should also ask:

- Did the genre pack create real fantasy tension?
- Did Shanghai/urban vocabulary make scenes more concrete?
- Are professions and social roles varied, and do they affect plot behavior?
- Are stretch words repeated naturally rather than dumped?
- Does the fantasy stay simple enough for the target level?
- Are locations meaningful, or just namedropped?
- For 林安 journalist/crime manuscripts, did the journalism/crime pack create real reporting pressure?
- Did interviews, sources, files, publication choices, suspects, and witnesses affect the plot?
- Are journalism/crime stretch words repeated enough to become learnable?

The lead reviewer may reject a book when stretch words make it harder but not better, when city/place words are decorative, or when the manuscript remains bland despite broader vocabulary.
