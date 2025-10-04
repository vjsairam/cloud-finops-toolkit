# Cloud FinOps Toolkit - Architecture

## Overview

The Cloud FinOps Toolkit is a multi-cloud cost management platform built with a modular architecture for scalability and extensibility.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Providers                          │
│          AWS  │  GCP  │  Azure  │  Kubernetes                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Ingestion Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │AWS CUR   │  │GCP BigQ  │  │Azure CM  │                  │
│  │Connector │  │Connector │  │Connector │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Schema Normalization                            │
│              (FOCUS Standard)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Warehouse                              │
│          PostgreSQL / BigQuery / Athena                      │
└──────────┬──────────────────────┬──────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────────────┐
│ Allocation       │   │  Anomaly Detection Engine            │
│ & Unit Economics │   │  ┌─────────┐  ┌──────────────┐      │
│                  │   │  │Baseline │  │Change-point  │      │
│ - dbt models     │   │  │Detector │  │Detector      │      │
│ - Cost per       │   │  └─────────┘  └──────────────┘      │
│   request/tenant │   │  ┌─────────────────────────┐        │
│                  │   │  │Ensemble Detector        │        │
│                  │   │  └─────────────────────────┘        │
└──────────────────┘   └──────────────┬───────────────────────┘
                                       │
                       ┌───────────────┴───────────────┐
                       ▼                               ▼
┌──────────────────────────────────┐  ┌─────────────────────────┐
│   Policy Engine (OPA)            │  │  Action Engine          │
│   ┌──────────┐  ┌──────────┐    │  │  ┌──────────────────┐  │
│   │Budget    │  │Tag       │    │  │  │EC2 Remediation   │  │
│   │Policies  │  │Governance│    │  │  │EBS Remediation   │  │
│   └──────────┘  └──────────┘    │  │  │RDS Remediation   │  │
│                                  │  │  └──────────────────┘  │
└──────────────────┬───────────────┘  └───────┬─────────────────┘
                   │                          │
                   ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Approval Engine                           │
│                 (Manual + Auto-approval)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│   /cost  │  /anomaly  │  /policy  │  /action                │
└──────────┬──────────────────────┬──────────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────────────┐
│   Grafana        │   │  Notifications                        │
│   Dashboards     │   │  ┌────────┐  ┌──────┐  ┌──────────┐ │
│                  │   │  │Slack   │  │Email │  │PagerDuty │ │
│                  │   │  └────────┘  └──────┘  └──────────┘ │
└──────────────────┘   └──────────────────────────────────────┘
```

## Data Flow

### 1. Ingestion Pipeline

**Daily Schedule (2 AM UTC):**
1. Pull cost data from cloud providers
2. Normalize to FOCUS schema
3. Enrich with tags
4. Load into data warehouse
5. Update allocation models

### 2. Anomaly Detection Pipeline

**Hourly:**
1. Fetch latest cost data
2. Run baseline detector
3. Run changepoint detector
4. Combine results in ensemble
5. Generate alerts for anomalies
6. Send notifications

### 3. Policy Enforcement

**On-Demand (CI/CD):**
1. Deployment triggers policy check
2. OPA evaluates budget/tag policies
3. Gate deployment if policy violated
4. Log policy decision

### 4. Remediation Workflow

**Weekly + On-Demand:**
1. Identify optimization opportunities
2. Create remediation plan
3. Request approval (auto or manual)
4. Execute if approved
5. Track savings realized

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **ORM**: SQLAlchemy

### Data Processing
- **ETL**: Python + Pandas
- **Warehouse**: PostgreSQL / BigQuery
- **Allocation**: dbt (data build tool)

### Anomaly Detection
- **Libraries**: ruptures, Prophet, scikit-learn
- **Methods**: Statistical baselines, PELT changepoint detection

### Policy as Code
- **Engine**: OPA (Open Policy Agent)
- **Language**: Rego

### Observability
- **Metrics**: Prometheus
- **Dashboards**: Grafana
- **Logging**: Python logging + JSON formatter

### Cloud SDKs
- **AWS**: boto3
- **GCP**: google-cloud-bigquery
- **Azure**: azure-mgmt-costmanagement

### Infrastructure
- **Containers**: Docker
- **Orchestration**: Docker Compose (Kubernetes ready)

## Deployment Patterns

### Development
- Docker Compose with local PostgreSQL
- SQLite for quick testing
- Dry-run mode for all actions

### Production
- Kubernetes deployment
- Managed database (RDS/Cloud SQL)
- Redis cluster for caching
- High availability setup

## Security

### Data Protection
- No PII in cost data
- Encrypted connections to cloud APIs
- Secrets in environment variables
- Read-only cloud permissions

### Access Control
- API authentication (add in prod)
- Role-based access control
- Audit logs for all actions
- Approval gates for risky operations

### Compliance
- SBOM generation
- Container image signing
- Vulnerability scanning
- Regular dependency updates

## Scalability

### Horizontal Scaling
- Stateless API servers
- Distributed task queue (future: Celery)
- Database connection pooling

### Data Volume
- Partitioned tables by date
- Data retention policies
- Archival to object storage

### Performance
- API response caching
- Materialized views for dashboards
- Async processing for heavy operations

## Extensibility

### Adding New Cloud Providers
1. Implement connector in `ingestion/connectors/`
2. Add normalization logic in `ingestion/schemas/`
3. Update API routes
4. Add Grafana panels

### Adding New Actions
1. Create playbook in `actions/playbooks/`
2. Add API endpoint in `api/routes/action_routes.py`
3. Define approval rules
4. Document in runbook

### Custom Policies
1. Write Rego policy in `policies/rego/`
2. Add evaluation endpoint
3. Integrate with CI/CD

## Monitoring

### Health Checks
- `/health` endpoint
- Database connectivity
- Cloud API reachability
- OPA availability

### SLOs
- API latency: p95 < 500ms
- Data freshness: < 2 hours
- Anomaly detection coverage: > 95%
- Uptime: 99.9%

## Disaster Recovery

### Backups
- Daily database backups
- Policy files in git
- Configuration in version control

### RTO/RPO
- RTO: < 2 hours
- RPO: < 24 hours (cost data)
- Critical data in managed services
