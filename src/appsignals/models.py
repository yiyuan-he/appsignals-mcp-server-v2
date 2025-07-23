from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_pascal


class AWSBaseModel(BaseModel):
    """Base model for all AWS API models with Pascal case aliasing"""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )


class MetricDimension(AWSBaseModel):
    """Represents a CloudWatch metric dimension."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    name: str
    value: str


class KeyAttributes(AWSBaseModel):
    """Key attributes that identify a service in Application Signals."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    type: Optional[str] = None
    resource_type: Optional[str] = None
    name: Optional[str] = None
    identifier: Optional[str] = None
    environment: Optional[str] = None


class MetricReference(AWSBaseModel):
    """Reference to a CloudWatch metric associated with a service."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    namespace: Optional[str] = None
    metric_type: Optional[str] = None
    dimensions: Optional[List[MetricDimension]] = None
    metric_name: Optional[str] = None
    account_id: Optional[str] = None


class ServiceSummary(AWSBaseModel):
    """Summary information about a discovered service."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    key_attributes: Optional[KeyAttributes] = None
    attribute_maps: Optional[List[Dict[str, Any]]] = None
    metric_references: Optional[List[MetricReference]] = None


class ListServicesResponse(AWSBaseModel):
    """Response from AWS Application Signals list_services API."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    service_summaries: Optional[List[ServiceSummary]] = None
    next_token: Optional[str] = None


class ListServicesParams(AWSBaseModel):
    """Input parameters for list_monitored_services tool."""
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True
    )

    start_time: datetime = Field(
        description="Start of time period to retrieve services"
    )
    end_time: datetime = Field(
        description="End of time period to retrieve services"
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="maximum number of services to return"
    )
    next_token: Optional[str] = Field(
        default=None,
        description="Token for pagination"
    )
    include_linked_accounts: bool = Field(
        default=False,
        description="Include services from linked accounts"
    )
    aws_account_id: Optional[str] = Field(
        default=None,
        description="Specific AWS account ID to filter by"
    )
