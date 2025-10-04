"""
FastAPI application entry point
Provides REST APIs for cost data, anomalies, budgets, and remediation actions
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from .routes import cost_routes, anomaly_routes, policy_routes, action_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cloud FinOps Toolkit API",
    description="Multi-cloud FinOps automation platform with cost visibility, anomaly detection, and automated remediations",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(cost_routes.router, prefix="/api/v1/cost", tags=["cost"])
app.include_router(anomaly_routes.router, prefix="/api/v1/anomaly", tags=["anomaly"])
app.include_router(policy_routes.router, prefix="/api/v1/policy", tags=["policy"])
app.include_router(action_routes.router, prefix="/api/v1/action", tags=["action"])


@app.get("/")
def root():
    """API health check"""
    return {
        "service": "Cloud FinOps Toolkit",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "up",
            "database": "up",  # Add actual DB check
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
