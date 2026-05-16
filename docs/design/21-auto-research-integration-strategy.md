# 21 — Auto-Research Integration Strategy

> **Purpose:** Integrate autonomous research capability into Friday — agents that can investigate topics, synthesise findings, and produce reports without step-by-step human direction. Inspired by autonomous research agent projects in the open ecosystem.

This is a capability layer, not just a skill. Friday agents become **researchers**, not only **executors**.

---

## 1. What Auto-Research Means

An autonomous research agent can:
1. Take an open-ended question or topic
2. Decompose it into sub-questions
3. Gather information from multiple sources (web search, internal documents, knowledge base)
4. Synthesise findings into structured analysis
5. Produce a citable report with sources
6. Iterate if the user requests deeper investigation

This is **distinct** from a chat session that searches. The research agent operates autonomously over minutes to hours, persists intermediate state, and produces a substantive deliverable.

---

## 2. Use Cases for Friday

| Domain | Auto-Research Application |
|---|---|
| Procurement | Research a new supplier — financial stability, reviews, certifications, alternatives |
| Sales | Pre-meeting research on a prospect — company profile, recent news, decision-makers |
| HR | Compensation benchmarking — research market rates, comparable roles |
| Legal | Regulatory landscape research before a new business activity |
| Engineering | Library/framework evaluation — compare options, read changelogs, summarise tradeoffs |
| Strategy | Competitive analysis — gather and synthesise competitor positioning |
| Compliance | Regulatory change tracking — monitor sources, flag changes, summarise impact |

Each is a real workflow currently done by humans in 2–8 hours. Friday should compress this to minutes.

---

## 3. Architecture

### 3.1 Research Project DocType

A research engagement is a first-class object.

| Field | Type | Notes |
|---|---|---|
| `topic` | Long Text | The research question or brief |
| `requested_by` | Link → User | Who asked |
| `assigned_to_profile` | Link → Agent Profile | Research-capable profile |
| `status` | Select | Pending / Decomposing / Researching / Synthesising / Review / Completed |
| `depth` | Select | Shallow (15 min) / Medium (1 hour) / Deep (4+ hours) |
| `max_token_budget` | Int | Cap on total LLM tokens |
| `sources_allowed` | Table | Web / Internal Wiki / ERPNext / Past Research |
| `sub_questions` | Table | Decomposed questions |
| `findings` | Table | Each finding with source citation |
| `final_report` | Link → File (markdown) | Output |
| `parent_task` | Link → Agent Task | If research was kicked off from a task |
| Submittable | Yes |  |

### 3.2 Research Sub-Question DocType

Each sub-question is tracked individually.

| Field | Type |
|---|---|
| `parent_project` | Link → Research Project |
| `question` | Text |
| `status` | Select (Pending / Researching / Answered / Inconclusive) |
| `answer` | Long Text |
| `confidence` | Select (Low / Medium / High) |
| `sources` | Table → Research Source |

### 3.3 Research Source DocType

Citations for traceability.

| Field | Type |
|---|---|
| `url` | URL (nullable) |
| `internal_doctype` | Link (nullable) |
| `internal_name` | Data (nullable) |
| `excerpt` | Long Text |
| `accessed_at` | Datetime |
| `reliability_score` | Float (0..1, learned over time) |

### 3.4 Research Agent Skills

Skills available to a research-capable profile:

| Skill | Purpose |
|---|---|
| `research_decompose(topic)` | Generates sub-questions |
| `web_search(query)` | Searches the web; returns ranked results |
| `web_fetch(url)` | Fetches and parses a page |
| `wiki_query(topic)` | Queries Frappe Wiki / knowledge graph (doc 33) |
| `memory_search(query)` | Searches past Research Projects and findings |
| `research_synthesise(sub_questions)` | Combines answers into structured findings |
| `research_report(findings, format)` | Produces final markdown/PDF deliverable |
| `research_cite(claim, source)` | Adds citation; ensures every claim has at least one source |

---

## 4. Research Loop

```
1. Operator creates Research Project with topic and depth
2. Research Agent picks up the project, status → Decomposing
3. Calls research_decompose → generates 5–15 sub-questions
4. For each sub-question (parallel, capped at concurrency limit):
   a. Determine best source(s) to consult
   b. Use web_search / web_fetch / wiki_query / memory_search
   c. Synthesise an answer with citations
   d. Mark sub-question Answered or Inconclusive
   e. Persist to Research Sub-Question DocType
5. Status → Synthesising
6. Calls research_synthesise → builds a coherent narrative across answers
7. Calls research_report → renders the final markdown
8. Status → Review
9. Requested_by sees the report in War Room with quick-actions:
   [Accept] [Ask Follow-up] [Re-do with focus on X]
10. Final status → Completed
```

