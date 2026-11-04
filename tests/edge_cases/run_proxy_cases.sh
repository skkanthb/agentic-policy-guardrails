#!/usr/bin/env bash
# Usage: ./run_proxy_cases.sh <cases.jsonl> <out.csv> [proxy_url]
# Sends each payload through the running proxy. Requires jq and curl.
# Each request carries an X-Case-Id header so target_received.jsonl can be matched to cases.
set -euo pipefail
CASES="$1"; OUT="$2"; PROXY="${3:-http://localhost:8000/api/v1/credit}"
echo "id,label,expected,http_status,status,error_code,reached_target" > "$OUT"
while IFS= read -r line; do
  id=$(jq -r .id <<<"$line"); label=$(jq -r .label <<<"$line"); exp=$(jq -r .expected <<<"$line")
  before=$(grep -c "\"case_id\": \"$id\"" target_received.jsonl 2>/dev/null || true)
  resp=$(curl -s -w '\n%{http_code}' -X POST "$PROXY" -H 'Content-Type: application/json' -H "X-Case-Id: $id" \
         -d "$(jq -c .payload <<<"$line")")
  code=$(tail -n1 <<<"$resp"); body=$(sed '$d' <<<"$resp")
  st=$(jq -r '.status // ""' <<<"$body" 2>/dev/null || echo PARSE_ERR)
  ec=$(jq -r '.error_code // ""' <<<"$body" 2>/dev/null || echo "")
  after=$(grep -c "\"case_id\": \"$id\"" target_received.jsonl 2>/dev/null || true)
  [ "${after:-0}" -gt "${before:-0}" ] && reached=YES || reached=NO
  echo "$id,$label,$exp,$code,$st,$ec,$reached" >> "$OUT"
done < "$CASES"
echo "Wrote $OUT"
