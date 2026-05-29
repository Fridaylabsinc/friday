# Friday Quickstart

Create your first agent and skill in 10 minutes.

## Before You Start

Make sure Friday is installed per [install.md](install.md) and the site is running.

## Step 1 — Create a Skill

Go to **Frappe Desk → Skills → New Skill**.

| Field | Value |
|-------|-------|
| Skill Name | `create_note` |
| Status | `Active` |
| Skill Handler | `create_note` |
| Description | Creates a note in the system |

For the first skill, we keep it simple — no parameters needed.

## Step 2 — Create an Agent Role

1. Go to **Frappe Desk → Roles → New Role**.
2. Name it `Friday Note Creator`.
3. Grant **Create** permission on the **Note** DocType.

## Step 3 — Create an Agent Profile

1. Go to **Frappe Desk → Agent Profiles → New Agent Profile**.
2. Fill in:

| Field | Value |
|-------|-------|
| Agent Profile Name | `note_taker` |
| Agent Role Profile | Add `Friday Note Creator` |
| Status | `Active` |

3. Under **Permitted Skills**, add the `create_note` skill.

## Step 4 — Connect an LLM Provider

1. Go to **Frappe Desk → LLM Providers → New LLM Provider**.
2. Configure your API key (e.g., Minimax M2).
3. Go to **Agent Settings** and set your default provider.
4. On the `note_taker` profile, set **Model Provider** to your LLM Provider.

## Step 5 — Create a Chat Platform

Go to **Frappe Desk → Chat Platforms → New Chat Platform**:

| Field | Value |
|-------|-------|
| Platform Name | `friday_cli` |
| Platform Type | `CLI` |
| Default Agent Profile | `note_taker` |

## Step 6 — Test with the CLI

```bash
bench --site friday.localhost console
```

Or use the CLI tool:

```bash
friday chat --profile note_taker
```

Try: `Create a note titled "My First Agent Note" with content "Hello from Friday!"`

The agent should:
1. Parse your request
2. Call the `create_note` skill
3. Create the Note row in the database
4. Reply with confirmation

## What Happened Under the Hood

1. **Gateway** received your message and routed it to the `note_taker` profile.
2. **LLM Provider** generated a tool call (`create_note`).
3. **Permission Engine** checked: does `note_taker` have permission to execute `create_note`? → Yes.
4. **Dispatcher** executed the skill handler.
5. **Execution Log** recorded the result.
6. **Permission Decision Log** recorded the permission check.

## Something Went Wrong?

- Check **Agent Settings** has a default LLM provider.
- Check the **Permission Decision Log** for denied skill calls.
- Check the **Execution Log** for failed skill executions.
- Check `logs/frappe.log` for errors.

## Next Steps

- [Architecture](architecture.md) — understand the system
- [Skill Loader](design/10-agent-execution-guide.md) — how skills are loaded and executed
- [Permission Engine](design/04-security-model.md) — how permission decisions are made
- [Docker Sandbox](docs/contributing/proposals/slice-7-docker-sandbox.md) — run skills in isolated containers