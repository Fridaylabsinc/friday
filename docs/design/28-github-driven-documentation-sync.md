# 28. GitHub-Driven Documentation Sync

## Goal

Keep Friday's local framework documentation snapshots and skill knowledge bundles current automatically. When upstream projects (Frappe, React, Kubernetes, Postgres, etc.) cut a new release on GitHub, a Friday scheduled job detects it, fetches the new docs, and updates the relevant Framework Version + embedding store.

## Why Not Just Search the Web?

Web-search-as-you-go has three problems:

1. **Latency:** every code-writing task triggers a search, blowing up response time.
2. **Hallucination risk:** scraped fragments out of context lead to wrong answers.
3. **Version mismatch:** generic search returns the most-popular-on-Stack-Overflow version, not the project's actual version.

Local snapshots scoped to the project's exact framework version (doc 26) solve all three. The remaining problem is keeping snapshots fresh — which is what this doc handles.

## DocType: Documentation Source

A new DocType `Documentation Source` registers each upstream we monitor.

Fields:
- `framework` (Link to Framework)
- `source_type` (Select: GitHub Release, Git Tag, ReadTheDocs, Custom Webhook, Manual)
- `github_repo` (Data) — e.g. "frappe/frappe"
- `github_release_url` (Data) — API endpoint we poll
- `docs_url_pattern` (Data) — template like "https://docs.frappe.io/framework/{version}/"
- `tarball_url_pattern` (Data) — for fetching the docs subtree
- `adapter_module` (Data) — Python module path for source-specific parsing
- `last_synced_at` (Datetime)
- `last_synced_version` (Data)
- `sync_status` (Select: Idle, Running, Failed)
- `sync_error_log` (Long Text)
- `enabled` (Check)

## Scheduled Job: `friday.sync.check_doc_sources`

Runs hourly via Frappe Scheduler.

For each enabled Documentation Source:
1. Hit the GitHub Releases API (or equivalent).
2. Compare `latest_release.tag_name` to `last_synced_version`.
3. If different, enqueue `friday.sync.fetch_documentation` for that source.

Rate limiting: GitHub allows 5000 authenticated requests/hour. With < 100 sources polled hourly, we're well within budget. We use a single Friday-controlled GitHub token stored in the Credential Profile DocType (doc 23).

## Background Job: `friday.sync.fetch_documentation`

For a given Documentation Source and target version:

1. Resolve the docs URL or tarball.
2. Download to a temp directory.
3. Run the source-specific adapter to extract markdown/HTML.
4. Chunk content (typically 1000-2000 tokens per chunk, with paragraph boundary preservation).
5. Embed each chunk via the configured embedding model.
6. Insert chunks into pgvector with metadata: `framework_id`, `framework_version_id`, `topic`, `source_url`, `chunk_index`.
7. Atomically swap: write new chunks to a staging schema, then `BEGIN; DELETE old; INSERT new; COMMIT;`.
8. Update `Framework Version` record: status, release_date, doc_url, latest_known_release flags.
9. Create a Skill Sync Notice (see below) listing skills that may need review against new version.
10. Post a War Room notification to a dedicated `#framework-updates` channel.

## Source-Specific Adapters

Each upstream has its own structure, so we have small adapter modules:

- `friday.sync.adapters.frappe_framework` — knows Frappe's docs site structure
- `friday.sync.adapters.erpnext` — ERPNext docs structure
- `friday.sync.adapters.kubernetes` — Kubernetes website docs repo
- `friday.sync.adapters.react` — React.dev docs repo
- `friday.sync.adapters.postgresql` — PostgreSQL official docs (SGML)
- `friday.sync.adapters.generic_mkdocs` — for any project using MkDocs
- `friday.sync.adapters.generic_sphinx` — for any project using Sphinx
- `friday.sync.adapters.deepwiki` — for fetching DeepWiki representations

