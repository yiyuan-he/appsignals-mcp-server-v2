import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import FastMCP, Client, Context
from pydantic import Field, ValidationError
import logging

from appsignals.models import ListServicesResponse, ListServicesParams, ServiceSummary

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


if __name__ == "__main__":
    mcp.run()
