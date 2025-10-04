"""Azure Cost Management API connector"""

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.consumption import ConsumptionManagementClient
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AzureCostConnector:
    """
    Pulls cost data from Azure Cost Management API
    Supports daily incremental pulls with filtering by resource groups, tags, and subscriptions
    """

    def __init__(
        self,
        subscription_id: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.subscription_id = subscription_id

        # Use service principal if credentials provided, otherwise use default credentials
        if tenant_id and client_id and client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
            )
        else:
            self.credential = DefaultAzureCredential()

        self.cost_client = CostManagementClient(self.credential)
        self.consumption_client = ConsumptionManagementClient(
            self.credential, self.subscription_id
        )

    def get_cost_by_service(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by Azure service (meter category)"""

        scope = f"/subscriptions/{self.subscription_id}"

        # Build query definition
        query_definition = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "time_period": {
                "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {
                    "totalCost": {"name": "Cost", "function": "Sum"},
                    "totalUsage": {"name": "UsageQuantity", "function": "Sum"},
                },
                "grouping": [
                    {"type": "Dimension", "name": "ServiceName"},
                    {"type": "Dimension", "name": "MeterCategory"},
                ],
            },
        }

        try:
            result = self.cost_client.query.usage(scope, query_definition)

            costs = []
            for row in result.rows:
                # Azure API returns: [cost, usage, date, service_name, meter_category]
                costs.append(
                    {
                        "date": str(row[2]),
                        "service": row[3],
                        "meter_category": row[4],
                        "cost": float(row[0]),
                        "usage": float(row[1]) if row[1] else 0.0,
                        "currency": result.columns[0].name
                        if result.columns
                        else "USD",
                    }
                )

            logger.info(f"Retrieved {len(costs)} cost records from Azure")
            return costs

        except Exception as e:
            logger.error(f"Error fetching Azure cost data: {str(e)}")
            raise

    def get_cost_by_resource_group(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by resource group"""

        scope = f"/subscriptions/{self.subscription_id}"

        query_definition = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "time_period": {
                "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ResourceGroupName"}],
            },
        }

        try:
            result = self.cost_client.query.usage(scope, query_definition)

            costs = []
            for row in result.rows:
                costs.append(
                    {
                        "date": str(row[1]),
                        "resource_group": row[2],
                        "cost": float(row[0]),
                        "currency": "USD",
                    }
                )

            return costs

        except Exception as e:
            logger.error(f"Error fetching Azure resource group costs: {str(e)}")
            raise

    def get_cost_by_tag(
        self, tag_key: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by a specific tag"""

        scope = f"/subscriptions/{self.subscription_id}"

        query_definition = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "time_period": {
                "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Tag", "name": tag_key}],
            },
        }

        try:
            result = self.cost_client.query.usage(scope, query_definition)

            costs = []
            for row in result.rows:
                costs.append(
                    {
                        "date": str(row[1]),
                        "tag_key": tag_key,
                        "tag_value": row[2] if len(row) > 2 else "untagged",
                        "cost": float(row[0]),
                        "currency": "USD",
                    }
                )

            return costs

        except Exception as e:
            logger.error(f"Error fetching Azure tag costs: {str(e)}")
            raise

    def get_cost_by_location(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by Azure region"""

        scope = f"/subscriptions/{self.subscription_id}"

        query_definition = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "time_period": {
                "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ResourceLocation"}],
            },
        }

        try:
            result = self.cost_client.query.usage(scope, query_definition)

            costs = []
            for row in result.rows:
                costs.append(
                    {
                        "date": str(row[1]),
                        "location": row[2],
                        "cost": float(row[0]),
                        "currency": "USD",
                    }
                )

            return costs

        except Exception as e:
            logger.error(f"Error fetching Azure location costs: {str(e)}")
            raise

    def get_budget_status(self, resource_group: Optional[str] = None) -> List[Dict]:
        """Get current budget status and alerts"""

        if resource_group:
            scope = f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_group}"
        else:
            scope = f"/subscriptions/{self.subscription_id}"

        try:
            budgets = self.consumption_client.budgets.list(scope)

            budget_status = []
            for budget in budgets:
                status = {
                    "name": budget.name,
                    "amount": budget.amount,
                    "time_grain": budget.time_grain,
                    "category": budget.category,
                    "current_spend": None,
                }

                # Get current spend if available
                if hasattr(budget, "current_spend"):
                    status["current_spend"] = budget.current_spend.amount
                    status["percent_used"] = (
                        (budget.current_spend.amount / budget.amount) * 100
                        if budget.amount > 0
                        else 0
                    )

                budget_status.append(status)

            return budget_status

        except Exception as e:
            logger.error(f"Error fetching Azure budgets: {str(e)}")
            raise

    def get_reservation_recommendations(self) -> List[Dict]:
        """Get Azure Reserved Instance recommendations for cost savings"""

        scope = f"/subscriptions/{self.subscription_id}"

        try:
            recommendations = (
                self.consumption_client.reservation_recommendations.list(scope)
            )

            results = []
            for rec in recommendations:
                results.append(
                    {
                        "resource_type": rec.resource_type,
                        "term": rec.term,
                        "sku": rec.sku_name if hasattr(rec, "sku_name") else None,
                        "location": rec.location if hasattr(rec, "location") else None,
                        "savings": rec.net_savings
                        if hasattr(rec, "net_savings")
                        else None,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error fetching reservation recommendations: {str(e)}")
            raise
