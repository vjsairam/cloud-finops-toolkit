"""
Baseline anomaly detector using statistical methods
Detects cost spikes based on historical mean/median and standard deviation
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnomalyAlert:
    """Anomaly detection alert"""

    timestamp: datetime
    metric_name: str
    actual_value: float
    expected_value: float
    deviation_percent: float
    severity: str  # low, medium, high, critical
    confidence: float  # 0-1
    dimensions: Dict[str, str]  # service, team, environment, etc.
    message: str


class BaselineDetector:
    """
    Statistical baseline anomaly detection
    Uses rolling mean/std with configurable sensitivity thresholds
    """

    def __init__(
        self,
        baseline_days: int = 14,
        sensitivity: str = "medium",
        min_data_points: int = 7,
    ):
        """
        Args:
            baseline_days: Number of days to use for baseline calculation
            sensitivity: low (4 std), medium (3 std), high (2 std), very_high (1.5 std)
            min_data_points: Minimum data points required for detection
        """
        self.baseline_days = baseline_days
        self.min_data_points = min_data_points

        # Map sensitivity to standard deviation threshold
        self.std_threshold_map = {
            "low": 4.0,
            "medium": 3.0,
            "high": 2.0,
            "very_high": 1.5,
        }
        self.std_threshold = self.std_threshold_map.get(sensitivity, 3.0)

    def detect(
        self, time_series: pd.DataFrame, value_col: str = "cost"
    ) -> List[AnomalyAlert]:
        """
        Detect anomalies in time series data

        Args:
            time_series: DataFrame with 'date' and value column
            value_col: Name of the column containing values to analyze

        Returns:
            List of anomaly alerts
        """
        if len(time_series) < self.min_data_points:
            logger.warning(
                f"Insufficient data points: {len(time_series)} < {self.min_data_points}"
            )
            return []

        # Ensure date column is datetime
        time_series = time_series.copy()
        if "date" not in time_series.columns:
            raise ValueError("time_series must have a 'date' column")

        time_series["date"] = pd.to_datetime(time_series["date"])
        time_series = time_series.sort_values("date")

        # Calculate rolling statistics
        time_series["rolling_mean"] = (
            time_series[value_col]
            .rolling(window=self.baseline_days, min_periods=self.min_data_points)
            .mean()
        )
        time_series["rolling_std"] = (
            time_series[value_col]
            .rolling(window=self.baseline_days, min_periods=self.min_data_points)
            .std()
        )

        # Calculate upper/lower bounds
        time_series["upper_bound"] = (
            time_series["rolling_mean"]
            + self.std_threshold * time_series["rolling_std"]
        )
        time_series["lower_bound"] = (
            time_series["rolling_mean"]
            - self.std_threshold * time_series["rolling_std"]
        )

        # Detect anomalies (values outside bounds)
        anomalies = []

        for idx, row in time_series.iterrows():
            if pd.isna(row["rolling_mean"]) or pd.isna(row["upper_bound"]):
                continue

            actual = row[value_col]
            expected = row["rolling_mean"]
            upper = row["upper_bound"]
            lower = row["lower_bound"]

            is_anomaly = actual > upper or actual < lower

            if is_anomaly:
                deviation = ((actual - expected) / expected * 100) if expected > 0 else 0
                severity = self._calculate_severity(abs(deviation))

                # Calculate confidence based on how far from bounds
                if actual > upper:
                    confidence = min(
                        1.0, (actual - upper) / (upper - expected) if upper > expected else 1.0
                    )
                else:
                    confidence = min(
                        1.0, (lower - actual) / (expected - lower) if expected > lower else 1.0
                    )

                alert = AnomalyAlert(
                    timestamp=row["date"],
                    metric_name=value_col,
                    actual_value=float(actual),
                    expected_value=float(expected),
                    deviation_percent=float(deviation),
                    severity=severity,
                    confidence=float(confidence),
                    dimensions=self._extract_dimensions(time_series, idx),
                    message=f"{value_col.capitalize()} {'spike' if deviation > 0 else 'drop'}: "
                    f"${actual:.2f} vs expected ${expected:.2f} ({deviation:+.1f}%)",
                )

                anomalies.append(alert)
                logger.info(
                    f"Anomaly detected: {alert.message} [Severity: {severity}, Confidence: {confidence:.2f}]"
                )

        return anomalies

    def _calculate_severity(self, deviation_percent: float) -> str:
        """Map deviation percentage to severity level"""
        if deviation_percent >= 100:
            return "critical"
        elif deviation_percent >= 50:
            return "high"
        elif deviation_percent >= 25:
            return "medium"
        else:
            return "low"

    def _extract_dimensions(self, df: pd.DataFrame, idx: int) -> Dict[str, str]:
        """Extract dimension columns (service, team, env, etc.) from row"""
        row = df.loc[idx]
        dimensions = {}

        dimension_cols = ["service", "team", "environment", "project", "region"]
        for col in dimension_cols:
            if col in df.columns:
                dimensions[col] = str(row[col])

        return dimensions

    def detect_by_dimension(
        self,
        time_series: pd.DataFrame,
        dimension_col: str,
        value_col: str = "cost",
    ) -> Dict[str, List[AnomalyAlert]]:
        """
        Detect anomalies separately for each dimension value
        (e.g., per service, per team, per environment)

        Returns:
            Dictionary mapping dimension value to list of anomalies
        """
        results = {}

        if dimension_col not in time_series.columns:
            raise ValueError(f"Dimension column '{dimension_col}' not found")

        for dimension_value in time_series[dimension_col].unique():
            subset = time_series[time_series[dimension_col] == dimension_value].copy()

            if len(subset) >= self.min_data_points:
                anomalies = self.detect(subset, value_col)
                if anomalies:
                    results[str(dimension_value)] = anomalies
                    logger.info(
                        f"Found {len(anomalies)} anomalies for {dimension_col}={dimension_value}"
                    )

        return results

    def calculate_cost_forecast(
        self, time_series: pd.DataFrame, days_ahead: int = 7, value_col: str = "cost"
    ) -> pd.DataFrame:
        """
        Simple forecast based on recent trend
        Returns DataFrame with date and forecasted value
        """
        if len(time_series) < self.min_data_points:
            raise ValueError("Insufficient data for forecasting")

        time_series = time_series.copy()
        time_series["date"] = pd.to_datetime(time_series["date"])
        time_series = time_series.sort_values("date")

        # Calculate recent trend (last 7 days)
        recent = time_series.tail(7)
        daily_change = recent[value_col].diff().mean()

        # Generate forecast dates
        last_date = time_series["date"].max()
        forecast_dates = pd.date_range(
            start=last_date + timedelta(days=1), periods=days_ahead, freq="D"
        )

        # Simple linear forecast
        last_value = time_series[value_col].iloc[-1]
        forecast_values = [last_value + (i + 1) * daily_change for i in range(days_ahead)]

        forecast_df = pd.DataFrame(
            {"date": forecast_dates, f"{value_col}_forecast": forecast_values}
        )

        return forecast_df
