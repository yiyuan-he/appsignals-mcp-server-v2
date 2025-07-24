import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import FastMCP, Client, Context
from pydantic import Field, ValidationError
import logging

from appsignals.models import (
    ListServicesResponse,
    ListServicesParams,
    ServiceSummary,
    GetServiceParams,
    GetServiceResponse,
    ServiceDetail,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

mcp = FastMCP(name="AppSignals MCP Server")

try:
    appsignals_client = boto3.client("application-signals")
    logger.info("Successfully initialized AWS Application Signals client")
except Exception as e:
    logger.error(f"Failed to initialize AWS client: {e}")
    raise


@mcp.tool(
    description="""
    List all services monitored by AWS Application Signals.

    Use this tool to:
    - Get an overview of all monitored services
    - See service names, types, and key attributes
    - Identify which services are being tracked
    - Count total number of services in your environment

    Returns a formatted list showing:
    - Service name and type
    - Key attributes (Environment, Platform, etc.)
    - Total count of services

    This is typically the first tool to use when starting monitoring or investigation.
    """
)
async def list_monitored_services(
    ctx: Context,
    hours_back: int = Field(24, description="Hours to look back from now"),
    max_results: int = Field(100, description="Maximum services to return (1-500)"),
) -> str:
    try:
        await ctx.info(f"Listing monitored services for the last {hours_back} hours")
        await ctx.debug(f"Max results set to {max_results}")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        params = ListServicesParams(
            start_time=start_time, end_time=end_time, max_results=max_results
        )

        raw_response = appsignals_client.list_services(
            StartTime=params.start_time,
            EndTime=params.end_time,
            MaxResults=params.max_results,
        )

        response = ListServicesResponse(**raw_response)

        if not response.service_summaries:
            await ctx.warning("No services found in the specified time range")
            return "No services found in Application Signals."

        service_count = len(response.service_summaries)
        await ctx.info(f"Found {service_count} monitored services")

        result = f"Application Signals Services ({service_count} total):\n\n"

        for service in response.service_summaries:
            if service.key_attributes:
                service_name = service.key_attributes.name or "Unknown"
                service_type = service.key_attributes.type or "Unknown"

                result += f"Service: {service_name}\n"
                result += f"   Type: {service_type}\n"

                if service.key_attributes.environment:
                    result += f"  Environment: {service.key_attributes.environment}\n"
                if service.key_attributes.resource_type:
                    result += (
                        f"  Resource Type: {service.key_attributes.resource_type}\n"
                    )

                if service.attribute_maps:
                    result += "  Additional Attributes:\n"
                    for attr_map in service.attribute_maps:
                        for key, value in attr_map.items():
                            result += f"    {key}: {value}\n"

                if service.metric_references:
                    result += (
                        f"  Metrics: {len(service.metric_references)} configured\n"
                    )
            else:
                result += "Service: Unknown (no attributes)\n"

            result += "\n"

        if response.next_token:
            await ctx.warning("Results truncated - more services available")
            result += f"Note: More services available (NextToken: {response.next_token[:20]} ...)\n"

        return result

    except ValidationError as e:
        error_message = f"Invalid parameters: {e}"
        await ctx.error(error_message)
        return error_message
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", "Unknown error")
        await ctx.error(f"AWS API error [{error_code}]: {error_message}")
        return f"AWS Error: {error_message}"
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        return f"Error: {str(e)}"


@mcp.tool(
    description="""Get detailed information about a specific Application Signals service.

    Use this tool when you need to:
    - Understand a service's configuration and setup
    - Understand where this service is deployed and where it is running such as EKS, Lambda, etc.
    - See what metrics are available for a service
    - Find log groups associated with the service
    - Get service metadata and attributes

    Returns comprehensive details including:
    - Key attributes (Type, Environment, Platform)
    - Available CloudWatch metrics with namespaces
    - Metric dimensions and types
    - Associated log groups for debugging

    This tool is essential before querying specific metrics, as it shows which metrics
    are available for the service.
    """
)
async def get_service_detail(
    ctx: Context,
    service_name: str = Field(
        ..., description="Name of the service to get details for (case-sensitive)"
    ),
    hours_back: int = Field(24, description="Hours to look back from now (1-168)"),
) -> str:
    try:
        await ctx.info(f"Getting details for service: {service_name}")

        params = GetServiceParams(service_name=service_name, hours_back=hours_back)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=params.hours_back)

        await ctx.debug(
            f"Searching for service '{service_name}' in the last {hours_back} hours"
        )

        list_response = appsignals_client.list_services(
            StartTime=start_time, EndTime=end_time, MaxResults=100
        )

        services = ListServicesResponse(**list_response)

        target_service = None
        for service in services.service_summaries or []:
            if service.key_attributes and service.key_attributes.name == service_name:
                target_service = service
                break

        if not target_service or not target_service.key_attributes:
            await ctx.warning(
                f"Service '{service_name}' not found in Application Signals"
            )
            return f"Service '{service_name}' not found in Application Signals."

        await ctx.debug(f"Getting detailed information for service: {service_name}")

        detail_response = appsignals_client.get_service(
            StartTime=start_time,
            EndTime=end_time,
            KeyAttributes=target_service.key_attributes.model_dump(
                by_alias=True, exclude_none=True
            ),
        )

        service_response = GetServiceResponse(**detail_response)

        if not service_response.service:
            await ctx.error(f"No service details returned for '{service_name}'")
            return f"No service details found for '{service_name}'."

        service_details = service_response.service

        result = f"Service Details: {service_name}\n\n"

        if service_details.key_attributes:
            result += "Key Attributes:\n"
            key_attrs = service_details.key_attributes
            if key_attrs.name:
                result += f"  Name: {key_attrs.name}\n"
            if key_attrs.type:
                result += f"  Type: {key_attrs.type}\n"
            if key_attrs.environment:
                result += f"  Environment: {key_attrs.environment}\n"
            if key_attrs.resource_type:
                result += f"  Resource Type: {key_attrs.resource_type}\n"
            if key_attrs.identifier:
                result += f"  Identifier: {key_attrs.identifier}\n"

        if service_details.attribute_maps:
            result += "Additional Attributes:\n"
            for attr_map in service_details.attribute_maps:
                for key, value in attr_map.items():
                    result += f"  {key}: {value}\n"
            result += "\n"

        if service_details.metric_references:
            result += (
                f"Metric References ({len(service_details.metric_references)} total):\n"
            )
            for metric in service_details.metric_references:
                namespace = metric.namespace or "Unknown"
                metric_name = metric.metric_name or "Unknown"
                result += f"  • {namespace}/{metric_name}\n"

                if metric.metric_type:
                    result += f"    Type: {metric.metric_type}\n"

                if metric.dimensions:
                    result += "    Dimensions: "
                    dim_strs = [f"{d.name}={d.value}" for d in metric.dimensions]
                    result += ", ".join(dim_strs) + "\n"
                result += "\n"

        if service_details.log_group_references:
            result += f"Log Group References ({len(service_details.log_group_references)} total):\n"
            for log_ref in service_details.log_group_references:
                log_group = log_ref.identifier or "Unknown"
                result += f"  • {log_group}\n"
            result += "\n"

        await ctx.info(f"Successfully retrieved details for service '{service_name}'")
        return result

    except ValidationError as e:
        error_message = f"Invalid parameters: {e}"
        await ctx.error(error_message)
        return error_message
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", "Unknown error")
        await ctx.error(f"AWS API error [{error_code}]: {error_message}")
        return f"AWS Error: {error_message}"
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
