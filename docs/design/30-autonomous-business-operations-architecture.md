# 30. Autonomous Business Operations Architecture (ERPNext)

## Vision

Friday runs an ERPNext-based SMB's operational backbone autonomously, with human supervisors approving high-stakes decisions and reviewing weekly. The business owner spends time on growth and customers, not on data entry, follow-ups, or reconciliations.

This is Friday's first Phase 1 flagship business validation after the v0.1 framework loop is proven. The foundation of the made-in-India mission remains the same: every Indian SMB owner gets a back-office team that never sleeps.

## The Six-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 6 — Strategic Layer (Owner / Supervisor)                  │
│   Reviews weekly summaries, approves policy changes,            │
│   sets quarterly targets                                        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 5 — Coordinator Agent                                     │
│   Routes cross-domain work, monitors KPIs, escalates anomalies  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4 — Domain Agents (one per ERPNext domain)                │
│   Procurement, Sales, Finance, HR, Production, Inventory        │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3 — Domain Skills                                         │
│   PO creation, GRN posting, payment entry, customer follow-up,  │
│   stock recon, salary slip generation, etc.                     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2 — ERPNext DocType Access (via Frappe ORM/REST)          │
│   Permission-gated; each agent has its own ERPNext user         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1 — ERPNext Site (PostgreSQL + Frappe)                    │
│   The source of truth for the business                          │
└─────────────────────────────────────────────────────────────────┘
```

## Layer 1: ERPNext Site

A standard ERPNext v15 site with the business's chart of accounts, item master, customer/supplier master, warehouses, employees, etc. already configured by the business at onboarding.

No Friday-specific patching of ERPNext is required — Friday operates as a privileged but ordinary user of the ERPNext APIs. This keeps ERPNext upgradable independently.

## Layer 2: ERPNext DocType Access

Every Friday agent has a corresponding ERPNext user (see doc 23). When an agent acts, it acts as itself in ERPNext — audit logs reflect "Procurement Agent" as the document creator, not a generic "Administrator" or "Friday Bot."

Roles are granted minimally:
- Procurement Agent: Purchase Manager, Item Manager (read), Supplier (read/write), Stock User (read)
- Sales Agent: Sales Manager, Customer (read/write), Sales User (read)
- Finance Agent: Accounts User, Payment Entry creation, Journal Entry creation (with approval workflow)
- HR Agent: HR User, Employee (read), Payroll Entry creation (with approval)
- Production Agent: Manufacturing User, Work Order management
- Inventory Agent: Stock Manager, Stock Reconciliation creation

These map directly to ERPNext's existing role permission system. No custom permission engine needed for Layer 2 — Friday's permission gate operates one layer above, deciding whether the agent can attempt the action in the first place.

## Layer 3: Domain Skills

Each domain agent has 15-40 skills covering its standard workflows. Examples:

**Procurement Agent skills:**
- `procurement.create_purchase_order(supplier, items, delivery_date)`
- `procurement.submit_purchase_order(po_name)` — requires approval gate
- `procurement.match_grn_to_po(po_name, grn_data)`
- `procurement.flag_quantity_variance(grn_name)`
- `procurement.follow_up_pending_delivery(po_name)` — drafts message
- `procurement.reorder_low_stock_items()` — generates Material Request

**Sales Agent skills:**
- `sales.draft_quotation(customer, items)`
- `sales.convert_quotation_to_sales_order(quotation_name)` — requires approval
- `sales.flag_overdue_invoice(invoice_name)`
- `sales.send_payment_reminder(customer, invoice_name)` — drafts message
- `sales.update_customer_credit_status(customer)`

**Finance Agent skills:**
- `finance.create_payment_entry(supplier, amount, reference)` — requires approval
- `finance.reconcile_bank_statement(statement_file)`
- `finance.generate_journal_entry(template, params)` — requires approval
- `finance.flag_aged_payable(supplier, age_threshold)`
- `finance.generate_weekly_cashflow_summary()`

**HR Agent skills:**
- `hr.process_attendance_from_log(log_file)`
- `hr.generate_salary_slips_for_period(month)` — requires approval
- `hr.flag_leave_balance_anomaly(employee)`
- `hr.send_onboarding_checklist(employee)` — drafts

**Production Agent skills:**
- `production.create_work_order_from_demand(item, quantity, deadline)`
- `production.flag_bom_cost_increase(bom)`
- `production.generate_production_plan_weekly()`

**Inventory Agent skills:**
- `inventory.run_stock_reconciliation(warehouse)` — requires approval
- `inventory.flag_negative_stock(item, warehouse)`
- `inventory.generate_movement_summary(period)`
- `inventory.detect_slow_moving_items(threshold_days)`

## Layer 4: Domain Agents

Each domain agent is an Agent Role Profile (doc 12) with:
- Identity (system prompt persona)
- Domain tag (doc 29) — e.g. `erpnext-procurement`
- ERPNext user
- Permitted skills (the list above for its domain)
- Memory access scoped to its domain
- Daily / weekly scheduled triggers (see "Operational Cadence" below)

Each runs as a long-lived agent (with heartbeat sessions per doc 15) plus event-driven triggers when ERPNext documents are created/modified that affect its scope.

## Layer 5: Coordinator Agent

The Coordinator agent is a meta-agent that:
1. Observes all domain agents' execution logs
2. Maintains a real-time KPI dashboard (open POs, overdue invoices, stock alerts, etc.)
3. Detects cross-domain anomalies (e.g. high procurement spend + low sales)
4. Escalates to the supervisor (Layer 6) with proposed actions
5. Routes one-off tasks that don't fit a domain to the right specialist or human

The Coordinator has very few direct skills — it mostly delegates. Its system prompt is heavy on operational awareness, light on execution.

## Layer 6: Strategic Layer (Human)

The supervisor is the business owner or operations lead. Their interface is:
- Daily Raven `#friday-ops` channel: morning summary of overnight actions, pending approvals, exceptions
- Weekly War Room review: KPIs, anomalies, proposed policy changes (e.g. "auto-approve POs under ₹5,000 for known suppliers")
- Monthly governance review: agent performance, skill quality, learning loop approvals

