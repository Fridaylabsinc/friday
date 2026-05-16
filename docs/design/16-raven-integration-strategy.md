# 16 — Raven Integration Strategy

> **Purpose:** Define how Friday integrates **Raven** (open-source team messaging built on Frappe) as the War Room and human-agent collaboration backbone. Replaces any custom chat implementation in earlier drafts.

Raven repo: `The-Commit-Company/raven`. License compatible with Friday's GPL v3.

---

## 1. Why Raven

Building chat from scratch is reinvention. Raven already exists, is GPL-compatible, integrates natively with Frappe (channels, DMs, files, reactions, message actions, document sharing, timeline integration), and uses Socket.IO for real-time.

Friday adopts Raven for:

| Purpose | Raven Feature |
|---|---|
| Project War Room | Public/private channel per Agent Project |
| Direct human ↔ agent chat | Direct messages |
| File sharing in context | Native file uploads with permission inheritance |
| Status indicators | Custom emoji reactions |
| Triggering workflows from chat | Message Actions (right-click → create DocType) |
| Embedded document previews | Raven's document sharing with form actions |
| Audit thread on every project | Raven Timeline integration on Frappe documents |

---

## 2. Core Integration Points

### 2.1 War Room as a Raven Channel

Every Agent Project gets one Raven channel auto-created on `after_insert`. Naming convention: `war-room/{project-code}`.

| Property | Value |
|---|---|
| Channel visibility | Mirrors Agent Project visibility (public / private / restricted) |
| Members on creation | Linked Users of all assigned Agent Profiles + supervisors |
| Pinned message | Project brief (Markdown) + emoji legend |
| Archive policy | When Agent Project transitions to `Completed`, channel becomes read-only (see §6) |

**Hook implementation:**
```python
# friday/integrations/raven/hooks.py
def on_project_created(doc, method=None):
    channel = create_raven_channel(
        name=f"war-room/{doc.project_code}",
        type="Public" if doc.visibility == "Public" else "Private",
        description=doc.brief[:200],
    )
    add_members(channel, agent_profiles_to_users(doc.assigned_profiles))
    pin_message(channel, render_project_brief(doc))
```

### 2.2 Message Actions for Agent Workflows

Raven's Message Actions let users right-click a message → trigger a configured DocType action. Friday ships four out of the box:

| Action | Effect |
|---|---|
| **Escalate** | Creates `Escalation` DocType pre-filled with message context |
| **Log Decision** | Creates a `Decision Record` from the message + thread context |
| **Approve Skill** | Resolves a pending `Workflow Request` (`approved=true`) |
| **Import Skill** | Validates an attached skill JSON/YAML, creates `Skill Draft` |

Permission: Message Actions are gated by Frappe role permissions. Only `supervisor_agent` or human supervisors can trigger `Approve Skill`. Misuse is impossible — the underlying DocType permissions enforce it.

### 2.3 Document Sharing in War Room

Raven's document-share renders an inline preview with workflow buttons. Friday extends it for:

- **Agent Task share** → preview shows state, assignee, due date; buttons: reassign, change priority, mark blocked
- **Execution Log share** → preview shows skill, parameters (masked), result; button: re-run with parameters
- **Skill share** → preview shows L0 header; button: view L1 / L2 in Desk

### 2.4 Timeline Sync

Every War Room message is mirrored into the Agent Project's Frappe Timeline. The Timeline is the canonical audit record; Raven is the live-conversation view of it.

Mirror implementation:
```python
# friday/integrations/raven/timeline_sync.py
def on_raven_message(message):
    if message.channel.startswith("war-room/"):
        project = resolve_project_from_channel(message.channel)
        frappe.get_doc({
            "doctype": "Communication",
            "reference_doctype": "Agent Project",
            "reference_name": project.name,
            "content": message.text,
            "sender": message.sender,
            "communication_medium": "Raven",
        }).insert(ignore_permissions=False)
```

Permissions still enforce: a user can only see Timeline entries for Projects they have permission on. No leak from Raven to Timeline.

### 2.5 Custom Emoji as Status Indicators

Friday installs a standard emoji set on Raven activation:

| Emoji | Meaning | Auto-trigger |
|---|---|---|
| 🚀 | Skill execution started | Gateway posts on skill dispatch |
| ✅ | Task completed | Gateway posts on Task → Completed |
| ⚠️ | Blocker hit | Gateway posts on Task → Blocked |
| ❌ | Permission denied | Gateway posts on denied invocation |
| 🔄 | Retry attempt | Gateway posts on retried execution |
| 👀 | Under human review | Gateway posts on Workflow Request created |
| 🧠 | Skill learned/improved | Gateway posts when curator promotes a Skill |
| 🛑 | Emergency pause | Supervisor reacts to halt agent in real-time |

