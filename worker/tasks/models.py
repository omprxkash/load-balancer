from pydantic import BaseModel
from typing import Any, Literal


class ProvisionTask(BaseModel):
    action: Literal["provision", "deprovision"]
    instance_id: str
    service_id: str
    plan_id: str
    parameters: dict[str, Any] = {}
