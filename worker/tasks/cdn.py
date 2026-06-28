import os
import uuid
import boto3

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def _client():
    return boto3.client(
        "cloudfront",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def create_distribution(host: str, origin: str = "envoy") -> str:
    """Create a CloudFront distribution for DDoS protection + CDN.

    CloudFront requires LocalStack Pro. In the free tier this is skipped
    and a synthetic distribution ID is returned so provisioning still succeeds.
    """
    client = _client()
    ref = str(uuid.uuid4())

    try:
        resp = client.create_distribution(
            DistributionConfig={
                "CallerReference": ref,
                "Comment": f"Load balancer distribution for {host}",
                "DefaultCacheBehavior": {
                    "TargetOriginId": "envoy-origin",
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "AllowedMethods": {
                        "Quantity": 7,
                        "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                        "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                    },
                    "ForwardedValues": {
                        "QueryString": True,
                        "Cookies": {"Forward": "all"},
                        "Headers": {"Quantity": 1, "Items": ["Host"]},
                    },
                    "MinTTL": 0,
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                },
                "Origins": {
                    "Quantity": 1,
                    "Items": [{
                        "Id": "envoy-origin",
                        "DomainName": origin,
                        "CustomOriginConfig": {
                            "HTTPPort": 10000,
                            "HTTPSPort": 443,
                            "OriginProtocolPolicy": "http-only",
                        },
                    }],
                },
                "Enabled": True,
                "Aliases": {"Quantity": 1, "Items": [host]},
            }
        )
        dist_id = resp["Distribution"]["Id"]
        print(f"[cdn] created CloudFront distribution {dist_id} for {host}")
        return dist_id
    except Exception as exc:
        # LocalStack free tier does not support CloudFront — treat as no-op
        synthetic_id = f"LOCAL-{ref[:8].upper()}"
        print(f"[cdn] CloudFront unavailable ({exc.__class__.__name__}), using synthetic id {synthetic_id}")
        return synthetic_id
