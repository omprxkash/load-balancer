#!/bin/bash
# Provision a load balancer for the jira-mock backend via the OSB API.
# This is what a developer's build server would do when deploying a new service.

set -e

OSB_URL="${OSB_URL:-http://localhost:8080}"
AUTH="admin:secret"

echo "=== Provisioning load balancer for jira-mock ==="
curl -s -X PUT "${OSB_URL}/v2/service_instances/jira-lb-001" \
  -u "${AUTH}" \
  -H "Content-Type: application/json" \
  -H "X-Broker-API-Version: 2.17" \
  -d '{
    "service_id": "atlassian-load-balancing-v1",
    "plan_id": "lb-basic",
    "parameters": {
      "backend": "jira-mock",
      "host": "jira.local",
      "port": 9010,
      "routes": ["/", "/rest/", "/issues/"],
      "timeout_ms": 30000,
      "retry_attempts": 3,
      "auth_required": false,
      "rate_limit_rps": 100
    }
  }' | python3 -m json.tool

echo ""
echo "=== Polling for completion ==="
for i in $(seq 1 10); do
  STATE=$(curl -s -u "${AUTH}" \
    -H "X-Broker-API-Version: 2.17" \
    "${OSB_URL}/v2/service_instances/jira-lb-001/last_operation" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "  state: ${STATE}"
  if [ "${STATE}" = "succeeded" ]; then
    echo "=== Provisioning complete! ==="
    break
  fi
  sleep 2
done
