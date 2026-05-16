# 17 — Open Source Launch Playbook

> **Purpose:** Step-by-step plan to take Friday from a private Phase 1 prototype to a healthy open-source project with active contributors. Covers repo setup, release engineering, community process, and the launch sequence.

This document assumes the Phase 1 MVP (per doc 06) is complete and dogfooded internally.

---

## 1. Pre-Launch Checklist

Before flipping the repo from private to public:

### Code Quality
- [ ] All Phase 1 tests passing on CI
- [ ] Test coverage ≥ 70% overall, ≥ 85% on permissions, gateway, isolation, dispatcher
- [ ] Pre-commit hooks pass on `--all-files`
- [ ] No `TODO: security` comments left in code
- [ ] No hard-coded credentials, tokens, or site names anywhere
- [ ] `bench migrate` runs clean from empty site to current state

### Repository Hygiene
- [ ] `LICENSE` file present (GPL v3 full text, unmodified)
- [ ] `README.md` — concise overview, 60-second install, link to docs
- [ ] `CONTRIBUTING.md` — DCO, code style, PR process, how to claim issues
- [ ] `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
- [ ] `SECURITY.md` — vulnerability reporting, response timeline
- [ ] `NOTICE` — attribution for Hermes, OpenClaw, Raven, Frappe references
- [ ] `CHANGELOG.md` — Keep-a-Changelog format, starts at v0.1.0
- [ ] `.github/ISSUE_TEMPLATE/` — bug, feature, security, question
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `.github/workflows/` — CI for tests, lint, build

### Documentation
- [ ] `docs/install.md` — full prerequisites and step-by-step setup
- [ ] `docs/quickstart.md` — first agent + skill in 10 minutes
- [ ] `docs/architecture.md` — high-level diagram + links to the seven specs (01–07)
- [ ] `docs/skills.md` — how to author a Skill
- [ ] `docs/security.md` — threat model, deployment hardening checklist
- [ ] `docs/faq.md` — anticipated questions
- [ ] All 39 internal design docs (00–38) committed to `docs/design/`

### Brand & Legal
- [ ] Project name confirmed: **Friday**
- [ ] Tagline: "An agentic framework powered by Frappe"
- [ ] Naming: avoid "Frappe Friday" or "Friday by Frappe" (trademark concerns)
- [ ] Logo (simple wordmark sufficient for v0.1.0)
- [ ] GitHub repo description and topics set
- [ ] Domain registered (`friday.dev` or `fridayagent.io` or fallback)

---

## 2. Repository Setup

### Layout

```
friday/                              ← Frappe app root, public repo
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── NOTICE
├── CHANGELOG.md
├── pyproject.toml
├── .pre-commit-config.yaml
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── test.yml
│       ├── lint.yml
│       └── docs-publish.yml
├── docs/
│   ├── install.md
│   ├── quickstart.md
│   ├── architecture.md
│   ├── skills.md
│   ├── security.md
│   ├── faq.md
│   └── design/                      ← all 39 internal design docs
├── friday/                          ← Python package
│   ├── gateway/
│   ├── agents/
│   ├── skills/
│   ├── tasks/
│   ├── messaging/
│   ├── permissions/
│   ├── memory/
│   └── api/
└── tests/
```

### Branch Strategy
- `main` — always green, releasable
- `develop` — integration branch for active work (optional; can omit if `main` works)
- Feature branches: `feat/{slug}`, `fix/{slug}`, `docs/{slug}`
- Release tags: semantic versioning, `v0.1.0` for first public release

### CI Workflows
- `test.yml`: matrix of Python 3.11 / 3.12, PostgreSQL 15, Redis 7 — runs full pytest suite + `bench migrate`
- `lint.yml`: black, ruff, mypy on critical modules
- `docs-publish.yml`: publishes docs to GitHub Pages (or Cloudflare Pages) on `main` push

---

## 3. Release Engineering

### Versioning
Semantic versioning. v0.x.y signals "early, breaking changes possible".

| Version | Milestone |
|---|---|
| v0.1.0 | First public release — Phase 1 MVP |
| v0.2.0 | Raven integration + Multi-Platform adapters |
| v0.3.0 | Memory module with pgvector |
| v0.4.0 | Learning loop + autonomous curator |
| v0.5.0 | Multi-site agent-to-agent (doc 37) |
| v1.0.0 | Production-ready, API-stable, ERPNext autonomous ops case study complete |

### Release Cadence
- Patch releases (x.y.Z): as needed for bugs and security
- Minor releases (x.Y.0): monthly during active development, then quarterly
- Major releases (X.0.0): only with breaking changes, advance notice

### Release Process
1. Create release branch `release/vX.Y.Z`
2. Bump version in `pyproject.toml`
3. Update `CHANGELOG.md`
4. Run full test suite + manual smoke test
5. Tag `vX.Y.Z`, push tag
6. GitHub Actions builds and publishes to PyPI (and Frappe Cloud app marketplace if applicable)
7. Publish GitHub Release with changelog excerpt
8. Announce in relevant channels (§6)

---

## 4. Contribution Process

### DCO (Developer Certificate of Origin)
All commits must be signed: `git commit -s -m "message"`. CI rejects unsigned commits. This is lighter-weight than a CLA and sufficient for OSS projects.

### Issue Triage
- New issues triaged within 7 days
- Labels: `bug`, `feature`, `docs`, `good-first-issue`, `help-wanted`, `security`, `breaking`, `priority/{low,med,high,critical}`
- Issues without activity for 60 days get a stale label; 30 more days → auto-close (security issues never auto-close)

### PR Review Standards
- Every PR linked to an issue (except trivial doc fixes)
- At least one approval from a maintainer required
- CI must be green
- For security-sensitive areas (permissions, isolation, gateway): two approvals required
- PRs > 800 lines diff are blocked — must be broken up

### Maintainer Tiers
- **Founder/BDFL** — Vasanth, final decisions on direction
- **Core Maintainers** — full commit access, can merge to `main`
- **Trusted Contributors** — can review and approve, cannot merge
- **Contributors** — anyone with a merged PR

Promotion is based on demonstrated quality + community fit, not just contribution count.

---

## 5. Security Policy

Per `SECURITY.md`:

- **Private reporting:** security@friday-project.org or GitHub private vulnerability reporting
- **Response SLA:** acknowledgement within 48 hours
- **Disclosure timeline:** 90 days standard, can be shortened for actively-exploited or high-severity issues
- **Credit:** reporters credited in changelog and SECURITY hall of fame
- **Bug bounty:** none in v0.x; revisit at v1.0

---

## 6. Launch Sequence

### T-30 days (pre-launch)
- Finalise public-facing docs
- Lock the API surface (anything renamed after v0.1.0 = breaking change)
- Internal red-team review of the security model

### T-14 days
- Soft launch to 5–10 trusted reviewers (private fork or NDA)
- Collect feedback, fix critical issues
- Draft launch posts and tweet thread

### T-7 days
- Final code freeze on `release/v0.1.0`
- Generate the v0.1.0 release artefacts
- Pre-write blog post, Show HN draft, LinkedIn post

### T-0 (launch day)
- Flip repo from private to public
- Tag v0.1.0
- Publish blog post on `friday.dev`
- Submit to Hacker News (Show HN), Reddit r/selfhosted and r/programming, dev.to, lobste.rs
- Post in Frappe forum and Frappe Discord
- Post on Twitter/X, LinkedIn with the architecture diagram

### T+1 to T+7
- Respond to every comment and issue within 24 hours
- Fix critical bugs as patches (v0.1.1, v0.1.2)
- Engage with anyone who tries to install — watch for install-experience friction

### T+30
- Retrospective: what worked, what didn't
- Plan v0.2.0 based on community feedback

---

## 7. Community Spaces

Set up before launch:

| Channel | Purpose |
|---|---|
| GitHub Discussions | Q&A, ideas, show-and-tell |
| Discord (or Matrix) | Real-time chat, dev coordination |
| Mailing list (low-volume) | Releases, security advisories |
| Twitter/X account | Announcements, dogfood updates |
| Blog on `friday.dev` | Long-form writing, case studies, design rationale |

**Don't:** set up Telegram, WhatsApp, Slack (closed-source), or any walled garden as a primary community space.

---

## 8. Documentation Site

Host on GitHub Pages or Cloudflare Pages. Static site built from `docs/` markdown.

Suggested stack: MkDocs Material, or Docusaurus, or Astro Starlight. Pick one and commit.

Structure:
- Landing page with 60-second value pitch
- "Get Started" → install + first agent
- "Concepts" → key abstractions (Agent Profile, Skill, War Room)
- "How-to" → recipes
- "Reference" → DocType schemas, REST API, configuration
- "Design" → the 39 design docs

---

## 9. Anti-Patterns to Avoid

- **Vanity metrics:** don't optimise for stars early. Optimise for repeat users.
- **Surface-only marketing:** if the install experience is broken, no amount of LinkedIn posts will save it. Fix friction first.
- **Roadmap public theatre:** keep a public roadmap, but don't make commitments you can't keep. Better to under-promise.
- **Burning out one maintainer:** delegate aggressively. Documented contribution paths matter more than your own throughput.
- **Closing issues fast:** an old open issue is honest. A closed-without-resolution issue burns trust.

---

## 10. Success Criteria (T+90 days)

The launch is successful if:

- [ ] >= 100 GitHub stars
- [ ] >= 10 external contributors with merged PRs
- [ ] >= 3 documented production deployments (case studies)
- [ ] No unfixed critical security issues
- [ ] Active Discussions traffic (>5 threads per week)
- [ ] At least one third-party blog post or video covering Friday
- [ ] Time-to-first-running-agent for a new user: < 30 minutes

These are deliberately modest. Healthy growth is the goal, not virality.
