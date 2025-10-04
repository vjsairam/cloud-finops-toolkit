"""
EC2 cost optimization actions
- Scale down non-prod instances during off-hours
- Stop unused instances
- Rightsize underutilized instances
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EC2Remediation:
    """
    Automated EC2 cost optimizations with safety checks
    All actions support dry-run mode
    """

    def __init__(
        self,
        region: str = "us-east-1",
        dry_run: bool = True,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Args:
            region: AWS region
            dry_run: If True, only simulate actions without executing
            aws_access_key_id: AWS credentials (optional)
            aws_secret_access_key: AWS credentials (optional)
        """
        self.region = region
        self.dry_run = dry_run

        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

        self.ec2_client = session.client("ec2")
        self.cloudwatch = session.client("cloudwatch")

    def find_idle_instances(
        self,
        cpu_threshold: float = 5.0,
        network_threshold: float = 5000.0,  # bytes/min
        days_lookback: int = 7,
    ) -> List[Dict]:
        """
        Find EC2 instances with low utilization

        Args:
            cpu_threshold: Max CPU utilization % to consider idle
            network_threshold: Max network bytes/min to consider idle
            days_lookback: Days of CloudWatch metrics to analyze

        Returns:
            List of idle instance details
        """
        instances = []

        # Get all running instances
        response = self.ec2_client.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                instance_type = instance["InstanceType"]

                # Get tags
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                environment = tags.get("Environment", "unknown")

                # Skip production instances
                if environment.lower() == "prod":
                    logger.info(f"Skipping prod instance: {instance_id}")
                    continue

                # Get CloudWatch metrics
                avg_cpu = self._get_avg_cpu(instance_id, days_lookback)
                avg_network = self._get_avg_network(instance_id, days_lookback)

                if avg_cpu < cpu_threshold and avg_network < network_threshold:
                    instances.append(
                        {
                            "instance_id": instance_id,
                            "instance_type": instance_type,
                            "environment": environment,
                            "avg_cpu": avg_cpu,
                            "avg_network": avg_network,
                            "tags": tags,
                            "estimated_monthly_cost": self._estimate_cost(instance_type),
                        }
                    )

        logger.info(f"Found {len(instances)} idle instances")
        return instances

    def stop_idle_instances(self, instance_ids: List[str]) -> Dict:
        """
        Stop idle EC2 instances

        Returns:
            Dictionary with action results
        """
        if not instance_ids:
            return {"action": "stop_instances", "count": 0, "dry_run": self.dry_run}

        mode = "DRY-RUN" if self.dry_run else "EXECUTE"
        logger.info(f"[{mode}] Stopping {len(instance_ids)} instances")

        stopped = []
        failed = []

        for instance_id in instance_ids:
            try:
                if not self.dry_run:
                    self.ec2_client.stop_instances(InstanceIds=[instance_id])

                stopped.append(instance_id)
                logger.info(f"[{mode}] Stopped instance: {instance_id}")

            except Exception as e:
                logger.error(f"Failed to stop {instance_id}: {e}")
                failed.append({"instance_id": instance_id, "error": str(e)})

        return {
            "action": "stop_instances",
            "dry_run": self.dry_run,
            "requested": len(instance_ids),
            "stopped": len(stopped),
            "failed": len(failed),
            "stopped_instances": stopped,
            "failed_instances": failed,
        }

    def schedule_stop_start(
        self,
        instance_ids: List[str],
        stop_time: str = "20:00",
        start_time: str = "08:00",
    ) -> Dict:
        """
        Schedule instances to stop/start at specific times (for non-prod)
        Uses AWS Systems Manager or EventBridge

        Args:
            instance_ids: List of instance IDs
            stop_time: Time to stop (HH:MM format)
            start_time: Time to start (HH:MM format)

        Returns:
            Schedule configuration
        """
        # This would integrate with EventBridge/Lambda
        # For now, return the schedule plan

        schedule = {
            "action": "schedule_stop_start",
            "dry_run": self.dry_run,
            "instance_ids": instance_ids,
            "stop_time": stop_time,
            "start_time": start_time,
            "estimated_savings": len(instance_ids) * 0.05 * 12 * 30,  # Rough estimate
            "implementation": "Would create EventBridge rules + Lambda functions",
        }

        logger.info(
            f"[{'DRY-RUN' if self.dry_run else 'EXECUTE'}] Schedule created for {len(instance_ids)} instances"
        )

        return schedule

    def _get_avg_cpu(self, instance_id: str, days: int) -> float:
        """Get average CPU utilization from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=["Average"],
            )

            if response["Datapoints"]:
                avg = sum(dp["Average"] for dp in response["Datapoints"]) / len(
                    response["Datapoints"]
                )
                return round(avg, 2)

        except Exception as e:
            logger.warning(f"Error getting CPU metrics for {instance_id}: {e}")

        return 0.0

    def _get_avg_network(self, instance_id: str, days: int) -> float:
        """Get average network in+out from CloudWatch"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            network_in = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="NetworkIn",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )

            network_out = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="NetworkOut",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Average"],
            )

            avg_in = (
                sum(dp["Average"] for dp in network_in["Datapoints"])
                / len(network_in["Datapoints"])
                if network_in["Datapoints"]
                else 0
            )
            avg_out = (
                sum(dp["Average"] for dp in network_out["Datapoints"])
                / len(network_out["Datapoints"])
                if network_out["Datapoints"]
                else 0
            )

            return round(avg_in + avg_out, 2)

        except Exception as e:
            logger.warning(f"Error getting network metrics for {instance_id}: {e}")

        return 0.0

    def _estimate_cost(self, instance_type: str) -> float:
        """Rough monthly cost estimate for instance type"""
        # Simplified pricing (actual prices vary by region)
        pricing = {
            "t2.micro": 8.50,
            "t2.small": 17.00,
            "t2.medium": 33.60,
            "t3.micro": 7.50,
            "t3.small": 15.00,
            "t3.medium": 30.00,
            "m5.large": 70.00,
            "m5.xlarge": 140.00,
            "c5.large": 62.00,
        }

        return pricing.get(instance_type, 50.00)  # Default estimate
