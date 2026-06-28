from pydantic import BaseModel
from typing import Any


class ProvisionRequest(BaseModel):
    service_id: str
    plan_id: str
    parameters: dict[str, Any] = {}
    context: dict[str, Any] = {}
    organization_guid: str | None = None
    space_guid: str | None = None


class ProvisionResponse(BaseModel):
    operation: str | None = None
    dashboard_url: str | None = None


class UpdateRequest(BaseModel):
    service_id: str
    plan_id: str | None = None
    parameters: dict[str, Any] = {}
    context: dict[str, Any] = {}


class LastOperationResponse(BaseModel):
    state: str  # "in progress" | "succeeded" | "failed"
    description: str | None = None


class InstanceResponse(BaseModel):
    service_id: str
    plan_id: str
    parameters: dict[str, Any] = {}
