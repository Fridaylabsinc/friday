# 30 — Autonomous Business Operations (ERPNext)

> See `00-glossary.md` for term definitions.
> See `42-phase-one-authority-contract.md` §6 — the ERPNext PO flagship begins **after** v0.1's governed framework loop is proven. This document covers the post-v0.1 PO track.
> See `41-porting-strategy-hermes-erpnext-raven.md` — DocTypes are ported from ERPNext into Friday Core. The deployment described here additionally installs the full ERPNext app on the Friday bench for the business's operational data.

---

## 1. Vision

Friday runs an ERPNext-based SMB's operational backbone autonomously. Human supervisors approve high-stakes decisions and review weekly. The business owner spends time on growth and customers, not data entry, follow-ups, or reconciliations.

Made-in-India mission carries through: every Indian SMB owner gets a back-office team that never sleeps.

---

## 2. Six-layer architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 6 — Strategic (Owner / Supervisor)                        │
│   Weekly summaries, policy approvals, quarterly targets         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5 — Coordinator Agent                                     │
│   Cross-domain routing, KPI monitoring, anomaly escalation      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4 — Domain Agents                                         │
│   Procurement, Sales, Finance, HR, Production, Inventory        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3 — Domain Skills                                         │
│   PO creation, GRN posting, payment entry, customer follow-up   │
│   stock reconciliation, salary slip generation, etc.            │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2 — ERPNext DocType access via Frappe ORM / REST          │
│   Permission-gated; each agent has its own ERPNext user         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1 — ERPNext site (PostgreSQL + Frappe)                    │
│   Source of truth for the business                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer 1 — ERPNext site

A standard ERPNext installation on the Friday bench, with the business's chart of accounts, item master, customer / supplier master, warehouses, and employees configured by the business at onboarding.

Friday does not patch ERPNext. Friday operates as a privileged but ordinary user of ERPNext APIs. ERPNext remains upgradable independently.

---

## 4. Layer 2 — DocType access

Every Friday agent has its own ERPNext user per `23-secrets-credentials-management.md` §7. When an agent acts, ERPNext audit logs reflect "Procurement Agent" as the document creator — never a generic `Administrator` or `Friday Bot`.

Roles granted minimally:

- **Procurement Agent** — Purchase Manager, Item Manager (read), Supplier (read/write), Stock User (read).
- **Sales Agent** — Sales Manager, Customer (read/write), Sales User (read).
- **Finance Agent** — Accounts User, Payment Entry create, Journal Entry create (with approval workflow).
- **HR Agent** — HR User, Employee (read), Payroll Entry create (with approval).
- **Production Agent** — Manufacturing User, Work Order management.
- **Inventory Agent** — Stock Manager, Stock Reconciliation create.

These map directly to ERPNext's existing role permission system. No custom permission engine at Layer 2; Friday's permission gate operates one layer above, deciding whether the agent may attempt the action at all.

---

## 5. Layer 3 — Domain skills

Each domain agent carries 15–40 skills covering standard workflows.

**Procurement Agent**
- `procurement.create_purchase_order(supplier, items, delivery_date)`
- `procurement.submit_purchase_order(po_name)` — requires approval
- `procurement.match_grn_to_po(po_name, grn_data)`
- `procurement.flag_quantity_variance(grn_name)`
- `procurement.follow_up_pending_delivery(po_name)` — drafts message
- `procurement.reorder_low_stock_items()` — generates Material Request

**Sales Agent**
- `sales.draft_quotation(customer, items)`
- `sales.convert_quotation_to_sales_order(quotation_name)` — requires approval
- `sales.flag_overdue_invoice(invoice_name)`
- `sales.send_payment_reminder(customer, invoice_name)` — drafts message
- `sales.update_customer_credit_status(customer)`

**Finance Agent**
- `finance.create_payment_entry(supplier, amount, reference)` — requires approval
- `finance.reconcile_bank_statement(statement_file)`
- `finance.generate_journal_entry(template, params)` — requires approval
- `finance.flag_aged_payable(supplier, age_threshold)`
- `finance.generate_weekly_cashflow_summary()`

**HR Agent**
- `hr.process_attendance_from_log(log_file)`
- `hr.generate_salary_slips_for_period(month)` — requires approval
- `hr.flag_leave_balance_anomaly(employee)`
- `hr.send_onboarding_checklist(employee)` — drafts

**Production Agent**
- `production.create_work_order_from_demand(item, quantity, deadline)`
- `production.flag_bom_cost_increase(bom)`
- `production.generate_production_plan_weekly()`

**Inventory Agent**
- `inventory.run_stock_reconciliation(warehouse)` — requires approval
- `inventory.flag_negative_stock(item, warehouse)`
- `inventory.generate_movement_summary(period)`
- `inventory.detect_slow_moving_items(threshold_days)`

---

## 6. Layer 4 — Domain agents

Each domain agent is an Agent Role Profile (per `12-refinement-agent-roles-and-features.md`) with:

- Identity (system prompt persona).
- Domain tag (`29-domain-specific-self-learning.md`) — e.g. `erpnext-procurement`.
- ERPNext user (`23-secrets-credentials-management.md` §7).
- Permitted skills (the list above for its domain).
- Memory access scoped to its domain.
- Daily / weekly scheduled triggers (see §8).

Long-lived with heartbeat sessions per `15-openclaw-insights-friday-refinements.md` Insight 2, plus event-driven triggers when ERPNext documents in the agent's scope are created or modified.

---

## 7. Layer 5 — Coordinator agent

