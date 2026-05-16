# 18 — Go-to-Market Strategy: India-First, Open-Source Funded

> **Purpose:** Define Friday's go-to-market positioning, target audiences, and sustainability model. Captures the founder's vision: **Made in India, for Indian growing businesses, open-source with revenue flowing back to contributors.**

This is a strategy document, not a business plan. It's the **why** and the **for whom**, not the financial projections.

---

## 1. Mission Statement

> **Friday is an open-source agentic framework, built in India, for the next generation of Indian businesses to automate intelligently — without vendor lock-in, predatory licensing, or compromise on governance.**

The mission has three non-negotiable pieces:
1. **Open-source** (GPL v3 / AGPL v3) — no proprietary trap doors
2. **Made in India** — Indian builders, Indian-hosted infrastructure (FridayLabs), Indian community first
3. **Enterprise governance from day one** — not a hobbyist tool retrofitted for business

---

## 2. Target Audience

### Primary (Phase 1 launch)
- **Indian SMBs and growth-stage startups** using ERPNext (or considering it)
- **System integrators and consultants** serving Indian businesses
- **Indian software developers** building automation for their employers

Why ERPNext users specifically: they already trust open-source enterprise software, they already run Frappe-based stacks, and they have real automation pain (manual data entry, repetitive workflow, supplier coordination). Friday lands on terrain they already understand.

### Secondary (Phase 2–3)
- **Global Frappe community** — same value prop, broader geography
- **Mid-market companies** in any vertical (manufacturing, services, healthcare) where governance matters
- **Internal automation teams** at larger enterprises evaluating open agentic platforms

### Not the target (yet)
- **Hobbyists / personal-automation users** — OpenClaw, Hermes, and Claude Code serve them well
- **AI researchers** — Friday isn't an experimentation platform
- **Pure-LLM applications** (chatbots, content generators) — wrong tool for the job

---

## 3. Positioning vs. Alternatives

| Alternative | What they have | What Friday adds |
|---|---|---|
| Custom in-house automation | Full control | Faster build, governance built-in, community |
| UiPath, Automation Anywhere (RPA) | Enterprise features | Open-source, no per-bot licensing, real LLM agents (not just bots) |
| LangChain, AutoGen, CrewAI | Agent frameworks | Enterprise governance, audit trails, role-based permissions |
| OpenClaw, Hermes Agent | Personal autonomy | Multi-tenant, enterprise-grade, ERPNext-native |
| ChatGPT Enterprise, Anthropic Claude for Work | Polished UX | Self-hosted, no data leaves premise, no per-seat lock-in |
| ERPNext alone | Solid ERP | Agentic layer on top — autonomous workflows, not just records |

**The pitch in one line:** "ERPNext for agents — open-source, enterprise-grade, made in India."

---

## 4. Differentiators

These are not marketing claims; they must be true in code:

1. **Permission-first.** Every skill invocation gated by Frappe's role matrix. Competitors gate at config; Friday gates at runtime.
2. **Audit trail by default.** Every decision is a submittable Frappe DocType. SOC 2-ready out of the box.
3. **Sandbox isolation.** Docker-per-execution with scoped credentials. Compromised skill can't pivot.
4. **Native ERPNext integration.** Project, Task, Issue ported from ERPNext; multi-user agent authentication respects ERPNext role separation (doc 31).
5. **Community-owned.** Friday Labs revenue flows back to contributors. Not a "open-source until we get acquired" play.
6. **No external vector DB.** pgvector inside PostgreSQL. Lower cost, less moving parts, easier audit.
7. **No vendor lock on LLM.** Provider-agnostic; runs against local models if desired.

---

## 5. Phasing

### Phase 1: Build & dogfood (months 1–4)
- Build Phase 1 MVP per doc 06
- Dogfood: use Friday to manage Friday's own development
- Prove ERPNext autonomous ops on a real (or carefully simulated) Indian SMB scenario
- **No marketing.** Don't launch what doesn't work.

### Phase 2: Quiet release (months 5–6)
- Open the repo (doc 17)
- Quiet announcement to the Frappe / ERPNext community first — Frappe forum, ERPNext Discord, Indian dev Twitter
- Invite 10–20 design partners from Indian SMBs to pilot
- Gather feedback aggressively; iterate weekly

### Phase 3: Public launch (months 7–9)
- Show HN, Reddit, broader social
- Document case studies from Phase 2 design partners
- Begin booking demos for FridayLabs hosted (see §7)

### Phase 4: Sustained growth (year 2+)
- FridayLabs revenue starts flowing
- Contributor revenue-share model live (see §8)
- Indian conference circuit: FOSS, ETPL, NASSCOM events
- Targeted partnerships with Indian ERPNext partners and consulting firms

---

## 6. Distribution & Discovery

How Friday reaches its first 1,000 users:

