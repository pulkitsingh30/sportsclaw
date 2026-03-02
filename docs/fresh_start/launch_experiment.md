# Single-Channel Launch Plan (2-Week Validation)

## Channel

Telegram only for MVP validation.

Reason:
- Fastest launch path.
- Low operational overhead.
- Supports rapid recommendation-feedback loops.

## Validation Cohorts

- Cohort A (treatment): users receiving OpenClaw workflow recommendations.
- Cohort B (control): users receiving a static generic message.
- Minimum suggested split: 70/30 to preserve learning speed while retaining a control signal.

## Runbook

### Day 0 (Pre-launch)

- Confirm event telemetry writes to `analytics/events.jsonl`.
- Confirm one recommendation cycle can run end-to-end.
- Confirm human approval gate blocks sends when disabled.

### Week 1

- Launch to first test users.
- Run one recommendation cycle.
- Track daily:
  - delivery success
  - recommendation action rate
  - errors
  - latency
- Fix only critical reliability or clarity issues.

### Week 2

- Run second recommendation cycle with same scope.
- Compare treatment vs control outcomes.
- Capture qualitative feedback from at least 10 users.
- Produce week-2 summary and go/no-go recommendation.

## Instrumentation Checklist

- `session_started`
- `recommendation_shown`
- `recommendation_delivered`
- `recommendation_accepted`
- `recommendation_rejected`
- `feedback_received`
- `error_raised`
- `session_completed`

## Decision at End of Week 2

Continue if:
- Recommendation action rate improves over control.
- P95 latency remains under 2 seconds.
- At least 25% of users return in the second week.

Hold if:
- Latency or reliability blocks user trust.
- Recommendations are consistently rejected.

## Deliverables

- 2-week KPI summary against targets in `docs/fresh_start/kpis.md`.
- List of top 2 drop-off points and fixes for next cycle.
