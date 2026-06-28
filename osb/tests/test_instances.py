import pytest
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

with (
    patch("app.storage.dynamodb._client"),
    patch("app.queue.sqs._client"),
):
    from app.main import app

client = TestClient(app)


def auth_headers():
    token = base64.b64encode(b"admin:secret").decode()
    return {"Authorization": f"Basic {token}", "X-Broker-API-Version": "2.17"}


PROVISION_BODY = {
    "service_id": "atlassian-load-balancing-v1",
    "plan_id": "lb-basic",
    "parameters": {"backend": "jira-mock", "host": "jira.local", "port": 9010},
}


@patch("app.routes.instances.sqs.enqueue_provision")
@patch("app.routes.instances.dynamodb.get_instance", return_value=None)
@patch("app.routes.instances.dynamodb.put_instance")
def test_provision_creates_instance(mock_put, mock_get, mock_enqueue):
    resp = client.put(
        "/v2/service_instances/test-jira",
        json=PROVISION_BODY,
        headers=auth_headers(),
    )
    assert resp.status_code == 202
    assert "operation" in resp.json()
    mock_put.assert_called_once()
    mock_enqueue.assert_called_once()


@patch("app.routes.instances.dynamodb.get_instance", return_value={
    "service_id": "atlassian-load-balancing-v1",
    "plan_id": "lb-basic",
    "state": "in progress",
    "operation": "op-123",
})
def test_provision_idempotent(mock_get):
    resp = client.put(
        "/v2/service_instances/test-jira",
        json=PROVISION_BODY,
        headers=auth_headers(),
    )
    assert resp.status_code == 200


@patch("app.routes.instances.dynamodb.get_instance", return_value={
    "state": "succeeded",
    "operation": "op-123",
})
def test_last_operation_succeeded(mock_get):
    resp = client.get(
        "/v2/service_instances/test-jira/last_operation",
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "succeeded"


@patch("app.routes.instances.dynamodb.get_instance", return_value=None)
def test_last_operation_gone(mock_get):
    resp = client.get(
        "/v2/service_instances/deleted-id/last_operation",
        headers=auth_headers(),
    )
    assert resp.status_code == 410


def test_provision_requires_auth():
    resp = client.put("/v2/service_instances/x", json=PROVISION_BODY)
    assert resp.status_code == 401
