# Security Policy

Friday is designed around governed agents, so security issues are treated as product-critical.

## Reporting

Until a public security email is configured, report vulnerabilities privately to the repository maintainers through GitHub private vulnerability reporting if enabled.

Please do not open public issues for exploitable vulnerabilities.

## Scope

Security-sensitive areas include:

- permission checks;
- Agent Profile and Skill activation;
- sandbox execution;
- credential handling;
- Execution Log and Permission Decision Log integrity;
- Raven message actions;
- ERPNext integration and agent users;
- workflow approvals;
- any path that lets an agent execute code or mutate business records.

## Baseline Expectations

- No hard-coded credentials.
- No secret values in logs, prompts, War Room messages, or issue comments.
- Every skill execution must have a Permission Decision Log.
- Every execution attempt must have an Execution Log.
- Agents must not silently activate profiles, skills, or workflows.

