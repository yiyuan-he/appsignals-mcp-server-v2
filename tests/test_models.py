import pytest
from datetime import datetime
from pydantic import ValidationError
from appsignals.models import (
    MetricDimension, KeyAttributes, ServiceSummary,
    ListServicesResponse, ListServicesParams, MetricReference
)


class TestMetricDimension:
    """Test MetricDimension model"""

    def test_create_metric_dimension(self):
        """Test creating a metric dimension with required fields"""
        dim = MetricDimension(name="ServiceName", value="checkout-service")

        assert dim.name == "ServiceName"
        assert dim.value == "checkout-service"


    def test_pascal_case_serialization(self):
        """Test that snake_case fields serialize to Pascal case"""
        dim = MetricDimension(name="ServiceName", value="checkout-service")

        serialized = dim.model_dump(by_alias=True)

        assert serialized == {
            "Name": "ServiceName",
            "Value": "checkout-service"
        }


    def test_missing_required_field(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError) as exc_info:
            MetricDimension(name="ServiceName") # missing "value"

        errors = exc_info.value.errors()

        assert len(errors) == 1
        assert errors[0]["loc"] == ("Value",)
        assert errors[0]["type"] == "missing"


class TestKeyAttributes:
    """Test KeyAttributes model"""

    def test_all_fields_optional(self):
        """Test that all fields in KeyAttributes are optional"""
        attrs = KeyAttributes()

        assert attrs.type is None
        assert attrs.name is None
        assert attrs.resource_type is None
        assert attrs.identifier is None
        assert attrs.environment is None


    def test_create_with_some_fields(self):
        """Test creating KeyAttributes with partial fields"""
        attrs = KeyAttributes(
            type="Service",
            name="checkout-service",
            environment="production"
        )

        assert attrs.type == "Service"
        assert attrs.name == "checkout-service"
        assert attrs.environment == "production"
        assert attrs.resource_type is None


    def test_pascal_case_deserialization(self):
        """Test parsing Pascal case input from AWS"""
        aws_data = {
            "Type": "Service",
            "Name": "my-service",
            "Environment": "prod",
            "ResourceType": "AWS::ECS::Service"
        }

        attrs = KeyAttributes(**aws_data)

        assert attrs.type == "Service"
        assert attrs.name == "my-service"
        assert attrs.resource_type == "AWS::ECS::Service"


class TestServiceSummary:
    """Test ServiceSummary model"""

    def test_create_with_nested_models(self):
        """Test creating ServiceSummary with nested models"""
        summary = ServiceSummary(
            key_attributes=KeyAttributes(
                type="Service",
                name="api-gateway"
            ),
            attribute_maps=[
                {"AWS.Application": "my-app"},
                {"Telemetry.SDK": "opentelemetry"}
            ],
            metric_references=[
                MetricReference(
                    namespace="AWS/ApplicationSignals",
                    metric_type="Latency"
                )
            ]
        )

        assert summary.key_attributes is not None
        assert summary.key_attributes.name == "api-gateway"
        assert summary.attribute_maps is not None
        assert len(summary.attribute_maps) == 2
        assert summary.attribute_maps[0]["AWS.Application"] == "my-app"
        assert summary.metric_references is not None
        assert len(summary.metric_references) == 1


    def test_all_fields_optional(self):
        """Test that ServiceSummary can be created with no fields"""
        summary = ServiceSummary()

        assert summary.key_attributes is None
        assert summary.attribute_maps is None
        assert summary.metric_references is None


class TestListServicesResponse:
    """Test ListServicesResponse model"""

    def test_parse_aws_response(self, sample_list_services_response):
        """Test parsing actual AWS response structure"""
        response = ListServicesResponse(**sample_list_services_response)

        assert response.service_summaries is not None
        assert len(response.service_summaries) == 1
        assert response.next_token is None

        service = response.service_summaries[0]
        assert service.key_attributes is not None
        assert service.key_attributes.name == "checkout-service"
        assert service.key_attributes.type == "Service"
        assert service.key_attributes.environment == "production"


    def test_empty_response(self):
        """Test handling empty service list"""
        response = ListServicesResponse(
            service_summaries=[],
            next_token=None
        )

        assert response.service_summaries == []
        assert response.next_token is None


    def test_response_with_pagination(self):
        """Test response with next token for pagination"""
        response = ListServicesResponse(
            service_summaries=[],
            next_token="abc123"
        )

        assert response.next_token == "abc123"


class TestListServicesParams:
    """Test ListServicesParams input validation"""

    def test_valid_params(self):
        """Test creating params with valid values"""
        now = datetime.now()
        params = ListServicesParams(
            start_time = now,
            end_time=now,
            max_results=100
        )

        assert params.start_time == now
        assert params.end_time == now
        assert params.max_results == 100
        assert params.include_linked_accounts is False
        assert params.aws_account_id is None


    def test_default_values(self):
        """Test that defaults are applied correctly"""
        now = datetime.now()
        params = ListServicesParams(
            start_time=now,
            end_time=now
        )

        assert params.max_results == 50
        assert params.next_token is None
        assert params.include_linked_accounts is False


    def test_max_results_lower_bound_validation(self):
        """Test max_results field lower bound validation"""
        now = datetime.now()

        with pytest.raises(ValidationError) as exc_info:
            ListServicesParams(
                start_time=now,
                end_time=now,
                max_results=0
            )
        assert "greater than or equal to 1" in str(exc_info.value)


    def test_max_results_upper_bound_validation(self):
        """Test max_results field upper bound validation"""
        now = datetime.now()

        with pytest.raises(ValidationError) as exc_info:
            ListServicesParams(
                start_time=now,
                end_time=now,
                max_results=501
            )
        assert "less than or equal to 500" in str(exc_info.value)


    def test_valid_boundary_values(self):
        """Test boundary values for max_results"""
        now = datetime.now()

        params = ListServicesParams(
            start_time=now,
            end_time=now,
            max_results=1
        )
        assert params.max_results == 1


    @pytest.mark.parametrize("max_results,expected", [
        (1, 1),
        (50, 50),
        (100, 100),
        (250, 250),
        (500, 500)
    ])
    def test_various_max_results(self, max_results, expected):
        """Test various valid max_results values"""
        now = datetime.now()
        params = ListServicesParams(
            start_time=now,
            end_time=now,
            max_results=max_results
        )

        assert params.max_results == expected
