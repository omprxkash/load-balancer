# Edge Load-Balancing Platform

A self-service load-balancing system I built to understand how large-scale platforms
handle routing, auth, and provisioning at the edge — without platform teams becoming a bottleneck.

The idea: developers declare "I want load balancing for my service" and the system
automatically provisions routing, security, and observability. No manual config, no tickets.

---

## Architecture

```
Developer / Build Server
         │
         │ PUT /v2/service_instances/:id  (Open Service Broker v2)
         ▼
┌─────────────────┐     ┌─────┐     ┌──────────┐     ┌──────────────┐
│  Open Service   │────▶│ SQS │────▶│  Worker  │────▶│   DynamoDB   │
│  Broker (FastAPI│     └─────┘     │ Route53  │     │ osb-instances│
│  port 8080)     │                 │ CloudFront│    │ sovereign-svc │
└─────────────────┘                 └──────────┘     └──────┬───────┘
                                                            │
                                                     ┌──────▼───────┐
                                                     │  Sovereign   │ ◀── S3 (global cfg)
                                                     │  (xDS ctrl   │
                                                     │  plane 8001) │
                                                     │  Jinja2 tmpl │
                                                     └──────┬───────┘
                                                            │ xDS REST (every 5s)
                                              ┌─────────────▼──────────────┐
                                              │      Envoy Fleet (×5)      │
                                              │  ext_authz → ratelimit     │
                                              │  → router  → access_log    │
                                              └──────┬─────────────────────┘
                                                     │ routes by Host: header
                                         ┌───────────┼───────────┐
                                         ▼           ▼           ▼
                                    jira-mock  confluence  bitbucket
```

---

## What It Covers

| Concept | Where |
|---|---|
| Open Service Broker v2 spec | `osb/` — all 10 endpoints |
| Async provisioning via SQS | `worker/main.py` — long-poll consumer |
| Route53 + CloudFront provisioning | `worker/tasks/dns.py`, `cdn.py` |
| xDS control plane | `sovereign/` — CDS/RDS/LDS/EDS |
| Jinja2 template abstraction | `sovereign/app/templates/*.j2` |
| Dynamic context from DynamoDB + S3 | `sovereign/app/context/` |
| Envoy proxy with dynamic config | `envoy/bootstrap.yaml` |
| ext_authz sidecar | `sidecars/auth/main.py` |
| Rate limiting | `sidecars/ratelimit/ratelimit.yaml` |
| Kubernetes (replaces EC2 + AMI + ASG) | `infra/k8s/` — 5 replicas + HPA |
| Historical: Packer + SaltStack | `packer/` — what AMI-based deploys looked like |
| LocalStack (local AWS) | `infra/localstack/init.sh` |
| CI pipeline | `.github/workflows/ci.yml` |

---

## Quickstart

### Prerequisites
```bash
bash scripts/bootstrap.sh
```

### Run locally with Docker Compose
```bash
make up      # starts everything: LocalStack, OSB, Worker, Sovereign, Envoy, sidecars, backends
make demo    # provisions jira-mock and tests routing end-to-end through Envoy
make test    # unit tests
```

### What the demo does

```bash
# 1. Provision a load balancer for jira-mock
curl -X PUT http://localhost:8080/v2/service_instances/jira-lb-001 \
  -u admin:secret \
  -H "Content-Type: application/json" \
  -H "X-Broker-API-Version: 2.17" \
  -d '{"service_id":"atlassian-load-balancing-v1","plan_id":"lb-basic",
       "parameters":{"backend":"jira-mock","host":"jira.local","port":9010}}'

# 2. Worker picks up SQS task → Route53 + CloudFront + writes config to DynamoDB

# 3. Sovereign polls DynamoDB → renders Jinja2 templates → Envoy picks up new route (every 5s)

# 4. Traffic now routes through Envoy
curl -H "Host: jira.local" http://localhost:10000/
# → {"service": "Jira Mock", "message": "Hello from Jira Mock — routed via Envoy proxy"}

# 5. Without auth token → 403 at the proxy, backend never reached
curl -H "Host: jira.local" http://localhost:10000/
# → 403
```

### Kubernetes (kind)
```bash
winget install Kubernetes.kind   # one-time setup
make k8s                         # creates cluster, deploys everything
make demo                        # same demo, runs in-cluster
make k8s-down
```

---

## Endpoints

| Service | URL | Notes |
|---|---|---|
| OSB Catalog | http://localhost:8080/v2/catalog | Basic auth: admin/secret |
| OSB Docs | http://localhost:8080/docs | Swagger UI |
| Sovereign health | http://localhost:8001/health | |
| Sovereign services | http://localhost:8001/admin/services | current provisioned state |
| Envoy proxy | http://localhost:10000 | use Host header to select backend |
| Envoy admin | http://localhost:9901 | cluster list, stats, config dump |
| Auth sidecar | http://localhost:9001/health | |
| LocalStack | http://localhost:4566 | all AWS services (free tier) |

---

## Reference Docs

- [OSB Spec](docs/references/osb-spec.md) — all 10 endpoints, schemas, status codes
- [Connexion Notes](docs/references/connexion-notes.md) — OpenAPI-first approach vs FastAPI
- [Envoy Concepts](docs/references/envoy-concepts.md) — xDS, HCM, filter chain, sidecars
- [Sovereign Guide](docs/references/sovereign-guide.md) — template engine, context sources, data flow
- [Architecture](docs/architecture.md) — full design with original vs modern comparison
- [Video Concepts](docs/video-concepts.md) — every concept explained with code references

---

## Directory Structure

```
load-balancer/
├── osb/              Open Service Broker (FastAPI, OSB v2 spec)
├── worker/           Async SQS consumer — Route53, CloudFront, config writes
├── sovereign/        Envoy xDS control plane — Jinja2 templates + context sources
├── sidecars/
│   ├── auth/         ext_authz Bearer token validation
│   └── ratelimit/    Rate limiting config (Envoy ratelimit service)
├── backends/         Mock Jira, Confluence, Bitbucket
├── envoy/            Bootstrap config + Dockerfile
├── infra/
│   ├── localstack/   DynamoDB + SQS + S3 + Route53 init scripts
│   ├── k8s/          kind cluster manifests (5 Envoy replicas + HPA)
│   └── terraform/    Optional: real AWS single-region deploy
├── packer/           Historical: Packer + SaltStack AMI build reference
├── demo/             Provisioning + load test scripts
├── docs/             Architecture, concepts, reference files
└── scripts/          Bootstrap + smoke test
```

---

## EC2 vs Kubernetes

The original pattern for this kind of system was:
Packer → SaltStack → AMI → CloudFormation AutoScaling Group → NLB

The `packer/` directory shows that approach. The `infra/k8s/` directory is the modern equivalent:

| Old Pattern | This Repo |
|---|---|
| Packer `.pkr.hcl` | `Dockerfile` |
| SaltStack states | `Dockerfile RUN` commands |
| AMI snapshot | Docker image |
| CloudFormation ASG | `Deployment` with 5 replicas |
| NLB | `Service` type LoadBalancer |
| CloudFormation parameters | `ConfigMap` + environment variables |
| 13 AWS regions | kind cluster (same concepts, local) |
| ASG scale-out policy | `HorizontalPodAutoscaler` |
