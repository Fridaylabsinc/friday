<!--
Welcome. Before opening this PR, please confirm:
- A proposal issue exists and was approved (link it below) — required for non-trivial changes
- Tests are included alongside the code change
- No secrets, hardcoded paths, or permission bypasses
- AI-authored work: human co-signer assigned, sponsor handle in commit metadata
-->

## Summary

What changed? One short paragraph.

## Why

Why is this needed? Link the problem this solves.

## Linked proposal

- Closes #<proposal-issue-number>

(For tiny fixes — typos, doc clarifications under 50 lines, test additions for existing behaviour — no proposal needed. Delete this section if it doesn't apply.)

## Design docs referenced

- `docs/design/...`

## Verification

- [ ] Tests run locally and pass (`bench --site friday.localhost run-tests --app friday`)
- [ ] `bench --site friday.localhost migrate` runs clean on a fresh site
- [ ] `pre-commit run --all-files` passes (when configured)
- [ ] Validation checklist boxes ticked for this slice (`docs/design/11-agent-validation-checklist.md`)
- [ ] No secrets, API keys, or tokens committed
- [ ] No hardcoded paths (`~/.friday`, `/tmp/x`, literal site names)
- [ ] Every new code path that invokes a skill goes through `friday.permissions.matrix.check`
- [ ] Every caught exception either logs at WARNING+ or re-raises (no silent `pass`)

## Security and audit impact

Does this affect agents, skills, credentials, sandboxing, permissions, approvals, or audit logs? If yes, describe.

## Contributor information

- [ ] Human contributor
- [ ] AI contributor (sponsor co-signing required)
- [ ] Human-AI pair

**If AI contributor:**

- AI handle: `<handle>`
- Sponsor: `@<github-handle>`
- Sponsor accountability: I have reviewed this diff and accept responsibility.

## Additional notes

Anything reviewers should know — surprises, decisions you made, alternatives you rejected.
