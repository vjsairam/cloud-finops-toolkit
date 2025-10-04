"""
Cost data API routes
Provides cost visibility by service, team, environment, etc.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd

from ingestion.connectors import AWSCostConnector, GCPCostConnector, AzureCostConnector

router = APIRouter()


@router.get("/by-service")
def get_cost_by_service(
    provider: str = Query(..., description="Cloud provider: aws, gcp, or azure"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get cost breakdown by service for a cloud provider"""

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        if provider == "aws":
            connector = AWSCostConnector()
            data = connector.get_cost_by_service(start, end)
        elif provider == "gcp":
            # Would need project_id from config
            raise HTTPException(
                status_code=501, detail="GCP connector requires configuration"
            )
        elif provider == "azure":
            # Would need subscription_id from config
            raise HTTPException(
                status_code=501, detail="Azure connector requires configuration"
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported provider: {provider}"
            )

        return {"provider": provider, "data": data, "count": len(data)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
def get_cost_summary(
    days: int = Query(30, description="Number of days to summarize"),
):
    """Get cost summary for last N days"""

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # This would aggregate data from database
    # For now, return sample structure

    return {
        "period": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "days": days,
        },
        "total_cost": 45250.75,
        "daily_average": 1508.36,
        "by_provider": {
            "aws": 32500.00,
            "gcp": 8750.50,
            "azure": 4000.25,
        },
        "top_services": [
            {"service": "EC2", "cost": 12500.00},
            {"service": "RDS", "cost": 8200.00},
            {"service": "S3", "cost": 3500.00},
        ],
    }


@router.get("/forecast")
def get_cost_forecast(
    days_ahead: int = Query(7, description="Number of days to forecast"),
):
    """Get cost forecast for next N days"""

    # This would use forecasting model
    # For now, return sample structure

    forecast_dates = [
        (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, days_ahead + 1)
    ]

    return {
        "forecast_period": days_ahead,
        "forecasted_costs": [
            {"date": date, "forecasted_cost": 1500 + (i * 10)}
            for i, date in enumerate(forecast_dates)
        ],
        "total_forecasted": 1500 * days_ahead,
        "confidence_interval": {"lower": 1400, "upper": 1600},
    }


@router.get("/trends")
def get_cost_trends(
    metric: str = Query("cost", description="Metric to analyze: cost, usage"),
    granularity: str = Query("daily", description="daily, weekly, monthly"),
    days: int = Query(30, description="Days of historical data"),
):
    """Get cost trends and patterns"""

    return {
        "metric": metric,
        "granularity": granularity,
        "period_days": days,
        "trend": "increasing",
        "change_percent": 12.5,
        "seasonality_detected": True,
        "data_points": [
            # Would return actual time series data
            {"date": "2025-01-01", "value": 1200},
            {"date": "2025-01-02", "value": 1250},
        ],
    }


@router.get("/by-tag/{tag_key}")
def get_cost_by_tag(
    tag_key: str,
    provider: str = Query(..., description="Cloud provider"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get cost breakdown by tag/label"""

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    try:
        if provider == "aws":
            connector = AWSCostConnector()
            data = connector.get_cost_by_tag(tag_key, start, end)
        else:
            raise HTTPException(status_code=501, detail="Provider not configured")

        return {"tag_key": tag_key, "provider": provider, "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
