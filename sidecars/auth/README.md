# Auth Sidecar

This implements Envoy's `ext_authz` HTTP external authorization service.

## How it works

```
Client → Envoy → [ext_authz check] → Auth Sidecar
                      ↓ 200 OK           ↓ Token valid
                  Envoy forwards     Return 200 + inject headers
                  to backend
                      ↓ 403 Denied
                  Envoy returns 403
                  Client never reaches backend
```

Envoy is configured with the `envoy.filters.http.ext_authz` filter in the
HTTP Connection Manager (HCM) filter chain. For every incoming request, Envoy
sends a `POST /check` to this sidecar before forwarding upstream.

## Why a sidecar

- Auth logic can change without redeploying Envoy
- All services get auth for free — no per-service implementation
- At scale, write this in Rust for zero GC pauses on the hot path
  (a 1ms GC pause at p99 adds 1ms to every request)
- Crates: `tonic` for gRPC, `axum` for HTTP, `jsonwebtoken` for JWT validation

## This Python implementation

We use Python for readability. The interface is identical — Envoy doesn't care
what language the sidecar is written in, only that `/check` returns the right response.

In production, replace the shared-secret check with JWT validation:
```python
from jose import jwt
payload = jwt.decode(token, public_key, algorithms=["RS256"])
```

## Envoy config (set via Sovereign listener.yaml.j2)

```yaml
- name: envoy.filters.http.ext_authz
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
    http_service:
      server_uri:
        uri: http://auth-sidecar:9001
        cluster: auth_sidecar_cluster
        timeout: 2s
      path_prefix: /check
```

## Extending to authorization (authz)

Authentication (authn) = "who are you?" — this sidecar.
Authorization (authz) = "what can you do?" — a separate sidecar that
checks permissions against a policy store (OPA, Casbin, etc.).
