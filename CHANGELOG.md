# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- dbt models for cost allocation
- OpenCost integration for Kubernetes
- Machine learning forecasting models
- Advanced commitment recommendations
- Multi-tenancy support

## [1.0.0] - 2025-01-10

### Added
- Multi-cloud cost ingestion (AWS, GCP, Azure)
- FOCUS-compliant schema normalization
- Baseline anomaly detection with configurable sensitivity
- Change-point detection using PELT algorithm
- Ensemble anomaly detection combining multiple methods
- OPA/Rego policy engine for budget and tag governance
- Automated EC2 remediation (idle instance detection and stop)
- Automated EBS remediation (unattached volume cleanup)
- Automated RDS remediation (idle database detection)
- Approval engine with auto-approval and manual gates
- FastAPI REST API with cost, anomaly, policy, and action endpoints
- Grafana dashboards for cost overview and anomaly detection
- Docker Compose deployment configuration
- Prometheus metrics integration
- Comprehensive documentation (setup, runbook, API, architecture)
- GitHub Actions CI/CD pipeline
- MIT License

### Cloud Provider Support
- AWS: Cost Explorer API and CUR S3 export support
- GCP: BigQuery Billing Export integration
- Azure: Cost Management API integration

### Security
- Read-only cloud permissions
- Dry-run mode for all remediation actions
- Approval gates for risky operations
- Secrets excluded from version control

### Documentation
- Complete setup guide with quick start
- Operational runbook with incident response
- API reference documentation
- Architecture documentation with diagrams
- README with features and examples

## [0.1.0] - 2025-01-09

### Added
- Initial project structure
- Basic cost connectors
- Placeholder anomaly detection
- Project planning and roadmap

---

## Version History

- **1.0.0** - Initial release with core features
- **0.1.0** - Project initialization

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow and guidelines.
