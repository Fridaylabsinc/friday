# 36. Analytical and Predictive Agents

## Why Separate from Operational Agents

Operational agents (Procurement, Sales, Finance, etc.) handle transactional work: creating documents, sending follow-ups, posting entries. Their cognitive load is "do the next correct thing."

Analytical and Predictive agents have a different job: examine data over time, identify patterns, forecast outcomes, surface insights. Their cognitive load is "what does this data mean, and what's coming?"

Mixing these in one agent profile produces mediocre results in both modes. Separate profiles let each specialize.

## Profile 1: Trend Analyst Agent

**Identity:** A business analyst who reads operational data and identifies trends.

**Inputs:**
- ERPNext transactional data (sales orders, invoices, POs, GRNs)
- Memory of past trends and anomalies
- Industry benchmarks (if configured)

**Outputs:**
- Weekly trend reports (revenue, expense, gross margin, inventory turns, DSO, DPO)
- Anomaly callouts (e.g. "Customer X's order frequency dropped 40% over last 30 days")
- Comparative analyses (this month vs last, this quarter vs same quarter last year)

**Skills:**
- `analytics.sales_trend(period, dimensions)` — slice/dice sales data
- `analytics.expense_trend(period, account_filter)`
- `analytics.customer_segmentation(criteria)`
- `analytics.cohort_analysis(metric, cohort_definition)`
- `analytics.detect_anomaly(metric, lookback, threshold)`
- `analytics.compare_periods(metric, period_a, period_b)`
- `analytics.generate_report(template, data, period)`

**Cadence:**
- Daily morning brief: notable changes in last 24h
- Weekly report: end of week (Friday evening IST)
- Monthly deep-dive: first business day of new month

**Output destination:** Raven `#friday-analytics` channel + emailed PDF to supervisor.

## Profile 2: Demand Forecaster Agent

**Identity:** A demand planner who predicts what's coming.

**Inputs:**
- Historical sales by item, customer, region
- Seasonality patterns
- External signals if configured (commodity prices, weather, holidays)

**Outputs:**
- Next-30/60/90 day demand forecasts by item
- Reorder recommendations (feed to Procurement Agent)
- Risk flags (e.g. "expected stockout for Item A in 12 days at current consumption")

**Skills:**
- `forecast.demand_by_item(item, horizon)`
- `forecast.demand_by_customer(customer, horizon)`
- `forecast.stockout_risk(item, warehouse, horizon)`
- `forecast.seasonality_decompose(item, lookback_years)`
- `forecast.reorder_recommendation(item, lead_time, safety_stock)`

