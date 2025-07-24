import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError


os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def sample_list_services_response():
    """Same AWS ApplicationSignals list_services response"""
    now = datetime.now(timezone.utc)
    return {
        "StartTime": now - timedelta(hours=24),
        "EndTime": now,
        "ServiceSummaries": [
            {
                "KeyAttributes": {
                    "Type": "Service",
                    "Name": "checkout-service",
                    "Environment": "production",
                },
                "AttributeMaps": [
                    {
                        "AWS.Application": "ecommerce-app",
                        "Telemetry.SDK": "aws-otel-python",
                    }
                ],
                "MetricReferences": [
                    {
                        "Namespace": "AWS/ApplicationSignals",
                        "MetricType": "Latency",
                        "Dimensions": [
                            {"Name": "ServiceName", "Value": "checkout-service"}
                        ],
                    }
                ],
            }
        ],
        "NextToken": None,
    }


@pytest.fixture
def sample_get_service_response():
    """Sample AWS ApplicationSignals get_service response"""
    now = datetime.now(timezone.utc)
    return {
        "StartTime": now - timedelta(hours=24),
        "EndTime": now,
        "Service": {
            "KeyAttributes": {
                "Type": "Service",
                "Name": "checkout-service",
                "Environment": "production",
                "ResourceType": "AWS::ECS::Service",
                "Identifier": "arn:aws:ecs:us-east-1:123456789012:service/production/checkout-service",
            },
            "AttributeMaps": [
                {
                    "Platform": "ECS",
                    "Application": "ecommerce-app",
                    "TelemetrySource": "AWS::Telemetry::OpenTelemetry",
                }
            ],
            "MetricReferences": [
                {
                    "Namespace": "AWS/ApplicationSignals",
                    "MetricName": "Latency",
                    "MetricType": "Latency",
                    "Dimensions": [
                        {"Name": "Service", "Value": "checkout-service"},
                        {"Name": "Environment", "Value": "production"},
                    ],
                },
                {
                    "Namespace": "AWS/ApplicationSignals",
                    "MetricName": "ErrorRate",
                    "MetricType": "Error",
                    "Dimensions": [{"Name": "Service", "Value": "checkout-service"}],
                },
            ],
            "LogGroupReferences": [
                {
                    "Type": "AWS::Resource",
                    "ResourceType": "AWS::Logs::LogGroup",
                    "Identifier": "/aws/ecs/checkout-service",
                }
            ],
        },
    }


@pytest.fixture
def mock_boto3_client(sample_list_services_response):
    """Mock boto3 client for Application Signals"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.return_value = sample_list_services_response
        yield mock_client


@pytest.fixture
def mock_boto3_client_with_get_service(
    sample_list_services_response, sample_get_service_response
):
    """Mock boto3 client for both list_services and get_service"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.return_value = sample_list_services_response
        mock_client.get_service.return_value = sample_get_service_response
        yield mock_client


@pytest.fixture
def mock_boto3_client_error():
    """Mock boto3 client that raises ClientError"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "list_services",
        )
        yield mock_client


@pytest.fixture
def mock_boto3_client_get_service_error(sample_list_services_response):
    """Mock that succeeds on list_services but fails on get_service"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.return_value = sample_list_services_response
        mock_client.get_service.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationException",
                    "Message": "Invalid key attributes",
                }
            },
            "get_service",
        )
        yield mock_client
