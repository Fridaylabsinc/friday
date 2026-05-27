# 36 — Analytical and Predictive Agents

> See `00-glossary.md` for term definitions.
> Phase: not in v0.1 per `42-phase-one-authority-contract.md` §4. Phase 2+. Even the Phase 2 scope below is conditional on Phase 1 governance loop maturity.

---

## 1. Why separate from operational agents

Operational agents (Procurement, Sales, Finance) handle transactional work: creating documents, sending follow-ups, posting entries. Their cognitive load is "do the next correct thing".

Analytical and predictive agents have a different job: examine data over time, identify patterns, forecast outcomes, surface insights. Their cognitive load is "what does this data mean, and what is coming?"

Mixing produces mediocre results in both modes. Separate profiles let each specialise.

---

## 2. Trend Analyst Agent

**Identity:** A business analyst who reads operational data and identifies trends.

**Inputs**
- ERPNext transactional data (sales orders, invoices, POs, GRNs).
- Memory of past trends and anomalies.
- Industry benchmarks if configured.

**Outputs**
- Weekly trend reports (revenue, expense, gross margin, inventory turns, DSO, DPO).
- Anomaly callouts (e.g. "Customer X's order frequency dropped 40% over 30 days").
- Comparative analyses (this month vs. last; this quarter vs. same quarter last year).

**Skills**
- `analytics.sales_trend(period, dimensions)` — slice/dice sales data.
- `analytics.expense_trend(period, account_filter)`.
- `analytics.customer_segmentation(criteria)`.
- `analytics.cohort_analysis(metric, cohort_definition)`.
- `analytics.detect_anomaly(metric, lookback, threshold)`.
- `analytics.compare_periods(metric, period_a, period_b)`.
- `analytics.generate_report(template, data, period)`.

**Cadence**
- Daily morning brief — notable changes in last 24h.
- Weekly report — end of week (Friday evening IST).
- Monthly deep-dive — first business day of the new month.

**Destination:** Raven `#friday-analytics` channel + emailed PDF to supervisor.

---

## 3. Demand Forecaster Agent

**Identity:** A demand planner who predicts what is coming.

**Inputs**
- Historical sales by item, customer, region.
- Seasonality patterns.
- External signals if configured (commodity prices, weather, holidays).

**Outputs**
- Next-30/60/90 day demand forecasts by item.
- Reorder recommendations (consumed by Procurement Agent).
- Risk flags ("expected stockout for Item A in 12 days at current consumption").

**Skills**
- `forecast.demand_by_item(item, horizon)`.
- `forecast.demand_by_customer(customer, horizon)`.
- `forecast.stockout_risk(item, warehouse, horizon)`.
- `forecast.seasonality_decompose(item, lookback_years)`.
- `forecast.reorder_recommendation(item, lead_time, safety_stock)`.

**Methods**
- Simple exponential smoothing for stable items.
- ARIMA / SARIMA for seasonal patterns.
- Prophet for items with holidays / weekly patterns.
- Held-out validation; model accuracy reported with each forecast.

The agent tests two or three methods and chooses the lowest held-out error on that specific item's history.

**Cadence**
- Weekly refresh of all item forecasts.
- Daily refresh of high-velocity SKUs (≥ 5 movements/day).
- On-demand for ad-hoc queries.

---

## 4. Cash Flow Forecaster Agent

**Identity:** A finance analyst projecting cash position.

**Inputs**
- Receivables aging.
- Payables schedule.
- Standing orders / recurring revenue.
- Payment terms by customer.
- Historical collection patterns per customer.

**Outputs**
- 30/60/90 day cash flow projection.
- Concentration risk flags ("60% of receivables concentrated in 3 customers").
- Recommended actions ("collect from Customer X to avoid Friday shortfall").

**Skills**
- `cashflow.project(horizon_days)`.
- `cashflow.customer_payment_behavior(customer)`.
- `cashflow.scenario_analysis(scenarios)` — best / base / worst case.
- `cashflow.concentration_risk()`.
- `cashflow.action_recommend(target_balance)`.

**Cadence**
- Daily morning — 30-day projection with overnight changes highlighted.
- Weekly — 90-day projection.
- On significant event (large invoice, large bill) — refresh and flag impact.

---

## 5. Performance Insights Agent

**Identity:** An ops-focused analyst examining Friday's own performance.

**Inputs**
- Execution Logs across all domain agents.
- Approval / rejection rates.
- Skill success rates per task type.
- Latency distributions.
- Cost (LLM token usage) per task type.

