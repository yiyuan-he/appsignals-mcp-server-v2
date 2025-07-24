import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

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
                    "Environment": "production"
                },
                "AttributeMaps": [
                    {
                        "AWS.Application": "ecommerce-app",
                        "Telemetry.SDK": "aws-otel-python"
                    }
                ],
                "MetricReferences": [
                    {
                        "Namespace": "AWS/ApplicationSignals",
                        "MetricType": "Latency",
                        "Dimensions": [
                            {"Name": "ServiceName", "Value": "checkout-service"}
                        ]
                    }
                ]
            }
        ],
        "NextToken": None
    }


@pytest.fixture
def mock_boto3_client(sample_list_services_response):
    """Mock boto3 client for Application Signals"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.return_value = sample_list_services_response
        yield mock_client


@pytest.fixture
def mock_boto3_client_error():
    """Mock boto3 client that raises ClientError"""
    with patch("appsignals.server.appsignals_client") as mock_client:
        mock_client.list_services.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ThrottlingException",
                    "Message": "Rate exceeded"
                }
            },
            "list_services"
        )
        yield mock_client
