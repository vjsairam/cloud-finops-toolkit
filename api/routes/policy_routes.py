"""
Policy enforcement API routes
Budget and tag policy evaluation
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict
from pydantic import BaseModel

from policies import PolicyEngine, BudgetPolicy, TagGovernance
from policies.budget_policies import Budget

router = APIRouter()


class BudgetCheckRequest(BaseModel):
    team: str
    budget_limit: float
    current_spend: float
    forecast_spend: float = None


class TagValidationRequest(BaseModel):
    resource_tags: Dict[str, str]
    environment: str = None


@router.post("/budget/check")
def check_budget(request: BudgetCheckRequest):
    """
    Check if current spend is within budget policy

    Example request:
    {
        "team": "platform",
        "budget_limit": 50000,
        "current_spend": 45000,
        "forecast_spend": 48000
    }
    """

    policy = BudgetPolicy()

    # Create budget
    budget = Budget(
        name=f"{request.team}_monthly",
        limit=request.budget_limit,
        period="monthly",
        team=request.team,
    )
    policy.add_budget(budget)

    # Evaluate
    result = policy.evaluate_budget(budget.name, request.current_spend)

    return result


@router.post("/tags/validate")
def validate_tags(request: TagValidationRequest):
    """
    Validate resource tags against policy

    Example request:
    {
        "resource_tags": {
            "Environment": "prod",
            "Team": "platform",
            "CostCenter": "12345"
        },
        "environment": "prod"
    }
    """

    governance = TagGovernance()
    result = governance.validate_tags(request.resource_tags, request.environment)

    return result


@router.get("/budget/{budget_name}/forecast")
def get_budget_forecast(budget_name: str, current_spend: float, days_elapsed: int):
    """Get budget forecast and burn rate analysis"""

    policy = BudgetPolicy()

    # This would load from database
    budget = Budget(
        name=budget_name,
        limit=50000,
        period="monthly",
        team="platform",
    )
    policy.add_budget(budget)

    forecast = policy.get_budget_forecast(budget_name, current_spend, days_elapsed)

    return forecast


@router.get("/policy/opa/evaluate")
def evaluate_opa_policy(
    policy_file: str, input_data: Dict = Body(...), query: str = "data.main.allow"
):
    """
    Evaluate OPA policy with input data

    Example:
    policy_file: "budget_policy.rego"
    input_data: {...}
    """

    engine = PolicyEngine()

    try:
        result = engine.evaluate_policy(policy_file, input_data, query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
