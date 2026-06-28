import uuid
import yaml
from fastapi import APIRouter
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from .discovery import DiscoveryRequest, DiscoveryResponse
from app.context.dynamodb_source import DynamoDBSource
from app.context.s3_source import S3GlobalSource

router = APIRouter()
TMPL_DIR = Path(__file__).parent.parent / "templates"
jinja = Environment(loader=FileSystemLoader(str(TMPL_DIR)))

CDS_TYPE = "type.googleapis.com/envoy.config.cluster.v3.Cluster"

def _socket_endpoint(address: str, port: int) -> dict:
    return {"lb_endpoints": [
        {"endpoint": {"address": {"socket_address": {
            "address": address, "port_value": port,
        }}}}
    ]}


_HTTP2_OPTIONS_TYPE = (
    "type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions"
)

STATIC_CLUSTERS = [
    {
        "@type": CDS_TYPE,
        "name": "auth_sidecar_cluster",
        "connect_timeout": "2s",
        "type": "STRICT_DNS",
        "lb_policy": "ROUND_ROBIN",
        "load_assignment": {
            "cluster_name": "auth_sidecar_cluster",
            "endpoints": [_socket_endpoint("auth-sidecar", 9001)],
        },
    },
    {
        "@type": CDS_TYPE,
        "name": "ratelimit_cluster",
        "connect_timeout": "2s",
        "type": "STRICT_DNS",
        "lb_policy": "ROUND_ROBIN",
        "typed_extension_protocol_options": {
            "envoy.extensions.upstreams.http.v3.HttpProtocolOptions": {
                "@type": _HTTP2_OPTIONS_TYPE,
                "explicit_http_config": {"http2_protocol_options": {}},
            }
        },
        "load_assignment": {
            "cluster_name": "ratelimit_cluster",
            "endpoints": [_socket_endpoint("ratelimit", 8081)],
        },
    },
]


@router.post("/v2/discovery:clusters", response_model=DiscoveryResponse)
def cds(req: DiscoveryRequest):
    services = DynamoDBSource().fetch()
    global_cfg = S3GlobalSource().fetch()[0] if S3GlobalSource().fetch() else {}
    tmpl = jinja.get_template("cluster.yaml.j2")

    resources = list(STATIC_CLUSTERS)
    seen_backends: set[str] = set()
    for svc in services:
        backend = svc.get("backend", "")
        if backend in seen_backends:
            continue
        seen_backends.add(backend)
        rendered = tmpl.render(service=svc, global_cfg=global_cfg)
        cluster = yaml.safe_load(rendered)
        resources.append(cluster)

    return DiscoveryResponse(
        version_info=str(uuid.uuid4()),
        resources=resources,
        type_url=CDS_TYPE,
    )