| Channel | Tactic |
|---|---|
| Frappe forum & community | First place to announce; native audience |
| ERPNext partner network | Direct outreach to top 20 Indian ERPNext implementers |
| Indian dev Twitter / LinkedIn | Founder-led content, weekly architecture posts |
| Hacker News | Show HN at v0.1.0; technically substantive post |
| YouTube | Architecture walkthroughs, "Friday managing an ERPNext business" demo videos |
| Conferences | FOSDEM India, PyCon India, Frappe Conference, NASSCOM events |
| Indian tech press | YourStory, Inc42, Entrackr — pitch the "Indian open-source agentic framework" angle |
| GitHub trending | Optimise repo metadata; aim for trending-page exposure on launch day |

**Anti-channel:** paid ads on Google/Facebook/LinkedIn until v1.0. The cost-per-acquisition for OSS is dominated by organic; ads waste budget.

---

## 7. FridayLabs: Hosted Platform

Separate project, separate revenue line. Begins in Phase 4 (year 2+).

### Concept
Managed Friday for businesses who want the value but not the operations. We host. They use.

### Tiers (placeholder pricing)

| Tier | Target | Includes |
|---|---|---|
| **Free Trial** | Anyone | 1 agent, 14 days, capped LLM tokens |
| **Starter** | Solo founders, micro-SMBs | 2 agents, single project, basic skills, INR 5,000–15,000/month |
| **Growth** | Growing SMBs | 10 agents, multiple projects, ERPNext integration, INR 50,000–1,50,000/month |
| **Enterprise** | Mid-market | Unlimited agents, custom integrations, SLA, dedicated support, contact for pricing |
| **Self-Host Support** | Anyone running self-hosted | Friday remains free; support contracts available, INR-priced |

### What FridayLabs owns
- Hosting (servers in Indian regions for data residency)
- Auto-upgrades and security patches
- Usage metering and billing
- Multi-tenancy isolation
- Customer dashboard (manage agents, view metrics, billing)
- L1 support

### What FridayLabs does **not** own
- The open-source code (still GPL v3, in the public repo)
- Customer data (encrypted, customer-controlled key)
- Lock-in mechanisms (one-click export to self-hosted at any time)

This is the **"open-core done right"** structure: the platform is free, the convenience is paid.

---

## 8. Contributor Revenue Share

The novel piece. FridayLabs revenue, after covering operational costs, flows back to community contributors based on contribution metrics.

### Metric Sources
- Merged PRs (weighted by code size, complexity, criticality)
- Skill contributions (weighted by usage across FridayLabs tenants)
- Documentation contributions
- Issue triage and community support (measurable via GitHub activity)
- Security disclosures

### Distribution Model (placeholder, to be ratified by community)
- **40%** of net revenue retained for FridayLabs operations and reserves
- **30%** to core maintainers (split by contribution score)
- **20%** to broader contributor pool (split by contribution score)
- **10%** to a community fund for grants, events, and outreach

### Why This Matters
Most "open-source startups" extract value from contributors and monetise it privately. Friday inverts this: contributors who build skills, integrations, and improvements receive a share of revenue their work generates.

This makes contributing economically rational, not just altruistic. Especially relevant for Indian developers — even a modest revenue share is meaningful at INR purchasing power.

### Governance
- Revenue and distribution are reported publicly (annual transparency report)
- Contributor scores are public and auditable
- A community-elected committee reviews and adjusts the formula yearly

---

## 9. What Success Looks Like

### Year 1 (Launch + initial growth)
- 1,000 GitHub stars
- 50 production deployments (mostly self-hosted)
- 20 active contributors
- 3 written case studies of Indian businesses using Friday

### Year 2 (FridayLabs launch)
- 10,000 GitHub stars
- 500 self-hosted deployments
- 50 FridayLabs paying customers
- 100 active contributors
- First contributor revenue distribution

### Year 3 (Sustained growth)
- Friday is the default agentic framework for Indian Frappe/ERPNext deployments
- FridayLabs revenue covers full operations and meaningful contributor share
- Recognised by NASSCOM, the broader Indian open-source community, and the Frappe project itself
- One conference dedicated to Friday (Friday Conf India)

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Anthropic / OpenAI release competing enterprise agent platforms | Lean into open-source, self-hosting, data sovereignty — they can't match those |
| Frappe core absorbs agentic features, Friday becomes redundant | Become so good and so embedded that Friday is what they'd absorb; collaborate, don't compete |
| Community contributions don't materialise | Founder + small core team must produce 80% of value for first year; revenue-share kicks in to attract contributors |
| FridayLabs operational complexity sinks the team | Don't launch FridayLabs until Phase 1 product is rock-solid; small early-customer beta first |
| Indian SMBs don't adopt agentic automation fast enough | Lead with concrete ROI on a single workflow (e.g. ERPNext PO automation) — not "platform" pitches |
| Founder bandwidth | Document everything (this is one of 39 design docs); build for handoff from day one |

---

## 11. The North Star

Every decision passes this test:

> **Does this decision make Friday more useful for an Indian SMB founder running their business on ERPNext, who wants automation without losing control or paying through the nose?**

If yes → ship it. If no → drop it.

This filter is opinionated on purpose. Optimising for everyone optimises for no one.
