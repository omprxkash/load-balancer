from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok", "service": "bitbucket-mock"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(request: Request, path: str = ""):
    return {
        "service": "Bitbucket Mock",
        "message": "Hello from Bitbucket Mock — routed via Envoy proxy",
        "method": request.method,
        "path": f"/{path}",
        "headers": {
            "host": request.headers.get("host"),
            "x-forwarded-for": request.headers.get("x-forwarded-for"),
        },
    }
