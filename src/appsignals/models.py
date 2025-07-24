from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_pascal


class AWSBaseModel(BaseModel):
    """Base model for all AWS API models with Pascal case aliasing"""

    model_config = ConfigDict(alias_generator=to_pascal, populate_by_name=True)


class MetricDimension(AWSBaseModel):
    """Represents a CloudWatch metric dimension."""

    name: str
    value: str


class KeyAttributes(AWSBaseModel):
    """Key attributes that identify a service in Application Signals."""

    type: Optional[str] = None
    resource_type: Optional[str] = None
    name: Optional[str] = None
    identifier: Optional[str] = None
    environment: Optional[str] = None


class MetricReference(AWSBaseModel):
    """Reference to a CloudWatch metric associated with a service."""

    namespace: Optional[str] = None
    metric_type: Optional[str] = None
    dimensions: Optional[List[MetricDimension]] = None
    metric_name: Optional[str] = None
    account_id: Optional[str] = None


class ServiceSummary(AWSBaseModel):
    """Summary information about a discovered service."""

    key_attributes: Optional[KeyAttributes] = None
    attribute_maps: Optional[List[Dict[str, Any]]] = None
    metric_references: Optional[List[MetricReference]] = None


class ListServicesResponse(AWSBaseModel):
    """Response from AWS Application Signals list_services API."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    service_summaries: Optional[List[ServiceSummary]] = None
    next_token: Optional[str] = None


class ListServicesParams(BaseModel):
    """Input parameters for list_monitored_services tool."""

    start_time: datetime = Field(
        description="Start of time period to retrieve services"
    )
    end_time: datetime = Field(description="End of time period to retrieve services")
    max_results: int = Field(
        default=50, ge=1, le=500, description="maximum number of services to return"
    )
    next_token: Optional[str] = Field(default=None, description="Token for pagination")
    include_linked_accounts: bool = Field(
        default=False, description="Include services from linked accounts"
    )
    aws_account_id: Optional[str] = Field(
        default=None, description="Specific AWS account ID to filter by"
    )


class LogGroupReference(AWSBaseModel):
    """Reference to a CloudWatch log group."""

    type: Optional[str] = Field(None, description="Should be 'AWS::Resource'")
    resource_type: Optional[str] = Field(
        None, description="Should be 'AWS::Logs::LogGroup'"
    )
    identifier: Optional[str] = Field(None, description="Log group name")


class ServiceDetail(AWSBaseModel):
    """Detailed information about a service from get_service."""

    key_attributes: Optional[KeyAttributes] = None
    attribute_maps: Optional[List[Dict[str, Any]]] = None
    metric_references: Optional[List[MetricReference]] = None
    log_group_references: Optional[List[LogGroupReference]] = None


class GetServiceResponse(AWSBaseModel):
    """Response from AWS Application Signals get_service API."""

    service: Optional[ServiceDetail] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    log_group_references: Optional[List[LogGroupReference]] = None


class GetServiceParams(BaseModel):
    """Input parameters for get_service_detail tool."""

    service_name: str = Field(
        description="Name of the service to get details for (case-sensitive)"
    )
    hours_back: int = Field(
        default=24, ge=1, le=168, description="Hours to look back from now"
    )