**Token budget management:** at each step, the agent compares cumulative tokens used against `max_token_budget`. On 80% used, it switches to "wrap-up mode" and produces a best-effort report even if some sub-questions are unresolved.

---

## 5. Quality Controls

Auto-research is high-leverage but easily produces confident-sounding garbage. Mitigations:

| Risk | Mitigation |
|---|---|
| Hallucinated facts | Every claim in the final report must cite a Research Source row. Skill `research_cite` enforces this. |
| Stale information | Web sources tagged with access timestamp; report flags claims based on sources older than N days |
| Source quality | Reliability score tracked per domain; low-reliability sources flagged in citations |
| Confirmation bias | Decompose step explicitly generates counter-questions ("what would falsify this?") |
| Token waste | Token budget is hard-capped; over-budget research auto-stops and produces partial report |
| Prompt injection from web content | `web_fetch` results sanitised; web text never executed as instructions, only as data |

---

## 6. Integration with Friday Memory

Every completed Research Project persists into long-term memory:
- The final report goes to `Memory Entry` with `kind='research_report'`
- Findings indexed for `memory_search` retrieval
- Future research on related topics surfaces this prior research as input
- Reliability scores update based on whether downstream actions succeeded

Over time, Friday accumulates institutional research knowledge.

---

## 7. War Room Integration

Research Projects appear in War Room as live updates:
- 🔍 Project started
- 📋 Sub-questions decomposed (N total)
- ✓ Sub-questions answered (5 of 12)
- 📊 Synthesising findings
- 📄 Report ready — view in DM or in Desk

Reviewers can comment inline on the report in War Room. Their comments become input for follow-up research projects.

---

## 8. Permission Model

Auto-research agents have powerful capabilities (web fetch, document read). Restrict accordingly:

- Web fetch limited to allowlist by default (configurable per Research Project)
- `wiki_query` respects Wiki page permissions
- `memory_search` returns only memories the agent's role can see
- Research reports inherit permissions of the most restrictive source consulted (high-water mark)
- A Research Project can be marked `confidential` — report visible only to requesting role + supervisor

---

## 9. Permission-Aware Source Tiers

Sources are tiered by trust level:

| Tier | Examples | Permission Required |
|---|---|---|
| Public web | News, blogs, docs | Default for research agents |
| Internal Wiki | Frappe Wiki pages | Wiki Reader role |
| ERPNext data | Customer, Supplier, Item records | Standard ERPNext role |
| Past research | Memory Entries | Memory Reader role |
| External APIs | Crunchbase, LinkedIn (if integrated) | Specific API role |

A research agent can only consult tiers its role permits.

---

## 10. Cost Tracking

Every Research Project tracks:
- LLM tokens used (split by sub-question)
- External API calls (web search, fetch)
- Time spent (start to completion)
- Estimated cost in INR (or configured currency)

This feeds the Cost Tracking system (Phase 2). Operators can set per-project token budgets, see actual cost, and identify which research is worth automating vs. doing manually.

---

## 11. Phasing

| Phase | Auto-Research Capability |
|---|---|
| 1 (MVP) | NOT in Phase 1 — explicit deferral |
| 2 | Basic loop: decompose → web_search → synthesise → report; web sources only |
| 3 | Internal sources (Wiki, ERPNext, memory); follow-up iterations |
| 4 | Adaptive depth, learned reliability scores, cost optimisation |

Phase 1 focus stays on autonomous ERPNext operations. Auto-research is a Phase 2 feature once the core agent runtime is proven.

---

## 12. Dependencies

- `web_search` and `web_fetch` skills (Phase 2)
- Frappe Wiki integration (doc 33)
- Memory module with pgvector (Phase 2 of doc 14)
- Research-capable Agent Role Profile (extends doc 12)
- LLM provider with adequate context window (≥128K) and structured output support

---

## 13. Attribution

The auto-research pattern is widely explored in the open-source community. Friday's implementation is its own, but draws on common patterns: decompose → search → synthesise → cite. No code is copied; the pattern is reimplemented on Frappe primitives.
