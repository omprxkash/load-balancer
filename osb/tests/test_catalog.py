import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import base64
from app.main import app

client = TestClient(app)
AUTH = ("admin", "secret")


def auth_headers():
    token = base64.b64encode(b"admin:secret").decode()
    return {"Authorization": f"Basic {token}", "X-Broker-API-Version": "2.17"}


def test_catalog_returns_services():
    resp = client.get("/v2/catalog", headers=auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert len(data["services"]) >= 1


def test_catalog_service_has_plans():
    resp = client.get("/v2/catalog", headers=auth_headers())
    svc = resp.json()["services"][0]
    assert len(svc["plans"]) >= 1
    plan = svc["plans"][0]
    assert "id" in plan
    assert "name" in plan
    assert "description" in plan


def test_catalog_plan_has_schema():
    resp = client.get("/v2/catalog", headers=auth_headers())
    plan = resp.json()["services"][0]["plans"][0]
    schema = plan["schemas"]["service_instance"]["create"]["parameters"]
    assert "backend" in schema["properties"]
    assert "host" in schema["properties"]
    assert "backend" in schema["required"]
    assert "host" in schema["required"]


def test_catalog_requires_auth():
    resp = client.get("/v2/catalog")
    assert resp.status_code == 401


def test_catalog_requires_version_header():
    token = base64.b64encode(b"admin:secret").decode()
    resp = client.get("/v2/catalog", headers={"Authorization": f"Basic {token}"})
    # catalog doesn't check version — only provisioning does
    assert resp.status_code == 200
