"""
Remediation action API routes
Manage and execute cost optimization actions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from pydantic import BaseModel

from actions import EC2Remediation, EBSRemediation, RDSRemediation, ApprovalEngine

router = APIRouter()

# Initialize engines
approval_engine = ApprovalEngine()


class ActionRequest(BaseModel):
    resource_ids: List[str]
    dry_run: bool = True


@router.get("/ec2/idle")
def find_idle_ec2(
    cpu_threshold: float = Query(5.0, description="Max CPU % to consider idle"),
    days_lookback: int = Query(7, description="Days of metrics to analyze"),
):
    """Find idle EC2 instances"""

    remediation = EC2Remediation(dry_run=True)
    idle_instances = remediation.find_idle_instances(
        cpu_threshold=cpu_threshold, days_lookback=days_lookback
    )

    total_savings = sum(inst["estimated_monthly_cost"] for inst in idle_instances)

    return {
        "action": "find_idle_ec2",
        "instances_found": len(idle_instances),
        "estimated_monthly_savings": total_savings,
        "instances": idle_instances,
    }


@router.post("/ec2/stop")
def stop_ec2_instances(request: ActionRequest):
    """Stop EC2 instances (requires approval)"""

    # Request approval first
    request_id = approval_engine.request_approval(
        action_type="stop_instances",
        resources=request.resource_ids,
        estimated_savings=100.0,  # Calculate actual savings
        risk_level="medium",
    )

    # Check if auto-approved
    if approval_engine.is_approved(request_id):
        remediation = EC2Remediation(dry_run=request.dry_run)
        result = remediation.stop_idle_instances(request.resource_ids)
        result["approval_request_id"] = request_id
        result["auto_approved"] = True
        return result
    else:
        return {
            "status": "pending_approval",
            "approval_request_id": request_id,
            "message": f"Action requires manual approval. Use /approval/{request_id}/approve to proceed.",
        }


@router.get("/ebs/unattached")
def find_unattached_ebs(
    days_unattached: int = Query(7, description="Minimum days unattached"),
):
    """Find unattached EBS volumes"""

    remediation = EBSRemediation(dry_run=True)
    volumes = remediation.find_unattached_volumes(days_unattached=days_unattached)

    total_savings = sum(vol["estimated_monthly_cost"] for vol in volumes)

    return {
        "action": "find_unattached_ebs",
        "volumes_found": len(volumes),
        "estimated_monthly_savings": total_savings,
        "volumes": volumes,
    }


@router.post("/ebs/delete")
def delete_ebs_volumes(request: ActionRequest):
    """Delete unattached EBS volumes (requires approval)"""

    request_id = approval_engine.request_approval(
        action_type="delete_volumes",
        resources=request.resource_ids,
        estimated_savings=50.0,
        risk_level="high",  # Deletion is risky
    )

    if approval_engine.is_approved(request_id):
        remediation = EBSRemediation(dry_run=request.dry_run)
        result = remediation.delete_unattached_volumes(request.resource_ids)
        result["approval_request_id"] = request_id
        return result
    else:
        return {
            "status": "pending_approval",
            "approval_request_id": request_id,
            "message": "Deletion requires manual approval due to high risk.",
        }


@router.get("/rds/idle")
def find_idle_rds(
    cpu_threshold: float = Query(5.0, description="Max CPU % to consider idle"),
    days_lookback: int = Query(7, description="Days of metrics"),
):
    """Find idle RDS instances"""

    remediation = RDSRemediation(dry_run=True)
    databases = remediation.find_idle_databases(
        cpu_threshold=cpu_threshold, days_lookback=days_lookback
    )

    total_savings = sum(db["estimated_monthly_cost"] for db in databases)

    return {
        "action": "find_idle_rds",
        "databases_found": len(databases),
        "estimated_monthly_savings": total_savings,
        "databases": databases,
    }


@router.get("/approval/pending")
def get_pending_approvals():
    """Get all pending approval requests"""

    pending = approval_engine.get_pending_approvals()

    return {"pending_approvals": len(pending), "requests": pending}


@router.post("/approval/{request_id}/approve")
def approve_action(request_id: str, approver: str = Query(..., description="Approver name")):
    """Approve a pending action"""

    try:
        result = approval_engine.approve(request_id, approver)
        return {"status": "approved", "request": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/approval/{request_id}/reject")
def reject_action(
    request_id: str,
    approver: str = Query(..., description="Approver name"),
    reason: str = Query(..., description="Rejection reason"),
):
    """Reject a pending action"""

    try:
        result = approval_engine.reject(request_id, approver, reason)
        return {"status": "rejected", "request": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
