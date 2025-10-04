"""
RDS cost optimization actions
- Rightsize underutilized databases
- Stop non-prod databases during off-hours
- Identify idle databases
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RDSRemediation:
    """
    Automated RDS cost optimizations
    """

    def __init__(
        self,
        region: str = "us-east-1",
        dry_run: bool = True,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.region = region
        self.dry_run = dry_run

        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

        self.rds_client = session.client("rds")
        self.cloudwatch = session.client("cloudwatch")

    def find_idle_databases(
        self,
        cpu_threshold: float = 5.0,
        connection_threshold: int = 5,
        days_lookback: int = 7,
    ) -> List[Dict]:
        """
        Find RDS instances with low utilization

        Args:
            cpu_threshold: Max CPU % to consider idle
            connection_threshold: Max DB connections to consider idle
            days_lookback: Days of metrics to analyze

        Returns:
            List of idle database details
        """
        databases = []

        response = self.rds_client.describe_db_instances()

        for db in response["DBInstances"]:
            db_id = db["DBInstanceIdentifier"]
            db_class = db["DBInstanceClass"]
            engine = db["Engine"]
            status = db["DBInstanceStatus"]

            if status != "available":
                continue

            # Get tags
            arn = db["DBInstanceArn"]
            tags_response = self.rds_client.list_tags_for_resource(ResourceName=arn)
            tags = {tag["Key"]: tag["Value"] for tag in tags_response["TagList"]}

            environment = tags.get("Environment", "unknown")

            # Skip production
            if environment.lower() == "prod":
                continue

            # Get CloudWatch metrics
            avg_cpu = self._get_avg_cpu(db_id, days_lookback)
            avg_connections = self._get_avg_connections(db_id, days_lookback)

            if avg_cpu < cpu_threshold and avg_connections < connection_threshold:
                databases.append(
                    {
                        "db_identifier": db_id,
                        "db_class": db_class,
                        "engine": engine,
                        "environment": environment,
                        "avg_cpu": avg_cpu,
                        "avg_connections": avg_connections,
                        "tags": tags,
                        "estimated_monthly_cost": self._estimate_cost(db_class),
                    }
                )

        logger.info(f"Found {len(databases)} idle databases")
        return databases

    def stop_idle_databases(self, db_identifiers: List[str]) -> Dict:
        """Stop idle RDS instances (non-prod only)"""
        mode = "DRY-RUN" if self.dry_run else "EXECUTE"
        logger.info(f"[{mode}] Stopping {len(db_identifiers)} databases")

        stopped = []
        failed = []

        for db_id in db_identifiers:
            try:
                if not self.dry_run:
                    self.rds_client.stop_db_instance(DBInstanceIdentifier=db_id)

                stopped.append(db_id)
                logger.info(f"[{mode}] Stopped database: {db_id}")

            except Exception as e:
                logger.error(f"Failed to stop {db_id}: {e}")
                failed.append({"db_identifier": db_id, "error": str(e)})

        return {
            "action": "stop_databases",
            "dry_run": self.dry_run,
            "requested": len(db_identifiers),
            "stopped": len(stopped),
            "failed": len(failed),
            "stopped_databases": stopped,
            "failed_databases": failed,
        }

    def _get_avg_cpu(self, db_id: str, days: int) -> float:
        """Get average CPU utilization from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )

            if response["Datapoints"]:
                avg = sum(dp["Average"] for dp in response["Datapoints"]) / len(
                    response["Datapoints"]
                )
                return round(avg, 2)

        except Exception as e:
            logger.warning(f"Error getting CPU metrics for {db_id}: {e}")

        return 0.0

    def _get_avg_connections(self, db_id: str, days: int) -> float:
        """Get average database connections from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="DatabaseConnections",
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )

            if response["Datapoints"]:
                avg = sum(dp["Average"] for dp in response["Datapoints"]) / len(
                    response["Datapoints"]
                )
                return round(avg, 2)

        except Exception as e:
            logger.warning(f"Error getting connection metrics for {db_id}: {e}")

        return 0.0

    def _estimate_cost(self, db_class: str) -> float:
        """Rough monthly cost estimate for DB instance class"""
        pricing = {
            "db.t2.micro": 15.00,
            "db.t2.small": 30.00,
            "db.t3.micro": 14.00,
            "db.t3.small": 28.00,
            "db.t3.medium": 56.00,
            "db.m5.large": 140.00,
            "db.m5.xlarge": 280.00,
            "db.r5.large": 180.00,
        }

        return pricing.get(db_class, 100.00)
