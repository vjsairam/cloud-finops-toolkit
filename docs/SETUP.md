# Cloud FinOps Toolkit - Setup Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Cloud provider credentials (AWS, GCP, and/or Azure)
- OPA (Open Policy Agent) - optional but recommended

## Quick Start with Docker

1. **Clone the repository and configure**

```bash
cd cloud-finops-toolkit
cp config.yaml.example config.yaml
# Edit config.yaml with your cloud credentials
```

2. **Start all services**

```bash
docker-compose up -d
```

This will start:
- FastAPI backend (port 8000)
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Grafana dashboards (port 3000)
- Prometheus metrics (port 9090)
- OPA policy engine (port 8181)

3. **Access the services**

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## Manual Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Cloud Credentials

#### AWS

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

#### GCP

```bash
# Download service account JSON from GCP Console
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

#### Azure

```bash
# Option 1: Azure CLI
az login

# Option 2: Service Principal
export AZURE_TENANT_ID=xxx
export AZURE_CLIENT_ID=xxx
export AZURE_CLIENT_SECRET=xxx
```

### 4. Initialize Database

```bash
# Using PostgreSQL
createdb finops

# Or using SQLite for development
# No setup needed - will auto-create
```

### 5. Install OPA (Optional)

```bash
# macOS
brew install opa

# Linux
curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x /usr/local/bin/opa

# Verify
opa version
```

### 6. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

## Cloud Provider Setup

### AWS Cost Explorer & CUR

1. Enable Cost Explorer in AWS Console
2. Create S3 bucket for Cost and Usage Reports
3. Enable CUR in Billing preferences
4. Update `config.yaml` with bucket name

### GCP BigQuery Billing Export

1. Enable BigQuery Billing Export
2. Create dataset (e.g., `billing_export`)
3. Grant service account `BigQuery Data Viewer` role
4. Update `config.yaml` with project/dataset info

### Azure Cost Management

1. Ensure subscription has Cost Management access
2. Create service principal with Reader access
3. Assign service principal to subscription
4. Update `config.yaml` with credentials

## Grafana Dashboard Setup

1. Login to Grafana (http://localhost:3000)
2. Add Prometheus data source: http://prometheus:9090
3. Import dashboards from `dashboards/grafana/`
4. Configure refresh intervals

## Verification

```bash
# Test API
curl http://localhost:8000/health

# Test AWS connection
python -c "from ingestion.connectors import AWSCostConnector; c = AWSCostConnector(); print('AWS OK')"

# Test OPA
opa eval -d policies/rego/budget_policy.rego "data.budget.allow" --input <(echo '{"budget": {"limit": 1000}, "current_spend": 500}')
```

## Troubleshooting

### Connection Issues

- Check cloud credentials are valid
- Verify network connectivity to cloud APIs
- Check firewall/security group settings

### Database Issues

- Ensure PostgreSQL is running: `docker-compose ps`
- Check connection string in config.yaml
- Verify database exists: `psql -l`

### Permission Issues

- AWS: Ensure IAM user has `ce:GetCostAndUsage` permission
- GCP: Ensure service account has BigQuery access
- Azure: Ensure subscription has Cost Management enabled

## Next Steps

1. Review `docs/RUNBOOK.md` for operational procedures
2. Customize budgets in `config.yaml`
3. Set up Slack/email notifications
4. Configure tag governance policies
5. Schedule cost ingestion jobs
