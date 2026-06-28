# Sovereign — Envoy xDS Control Plane

PyPI: `pip install sovereign`

---

## What Sovereign Is

A Python-based xDS control plane for Envoy. Envoy proxies poll Sovereign for configuration.
Sovereign dynamically renders that configuration from **Jinja2 templates + context data**.

**Core idea:**
```
Developer parameters → DynamoDB → Sovereign context → Jinja2 template → Envoy config
```

The developer never writes raw Envoy YAML. They provide simple parameters
(backend name, host, port, routes). Sovereign's templates translate those into
valid, complete Envoy configuration.

---

## Architecture

```
┌─────────────────────────────────────────┐
│              Sovereign                  │
│                                         │
│  ┌──────────┐    ┌────────────────────┐ │
│  │ Sources  │    │    Templates       │ │
│  │          │    │                    │ │
│  │ DynamoDB │───▶│ cluster.yaml.j2    │ │
│  │ S3       │    │ route.yaml.j2      │ │
│  │ HTTP     │    │ listener.yaml.j2   │ │
│  │ (custom) │    │                    │ │
│  └──────────┘    └─────────┬──────────┘ │
│                            │            │
│                   Rendered Envoy YAML   │
│                            │            │
└────────────────────────────┼────────────┘
                             │ xDS REST API
                             ▼
                    ┌─────────────────┐
                    │   Envoy Proxy   │
                    │  (polls every   │
                    │   5 seconds)    │
                    └─────────────────┘
```

---

## Template System

You define one Jinja2 template per xDS resource type.
Each template receives `services` (list from DynamoDB) and `global_cfg` (from S3) as context.

### cluster.yaml.j2
Renders one `Cluster` resource per provisioned service.
Variables: `service.backend`, `service.port`, `service.timeout_ms`

### route.yaml.j2
Renders one `RouteConfiguration` with virtual hosts — one per service.
Variables: `service.host`, `service.routes`, `service.auth_required`

### listener.yaml.j2
Renders the main `Listener` with the full HCM filter chain:
ext_authz → ratelimit → router, plus access logging.

---

## Sources (Where Context Comes From)

Sources are Python classes that implement `fetch() → list[dict]`.

| Source | What it fetches |
|---|---|
| `DynamoDBSource` | All provisioned service configs (written by the worker) |
| `S3GlobalSource` | Global overrides (default timeouts, feature flags) from S3 |
| Custom plugin | Write your own — fetch from any system |

**The key insight:** Sovereign polls sources on every xDS request. When a developer
provisions a new load balancer via the OSB API, the worker writes to DynamoDB.
The next time Envoy polls Sovereign (every 5 seconds), Sovereign fetches the new data,
renders the templates, and Envoy picks up the new routing config — **with no restarts anywhere**.

---

## xDS REST Endpoints (our implementation)

| Method | Path | xDS Type | What it returns |
|---|---|---|---|
| POST | `/v2/discovery:clusters` | CDS | All cluster definitions |
| POST | `/v2/discovery:routes` | RDS | Route configuration with virtual hosts |
| POST | `/v2/discovery:listeners` | LDS | Main listener + HCM filter chain |
| POST | `/v2/discovery:endpoints` | EDS | Endpoint IP:port per cluster |
| GET | `/admin/services` | — | Read-only view of current context |

### Request body (DiscoveryRequest)
```json
{
  "version_info": "0",
  "node": {"id": "envoy-proxy-1", "cluster": "proxy-fleet"},
  "resource_names": []
}
```

### Response body (DiscoveryResponse)
```json
{
  "version_info": "abc123",
  "type_url": "type.googleapis.com/envoy.config.cluster.v3.Cluster",
  "resources": [
    { "@type": "...", "name": "jira-mock", "connect_timeout": "30s", ... }
  ]
}
```

---

## The Full Data Flow

```
1. Developer calls OSB API: PUT /v2/service_instances/jira-lb
2. OSB FastAPI receives request, validates parameters, writes to DynamoDB (state: in progress)
3. OSB drops task into SQS queue, responds 202 Accepted
4. Worker picks up SQS message, runs provisioning tasks:
   - Creates Route53 DNS record
   - Creates CloudFront distribution (DDoS protection)
   - Writes Envoy routing intent to DynamoDB sovereign-services table
   - Updates instance state in DynamoDB to "succeeded"
5. Developer polls GET /v2/service_instances/jira-lb/last_operation
   → receives {"state": "succeeded"}
6. Sovereign polls DynamoDB every 5 seconds
   → sees new entry in sovereign-services table
   → renders cluster.yaml.j2, route.yaml.j2, listener.yaml.j2 with new context
7. Envoy polls Sovereign every 5 seconds
   → receives new CDS/LDS responses
   → applies new cluster + virtual host + route config hot (no restart)
8. Traffic to jira.local now routes through Envoy to jira backend
```

Total time from provision to live routing: **~10-15 seconds** (5s worker + 5s Sovereign poll)
