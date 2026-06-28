import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Response
from app.models.instance import (
    ProvisionRequest, ProvisionResponse, UpdateRequest,
    LastOperationResponse, InstanceResponse,
)
from app.storage import dynamodb
from app.queue import sqs

router = APIRouter(prefix="/v2")


def _require_version(x_broker_api_version: str | None):
    if not x_broker_api_version:
        raise HTTPException(
            status_code=400, detail="X-Broker-API-Version header required"
        )


@router.put(
    "/service_instances/{instance_id}",
    status_code=202,
    response_model=ProvisionResponse,
)
def provision(
    instance_id: str,
    body: ProvisionRequest,
    response: Response,
    x_broker_api_version: str | None = Header(default=None),
    accepts_incomplete: bool = False,
):
    _require_version(x_broker_api_version)

    existing = dynamodb.get_instance(instance_id)
    if existing:
        if (
            existing.get("service_id") == body.service_id
            and existing.get("plan_id") == body.plan_id
        ):
            response.status_code = 200
            return ProvisionResponse(operation=existing.get("operation"))
        raise HTTPException(
            status_code=409,
            detail="Instance exists with different parameters",
        )

    operation_id = str(uuid.uuid4())
    dynamodb.put_instance(instance_id, {
        "service_id": body.service_id,
        "plan_id": body.plan_id,
        "parameters": body.parameters,
        "state": "in progress",
        "operation": operation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    sqs.enqueue_provision(instance_id, body.service_id, body.plan_id, body.parameters)

    return ProvisionResponse(operation=operation_id)


@router.get("/service_instances/{instance_id}", response_model=InstanceResponse)
def fetch_instance(
    instance_id: str, x_broker_api_version: str | None = Header(default=None)
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_instance(instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Instance not found")
    return InstanceResponse(
        service_id=item["service_id"],
        plan_id=item["plan_id"],
        parameters=item.get("parameters", {}),
    )


@router.patch("/service_instances/{instance_id}", status_code=200)
def update_instance(
    instance_id: str,
    body: UpdateRequest,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_instance(instance_id)
    if not item:
        raise HTTPException(status_code=404, detail="Instance not found")
    dynamodb.put_instance(instance_id, {
        **item,
        "plan_id": body.plan_id or item["plan_id"],
        "parameters": body.parameters or item.get("parameters", {}),
        "state": "in progress",
    })
    sqs.enqueue_provision(
        instance_id,
        item["service_id"],
        body.plan_id or item["plan_id"],
        body.parameters,
    )
    return {}


@router.delete("/service_instances/{instance_id}", status_code=202)
def deprovision(
    instance_id: str,
    service_id: str,
    plan_id: str,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_instance(instance_id)
    if not item:
        raise HTTPException(status_code=410, detail="Gone")
    dynamodb.update_instance_state(instance_id, "in progress")
    sqs.enqueue_deprovision(instance_id, service_id, plan_id)
    return {"operation": item.get("operation")}


@router.get(
    "/service_instances/{instance_id}/last_operation",
    response_model=LastOperationResponse,
)
def last_operation(
    instance_id: str,
    response: Response,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_instance(instance_id)
    if not item:
        response.status_code = 410
        return LastOperationResponse(
            state="succeeded", description="Instance was deleted"
        )
    return LastOperationResponse(
        state=item.get("state", "in progress"),
        description=item.get("error"),
    )
