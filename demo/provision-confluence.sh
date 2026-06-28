#!/bin/bash
set -e

OSB_URL="${OSB_URL:-http://localhost:8080}"
AUTH="admin:secret"

echo "=== Provisioning load balancer for confluence-mock ==="
curl -s -X PUT "${OSB_URL}/v2/service_instances/confluence-lb-001" \
  -u "${AUTH}" \
  -H "Content-Type: application/json" \
  -H "X-Broker-API-Version: 2.17" \
  -d '{
    "service_id": "atlassian-load-balancing-v1",
    "plan_id": "lb-basic",
    "parameters": {
      "backend": "confluence-mock",
      "host": "confluence.local",
      "port": 9011,
      "routes": ["/", "/wiki/", "/display/"],
      "timeout_ms": 60000,
      "retry_attempts": 2,
      "auth_required": true,
      "rate_limit_rps": 50
    }
  }' | python3 -m json.tool

echo ""
echo "=== Waiting for provisioning ==="
sleep 5
STATE=$(curl -s -u "${AUTH}" -H "X-Broker-API-Version: 2.17" \
  "${OSB_URL}/v2/service_instances/confluence-lb-001/last_operation" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
echo "Final state: ${STATE}"
