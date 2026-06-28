from fastapi import FastAPI
from app.xds import clusters, routes, listeners, endpoints

app = FastAPI(
    title="Sovereign",
    description=(
        "Envoy xDS control plane — dynamically renders proxy config"
        " from templates + context"
    ),
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sovereign"}


@app.get("/admin/services")
def list_services():
    """Read-only view of all services currently in context
    (matches Sovereign's built-in UI).
    """
    from app.context.dynamodb_source import DynamoDBSource
    return {"services": DynamoDBSource().fetch()}


app.include_router(clusters.router)
app.include_router(routes.router)
app.include_router(listeners.router)
app.include_router(endpoints.router)
