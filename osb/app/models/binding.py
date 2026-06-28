from pydantic import BaseModel
from typing import Any


class BindResource(BaseModel):
    app_guid: str | None = None
    route: str | None = None


class BindRequest(BaseModel):
    service_id: str
    plan_id: str
    parameters: dict[str, Any] = {}
    bind_resource: BindResource | None = None
    context: dict[str, Any] = {}


class BindResponse(BaseModel):
    credentials: dict[str, Any] | None = None
    endpoints: list[dict[str, Any]] | None = None
    operation: str | None = None
