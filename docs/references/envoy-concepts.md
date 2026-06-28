# Envoy Proxy — Core Concepts

Reference: https://www.envoyproxy.io/docs/envoy/latest

## Quick Links (from the video)

### Listeners & Network Layer
- [Listeners — Overview](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/overview)
- [Listener Discovery Service (LDS)](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/lds)
- [HTTP Connection Manager (HCM)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/overview)
- [Route Matching](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/route_matching)
- [Route Discovery Service (RDS)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/rds)
- [Virtual Host Discovery Service (VHDS)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/vhds)
- [HTTP Header Manipulation](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers)
- [Traffic Shifting / Splitting](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/traffic_splitting)

### Upstream Clusters
- [Cluster Manager — Overview](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/overview)
- [Cluster Discovery Service (CDS)](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cds)
- [Health Checking](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_hc)
- [Circuit Breaking](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_circuit_breakers)

### HTTP Filters (Sidecars)
- [External Authorization (ext_authz)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_authz_filter)
- [External Processing (ext_proc)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter)
- [Rate Limit Filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/rate_limit_filter)
- [Local Rate Limit Filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter)

### Observability
- [Access Logging](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)

### xDS Protocol
- [xDS REST and gRPC Protocol](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol)

---

## What Envoy Is

An L7 (application-layer) proxy and communication bus built at Lyft, now CNCF graduated.
Runs alongside services ("out of process") and forms a transparent communication mesh.

**Key design principle:** All configuration is API-driven and hot-reloadable.
No restart needed to change routes, clusters, or TLS certs.

## Envoy vs nginx

| Envoy | nginx |
|---|---|
| Cloud-native, dynamic config via xDS API | Originally static config (nginx.conf) |
| Hot config reload without restart | SIGHUP reload (brief interruption risk) |
| First-class gRPC, HTTP/2, HTTP/3 | Add-on module |
| Filter chain: stackable L3/L4 + L7 filters | Module-based |
| Designed for 1000s of service clusters | Works best with smaller upstream sets |
| Built-in distributed tracing | Plugin |
| Native Prometheus metrics endpoint | nginx-prometheus-exporter needed |

---

## Core Concepts

### Listener
The entry point — a named address + port that Envoy accepts connections on.
```yaml
listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
    filter_chains: [...]
```
Discovered via **LDS** (Listener Discovery Service).

### Filter Chain
Stacked filters applied to each connection in order.
Outer layer = L3/L4 (TCP). The `http_connection_manager` is a network filter that adds L7.

### HTTP Connection Manager (HCM)
The most important L7 network filter. It:
- Parses HTTP/1.1, HTTP/2, HTTP/3 and WebSocket
- Routes requests to upstream clusters based on virtual host + route rules
- Runs HTTP filters (auth, rate limit, access log, router)
- Is configured via Sovereign's `listener.yaml.j2` template

```yaml
- name: envoy.filters.network.http_connection_manager
  typed_config:
    "@type": .../HttpConnectionManager
    stat_prefix: ingress_http
    route_config: ...
    http_filters:
      - ext_authz
      - ratelimit
      - router   # must be last
```

### Virtual Host
Inside HCM's route config, a virtual host matches on the `Host:` header.
One listener can serve thousands of virtual hosts — one per provisioned service.
```yaml
virtual_hosts:
  - name: jira
    domains: ["jira.local"]
    routes: [...]
  - name: confluence
    domains: ["confluence.local"]
    routes: [...]
```

### Route
Inside a virtual host, a route matches on path/method/headers and specifies action:
- `route` → forward to a cluster
- `redirect` → 301/302
- `direct_response` → return static body (200, 503, etc.)

Routes support: header modification, timeout, retry policy, weighted clusters (canary).

### Cluster
The upstream — a named group of backend servers.
```yaml
clusters:
  - name: jira-mock
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: jira-mock
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: jira-mock
                    port_value: 9010
```
Discovered via **CDS** + **EDS**.

---

## xDS — The Dynamic Configuration Protocol

xDS = "x Discovery Service" — the API family between Envoy and its control plane (Sovereign).

| Acronym | Full Name | Configures |
|---|---|---|
| **LDS** | Listener Discovery Service | Listeners + filter chains |
| **RDS** | Route Discovery Service | HTTP routing tables |
| **CDS** | Cluster Discovery Service | Upstream cluster definitions |
| **EDS** | Endpoint Discovery Service | IP:port endpoints within clusters |
| **SDS** | Secret Discovery Service | TLS certs + private keys |
| **VHDS** | Virtual Host Discovery Service | Virtual hosts (separate from full RDS) |
| **SRDS** | Scoped Route Discovery Service | Splits massive route tables |
| **ADS** | Aggregated Discovery Service | Single gRPC stream for all types |
| **RTDS** | Runtime Discovery Service | Feature flags |
| **ECDS** | Extension Config Discovery Service | Pluggable extension configs |

**How it works:**
1. Envoy boots with `bootstrap.yaml` pointing at Sovereign address
2. Envoy sends `POST /v3/discovery:clusters` → Sovereign returns CDS DiscoveryResponse
3. Envoy applies cluster config live — no restart
4. Envoy repeats for LDS, RDS, EDS every `refresh_delay` seconds
5. If config changes in DynamoDB, next poll picks it up automatically

---

## Sidecars — Edge Security Services

### ext_authz (External Authorization)
```
Request → Envoy → POST /check → Auth Sidecar
                      ↓ 200             ↓ Valid token
                  Forward to backend    Add x-authenticated header
                      ↓ 403
                  Return 403 to client
                  (backend never sees request)
```

The auth sidecar implements this interface. In production, this would validate JWTs
against an identity provider. Written in Rust at scale for zero GC pauses on the hot path.
Our replica implements the same interface in Python for clarity.

### ext_proc (External Processing)
More powerful than ext_authz — the sidecar can read AND modify request/response body and headers.
Used for: request signing, response transformation, custom header injection.

### HTTP Filters (inside HCM, in order)
1. `ext_authz` — check authorization
2. `ratelimit` — enforce rate limits via ratelimit service
3. `router` — actually forward the request (must always be last)

### Access Logging
Native to HCM — not a sidecar. Configured via Sovereign templates.
Structured JSON output includes: timestamp, method, path, host, response code, latency, upstream cluster.
