# Open Service Broker API — Reference

Source: https://github.com/cloudfoundry/servicebroker/blob/master/spec.md

The OSB spec defines a standardized REST API that any provisioning system can implement.
It lets internal build systems provision load balancing resources the same way they
provision databases or caches — through a unified broker, no custom API per service.

---

## All API Endpoints

```
GET    /v2/catalog
PUT    /v2/service_instances/:instance_id
GET    /v2/service_instances/:instance_id
PATCH  /v2/service_instances/:instance_id
DELETE /v2/service_instances/:instance_id
GET    /v2/service_instances/:instance_id/last_operation
PUT    /v2/service_instances/:instance_id/service_bindings/:binding_id
GET    /v2/service_instances/:instance_id/service_bindings/:binding_id
DELETE /v2/service_instances/:instance_id/service_bindings/:binding_id
GET    /v2/service_instances/:instance_id/service_bindings/:binding_id/last_operation
```

---

## Authentication

**Method:** HTTP Basic Auth (`Authorization: Basic base64(user:pass)`) on every request.
**Required header:** `X-Broker-API-Version: 2.17`
**On failure:** Return `401 Unauthorized`

---

## Catalog (GET /v2/catalog)

What developers browse to see available services and plans.

```json
{
  "services": [{
    "id": "globally-unique-guid",
    "name": "load-balancing",
    "description": "Self-service edge load balancing via Envoy proxy",
    "bindable": true,
    "plans": [{
      "id": "plan-guid",
      "name": "basic",
      "description": "HTTP/HTTPS routing with TLS termination",
      "free": true,
      "schemas": {
        "service_instance": {
          "create": {
            "parameters": {
              "$schema": "http://json-schema.org/draft-04/schema#",
              "type": "object",
              "properties": {
                "backend":       {"type": "string"},
                "host":          {"type": "string"},
                "port":          {"type": "integer", "default": 80},
                "routes":        {"type": "array", "items": {"type": "string"}},
                "timeout_ms":    {"type": "integer", "default": 30000},
                "auth_required": {"type": "boolean", "default": false}
              },
              "required": ["backend", "host"]
            }
          }
        }
      }
    }]
  }]
}
```

---

## Provisioning (PUT /v2/service_instances/:instance_id)

### Request body
```json
{
  "service_id": "edge-load-balancing-v1",
  "plan_id":    "lb-basic",
  "parameters": {
    "backend": "jira-mock",
    "host":    "jira.local",
    "port":    9010
  }
}
```

### Response (async — 202)
```json
{"operation": "some-uuid"}
```

### Status codes
| Code | Meaning |
|---|---|
| 200 | Already exists with identical params (idempotent) |
| 201 | Created synchronously |
| 202 | Async provisioning started — client must poll |
| 400 | Bad request / missing required field |
| 401 | Unauthorized |
| 409 | Exists with different params (conflict) |
| 422 | Async required but client didn't set `accepts_incomplete=true` |

---

## Polling (GET /v2/service_instances/:id/last_operation)

Client polls this until state is `succeeded` or `failed`.

```json
{"state": "in progress"}   // → keep polling
{"state": "succeeded"}     // → done
{"state": "failed", "description": "Route53 API error"}
```

Status codes: `200` (has state), `410` (deleted), `404` (never existed)

---

## Bindings (PUT /v2/service_instances/:id/service_bindings/:bid)

A binding returns credentials — in this case, the proxy endpoint info.

### Response
```json
{
  "credentials": {
    "host":           "jira.local",
    "proxy_endpoint": "http://envoy:10000",
    "host_header":    "jira.local",
    "binding_id":     "some-uuid"
  },
  "endpoints": [
    {"host": "envoy", "ports": [{"port": 10000, "protocol": "http"}]}
  ]
}
```

---

## Key Behavioral Rules

- **Idempotency:** Same request → same result (no duplicate provisioning)
- **Async always:** Return `202` and use last_operation polling for slow tasks
- **5xx must not mutate state:** If the broker crashes mid-provision, DynamoDB state is the truth
- **410 Gone:** Correct response when polling last_operation after a completed deprovision