A meta-agent that:

1. Observes all domain agents' execution logs.
2. Maintains a real-time KPI dashboard (open POs, overdue invoices, stock alerts).
3. Detects cross-domain anomalies (e.g. high procurement spend + low sales).
4. Escalates to the supervisor (Layer 6) with proposed actions.
5. Routes one-off tasks that do not fit a domain to the right specialist or human.

Few direct skills — mostly delegates. The system prompt is heavy on operational awareness, light on execution.

---

## 8. Layer 6 — Strategic (human)

The supervisor is the business owner or operations lead. Interfaces:

- **Daily** Raven `#friday-ops` channel — morning summary of overnight actions, pending approvals, exceptions.
- **Weekly** War Room review — KPIs, anomalies, proposed policy changes (e.g. "auto-approve POs under ₹5,000 for known suppliers").
- **Monthly** governance review — agent performance, skill quality, learning-loop approvals.

The supervisor does not log into ERPNext for routine work — that is Friday's job. They log in for strategic configuration and exception handling.

---

## 9. Operational cadence

Frappe Scheduler jobs:

**Every 15 minutes**
- Coordinator polls ERPNext for new documents matching domain agent interests.
- Each domain agent processes its inbox (events queued in Redis).

**Hourly**
- Procurement — reorder check for items below reorder level.
- Sales — overdue invoice scan.
- Finance — aged payable scan.
- Inventory — negative stock check.

**Daily (07:00 IST default)**
- Each domain agent posts overnight summary to `#friday-ops`.
- Coordinator posts consolidated daily brief to supervisor.

**Weekly (Monday 09:00 IST)**
- Domain agents post weekly performance summaries.
- Coordinator posts the weekly KPI dashboard.
- Open Skill Drafts surfaced for supervisor review.

**Monthly**
- Domain agents generate trend reports.
- Coordinator generates a governance review summary.

---

## 10. Approval gates

Every action with financial or contractual impact passes through an approval gate:

- Purchase Order submission with value > threshold.
- Payment Entry submission.
- Journal Entry submission.
- Salary slip generation.
- Customer credit limit changes.
- Supplier price agreement changes.

Thresholds configured per business in a `Friday Operations Policy` DocType. Below threshold may become autopilot once enough success data accumulates (`35-autopilot-mode-autonomous-execution.md`); before that, actions remain shadow / manual / assisted. Above threshold always requires War Room approval.

---

## 11. Event triggers

Friday subscribes to ERPNext document events via `doc_events` in `hooks.py`:

```python
doc_events = {
    "Purchase Order": {
        "on_submit": "friday.erpnext_hooks.po_submitted",
        "on_cancel": "friday.erpnext_hooks.po_cancelled",
    },
    "Sales Invoice": {
        "on_submit": "friday.erpnext_hooks.invoice_submitted",
    },
    "Stock Entry": {
        "on_submit": "friday.erpnext_hooks.stock_movement",
    },
    # ...
}
```

Handlers enqueue events for the relevant domain agent. The agent processes in its next heartbeat, or immediately if marked urgent.

---

## 12. Exception handling

When a domain agent encounters a situation outside its scope:

1. It does not guess. It pauses and creates an Escalation document.
2. The escalation lands in `#friday-ops` with full context: what the agent considered, what it is uncertain about, options it sees.
3. Supervisor responds via Raven Message Action (Approve / Reject / Modify / Discuss).
4. The interaction is recorded as a candidate Skill Draft for future automation.

---

## 13. Onboarding a new business

Onboarding takes 1–2 weeks.

**Week 1**
- ERPNext site provisioned with chart of accounts, items, suppliers, customers.
- Friday installed and connected.
- Domain agents created with the business's configuration.
- Friday Operations Policy DocType filled (thresholds, approval matrices).
- Supervisor trained on War Room workflows.

**Week 2**
- **Shadow mode** — Friday observes, drafts, but does not execute. Supervisor reviews drafts.
- Day 3–4 — confidence checked. If high, selected task types move to assisted execution (not autopilot).
- Day 7 — decide which task types remain shadow vs. assisted. Autopilot promotion waits for Phase 2+ success data.

Trust is earned, not assumed.

---

## 14. PO flagship scope

After v0.1 ships the governed framework loop, the Phase 1 PO track ships:

- Procurement Agent (full).
- Inventory Agent (read-only + alerts; no autonomous reconciliation yet).
- Coordinator Agent (basic, with KPI dashboard).
- Friday Operations Policy DocType.
- Event-hook integration.
- Daily / weekly cadence.

**Phase 2** adds Sales, Finance (strict approval gates), HR, and Production agents.

**Phase 3** adds cross-business pattern library (anonymised), industry templates (manufacturing, distribution, services), multi-currency, multi-company.

---

## 15. Success criterion

In a 7-day dogfood with a real or carefully simulated SMB, Friday executes the Purchase Order workflow (creation, supplier follow-up, GRN matching, variance flagging) with zero unsafe actions, human approval for high-risk actions, and 100% audit traceability.

---

## 16. Open questions

- Multi-language operations — Tamil / Hindi / Telugu supplier names and item descriptions in agent prompts. Plan: internal reasoning in English, localised output. Phase 3 explores native-language reasoning.
- GST / TDS compliance gates — ERPNext handles calculations; Friday's role is ensuring no submission happens without correct tax classifications. Defined as a forbidden-without-validation skill.
- Business-specific ERPNext customisations — Skills can be customer-specific, stored in their own domain like `erpnext-custom-{tenant}`.
