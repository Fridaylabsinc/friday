# 32. Memory Association and Neural Linking

## The Problem with Flat Memory

A naive memory system stores facts independently:
- "Customer X prefers email contact"
- "Customer X had a quality complaint in March"
- "Quality complaints in March were due to supplier S's faulty batch"

These three facts live as separate entries. When an agent asks about Customer X, it surfaces the first two. The connection to Supplier S is lost.

Real cognition links concepts. When you think "Customer X," related concepts (their complaints, the supplier behind those complaints, the product line involved) come along, surfaced by association strength.

This doc designs an association graph that augments Friday's vector memory.

## DocType: Memory Concept

A concept is a noun that anchors memory entries. Examples: a Customer, a Supplier, an Item, a Project, a Skill, an Issue, a Topic, an Event.

Fields:
- `concept_name` (Data) — human-readable name
- `concept_type` (Select: Customer, Supplier, Item, Project, Skill, Issue, Topic, Event, Other)
- `linked_doctype` (Data, optional) — e.g. "Customer" if this concept maps to a Frappe DocType
- `linked_docname` (Data, optional) — e.g. "CUST-001"
- `domain` (Link to Domain) — per doc 29
- `created_from` (Select: Manual, Auto-Extracted, Imported)
- `embedding` (Long Text) — concept's own vector representation
- `aliases` (Small Text) — alternate names

When agents process content, an extraction pass identifies concept mentions and either matches them to existing concepts or creates new ones.

## DocType: Memory Concept Link

The edge in the association graph.

Fields:
- `from_concept` (Link to Memory Concept)
- `to_concept` (Link to Memory Concept)
- `link_type` (Select: Mentioned-With, Caused-By, Resolved-By, Owns, Part-Of, Related-To, Custom)
- `strength` (Float, 0.0 - 1.0) — association strength
- `decay_rate` (Float) — how fast strength decays without reinforcement
- `evidence_count` (Int) — number of memory entries supporting this link
- `last_reinforced_at` (Datetime)
- `domain` (Link to Domain)
- `created_at` (Datetime)

A link from "Customer X" to "Supplier S" with type "Caused-By" represents the chain in the example above.

## DocType: Memory Entry (Extended)

The existing memory entry DocType (created in earlier docs) gets two new fields:
- `mentioned_concepts` (child table of Memory Concept) — concepts referenced in this memory
- `primary_concept` (Link to Memory Concept) — the main subject if any

## Concept Extraction

When a memory entry is created:

1. The entry text is processed by a lightweight extraction pipeline.
2. Named entities (people, organizations, products, places) are identified.
3. Each entity is matched to an existing Memory Concept (by name, alias, or embedding similarity).
4. If no match, a new Memory Concept is created with `created_from = Auto-Extracted`.
5. `mentioned_concepts` is populated.
6. For each pair of mentioned concepts, a Memory Concept Link is created or its strength reinforced.

Extraction implementation: a small LLM call (e.g. Sonnet/Haiku-class) with a focused prompt and JSON output. Skipping spaCy etc. — too brittle for the variety of inputs Friday handles.

## Association Strength Math

Strength `s` evolves with each new evidence:

```
s_new = s_old * exp(-decay_rate * time_elapsed) + reinforcement
```

Where `reinforcement` is typically 0.1 per fresh co-occurrence, capped at 1.0.

`decay_rate` defaults to 0.05/day. A link not reinforced for a month decays from 1.0 to ~0.22.

Links with strength < 0.05 are pruned by a nightly job to keep the graph tractable.

## Memory Retrieval With Association

The `memory_search(query)` skill is extended:

1. Embed the query and find top K matching memory entries (vector search).
2. Identify primary concepts of those memory entries.
3. For each primary concept, walk the association graph up to depth 2 with strength > 0.3.
4. Surface concepts reached this way as "associated context."
5. For each associated concept, optionally retrieve its top memory entries.

Result format:
```json
{
  "direct_matches": [...],
  "associated_concepts": [
    {"concept": "Supplier S", "via": "Customer X", "strength": 0.78, "memories": [...]}
  ]
}
```

