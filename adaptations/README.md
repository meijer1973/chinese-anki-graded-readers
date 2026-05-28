# Adaptation Intake Workspace

This namespace is for source-aligned EPUB-to-graded-reader adaptation.

Generated source intake may create:

```text
adaptations/<slug>/source_private/
adaptations/<slug>/source_units/
adaptations/<slug>/source_map.json
adaptations/<slug>/adaptation_config.json
adaptations/<slug>/vocabulary_profile_baseline.json
adaptations/<slug>/proper_noun_candidates.tsv
adaptations/<slug>/stretch_candidates.tsv
```

`source_private/` and `source_units/*_source.md` are ignored by Git by default because they may contain copyrighted source text. Track only analysis/config artifacts unless rights explicitly allow publishing the source.
