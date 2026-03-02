# WinbackFlow PoC Demo Script (5 Minutes)

## Minute 0-1: Context

"WinbackFlow helps brands recover low-engagement customers with explainable, approval-first recommendations."

Highlight:

- Existing tools can send campaigns, but teams still struggle with segmentation and clear attribution.
- This PoC shows the full decision loop in a deterministic way.

## Minute 1-2: Run the PoC

Command:

```bash
python3 run_poc_demo.py --approved true
```

Narrate:

- Customer data is loaded from Shopify-like CSV.
- Low-engagement customers are selected using explicit rules.
- Recommendations are generated with confidence and rationale.

## Minute 2-3: Approval and Delivery

Explain:

- Approval gate is explicit (`--approved true|false`).
- Delivery is simulated with clear customer/action payloads.
- No message is sent when approval is off.

Optional command:

```bash
python3 run_poc_demo.py --approved false
```

## Minute 3-4: KPI Summary

Call out:

- targeted customers
- recommendation action rate
- accepted/rejected split
- delivery latency
- projected recovered revenue
- `analytics/poc_summary.json` generated for deterministic replay

## Minute 4-5: Close and Next Step

"This proves we can move from data to measured reactivation decisions quickly. The next step is replacing simulated delivery with a live ESP adapter for a 14-day customer pilot."
