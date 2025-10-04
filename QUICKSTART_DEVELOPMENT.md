# Quick Start Development Guide

## 🎯 Project Status

**Current Version:** 1.0.0 (Foundation)
**Completion:** 35% of full scope
**Production Ready:** No
**Enterprise Grade:** Not yet

---

## 📦 What You Have Now

### ✅ Working Components

**Infrastructure:**
- Docker Compose setup with all services
- FastAPI backend with 4 route modules
- Grafana + Prometheus monitoring
- OPA policy engine

**Features:**
- Multi-cloud cost ingestion (AWS, GCP, Azure)
- FOCUS schema normalization
- 3 anomaly detection algorithms
- Budget & tag policies (OPA/Rego)
- EC2, EBS, RDS remediation playbooks
- Approval engine with dry-run

**Documentation:**
- Setup guide
- API reference
- Architecture docs
- Operational runbook

---

## ⚠️ What's Missing (Critical for Production)

### 🔴 Blockers
1. **No persistent database** - Currently in-memory only
2. **No authentication** - APIs are completely open
3. **No error handling** - Will crash on failures
4. **No real data** - All responses are mocked
5. **No tests** - Zero test coverage
6. **Limited logging** - Basic prints only

### 🟡 Important
- dbt models for allocation (mentioned in README.txt)
- OpenCost integration for Kubernetes
- Slack/Jira notifications
- Real cloud API integration
- Performance optimization

---

## 🚀 Your First Week (40 hours)

### Day 1: Database Setup (8 hours)

**Goal:** Persistent PostgreSQL database with migrations

```bash
# 1. Install Alembic
pip install alembic sqlalchemy psycopg2-binary

# 2. Create models
mkdir -p api/models
touch api/models/__init__.py
```

Create `api/models/cost.py`:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True)
    provider = Column(String(20))  # aws, gcp, azure
    date = Column(DateTime)
    service = Column(String(100))
    cost = Column(Float)
    usage = Column(Float)
    tags = Column(JSON)
    created_at = Column(DateTime)
```

```bash
# 3. Initialize Alembic
alembic init alembic

# 4. Edit alembic.ini - set database URL
# sqlalchemy.url = postgresql://finops:finops@localhost:5432/finops

# 5. Edit alembic/env.py - import your models

# 6. Create migration
alembic revision --autogenerate -m "Add cost_records table"

# 7. Run migration
alembic upgrade head

# 8. Test
psql -U finops -d finops -c "\dt"
```

**Deliverable:** Working database with cost_records table ✅

---

### Day 2: Connect API to Database (8 hours)

**Goal:** Replace mock data with real database queries

Edit `api/routes/cost_routes.py`:
```python
from sqlalchemy.orm import Session
from api.models.cost import CostRecord
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/summary")
def get_cost_summary(days: int = 30, db: Session = Depends(get_db)):
    # Real query instead of mock data
    results = db.query(CostRecord).filter(
        CostRecord.date >= datetime.now() - timedelta(days=days)
    ).all()

    total_cost = sum(r.cost for r in results)
    # ... rest of logic
```

**Deliverable:** API reads from real database ✅

---

### Day 3: Authentication (8 hours)

**Goal:** JWT-based API authentication

```bash
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

Create `api/auth.py`:
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "your-secret-key-here"  # Move to env var
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
        return username
    except JWTError:
        raise HTTPException(status_code=401)
```

Add login endpoint:
```python
@app.post("/token")
async def login(username: str, password: str):
    # Verify user (implement user table)
    token = create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer"}
```

Protect routes:
```python
@router.get("/summary")
def get_cost_summary(
    days: int = 30,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... existing logic
```

**Deliverable:** Secured API with JWT auth ✅

---

### Day 4: Error Handling & Logging (8 hours)

**Goal:** Proper error handling and structured logging

```bash
pip install python-json-logger
```

Create `api/logging_config.py`:
```python
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()

    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

Create `api/exceptions.py`:
```python
class FinOpsException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class IngestionError(FinOpsException):
    pass

class AnomalyDetectionError(FinOpsException):
    pass
```

Add global exception handler in `api/main.py`:
```python
import logging
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

@app.exception_handler(FinOpsException)
async def finops_exception_handler(request, exc):
    logger.error(f"FinOps error: {exc.message}", extra={
        "error_type": type(exc).__name__,
        "path": request.url.path
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
```

Add retry logic to connectors:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_cost_data(self):
    try:
        # API call
        return response
    except Exception as e:
        logger.error(f"Error fetching cost data: {e}")
        raise IngestionError(f"Failed to fetch cost data: {e}")
```

**Deliverable:** Production-grade error handling ✅

---

### Day 5: Testing Foundation (8 hours)

**Goal:** Set up testing infrastructure and write first tests

```bash
pip install pytest pytest-cov httpx
mkdir -p tests/test_api tests/test_anomaly
```

Create `tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.main import app
from api.models.cost import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)
```

Create `tests/test_api/test_cost_routes.py`:
```python
def test_get_cost_summary(client):
    response = client.get("/api/v1/cost/summary?days=7")
    assert response.status_code == 200
    assert "total_cost" in response.json()

