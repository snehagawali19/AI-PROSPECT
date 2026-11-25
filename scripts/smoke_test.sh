#!/usr/bin/env bash
# Smoke test a running instance. Usage: scripts/smoke_test.sh [base_url]   (default http://localhost:4000)
set -u
BASE="${1:-http://localhost:4000}"
pass=0; fail=0
check() {  # name expected_status method path [json_body]
  local name="$1" expected="$2" method="$3" path="$4" body="${5:-}"
  if [ -n "$body" ]; then
    code=$(curl -s -o /tmp/smoke_body -w "%{http_code}" -X "$method" "$BASE$path" -H "Content-Type: application/json" -d "$body")
  else
    code=$(curl -s -o /tmp/smoke_body -w "%{http_code}" -X "$method" "$BASE$path")
  fi
  if [ "$code" = "$expected" ]; then echo "PASS  $name ($code)"; pass=$((pass+1));
  else echo "FAIL  $name (got $code, expected $expected): $(head -c 300 /tmp/smoke_body)"; fail=$((fail+1)); fi
}
check "health"              200 GET  /health
check "openapi docs"        200 GET  /docs
check "openapi schema"      200 GET  /openapi.json
check "validation error"    422 POST /prospect-discovery '{"query":"a"}'
check "missing body field"  422 POST /prospect-discovery '{}'
echo "--- live discovery (needs real keys in .env; 503 = LLM keys/model IDs not configured) ---"
check "live discovery"      200 POST /prospect-discovery '{"query":"Restaurant owners in Dubai UAE"}'
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
