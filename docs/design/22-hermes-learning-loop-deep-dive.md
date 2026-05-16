# 22 — Hermes Learning Loop Deep Dive & Friday Enhancement Strategy

> **Purpose:** Detail how Hermes Agent's skill-improvement learning loop works, and define Friday's implementation that preserves the core mechanism while adding enterprise governance: versioning, supervisor approval, cross-agent sharing, confidence scoring, and rollback.

This document specifies the **autonomous curator** and **skill evolution** subsystem.

---

## 1. What Hermes Does

Hermes' learning loop (synthesised from public documentation and the OpenClaw-pattern discussion in doc 15):

1. **Trigger:** Every N tool calls (default ~15), or end of session, or on heartbeat.
2. **Analysis:** Agent reads its own recent conversation transcript and execution log.
3. **Pattern extraction:** Identifies which skills were invoked, which succeeded, which failed, common failure modes.
4. **Performance index:** Tracks success rate per skill over time.
5. **Improvement draft:** For skills below a threshold (e.g. <80% success), the agent drafts an improvement — clearer instructions, refined `when_to_use` conditions, corrected parameter examples.
6. **Confidence score:** Agent self-rates confidence in the improvement (0..1).
7. **Persist:** If confidence > threshold (default 0.75), the agent writes the patch to the skill's markdown file using `skill_manage` tool.
8. **Async:** All of this runs in the background so the main conversation isn't blocked.

The strength: skills evolve continuously without explicit human curation.

The weakness for enterprise use: an agent silently editing its own behaviour rules is exactly the failure mode auditors flag. We keep the mechanism; we change the governance.

---

## 2. Friday's Enhancement: Governed Learning Loop

The same core loop, with five additions:

### Addition 1 — DocType-backed versioning
Skills in Friday are DocTypes (doc 05). Every improvement creates a new `Skill Version` row, not an in-place edit. Old versions remain queryable. Active version is referenced by a pointer.

### Addition 2 — Mandatory human approval for production
The agent never auto-promotes an improvement to production. The flow is:

```
Agent generates improvement → Skill Draft DocType (status=Pending Review)
  → Supervisor sees in War Room: "Procurement Agent suggests this update to skill X"
    → Supervisor reviews diff, sees confidence + reasoning
      → Approves: Skill Draft → Skill (new version) → Active
      → Rejects: Skill Draft marked Rejected with reason; agent learns the reasoning
```

### Addition 3 — Cross-agent learning via Redis pubsub
When a skill is promoted, the gateway publishes `skill.promoted` on Redis pubsub. All agents using that skill flush their local cache and pick up the new version on next invocation. Across many agents using the same skills, improvements propagate immediately.

