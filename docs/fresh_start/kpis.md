# KPI Specification (Weeks 1-12)

## Measurement Principles

- Track all KPIs weekly and maintain a fixed definition for 12 weeks.
- Calculate KPI values from telemetry events, not manual estimates.
- Compare against baseline gathered before rollout.
- Use a control cohort whenever available.

## Core KPIs

### 1) Weekly Active Users (WAU)

Definition:
- Count of unique users with at least one `session_started` event in a 7-day window.

Target (Week 6):
- `WAU >= 50` for initial validation cohort.

### 2) Recommendation Action Rate (RAR)

Definition:
- `RAR = accepted_recommendations / shown_recommendations`.
- Count events: `recommendation_accepted` and `recommendation_shown`.

Target (Week 6):
- `RAR >= 20%`.

### 3) Two-Week Retention

Definition:
- Percentage of users active in week N and again in week N+2.
- `Retention_2w = retained_users / cohort_users`.

Target (Week 6):
- `Retention_2w >= 25%`.

### 4) Response Latency (P95)

Definition:
- P95 end-to-end time from `session_started` to `recommendation_delivered`.

Target (Week 6):
- `P95 latency <= 2.0 seconds`.

## Supporting KPIs

- Explanation Read Rate: users expanding/viewing rationale.
- Delivery Success Rate: successful sends / attempted sends.
- Feedback Rate: feedback submitted / recommendation delivered.

## Event Schema (Minimum)

- `session_started`
- `data_ingested`
- `recommendation_shown`
- `recommendation_accepted`
- `recommendation_rejected`
- `recommendation_delivered`
- `feedback_received`
- `error_raised`

Each event must include:
- `event_name`
- `timestamp_utc`
- `workflow_id`
- `user_id`
- `session_id`
- `channel`
- `latency_ms` (when relevant)

## Go/No-Go Thresholds

Week 6 continue gate:
- Pass at least 3/4 core KPIs and no critical reliability failures.

Week 12 scale gate:
- Positive trend in WAU and retention.
- Stable latency and delivery success.
- Evidence of business lift in pilot cohort versus baseline/control.
