import os
import json
import boto3
from typing import Any
from .base import ContextSource

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BUCKET = "sovereign-config"
KEY = "global.json"


class S3GlobalSource(ContextSource):
    """Fetches global config overrides from S3 (e.g. default timeouts, flags)."""

    def fetch(self) -> list[dict[str, Any]]:
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=ENDPOINT,
                region_name=REGION,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
            )
            obj = s3.get_object(Bucket=BUCKET, Key=KEY)
            return [json.loads(obj["Body"].read())]
        except Exception as e:
            print(f"[s3_source] could not fetch global config: {e}")
            return [{}]
