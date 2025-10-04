"""
Ensemble anomaly detector combining multiple detection methods
Provides more robust detection by aggregating signals from different algorithms
"""

from typing import List, Dict
import pandas as pd
from datetime import datetime
import logging

from .baseline_detector import BaselineDetector, AnomalyAlert
from .changepoint_detector import ChangepointDetector

logger = logging.getLogger(__name__)


class EnsembleDetector:
    """
    Combines multiple anomaly detection methods for robust detection
    Uses voting or scoring mechanism to reduce false positives
    """

    def __init__(
        self,
        baseline_sensitivity: str = "medium",
        changepoint_penalty: float = 10.0,
        min_detectors_agreement: int = 1,
    ):
        """
        Args:
            baseline_sensitivity: Sensitivity for baseline detector
            changepoint_penalty: Penalty for changepoint detector
            min_detectors_agreement: Minimum number of detectors that must agree
        """
        self.baseline_detector = BaselineDetector(sensitivity=baseline_sensitivity)
        self.changepoint_detector = ChangepointDetector(penalty=changepoint_penalty)
        self.min_detectors_agreement = min_detectors_agreement

    def detect(
        self, time_series: pd.DataFrame, value_col: str = "cost"
    ) -> Dict[str, List]:
        """
        Run all detection methods and aggregate results

        Returns:
            Dictionary with:
            - baseline_anomalies: List of AnomalyAlert from baseline detector
            - changepoint_events: List of change point events
            - high_confidence_anomalies: Anomalies detected by multiple methods
        """
        time_series = time_series.copy()
        time_series["date"] = pd.to_datetime(time_series["date"])

        # Run baseline detection
        baseline_anomalies = self.baseline_detector.detect(time_series, value_col)

        # Run changepoint detection
        changepoint_events = self.changepoint_detector.detect(time_series, value_col)

        # Find high-confidence anomalies (detected by both methods)
        high_confidence = self._find_overlapping_anomalies(
            baseline_anomalies, changepoint_events
        )

        results = {
            "baseline_anomalies": baseline_anomalies,
            "changepoint_events": changepoint_events,
            "high_confidence_anomalies": high_confidence,
            "total_anomalies": len(baseline_anomalies),
            "total_changepoints": len(changepoint_events),
            "high_confidence_count": len(high_confidence),
        }

        logger.info(
            f"Ensemble detection complete: {results['total_anomalies']} baseline anomalies, "
            f"{results['total_changepoints']} change points, "
            f"{results['high_confidence_count']} high-confidence events"
        )

        return results

    def _find_overlapping_anomalies(
        self, baseline_anomalies: List[AnomalyAlert], changepoint_events: List[Dict]
    ) -> List[Dict]:
        """
        Find anomalies that are detected by both baseline and changepoint methods
        within a time window
        """
        high_confidence = []

        # Convert changepoint events to dates
        changepoint_dates = [event["date"] for event in changepoint_events]

        for anomaly in baseline_anomalies:
            # Check if anomaly is within 3 days of a changepoint
            for cp_date in changepoint_dates:
                days_diff = abs((anomaly.timestamp - cp_date).days)

                if days_diff <= 3:
                    high_confidence.append(
                        {
                            "date": anomaly.timestamp,
                            "type": "high_confidence_anomaly",
                            "baseline_severity": anomaly.severity,
                            "baseline_deviation": anomaly.deviation_percent,
                            "actual_value": anomaly.actual_value,
                            "expected_value": anomaly.expected_value,
                            "confidence": anomaly.confidence,
                            "message": f"High-confidence anomaly: Detected by both baseline and changepoint methods. {anomaly.message}",
                            "dimensions": anomaly.dimensions,
                        }
                    )
                    break

        return high_confidence

    def detect_by_service(
        self, time_series: pd.DataFrame, value_col: str = "cost"
    ) -> Dict[str, Dict]:
        """
        Run ensemble detection separately for each service

        Returns:
            Dictionary mapping service name to detection results
        """
        if "service" not in time_series.columns:
            raise ValueError("time_series must have a 'service' column")

        results_by_service = {}

        for service in time_series["service"].unique():
            service_data = time_series[time_series["service"] == service].copy()

            if len(service_data) >= 7:  # Minimum data points
                results_by_service[service] = self.detect(service_data, value_col)
                logger.info(f"Completed detection for service: {service}")

        return results_by_service

    def generate_summary_report(self, detection_results: Dict) -> str:
        """
        Generate a human-readable summary of detection results

        Args:
            detection_results: Output from detect() method

        Returns:
            Formatted summary string
        """
        report_lines = [
            "=" * 70,
            "ANOMALY DETECTION SUMMARY",
            "=" * 70,
            "",
            f"Total Baseline Anomalies: {detection_results['total_anomalies']}",
            f"Total Change Points: {detection_results['total_changepoints']}",
            f"High-Confidence Anomalies: {detection_results['high_confidence_count']}",
            "",
        ]

        # Summarize high-confidence anomalies
        if detection_results["high_confidence_anomalies"]:
            report_lines.append("HIGH-CONFIDENCE ANOMALIES:")
            report_lines.append("-" * 70)

            for anomaly in detection_results["high_confidence_anomalies"]:
                report_lines.append(f"  Date: {anomaly['date'].strftime('%Y-%m-%d')}")
                report_lines.append(f"  Severity: {anomaly['baseline_severity']}")
                report_lines.append(
                    f"  Cost: ${anomaly['actual_value']:.2f} (expected: ${anomaly['expected_value']:.2f})"
                )
                report_lines.append(
                    f"  Deviation: {anomaly['baseline_deviation']:+.1f}%"
                )
                report_lines.append("")

        # Summarize change points
        if detection_results["changepoint_events"]:
            report_lines.append("STRUCTURAL CHANGES:")
            report_lines.append("-" * 70)

            for event in detection_results["changepoint_events"]:
                report_lines.append(f"  Date: {event['date'].strftime('%Y-%m-%d')}")
                report_lines.append(f"  Type: {event['change_type']}")
                report_lines.append(f"  Severity: {event['severity']}")
                report_lines.append(
                    f"  Change: ${event['before_mean']:.2f} → ${event['after_mean']:.2f} "
                    f"({event['change_percent']:+.1f}%)"
                )
                report_lines.append("")

        report_lines.append("=" * 70)

        return "\n".join(report_lines)
