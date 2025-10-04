# Contributing to Cloud FinOps Toolkit

## Development Workflow

### Getting Started

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/cloud-finops-toolkit.git
   cd cloud-finops-toolkit
   ```

2. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Standards

#### Code Style

We use **Black** for Python code formatting:
```bash
black .
```

#### Linting

We use **flake8** for linting:
```bash
flake8 . --max-line-length=127 --exclude=venv
```

#### Type Checking

We use **mypy** for static type checking:
```bash
mypy ingestion/ anomaly/ policies/ actions/ api/
```

#### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

This will automatically run:
- Black formatting
- flake8 linting
- mypy type checking
- Trailing whitespace removal
- YAML validation

### Testing

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_anomaly.py

# Run specific test
pytest tests/test_anomaly.py::test_baseline_detector
```

#### Writing Tests

- Place tests in `tests/` directory
- Mirror the source structure (e.g., `tests/test_ingestion/test_aws_connector.py`)
- Use descriptive test names: `test_should_detect_anomaly_when_cost_exceeds_threshold`
- Aim for 80%+ code coverage
- Mock external API calls

Example test:
```python
import pytest
from anomaly import BaselineDetector
import pandas as pd

def test_baseline_detector_finds_spike():
    # Arrange
    data = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=30),
        'cost': [100] * 25 + [500] * 5  # Spike in last 5 days
    })
    detector = BaselineDetector(sensitivity='medium')

    # Act
    anomalies = detector.detect(data)

    # Assert
    assert len(anomalies) > 0
    assert anomalies[0].severity in ['high', 'critical']
```

### Pull Request Process

1. **Update documentation**
   - Update README.md if adding new features
   - Add docstrings to new functions/classes
   - Update API.md for new endpoints

2. **Add tests**
   - Write unit tests for new code
   - Ensure all tests pass
   - Maintain or improve code coverage

3. **Update CHANGELOG.md**
   ```markdown
   ## [Unreleased]
   ### Added
   - New feature X that does Y

   ### Fixed
   - Bug in Z that caused W
   ```

4. **Commit messages**
   Follow conventional commits:
   ```
   feat: add Kubernetes cost allocation
   fix: correct anomaly detection threshold calculation
   docs: update API documentation for budget endpoints
   test: add unit tests for EC2 remediation
   refactor: simplify connector base class
   ```

5. **Submit PR**
   - Fill out the PR template
   - Link related issues
   - Request review from maintainers
   - Address review feedback

### Project Structure Guidelines

```
cloud-finops-toolkit/
├── ingestion/          # Data ingestion from cloud providers
│   ├── connectors/     # Cloud provider connectors
│   └── schemas/        # Data normalization schemas
├── anomaly/            # Anomaly detection algorithms
│   └── detectors/      # Detection implementations
├── policies/           # Policy-as-code
│   ├── rego/          # OPA policy files
│   └── *.py           # Python policy engines
├── actions/            # Automated remediation
│   └── playbooks/     # Action playbooks
├── allocation/         # Cost allocation (dbt models)
├── api/                # FastAPI application
│   ├── routes/        # API endpoints
│   └── models/        # Pydantic models
├── dashboards/         # Grafana dashboards
├── docs/              # Documentation
├── tests/             # Test suite
└── scripts/           # Utility scripts
```

### Adding New Features

#### New Cloud Connector

1. Create `ingestion/connectors/newcloud_connector.py`
2. Inherit from base connector pattern
3. Implement required methods
4. Add to `ingestion/connectors/__init__.py`
5. Update `ingestion/schemas/normalizer.py`
6. Add tests in `tests/test_ingestion/`
7. Update documentation

#### New Anomaly Detector

1. Create `anomaly/detectors/new_detector.py`
2. Follow detector interface
3. Add to `anomaly/__init__.py`
4. Update ensemble detector
5. Add tests
6. Update API endpoints

#### New Remediation Action

1. Create `actions/playbooks/new_action.py`
2. Implement with dry-run support
3. Add approval logic
4. Create API endpoint in `api/routes/action_routes.py`
5. Add tests
6. Document in runbook

### Code Review Checklist

**For Reviewers:**
- [ ] Code follows project style guide
- [ ] Tests are present and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance implications considered
- [ ] Error handling is appropriate
- [ ] Logging is adequate
- [ ] API changes are backward compatible

**For Contributors:**
- [ ] I have tested my changes locally
- [ ] I have added tests for new functionality
- [ ] I have updated documentation
- [ ] I have run linters and formatters
- [ ] I have considered security implications
- [ ] I have updated CHANGELOG.md
- [ ] My commits follow conventional commit format

### Documentation

#### Docstring Format

Use Google-style docstrings:

```python
def detect_anomalies(time_series: pd.DataFrame, threshold: float = 3.0) -> List[Anomaly]:
    """
    Detect cost anomalies in time series data.

    Args:
        time_series: DataFrame with 'date' and 'cost' columns
        threshold: Number of standard deviations for threshold

    Returns:
        List of Anomaly objects with detected anomalies

    Raises:
        ValueError: If time_series is missing required columns

    Example:
        >>> df = pd.DataFrame({'date': [...], 'cost': [...]})
        >>> anomalies = detect_anomalies(df, threshold=2.5)
        >>> print(f"Found {len(anomalies)} anomalies")
    """
    pass
```

#### API Documentation

Update `docs/API.md` when adding new endpoints:

```markdown
#### New Endpoint

\`\`\`http
POST /api/v1/new-endpoint
\`\`\`

**Description:** Brief description

**Parameters:**
- `param1` (required): Description

**Example:**
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/new-endpoint \\
  -H "Content-Type: application/json" \\
  -d '{"param1": "value"}'
\`\`\`
```

### Performance Guidelines

- Use database indexes for frequently queried columns
- Implement pagination for large result sets
- Cache expensive computations
- Use async operations for I/O-bound tasks
- Profile code before optimizing
- Document performance requirements

### Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Sanitize data before database queries
- Use parameterized queries (no string interpolation)
- Implement rate limiting
- Log security events
- Follow principle of least privilege

### Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create a GitHub Issue with reproduction steps
- **Features**: Open a GitHub Issue with use case description
- **Security**: Email security@example.com (do not create public issue)

### Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to Cloud FinOps Toolkit! 🎉
