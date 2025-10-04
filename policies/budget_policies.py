"""
Budget policy management and enforcement
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    """Budget configuration"""

    name: str
    limit: float
    period: str  # monthly, quarterly, annual
    team: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    threshold_alerts: List[float] = None  # [0.5, 0.75, 0.9, 1.0]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def __post_init__(self):
        if self.threshold_alerts is None:
            self.threshold_alerts = [0.5, 0.75, 0.9, 1.0]


class BudgetPolicy:
    """
    Manages budgets and evaluates spend against limits
    Triggers alerts and policy violations
    """

    def __init__(self):
        self.budgets: Dict[str, Budget] = {}

    def add_budget(self, budget: Budget):
        """Register a budget"""
        self.budgets[budget.name] = budget
        logger.info(f"Added budget: {budget.name} (${budget.limit} {budget.period})")

    def evaluate_budget(
        self, budget_name: str, current_spend: float, days_elapsed: int = None
    ) -> Dict:
        """
        Evaluate current spend against budget

        Returns:
            Dictionary with status, violations, and alert level
        """
        if budget_name not in self.budgets:
            raise ValueError(f"Budget not found: {budget_name}")

        budget = self.budgets[budget_name]
        utilization = current_spend / budget.limit if budget.limit > 0 else 0

        # Determine alert level
        alert_level = None
        for threshold in sorted(budget.threshold_alerts):
            if utilization >= threshold:
                alert_level = f"{int(threshold * 100)}%"

        # Calculate burn rate if days_elapsed provided
        projected_spend = None
        if days_elapsed:
            daily_burn = current_spend / days_elapsed
            days_in_period = {"monthly": 30, "quarterly": 90, "annual": 365}.get(
                budget.period, 30
            )
            projected_spend = daily_burn * days_in_period

        violations = []

        # Check violations
        if utilization >= 1.0:
            violations.append(
                f"Budget exceeded: ${current_spend:.2f} > ${budget.limit:.2f}"
            )

        if projected_spend and projected_spend > budget.limit * 1.1:
            violations.append(
                f"Projected to exceed budget by >10%: ${projected_spend:.2f} projected"
            )

        result = {
            "budget_name": budget_name,
            "limit": budget.limit,
            "current_spend": current_spend,
            "utilization_percent": utilization * 100,
            "alert_level": alert_level,
            "projected_spend": projected_spend,
            "allowed": len(violations) == 0,
            "violations": violations,
            "message": self._format_budget_message(
                budget, current_spend, utilization, violations
            ),
        }

        return result

    def _format_budget_message(
        self, budget: Budget, current_spend: float, utilization: float, violations: List[str]
    ) -> str:
        """Format a human-readable budget status message"""
        if len(violations) == 0:
            return f"Budget '{budget.name}' is healthy: ${current_spend:.2f} / ${budget.limit:.2f} ({utilization * 100:.1f}%)"
        else:
            return (
                f"Budget '{budget.name}' policy violated: ${current_spend:.2f} / ${budget.limit:.2f} ({utilization * 100:.1f}%) - "
                + "; ".join(violations)
            )

    def get_budgets_by_team(self, team: str) -> List[Budget]:
        """Get all budgets for a specific team"""
        return [b for b in self.budgets.values() if b.team == team]

    def get_budget_forecast(
        self, budget_name: str, current_spend: float, days_elapsed: int
    ) -> Dict:
        """
        Forecast end-of-period spend based on current burn rate

        Returns:
            Forecast data including projected spend, overage, days until exhaustion
        """
        if budget_name not in self.budgets:
            raise ValueError(f"Budget not found: {budget_name}")

        budget = self.budgets[budget_name]
        days_in_period = {"monthly": 30, "quarterly": 90, "annual": 365}.get(
            budget.period, 30
        )

        daily_burn = current_spend / days_elapsed if days_elapsed > 0 else 0
        projected_spend = daily_burn * days_in_period
        days_remaining = days_in_period - days_elapsed

        # Calculate days until budget exhausted
        if daily_burn > 0:
            remaining_budget = budget.limit - current_spend
            days_until_exhaustion = (
                remaining_budget / daily_burn if remaining_budget > 0 else 0
            )
        else:
            days_until_exhaustion = float("inf")

        return {
            "budget_name": budget_name,
            "period": budget.period,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "current_spend": current_spend,
            "daily_burn_rate": daily_burn,
            "projected_spend": projected_spend,
            "budget_limit": budget.limit,
            "projected_overage": max(0, projected_spend - budget.limit),
            "days_until_exhaustion": min(days_until_exhaustion, days_remaining),
            "will_exceed_budget": projected_spend > budget.limit,
        }

    def create_budget_alert(self, budget_eval: Dict) -> Optional[Dict]:
        """
        Create an alert if budget thresholds are exceeded

        Returns:
            Alert dict if action needed, None otherwise
        """
        if not budget_eval["alert_level"]:
            return None

        severity_map = {
            "50%": "low",
            "75%": "medium",
            "90%": "high",
            "100%": "critical",
        }

        alert = {
            "type": "budget_threshold",
            "severity": severity_map.get(budget_eval["alert_level"], "medium"),
            "budget_name": budget_eval["budget_name"],
            "utilization": budget_eval["utilization_percent"],
            "threshold": budget_eval["alert_level"],
            "message": budget_eval["message"],
            "timestamp": datetime.now().isoformat(),
            "action_required": budget_eval["utilization_percent"] >= 90,
        }

        return alert
