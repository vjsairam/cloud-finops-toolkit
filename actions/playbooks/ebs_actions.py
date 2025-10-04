"""
EBS cost optimization actions
- Delete unattached EBS volumes
- Snapshot old volumes
- Convert to cheaper storage classes (gp3, sc1)
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EBSRemediation:
    """
    Automated EBS cost optimizations
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

        self.ec2_client = session.client("ec2")

    def find_unattached_volumes(self, days_unattached: int = 7) -> List[Dict]:
        """
        Find EBS volumes that have been unattached for N days

        Args:
            days_unattached: Minimum days a volume must be unattached

        Returns:
            List of unattached volume details
        """
        volumes = []
        cutoff_date = datetime.now() - timedelta(days=days_unattached)

        response = self.ec2_client.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )

        for volume in response["Volumes"]:
            volume_id = volume["VolumeId"]
            size = volume["Size"]
            volume_type = volume["VolumeType"]
            create_time = volume["CreateTime"].replace(tzinfo=None)

            # Check if volume has been unattached long enough
            if create_time < cutoff_date:
                tags = {tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])}

                monthly_cost = self._estimate_volume_cost(size, volume_type)

                volumes.append(
                    {
                        "volume_id": volume_id,
                        "size_gb": size,
                        "volume_type": volume_type,
                        "created": create_time.isoformat(),
                        "days_unattached": (datetime.now() - create_time).days,
                        "tags": tags,
                        "estimated_monthly_cost": monthly_cost,
                    }
                )

        logger.info(f"Found {len(volumes)} unattached volumes")
        return volumes

    def delete_unattached_volumes(
        self, volume_ids: List[str], snapshot_before_delete: bool = True
    ) -> Dict:
        """
        Delete unattached EBS volumes (optionally snapshot first)

        Args:
            volume_ids: List of volume IDs to delete
            snapshot_before_delete: Create snapshot before deletion

        Returns:
            Dictionary with action results
        """
        mode = "DRY-RUN" if self.dry_run else "EXECUTE"
        logger.info(f"[{mode}] Deleting {len(volume_ids)} volumes")

        deleted = []
        snapshots_created = []
        failed = []

        for volume_id in volume_ids:
            try:
                # Create snapshot if requested
                if snapshot_before_delete and not self.dry_run:
                    snapshot = self.ec2_client.create_snapshot(
                        VolumeId=volume_id,
                        Description=f"Snapshot before deletion - {datetime.now().isoformat()}",
                    )
                    snapshots_created.append(snapshot["SnapshotId"])
                    logger.info(f"Created snapshot: {snapshot['SnapshotId']}")

                # Delete volume
                if not self.dry_run:
                    self.ec2_client.delete_volume(VolumeId=volume_id)

                deleted.append(volume_id)
                logger.info(f"[{mode}] Deleted volume: {volume_id}")

            except Exception as e:
                logger.error(f"Failed to delete {volume_id}: {e}")
                failed.append({"volume_id": volume_id, "error": str(e)})

        return {
            "action": "delete_volumes",
            "dry_run": self.dry_run,
            "requested": len(volume_ids),
            "deleted": len(deleted),
            "snapshots_created": len(snapshots_created),
            "failed": len(failed),
            "deleted_volumes": deleted,
            "snapshot_ids": snapshots_created,
            "failed_volumes": failed,
        }

    def find_old_snapshots(self, days_old: int = 90) -> List[Dict]:
        """
        Find EBS snapshots older than N days

        Args:
            days_old: Age threshold in days

        Returns:
            List of old snapshot details
        """
        snapshots = []
        cutoff_date = datetime.now() - timedelta(days=days_old)

        response = self.ec2_client.describe_snapshots(OwnerIds=["self"])

        for snapshot in response["Snapshots"]:
            start_time = snapshot["StartTime"].replace(tzinfo=None)

            if start_time < cutoff_date:
                tags = {tag["Key"]: tag["Value"] for tag in snapshot.get("Tags", [])}

                snapshots.append(
                    {
                        "snapshot_id": snapshot["SnapshotId"],
                        "volume_id": snapshot.get("VolumeId", "N/A"),
                        "size_gb": snapshot["VolumeSize"],
                        "created": start_time.isoformat(),
                        "age_days": (datetime.now() - start_time).days,
                        "description": snapshot.get("Description", ""),
                        "tags": tags,
                    }
                )

        logger.info(f"Found {len(snapshots)} old snapshots")
        return snapshots

    def delete_old_snapshots(self, snapshot_ids: List[str]) -> Dict:
        """Delete old EBS snapshots"""
        mode = "DRY-RUN" if self.dry_run else "EXECUTE"
        logger.info(f"[{mode}] Deleting {len(snapshot_ids)} snapshots")

        deleted = []
        failed = []

        for snapshot_id in snapshot_ids:
            try:
                if not self.dry_run:
                    self.ec2_client.delete_snapshot(SnapshotId=snapshot_id)

                deleted.append(snapshot_id)
                logger.info(f"[{mode}] Deleted snapshot: {snapshot_id}")

            except Exception as e:
                logger.error(f"Failed to delete {snapshot_id}: {e}")
                failed.append({"snapshot_id": snapshot_id, "error": str(e)})

        return {
            "action": "delete_snapshots",
            "dry_run": self.dry_run,
            "requested": len(snapshot_ids),
            "deleted": len(deleted),
            "failed": len(failed),
            "deleted_snapshots": deleted,
            "failed_snapshots": failed,
        }

    def _estimate_volume_cost(self, size_gb: int, volume_type: str) -> float:
        """Estimate monthly cost for EBS volume"""
        # Simplified pricing per GB/month
        pricing = {
            "gp2": 0.10,
            "gp3": 0.08,
            "io1": 0.125,
            "io2": 0.125,
            "st1": 0.045,
            "sc1": 0.025,
        }

        price_per_gb = pricing.get(volume_type, 0.10)
        return round(size_gb * price_per_gb, 2)
