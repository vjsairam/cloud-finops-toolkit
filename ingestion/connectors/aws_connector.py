"""AWS Cost and Usage Report (CUR) connector"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AWSCostConnector:
    """
    Pulls cost data from AWS Cost Explorer and CUR S3 exports
    Supports daily incremental pulls with filtering by service, tags, and accounts
    """

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: str = "us-east-1",
        cur_s3_bucket: Optional[str] = None,
    ):
        self.session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        self.ce_client = self.session.client("ce")
        self.s3_client = self.session.client("s3")
        self.cur_s3_bucket = cur_s3_bucket

    def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "DAILY",
        metrics: List[str] = None,
        group_by: List[Dict] = None,
        filter_expr: Optional[Dict] = None,
    ) -> Dict:
        """
        Fetch cost and usage data from AWS Cost Explorer API

        Args:
            start_date: Start date for cost data
            end_date: End date for cost data
            granularity: DAILY, MONTHLY, or HOURLY
            metrics: List of metrics (UnblendedCost, BlendedCost, UsageQuantity, etc.)
            group_by: Dimensions to group by (SERVICE, USAGE_TYPE, TAG, etc.)
            filter_expr: Filter expression for cost data

        Returns:
            Dictionary containing cost and usage data
        """
        if metrics is None:
            metrics = ["UnblendedCost", "UsageQuantity"]

        if group_by is None:
            group_by = [{"Type": "DIMENSION", "Key": "SERVICE"}]

        try:
            params = {
                "TimePeriod": {
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                "Granularity": granularity,
                "Metrics": metrics,
                "GroupBy": group_by,
            }

            if filter_expr:
                params["Filter"] = filter_expr

            response = self.ce_client.get_cost_and_usage(**params)
            logger.info(
                f"Retrieved {len(response.get('ResultsByTime', []))} time periods from AWS Cost Explorer"
            )
            return response

        except Exception as e:
            logger.error(f"Error fetching AWS cost data: {str(e)}")
            raise

    def get_cost_by_service(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by AWS service"""
        response = self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            group_by=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        results = []
        for time_period in response.get("ResultsByTime", []):
            period_start = time_period["TimePeriod"]["Start"]
            for group in time_period.get("Groups", []):
                service = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                usage = float(group["Metrics"]["UsageQuantity"]["Amount"])

                results.append(
                    {
                        "date": period_start,
                        "service": service,
                        "cost": cost,
                        "usage": usage,
                        "currency": group["Metrics"]["UnblendedCost"]["Unit"],
                    }
                )

        return results

    def get_cost_by_tag(
        self, tag_key: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Get cost breakdown by a specific tag (e.g., team, environment, project)"""
        response = self.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            group_by=[{"Type": "TAG", "Key": tag_key}],
        )

        results = []
        for time_period in response.get("ResultsByTime", []):
            period_start = time_period["TimePeriod"]["Start"]
            for group in time_period.get("Groups", []):
                tag_value = group["Keys"][0] if group["Keys"] else "untagged"
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])

                results.append(
                    {
                        "date": period_start,
                        "tag_key": tag_key,
                        "tag_value": tag_value,
                        "cost": cost,
                        "currency": group["Metrics"]["UnblendedCost"]["Unit"],
                    }
                )

        return results

    def pull_cur_from_s3(self, prefix: str, local_dir: str) -> List[str]:
        """
        Download CUR files from S3 for detailed analysis

        Args:
            prefix: S3 prefix path to CUR files
            local_dir: Local directory to download files to

        Returns:
            List of downloaded file paths
        """
        if not self.cur_s3_bucket:
            raise ValueError("CUR S3 bucket not configured")

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.cur_s3_bucket, Prefix=prefix
            )

            downloaded_files = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".csv.gz") or key.endswith(".parquet"):
                    local_path = f"{local_dir}/{key.split('/')[-1]}"
                    self.s3_client.download_file(self.cur_s3_bucket, key, local_path)
                    downloaded_files.append(local_path)
                    logger.info(f"Downloaded {key} to {local_path}")

            return downloaded_files

        except Exception as e:
            logger.error(f"Error downloading CUR from S3: {str(e)}")
            raise

    def get_cost_forecast(self, days_ahead: int = 30) -> Dict:
        """Get AWS cost forecast for specified number of days"""
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=days_ahead)

        try:
            response = self.ce_client.get_cost_forecast(
                TimePeriod={
                    "Start": start_date.strftime("%Y-%m-%d"),
                    "End": end_date.strftime("%Y-%m-%d"),
                },
                Metric="UNBLENDED_COST",
                Granularity="DAILY",
            )

            return response

        except Exception as e:
            logger.error(f"Error fetching cost forecast: {str(e)}")
            raise
