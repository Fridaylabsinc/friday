# 33. Knowledge Graph & Wiki Integration

## Vision

Friday agents don't just store memories — they build structured, human-readable knowledge bases. The Frappe Wiki app becomes Friday's collaborative knowledge layer, where agents and humans together curate domain knowledge that survives across agent versions and team changes.

## Why Frappe Wiki

Frappe Wiki is an existing, mature open-source app from the Frappe ecosystem:
- Hierarchical pages with markdown
- Versioning and rollback
- Comments and discussion
- Permissions tied to Frappe roles
- Already integrated with Frappe's auth, audit, and search

We don't reinvent — we extend.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Friday Knowledge Graph (semantic layer)                 │
│   - Memory Concepts (doc 32)                            │
│   - Memory Concept Links                                │
│   - Memory Entries (vector store)                       │
└────────────┬────────────────────────────────────────────┘
             │ surfaces / curates / links to
┌────────────▼────────────────────────────────────────────┐
│ Frappe Wiki (human-readable layer)                      │
│   - Domain pages: /erpnext-procurement, /infra-k8s      │
│   - Process pages: "How we handle late deliveries"      │
│   - Reference pages: "Supplier S onboarding history"    │
│   - Decision logs: "Why we chose vendor X"              │
└─────────────────────────────────────────────────────────┘
```

The wiki is the human-readable, narrative layer. The knowledge graph is the structured, agent-queryable layer. They link to each other.

## DocType: Wiki Page Friday Metadata

A child table or related DocType on Wiki Page that adds:
- `friday_indexed` (Check) — whether Friday has indexed this page
- `last_indexed_at` (Datetime)
- `linked_concepts` (child table of Memory Concept)
- `domain` (Link to Domain)
- `agent_can_edit` (Check) — whether agents can propose edits
- `agent_edit_requires_approval` (Check)

## Wiki Sync Pipeline

A scheduled job `friday.wiki.sync_pages` runs every 15 minutes:

1. Query Wiki Pages modified since `last_indexed_at`.
2. For each page:
   - Extract text content (strip markdown formatting).
   - Chunk to ~1000-token windows with overlap.
   - Embed each chunk via configured embedding model.
   - Insert chunks into pgvector with metadata: `wiki_page_id`, `domain`, `linked_concepts`.
   - Run concept extraction (doc 32) on the full page → update `linked_concepts`.
3. Update `last_indexed_at` on each page.

## Agent Wiki Query

A new skill `wiki_search(query, domain=None)`:

1. Embed query.
2. Run pgvector similarity search filtered by `domain` if specified.
3. Return top N matching chunks with: wiki page title, chunk text, page URL, last-modified date.

This sits alongside `memory_search` (doc 32). Memory search returns episodic memories; wiki search returns curated knowledge.

## Agent-Authored Wiki Edits

Agents can propose wiki edits. Two modes:

### Mode 1: New Page Creation
Agent identifies a knowledge gap (e.g. "no wiki page describes our customs clearance process"). Skill `wiki_propose_new_page(title, domain, content_draft)`:
1. Creates a draft Wiki Page with status `Pending Review`.
2. Author = the calling agent's Frappe user.
3. Posts a Raven message in the domain's War Room.
4. Domain supervisor reviews and either approves (publishes) or rejects with feedback.
5. If approved, the page goes live with a footer note: "Drafted by Friday agent {X} on {date}, approved by {supervisor}."

### Mode 2: Existing Page Edit
Agent finds outdated content during a task. Skill `wiki_propose_edit(page_id, change_summary, new_content)`:
1. Creates a Wiki Page Revision (using Wiki's built-in versioning) in `Pending Review` state.
2. Posts a diff to Raven.
3. Supervisor approves or rejects.
4. On approval, the revision is published; on rejection, it's archived with reason.

In Phase 1, agent wiki authoring is disabled by default — only humans write wiki content. Phase 2 enables it with the approval gates above.

## Concept Anchoring to Wiki Pages

Every Memory Concept (doc 32) can have a `canonical_wiki_page` link. This means:
- The wiki page for Customer X is "the" reference on Customer X.
- Memory entries about Customer X surface this page in their context.
- Updates to the wiki page invalidate downstream caches.

This creates a clear hierarchy:
- **Wiki page** = authoritative, curated, narrative
- **Memory entries** = raw observations, episodic
- **Concept** = the bridge

## Auto-Generated Wiki Stubs

When a Memory Concept reaches a maturity threshold (e.g. 20+ memory entries, multiple link types) but lacks a canonical wiki page, Friday proposes a stub:

1. Agent or curator detects threshold cross.
2. Composes a stub page summarising what memory says about the concept.
3. Submits as a `Pending Review` wiki page.
4. Supervisor accepts (publishes), modifies, or rejects.

This bootstraps the wiki from accumulated memory rather than expecting humans to write everything from scratch.

## Cross-Linking Within Wiki

Wiki pages can use `[[Concept Name]]` syntax to link to other pages by concept. When Friday renders or indexes:
1. Each `[[X]]` is resolved to a concept lookup.
2. If concept exists → link to its canonical wiki page (or back-fill if missing).
3. If concept doesn't exist → create a stub Memory Concept (no wiki page yet).
4. Link is recorded in Memory Concept Link table with type "References-In-Wiki."

Over time the wiki becomes a deeply connected graph of pages, mirroring the concept graph.

## Permissions

Wiki pages inherit Frappe role permissions. Friday additionally checks domain alignment:
- An `erpnext-procurement` agent reads pages in its domain freely.
- It reads pages in other domains only if `cross_domain_read = True` in its profile.
- It edits only pages tagged with its domain.

Supervisors override these for special cases via the standard Frappe permission system.

## Search Unification

A unified `friday_search(query)` skill combines:
- Memory entries (vector match)
- Wiki pages (vector match)
- ERPNext documents (Frappe full-text search)
- Skill library (skill descriptions)

Returns ranked results across all four sources with type tags. Agents can request specific source filters when needed.

This is the agent's "ask anything" interface.

## Wiki as Onboarding Material

When a new agent profile is created, its training context includes:
1. The domain's root wiki page (a curated index)
2. The top 10 most-linked pages in that domain
3. Recent decision log entries

This way new agents inherit organizational knowledge, not just raw skills.

## Wiki for Human Supervisors

Supervisors use the wiki to:
- Document operational policies that agents must respect
- Record decisions and their rationale (decision logs)
- Write postmortems for incidents
- Maintain runbooks

Friday's agents read this content as authoritative guidance.

## Decision Log Pattern

A specific wiki structure: `/decisions/{YYYY-MM-DD}-{slug}.md`

Each decision log records:
- Context: what situation prompted this decision
- Options considered: what alternatives existed
- Decision: what was chosen
- Rationale: why
- Date and stakeholders

Agents read these when facing similar situations and respect the documented rationale.

A skill `decision_log_search(situation_description)` returns relevant past decisions.

## Phase 1 Scope

Phase 1 ships:
- Wiki app installed
- Manual wiki authoring (humans write)
- `wiki_search` skill with pgvector indexing
- Wiki Page Friday Metadata DocType
- Sync pipeline (15-min schedule)

Phase 2 adds:
- Agent-authored wiki edits with approval gates
- Concept anchoring to wiki pages
- Auto-generated stubs

Phase 3 adds:
- Unified `friday_search` across all sources
- Decision log pattern + skill
- Cross-linking with `[[concept]]` syntax

## Open Questions

1. Wiki page count at scale — performance of full-text + vector search on 10K+ pages? Standard PostgreSQL + pgvector handles this; profile in Phase 2.
2. Multi-language wiki content — Frappe Wiki has basic i18n; how do agents handle bilingual pages? Phase 3 adds language metadata to chunks.
3. External wiki migration (Confluence, Notion, GitBook)? Adapters per source; not a Phase 1 priority.
