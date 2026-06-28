"""
Auth Sidecar — implements Envoy's ext_authz HTTP service.

Envoy sends every incoming request here BEFORE forwarding to the backend.
We inspect the Authorization header. If valid, we return 200 OK and Envoy
continues. If invalid or missing, we return 403 and Envoy returns 403 to
the client — the backend never sees the request.

We implement it in Python so the architecture is clear and readable.
In production, replace the shared-secret check with JWT validation
against an identity provider.

The Envoy ext_authz filter sends a POST to /check with request metadata.
We validate a Bearer token against AUTH_SHARED_SECRET.

In production this would validate JWTs against an identity provider.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

AUTH_SECRET = os.getenv("AUTH_SHARED_SECRET", "dev-token-for-testing")

app = FastAPI(
    title="Auth Sidecar",
    description="Envoy ext_authz HTTP service",
    redirect_slashes=False,
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-sidecar"}


@app.api_route("/check", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"])
@app.api_route(
    "/check/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
)
async def check(request: Request, full_path: str = ""):
    """
    Envoy ext_authz check endpoint.
    Returns 200 to allow, 403 to deny.
    Envoy passes original request headers in the body and as HTTP headers.
    """
    body = await request.json()

    auth_header = (
        body.get("attributes", {})
        .get("request", {})
        .get("http", {})
        .get("headers", {})
        .get("authorization", "")
    )

    if not auth_header:
        auth_header = request.headers.get("authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=403,
            content={"status": {"code": 7, "message": "Missing Bearer token"}},
        )

    token = auth_header.removeprefix("Bearer ").strip()

    if token != AUTH_SECRET:
        return JSONResponse(
            status_code=403,
            content={"status": {"code": 7, "message": "Invalid token"}},
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": {"code": 0},
            "ok_response": {
                "headers": [
                    {"header": {"key": "x-authenticated", "value": "true"}},
                    {"header": {"key": "x-auth-user", "value": "verified"}},
                ]
            },
        },
    )


