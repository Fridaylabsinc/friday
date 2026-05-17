# 45 — Fork Policy

> **Purpose:** Define the discipline by which Friday derives from Frappe Framework source without becoming an unmaintainable private fork. Doc 39 declares Friday "Frappe-derived"; this document is the operating manual for what that means in practice over time.

---

## 1. The Risk Being Managed

Forking an active upstream framework is one of the most common ways open-source projects collapse over five years:

- The fork accumulates local modifications scattered through dozens of files.
- Upstream releases become harder and harder to merge.
- After 18 months, the maintainer can no longer cleanly absorb upstream security fixes.
- After 36 months, the fork is effectively a private framework with no upstream relationship.
- Contributors fork ecosystems, not codebases — they will not join a project whose foundation is a slow-drifting fork.

Friday's vision (per doc 39) requires some Frappe-derived feel from day one. The risk is that "framework feel" becomes "framework rewrite by accident."

This document prevents that.

---

## 2. The Two-Path Decision (Set by the Spike)

Doc 44 (Technical Feasibility Spike) decides whether Friday begins as:

- **Path A — Frappe app + Workspace branding.** No fork of Frappe core. Friday is a custom app installed on standard Frappe, with deep Workspace customization for the Control Room and bench command extensions for the `friday` CLI.
- **Path B — Friday-derived fork of Frappe.** Friday begins from Frappe source, applies a documented minimal patch set, and tracks upstream releases.

If the spike chooses Path A, **this document still applies** as a forward-looking discipline in case future requirements force a partial fork later. Sections 5–10 become relevant only if Friday ever modifies Frappe core.

If the spike chooses Path B, this document is operationally binding from day one.

---

## 3. The Forking Principle

> **Fork for identity and extension points. Do not fork into chaos.**

Friday may modify Frappe core source only when:

1. The behavior cannot be safely achieved as an app, module, hook, or DocType override.
2. The behavior makes agents first-class actors in identity, permission, audit, workflow, or job execution.
3. The benefit is universal across Friday — not specific to one feature or one customer.
4. The maintainer has documented the rationale, the alternatives considered, and the upstream incompatibility this creates.

Modifications that fail any of these tests belong in a Friday app, not in core.

---

## 4. Branch Strategy

If Path B is chosen, the friday repository uses this branch model:

- `upstream/main` — read-only mirror of `frappe/frappe:develop` or the chosen Frappe branch
- `upstream/v15` — read-only mirror of Frappe v15 branch
- `upstream/v16` — read-only mirror of Frappe v16 branch (or whichever version the spike chose)
- `friday/main` — Friday's main development branch
- `friday/release-X.Y` — Friday release branches

Friday changes never go on `upstream/*`. The `upstream/*` branches exist solely to make merging upstream releases tractable.

Merging upstream into `friday/main` happens on a scheduled cadence (see §6), never ad-hoc, never silently.

---

## 5. What May and May Not Be Modified in Core

### Permitted (with documentation)

