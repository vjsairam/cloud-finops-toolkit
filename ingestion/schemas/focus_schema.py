"""
FOCUS (FinOps Open Cost and Usage Specification) compatible schema
https://focus.finops.org/

Common schema for normalizing multi-cloud billing data
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class FOCUSSchema:
    """
    Normalized billing record following FOCUS specification
    This schema allows consistent analysis across AWS, GCP, and Azure
    """

    # Time dimensions
    billing_period_start: datetime
    billing_period_end: datetime
    charge_period_start: datetime
    charge_period_end: datetime

    # Provider & account dimensions
    provider: str  # aws, gcp, azure
    billing_account_id: str
    billing_account_name: Optional[str] = None

    # Resource dimensions
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    resource_type: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None

    # Service dimensions
    service_name: str
    service_category: Optional[str] = None
    pricing_category: Optional[str] = None  # On-Demand, Reserved, Spot, etc.

    # Cost & pricing
    billed_cost: Decimal
    effective_cost: Optional[Decimal] = None  # After discounts/credits
    list_cost: Optional[Decimal] = None  # Before any discounts
    pricing_unit: Optional[str] = None
    pricing_quantity: Optional[Decimal] = None
    currency: str = "USD"

    # Usage
    usage_quantity: Optional[Decimal] = None
    usage_unit: Optional[str] = None

    # Tags & labels (stored as JSON/dict)
    tags: Optional[dict] = None

    # Organizational dimensions
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    environment: Optional[str] = None  # prod, staging, dev
    team: Optional[str] = None
    cost_center: Optional[str] = None

    # Commitment/savings plans
    commitment_discount_id: Optional[str] = None
    commitment_discount_type: Optional[str] = None  # reservation, savings plan
    commitment_discount_status: Optional[str] = None  # used, unused

    # Invoice & payment
    invoice_id: Optional[str] = None
    charge_type: Optional[str] = None  # usage, tax, fee, credit, refund

    # Metadata
    ingestion_time: Optional[datetime] = None
    data_source: Optional[str] = None  # cost_explorer, cur, bigquery_billing, etc.

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (datetime, Decimal)):
                result[field_name] = str(field_value)
            else:
                result[field_name] = field_value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "FOCUSSchema":
        """Create instance from dictionary"""
        # Convert string dates back to datetime
        for date_field in [
            "billing_period_start",
            "billing_period_end",
            "charge_period_start",
            "charge_period_end",
            "ingestion_time",
        ]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Convert string decimals back to Decimal
        for decimal_field in [
            "billed_cost",
            "effective_cost",
            "list_cost",
            "pricing_quantity",
            "usage_quantity",
        ]:
            if decimal_field in data and isinstance(data[decimal_field], str):
                data[decimal_field] = Decimal(data[decimal_field])

        return cls(**data)
