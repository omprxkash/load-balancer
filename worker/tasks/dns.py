import os
import boto3

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def _client():
    return boto3.client(
        "route53",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def create_dns_record(host: str, target: str = "envoy") -> str:
    """Create a Route53 A record pointing host → Envoy NLB."""
    client = _client()

    zones = client.list_hosted_zones()["HostedZones"]
    if not zones:
        zone = client.create_hosted_zone(
            Name="local.",
            CallerReference=f"init-{host}",
        )
        zone_id = zone["HostedZone"]["Id"]
    else:
        zone_id = zones[0]["Id"]

    client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": f"{host}.",
                    "Type": "CNAME",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": target}],
                },
            }]
        },
    )
    print(f"[dns] created CNAME {host} → {target}")
    return zone_id


def delete_dns_record(host: str) -> None:
    client = _client()
    zones = client.list_hosted_zones()["HostedZones"]
    if not zones:
        return
    zone_id = zones[0]["Id"]
    try:
        client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [{
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": f"{host}.",
                        "Type": "CNAME",
                        "TTL": 60,
                        "ResourceRecords": [{"Value": "envoy"}],
                    },
                }]
            },
        )
    except Exception as e:
        print(f"[dns] delete skipped: {e}")
