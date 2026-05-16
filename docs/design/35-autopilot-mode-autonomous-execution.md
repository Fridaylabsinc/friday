# 35. Autopilot Mode — Autonomous Execution

## Concept

Friday agents operate on a spectrum from "every step requires human approval" to "fully autonomous." Autopilot is the highest level on this spectrum — the agent executes a task end-to-end without per-step approval, returning a summary at completion.

Autopilot is not granted by default. It is **earned per task type** based on measured success rate, and revoked when conditions deteriorate.

## Why Confidence-Gated Autopilot

Three risks of premature autopilot:
1. **Quiet failures** — agent makes mistakes the supervisor doesn't notice until consequences manifest
2. **Compound errors** — agent acts on flawed inference, then acts again on the flawed result
3. **Trust collapse** — one bad autopilot incident destroys months of credibility

Confidence-gating ensures autopilot is only enabled for task types Friday has proven it handles reliably, with circuit breakers when reliability drops.

## DocType: Task Type

A taxonomy entry for repeated task patterns:

Fields:
- `task_type_code` (Data, unique) — e.g. "procurement.create_po_standard"
- `description` (Text) — what this task type covers
- `domain` (Link to Domain)
- `agent_role_profile` (Link to Agent Role Profile) — which profile executes
- `signature_pattern` (Long Text) — heuristic for matching tasks to this type
- `success_definition` (Long Text) — what constitutes success for this task type
- `total_executions` (Int) — lifetime count
- `successful_executions` (Int)
- `success_rate_rolling_30d` (Float) — auto-computed
- `current_mode` (Select: Shadow, Manual, Assisted, Autopilot)
- `autopilot_threshold` (Float, default 0.95)
- `autopilot_min_samples` (Int, default 50) — minimum executions before autopilot eligible
- `last_anomaly_at` (Datetime)
- `circuit_breaker_active` (Check)

## Execution Modes

### Shadow Mode
- Agent processes the task, generates the plan, but doesn't execute
- Plan goes to War Room as a "proposed action"
- Supervisor reviews and either executes manually or approves Friday to execute
- Used during onboarding and for new task types

### Manual Mode
- Agent waits for supervisor to assign and approve each task individually
- Default for new task types after Shadow

### Assisted Mode
- Agent executes step by step, each step posted to War Room
- Supervisor can interrupt at any step
- No upfront approval, but visibility is continuous

### Autopilot Mode
- Agent executes the full task autonomously
- Single summary posted to War Room at completion
- No mid-task interruptions unless agent self-escalates

## Promotion to Autopilot

A task type promotes from Assisted → Autopilot when:
1. `total_executions` ≥ `autopilot_min_samples` (default 50)
2. `success_rate_rolling_30d` ≥ `autopilot_threshold` (default 0.95)
3. No anomalies in last 14 days
4. Supervisor explicitly approves the promotion (one-click via War Room "Promote to Autopilot")
5. Promotion logged immutably

Promotion is **not** automatic on threshold crossing. Friday surfaces the candidate; the human decides.

## Demotion from Autopilot

A task type demotes from Autopilot → Assisted when:
1. Rolling 30d success rate falls below `autopilot_threshold - 0.05` (default: below 0.90), OR
2. Three or more anomalies occur in 7 days, OR
3. A single high-severity incident occurs (financial loss, customer complaint, regulator-relevant), OR
4. Supervisor manually demotes via War Room

Demotion is **automatic** for the first three conditions. Friday does not wait for permission to step down — fail-safe defaults.

Demotion notice is high-priority in War Room with the data that triggered it.

## Circuit Breaker

In addition to demotion, a circuit breaker pauses execution entirely:

Triggers:
- Two consecutive failures in autopilot mode
- Detected anomaly during execution (output validation fails)
- External dependency reports degraded state

When tripped:
- All pending tasks of this type pause
- Supervisor notified
- Manual reset required to resume
- Reset logged with reason

## Anomaly Detection

During execution, the agent runs continuous validation:

### Output Validation
After each skill call, validate the output against expected schema/range:
- Numeric outputs within expected bounds
- Required fields present
- Status fields show valid transitions
- No NULL/empty where unexpected

