# Architecture

---

## Full System Diagram

```
Developer / Build Server
         │
         │ PUT /v2/service_instances/:id
         │ {backend, host, port, routes, ...}
         ▼
┌─────────────────────┐
│   Open Service      │   GET /v2/catalog        → list available services
│   Broker (FastAPI)  │   PUT /v2/service_instances → provision
│   port 8080         │   GET /last_operation    → poll status
│   Basic Auth        │   PUT /service_bindings  → get credentials back
└────────┬────────────┘
         │ 202 Accepted + enqueue task
         ▼
    ┌─────────┐         ┌──────────────┐
    │   SQS   │────────▶│    Worker    │
    │  Queue  │         │              │
    └─────────┘         │ • Route53    │  (LocalStack mock)
                        │ • CloudFront │  (LocalStack mock)
                        │ • lb_config  │──▶ DynamoDB
                        └──────────────┘    sovereign-services table

                    ┌───────────────────────────────────┐
                    │          Sovereign                 │
                    │  (Envoy xDS Control Plane)         │
                    │  port 8001                         │
                    │                                   │
                    │  Sources:                          │
                    │    DynamoDBSource ◀── DynamoDB    │
                    │    S3GlobalSource ◀── S3 bucket   │
                    │                                   │
                    │  Templates (Jinja2):               │
                    │    cluster.yaml.j2                 │
                    │    route.yaml.j2                   │
                    │    listener.yaml.j2                │
                    └──────────────┬────────────────────┘
                                   │ xDS REST API (every 5s)
                                   │ POST /v3/discovery:clusters
                                   │ POST /v3/discovery:listeners
                                   ▼
                     ┌─────────────────────────┐
                     │     Envoy Proxy Fleet   │
                     │  port 10000 (traffic)   │
                     │  port 9901 (admin)      │
                     │                         │
                     │  Filter chain:          │
                     │    ext_authz ──▶ Auth   │
                     │    ratelimit            │
                     │    router               │
                     │    access_log           │
                     └──────┬──────────────────┘
                            │ routes by Host: header
                   ┌────────┴────────────────┐
                   │                         │
                   ▼                         ▼
          ┌──────────────┐         ┌──────────────────┐
          │  jira-mock   │         │ confluence-mock   │
          │  port 9010   │         │  port 9011        │
          └──────────────┘         └──────────────────┘
                                   ┌──────────────────┐
                                   │ bitbucket-mock   │
                                   │  port 9012        │
                                   └──────────────────┘
```

---

## Component Summary

| Component | Tech | Role |
|---|---|---|
| **Open Service Broker** | FastAPI + Pydantic | REST API for provisioning requests (OSB v2 spec) |
| **SQS** | LocalStack | Durable queue decoupling web from slow provisioning work |
| **DynamoDB** | LocalStack | Shared state: instance records + Sovereign context |
| **Worker** | Python | SQS consumer: runs Route53/CloudFront/config tasks |
| **Sovereign** | FastAPI + Jinja2 | xDS control plane: templates + context → Envoy config |
| **Envoy** | envoyproxy/envoy | L7 proxy: dynamic routing, filter chain, observability |
| **Auth Sidecar** | FastAPI (Python) | ext_authz: validates Bearer tokens before backend |
| **Ratelimit** | envoyproxy/ratelimit | Per-route/per-IP rate limiting |
| **Backends** | FastAPI | Mock services for demo routing |
| **kind cluster** | Kubernetes | Modern replacement for EC2 + AMI + CloudFormation ASG |

---

## EC2 vs Kubernetes

| EC2 Pattern | This Repo |
|---|---|
| FastAPI | FastAPI (same) |
| SQS | LocalStack SQS |
| DynamoDB | LocalStack DynamoDB |
| S3 | LocalStack S3 |
| Route53 | LocalStack Route53 |
| CloudFront | LocalStack CloudFront |
| Sovereign | Re-implemented (same design) |
| Envoy proxy | Envoy (same) |
| Auth sidecar (Rust) | Auth sidecar (Python, same interface) |
| 2000 EC2 instances, 13 regions | 5 Envoy pods in kind cluster |
| HashiCorp Packer + SaltStack AMI | Docker images |
| CloudFormation ASG | Kubernetes Deployment + HPA |
| NLB | Kubernetes Service type LoadBalancer |

---

## Why Kubernetes Instead of EC2

The original pattern for this kind of system was:
Packer → SaltStack → AMI → CloudFormation AutoScaling Group → NLB

Today you'd use Kubernetes instead:
- HashiCorp Packer → `Dockerfile`
- SaltStack states → `Dockerfile RUN` commands
- AMI snapshots → Docker images pushed to registry
- CloudFormation AutoScaling Group → `Deployment` with replicas
- CloudFormation NLB → `Service` type LoadBalancer
- CloudFormation parameters → `ConfigMap` + `Secret`

Our `infra/k8s/` directory is exactly this modern version.
