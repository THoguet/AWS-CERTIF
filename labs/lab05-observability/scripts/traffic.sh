#!/usr/bin/env bash
# Send a mix of checkout requests to the lab05 API: several tiers, varied latencies, a few failures.
# Usage: bash scripts/traffic.sh "$API" [count]
set -euo pipefail
API="${1:?usage: traffic.sh API_URL [count]}"
COUNT="${2:-60}"
tiers=(gold silver free free free)

for i in $(seq 1 "$COUNT"); do
  tier=${tiers[$((RANDOM % ${#tiers[@]}))]}
  delay="0.$((RANDOM % 9))"                       # 0.0 to 0.8 s
  if (( RANDOM % 15 == 0 )); then delay=2.5; fi    # a slow payment now and then
  fail=false
  if (( RANDOM % 10 == 0 )); then fail=true; fi    # about 10% failures
  amount=$(( (RANDOM % 200) + 5 ))
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-Correlation-Id: lab05-$i" \
         "$API/checkout?tier=$tier&amount=$amount&delay=$delay&fail=$fail")
  echo "$i tier=$tier amount=$amount delay=${delay}s fail=$fail -> HTTP $code"
  sleep 0.5
done
