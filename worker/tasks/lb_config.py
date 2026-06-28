import os
import boto3
from typing import Any

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
SOVEREIGN_TABLE = os.getenv("DYNAMODB_SERVICES_TABLE", "sovereign-services")


def _db():
    return boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def write_service_config(instance_id: str, parameters: dict[str, Any]) -> None:
    """Write Envoy routing intent to DynamoDB so Sovereign picks it up."""
    db = _db()
    db.Table(SOVEREIGN_TABLE).put_item(Item={
        "service_id": instance_id,
        "backend": parameters.get("backend", ""),
        "host": parameters.get("host", ""),
        "port": parameters.get("port", 80),
        "routes": parameters.get("routes", ["/"]),
        "timeout_ms": parameters.get("timeout_ms", 30000),
        "retry_attempts": parameters.get("retry_attempts", 3),
        "auth_required": parameters.get("auth_required", False),
        "rate_limit_rps": parameters.get("rate_limit_rps", 0),
        "enabled": True,
    })
    print(f"[lb_config] wrote service config for {instance_id} → {parameters.get('backend')}")


def delete_service_config(instance_id: str) -> None:
    db = _db()
    db.Table(SOVEREIGN_TABLE).delete_item(Key={"service_id": instance_id})
    print(f"[lb_config] deleted service config for {instance_id}")
