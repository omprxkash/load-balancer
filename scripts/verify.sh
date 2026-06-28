#!/bin/bash
# End-to-end smoke test. Run after `make up`.
set -e

OSB="http://localhost:8080"
SOVEREIGN="http://localhost:8001"
PROXY="http://localhost:10000"
AUTH_HDR="Authorization: Basic $(echo -n admin:secret | base64)"
VER_HDR="X-Broker-API-Version: 2.17"
TOKEN="dev-token-for-testing"

pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }
check() { [ "$1" = "$2" ] && pass "$3" || fail "$3 (got $1, expected $2)"; }

echo ""
echo "=== Verifying OSB health ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${OSB}/health")
check "${STATUS}" "200" "OSB health"

echo ""
echo "=== Verifying catalog ==="
SERVICES=$(curl -s -H "${AUTH_HDR}" "${OSB}/v2/catalog" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['services']))")
[ "${SERVICES}" -ge 1 ] && pass "Catalog has services" || fail "Catalog empty"

echo ""
echo "=== Provisioning test service ==="
curl -s -X PUT "${OSB}/v2/service_instances/smoke-test-001" \
  -H "${AUTH_HDR}" -H "${VER_HDR}" -H "Content-Type: application/json" \
  -d '{"service_id":"atlassian-load-balancing-v1","plan_id":"lb-basic","parameters":{"backend":"jira-mock","host":"jira.local","port":9010}}' > /dev/null
pass "Provision request sent"

echo ""
echo "=== Waiting for worker to complete provisioning ==="
for i in $(seq 1 20); do
  STATE=$(curl -s -H "${AUTH_HDR}" -H "${VER_HDR}" \
    "${OSB}/v2/service_instances/smoke-test-001/last_operation" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state','in_progress'))" 2>/dev/null \
    || echo "in_progress")
  [ "${STATE}" = "succeeded" ] && break
  sleep 3
done
check "${STATE}" "succeeded" "Worker completed provisioning"

echo ""
echo "=== Verifying Sovereign sees the service ==="
SCOUNT=$(curl -s "${SOVEREIGN}/admin/services" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['services']))")
[ "${SCOUNT}" -ge 1 ] && pass "Sovereign has services in context" || fail "Sovereign context empty"

echo ""
echo "=== Verifying Envoy xDS responses ==="
CDS=$(curl -s -X POST "${SOVEREIGN}/v2/discovery:clusters" -H "Content-Type: application/json" -d '{}')
echo "${CDS}" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['resources']) >= 1" && pass "CDS returns clusters" || fail "CDS empty"

echo ""
echo "=== Testing auth sidecar ==="
AUTH_STATUS=$(curl -s -X POST "http://localhost:9001/check" \
  -H "Content-Type: application/json" \
  -d "{\"attributes\":{\"request\":{\"http\":{\"headers\":{\"authorization\":\"Bearer ${TOKEN}\"}}}}}" \
  -o /dev/null -w "%{http_code}")
check "${AUTH_STATUS}" "200" "Auth sidecar accepts valid token"

REJECT_STATUS=$(curl -s -X POST "http://localhost:9001/check" \
  -H "Content-Type: application/json" -d '{}' \
  -o /dev/null -w "%{http_code}")
check "${REJECT_STATUS}" "403" "Auth sidecar rejects missing token"

echo ""
echo "=== All checks passed! ==="
