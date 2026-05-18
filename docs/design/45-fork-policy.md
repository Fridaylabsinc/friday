# 45 — Fork Policy

> **Purpose:** Define how Friday develops on its Frappe v16 fork — what we freely change in core, what we keep stable, and how we manually absorb upstream Frappe patches when needed.

---

## 1. The Architectural Decision

**Friday is a framework. Under the hood it runs on a hard fork of Frappe v16 stable. Today.**

This is not a conditional decision pending a spike. It is the starting point — but it is intentionally architected to preserve optionality. Frappe is the substrate we leverage now. The agent governance model, contributor model, and Friday's identity are designed to outlive any single substrate.

### Two-Repo Topology

Friday lives across two GitHub repositories:

| Repo | Role | Lifecycle |
|---|---|---|
| `Friday-Labs-Inc/frappe` | Friday's hard fork of Frappe v16 stable. Agent-native core primitives (actor context, trace propagation, audit hooks, agent-scoped auth) are patched directly into this fork. | Independent — we cherry-pick from upstream Frappe selectively per §5. |
| `Friday-Labs-Inc/friday` | Friday's agent kernel app + design docs + governance + contributor policies + scripts. Slice 1 onward, agent kernel modules live here. | Independent — evolves with Friday's roadmap, not Frappe's. |

Both repos are public, GPL v3, and contribute to the same `friday-bench` at runtime — but they are not entangled at the git level.

### Why Two Repos, Not One

Two repos cost slightly more operational glue today but preserve the path to **Friday's own kernel later.** If the community evolves Friday toward an agent-native runtime that doesn't need Frappe as substrate (software 3.0: vector-first storage, ambient UX, dedicated agent runtimes), the agent kernel repo can be ported. With a merged repo, that future requires git surgery on hundreds of MB of Frappe history.

The architectural promise: *Friday's agent governance model is portable. The Frappe substrate is what we use today.*

### What "Friday IS the fork" Means In Practice

- The Friday framework (the `Friday-Labs-Inc/frappe` fork) **is** a hard fork of `frappe/frappe` at the Frappe v16 stable tag.
- Friday's core team develops directly on that fork — agent-native primitives are built into core, not bolted on top.
- The Frappe **bench ecosystem is fully retained**: `bench init`, `bench new-site`, apps, migrations, site operations, and the full Frappe app developer experience all work exactly as they do in upstream Frappe.
- Frappe's runtime substrate is preserved: DocTypes, ORM, permissions, workflows, scheduler, RQ workers, files, realtime, Desk.
- Friday adds agent identity, execution trace, governed skill dispatch, and sandbox execution as **first-class framework primitives** — not as a separate app layer that can be uninstalled. They live in the framework fork, not the kernel app.
- Domain features (Agent Profile DocType, Skill DocType, Execution Log, etc.) live in the `friday` agent kernel app — installable on any site running the Friday framework.
- Upstream Frappe improvements are absorbed **manually** when they are relevant — security patches, critical bug fixes, or improvements the Friday project wants. There is no automatic merge cadence.

Users and developers interact with **Friday**. Frappe is the engine.

### Every Site Is An Agentic Deployment

The two-repo layout would normally require two install steps when provisioning a site:

```bash
bench new-site mybusiness.localhost
bench --site mybusiness.localhost install-app friday
```

That friction is unacceptable for a framework that calls itself "agentic." Friday eliminates it with a bench wrapper:

```bash
bench friday-new-site mybusiness.localhost
```

Internally this runs both commands — provisioning a site and installing the agent kernel app in one step. From the operator's point of view, **every new site is automatically an agentic deployment.** This matches the UX of a single-repo framework while preserving the architectural cleanliness of two repos.

The wrapper is defined as a custom bench command shipped with the agent kernel app. See `CODEX.md` §4 for the implementation specification.

---

## 2. Why a Hard Fork

Agents must be first-class actors in the permission engine, job system, audit layer, and request context. That requires modifying Frappe's core — not wrapping it from outside.

Trying to treat agents as first-class citizens through app/module hooks alone would mean:

