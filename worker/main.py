import os
import json
import time
import boto3
from tasks.models import ProvisionTask
from tasks import dns, cdn, lb_config

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "osb-provisioning")
INSTANCES_TABLE = os.getenv("DYNAMODB_INSTANCES_TABLE", "osb-instances")


def _sqs():
    return boto3.client(
        "sqs",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def _db():
    return boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def mark_state(instance_id: str, state: str, error: str | None = None) -> None:
    db = _db()
    table = db.Table(INSTANCES_TABLE)
    expr = "SET #s = :s"
    names = {"#s": "state"}
    values = {":s": state}
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


def handle_provision(task: ProvisionTask) -> None:
    params = task.parameters
    host = params.get("host", task.instance_id)

    dns.create_dns_record(host)
    cdn.create_distribution(host)
    lb_config.write_service_config(task.instance_id, params)

    mark_state(task.instance_id, "succeeded")
    print(f"[worker] provisioned {task.instance_id} for host={host}")


def handle_deprovision(task: ProvisionTask) -> None:
    params = task.parameters
    host = params.get("host", task.instance_id)

    dns.delete_dns_record(host)
    lb_config.delete_service_config(task.instance_id)

    mark_state(task.instance_id, "succeeded")
    print(f"[worker] deprovisioned {task.instance_id}")


def process_message(body: str) -> None:
    data = json.loads(body)
    task = ProvisionTask(**data)

    try:
        if task.action == "provision":
            handle_provision(task)
        elif task.action == "deprovision":
            handle_deprovision(task)
    except Exception as exc:
        print(f"[worker] ERROR on {task.instance_id}: {exc}")
        mark_state(task.instance_id, "failed", str(exc))
        raise


def run() -> None:
    client = _sqs()

    while True:
        try:
            url = client.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
        except Exception:
            print("[worker] waiting for SQS queue...")
            time.sleep(3)
            continue

        resp = client.receive_message(
            QueueUrl=url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
        )
        messages = resp.get("Messages", [])

        for msg in messages:
            try:
                process_message(msg["Body"])
                client.delete_message(QueueUrl=url, ReceiptHandle=msg["ReceiptHandle"])
            except Exception as exc:
                print(f"[worker] message processing failed, leaving in queue: {exc}")


if __name__ == "__main__":
    print("[worker] starting, polling SQS...")
    run()