### Addition 4 — Confidence + provenance scoring
Every improvement carries:
- Confidence (agent's self-rating)
- Evidence count (how many executions informed it)
- Provenance trace (which Execution Log rows fed into the analysis)

Supervisors see all of this before approving.

### Addition 5 — Rollback as first-class
Every skill change is rollback-safe. If a new version causes regressions:
- Supervisor clicks "Rollback" on the Skill DocType
- Active pointer reverts to the prior version
- Affected Execution Logs flagged for review
- The rolled-back version is marked `Reverted` with reason

---

## 3. DocTypes Involved

### Skill (extended from doc 05)

New fields:
| Field | Type |
|---|---|
| `active_version` | Link → Skill Version |
| `version_count` | Int (read-only) |
| `success_rate` | Float (rolling, last N executions) |
| `last_improvement_at` | Datetime |

### Skill Version (new)

| Field | Type |
|---|---|
| `parent_skill` | Link → Skill |
| `version_number` | Int (auto-increment per skill) |
| `description` | Text |
| `when_to_use` | Long Text |
| `instructions` | Long Text |
| `parameters_schema` | JSON |
| `created_by_agent` | Link → Agent Profile (nullable; null for human-authored versions) |
| `confidence` | Float |
| `evidence_count` | Int |
| `provenance` | Table → Execution Log |
| `status` | Select (Active / Superseded / Reverted) |
| `promoted_at` | Datetime |
| `promoted_by` | Link → User |
| Submittable | Yes |

### Skill Draft (new)

| Field | Type |
|---|---|
| `target_skill` | Link → Skill |
| `proposed_by_agent` | Link → Agent Profile |
| `proposed_version` | Section with same fields as Skill Version |
| `diff_summary` | Long Text (what changed and why) |
| `confidence` | Float |
| `evidence_count` | Int |
| `provenance` | Table → Execution Log |
| `status` | Select (Pending Review / Approved / Rejected) |
| `reviewed_by` | Link → User |
| `review_reason` | Text |
| `reviewed_at` | Datetime |
| Submittable | Yes |

---

## 4. The Learning Job

A background RQ job, `friday.skills.learner.tick`, scheduled every hour (configurable).

```python
def tick():
    # 1. Find skills with enough recent evidence and low success rate
    candidates = frappe.db.sql("""
        SELECT s.name
        FROM `tabSkill` s
        WHERE s.status = 'Active'
          AND s.success_rate < 0.80
          AND (SELECT COUNT(*) FROM `tabExecution Log` el
               WHERE el.skill = s.name AND el.creation > NOW() - INTERVAL 24 HOUR
              ) >= 10
    """)

    for skill in candidates:
        # 2. Pick an agent qualified to propose an improvement
        agent = pick_qualified_proposer(skill)

        # 3. Spawn an analysis job for that agent
        frappe.enqueue(
            'friday.skills.learner.analyse_and_propose',
            agent_profile=agent.name,
            skill_name=skill.name,
        )
```

The `analyse_and_propose` task:

```python
def analyse_and_propose(agent_profile, skill_name):
    skill = frappe.get_doc('Skill', skill_name)
    logs = recent_execution_logs(skill_name, limit=50)

    # The agent runs in its own sandbox with a focused prompt:
    # "You are improving the skill 'send_invoice'. Here is the current
    #  version. Here are the recent execution logs (successes and
    #  failures). Propose a revised version that addresses the failure
    #  patterns. Output: diff_summary, proposed_version JSON, confidence."

    result = run_agent_for_skill_improvement(
        agent_profile=agent_profile,
        skill=skill,
        evidence=logs,
        token_budget=20000,
    )

    if result.confidence >= 0.5:  # generous threshold for drafting
        frappe.get_doc({
            'doctype': 'Skill Draft',
            'target_skill': skill_name,
            'proposed_by_agent': agent_profile,
            'proposed_version': result.version_fields,
            'diff_summary': result.diff_summary,
            'confidence': result.confidence,
            'evidence_count': len(logs),
            'provenance': [{'execution_log': log.name} for log in logs],
            'status': 'Pending Review',
        }).insert().submit()

        # Notify supervisor
        post_to_warroom(
            project=skill.governing_project,
            message=f"💡 Agent @{agent_profile} proposes an improvement to skill `{skill_name}` (confidence {result.confidence:.2f}). [Review →]"
        )
    else:
        log_low_confidence(agent_profile, skill_name, result)
```

---

## 5. Approval UX in War Room

A Skill Draft appears in War Room with a Raven Message Action:

```
💡 Procurement Agent proposes update to skill `send_supplier_email`
   Confidence: 0.87 (high)
   Evidence: 23 recent executions
   Summary: "Current skill produces overly formal emails for follow-ups.
            Proposed: detect message tone from prior thread; mirror tone."

   [View Diff in Desk]  [Approve]  [Reject with reason]
```

`Approve` triggers:
1. Skill Draft status → Approved
2. New Skill Version row created with the proposed content
3. Skill's `active_version` updated to the new version
4. Previous version's status → Superseded
5. Redis pubsub `skill.promoted` fires
6. Agents flush local skill cache
7. War Room reaction 🧠 added to the draft message

`Reject` requires a reason, fed back to the learner for future calibration.

---

## 6. Confidence Calibration

Over time, we track:
- Predicted confidence at draft time
- Actual outcome (Approved / Rejected, and post-deployment success rate of the new version)

This calibration data trains a per-agent confidence-adjustment model. Agents whose self-reported confidence overestimates reality get their drafts displayed with calibration-adjusted scores in War Room.

This is a Phase 3 enhancement; in Phase 2 we use raw confidence with the supervisor's judgment as the only filter.

---

## 7. Rollback Mechanics

Every skill carries pointers to:
- `active_version`
- `previous_active_version` (auto-tracked on each promotion)

Rollback action:
1. Supervisor clicks "Rollback Active Version" on the Skill DocType
2. System sets `active_version = previous_active_version`
3. Current active version's status → `Reverted`
4. Reason captured
5. Redis pubsub `skill.rolled_back` fires
6. Affected agents flush cache
7. Notification posted to War Room

Rollback is **always safe** because every version was previously validated. Multiple rollbacks chain — you can rollback the rollback.

---

## 8. Cross-Agent Sharing

When a skill is promoted, all agents using that skill benefit immediately. But sometimes a specialised agent (e.g. React Developer) learns something the generic Full Stack Developer wouldn't. To support this:

- Skills can be **scoped** by Agent Role Profile (default: scoped to the profile of the proposing agent)
- Promotion within scope is automatic; cross-scope promotion requires explicit supervisor approval
- Supervisor sees "Promote to all Engineering Agent profiles" as a separate action when reviewing a draft

This balances local learning vs. fleet-wide propagation.

---

## 9. Audit Trail

Every step is queryable:
- Skill Draft rows = every proposal ever made
- Skill Version rows = every version ever active
- Execution Log rows = every execution; linked to the Skill Version it ran against (forensics: did this execution use v3 or v4 of the skill?)
- Permission Decision Log = who approved which promotion

For compliance, this trail answers: "Why did the agent act this way at time T?" with a deterministic chain through specific skill versions.

---

## 10. Anti-Patterns to Prevent

| Pattern | Prevention |
|---|---|
| Agent silently mutates its own skill | All changes go through Skill Draft + supervisor approval; agent never writes directly to active Skill |
| Improvement removes safety checks | Diff review surfaces removed constraints; high-risk skills require multi-supervisor approval |
| Skill drift across versions | Version history immutable; every version persisted |
| Forgotten rollback context | Rollback reason is mandatory and visible |
| Confidence inflation | Calibration data tracked; over time, mis-calibrated agents are flagged |
| Same draft proposed repeatedly | Deduplication: if a draft with the same diff was rejected within the last N days, suppress and inform the agent |

---

## 11. Phasing

| Phase | Learning Loop Scope |
|---|---|
| 1 (MVP) | Out of scope. Skills are human-authored. No learning loop. |
| 2 | Skill Draft DocType + manual flow (supervisor authors drafts; learner job exists but inactive) |
| 3 | Active learner job; agents propose drafts based on Execution Log analysis |
| 4 | Cross-agent sharing, calibration models, automated rollback heuristics |

Phase 1 must not run this loop. Friday's v0.1 proof point uses fixed skills curated by humans; ERPNext PO operations remain the Phase 1 flagship dogfood after that governed framework loop is proven. Learning is a Phase 2+ feature once the agent runtime is proven safe.

---

## 12. Dependencies

- Skill DocType from doc 05
- Execution Log DocType from doc 05
- Agent Profile + Role Profiles from docs 05 and 12
- Frappe RQ for background jobs
- Redis pubsub for cache invalidation
- Raven for War Room notifications (doc 16)

---

## 13. Engineering TODOs

- [ ] Decide how to expose Skill Version to the LLM. The agent should know what version it's running against (for context), but version-switching mid-conversation could confuse it. Likely: pin to active version at session start, refresh only on explicit boundary.
- [ ] Diff representation in War Room — text diff is hard to skim for non-technical supervisors. Consider a structured summary ("Changed: when_to_use; Added: 1 parameter; Removed: 0 lines").
- [ ] Throttle: a flood of drafts on the same skill within a short window should be coalesced.
- [ ] Bound the learner's evidence window — too narrow misses patterns, too wide produces stale drafts. Default 24 hours, configurable.