- Fragile monkey-patching of framework internals from an app.
- Agent context injected into request cycles through hacks rather than designed interfaces.
- Two competing identities (Frappe user, Friday agent) with no coherent model in the permission engine.
- A "Friday app" that modifies behavior Frappe didn't intend to expose — which is worse than an explicit fork because the surface is undocumented and fragile.

A hard fork is the honest position: Friday **is** a new framework. It starts from proven Frappe engineering and adds the governed-agent layer. The bench ecosystem is retained because it is excellent operational infrastructure. The core is ours.

---

## 3. What We Change in Core

### First-class agent primitives (core modifications, always)

- **Actor context propagation** — agent identity flows through request context, background jobs, and workflows alongside human user context.
- **Trace ID propagation** — a consistent trace ID links: gateway event → permission check → job dispatch → sandbox execution → audit row.
- **Audit hook surface** — framework-level hooks for `Permission Decision Log` and `Execution Log` emission, fired from the permission engine and job system.
- **Agent-scoped API key authentication** — agent profiles authenticate via scoped API keys; the framework's auth layer understands agent vs human actor distinction.
- **Friday shell** — default workspace, CLI entrypoint branding, and control-room navigation registered at the framework level.

### Domain features (Friday apps, not core)

- ERPNext Purchase Order automation
- Raven War Room integration
- pgvector memory and knowledge graph
- Auto-research agents
- Analytical and predictive agents
- Multi-site ACP
- Industry-specific skill templates

The line: **framework identity and cross-cutting execution infrastructure live in core. Domain features live in Friday apps.**

---

## 4. Branch Strategy

```
upstream/v16     ← read-only mirror of frappe/frappe v16 stable tag
upstream/v16-sec ← read-only tracking branch for upstream security releases
friday/main      ← Friday's main development branch (derived from upstream/v16)
friday/release-X.Y
```

`upstream/*` branches exist solely to make manual patch review tractable. Friday development never happens on `upstream/*`.

---

## 5. Upstream Patch Policy

Upstream Frappe patches are absorbed **manually and selectively**. There is no automatic sync.

**This is the protection a hard fork buys us.** Upstream Frappe cannot push to our fork. If Frappe drops Redis, deprecates a feature, restructures their permission engine, or releases v17 with breaking changes — none of that reaches Friday unless we choose to pull it. Our lifecycle is independent.

The price of independence: we own all maintenance of what we kept. We assess every upstream change. We cherry-pick what we want. We refuse what we don't.

| Trigger | Action |
|---|---|
| Upstream security release (CVE) | Maintainer reviews within 48 hours; if Friday is affected, cherry-pick or reimplement the fix into `friday/main` |
| Upstream bug fix we hit | Cherry-pick into `friday/main` when encountered |
| Upstream performance or architectural improvement | Reviewed quarterly; incorporated if it benefits Friday's substrate |
| Upstream feature | Incorporated only if Friday wants it and it doesn't conflict with agent-native architecture |
| Upstream major release (v17+) | Project-level decision: plan migration, stay on current, or skip |

This is intentionally lightweight. The Frappe bench ecosystem moves slowly at the core level. Most upstream activity is in ERPNext and apps, which Friday does not track.

### 5.1 Selective Absorption Workflow

The concrete day-to-day for watching upstream without being controlled by it.

**One-time setup** (on any clone of our fork):

```bash
cd <bench>/apps/frappe   # or wherever our fork lives locally
git remote add upstream https://github.com/frappe/frappe.git
git fetch upstream
```

After this, `origin` points at Friday's fork (we control), `upstream` points at frappe/frappe (read-only for us).

**Weekly / monthly: watch what upstream is doing**

```bash
git fetch upstream
git log upstream/version-16 --oneline --since="2 weeks ago"
```

Read the commit messages. No code is pulled into our fork by this — `git fetch` only updates remote-tracking references locally. Nothing on GitHub changes.

**When a specific upstream commit looks relevant** (CVE fix, bug we hit, improvement we want):

```bash
git checkout friday/main           # work on our branch
git cherry-pick <upstream-sha>     # pull only that commit in
# resolve conflicts if any
bench --site friday.localhost migrate
bench --site friday.localhost run-tests --app friday
# if clean:
git push origin friday/main
```

