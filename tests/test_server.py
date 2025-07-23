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
            result = await client.call_tool("list_monitored_services", {
                "hours_back": 48,
                "max_results": 50
            })

            call_args = mock_boto3_client.list_services.call_args[1]

            time_diff = call_args["EndTime"] - call_args["StartTime"]
            assert 47 <= time_diff.total_seconds() / 3600 <= 49

            assert call_args["MaxResults"] == 50


    @pytest.mark.asyncio
    async def test_list_services_empty_response(self, mock_boto3_client):
        """Test handling of empty service list"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [],
            "NextToken": None
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert result.data == "No services found in Application Signals."


    @pytest.mark.asyncio
    async def test_list_services_with_minimal_attributes(self, mock_boto3_client):
        """Test handling services with minimal attributes"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [{
                "KeyAttributes": {
                    "Name": "minimal-service"
                }
            }],
            "NextToken": None
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
            "ServiceSummaries": [{
                "AttributeMaps": [{"some": "data"}]
            }],
            "NextToken": None
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
                        "Environment": "production"
                    }
                },
                {
                    "KeyAttributes": {
                        "Type": "Service",
                        "Name": "payment-api",
                        "Environment": "staging",
                    }
                }
            ],
            "NextToken": None
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
            "ServiceSummaries": [{
                "KeyAttributes": {
                    "Type": "Service",
                    "Name": "api-gateway"
                },
                "MetricReferences": [
                    {"Namespace": "AWS/ApplicationSignals", "MetricType": "Latency"},
                    {"Namespace": "AWS/ApplicationSignals", "MetricType": "Error"}
                ]
            }]
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "api-gateway" in result.data
            assert "Metrics: 2 configured" in result.data


    @pytest.mark.asyncio
    async def test_pagination_token_in_response(self, mock_boto3_client):
        """Test that pagination token is mentioned in output"""
        mock_boto3_client.list_services.return_value = {
            "ServiceSummaries": [{
                "KeyAttributes": {"Name": "service1", "Type": "Service"}
            }],
            "NextToken": "abcdefghijklmnopqrstuvwxyz123456"
        }

        async with Client(mcp) as client:
            result = await client.call_tool("list_monitored_services", {})

            assert "Note: More services available (NextToken: abcdefghijklmnopqrst ...)" in result.data


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
