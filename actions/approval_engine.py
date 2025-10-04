"""
Approval engine for gating automated remediation actions
Supports manual approval, auto-approval based on rules, and audit trail
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of approval request"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalEngine:
    """
    Manages approval workflow for remediation actions
    Stores approval requests and enforces approval before execution
    """

    def __init__(self):
        self.approval_requests: Dict[str, Dict] = {}
        self.approval_log: List[Dict] = []

        # Auto-approval rules
        self.auto_approval_rules = {
            "max_cost_impact": 100.0,  # Auto-approve if savings < $100
            "allowed_actions": [
                "delete_snapshots",
                "stop_instances",
            ],  # Safe actions
            "require_manual_approval": [
                "delete_volumes",
                "terminate_instances",
            ],  # Risky actions
        }

    def request_approval(
        self,
        action_type: str,
        resources: List[str],
        estimated_savings: float,
        risk_level: str = "medium",
        requestor: str = "system",
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create an approval request

        Args:
            action_type: Type of action (e.g., stop_instances, delete_volumes)
            resources: List of resource IDs affected
            estimated_savings: Estimated monthly savings
            risk_level: low, medium, high
            requestor: Who is requesting the action
            metadata: Additional context

        Returns:
            Approval request ID
        """
        import uuid

        request_id = str(uuid.uuid4())

        # Determine if auto-approval applies
        auto_approved = self._check_auto_approval(
            action_type, estimated_savings, risk_level
        )

        request = {
            "request_id": request_id,
            "action_type": action_type,
            "resources": resources,
            "resource_count": len(resources),
            "estimated_savings": estimated_savings,
            "risk_level": risk_level,
            "requestor": requestor,
            "status": (
                ApprovalStatus.APPROVED.value
                if auto_approved
                else ApprovalStatus.PENDING.value
            ),
            "auto_approved": auto_approved,
            "created_at": datetime.now().isoformat(),
            "approved_at": datetime.now().isoformat() if auto_approved else None,
            "approved_by": "system" if auto_approved else None,
            "metadata": metadata or {},
        }

        self.approval_requests[request_id] = request

        if auto_approved:
            logger.info(
                f"Auto-approved action: {action_type} (request_id: {request_id})"
            )
        else:
            logger.info(
                f"Approval required for: {action_type} (request_id: {request_id})"
            )

        return request_id

    def approve(self, request_id: str, approver: str, comment: str = "") -> Dict:
        """Manually approve a request"""
        if request_id not in self.approval_requests:
            raise ValueError(f"Approval request not found: {request_id}")

        request = self.approval_requests[request_id]

        if request["status"] != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Request {request_id} is not pending (status: {request['status']})"
            )

        request["status"] = ApprovalStatus.APPROVED.value
        request["approved_by"] = approver
        request["approved_at"] = datetime.now().isoformat()
        request["approval_comment"] = comment

        # Log approval
        self.approval_log.append(
            {
                "request_id": request_id,
                "action": "approve",
                "approver": approver,
                "timestamp": datetime.now().isoformat(),
                "comment": comment,
            }
        )

        logger.info(f"Request {request_id} approved by {approver}")

        return request

    def reject(self, request_id: str, approver: str, reason: str = "") -> Dict:
        """Reject a request"""
        if request_id not in self.approval_requests:
            raise ValueError(f"Approval request not found: {request_id}")

        request = self.approval_requests[request_id]

        if request["status"] != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Request {request_id} is not pending (status: {request['status']})"
            )

        request["status"] = ApprovalStatus.REJECTED.value
        request["rejected_by"] = approver
        request["rejected_at"] = datetime.now().isoformat()
        request["rejection_reason"] = reason

        # Log rejection
        self.approval_log.append(
            {
                "request_id": request_id,
                "action": "reject",
                "approver": approver,
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
            }
        )

        logger.info(f"Request {request_id} rejected by {approver}: {reason}")

        return request

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved"""
        if request_id not in self.approval_requests:
            return False

        return (
            self.approval_requests[request_id]["status"]
            == ApprovalStatus.APPROVED.value
        )

    def get_pending_approvals(self) -> List[Dict]:
        """Get all pending approval requests"""
        return [
            req
            for req in self.approval_requests.values()
            if req["status"] == ApprovalStatus.PENDING.value
        ]

    def _check_auto_approval(
        self, action_type: str, estimated_savings: float, risk_level: str
    ) -> bool:
        """
        Determine if action qualifies for auto-approval

        Rules:
        - Low-risk actions with savings < threshold: auto-approve
        - Specific safe actions: auto-approve
        - High-risk actions: always require manual approval
        """
        # High-risk always requires approval
        if risk_level == "high":
            return False

        # Require manual approval for dangerous actions
        if action_type in self.auto_approval_rules["require_manual_approval"]:
            return False

        # Auto-approve safe actions with low cost impact
        if (
            action_type in self.auto_approval_rules["allowed_actions"]
            and estimated_savings < self.auto_approval_rules["max_cost_impact"]
        ):
            return True

        return False

    def generate_approval_summary(self) -> str:
        """Generate summary of approval activity"""
        total = len(self.approval_requests)
        pending = len(
            [
                r
                for r in self.approval_requests.values()
                if r["status"] == ApprovalStatus.PENDING.value
            ]
        )
        approved = len(
            [
                r
                for r in self.approval_requests.values()
                if r["status"] == ApprovalStatus.APPROVED.value
            ]
        )
        rejected = len(
            [
                r
                for r in self.approval_requests.values()
                if r["status"] == ApprovalStatus.REJECTED.value
            ]
        )

        summary = f"""
Approval Summary
================
Total Requests: {total}
Pending: {pending}
Approved: {approved}
Rejected: {rejected}
"""
        return summary
