import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from pydantic import ValidationError
from fastmcp import Client

from appsignals.server import mcp


class TestListMonitoredServices:
    """Test the list_monitored_services MCP tool"""

    @pytest.mark.asyncio
    async def test_list_services_success(self, mock_boto3_client):
        """Test successful service listing with typical response"""
        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            mock_boto3_client.list_services.assert_called_once()
            call_args = mock_boto3_client.list_services.call_args[1]

            assert "StartTime" in call_args
            assert "EndTime" in call_args
            assert isinstance(call_args["StartTime"], datetime)
            assert isinstance(call_args["EndTime"], datetime)

            # Check time range is approximately 24 hours
            time_diff = call_args["EndTime"] - call_args["StartTime"]
            assert 24 <= time_diff.total_seconds() / 3600 <= 25

            # Check max results default
            assert call_args["MaxResults"] == 100

            assert "Application Signals Services (1 total):" in result.data
            assert "checkout-service" in result.data
            assert "Type: Service" in result.data
            assert "Environment: production" in result.data
            assert "AWS.Application: ecommerce-app" in result.data

    @pytest.mark.asyncio
    async def test_list_services_with_custom_params(self, mock_boto3_client):
        """Test with custom hours_back and max_results parameters"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "list_monitored_services", {"hours_back": 48, "max_results": 50}
            )

            call_args = mock_boto3_client.list_services.call_args[1]

            time_diff = call_args["EndTime"] - call_args["StartTime"]
            assert 47 <= time_diff.total_seconds() / 3600 <= 49

            assert call_args["MaxResults"] == 50

    @pytest.mark.asyncio
    async def test_list_services_empty_response(self, mock_boto3_client):
        """Test handling of empty service list"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [],
            "NextToken": None,
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert result.data == "No services found in Application Signals."

    @pytest.mark.asyncio
    async def test_list_services_with_minimal_attributes(self, mock_boto3_client):
        """Test handling services with minimal attributes"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [{"KeyAttributes": {"Name": "minimal-service"}}],
            "NextToken": None,
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "minimal-service" in result.data
            assert "Type: Unknown" in result.data
            assert "Environment:" not in result.data
            assert "Resource Type:" not in result.data

    @pytest.mark.asyncio
    async def test_list_services_no_key_attributes(self, mock_boto3_client):
        """Test handling services with no key attributes at all"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [{"AttributeMaps": [{"some": "data"}]}],
            "NextToken": None,
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "Service: Unknown (no attributes)" in result.data

    @pytest.mark.asyncio
    async def test_client_error_handling(self, mock_boto3_client_error):
        """Test handling of AWS ClientError"""
        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "AWS Error: Rate exceeded" in result.data

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, mock_boto3_client):
        """Test handling of unexpected errors"""
        mock_boto3_client.list_services.side_effect = Exception("Unexpected error")

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "Error: Unexpected error" in result.data

    @pytest.mark.asyncio
    async def test_multiple_services(self, mock_boto3_client):
        """Test formatting of multiple services"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [
                {
                    "KeyAttributes": {
                        "Type": "Service",
                        "Name": "checkout-service",
                        "Environment": "production",
                    }
                },
                {
                    "KeyAttributes": {
                        "Type": "Service",
                        "Name": "payment-api",
                        "Environment": "staging",
                    }
                },
            ],
            "NextToken": None,
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "Application Signals Services (2 total):" in result.data
            assert "checkout-service" in result.data
            assert "payment-api" in result.data
            assert "Environment: production" in result.data
            assert "Environment: staging" in result.data

    @pytest.mark.asyncio
    async def test_service_with_metrics(self, mock_boto3_client):
        """Test service with metric references"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [
                {
                    "KeyAttributes": {"Type": "Service", "Name": "api-gateway"},
                    "MetricReferences": [
                        {
                            "Namespace": "AWS/ApplicationSignals",
                            "MetricType": "Latency",
                        },
                        {"Namespace": "AWS/ApplicationSignals", "MetricType": "Error"},
                    ],
                }
            ]
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "api-gateway" in result.data
            assert "Metrics: 2 configured" in result.data

    @pytest.mark.asyncio
    async def test_pagination_token_in_response(self, mock_boto3_client):
        """Test that pagination token is mentioned in output"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [
                {"KeyAttributes": {"Name": "service1", "Type": "Service"}}
            ],
            "NextToken": "abcdefghijklmnopqrstuvwxyz123456",
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert (
                "Note: More services available (NextToken: abcdefghijklmnopqrst ...)"
                in result.data
            )

    @pytest.mark.asyncio
    async def test_timezone_awareness(self, mock_boto3_client):
        """Test that datetime parameters are timezone-aware"""
        async with Client(mcp) as client:
            await client.call_tool("list_monitored_services", {})

            call_args = mock_boto3_client.list_services.call_args[1]
            start_time = call_args["StartTime"]
            end_time = call_args["EndTime"]

            assert start_time.tzinfo is not None
            assert end_time.tzinfo is not None

            assert start_time.tzinfo == timezone.utc
            assert end_time.tzinfo == timezone.utc


class TestGetServiceDetail:
    """Test the get_service_detail MCP tool"""

    @pytest.mark.asyncio
    async def test_get_service_detail_success(self, mock_boto3_client_with_get_service):
        """Test successful service detail retrieval with all fields"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            mock_boto3_client_with_get_service.list_services.assert_called_once()
            mock_boto3_client_with_get_service.get_service.assert_called_once()

            call_args = mock_boto3_client_with_get_service.get_service.call_args[1]
            assert call_args["KeyAttributes"]["Name"] == "checkout-service"
            assert call_args["KeyAttributes"]["Type"] == "Service"
            assert call_args["KeyAttributes"]["Environment"] == "production"

            assert "Service Details: checkout-service" in result.data
            assert "Key Attributes:" in result.data
            assert "Type: Service" in result.data
            assert "Environment: production" in result.data
            assert "Resource Type: AWS::ECS::Service" in result.data
            assert "Identifier: arn:aws:ecs" in result.data

            assert "Additional Attributes:" in result.data
            assert "Platform: ECS" in result.data
            assert "Application: ecommerce-app" in result.data

            assert "Metric References (2 total):" in result.data
            assert "• AWS/ApplicationSignals/Latency" in result.data
            assert "• AWS/ApplicationSignals/ErrorRate" in result.data
            assert "Type: Latency" in result.data
            assert (
                "Dimensions: Service=checkout-service, Environment=production"
                in result.data
            )

            assert "Log Group References (1 total):" in result.data
            assert "• /aws/ecs/checkout-service" in result.data

    @pytest.mark.asyncio
    async def test_service_not_found(self, mock_boto3_client):
        """Test when service is not found in list"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "non-existent-service"}
            )

            assert (
                result.data
                == "Service 'non-existent-service' not found in Application Signals."
            )
            mock_boto3_client.list_services.assert_called_once()
            mock_boto3_client.get_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_hours_back(self, mock_boto3_client):
        """Test validation error for hours_back > 168"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail",
                {"service_name": "checkout-service", "hours_back": 200},
            )

            assert "Invalid parameters" in result.data
            assert "less than or equal to 168" in result.data

    @pytest.mark.asyncio
    async def test_list_services_error(self, mock_boto3_client_error):
        """Test handling of AWS error during list_services"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert "AWS Error: Rate exceeded" in result.data

    @pytest.mark.asyncio
    async def test_get_service_error(self, mock_boto3_client_get_service_error):
        """Test handling of AWS error during get_service"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert "AWS Error: Invalid key attributes" in result.data
            mock_boto3_client_get_service_error.list_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_with_no_metrics(self, mock_boto3_client_with_get_service):
        """Test service with no metric references"""
        mock_boto3_client_with_get_service.get_service.return_value = {
            "Service": {
                "KeyAttributes": {
                    "Type": "Service",
                    "Name": "checkout-service",
                    "Environment": "production",
                },
                "MetricReferences": [],
                "LogGroupReferences": [],
            }
        }

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert "Metric References" not in result.data
            assert "Log Group References" not in result.data

    @pytest.mark.asyncio
    async def test_service_with_minimal_attributes(
        self, mock_boto3_client_with_get_service
    ):
        """Test service with only required attributes"""
        mock_boto3_client_with_get_service.get_service.return_value = {
            "Service": {"KeyAttributes": {"Name": "minimal-service"}}
        }

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert "Service Details: checkout-service" in result.data
            assert "Name: minimal-service" in result.data
            assert "Type:" not in result.data
            assert "Environment:" not in result.data

    @pytest.mark.asyncio
    async def test_empty_service_response(self, mock_boto3_client_with_get_service):
        """Test when get_service returns empty service details"""
        mock_boto3_client_with_get_service.get_service.return_value = {"Service": None}

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert result.data == "No service details found for 'checkout-service'."

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_boto3_client_with_get_service):
        """Test handling of unexpected exceptions"""
        mock_boto3_client_with_get_service.get_service.side_effect = Exception(
            "Unexpected error"
        )

        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail", {"service_name": "checkout-service"}
            )

            assert "Error: Unexpected error" in result.data

    @pytest.mark.asyncio
    async def test_custom_hours_back(self, mock_boto3_client_with_get_service):
        """Test with custom hours_back parameter"""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_service_detail",
                {"service_name": "checkout-service", "hours_back": 48},
            )

            call_args = mock_boto3_client_with_get_service.list_services.call_args[1]
            time_diff = call_args["EndTime"] - call_args["StartTime"]
            assert 47 <= time_diff.total_seconds() / 3600 <= 49
