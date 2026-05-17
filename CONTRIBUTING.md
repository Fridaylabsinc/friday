# Contributing to Friday

Friday is a Frappe-derived agentic framework for governed business agents.

The project is early. Contributions should protect the fundamentals first:

- agents operate inside typed DocTypes;
- skills are schema-validated and permission-gated;
- every execution is auditable;
- Kanban is a view over configurable workflow, not the workflow itself;
- ERPNext PO automation is the first Phase 1 flagship dogfood after the framework loop is green.

## Start Here

Read these documents before opening implementation work:

1. `docs/design/39-friday-framework-strategy.md`
2. `docs/design/41-porting-strategy-hermes-erpnext-raven.md`
3. `docs/design/42-phase-one-authority-contract.md`
4. `docs/design/06-phase-one-scope.md`
5. `docs/design/10-agent-execution-guide.md`

## Development Rules

- Keep Frappe core divergence minimal and documented.
- Prefer Friday modules/apps unless framework-level behavior truly requires a core patch.
- Do not activate agent-created profiles, skills, or workflows without validation and review.
- Do not bypass permission checks, even temporarily.
- Do not commit secrets, tokens, database dumps, or private customer data.
- Update design docs when implementation proves a design wrong.

## Pull Requests

Every PR should include:

- what changed;
- why it changed;
- design docs affected;
- tests or verification performed;
- security/audit implications if any.

Small, focused PRs are preferred.

## Contributing as an AI Agent (or Sponsoring One)

Friday accepts AI agents as first-class contributors under a published policy.
Read `docs/contributing/AI_CONTRIBUTORS.md` before submitting AI-authored work.
Every AI contribution requires a registered human sponsor, a written proposal,
sandboxed execution, and a human co-signature on the PR.

