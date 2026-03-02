# B2B Pilot Pack (D2C Brands)

## One-line Offer

Deploy an OpenClaw-powered customer reactivation workflow that helps ecommerce brands convert low-engagement customers with explainable weekly recommendations and measurable outcome telemetry.

## Ideal Buyer

- Head of CRM
- Commercial operations lead
- Lifecycle marketing manager

## Problem Statement

Brands already have ecommerce, CRM, and messaging tools, but campaign execution is fragmented and slow. The pilot focuses on one repeatable workflow that can be operationalized in under 12 weeks:

- identify low-engagement customers
- generate next-best actions
- explain recommendations
- deliver approved outreach
- capture acceptance/rejection signals

## Pilot Scope (8-12 weeks)

- One use case: low-engagement customer reactivation.
- One channel: Telegram-like outbound message format.
- One recommendation cycle per week.
- Human approval required before delivery.
- Full telemetry and KPI reporting.

## Pilot Deliverables

- Configured workflow using OpenClaw-style skills.
- Weekly KPI dashboard extract from telemetry.
- End-of-pilot business impact report.
- Scale plan for second workflow (upsell or post-purchase nurture).

## Commercial Structure

- Pilot fee: fixed implementation + weekly operating review.
- Optional success fee tied to agreed conversion uplift.
- Post-pilot: subscription priced by workflow count + event volume.

## KPI Framework for Buyer Sign-off

- Recommendation action rate uplift versus control.
- Return engagement improvement in target cohort.
- Campaign cycle-time reduction.
- Delivery reliability and latency targets met.

## ROI Model (Template)

Estimated monthly lift:
- `target_fans * incremental_conversion * avg_ticket_margin`

Estimated monthly savings:
- `hours_saved * blended_hourly_cost`

Net impact:
- `(lift + savings) - pilot_or_subscription_cost`

## Demo Evidence (Current Prototype Snapshot)

Generated from:

```bash
python3 run_hybrid_demo.py
python3 tools/experiment_summary.py
```

Current sample output:
- WAU: 4
- Recommendation action rate: 50%
- Delivery count: 4
- P95 delivery latency: 7 ms

Note: These are synthetic MVP telemetry outputs used to validate instrumentation and workflow viability, not production business outcomes.

## Sales Narrative

1. We start with one high-frequency workflow tied to revenue.
2. We keep human approval in the loop to protect brand and compliance.
3. We prove outcomes with telemetry before scaling scope.
4. We expand by adding workflows on the same skill orchestration core.

## Objection Handling

- "We already have CRM automation":
  - This complements CRM by orchestrating data, reasoning, explanation, and feedback loops in one workflow.
- "AI outputs are hard to trust":
  - Every recommendation includes rationale and approval gating.
- "Integration may be heavy":
  - Pilot can start with exported data and one channel, then deepen integrations after ROI proof.
