# WinbackFlow PoC Architecture

## Objective

Demonstrate a full reactivation loop from CSV ingest to KPI summary without live ESP dependencies.

## System flow

```mermaid
flowchart LR
    csvInput[CSVInputShopifyLike] --> ingest[IngestAndValidate]
    ingest --> segment[LowEngagementSegmentation]
    segment --> recommend[RecommendAndExplain]
    recommend --> approval[ApprovalGate]
    approval --> delivery[SimulatedDelivery]
    delivery --> telemetry[TelemetryAndKPIs]
    telemetry --> demo[InvestorDemoOutputs]
```

## Components

- `openclaw_winback/poc_csv_ingest.py`
  - Parses and validates customer CSV schema.
- `openclaw_winback/segmentation.py`
  - Applies deterministic low-engagement selection rules.
- `openclaw_winback/skills/*.py`
  - Creates recommendation, explanation, delivery, and feedback events.
- `openclaw_winback/pipeline.py`
  - Orchestrates all steps with an approval toggle.
- `tools/experiment_summary.py`
  - Produces investor-facing KPI summary and deterministic output artifact.

## Integration fit in existing stack

- Input: Shopify exports (or any CSV with mapped fields).
- Output: recommendation payloads and delivery simulation logs.
- Future integration points:
  - ESP adapters (Klaviyo/Attentive/Customer.io)
  - Segment/CDP ingestion
  - BI dashboard sync.
