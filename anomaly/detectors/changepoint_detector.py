"""
Change-point detection for identifying structural shifts in cost patterns
Uses PELT (Pruned Exact Linear Time) algorithm via ruptures library
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChangepointDetector:
    """
    Detects structural changes in time series (e.g., sudden sustained cost increases)
    Uses change-point detection algorithms to identify regime shifts
    """

    def __init__(self, min_segment_length: int = 3, penalty: float = 10.0):
        """
        Args:
            min_segment_length: Minimum number of data points between change points
            penalty: Penalty for adding change points (higher = fewer change points)
        """
        self.min_segment_length = min_segment_length
        self.penalty = penalty

    def detect(
        self, time_series: pd.DataFrame, value_col: str = "cost"
    ) -> List[Dict]:
        """
        Detect change points in time series

        Args:
            time_series: DataFrame with 'date' and value column
            value_col: Name of column to analyze

        Returns:
            List of change point events with metadata
        """
        try:
            import ruptures as rpt
        except ImportError:
            logger.warning(
                "ruptures library not installed. Using fallback simple change detection."
            )
            return self._simple_change_detection(time_series, value_col)

        if len(time_series) < self.min_segment_length * 2:
            logger.warning("Insufficient data for change point detection")
            return []

        time_series = time_series.copy()
        time_series["date"] = pd.to_datetime(time_series["date"])
        time_series = time_series.sort_values("date").reset_index(drop=True)

        # Extract signal
        signal = time_series[value_col].values

        # PELT algorithm for change point detection
        try:
            algo = rpt.Pelt(model="rbf", min_size=self.min_segment_length).fit(signal)
            change_points = algo.predict(pen=self.penalty)
        except Exception as e:
            logger.error(f"Error in ruptures detection: {e}")
            return self._simple_change_detection(time_series, value_col)

        # Remove last index (it's always the end of the series)
        if change_points and change_points[-1] == len(signal):
            change_points = change_points[:-1]

        # Build change point events
        events = []
        for cp_idx in change_points:
            if cp_idx == 0 or cp_idx >= len(time_series):
                continue

            # Calculate before/after statistics
            before_values = signal[max(0, cp_idx - 7) : cp_idx]
            after_values = signal[cp_idx : min(len(signal), cp_idx + 7)]

            before_mean = np.mean(before_values) if len(before_values) > 0 else 0
            after_mean = np.mean(after_values) if len(after_values) > 0 else 0

            change_percent = (
                ((after_mean - before_mean) / before_mean * 100)
                if before_mean > 0
                else 0
            )

            event = {
                "date": time_series.loc[cp_idx, "date"],
                "index": cp_idx,
                "before_mean": float(before_mean),
                "after_mean": float(after_mean),
                "change_percent": float(change_percent),
                "change_type": "increase" if change_percent > 0 else "decrease",
                "severity": self._calculate_change_severity(abs(change_percent)),
                "message": f"Cost pattern shift detected: {change_percent:+.1f}% change "
                f"(${before_mean:.2f} → ${after_mean:.2f})",
            }

            events.append(event)
            logger.info(event["message"])

        return events

    def _simple_change_detection(
        self, time_series: pd.DataFrame, value_col: str = "cost"
    ) -> List[Dict]:
        """
        Fallback simple change detection using moving averages
        Detects when 7-day average deviates significantly from 30-day average
        """
        if len(time_series) < 14:
            return []

        time_series = time_series.copy()
        time_series["date"] = pd.to_datetime(time_series["date"])
        time_series = time_series.sort_values("date").reset_index(drop=True)

        # Calculate moving averages
        time_series["ma_7"] = time_series[value_col].rolling(window=7, min_periods=4).mean()
        time_series["ma_30"] = time_series[value_col].rolling(window=30, min_periods=14).mean()

        events = []

        for idx in range(7, len(time_series)):
            ma_7 = time_series.loc[idx, "ma_7"]
            ma_30 = time_series.loc[idx, "ma_30"]

            if pd.isna(ma_7) or pd.isna(ma_30) or ma_30 == 0:
                continue

            deviation = (ma_7 - ma_30) / ma_30 * 100

            # Trigger if 7-day average deviates > 30% from 30-day average
            if abs(deviation) > 30:
                # Check if this is a new event (not consecutive to previous)
                if not events or (idx - events[-1]["index"]) > 7:
                    event = {
                        "date": time_series.loc[idx, "date"],
                        "index": idx,
                        "before_mean": float(ma_30),
                        "after_mean": float(ma_7),
                        "change_percent": float(deviation),
                        "change_type": "increase" if deviation > 0 else "decrease",
                        "severity": self._calculate_change_severity(abs(deviation)),
                        "message": f"Cost trend shift: {deviation:+.1f}% deviation "
                        f"(7-day avg ${ma_7:.2f} vs 30-day avg ${ma_30:.2f})",
                    }
                    events.append(event)

        return events

    def _calculate_change_severity(self, change_percent: float) -> str:
        """Map change percentage to severity"""
        if change_percent >= 100:
            return "critical"
        elif change_percent >= 50:
            return "high"
        elif change_percent >= 25:
            return "medium"
        else:
            return "low"

    def analyze_segment_costs(
        self, time_series: pd.DataFrame, change_points: List[int], value_col: str = "cost"
    ) -> List[Dict]:
        """
        Analyze cost statistics for each segment between change points

        Returns:
            List of segment statistics
        """
        time_series = time_series.copy().sort_values("date").reset_index(drop=True)
        signal = time_series[value_col].values

        # Add start and end points
        segments_bounds = [0] + change_points + [len(signal)]

        segments = []
        for i in range(len(segments_bounds) - 1):
            start_idx = segments_bounds[i]
            end_idx = segments_bounds[i + 1]

            segment_values = signal[start_idx:end_idx]

            segments.append(
                {
                    "segment_number": i + 1,
                    "start_date": time_series.loc[start_idx, "date"],
                    "end_date": time_series.loc[end_idx - 1, "date"],
                    "mean": float(np.mean(segment_values)),
                    "median": float(np.median(segment_values)),
                    "std": float(np.std(segment_values)),
                    "min": float(np.min(segment_values)),
                    "max": float(np.max(segment_values)),
                    "total": float(np.sum(segment_values)),
                    "length": len(segment_values),
                }
            )

        return segments
