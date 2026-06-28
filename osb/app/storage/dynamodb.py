import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException
from typing import Any

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
INSTANCES_TABLE = os.getenv("DYNAMODB_INSTANCES_TABLE", "osb-instances")
BINDINGS_TABLE = os.getenv("DYNAMODB_BINDINGS_TABLE", "osb-bindings")


def _client():
    return boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def put_instance(instance_id: str, data: dict[str, Any]) -> None:
    db = _client()
    table = db.Table(INSTANCES_TABLE)
    table.put_item(Item={"instance_id": instance_id, **data})


def get_instance(instance_id: str) -> dict[str, Any] | None:
    db = _client()
    table = db.Table(INSTANCES_TABLE)
    try:
        resp = table.get_item(Key={"instance_id": instance_id})
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {code}")
    except BotoCoreError as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}")
    return resp.get("Item")


def update_instance_state(
    instance_id: str, state: str, error: str | None = None
) -> None:
    db = _client()
    table = db.Table(INSTANCES_TABLE)
    expr = "SET #s = :s"
    names = {"#s": "state"}
    values: dict[str, Any] = {":s": state}
    if error:
        expr += ", #e = :e"
        names["#e"] = "error"
        values[":e"] = error
    table.update_item(
        Key={"instance_id": instance_id},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def delete_instance(instance_id: str) -> None:
    db = _client()
    db.Table(INSTANCES_TABLE).delete_item(Key={"instance_id": instance_id})


def put_binding(binding_id: str, data: dict[str, Any]) -> None:
    db = _client()
    db.Table(BINDINGS_TABLE).put_item(Item={"binding_id": binding_id, **data})


def get_binding(binding_id: str) -> dict[str, Any] | None:
    db = _client()
    resp = db.Table(BINDINGS_TABLE).get_item(Key={"binding_id": binding_id})
    return resp.get("Item")


def delete_binding(binding_id: str) -> None:
    db = _client()
    db.Table(BINDINGS_TABLE).delete_item(Key={"binding_id": binding_id})


def scan_instances() -> list[dict[str, Any]]:
    db = _client()
    resp = db.Table(INSTANCES_TABLE).scan()
    return resp.get("Items", [])
