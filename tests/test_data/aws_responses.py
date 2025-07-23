EMPTY_SERVICE_RESPONSE = {
    "ServiceSummaries": [],
    "NextToken": None
}

MULTI_SERVICE_RESPONSE = {
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
                "Name": "payment-service",
                "Environment": "production"
            }
        }
    ],
    "NextToken": "next-page-token"
}

SERVICE_WITH_MINIMAL_ATTRS = {
    "ServiceSummaries": [
        {
            "KeyAttributes": {
                "Name": "minimal-service"
            }
        }
    ]
}
