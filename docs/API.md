# Cloud FinOps Toolkit - API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Current version: Open (add authentication in production)

## Endpoints

### Cost APIs

#### Get Cost by Service

```http
GET /api/v1/cost/by-service
```

**Parameters:**
- `provider` (required): aws, gcp, or azure
- `start_date` (required): YYYY-MM-DD
- `end_date` (required): YYYY-MM-DD

**Example:**
```bash
curl "http://localhost:8000/api/v1/cost/by-service?provider=aws&start_date=2025-01-01&end_date=2025-01-31"
```

#### Get Cost Summary

```http
GET /api/v1/cost/summary
```

**Parameters:**
- `days` (optional): Number of days to summarize (default: 30)

**Example:**
```bash
curl "http://localhost:8000/api/v1/cost/summary?days=7"
```

#### Get Cost Forecast

```http
GET /api/v1/cost/forecast
```

**Parameters:**
- `days_ahead` (optional): Days to forecast (default: 7)

**Example:**
```bash
curl "http://localhost:8000/api/v1/cost/forecast?days_ahead=14"
```

#### Get Cost by Tag

```http
GET /api/v1/cost/by-tag/{tag_key}
```

**Parameters:**
- `tag_key` (path): Tag key (e.g., Team, Environment)
- `provider` (required): Cloud provider
- `start_date` (required): YYYY-MM-DD
- `end_date` (required): YYYY-MM-DD

**Example:**
```bash
curl "http://localhost:8000/api/v1/cost/by-tag/Team?provider=aws&start_date=2025-01-01&end_date=2025-01-31"
```

### Anomaly Detection APIs

#### Detect Anomalies

```http
GET /api/v1/anomaly/detect
```

**Parameters:**
- `metric` (optional): Metric to analyze (default: cost)
- `sensitivity` (optional): low, medium, high, very_high (default: medium)
- `days` (optional): Days to analyze (default: 30)

**Example:**
```bash
curl "http://localhost:8000/api/v1/anomaly/detect?sensitivity=high&days=14"
```

#### Detect Change Points

```http
GET /api/v1/anomaly/changepoints
```

**Parameters:**
- `metric` (optional): Metric to analyze
- `days` (optional): Days to analyze

**Example:**
```bash
curl "http://localhost:8000/api/v1/anomaly/changepoints?days=30"
```

#### Ensemble Detection

```http
GET /api/v1/anomaly/ensemble
```

Combines multiple detection methods for robust anomaly detection.

**Example:**
```bash
curl "http://localhost:8000/api/v1/anomaly/ensemble?days=30"
```

### Policy APIs

#### Check Budget

```http
POST /api/v1/policy/budget/check
```

**Body:**
```json
{
  "team": "platform",
  "budget_limit": 50000,
  "current_spend": 45000,
  "forecast_spend": 48000
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/policy/budget/check \
  -H "Content-Type: application/json" \
  -d '{"team": "platform", "budget_limit": 50000, "current_spend": 45000}'
```

#### Validate Tags

```http
POST /api/v1/policy/tags/validate
```

**Body:**
```json
{
  "resource_tags": {
    "Environment": "prod",
    "Team": "platform",
    "CostCenter": "12345"
  },
  "environment": "prod"
}
```

### Action APIs

#### Find Idle EC2 Instances

```http
GET /api/v1/action/ec2/idle
```

**Parameters:**
- `cpu_threshold` (optional): Max CPU % (default: 5.0)
- `days_lookback` (optional): Days to analyze (default: 7)

**Example:**
```bash
curl "http://localhost:8000/api/v1/action/ec2/idle?cpu_threshold=5&days_lookback=7"
```

#### Stop EC2 Instances

```http
POST /api/v1/action/ec2/stop
```

**Body:**
```json
{
  "resource_ids": ["i-1234567890abcdef0"],
  "dry_run": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/action/ec2/stop \
  -H "Content-Type: application/json" \
  -d '{"resource_ids": ["i-123"], "dry_run": true}'
```

#### Find Unattached EBS Volumes

```http
GET /api/v1/action/ebs/unattached
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/action/ebs/unattached?days_unattached=7"
```

#### Get Pending Approvals

```http
GET /api/v1/action/approval/pending
```

**Example:**
```bash
curl http://localhost:8000/api/v1/action/approval/pending
```

#### Approve Action

```http
POST /api/v1/action/approval/{request_id}/approve
```

**Parameters:**
- `request_id` (path): Approval request ID
- `approver` (query): Name of approver

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/action/approval/abc-123/approve?approver=john"
```

#### Reject Action

```http
POST /api/v1/action/approval/{request_id}/reject
```

**Parameters:**
- `request_id` (path): Approval request ID
- `approver` (query): Name of approver
- `reason` (query): Rejection reason

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/action/approval/abc-123/reject?approver=john&reason=Not+safe"
```

## Response Formats

All APIs return JSON responses.

**Success Response:**
```json
{
  "status": "success",
  "data": {...}
}
```

**Error Response:**
```json
{
  "detail": "Error message"
}
```

## Interactive API Docs

Visit http://localhost:8000/docs for interactive Swagger UI documentation.