def test_cost_summary_requires_auth(client):
    # Without token
    response = client.get("/api/v1/cost/summary")
    assert response.status_code == 401
```

Create `tests/test_anomaly/test_baseline_detector.py`:
```python
import pandas as pd
from anomaly import BaselineDetector

def test_baseline_detector_finds_spike():
    data = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=30),
        'cost': [100] * 25 + [500] * 5
    })

    detector = BaselineDetector(sensitivity='medium')
    anomalies = detector.detect(data)

    assert len(anomalies) > 0
    assert anomalies[0].severity in ['high', 'critical']

def test_baseline_detector_no_spike():
    data = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=30),
        'cost': [100] * 30
    })

    detector = BaselineDetector(sensitivity='medium')
    anomalies = detector.detect(data)

    assert len(anomalies) == 0
```

Run tests:
```bash
pytest -v
pytest --cov=. --cov-report=html
```

**Deliverable:** Test framework with 20+ tests ✅

---

## 📊 Week 1 Success Metrics

After completing these 5 days:

- [ ] PostgreSQL database with migrations ✅
- [ ] API connected to real database ✅
- [ ] JWT authentication working ✅
- [ ] Structured logging implemented ✅
- [ ] Error handling with retries ✅
- [ ] 20+ passing tests ✅
- [ ] Test coverage report ✅

**You'll have a production-ready foundation!**

---

## 🎯 Week 2 Preview

### Day 6-7: Data Ingestion Pipeline
- Implement scheduled ingestion jobs
- Add real AWS Cost Explorer calls
- Store normalized data in database
- Create ingestion monitoring

### Day 8-9: Notification System
- Slack webhook integration
- Anomaly alert formatting
- Budget alert templates
- Notification preferences

### Day 10: CI/CD Enhancement
- Add database migrations to CI
- Implement integration tests in CI
- Add code coverage reporting
- Deploy to staging environment

---

## 🛠️ Development Tools Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Configure IDE (VS Code example)
cat > .vscode/settings.json <<EOF
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
EOF
```

---

## 📝 Daily Development Workflow

```bash
# 1. Start services
docker-compose up -d postgres redis

# 2. Activate venv
source venv/bin/activate

# 3. Run migrations
alembic upgrade head

# 4. Start API in dev mode
uvicorn api.main:app --reload --port 8000

# 5. In another terminal: Run tests
pytest --cov=. -v

# 6. Format code before commit
black .
isort .

# 7. Commit
git add .
git commit -m "feat: add database models and migrations"
```

---

## 🎓 Learning Path

### Essential Skills (Do First)
1. **SQLAlchemy** - 4 hours
   - https://docs.sqlalchemy.org/en/14/tutorial/

2. **FastAPI Dependencies** - 2 hours
   - https://fastapi.tiangolo.com/tutorial/dependencies/

3. **pytest** - 3 hours
   - https://docs.pytest.org/en/stable/

### Next Skills (Week 2+)
4. **dbt** - 8 hours
5. **Alembic** - 3 hours
6. **Celery** - 6 hours

---

## 💡 Pro Tips

1. **Code in small increments** - Commit after each working feature
2. **Write tests first** - TDD saves time debugging later
3. **Use Docker for dependencies** - Don't install Postgres locally
4. **Keep it simple** - Don't over-engineer
5. **Document as you go** - Future you will thank present you

---

## 🆘 Common Issues

### Database connection fails
```bash
# Check if Postgres is running
docker-compose ps

# Check connection string
# Should be: postgresql://finops:finops@localhost:5432/finops
```

### Import errors
```bash
# Make sure you're in project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tests fail
```bash
# Clear test database
rm test.db

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📞 Getting Help

- **Documentation**: Check `/docs` folder
- **TODO List**: See `TODO.md` for full roadmap
- **Roadmap**: See `PROJECT_ROADMAP.md` for timeline
- **Contributing**: See `CONTRIBUTING.md` for guidelines

---

**Start with Day 1 and build momentum! 🚀**

Each day adds critical production capabilities. By end of Week 1, you'll have a secure, tested, production-ready foundation to build on.
