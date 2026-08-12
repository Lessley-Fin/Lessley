#!/usr/bin/env bash
# Verify the college-hosted model endpoint (run from a machine ON the college network/VPN).
# Usage:
#   BASE=https://10.10.248.21/v1 \
#   HOST=<ingress-host>.cs.colman.ac.il \
#   MODEL=mistral-small-4-119b-nvfp4 \
#   bash scripts/check_college_model.sh
set -u
BASE="${BASE:-https://10.10.248.21/v1}"
HOST="${HOST:?set HOST to the Run:AI ingress hostname}"
MODEL="${MODEL:-mistral-small-4-119b-nvfp4}"

echo "== 1) /v1/models (what the server actually serves) =="
curl -sk --max-time 20 "$BASE/models" -H "Host: $HOST" \
  -w "\n[http_code=%{http_code} time=%{time_total}s]\n"

echo
echo "== 2) plain chat completion =="
curl -sk --max-time 60 "$BASE/chat/completions" -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply with the single word: ok\"}],\"max_tokens\":10,\"temperature\":0}" \
  -w "\n[http_code=%{http_code} time=%{time_total}s]\n"

echo
echo "== 3) structured output / guided JSON (this is what the app relies on) =="
curl -sk --max-time 60 "$BASE/chat/completions" -H "Host: $HOST" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Return a deal for the store Nike\"}],\"max_tokens\":200,\"temperature\":0,\"response_format\":{\"type\":\"json_schema\",\"json_schema\":{\"name\":\"Deal\",\"strict\":true,\"schema\":{\"type\":\"object\",\"additionalProperties\":false,\"required\":[\"store_name\",\"deal_description\"],\"properties\":{\"store_name\":{\"type\":\"string\"},\"deal_description\":{\"type\":\"string\"}}}}}}" \
  -w "\n[http_code=%{http_code} time=%{time_total}s]\n"
