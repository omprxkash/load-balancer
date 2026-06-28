import os
import json
import boto3

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "osb-provisioning")


def _client():
    return boto3.client(
        "sqs",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def _queue_url(client) -> str:
    return client.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]


def enqueue_provision(
    instance_id: str, service_id: str, plan_id: str, parameters: dict
) -> None:
    client = _client()
    client.send_message(
        QueueUrl=_queue_url(client),
        MessageBody=json.dumps({
            "action": "provision",
            "instance_id": instance_id,
            "service_id": service_id,
            "plan_id": plan_id,
            "parameters": parameters,
        }),
    )


def enqueue_deprovision(instance_id: str, service_id: str, plan_id: str) -> None:
    client = _client()
    client.send_message(
        QueueUrl=_queue_url(client),
        MessageBody=json.dumps({
            "action": "deprovision",
            "instance_id": instance_id,
            "service_id": service_id,
            "plan_id": plan_id,
        }),
    )
