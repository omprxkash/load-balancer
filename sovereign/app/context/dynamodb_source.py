import os
import boto3
from typing import Any
from .base import ContextSource

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
TABLE = os.getenv("DYNAMODB_SERVICES_TABLE", "sovereign-services")


class DynamoDBSource(ContextSource):
    def fetch(self) -> list[dict[str, Any]]:
        db = boto3.resource(
            "dynamodb",
            endpoint_url=ENDPOINT,
            region_name=REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        )
        resp = db.Table(TABLE).scan()
        items = resp.get("Items", [])
        return [i for i in items if i.get("enabled", True)]
