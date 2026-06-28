from pydantic import BaseModel
from typing import Any


class Node(BaseModel):
    id: str = "envoy-node"
    cluster: str = "proxy-fleet"
    metadata: dict[str, Any] = {}


class DiscoveryRequest(BaseModel):
    version_info: str = "0"
    node: Node = Node()
    resource_names: list[str] = []
    type_url: str = ""


class DiscoveryResponse(BaseModel):
    version_info: str
    resources: list[dict[str, Any]]
    type_url: str
    nonce: str = ""
