import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

from app.routes import catalog, instances, bindings

app = FastAPI(
    title="Open Service Broker",
    description="Self-service load balancing — OSB v2 spec",
    version="2.17",
)

security = HTTPBasic()

OSB_USERNAME = os.getenv("OSB_USERNAME", "admin")
OSB_PASSWORD = os.getenv("OSB_PASSWORD", "secret")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(
        credentials.username.encode(), OSB_USERNAME.encode()
    )
    ok_pass = secrets.compare_digest(
        credentials.password.encode(), OSB_PASSWORD.encode()
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.17"}


@app.get("/ready")
def ready():
    from app.storage import dynamodb
    from botocore.exceptions import BotoCoreError, ClientError
    try:
        dynamodb.get_instance("__healthcheck__")
        return {"status": "ready"}
    except (BotoCoreError, ClientError, HTTPException):
        raise HTTPException(status_code=503, detail="Storage not ready")


app.include_router(catalog.router, dependencies=[Depends(verify_credentials)])
app.include_router(instances.router, dependencies=[Depends(verify_credentials)])
app.include_router(bindings.router, dependencies=[Depends(verify_credentials)])
