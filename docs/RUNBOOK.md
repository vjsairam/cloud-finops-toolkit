# Cloud FinOps Toolkit - Operational Runbook

## Daily Operations

### Morning Cost Review

1. **Check overnight anomalies**
   ```bash
   curl http://localhost:8000/api/v1/anomaly/summary
   ```

2. **Review budget status**
   ```bash
   curl http://localhost:8000/api/v1/cost/summary?days=1
   ```

3. **Check Grafana dashboards**
   - Open Cost Overview dashboard
   - Review anomaly alerts
   - Verify budget utilization

### Anomaly Response

When anomaly detected:

1. **Investigate the alert**
   - Check service/team causing spike
   - Review CloudWatch/Stackdriver metrics
   - Check recent deployments

2. **Determine if legitimate**
   - Expected traffic increase?
   - Scheduled batch job?
   - New feature launch?

3. **Take action if needed**
   - Stop idle resources
   - Scale down over-provisioned instances
   - Contact team owner

## Weekly Operations

### Cost Optimization Review

1. **Find idle EC2 instances**
   ```bash
   curl http://localhost:8000/api/v1/action/ec2/idle?cpu_threshold=5&days_lookback=7
   ```

2. **Find unattached EBS volumes**
   ```bash
   curl http://localhost:8000/api/v1/action/ebs/unattached?days_unattached=7
   ```

3. **Find idle RDS databases**
   ```bash
   curl http://localhost:8000/api/v1/action/rds/idle
   ```

4. **Review and approve actions**
   ```bash
   # Get pending approvals
   curl http://localhost:8000/api/v1/action/approval/pending

   # Approve action
   curl -X POST "http://localhost:8000/api/v1/action/approval/{request_id}/approve?approver=yourname"
   ```

### Tag Compliance Audit

1. **Run tag audit**
   ```python
   from policies import TagGovernance
   governance = TagGovernance()
   # Fetch resources and audit
   ```

2. **Generate compliance report**
3. **Contact teams with violations**
4. **Update tag policies if needed**

## Monthly Operations

### Budget Reconciliation

1. **Compare platform costs vs provider bills**
2. **Verify accuracy (should be ±3%)**
3. **Investigate discrepancies**
4. **Update budget forecasts**

### Savings Report

1. **Calculate total savings from remediations**
2. **Generate month-over-month comparison**
3. **Present to stakeholders**

## Incident Response

### Cost Spike Alert

**Severity: High**

1. **Immediate Actions (< 5 min)**
   - Check anomaly dashboard
   - Identify service/team
   - Verify not a false positive

2. **Investigation (< 15 min)**
   - Review recent changes (deployments, configs)
   - Check resource metrics
   - Contact service owner

3. **Mitigation (< 30 min)**
   - Stop runaway resources (if appropriate)
   - Scale down if over-provisioned
   - Apply temporary quota limits

4. **Post-Incident**
   - Document root cause
   - Update anomaly thresholds if needed
   - Create prevention measures

### Budget Exceeded

**Severity: Critical**

1. **Alert stakeholders immediately**
2. **Freeze non-critical spending**
3. **Emergency cost reduction**
   - Stop dev/test environments
   - Reduce non-prod capacity
   - Defer non-critical workloads

4. **Recovery Plan**
   - Identify cost drivers
   - Implement optimization actions
   - Revise budget if needed

## Maintenance Tasks

### Data Retention

1. **Archive old cost data (> 1 year)**
   ```sql
   COPY (SELECT * FROM cost_data WHERE date < NOW() - INTERVAL '1 year')
   TO '/backup/cost_archive.csv';
   DELETE FROM cost_data WHERE date < NOW() - INTERVAL '1 year';
   ```

2. **Cleanup old snapshots**
   ```bash
   curl http://localhost:8000/api/v1/action/ebs/old-snapshots?days_old=90
   ```

### Database Maintenance

1. **Vacuum and analyze**
   ```sql
   VACUUM ANALYZE cost_data;
   VACUUM ANALYZE anomaly_events;
   ```

2. **Backup database**
   ```bash
   pg_dump finops > finops_backup_$(date +%Y%m%d).sql
   ```

3. **Monitor disk usage**
   ```bash
   df -h
   docker system df
   ```

### Update Dependencies

```bash
# Monthly security updates
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Update Docker images
docker-compose pull
docker-compose up -d
```

## Monitoring & Alerts

### Key Metrics to Monitor

- API response times (p95 < 500ms)
- Data ingestion latency (< 2 hours)
- Anomaly detection coverage (> 95% of spend)
- Budget utilization per team
- Tag compliance rate (target > 90%)

### Alert Thresholds

- **Critical**: Budget exceeded, API down, data ingestion failed
- **High**: Anomaly > 100% deviation, budget > 90%
- **Medium**: Anomaly > 50% deviation, budget > 75%
- **Low**: Tag compliance < 90%, minor anomalies

## Escalation

### Level 1: Automated Actions
- Auto-approved remediations execute automatically
- Slack notifications to #finops-alerts

### Level 2: Manual Review
- Pending approvals require engineer review
- Notify on-call FinOps engineer

### Level 3: Management
- Budget overruns > 10%
- Repeated policy violations
- Critical cost incidents

## Support Contacts

- FinOps Team: #finops-team
- Cloud Engineering: #cloud-engineering
- Security: #security
- On-call: PagerDuty

## Useful Commands

```bash
# Restart API
docker-compose restart api

# View API logs
docker-compose logs -f api

# Execute dry-run action
curl -X POST http://localhost:8000/api/v1/action/ec2/stop \
  -H "Content-Type: application/json" \
  -d '{"resource_ids": ["i-1234"], "dry_run": true}'

# Check policy
opa eval -d policies/rego/budget_policy.rego "data.budget.allow" \
  --input policy_input.json

# Manual cost pull
python -m ingestion.connectors.aws_connector

# Run anomaly detection
python -m anomaly.detectors.ensemble_detector
```
