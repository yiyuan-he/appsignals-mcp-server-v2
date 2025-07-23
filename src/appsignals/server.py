import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import FastMCP, Client
from pydantic import Field, ValidationError

from appsignals.models import ListServicesResponse, ListServicesParams, ServiceSummary

mcp = FastMCP(name="AppSignals MCP Server")

try:
    appsignals_client = boto3.client("application-signals")
except Exception as e:
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
    hours_back: int = Field(24, description="Hours to look back from now"),
    max_results: int = Field(100, description="Maximum services to return (1-500)")
) -> str:
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        params = ListServicesParams(
            start_time=start_time,
            end_time=end_time,
            max_results=max_results
        )

        raw_response = appsignals_client.list_services(
            StartTime=params.start_time,
            EndTime=params.end_time,
            MaxResults=params.max_results
        )

        response = ListServicesResponse(**raw_response)

        if not response.service_summaries:
            return "No services found in Application Signals."

        result = f"Application Signals Services ({len(response.service_summaries)} total):\n\n"

        for service in response.service_summaries:
            if service.key_attributes:
                service_name = service.key_attributes.name or "Unknown"
                service_type = service.key_attributes.type or "Unknown"

                result += f"Service: {service_name}\n"
                result += f"   Type: {service_type}\n"

                if service.key_attributes.environment:
                    result += f"  Environment: {service.key_attributes.environment}\n"
                if service.key_attributes.resource_type:
                    result += f"  Resource Type: {service.key_attributes.resource_type}\n"

                if service.attribute_maps:
                    result += "  Additional Attributes:\n"
                    for attr_map in service.attribute_maps:
                        for key, value in attr_map.items():
                            result += f"    {key}: {value}\n"

                if service.metric_references:
                    result += f"  Metrics: {len(service.metric_references)} configured\n"
            else:
                result += "Service: Unknown (no attributes)\n"

            result += "\n"

        if response.next_token:
            result += f"Note: More services available (NextToken: {response.next_token[:20]} ...)\n"

        return result

    except ValidationError as e:
        return f"Invalid parameters: {e}"
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", "Unknown error")
        return f"AWS Error: {error_message}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
