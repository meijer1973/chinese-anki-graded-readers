# Machine-Readable Repository Surface

This repository follows the same broad pattern used in `meijer1973/4veco-platform`: a GitHub-facing entry file, a research-agent map, a research prompt, a machine manifest, and generated URL/file indexes.

## Files

- `AGENT_GITHUB_ENTRY.md`: quick orientation for agents landing on GitHub.
- `RESEARCH_AGENT_MAP.md`: exact path and raw URL traversal rules.
- `RESEARCH_AGENT_PROMPT.md`: reusable prompt for remote research agents.
- `repo_manifest.json`: machine-readable manifest of entry points, namespaces, commands, and generated/local surfaces.
- `data/external_agent_vocab/`: generated compact vocabulary bundle for external Marcel-personalized writer agents.
- `reports/url-index.md`: full raw URLs for agents that cannot construct URLs.
- `reports/github-agent-index.md`: tracked file inventory grouped by repository surface.

## Refresh

Run:

```powershell
python scripts/build_agent_index.py
```

Refresh these files when paths, scripts, workflows, skills, agents, reports, or manuscript conventions change:

- `RESEARCH_AGENT_MAP.md`
- `AGENT_GITHUB_ENTRY.md`
- `repo_manifest.json`
- `reports/url-index.md`
- `reports/github-agent-index.md`

## Rules For Agents

- Use exact paths from the map or manifest before searching.
- Treat `chapters/*.zh-tok.txt` as canonical story text.
- Treat EPUBs, TSV exports, backups, and local downloads as generated or local artifacts.
- Treat `0.`-prefixed folders as user-managed local intake. Agents may read them when asked, but should not reorganize or bulk-edit them.
- Treat `adaptations/*/source_private/` and `adaptations/*/source_units/` as private/local unless rights explicitly allow publishing.
- Confirm file existence with `reports/github-agent-index.md`.
- Use `reports/url-index.md` as a single-fetch entry point when raw URL construction is unavailable.
- Commit and push accepted tracked work to `origin` before calling it done, unless the user explicitly asks not to or Git/validation blocks publication.