- **Actor context propagation** — making agent identity a first-class actor type across requests, jobs, and workflows
- **Trace ID propagation** — assigning consistent trace IDs from request entry through to audit log
- **Audit hook surface** — adding hook points for Permission Decision Log and Execution Log emission
- **Workspace shell** — branding, default landing, navigation skeleton (when Frappe's existing Workspace API is insufficient)
- **bench command namespace** — registering `friday` subcommand group (if Frappe's command extension API does not suffice)
- **Permission check signature** — extending Frappe's permission check to receive agent context, only if app-level hooks cannot

### Forbidden (or requires escalation)

- **DocType engine internals** — never. Use DocType extension, not modification.
- **ORM internals** — never. Use Frappe's existing extension surfaces.
- **Database adapter code** — only via upstream contribution
- **Authentication/session core** — only via documented extension API
- **Frontend Desk JS core** — only via Workspace customization or app-level overrides
- **Setup/install/migration logic** — only via app hooks
- **Anything that breaks existing Frappe apps' compatibility** — never without explicit project-owner approval and a compatibility audit

If a Friday feature seems to require a forbidden modification, that is a signal to redesign the feature, not to make the modification.

---

## 6. Upstream Cadence

Friday reviews upstream Frappe releases on a fixed cadence:

| Cadence | Action |
|---|---|
| **Within 48 hours of upstream security release** | Review CVE; if affected, prepare emergency merge or patch |
| **Monthly** | Review upstream patch releases on the chosen Frappe version; merge into `friday/main` if no conflict |
| **Quarterly** | Review upstream minor releases; plan integration if relevant |
| **At each Frappe major release** | Project-level decision: stay on current major, plan migration, or skip |

Security releases are non-negotiable. Other releases follow the calendar.

The maintainer documents each upstream review in a `docs/upstream-log.md` even if the conclusion is "skipped, not relevant to Friday's substrate."

---

## 7. Divergence Registry

If Path B is chosen, the repo maintains a living document: `docs/core-divergences.md`.

Each modification to Frappe core gets one entry:

```
## Divergence: <short name>

- **File(s):** path/to/file.py:42-67, other/file.js:120
- **Date:** YYYY-MM-DD
- **Author:** name
- **Why:** explanation
- **Alternatives considered:** what app/module/hook paths were tried first and why they were insufficient
- **Upstream conflict risk:** Low / Medium / High
- **Reversibility:** how hard would it be to remove this if upstream provides an extension point
- **Tests:** which tests cover this divergence
```

The registry is reviewed quarterly. Divergences with Low reversibility and Low upstream conflict that have lived for over 12 months are candidates for upstream contribution.

---

## 8. Patch Discipline

If Path B is chosen, every core modification follows these rules:

1. **Minimal scope.** Touch the smallest possible surface. A 3-line change is preferred over a 30-line refactor.
2. **Documented in code.** Every modified line near a Friday divergence has a comment: `# friday-divergence: see docs/core-divergences.md#<name>`.
3. **Tested.** The divergence has a test that asserts the Friday-specific behavior; if upstream removes/changes the surrounding code, the test fails loudly.
4. **Tagged in git.** Every commit that modifies core has a `[friday-core]` prefix and references the divergence registry entry.
5. **Reviewed.** No core modification merges without the project owner's explicit review and approval.

---

## 9. App vs Core Decision Tree

When a new Friday capability is proposed, decide where it lives by walking this tree:

```
1. Can it be a Friday app?
   YES → Build as app. Stop.
   NO → continue.
2. Can it be implemented via a Frappe hook, override, or extension point?
   YES → Build as app using that mechanism. Stop.
   NO → continue.
3. Can it be implemented by extending Workspace, command, or DocType primitives that already exist?
   YES → Build as app. Stop.
   NO → continue.
4. Would the modification benefit all Friday features (not just this one)?
   YES → continue.
   NO → redesign feature to fit one of the above paths. Stop.
5. Does the modification fall into the "Permitted" list in §5?
   YES → propose as a core divergence. Document in the registry. Project owner review.
   NO → redesign or escalate.
```

A clear default in this tree: ship as an app whenever possible.

---

## 10. Compatibility Promise

Friday makes a public compatibility promise:

- **Existing Frappe apps installed on a Friday substrate should continue to work** unless they directly modify the same core surface Friday has modified.
- **Friday will document any breaking changes** to Frappe's public APIs that Friday introduces.
- **Friday will provide a migration guide** for each release that changes core behavior visible to apps.

This promise is what lets community Frappe developers consider Friday seriously. Without it, Friday becomes a private framework with no ecosystem.

If a Friday feature would require breaking this promise, the feature is redesigned. The promise is more valuable than the feature.

---

## 11. Failure Modes to Prevent

Common ways forks die. We name them explicitly:

| Failure Mode | Prevention |
|---|---|
| **Scope creep into core** | Strict §5 list; require project owner approval for every core modification |
| **Silent drift** | Divergence registry; quarterly review |
| **Security lag** | 48-hour CVE response; monthly upstream review |
| **App incompatibility** | Compatibility promise §10; CI tests against popular Frappe apps |
| **Lost upstream relationship** | Annual review of upstream maintainer relationship; contribute back where divergences match upstream needs |
| **Maintainer burnout** | Upstream cadence is calendar-driven, not on-demand; no heroics required |

---

## 12. Contributing Back Upstream

Friday should actively contribute improvements back to Frappe when:

- A divergence solves a problem that other Frappe users also have
- The divergence has stable design and would survive review
- The Frappe maintainers signal interest

This shrinks Friday's private patch set and strengthens the upstream relationship. Both sides benefit.

The maintainer reviews the divergence registry quarterly and flags candidates for upstream PR.

---

## 13. End-of-Life for Divergences

A divergence is retired when:

- Upstream Frappe adds an equivalent extension point
- The Friday feature requiring the divergence is removed
- The divergence is contributed back to upstream and accepted

Retired divergences are removed from the registry and from the codebase. A note remains in `docs/upstream-log.md` recording the date and reason.

---

## 14. Naming

If Path B is chosen and Friday distributes a Frappe-derived runtime:

- The Friday distribution is called **Friday Framework** in user-facing material.
- The upstream is called **Frappe Framework** in attribution and in all documentation acknowledging the substrate.
- The Friday repo's README clearly states: "Friday is derived from Frappe Framework (https://github.com/frappe/frappe), distributed under GPL v3."
- The Frappe NOTICE file content is preserved and extended, never removed.

This is not optional. GPL v3 requires preservation of copyright and attribution, and good faith requires more.

---

## 15. Open Questions

1. If the spike chooses Path A (no fork), does this document still apply? Lean: archive sections 4–9 as "if needed later." Keep sections 1–3, 10–14 as standing principles.
2. What is the upstream contribution etiquette specifically with Frappe Technologies and The Commit Company (now part of Frappe)? Establish direct relationship before contributing significant patches.
3. Should Friday maintain a public list of "Frappe versions we test against"? Yes, in `docs/compatibility-matrix.md` once Path A or Path B is decided.
4. How does the fork policy interact with FridayLabs SaaS distribution? FridayLabs runs Friday; the fork policy applies to the upstream relationship regardless of how FridayLabs distributes.

---

## 16. Summary

A fork dies by a thousand small cuts. This document tries to make every cut deliberate, documented, reversible, and rare.

If Friday becomes a private framework that cannot absorb upstream Frappe improvements, the project has failed even if every product feature ships on time.

The fork policy is therefore not bureaucracy. It is the discipline that lets Friday remain a framework that the Frappe community recognizes as one of their own — even as it adds the governed-agent layer they don't yet have.

---

**This document is binding from the moment doc 44's spike chooses Path B. Until then, it is forward-looking guidance.**
