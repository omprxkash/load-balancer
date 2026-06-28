#!/bin/bash
# Load test the Envoy proxy using curl in a loop.
# Install `hey` (https://github.com/rakyll/hey) for proper load testing.

PROXY_URL="${PROXY_URL:-http://localhost:10000}"
TOKEN="${AUTH_SHARED_SECRET:-dev-token-for-testing}"
REQUESTS="${REQUESTS:-100}"

echo "=== Load testing Envoy proxy at ${PROXY_URL} ==="
echo "    Sending ${REQUESTS} requests to jira.local"
echo ""

if command -v hey &>/dev/null; then
  hey -n "${REQUESTS}" -c 10 \
    -H "Host: jira.local" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${PROXY_URL}/"
else
  echo "  (hey not installed, falling back to sequential curl)"
  SUCCESS=0
  FAIL=0
  for i in $(seq 1 "${REQUESTS}"); do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Host: jira.local" \
      -H "Authorization: Bearer ${TOKEN}" \
      "${PROXY_URL}/")
    if [ "${CODE}" = "200" ]; then
      ((SUCCESS++))
    else
      ((FAIL++))
    fi
  done
  echo "Results: ${SUCCESS} OK, ${FAIL} failed out of ${REQUESTS}"
fi

echo ""
echo "=== Envoy stats ==="
curl -s http://localhost:9901/stats | grep -E "upstream_rq_total|downstream_rq_total" | head -10
