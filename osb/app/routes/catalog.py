from fastapi import APIRouter
from app.models.catalog import (
    CatalogResponse, ServiceOffering, ServicePlan, PlanSchemas,
    InstanceSchema, SchemaParameters,
)

router = APIRouter(prefix="/v2")

LB_SERVICE = ServiceOffering(
    id="atlassian-load-balancing-v1",
    name="load-balancing",
    description="Self-service edge load balancing via Envoy proxy",
    bindable=True,
    instances_retrievable=True,
    bindings_retrievable=True,
    plan_updateable=True,
    tags=["networking", "proxy", "edge"],
    plans=[
        ServicePlan(
            id="lb-basic",
            name="basic",
            description="HTTP/HTTPS routing with TLS termination and access logging",
            free=True,
            schemas=PlanSchemas(
                service_instance=InstanceSchema(
                    create={
                        "parameters": SchemaParameters(
                            properties={
                                "backend": {
                                    "type": "string",
                                    "description": (
                                        "Backend service name"
                                        " (must match a running service)"
                                    ),
                                },
                                "host": {
                                    "type": "string",
                                    "description": (
                                        "Virtual host domain (e.g. jira.local)"
                                    ),
                                },
                                "port": {
                                    "type": "integer",
                                    "description": "Backend port",
                                    "default": 80,
                                },
                                "routes": {
                                    "type": "array",
                                    "description": "List of route prefix matches",
                                    "items": {"type": "string"},
                                },
                                "timeout_ms": {
                                    "type": "integer",
                                    "description": (
                                        "Per-request timeout in milliseconds"
                                    ),
                                    "default": 30000,
                                },
                                "retry_attempts": {
                                    "type": "integer",
                                    "description": "Number of retry attempts on 5xx",
                                    "default": 3,
                                },
                                "auth_required": {
                                    "type": "boolean",
                                    "description": (
                                        "Require Bearer token auth"
                                        " via ext_authz sidecar"
                                    ),
                                    "default": False,
                                },
                                "rate_limit_rps": {
                                    "type": "integer",
                                    "description": (
                                        "Requests per second rate limit"
                                        " (0 = disabled)"
                                    ),
                                    "default": 0,
                                },
                            },
                            required=["backend", "host"],
                        )
                    }
                )
            ),
        ),
        ServicePlan(
            id="lb-advanced",
            name="advanced",
            description=(
                "All basic features plus weighted routing,"
                " header manipulation, and canary support"
            ),
            free=True,
        ),
    ],
)


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog():
    return CatalogResponse(services=[LB_SERVICE])