Humans can react with these emoji to drive actions (a 🛑 reaction triggers a pause-agent action, gated by supervisor role).

### 2.6 Direct Messages for Supervisor Interventions

Supervisors can DM an Agent Profile (its linked User). The agent treats DMs as direct instructions, scoped to the supervisor's permission level. DMs are also Timelined for audit.

---

## 3. Security & Permissions

| Concern | Mitigation |
|---|---|
| Channel membership reveals project scope | Channel visibility mirrors Agent Project permission; users without project access can't even see the channel exists |
| Messages may contain secrets | Field masking (doc 13) applies on Timeline; Raven respects same masking via render hook |
| Message Action abuse | Each action gates on the underlying DocType permission |
| Channel archive | When project closes, channel becomes read-only; deletion is a separate explicit operator action |
| File uploads | Inherit Frappe File DocType permissions; private by default |

---

## 4. Setup Sequence

On Friday installation with Raven:

1. Verify Raven app is installed: `bench --site {site} list-apps | grep raven`
2. Install Friday-Raven bridge: `bench --site {site} install-app friday-raven-bridge`
3. Migrate: `bench --site {site} migrate`
4. Bridge installs:
   - Message Action definitions (Escalate, Log Decision, Approve Skill, Import Skill)
   - Standard emoji set
   - Hooks on Agent Project, Agent Task, Workflow Request
5. First-run wizard creates a default "Friday Operations" channel for system-wide notifications

If Raven isn't installed, Friday falls back to Frappe Comments on Agent Project. Functional but degraded — no real-time, no Message Actions, no rich UX.

---

## 5. Use Cases

### Use Case A — Task execution with real-time coordination
1. Supervisor creates Agent Task in Frappe Desk.
2. War Room channel exists from project creation.
3. Dispatcher claims task → posts 🚀 in channel.
4. Agent executes, posts intermediate updates as it works.
5. Hits a question → tags supervisor; supervisor replies in channel.
6. Agent completes → posts ✅ with link to result document.
7. Supervisor right-clicks completion message → "Approve Skill" if it learned something new.

### Use Case B — Escalation flow
1. Agent hits permission_denied.
2. Gateway posts ⚠️ in War Room with structured context + [Approve in Frappe] / [Take Over] / [Decline] buttons.
3. Supervisor clicks Take Over → Message Action invokes the underlying skill as the supervisor's user; result posted back.
4. Original agent resumes its task with the new data.

### Use Case C — Skill import discussion
1. Engineer pastes a skill JSON file in War Room.
2. Team discusses inline.
3. Supervisor right-clicks the file message → "Import Skill".
4. Validator runs; Skill Draft created; supervisor reviews in Desk.
5. After approval, Skill becomes Active and propagates to permitted agents.

---

## 6. Lifecycle Policy

| Project State | Raven Channel State |
|---|---|
| Active | Channel writeable, real-time |
| Completed | Channel locked read-only; pinned message updated with completion summary |
| Archived | Channel hidden from default channel list; still searchable; Timeline preserved |
| Deleted | Channel archived but Timeline retained on Agent Project for audit |

**Retention:** channels persist indefinitely by default. Operators can configure age-based archival (e.g. archive channels for projects completed >180 days ago).

**⚠️ Engineering TODO:** confirm Raven's channel deletion semantics — does it preserve message history in the database after delete, or hard-delete? Friday requires the former for audit.

---

## 7. Known Limitations

- **Scale:** untested with >100 active agents in a single channel. Phase 2 load test required.
- **Mobile UX:** Raven's mobile app surfaces standard messages well, but Message Actions need verification.
- **Cross-site:** if Friday runs multi-site (doc 37), Raven channels are per-site. Cross-site supervision needs federation, which isn't in Phase 1.
- **Voice/video:** not in Raven scope. Out of scope for Friday Phase 1–2.
- **Retention compliance:** Raven doesn't yet have built-in retention policy. Friday wraps this via scheduler job.

---

## 8. Phasing

| Phase | Raven Scope |
|---|---|
| 1 (MVP) | Channel auto-creation; Timeline sync; default emoji set; basic Message Actions (Escalate, Log Decision) |
| 2 | Approve Skill / Import Skill actions; document share previews with workflow buttons; archive policy automation |
| 3 | Cross-site channel federation (if multi-site deployment matures) |

---

## 9. Dependencies

- Raven app v2.0+ (for Message Actions and document sharing)
- Frappe v15 (Friday's target) — Raven v2 is v15-compatible
- Friday core modules: Agent Project, Agent Task, Execution Log, Workflow Request, Skill, Agent Profile

---

## 10. Rollback Plan

If Raven proves unstable or becomes unmaintained, the integration is a separate Frappe app (`friday-raven-bridge`). Disabling it falls back to Frappe Comments on Agent Project. No data loss — Timeline is the source of truth, Raven is the surface.