The supervisor never needs to log into ERPNext for routine work — that's Friday's job. They log in for strategic configuration and exception handling.

## Operational Cadence

Scheduled jobs (Frappe Scheduler):

**Every 15 minutes:**
- Coordinator polls ERPNext for new documents matching domain agent interests
- Each domain agent processes its inbox (events queued in Redis)

**Hourly:**
- Procurement Agent: reorder check for items below reorder level
- Sales Agent: overdue invoice scan
- Finance Agent: aged payable scan
- Inventory Agent: negative stock check

**Daily (07:00 IST default):**
- Each domain agent posts overnight summary to `#friday-ops`
- Coordinator posts consolidated daily brief to supervisor

**Weekly (Monday 09:00 IST):**
- Domain agents post weekly performance summary
- Coordinator posts weekly KPI dashboard
- Open Skill Drafts surfaced for supervisor review

**Monthly:**
- Domain agents generate trend reports
- Coordinator generates governance review summary

## Approval Gates

Every action with financial or contractual impact passes through an approval gate:
- Purchase Order submission with value > threshold
- Payment Entry submission
- Journal Entry submission
- Salary slip generation
- Customer credit limit changes
- Supplier price agreement changes

Thresholds are configured per business in a `Friday Operations Policy` DocType. Below threshold may become autopilot after enough observed success data (doc 35); before that, actions remain shadow/manual/assisted. Above threshold = War Room approval.

## Event Triggers

Friday subscribes to ERPNext document events via Frappe's `doc_events` hook in `hooks.py`:

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
    # ... etc
}
```

These handlers enqueue events for the relevant domain agent. The agent processes the event in its next heartbeat or immediately if marked urgent.

## Exception Handling

When a domain agent encounters a situation outside its trained scope:
1. It does NOT guess. It pauses and creates an Escalation document.
2. Escalation goes to the supervisor in `#friday-ops` with: full context, what the agent considered, what it's uncertain about, options it sees.
3. Supervisor responds via Raven Message Action (Approve / Reject / Modify / Discuss).
4. The interaction is recorded as a candidate Skill Draft for future automation.

## Onboarding a New Business

Onboarding takes 1-2 weeks:

**Week 1:**
- ERPNext site provisioned with chart of accounts, items, suppliers, customers
- Friday installed and connected
- Domain agents created with the business's specific configuration
- Operations Policy DocType filled (thresholds, approval matrices)
- Supervisor trained on War Room workflows

**Week 2:**
- Shadow mode: Friday observes, drafts, but doesn't execute. Supervisor reviews drafts.
- Day 3-4 of shadow: confidence checked. If high, switch selected task types to assisted execution, not autopilot.
- Day 7: review and decide which task types remain in shadow vs assisted. Autopilot promotion waits for Phase 2+ success data.

This gradual rollout is critical: trust must be earned, not assumed.

## Phase 1 Flagship Scope

After v0.1 ships the governed framework loop, the Phase 1 PO track ships:
- Procurement Agent (full)
- Inventory Agent (read-only + alerts; no autonomous reconciliation yet)
- Coordinator Agent (basic, with KPI dashboard)
- Operations Policy DocType
- Event hook integration
- Daily / weekly cadence

Phase 2 adds:
- Sales Agent
- Finance Agent (with strict approval gates)
- HR Agent
- Production Agent

Phase 3:
- Cross-business pattern library (anonymized)
- Industry-specific templates (manufacturing, distribution, services)
- Multi-currency, multi-company support beyond ERPNext basics

## Success Criterion

In a 7-day dogfood with a real or carefully simulated SMB, Friday executes the Purchase Order workflow (creation, supplier follow-up, GRN matching, variance flagging) with zero unsafe actions, human approval for high-risk actions, and 100% audit traceability.

## Open Questions

1. Multi-language operations: how do we handle Tamil/Hindi/Telugu supplier names and item descriptions in agent prompts? Plan: keep internal reasoning in English, surface localized output. Phase 2 explores native language reasoning.
2. GST/TDS compliance gates: ERPNext handles the calculations; Friday's role is ensuring no submission happens without correct tax classifications. Defined as forbidden-without-validation skill.
3. How does Friday handle ERPNext customizations specific to the business? Skills can be customer-specific; stored in their own domain like `erpnext-custom-{tenant}`.
