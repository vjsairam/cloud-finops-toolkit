"""GCP BigQuery Billing Export connector"""

from google.cloud import bigquery
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GCPCostConnector:
    """
    Pulls cost data from GCP BigQuery Billing Export
    Supports daily incremental pulls with filtering by service, project, and labels
    """

    def __init__(
        self,
        project_id: str,
        billing_dataset: str,
        billing_table: str = "gcp_billing_export_v1",
        credentials_path: Optional[str] = None,
    ):
        self.project_id = project_id
        self.billing_dataset = billing_dataset
        self.billing_table = billing_table

        if credentials_path:
            self.client = bigquery.Client.from_service_account_json(credentials_path)
        else:
            self.client = bigquery.Client(project=project_id)

    def get_cost_by_service(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by GCP service"""

        query = f"""
        SELECT
            DATE(usage_start_time) as date,
            service.description as service,
            SUM(cost) as cost,
            SUM(usage.amount) as usage,
            currency
        FROM
            `{self.project_id}.{self.billing_dataset}.{self.billing_table}`
        WHERE
            DATE(usage_start_time) >= @start_date
            AND DATE(usage_start_time) < @end_date
        GROUP BY
            date, service, currency
        ORDER BY
            date DESC, cost DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date.date()
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.date()),
            ]
        )

        try:
            results = self.client.query(query, job_config=job_config).result()
            rows = [dict(row) for row in results]
            logger.info(f"Retrieved {len(rows)} rows from GCP billing export")
            return rows

        except Exception as e:
            logger.error(f"Error fetching GCP cost data: {str(e)}")
            raise

    def get_cost_by_project(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by GCP project"""

        query = f"""
        SELECT
            DATE(usage_start_time) as date,
            project.id as project_id,
            project.name as project_name,
            SUM(cost) as cost,
            currency
        FROM
            `{self.project_id}.{self.billing_dataset}.{self.billing_table}`
        WHERE
            DATE(usage_start_time) >= @start_date
            AND DATE(usage_start_time) < @end_date
        GROUP BY
            date, project_id, project_name, currency
        ORDER BY
            date DESC, cost DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date.date()
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.date()),
            ]
        )

        try:
            results = self.client.query(query, job_config=job_config).result()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error fetching GCP project costs: {str(e)}")
            raise

    def get_cost_by_label(
        self, label_key: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by a specific label (e.g., team, env, app)"""

        query = f"""
        SELECT
            DATE(usage_start_time) as date,
            labels.value as label_value,
            SUM(cost) as cost,
            currency
        FROM
            `{self.project_id}.{self.billing_dataset}.{self.billing_table}`,
            UNNEST(labels) as labels
        WHERE
            DATE(usage_start_time) >= @start_date
            AND DATE(usage_start_time) < @end_date
            AND labels.key = @label_key
        GROUP BY
            date, label_value, currency
        ORDER BY
            date DESC, cost DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date.date()
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.date()),
                bigquery.ScalarQueryParameter("label_key", "STRING", label_key),
            ]
        )

        try:
            results = self.client.query(query, job_config=job_config).result()
            rows = [dict(row) for row in results]

            # Add label_key to each row for consistency
            for row in rows:
                row["label_key"] = label_key

            return rows

        except Exception as e:
            logger.error(f"Error fetching GCP label costs: {str(e)}")
            raise

    def get_cost_by_sku(
        self, start_date: datetime, end_date: datetime, top_n: int = 100
    ) -> List[Dict]:
        """Get most expensive SKUs (resource types)"""

        query = f"""
        SELECT
            DATE(usage_start_time) as date,
            sku.description as sku,
            service.description as service,
            SUM(cost) as cost,
            SUM(usage.amount) as usage,
            usage.unit as usage_unit,
            currency
        FROM
            `{self.project_id}.{self.billing_dataset}.{self.billing_table}`
        WHERE
            DATE(usage_start_time) >= @start_date
            AND DATE(usage_start_time) < @end_date
        GROUP BY
            date, sku, service, usage_unit, currency
        ORDER BY
            cost DESC
        LIMIT @top_n
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date.date()
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.date()),
                bigquery.ScalarQueryParameter("top_n", "INT64", top_n),
            ]
        )

        try:
            results = self.client.query(query, job_config=job_config).result()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error fetching GCP SKU costs: {str(e)}")
            raise

    def get_untagged_resources(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Identify resources without required labels for governance"""

        query = f"""
        SELECT
            DATE(usage_start_time) as date,
            project.id as project_id,
            service.description as service,
            SUM(cost) as cost,
            currency
        FROM
            `{self.project_id}.{self.billing_dataset}.{self.billing_table}`
        WHERE
            DATE(usage_start_time) >= @start_date
            AND DATE(usage_start_time) < @end_date
            AND ARRAY_LENGTH(labels) = 0
        GROUP BY
            date, project_id, service, currency
        ORDER BY
            cost DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date.date()
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date.date()),
            ]
        )

        try:
            results = self.client.query(query, job_config=job_config).result()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error fetching untagged resources: {str(e)}")
            raise