### Pre-Submit Validation
Before document submission to ERPNext:
- Tax calculations match expected formulas
- Account postings balance
- Dates within reasonable range
- Quantities match upstream document

### Cross-Reference Validation
- Created document references resolve correctly
- Sums match across linked documents
- No orphaned references

Failed validation → task pauses, supervisor notified, optional revert.

## Per-Task Autopilot Override

Even if a task type is in Autopilot mode, individual tasks can be marked:
- `force_supervisor_review = True` — this specific task requires approval despite Autopilot
- `confidence_override` — agent self-reports lower confidence on this specific task, drops to Assisted

Used when:
- Task references unusually large amounts (above per-task threshold)
- Task involves a new entity (first-time supplier, first-time customer)
- Task is in a sensitive time window (end-of-month close, audit period)

## DocType: Operations Policy

The autopilot configuration lives in `Friday Operations Policy`:

Fields:
- `business` (Link to Company)
- `default_autopilot_threshold` (Float)
- `default_min_samples` (Int)
- `task_type_overrides` (child table) — per-task-type config
- `autopilot_value_thresholds` (child table) — monetary thresholds per domain
  - "procurement: autopilot only for POs ≤ ₹50,000"
  - "finance: autopilot only for payments ≤ ₹10,000"
- `autopilot_time_windows` (child table) — restrict autopilot to certain hours
  - "no autopilot 22:00-06:00 IST" — overnight only with explicit opt-in
- `autopilot_blackout_dates` (child table) — disable around key dates
  - "no autopilot during financial year close (March 25 - April 5)"

Supervisors tune this policy without code changes.

## Onboarding Trajectory

For a new business:

Week 1 → All task types in Shadow Mode. Agents propose; humans execute.

Week 2 → Move high-frequency, low-risk task types to Assisted. Humans see every step.

Month 2 → Task types with high success start showing as Autopilot candidates. Supervisor promotes one at a time.

Month 3+ → Mature operation: 60-80% of routine task types in Autopilot, 20-40% in Assisted, 5-10% in Manual/Shadow (genuinely complex or rare cases).

## Confidence Reporting

Each agent execution reports a confidence score (0.0-1.0) at completion:

How it's computed:
- Skill calls succeeded vs failed (high weight)
- Validation pass rate
- Memory search hit rate (low hit = uncertain context)
- LLM self-reported confidence (lowest weight, calibration uncertain)
- Anomaly detection results

Confidence appears in War Room summaries. Below-threshold confidence escalates regardless of mode.

## Audit Trail

Every autopilot execution writes to an immutable Audit Log:
- Task ID, agent profile, execution timestamps
- Skills invoked with inputs and outputs
- Documents created/modified
- Validation results
- Confidence score
- Final summary

Audit logs are retained for legal-minimum periods (typically 7-10 years for financial actions).

Supervisors can replay any execution from the audit log to understand exactly what happened.

## Phase 1 Scope

Phase 1 ships:
- Task Type DocType
- Modes: Shadow, Manual, Assisted (no Autopilot in Phase 1)
- Success tracking (executions, success rate, rolling 30d)
- Anomaly detection (output validation, pre-submit validation)
- Audit log

NOT in Phase 1: Autopilot promotion (humans approve every action). Autopilot ships in Phase 2 once we have real-world success data.

## Phase 2 Scope

Phase 2 adds:
- Autopilot mode
- Promotion workflow with supervisor approval
- Automatic demotion + circuit breaker
- Operations Policy DocType with value thresholds, time windows, blackouts
- Confidence reporting in War Room

## Phase 3 Scope

Phase 3 adds:
- Cross-business benchmarking ("similar businesses promote these task types to autopilot")
- ML-based anomaly detection (beyond rule-based validation)
- Per-task confidence calibration based on historical accuracy
- Auto-promotion suggestions with risk scoring

## Open Questions

1. Confidence calibration — how do we know an agent's self-reported 0.95 is actually 0.95 accurate? Calibration model in Phase 3 compares predicted vs actual outcomes.
2. Autopilot during agent version transitions — when we upgrade an agent's underlying model, do we reset success metrics? Yes; trust must be re-earned after model changes.
3. Multi-step task autopilot — if step 3 of 7 fails, do we revert steps 1-2? Defined per task type in the Task Type DocType (rollback_strategy field, Phase 2).
