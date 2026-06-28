from fastapi import APIRouter, Header, HTTPException, Response
from app.models.binding import BindRequest, BindResponse
from app.storage import dynamodb

router = APIRouter(prefix="/v2")


def _require_version(x_broker_api_version: str | None):
    if not x_broker_api_version:
        raise HTTPException(
            status_code=400, detail="X-Broker-API-Version header required"
        )


@router.put(
    "/service_instances/{instance_id}/service_bindings/{binding_id}",
    status_code=201,
    response_model=BindResponse,
)
def create_binding(
    instance_id: str,
    binding_id: str,
    body: BindRequest,
    response: Response,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)

    instance = dynamodb.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Service instance not found")

    existing = dynamodb.get_binding(binding_id)
    if existing:
        response.status_code = 200
        return BindResponse(credentials=existing.get("credentials"))

    params = instance.get("parameters", {})
    credentials = {
        "host": params.get("host", ""),
        "port": params.get("port", 80),
        "proxy_endpoint": "http://envoy:10000",
        "host_header": params.get("host", ""),
        "binding_id": binding_id,
    }
    dynamodb.put_binding(binding_id, {
        "binding_id": binding_id,
        "instance_id": instance_id,
        "service_id": body.service_id,
        "plan_id": body.plan_id,
        "credentials": credentials,
    })
    return BindResponse(
        credentials=credentials,
        endpoints=[{"host": "envoy", "ports": [{"port": 10000, "protocol": "http"}]}],
    )


@router.get("/service_instances/{instance_id}/service_bindings/{binding_id}")
def fetch_binding(
    instance_id: str,
    binding_id: str,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_binding(binding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"credentials": item.get("credentials", {})}


@router.delete(
    "/service_instances/{instance_id}/service_bindings/{binding_id}",
    status_code=200,
)
def delete_binding(
    instance_id: str,
    binding_id: str,
    service_id: str,
    plan_id: str,
    x_broker_api_version: str | None = Header(default=None),
):
    _require_version(x_broker_api_version)
    item = dynamodb.get_binding(binding_id)
    if not item:
        raise HTTPException(status_code=410, detail="Gone")
    dynamodb.delete_binding(binding_id)
    return {}
