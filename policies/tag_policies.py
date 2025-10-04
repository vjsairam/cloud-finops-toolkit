"""
Tag governance and validation
"""

from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class TagGovernance:
    """
    Enforces tag policies across cloud resources
    Validates tag presence and values
    """

    def __init__(
        self,
        required_tags: List[str] = None,
        environment_specific_tags: Dict[str, List[str]] = None,
    ):
        """
        Args:
            required_tags: Tags required on all resources
            environment_specific_tags: Additional tags required per environment
        """
        self.required_tags = required_tags or [
            "Environment",
            "Team",
            "CostCenter",
        ]

        self.environment_specific_tags = environment_specific_tags or {
            "prod": ["Owner", "Backup"],
            "staging": ["Owner"],
        }

    def validate_tags(self, resource_tags: Dict[str, str], environment: str = None) -> Dict:
        """
        Validate resource tags against policy

        Args:
            resource_tags: Dictionary of tags on the resource
            environment: Environment name (prod, staging, dev, etc.)

        Returns:
            Validation result with violations
        """
        violations = []

        # Check required tags
        missing_tags = [
            tag for tag in self.required_tags if tag not in resource_tags
        ]
        if missing_tags:
            violations.append(f"Missing required tags: {', '.join(missing_tags)}")

        # Check for empty values
        empty_tags = [
            key for key, value in resource_tags.items() if not value or value.strip() == ""
        ]
        if empty_tags:
            violations.append(f"Tags have empty values: {', '.join(empty_tags)}")

        # Check environment-specific tags
        if environment and environment in self.environment_specific_tags:
            env_required = self.environment_specific_tags[environment]
            missing_env_tags = [
                tag for tag in env_required if tag not in resource_tags
            ]
            if missing_env_tags:
                violations.append(
                    f"Missing {environment} environment tags: {', '.join(missing_env_tags)}"
                )

        # Validate CostCenter is numeric
        if "CostCenter" in resource_tags:
            cost_center = resource_tags["CostCenter"]
            if not cost_center.isdigit():
                violations.append(f"CostCenter must be numeric, got: {cost_center}")

        # Validate Environment value
        if "Environment" in resource_tags:
            env = resource_tags["Environment"].lower()
            valid_envs = ["prod", "staging", "dev", "test", "qa"]
            if env not in valid_envs:
                violations.append(
                    f"Invalid Environment value: {env}. Must be one of: {', '.join(valid_envs)}"
                )

        result = {
            "valid": len(violations) == 0,
            "violations": violations,
            "tags_checked": len(resource_tags),
            "message": (
                "All tags valid"
                if len(violations) == 0
                else f"{len(violations)} tag policy violations found"
            ),
        }

        return result

    def audit_untagged_resources(
        self, resources: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Audit resources for tag compliance

        Args:
            resources: List of resources with 'id', 'tags', and optionally 'cost'

        Returns:
            Dictionary categorizing compliant vs non-compliant resources
        """
        compliant = []
        non_compliant = []
        untagged_cost = 0.0

        for resource in resources:
            resource_id = resource.get("id", "unknown")
            tags = resource.get("tags", {})
            cost = resource.get("cost", 0.0)

            validation = self.validate_tags(tags)

            resource_result = {
                "id": resource_id,
                "tags": tags,
                "cost": cost,
                "violations": validation["violations"],
            }

            if validation["valid"]:
                compliant.append(resource_result)
            else:
                non_compliant.append(resource_result)
                untagged_cost += cost

        return {
            "total_resources": len(resources),
            "compliant": len(compliant),
            "non_compliant": len(non_compliant),
            "compliance_rate": (
                len(compliant) / len(resources) * 100 if resources else 0
            ),
            "untagged_cost": untagged_cost,
            "non_compliant_resources": non_compliant[:10],  # Top 10 violations
        }

    def generate_tagging_report(self, audit_results: Dict) -> str:
        """Generate a human-readable tagging compliance report"""
        lines = [
            "=" * 70,
            "TAG GOVERNANCE AUDIT REPORT",
            "=" * 70,
            "",
            f"Total Resources: {audit_results['total_resources']}",
            f"Compliant: {audit_results['compliant']}",
            f"Non-Compliant: {audit_results['non_compliant']}",
            f"Compliance Rate: {audit_results['compliance_rate']:.1f}%",
            f"Cost of Untagged Resources: ${audit_results['untagged_cost']:.2f}",
            "",
        ]

        if audit_results["non_compliant_resources"]:
            lines.append("TOP VIOLATIONS:")
            lines.append("-" * 70)

            for resource in audit_results["non_compliant_resources"]:
                lines.append(f"Resource ID: {resource['id']}")
                lines.append(f"  Cost: ${resource['cost']:.2f}")
                lines.append(f"  Violations:")
                for violation in resource["violations"]:
                    lines.append(f"    - {violation}")
                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def suggest_tag_fixes(self, resource: Dict) -> List[str]:
        """
        Suggest tag fixes for a non-compliant resource

        Returns:
            List of suggested actions
        """
        suggestions = []
        tags = resource.get("tags", {})

        # Check missing required tags
        for tag in self.required_tags:
            if tag not in tags:
                suggestions.append(f"Add required tag: {tag}")

        # Check empty values
        for key, value in tags.items():
            if not value or value.strip() == "":
                suggestions.append(f"Set value for tag: {key}")

        return suggestions
