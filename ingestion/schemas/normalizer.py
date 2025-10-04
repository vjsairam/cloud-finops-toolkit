"""
Normalizes billing data from AWS, GCP, and Azure into common FOCUS schema
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List
import logging

from .focus_schema import FOCUSSchema

logger = logging.getLogger(__name__)


class BillingNormalizer:
    """
    Transforms provider-specific billing data into normalized FOCUS schema
    Handles field mapping, unit conversion, and tag normalization
    """

    @staticmethod
    def normalize_aws(raw_data: Dict) -> FOCUSSchema:
        """
        Normalize AWS Cost Explorer or CUR data

        Expected fields from AWS:
        - date, service, cost, usage, currency
        - Optional: resource_id, tags, pricing_category
        """
        try:
            charge_date = (
                datetime.strptime(raw_data["date"], "%Y-%m-%d")
                if isinstance(raw_data["date"], str)
                else raw_data["date"]
            )

            # Extract tags if present
            tags = raw_data.get("tags", {})
            if isinstance(tags, str):
                # Parse tag string if needed
                import json

                try:
                    tags = json.loads(tags)
                except:
                    tags = {}

            return FOCUSSchema(
                # Time
                billing_period_start=charge_date,
                billing_period_end=charge_date,
                charge_period_start=charge_date,
                charge_period_end=charge_date,
                # Provider
                provider="aws",
                billing_account_id=raw_data.get("account_id", "unknown"),
                billing_account_name=raw_data.get("account_name"),
                # Resource
                resource_id=raw_data.get("resource_id"),
                resource_name=raw_data.get("resource_name"),
                resource_type=raw_data.get("usage_type"),
                region=raw_data.get("region"),
                availability_zone=raw_data.get("availability_zone"),
                # Service
                service_name=raw_data.get("service", "Unknown"),
                service_category=BillingNormalizer._categorize_aws_service(
                    raw_data.get("service", "")
                ),
                pricing_category=raw_data.get("pricing_category", "On-Demand"),
                # Cost
                billed_cost=Decimal(str(raw_data.get("cost", 0))),
                effective_cost=Decimal(str(raw_data.get("effective_cost", raw_data.get("cost", 0)))),
                list_cost=Decimal(str(raw_data.get("list_cost", raw_data.get("cost", 0)))),
                currency=raw_data.get("currency", "USD"),
                # Usage
                usage_quantity=Decimal(str(raw_data.get("usage", 0))) if raw_data.get("usage") else None,
                usage_unit=raw_data.get("usage_unit"),
                # Tags
                tags=tags,
                environment=tags.get("Environment") or tags.get("environment") or tags.get("env"),
                team=tags.get("Team") or tags.get("team"),
                cost_center=tags.get("CostCenter") or tags.get("cost_center"),
                # Metadata
                ingestion_time=datetime.now(),
                data_source="aws_cost_explorer",
            )

        except Exception as e:
            logger.error(f"Error normalizing AWS data: {str(e)}, data: {raw_data}")
            raise

    @staticmethod
    def normalize_gcp(raw_data: Dict) -> FOCUSSchema:
        """
        Normalize GCP BigQuery Billing data

        Expected fields from GCP:
        - date, service, cost, usage, currency
        - Optional: project_id, project_name, sku, labels
        """
        try:
            charge_date = (
                datetime.strptime(str(raw_data["date"]), "%Y-%m-%d")
                if isinstance(raw_data["date"], str)
                else raw_data["date"]
            )

            # Parse labels (GCP's version of tags)
            labels = raw_data.get("labels", {})

            return FOCUSSchema(
                # Time
                billing_period_start=charge_date,
                billing_period_end=charge_date,
                charge_period_start=charge_date,
                charge_period_end=charge_date,
                # Provider
                provider="gcp",
                billing_account_id=raw_data.get("billing_account_id", "unknown"),
                billing_account_name=raw_data.get("billing_account_name"),
                # Resource
                resource_id=raw_data.get("resource_name"),
                resource_name=raw_data.get("resource_name"),
                resource_type=raw_data.get("sku"),
                region=raw_data.get("location") or raw_data.get("region"),
                availability_zone=raw_data.get("zone"),
                # Service
                service_name=raw_data.get("service", "Unknown"),
                service_category=BillingNormalizer._categorize_gcp_service(
                    raw_data.get("service", "")
                ),
                pricing_category=raw_data.get("pricing_category", "On-Demand"),
                # Cost
                billed_cost=Decimal(str(raw_data.get("cost", 0))),
                effective_cost=Decimal(str(raw_data.get("cost", 0))),  # GCP applies credits automatically
                currency=raw_data.get("currency", "USD"),
                # Usage
                usage_quantity=Decimal(str(raw_data.get("usage", 0))) if raw_data.get("usage") else None,
                usage_unit=raw_data.get("usage_unit") or raw_data.get("unit"),
                # Project
                project_id=raw_data.get("project_id"),
                project_name=raw_data.get("project_name"),
                # Tags/Labels
                tags=labels,
                environment=labels.get("environment") or labels.get("env"),
                team=labels.get("team"),
                cost_center=labels.get("cost_center"),
                # Metadata
                ingestion_time=datetime.now(),
                data_source="gcp_bigquery_billing",
            )

        except Exception as e:
            logger.error(f"Error normalizing GCP data: {str(e)}, data: {raw_data}")
            raise

    @staticmethod
    def normalize_azure(raw_data: Dict) -> FOCUSSchema:
        """
        Normalize Azure Cost Management data

        Expected fields from Azure:
        - date, service, meter_category, cost, usage, currency
        - Optional: resource_group, location, tags
        """
        try:
            charge_date = (
                datetime.strptime(str(raw_data["date"]), "%Y-%m-%d")
                if isinstance(raw_data["date"], str)
                else raw_data["date"]
            )

            # Parse tags
            tags = raw_data.get("tags", {})

            return FOCUSSchema(
                # Time
                billing_period_start=charge_date,
                billing_period_end=charge_date,
                charge_period_start=charge_date,
                charge_period_end=charge_date,
                # Provider
                provider="azure",
                billing_account_id=raw_data.get("subscription_id", "unknown"),
                billing_account_name=raw_data.get("subscription_name"),
                # Resource
                resource_id=raw_data.get("resource_id"),
                resource_name=raw_data.get("resource_name"),
                resource_type=raw_data.get("meter_category"),
                region=raw_data.get("location") or raw_data.get("region"),
                # Service
                service_name=raw_data.get("service", "Unknown"),
                service_category=BillingNormalizer._categorize_azure_service(
                    raw_data.get("service", "")
                ),
                pricing_category=raw_data.get("pricing_category", "On-Demand"),
                # Cost
                billed_cost=Decimal(str(raw_data.get("cost", 0))),
                effective_cost=Decimal(str(raw_data.get("cost", 0))),
                currency=raw_data.get("currency", "USD"),
                # Usage
                usage_quantity=Decimal(str(raw_data.get("usage", 0))) if raw_data.get("usage") else None,
                usage_unit=raw_data.get("usage_unit") or raw_data.get("unit_of_measure"),
                # Project (Resource Group in Azure)
                project_name=raw_data.get("resource_group"),
                # Tags
                tags=tags,
                environment=tags.get("Environment") or tags.get("environment"),
                team=tags.get("Team") or tags.get("team"),
                cost_center=tags.get("CostCenter") or tags.get("cost_center"),
                # Metadata
                ingestion_time=datetime.now(),
                data_source="azure_cost_management",
            )

        except Exception as e:
            logger.error(f"Error normalizing Azure data: {str(e)}, data: {raw_data}")
            raise

    @staticmethod
    def _categorize_aws_service(service_name: str) -> str:
        """Map AWS service to high-level category"""
        service_lower = service_name.lower()

        if any(x in service_lower for x in ["ec2", "ebs", "elastic compute"]):
            return "Compute"
        elif any(x in service_lower for x in ["s3", "glacier", "storage"]):
            return "Storage"
        elif any(x in service_lower for x in ["rds", "dynamodb", "redshift", "database"]):
            return "Database"
        elif any(x in service_lower for x in ["cloudfront", "route53", "vpc", "network"]):
            return "Networking"
        elif any(x in service_lower for x in ["lambda", "fargate"]):
            return "Serverless"
        elif any(x in service_lower for x in ["sagemaker", "bedrock"]):
            return "AI/ML"
        else:
            return "Other"

    @staticmethod
    def _categorize_gcp_service(service_name: str) -> str:
        """Map GCP service to high-level category"""
        service_lower = service_name.lower()

        if any(x in service_lower for x in ["compute engine", "gce"]):
            return "Compute"
        elif any(x in service_lower for x in ["cloud storage", "gcs"]):
            return "Storage"
        elif any(x in service_lower for x in ["cloud sql", "bigtable", "firestore", "spanner"]):
            return "Database"
        elif any(x in service_lower for x in ["cloud cdn", "load balancing", "vpc"]):
            return "Networking"
        elif any(x in service_lower for x in ["cloud functions", "cloud run"]):
            return "Serverless"
        elif any(x in service_lower for x in ["vertex ai", "ai platform"]):
            return "AI/ML"
        else:
            return "Other"

    @staticmethod
    def _categorize_azure_service(service_name: str) -> str:
        """Map Azure service to high-level category"""
        service_lower = service_name.lower()

        if any(x in service_lower for x in ["virtual machines", "vm", "compute"]):
            return "Compute"
        elif any(x in service_lower for x in ["storage", "blob", "disk"]):
            return "Storage"
        elif any(x in service_lower for x in ["sql", "cosmos", "database"]):
            return "Database"
        elif any(x in service_lower for x in ["bandwidth", "cdn", "networking"]):
            return "Networking"
        elif any(x in service_lower for x in ["functions", "container instances"]):
            return "Serverless"
        elif any(x in service_lower for x in ["machine learning", "cognitive"]):
            return "AI/ML"
        else:
            return "Other"

    @staticmethod
    def normalize_batch(provider: str, raw_data_list: List[Dict]) -> List[FOCUSSchema]:
        """Normalize a batch of records from a specific provider"""
        normalized = []

        normalizer_map = {
            "aws": BillingNormalizer.normalize_aws,
            "gcp": BillingNormalizer.normalize_gcp,
            "azure": BillingNormalizer.normalize_azure,
        }

        if provider not in normalizer_map:
            raise ValueError(f"Unsupported provider: {provider}")

        normalizer_func = normalizer_map[provider]

        for raw_data in raw_data_list:
            try:
                normalized.append(normalizer_func(raw_data))
            except Exception as e:
                logger.warning(f"Skipping record due to error: {str(e)}")
                continue

        logger.info(f"Normalized {len(normalized)}/{len(raw_data_list)} {provider} records")
        return normalized