The agent sees not just direct hits but the surrounding knowledge web.

## Concept Disambiguation

"John Smith" might be three different people. Friday handles this by:
1. Each concept has a unique ID, never collapsed by name alone.
2. Aliases field holds variations.
3. When extraction sees "John Smith," it pulls all concepts with that name + their evidence, then uses the surrounding context to pick the right one (via small LLM call).
4. If ambiguous, the memory entry is flagged for human review rather than guessed.

## Cross-Domain Associations

Memory Concept Links carry a domain. Cross-domain links (e.g. from `erpnext-procurement.Supplier S` to `erpnext-quality.Issue Q`) require:
- Explicit allow-list in the Domain DocType
- Approval workflow if not in allow-list

This prevents accidental cross-contamination while allowing intentional integration.

## Concept Lifecycle

**Creation:** Auto-extracted from memory entries, or manually created by supervisors.

**Maintenance:** Daily job:
- Decay association strengths
- Prune below-threshold links
- Merge duplicate concepts (e.g. "ACME Co." and "ACME Co" with high concept embedding similarity)
- Flag orphan concepts (no links, no memory entries) for cleanup

**Retirement:** Concepts inactive >180 days move to an archive table. Still queryable but not in default search results.

## DocType Linkage

When a Memory Concept has `linked_doctype` and `linked_docname` set, it's anchored to a real Frappe document. This lets agents:
- Move from memory to ERPNext records seamlessly: "What do you know about Customer X?" pulls the Customer doc AND surrounding memory
- Move from ERPNext records to memory: opening Customer X in ERPNext could display a Friday-rendered sidebar of associated memories (Phase 3 UI feature)

## Visualisation

A "Concept Graph" view (Phase 3) shows the association graph for a chosen concept with:
- Nodes sized by memory count
- Edges weighted by strength
- Color-coded by domain
- Filterable by link type

Useful for supervisors to audit "what does Friday think it knows about Customer X?"

## Use Case Walkthrough

**Scenario:** Agent receives task "Draft a follow-up email to Customer X about their pending order."

1. Memory search on "Customer X pending order"
2. Direct matches:
   - "Customer X ordered 50 units of Item A on March 5"
   - "Customer X had quality complaint about Item A in March"
3. Associated concepts surfaced via graph:
   - "Item A" → linked to "Supplier S" (caused-by, strength 0.78)
   - "Quality complaint" → linked to "Resolution: replacement batch" (resolved-by, strength 0.9)
4. Agent now knows: there was a complaint, it was resolved with a replacement, the original cause was Supplier S.
5. Draft email acknowledges the prior issue and confirms the replacement batch is being shipped.

Without association, the agent might draft a generic follow-up that ignores the complaint history.

## Performance

Storage:
- ~10K memory entries → ~5K concepts → ~50K links typical for an active SMB after a year
- Per concept: ~2KB (with embedding); per link: ~500 bytes
- Total: ~50MB per business — trivial

Query latency:
- Vector search on memory: 50-100ms
- Graph walk (depth 2, strength filter): 20-50ms
- Concept retrieval: <10ms each
- Total: 200-300ms per `memory_search` call. Acceptable.

## Phase 1 Scope

NOT in Phase 1. Phase 1 ships flat memory (vector search only).

## Phase 2 Scope

Phase 2 ships:
- Memory Concept + Memory Concept Link DocTypes
- Concept extraction pipeline
- Basic association walk in `memory_search`
- Manual concept management UI

## Phase 3 Scope

Phase 3 ships:
- Concept Graph visualisation
- ERPNext sidebar integration
- Concept merge/split workflows
- Domain-level association policies

## Open Questions

1. Embedding model for concept embeddings — same as memory entries or separate model? Same in Phase 2; revisit if quality demands specialised embedding.
2. How to handle concepts that should never link (e.g. competitive customer info that must stay isolated)? "Quarantined" flag on concept; links involving it require explicit permission.
3. Graph traversal cost at very high concept counts (>100K)? Likely fine with indexed link table; profile in Phase 2.
