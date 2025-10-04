"""
Policy engine for evaluating OPA/Rego policies
Integrates with deployment pipelines for cost governance
"""

import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Evaluates policies using OPA (Open Policy Agent)
    Can be used in CI/CD to gate deployments based on cost/budget rules
    """

    def __init__(self, policy_dir: str = "./policies/rego"):
        """
        Args:
            policy_dir: Directory containing .rego policy files
        """
        self.policy_dir = Path(policy_dir)
        self._verify_opa_installed()

    def _verify_opa_installed(self):
        """Check if OPA is installed and available"""
        try:
            result = subprocess.run(
                ["opa", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"OPA version: {result.stdout.strip()}")
            else:
                logger.warning(
                    "OPA not found. Install from https://www.openpolicyagent.org/docs/latest/#running-opa"
                )
        except FileNotFoundError:
            logger.warning(
                "OPA not installed. Policy evaluation will use Python fallback."
            )
        except Exception as e:
            logger.warning(f"Error checking OPA: {e}")

    def evaluate_policy(
        self, policy_file: str, input_data: Dict, query: str = "data.main.allow"
    ) -> Dict:
        """
        Evaluate a policy against input data using OPA

        Args:
            policy_file: Path to .rego policy file
            input_data: JSON-serializable input data
            query: OPA query to evaluate (default: data.main.allow)

        Returns:
            Dictionary with result, allowed (bool), and violations (list)
        """
        policy_path = self.policy_dir / policy_file

        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_path}")

        # Write input data to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as input_file:
            json.dump(input_data, input_file)
            input_path = input_file.name

        try:
            # Run OPA eval
            cmd = [
                "opa",
                "eval",
                "--data",
                str(policy_path),
                "--input",
                input_path,
                "--format",
                "json",
                query,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.error(f"OPA eval failed: {result.stderr}")
                return {
                    "allowed": False,
                    "error": result.stderr,
                    "violations": ["Policy evaluation failed"],
                }

            # Parse OPA output
            opa_output = json.loads(result.stdout)

            if opa_output.get("result"):
                policy_result = opa_output["result"][0].get("expressions", [{}])[0].get(
                    "value", False
                )

                return {
                    "allowed": bool(policy_result),
                    "result": policy_result,
                    "violations": [] if policy_result else ["Policy check failed"],
                }
            else:
                return {
                    "allowed": False,
                    "violations": ["No policy result returned"],
                }

        except FileNotFoundError:
            # Fallback to Python evaluation
            logger.warning("OPA not available, using Python fallback")
            return self._python_fallback_evaluation(policy_file, input_data)

        except Exception as e:
            logger.error(f"Error evaluating policy: {e}")
            return {
                "allowed": False,
                "error": str(e),
                "violations": [f"Policy evaluation error: {e}"],
            }

        finally:
            # Clean up temp file
            import os

            try:
                os.unlink(input_path)
            except:
                pass

    def _python_fallback_evaluation(
        self, policy_file: str, input_data: Dict
    ) -> Dict:
        """
        Fallback policy evaluation using Python (when OPA not available)
        Implements basic budget and tag checks
        """
        violations = []

        # Budget check
        if "budget" in input_data:
            current_spend = input_data.get("current_spend", 0)
            budget_limit = input_data["budget"].get("limit", 0)
            threshold = input_data["budget"].get("threshold", 0.9)

            if current_spend > budget_limit * threshold:
                violations.append(
                    f"Budget threshold exceeded: ${current_spend:.2f} > ${budget_limit * threshold:.2f}"
                )

        # Tag check
        if "required_tags" in input_data:
            resource_tags = input_data.get("tags", {})
            required_tags = input_data["required_tags"]

            missing_tags = [tag for tag in required_tags if tag not in resource_tags]
            if missing_tags:
                violations.append(f"Missing required tags: {', '.join(missing_tags)}")

        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "fallback": True,
        }

    def evaluate_budget_policy(self, budget_data: Dict) -> Dict:
        """
        Evaluate budget policy

        Expected input:
        {
            "team": "platform",
            "budget": {"limit": 50000, "period": "monthly"},
            "current_spend": 45000,
            "forecast_spend": 52000
        }
        """
        return self.evaluate_policy(
            "budget_policy.rego", budget_data, "data.budget.allow"
        )

    def evaluate_tag_policy(self, resource_data: Dict) -> Dict:
        """
        Evaluate tag governance policy

        Expected input:
        {
            "resource_type": "ec2",
            "tags": {"Environment": "prod", "Team": "platform"},
            "required_tags": ["Environment", "Team", "CostCenter"]
        }
        """
        return self.evaluate_policy(
            "tag_policy.rego", resource_data, "data.tags.allow"
        )

    def create_ci_check(self, policy_type: str = "budget") -> str:
        """
        Generate a CI/CD script for policy checking

        Returns:
            Shell script content for GitHub Actions or similar
        """
        if policy_type == "budget":
            script = """#!/bin/bash
# Budget Policy CI Check
# Add to GitHub Actions workflow

set -e

echo "Fetching current spend..."
CURRENT_SPEND=$(python -m api.routes.cost_routes get_current_spend --team=$TEAM)

echo "Evaluating budget policy..."
cat > input.json <<EOF
{
  "team": "$TEAM",
  "budget": {"limit": $BUDGET_LIMIT, "period": "monthly"},
  "current_spend": $CURRENT_SPEND,
  "forecast_spend": $FORECAST_SPEND
}
EOF

opa eval --data policies/rego/budget_policy.rego --input input.json 'data.budget.allow'

if [ $? -ne 0 ]; then
  echo "❌ Budget policy check failed"
  exit 1
else
  echo "✅ Budget policy check passed"
fi
"""
        else:
            script = """#!/bin/bash
# Tag Policy CI Check

set -e

echo "Checking infrastructure tags..."
python -m policies.ci.tag_check --terraform-dir=$TF_DIR

if [ $? -ne 0 ]; then
  echo "❌ Tag policy check failed"
  exit 1
else
  echo "✅ Tag policy check passed"
fi
"""

        return script
