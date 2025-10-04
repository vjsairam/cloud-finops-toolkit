"""
Anomaly detection API routes
Provides anomaly alerts and change-point analysis
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd

from anomaly import BaselineDetector, ChangepointDetector, EnsembleDetector

router = APIRouter()


@router.get("/detect")
def detect_anomalies(
    metric: str = Query("cost", description="Metric to analyze"),
    sensitivity: str = Query("medium", description="low, medium, high, very_high"),
    days: int = Query(30, description="Days of historical data to analyze"),
):
    """Detect cost anomalies using baseline method"""

    # This would fetch actual data from database
    # For demo, create sample data
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    costs = [1000 + (i * 10) if i < 20 else 1500 + (i * 20) for i in range(days)]

    df = pd.DataFrame({"date": dates, "cost": costs})

    detector = BaselineDetector(sensitivity=sensitivity)
    anomalies = detector.detect(df, value_col="cost")

    return {
        "method": "baseline",
        "sensitivity": sensitivity,
        "days_analyzed": days,
        "anomalies_found": len(anomalies),
        "anomalies": [
            {
                "timestamp": a.timestamp.isoformat(),
                "actual": a.actual_value,
                "expected": a.expected_value,
                "deviation_percent": a.deviation_percent,
                "severity": a.severity,
                "message": a.message,
            }
            for a in anomalies
        ],
    }


@router.get("/changepoints")
def detect_changepoints(
    metric: str = Query("cost", description="Metric to analyze"),
    days: int = Query(30, description="Days of historical data"),
):
    """Detect structural changes in cost patterns"""

    # Sample data
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    costs = [1000 + (i * 10) if i < 15 else 2000 + (i * 10) for i in range(days)]

    df = pd.DataFrame({"date": dates, "cost": costs})

    detector = ChangepointDetector()
    changepoints = detector.detect(df, value_col="cost")

    return {
        "method": "changepoint",
        "days_analyzed": days,
        "changepoints_found": len(changepoints),
        "changepoints": changepoints,
    }


@router.get("/ensemble")
def ensemble_detection(
    metric: str = Query("cost", description="Metric to analyze"),
    days: int = Query(30, description="Days of historical data"),
):
    """Run ensemble detection combining multiple methods"""

    # Sample data
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    costs = [1000 + (i * 15) for i in range(days)]

    df = pd.DataFrame({"date": dates, "cost": costs})

    detector = EnsembleDetector()
    results = detector.detect(df, value_col="cost")

    return {
        "method": "ensemble",
        "days_analyzed": days,
        "baseline_anomalies": results["total_anomalies"],
        "changepoints": results["total_changepoints"],
        "high_confidence_anomalies": results["high_confidence_count"],
    }


@router.get("/summary")
def get_anomaly_summary():
    """Get summary of recent anomalies"""

    # This would query from database
    return {
        "last_24_hours": {
            "total_anomalies": 3,
            "critical": 1,
            "high": 1,
            "medium": 1,
        },
        "last_7_days": {
            "total_anomalies": 18,
            "critical": 2,
            "high": 6,
            "medium": 10,
        },
        "top_anomalies": [
            {
                "timestamp": datetime.now().isoformat(),
                "service": "EC2",
                "deviation_percent": 125.5,
                "severity": "critical",
            },
        ],
    }
