# WinbackFlow PoC Data Schema

This folder contains deterministic, Shopify-like CSV inputs for the investor demo.

## `customers.csv` fields

- `customer_id`: unique customer key
- `email`: customer email
- `first_name`, `last_name`: profile names
- `signup_date`: first seen date (`YYYY-MM-DD`)
- `last_order_date`: most recent order date (`YYYY-MM-DD`)
- `total_orders`: lifetime order count
- `total_spend`: lifetime spend in base currency
- `avg_order_value`: average order value
- `email_engagement_score`: 0.0 to 1.0
- `sms_engagement_score`: 0.0 to 1.0
- `preferred_channel`: `email` or `sms`
- `primary_category`: dominant purchase category

## `orders.csv` fields

- `order_id`: unique order key
- `customer_id`: link to `customers.csv`
- `order_date`: transaction date (`YYYY-MM-DD`)
- `order_total`: order value
- `discount_used`: `true` or `false`
- `category`: product category
- `purchase_channel`: source channel

## Segmentation assumptions

Low-engagement candidates satisfy any of:

- days since last order >= 90
- engagement score < 0.25
- total orders <= 2
