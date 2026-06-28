from pydantic import BaseModel, Field
from typing import Any


class SchemaParameters(BaseModel):
    schema_: str = Field(
        "http://json-schema.org/draft-04/schema#", alias="$schema"
    )
    type: str = "object"
    properties: dict[str, Any] = {}
    required: list[str] = []

    model_config = {"populate_by_name": True}


class InstanceSchema(BaseModel):
    create: dict[str, SchemaParameters] | None = None
    update: dict[str, SchemaParameters] | None = None


class PlanSchemas(BaseModel):
    service_instance: InstanceSchema | None = None


class ServicePlan(BaseModel):
    id: str
    name: str
    description: str
    free: bool = True
    bindable: bool | None = None
    plan_updateable: bool = False
    schemas: PlanSchemas | None = None
    maximum_polling_duration: int | None = None


class ServiceOffering(BaseModel):
    id: str
    name: str
    description: str
    bindable: bool = True
    instances_retrievable: bool = True
    bindings_retrievable: bool = True
    plan_updateable: bool = False
    tags: list[str] = []
    plans: list[ServicePlan]


class CatalogResponse(BaseModel):
    services: list[ServiceOffering]
