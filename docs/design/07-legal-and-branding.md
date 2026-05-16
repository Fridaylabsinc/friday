# 07 — Legal & Branding

## License

**Friday is licensed under the GNU General Public License v3 (GPL v3)** to maintain compatibility with Frappe Framework.

### Why GPL v3

- Frappe Framework is licensed under GPL v3. Anything built on top of it that distributes Frappe must comply with GPL v3.
- Friday's vision is fully open-source from day one, so GPL v3 aligns with the project's intent.
- GPL v3 ensures derivative works remain open, protecting the community contribution model.

### What This Means in Practice

- Friday's source code must remain freely available.
- Anyone using or modifying Friday must release their modifications under GPL v3 if they distribute it.
- Friday cannot be relicensed to a permissive license (MIT, Apache) without consent of all contributors.
- Friday **can** be deployed and used internally without distribution obligations (GPL only triggers on distribution).
- Commercial use is **explicitly allowed**. Companies can deploy Friday in production without paying license fees.

### AGPL Consideration

Frappe Technologies has been moving newer apps (Helpdesk, Gameplan) toward **AGPL v3**, which extends GPL's reciprocal obligations to SaaS deployments. Friday should evaluate AGPL v3 vs GPL v3 closer to open-source launch:

- **GPL v3**: copyleft on distribution. SaaS providers can use Friday without releasing modifications.
- **AGPL v3**: copyleft on distribution **and network use**. SaaS providers must release modifications.

For an agentic framework where most usage will be SaaS / hosted, **AGPL v3** is likely the better fit — it prevents commercial forks from offering proprietary hosted Friday without contributing back.

**Recommended:** Start drafting with GPL v3 (matches Frappe core), revisit AGPL v3 before public launch.

## Copyright

- The Friday project's copyright is held by the **contributors**, with the original author as the primary copyright holder for initial code.
- Use a `LICENSE` file (verbatim GPL v3 text) at the repo root.
- Use a `NOTICE` or `AUTHORS` file to track significant contributors.
- File headers should include a brief copyright notice: `Copyright (c) [year] [author] and contributors. Licensed under GPL v3.`
- Consider a **Developer Certificate of Origin (DCO)** for contributions, signed via `git commit -s`. Simpler than a CLA, sufficient for most OSS projects.

## Documentation License

Documentation should be **Creative Commons Attribution-ShareAlike 3.0 (CC-BY-SA-3.0)**, matching Frappe's documentation license. This allows broad reuse while keeping derivatives open.

Mark this explicitly in `docs/LICENSE` and in the docs site footer.

## Branding

### Product Name

**Friday** — the framework name. Short, memorable, evocative (echoes "Man Friday" — the helpful companion).

### Tagline Options

- "An agentic framework powered by Frappe"
- "Hermes-grade agents, Frappe-grade governance"
- "The agent that grows with your enterprise"

### Naming Rules

- **Do**: "Friday — an agentic framework powered by Frappe"
- **Do**: "Friday for Frappe"
- **Do**: "Friday (built on Frappe Framework)"
- **Don't**: "Frappe Friday" (sounds like an official Frappe product)
- **Don't**: "Friday by Frappe" (implies Frappe Technologies is the author)
- **Don't**: use the Frappe logo unmodified as Friday's logo

The name "Frappe" and the Frappe logo are trademarks of **Frappe Technologies Pvt. Ltd.** You can reference Frappe factually ("built on Frappe Framework", "compatible with Frappe sites") but cannot imply official endorsement, partnership, or origin.

### Hermes / Nous Research / OpenClaw

Friday is **inspired by** Hermes Agent's architecture and OpenClaw's patterns but is **not a fork**. You're free to:

- Reference Hermes / OpenClaw in documentation and architecture discussions ("inspired by Hermes Agent's gateway pattern").
- Implement the same design ideas (gateway, skills, Kanban, learning loop) — ideas aren't copyrighted.
- Quote short, attributed snippets from their open documentation under fair use.

You should **not**:

- Copy substantial source code from Hermes or OpenClaw without complying with their licenses.
- Use the "Hermes" or "OpenClaw" name as part of Friday's product name.
- Imply endorsement by Nous Research or the OpenClaw maintainers.

If you reuse any code from Hermes (which is also open-source), preserve its license headers and attribute clearly in `NOTICE`.

## Repository Setup

When you flip from private to public (Phase 2), ensure the repo has:

| File | Purpose |
|---|---|
| `LICENSE` | GPL v3 (or AGPL v3) full text |
| `README.md` | Project overview, install, quick start, link to docs |
| `CONTRIBUTING.md` | How to contribute, DCO, code style, PR process |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 is standard |
| `SECURITY.md` | How to report security issues privately (mirror Hermes' approach) |
| `NOTICE` or `AUTHORS` | Attribution to contributors and inherited works |
| `CHANGELOG.md` | Versioned release notes |
| `.github/ISSUE_TEMPLATE/` | Bug, feature, security templates |
| `.github/PULL_REQUEST_TEMPLATE.md` | Standardised PR description |

## Trademark Strategy

For the first 12–24 months, don't worry about trademarking "Friday" — focus on building. Trademark searches are cheap; trademark filings are not. Once the project has meaningful adoption (a few hundred stars, multiple production users), consider:

- A USPTO trademark search on "Friday" in the software / SaaS classes (likely many existing marks; you may need to pivot the name or scope tightly to "agentic framework").
- Defensive trademark registration if you find clear conflict risk.

If "Friday" turns out to be too crowded a trademark space, fallback names to consider:

- **Fri** — even shorter
- **FridayKit**
- **AgentFriday**
- **Friday Framework**

Decide before open-source launch, not after — renaming a public project is painful.

## Patents

Frappe Technologies does not assert patents against derivative works. Hermes and OpenClaw similarly do not appear to hold restrictive patents. Friday inherits the GPL v3 patent grant from any GPL-licensed dependencies, which provides reasonable defensive coverage.

You should not file patents on Friday's design — it would conflict with the open-source ethos and could deter contributions.

## Compliance Summary

| Area | Status | Action |
|---|---|---|
| License (Friday code) | Confirmed: GPL v3 required | Add LICENSE file at scaffold time |
| License (Friday docs) | CC-BY-SA-3.0 recommended | Add docs/LICENSE |
| Frappe license compatibility | ✅ GPL v3 ↔ GPL v3 | No action |
| Trademark — "Frappe" | Third-party trademark | Use factually, never as Friday's name |
| Trademark — "Hermes" / "OpenClaw" | Third-party names | Reference, don't appropriate |
| Trademark — "Friday" | Likely crowded space | Search before public launch |
| Patents | No restrictive IP | None needed |
| Contributor licensing | DCO recommended | Document in CONTRIBUTING.md |

## TL;DR

- Friday is **GPL v3** (consider AGPL v3 closer to launch).
- Docs are **CC-BY-SA-3.0**.
- The name **"Friday"** is the product; **"powered by Frappe"** is the relationship.
- Reference Hermes and OpenClaw as inspiration, never as the product.
- Use a DCO for contributions to keep licensing clean.
- No license fees, no patents, no proprietary lock-in — ever.
