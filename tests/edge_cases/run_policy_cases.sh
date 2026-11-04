#!/usr/bin/env bash
# Usage: ./run_policy_cases.sh <path-to-opa> <rego-file> <cases.jsonl> <out.csv>
# Evaluates each payload against the policy only (no proxy). Requires jq.
set -euo pipefail
OPA="$1"; REGO="$2"; CASES="$3"; OUT="$4"
echo "id,label,expected,allow,require_hitl,decision,match" > "$OUT"
while IFS= read -r line; do
  id=$(jq -r .id <<<"$line"); label=$(jq -r .label <<<"$line"); exp=$(jq -r .expected <<<"$line")
  jq -c .payload <<<"$line" > /tmp/_edge_in.json
  res=$("$OPA" eval -f raw -d "$REGO" -i /tmp/_edge_in.json 'data.agent.governance')
  allow=$(jq -r '.allow' <<<"$res"); hitl=$(jq -r '.require_hitl' <<<"$res")
  if [ "$allow" = "true" ]; then dec=ALLOW; elif [ "$hitl" = "true" ]; then dec=HITL; else dec=DENY; fi
  case "$exp" in ALLOW_IF_TOKEN_VALID) m=REVIEW;; *) [ "$dec" = "$exp" ] && m=OK || m=MISMATCH;; esac
  echo "$id,$label,$exp,$allow,$hitl,$dec,$m" >> "$OUT"
done < "$CASES"
echo "Wrote $OUT"; grep -c MISMATCH "$OUT" | xargs echo "Mismatches:"
