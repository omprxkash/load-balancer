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

RDS_TYPE = "type.googleapis.com/envoy.config.route.v3.RouteConfiguration"


@router.post("/v2/discovery:routes", response_model=DiscoveryResponse)
def rds(req: DiscoveryRequest):
    all_services = DynamoDBSource().fetch()
    global_cfg_list = S3GlobalSource().fetch()
    global_cfg = global_cfg_list[0] if global_cfg_list else {}

    seen_hosts: dict[str, dict] = {}
    for svc in all_services:
        seen_hosts[svc.get("host", "")] = svc
    services = list(seen_hosts.values())

    tmpl = jinja.get_template("route.yaml.j2")
    rendered = tmpl.render(services=services, global_cfg=global_cfg)
    route_config = yaml.safe_load(rendered)

    return DiscoveryResponse(
        version_info=str(uuid.uuid4()),
        resources=[route_config],
        type_url=RDS_TYPE,
    )