**Methods used:**
- Simple exponential smoothing for stable items
- ARIMA / SARIMA for seasonal patterns
- Prophet (Facebook's library) for items with holidays / weekly patterns
- Held-out validation: model accuracy reported with each forecast

The agent doesn't pick the method blindly — it tests two or three and chooses the one with best held-out error on that specific item's history.

**Forecast cadence:**
- Weekly refresh of all item forecasts
- Daily refresh of high-velocity SKUs (≥5 movements/day)
- On-demand for ad-hoc queries

## Profile 3: Cash Flow Forecaster Agent

**Identity:** A finance analyst projecting cash position.

**Inputs:**
- Receivables aging
- Payables schedule
- Standing orders / recurring revenue
- Payment terms by customer
- Historical collection patterns per customer

**Outputs:**
- 30/60/90 day cash flow projection
- Concentration risk flags (e.g. "60% of receivables concentrated in 3 customers")
- Recommended actions ("collect from Customer X to avoid Friday shortfall")

**Skills:**
- `cashflow.project(horizon_days)`
- `cashflow.customer_payment_behavior(customer)` — historical patterns
- `cashflow.scenario_analysis(scenarios)` — best/base/worst case
- `cashflow.concentration_risk()`
- `cashflow.action_recommend(target_balance)`

**Cadence:**
- Daily morning: 30-day cash projection with overnight changes highlighted
- Weekly: 90-day projection
- On significant event (large invoice, large bill): refresh and flag impact

## Profile 4: Performance Insights Agent

**Identity:** An ops-focused analyst examining Friday's own performance.

**Inputs:**
- Execution Logs across all domain agents
- Approval/rejection rates
- Skill success rates per task type
- Latency distributions
- Cost (LLM token usage) per task type

**Outputs:**
- Weekly Friday performance report
- Skill candidates for autopilot promotion (with data)
- Bottleneck callouts (slow skills, frequently-failing patterns)
- Cost optimization suggestions

**Skills:**
- `friday_perf.skill_success_rate(skill, period)`
- `friday_perf.execution_latency_distribution(profile, period)`
- `friday_perf.cost_attribution(domain, period)`
- `friday_perf.identify_autopilot_candidates()`
- `friday_perf.bottleneck_analysis()`

**Cadence:**
- Weekly: comprehensive Friday performance report
- Monthly: governance review prep (skill quality, learning loop outputs, costs)

This agent is the meta-feedback loop on Friday itself.

## Architecture Pattern

Analytical agents do NOT modify ERPNext data. They are read-only with respect to the operational system. Their outputs are:
1. Reports (PDF, markdown, Raven posts)
2. Memory entries (Reflective category — "we learned X")
3. Recommendations to operational agents (e.g. Demand Forecaster → Procurement Agent reorder skill)

This separation prevents an analytical bug from accidentally creating spurious POs or Payment Entries.

## Tooling

Analytical agents need different tooling than operational ones:
- **Compute environment:** access to numpy, pandas, statsmodels, prophet, scikit-learn
- **Sandboxing:** longer execution timeout (forecasting can take 30-120 seconds)
- **Memory budget:** higher (working with dataframes)
- **GPU access:** not required Phase 1; some advanced models in Phase 3 may use GPU sandboxes

These differences are encoded in the Sandbox profile (doc 24) used by analytical agents.

## Skill Library: Analytics Primitives

A shared library of analytical primitives all four profiles use:

- `sql_query(query, params, max_rows)` — read-only ERPNext SQL with safety checks
- `dataframe_describe(df)` — quick stats
- `dataframe_groupby_aggregate(df, by, agg)` — common pandas pattern
- `timeseries_resample(series, freq)` — for forecasting prep
- `regression_fit(X, y, model_type)` — wrapper around sklearn
- `arima_fit(series, order)` — wrapper around statsmodels
- `prophet_fit(df, holidays)` — wrapper around prophet
- `chart_render(data, chart_type, file_path)` — matplotlib/plotly output

These primitives are skill-level building blocks; agents compose them into higher-level workflows.

## Output Storage

Reports generated by analytical agents are stored in a `Friday Analytics Report` DocType:
- `report_type` (Select: Trend, Demand Forecast, Cash Flow, Performance Insights, Custom)
- `period_start`, `period_end`
- `generated_at`
- `generated_by_agent` (Link to Agent Role Profile)
- `summary` (Text)
- `attachments` (File field — PDF, CSV, charts)
- `key_findings` (Long Text)
- `recommendations` (Long Text)

Searchable, archived, linkable from Wiki pages and Memory entries.

## Integration with Operational Agents

Analytical agents produce recommendations. Operational agents consume them.

Example flow:
1. Demand Forecaster predicts stockout of Item A in 12 days.
2. Posts recommendation to `#friday-procurement` channel with reorder data.
3. Procurement Agent picks up the recommendation in next heartbeat.
4. Drafts a Purchase Order to preferred supplier.
5. Routes through normal approval / autopilot gate.

The recommendation is not a command. The operational agent evaluates context (cash position, supplier capacity, current PO pipeline) before acting.

## Phase 1 Scope

Phase 1 ships:
- Trend Analyst Agent (basic) — sales and expense trend reports only
- Skill library: SQL queries, dataframe ops, simple chart rendering
- Friday Analytics Report DocType

Phase 2 adds:
- Demand Forecaster Agent (exponential smoothing + ARIMA)
- Cash Flow Forecaster Agent
- Performance Insights Agent
- Recommendation flow to operational agents

Phase 3 adds:
- Prophet integration for seasonality
- ML-based anomaly detection
- Industry benchmark integration
- External signal ingestion (commodity prices, weather)

## Open Questions

1. Should analytical agents have their own ERPNext user with read-only role? Yes — cleaner audit and stricter least-privilege.
2. How to handle very large queries (e.g. 5-year SKU history with millions of rows)? Query budget enforcement at the skill level; pagination patterns; pre-aggregation tables in Phase 2.
3. Model retraining cadence for forecasts? Weekly retrain; daily score-only.
4. Confidence intervals on forecasts — how to surface them in War Room without overwhelming supervisors? Default to point forecast + risk bands; full uncertainty visible in detail view only.
