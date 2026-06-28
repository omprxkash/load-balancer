import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

with patch("app.context.dynamodb_source.DynamoDBSource.fetch", return_value=[]):
    with patch("app.context.s3_source.S3GlobalSource.fetch", return_value=[{}]):
        from app.main import app

client = TestClient(app)

MOCK_SERVICES = [
    {
        "service_id": "jira-lb-001",
        "backend": "jira-mock",
        "host": "jira.local",
        "port": 9010,
        "routes": ["/"],
        "timeout_ms": 30000,
        "retry_attempts": 3,
        "auth_required": False,
        "rate_limit_rps": 0,
        "enabled": True,
    }
]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@patch("app.xds.clusters.DynamoDBSource.fetch", return_value=MOCK_SERVICES)
@patch("app.xds.clusters.S3GlobalSource.fetch", return_value=[{}])
def test_cds_returns_clusters(mock_s3, mock_db):
    resp = client.post("/v2/discovery:clusters", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "resources" in data
    assert "version_info" in data
    names = [r.get("name") for r in data["resources"]]
    assert "jira-mock" in names
    assert "auth_sidecar_cluster" in names
    assert "ratelimit_cluster" in names


@patch("app.xds.routes.DynamoDBSource.fetch", return_value=MOCK_SERVICES)
@patch("app.xds.routes.S3GlobalSource.fetch", return_value=[{}])
def test_rds_returns_route_config(mock_s3, mock_db):
    resp = client.post("/v2/discovery:routes", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["resources"]) == 1
    rc = data["resources"][0]
    assert rc["name"] == "local_route"
    vh_names = [vh["name"] for vh in rc.get("virtual_hosts", [])]
    assert "jira-mock" in vh_names


@patch("app.xds.listeners.DynamoDBSource.fetch", return_value=MOCK_SERVICES)
@patch("app.xds.listeners.S3GlobalSource.fetch", return_value=[{}])
def test_lds_returns_listener(mock_s3, mock_db):
    resp = client.post("/v2/discovery:listeners", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["resources"]) == 1
    listener = data["resources"][0]
    assert listener["name"] == "listener_0"


@patch("app.xds.endpoints.DynamoDBSource.fetch", return_value=MOCK_SERVICES)
def test_eds_returns_endpoints(mock_db):
    resp = client.post("/v2/discovery:endpoints", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["resources"]) >= 1
    assert data["resources"][0]["cluster_name"] == "jira-mock"
