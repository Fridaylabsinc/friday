# 26. Dynamic Framework Version Management

## Problem Statement

Friday agents work across many frameworks (Frappe v15, Frappe v16, ERPNext v15, Next.js 14/15, React 18/19, PostgreSQL 14/15/16, Kubernetes 1.28+, etc.). Each framework version has different APIs, deprecated patterns, new features, and different best practices.

A naive agent that knows "React" gives generic answers — sometimes correct for v17, sometimes for v18, sometimes for v19. Production code breaks.

We need agents that always know **which exact framework version this project uses** and can pull skills/documentation matched to that version.

## Design Goals

1. Every Agent Project records the exact framework versions in play.
2. Skills are versioned per framework version. A skill for "Frappe DocType creation" exists separately for v15 and v16.
3. The dispatcher selects the right skill version automatically based on the project's framework version.
4. Documentation snapshots are stored locally so agents work offline and don't hallucinate against stale memory.
5. Documentation auto-updates when upstream releases happen (see doc 28).

## DocType: Framework Version

A new DocType `Framework Version` records each (framework, version) pair we support.

Fields:
- `framework_name` (Link to Framework DocType) — e.g. "Frappe", "React", "PostgreSQL"
- `version` (Data) — e.g. "v15.42.0", "18.2.0", "16.1"
- `release_date` (Date)
- `is_lts` (Check) — is this a long-term-support release?
- `status` (Select: Active, Deprecated, EOL)
- `doc_url` (Data) — canonical documentation URL
- `release_notes_url` (Data)
- `github_release_url` (Data) — used by doc 28 sync job
- `latest_known_release` (Check) — only one version per framework is "latest known"
- `breaking_changes_from_previous` (Long Text)

## DocType: Framework

The parent DocType holds the framework identity itself.

Fields:
- `framework_name` (Data, unique)
- `category` (Select: Backend, Frontend, Database, Infra, DevOps, ML, Other)
- `homepage_url` (Data)
- `github_repo` (Data)
- `default_version` (Link to Framework Version) — used when project doesn't specify
- `tracked` (Check) — whether Friday actively syncs docs for this framework

## DocType: Agent Project — New Fields

Extend Agent Project with a child table `project_framework_versions`:
- `framework` (Link to Framework)
- `version` (Link to Framework Version)
- `notes` (Small Text) — e.g. "production runs v15.40 but staging runs v15.42"

When the project is created, the supervisor (or System Manager Agent) fills this child table. Friday can also auto-detect for some frameworks: read `package.json` for Node, `requirements.txt` for Python, `frappe --version` for Frappe sites, etc.

## DocType: Skill — Version Fields

Extend the Skill DocType with:
- `applicable_frameworks` (child table of Framework Version)
- `min_version` (Data) — optional semver-style floor
- `max_version` (Data) — optional ceiling
- `version_specific_notes` (Long Text)

A single skill record can apply to multiple framework versions if behavior is identical. Where behavior differs, separate skill records are created (e.g. "Frappe DocType Save v15" vs "Frappe DocType Save v16").

## Skill Resolution Logic

When the dispatcher matches a task to skills:

1. Read the Agent Project's `project_framework_versions`.
2. Filter skills whose `applicable_frameworks` includes any matching (framework, version) pair OR whose `min_version`/`max_version` window contains the project's version.
3. Rank by version specificity: exact match > range match > generic skill (no framework specified).
4. If multiple skills match equally, pick the most recent `last_used` or highest `success_rate`.

This logic is implemented in `friday.dispatcher.resolve_skills_for_task(project, task)` and is unit-tested with fixture projects across versions.

## Documentation Snapshot Storage

For each tracked Framework Version, Friday stores a local snapshot of its documentation:

- Path: `friday/framework_docs/{framework_name}/{version}/`
- Format: Markdown files indexed by topic
- Optionally: full HTML mirror for fidelity
- Embedding store: each doc chunk goes into pgvector with `framework_version_id` as a metadata filter

Snapshots are fetched by a scheduled job (see doc 28). Initial seed is manual: maintainers download and commit the snapshot for each framework version on initial support.

## Skill `framework_doc_lookup`

A new built-in skill `framework_doc_lookup(query, framework=None, version=None)`:

1. Resolves framework + version from project context if not supplied.
2. Embeds the query and runs a pgvector similarity search filtered by `framework_version_id`.
3. Returns top N chunks with citations.

Agents call this skill **before** generating code, ensuring grounded responses. If no results above threshold, the agent returns "documentation not found in snapshot, escalating for human verification" rather than hallucinating.

## Version Upgrade Workflows

When a project decides to upgrade (e.g. Frappe v15 → v16):

1. Supervisor opens an "Agent Project Framework Upgrade" workflow.
2. Friday's Migration Specialist agent (a specialised profile) reads `breaking_changes_from_previous` for the new version.
3. Generates an upgrade plan as Agent Tasks.
4. Each task references skills filtered to the new version.
5. Plan goes to War Room for human approval before execution.

This makes framework upgrades a first-class operation, not a last-minute scramble.

## Multi-Version Coexistence

Some projects run mixed versions (e.g. legacy app on Frappe v14, new app on v15). The project_framework_versions child table supports multiple rows. Agents working on tasks within that project must specify which sub-project / app they're acting on, and the dispatcher resolves skills accordingly.

If ambiguity remains, the dispatcher asks (via War Room) which version applies before proceeding.

## Cleanup and Deprecation

When a Framework Version is marked EOL:

1. All associated skills get a banner: "Skill applies to EOL framework version; consider upgrading."
2. Projects still using that version get a War Room notice once per week.
3. Skills are not deleted — they remain available for legacy support but are deprioritised in ranking.

## Phase 1 Scope

Phase 1 ships:
- Framework + Framework Version DocTypes
- Project framework versions child table
- Skill version fields (applicable_frameworks)
- `framework_doc_lookup` skill (with pgvector search)
- Manual seed of snapshots for: Frappe v15, ERPNext v15, PostgreSQL 15

Phase 2 adds:
- Automated sync (doc 28)
- Migration Specialist profile
- Snapshot rotation and storage limits

## Open Questions / Engineering TODOs

1. Storage budget per framework snapshot? Cap at 500MB initially.
2. How to detect framework version automatically across many project types — separate detection rules per framework, registered as small Python plugins.
3. What happens when documentation URL structure changes between versions (Frappe wiki vs docs.frappe.io)? Sync job needs per-framework adapter (doc 28).
4. Do we expose the framework version list as a public API for community contribution of new framework support? Likely yes in Phase 3.