**Outputs**
- Weekly Friday performance report.
- Skill candidates for autopilot promotion (with data — per `35-autopilot-mode-autonomous-execution.md`).
- Bottleneck callouts (slow skills, frequently-failing patterns).
- Cost optimisation suggestions.

**Skills**
- `friday_perf.skill_success_rate(skill, period)`.
- `friday_perf.execution_latency_distribution(profile, period)`.
- `friday_perf.cost_attribution(domain, period)`.
- `friday_perf.identify_autopilot_candidates()`.
- `friday_perf.bottleneck_analysis()`.

**Cadence**
- Weekly — comprehensive Friday performance report.
- Monthly — governance review prep (skill quality, learning loop output, cost).

The meta-feedback loop on Friday itself.

---

## 6. Architectural rule — read-only

Analytical agents do **not** modify ERPNext data. They are read-only with respect to the operational system. Outputs are:

1. Reports (PDF, markdown, Raven posts).
2. Memory entries (`Reflective` category — "we learned X").
3. Recommendations to operational agents (e.g. Demand Forecaster → Procurement Agent reorder skill).

This separation prevents an analytical bug from creating spurious POs or Payment Entries.

---

## 7. Sandbox tooling

Analytical agents need different sandbox configuration than operational ones, per `24-sandbox-architecture-implementation.md`:

- Compute environment with numpy, pandas, statsmodels, prophet, scikit-learn.
- Longer execution timeout (forecasting can take 30–120 seconds).
- Higher memory budget (working with dataframes).
- GPU access not required Phase 2; some Phase 3 advanced models may use GPU sandboxes.

Encoded in the sandbox profile for analytical agents.

---

## 8. Analytics primitives

A shared skill library all four profiles consume:

- `sql_query(query, params, max_rows)` — read-only ERPNext SQL with safety checks.
- `dataframe_describe(df)`.
- `dataframe_groupby_aggregate(df, by, agg)`.
- `timeseries_resample(series, freq)`.
- `regression_fit(X, y, model_type)` — sklearn wrapper.
- `arima_fit(series, order)` — statsmodels wrapper.
- `prophet_fit(df, holidays)` — Prophet wrapper.
- `chart_render(data, chart_type, file_path)` — matplotlib/plotly output.

Building blocks; agents compose them into higher-level workflows.

---

## 9. Friday Analytics Report DocType

| Field | Type |
|---|---|
| `report_type` | Select — Trend / Demand Forecast / Cash Flow / Performance Insights / Custom |
| `period_start`, `period_end` | Date |
| `generated_at` | Datetime |
| `generated_by_agent` | Link → Agent Role Profile |
| `summary` | Text |
| `attachments` | File — PDF, CSV, charts |
| `key_findings` | Long Text |
| `recommendations` | Long Text |

Searchable, archived, linkable from Wiki pages and Memory entries.

---

## 10. Operational integration

Analytical agents produce recommendations. Operational agents consume them.

```
1. Demand Forecaster predicts stockout of Item A in 12 days.
2. Posts recommendation to #friday-procurement with reorder data.
3. Procurement Agent picks it up in next heartbeat.
4. Drafts a Purchase Order to the preferred supplier.
5. Routes through the normal approval / autopilot gate.
```

The recommendation is not a command. The operational agent evaluates context (cash position, supplier capacity, current PO pipeline) before acting.

---

## 11. Phasing

| Phase | Scope |
|---|---|
| 1 (v0.1) | Not in scope per `42-phase-one-authority-contract.md` §4 |
| 2 | Trend Analyst Agent (basic — sales and expense trend reports); analytics primitives skill library (SQL, dataframe ops, simple chart rendering); Friday Analytics Report DocType |
| 3 | Demand Forecaster (exponential smoothing + ARIMA); Cash Flow Forecaster; Performance Insights Agent; recommendation flow to operational agents |
| 4 | Prophet integration for seasonality; ML-based anomaly detection; industry benchmark integration; external signal ingestion (commodity prices, weather) |

---

## 12. Open questions

- Analytical agents with their own ERPNext user (read-only role) — cleaner audit and stricter least-privilege.
- Very large queries (e.g. 5-year SKU history, millions of rows) — query budget at skill level; pagination; pre-aggregation tables.
- Forecast model retraining cadence — weekly retrain, daily score-only.
- Confidence intervals on forecasts in War Room — default point forecast + risk bands; full uncertainty in detail view.