Each adapter implements:
```python
class DocsAdapter:
    def fetch(self, source: DocumentationSource, version: str) -> Path: ...
    def parse(self, raw_path: Path) -> Iterator[DocChunk]: ...
```

Community contributors can add adapters for new frameworks via PR.

## Skill Sync Notice

When a new framework version is synced, any Skill records with `applicable_frameworks` covering the prior version automatically get a Skill Sync Notice:

- Type: Information
- Action required: maintainer reviews whether skill behavior changed between versions
- Outcome:
  - **No change** → mark notice resolved, extend `applicable_frameworks` to include new version
  - **Behavior changed** → create a new Skill record for the new version; old skill remains scoped to prior versions

This is human-mediated in Phase 1. In Phase 2 we explore automated behavioral testing of skills against the new version.

## DeepWiki Integration

DeepWiki (`https://deepwiki.com/{owner}/{repo}`) provides AI-friendly summaries of GitHub repos. For frameworks whose official docs are sparse but whose source code is canonical (e.g. small libraries), the DeepWiki adapter is the primary source.

The adapter fetches the DeepWiki representation as a single document, chunks it, and embeds it. This is especially useful for less-documented internals (e.g. Frappe internals beyond the user-facing docs).

## ReadTheDocs Webhook

For projects hosted on ReadTheDocs that support outgoing webhooks, we register a Friday endpoint:

`POST /api/method/friday.sync.readthedocs_webhook?token=...`

This pushes updates within seconds of upstream publication, removing reliance on polling.

## Manual Refresh Trigger

A button on the Documentation Source form: "Refresh now". This enqueues `fetch_documentation` immediately, bypassing the schedule.

Useful when:
- Maintainer wants to test a new adapter
- Upstream pushed a critical patch and we don't want to wait
- A new framework was just added and we want to seed it

## Storage and Retention

Per Framework Version:
- Raw fetched docs: kept for 30 days, then purged (re-fetchable from upstream)
- Embeddings in pgvector: kept indefinitely until version reaches EOL + 1 year
- Chunk source URLs: always kept for citation

Total storage estimate: 50 frameworks × 5 active versions × ~200MB embeddings each ≈ 50GB. Reasonable for a single PostgreSQL instance.

## Failure Handling

If a sync fails:
1. Mark `sync_status = Failed`
2. Write detailed error to `sync_error_log`
3. Post a Raven message to `#framework-updates`
4. Do NOT delete or modify the prior snapshot — fallback to last good

Sync failures don't block agents: they continue using the last-good snapshot with a stale-warning banner visible in War Room.

## Security Considerations

1. Doc sources are fetched from public URLs only — no private repo access by default. Private repos require an explicit token and supervisor approval.
2. Fetched content is treated as untrusted: parsing happens in a sandboxed worker (doc 24).
3. We validate that fetched content is plausibly documentation (markdown, restructured text, HTML with text content) before storing — prevents fetching arbitrary binaries.
4. The GitHub token is least-privilege: read-only, public-repos-only by default.

## Phase 1 Scope

Phase 1 ships:
- Documentation Source DocType
- Hourly scheduled job
- Adapters for Frappe and ERPNext only
- Manual refresh button
- pgvector storage with version metadata

Phase 2 adds:
- React, Kubernetes, PostgreSQL adapters
- DeepWiki adapter
- ReadTheDocs webhook
- Skill Sync Notice workflow

Phase 3 adds:
- Community-contributed adapters via plugin registry
- Automated behavioral skill testing against new versions
- Differential analysis: "Frappe v15 → v16, here are the API changes that affect your project"

## Open Questions

1. How to handle docs for closed-source upstreams (e.g. AWS service docs)? Adapter scrapes their public docs; legality reviewed before shipping.
2. Per-framework storage budget when a major project has huge docs (e.g. PostgreSQL is ~10MB of SGML)? Cap at 1GB per framework version; truncate or sub-select if exceeded.
3. Multi-language docs (e.g. Frappe has English + others)? Phase 1 English only; later add language metadata to chunks.