Tag the cherry-picked commit with `[upstream-absorb: <reason>]` in the message so the divergence registry can track origin.

**When upstream does something we explicitly reject** (e.g. drops Redis, removes a feature Friday depends on):

```bash
# Do nothing. Our fork is unaffected.
# Optionally: open an issue at Friday-Labs-Inc/friday documenting the decision
# so future contributors know we deliberately diverged from this upstream change.
```

**When upstream releases a new minor version** (e.g. v16.1, v16.2):

1. Read their changelog.
2. List the changes that matter to Friday.
3. Cherry-pick each in its own commit, test in isolation.
4. If a change is too entangled to cherry-pick safely, defer or reimplement.

**When upstream releases a new major version** (v17+):

Project-level decision under §5 table. Not a routine task.

### 5.2 What Independence Looks Like In Practice

A concrete scenario, for clarity.

> *Upstream Frappe announces in their v17 plan: "We are dropping Redis. Background jobs will move to a Postgres-backed queue."*

Friday's response:

1. **Read the announcement.** Decide whether Redis matters to Friday's roadmap.
2. **If we keep Redis:** do nothing. Our fork still uses Redis. The upstream v17 commits never reach us. Our v16 fork lives on.
3. **If we follow:** plan it as a major version migration of our own fork. Cherry-pick or rewrite the queue layer. Test heavily. Ship as Friday vX.Y when ready.
4. **The decision is ours, not theirs.**

This is the architectural promise of a hard fork. Anyone evaluating Friday — sponsor, contributor, downstream user — can rely on it.

---

## 6. Divergence Registry

The repo maintains `docs/core-divergences.md` — a living record of every place Friday's fork differs from the Frappe v16 base.

Each entry:

```
## Divergence: <short name>

- **File(s):** path/to/file.py:42-67
- **Date:** YYYY-MM-DD
- **Why:** what agent-native behavior this enables
- **Upstream conflict risk:** Low / Medium / High
- **Tests:** which tests cover this divergence
```

Entries are added when a divergence lands. Reviewed quarterly for candidates to retire (upstream added an equivalent, or the feature was removed).

---

## 7. Patch Discipline

Every core modification:

1. **Tagged in git.** Commit prefix `[friday-core]` with a reference to the divergence registry entry.
2. **Marked in code.** A comment `# friday-core: <name>` on or near the changed lines.
3. **Tested.** A test asserts the Friday-specific behavior; if upstream later changes the surrounding code, the test fails loudly.
4. **Reviewed.** No core modification merges without project owner approval.

---

## 8. What Stays Untouched

These areas of Frappe core are not modified in Friday unless a critical security or correctness reason forces it:

- DocType engine internals
- ORM internals
- Database adapter code
- Setup / install / migration logic
- Frontend Desk JS internals beyond workspace customization

If a Friday feature seems to require touching these, redesign the feature first.

---

## 9. Compatibility Promise

Existing Frappe apps installed on a Friday site should continue to work unless they directly conflict with a Friday core divergence. Friday documents breaking changes to Frappe's public APIs and provides migration guidance per release.

This promise is practical, not absolute. Friday is a new framework. If a Frappe app relies on an internal that Friday needs to change for agent-native reasons, Friday's framework needs win. The promise covers public APIs and expected behavior, not implementation internals.

---

## 10. Naming and Attribution

- The framework is called **Friday** in all user-facing material.
- Documentation and the README acknowledge: "Friday is derived from Frappe Framework (https://github.com/frappe/frappe), distributed under GPL v3."
- The Frappe NOTICE file is preserved and extended in Friday's repo.
- Frappe Technologies and The Commit Company are credited as the upstream authors.

GPL v3 requires this. Good faith requires it too.

---

## 11. Summary

Friday forks Frappe v16 stable and develops the agentic framework directly in core. The bench ecosystem is kept intact. Agent-native primitives — actor context, trace propagation, audit hooks, sandboxed execution — are built into the framework, not bolted on. Upstream Frappe patches are applied manually when Friday needs them. The fork is the starting point, not a last resort.
