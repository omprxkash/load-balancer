import uuid
from fastapi import APIRouter
from .discovery import DiscoveryRequest, DiscoveryResponse
from app.context.dynamodb_source import DynamoDBSource

router = APIRouter()
EDS_TYPE = "type.googleapis.com/envoy.config.endpoint.v3.ClusterLoadAssignment"


@router.post("/v2/discovery:endpoints", response_model=DiscoveryResponse)
def eds(req: DiscoveryRequest):
    services = DynamoDBSource().fetch()
    resources = []
    for svc in services:
        resources.append({
            "@type": EDS_TYPE,
            "cluster_name": svc["backend"],
            "endpoints": [{
                "lb_endpoints": [{
                    "endpoint": {
                        "address": {
                            "socket_address": {
                                "address": svc["backend"],
                                "port_value": int(svc.get("port", 80)),
                            }
                        }
                    }
                }]
            }],
        })
    return DiscoveryResponse(
        version_info=str(uuid.uuid4()),
        resources=resources,
        type_url=EDS_TYPE,
    )
