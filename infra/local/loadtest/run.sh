#!/usr/bin/env bash
# Drives load through the ingress with k6 while recording both HPAs every 5 s.
# Output: results/<LABEL>/{k6-summary.json,k6-stdout.txt,hpa-timeline.csv}, then a printed summary.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
LABEL=${LABEL:-load}
RATE=${RATE:-40}                     # requests per second
DURATION_S=${DURATION_S:-240}        # how long to apply load
COOLDOWN_S=${COOLDOWN_S:-180}        # keep recording after load stops, to see scale-down
SETTLE_TIMEOUT_S=${SETTLE_TIMEOUT_S:-600}
KCTX=${KCTX:-kind-eks-ms}
NAMESPACE=${NAMESPACE:-microservices}
RELEASE=${RELEASE:-microservices}
BASE_URL=${BASE_URL:-http://localhost:8080}
K6_IMAGE=grafana/k6:2.3.0@sha256:2dd4756ec6e14e62778916e1eb850108e4b499304c02df56760fa0bdb0fba0b8

OUT="$HERE/results/$LABEL"
mkdir -p "$OUT"
KUBECTL=(kubectl --context "$KCTX" -n "$NAMESPACE")

curl -fsS -o /dev/null "$BASE_URL/compute?n=1" || { echo "api not reachable at $BASE_URL (run: make deploy)"; exit 1; }

# A clean measurement starts from min replicas on both HPAs.
echo "waiting for HPAs to settle at minReplicas (timeout ${SETTLE_TIMEOUT_S}s)..."
deadline=$(( $(date +%s) + SETTLE_TIMEOUT_S ))
until "${KUBECTL[@]}" get hpa -o json | python3 -c '
import json, sys
bad = [h for h in json.load(sys.stdin)["items"]
       if h["status"].get("currentReplicas") != h["spec"]["minReplicas"]
       or h["status"].get("desiredReplicas") != h["spec"]["minReplicas"]]
sys.exit(1 if bad else 0)'; do
  [ "$(date +%s)" -lt "$deadline" ] || { echo "HPAs did not settle; not measuring from a dirty state"; exit 1; }
  sleep 10
done

record_hpa() {
  local start end
  start=$(date +%s); end=$(( start + DURATION_S + COOLDOWN_S ))
  echo "t_s,api_current,api_desired,api_cpu_pct,worker_current,worker_desired,worker_cpu_pct" > "$OUT/hpa-timeline.csv"
  while [ "$(date +%s)" -lt "$end" ]; do
    "${KUBECTL[@]}" get hpa -o json | python3 -c '
import json, sys
t, rel = sys.argv[1], sys.argv[2]
by = {h["metadata"]["name"]: h["status"] for h in json.load(sys.stdin)["items"]}
def cols(svc):
    s = by.get(f"{rel}-{svc}", {})
    m = s.get("currentMetrics") or [{}]
    cpu = m[0].get("resource", {}).get("current", {}).get("averageUtilization", "")
    return [s.get("currentReplicas", ""), s.get("desiredReplicas", ""), cpu]
print(",".join(str(x) for x in [t] + cols("api") + cols("worker")))' \
      "$(( $(date +%s) - start ))" "$RELEASE" >> "$OUT/hpa-timeline.csv" || true
    sleep 5
  done
}

echo "load: ${RATE} req/s for ${DURATION_S}s, then recording ${COOLDOWN_S}s more (label=$LABEL)"
record_hpa &
RECORDER=$!

K6_EXIT=0
docker run --rm --network host -u "$(id -u):$(id -g)" \
  -e BASE_URL="$BASE_URL" -e RATE="$RATE" -e DURATION="${DURATION_S}s" \
  -v "$HERE/k6.js":/scripts/k6.js:ro -v "$OUT":/results \
  "$K6_IMAGE" run --quiet --summary-export=/results/k6-summary.json \
  --summary-trend-stats="avg,med,p(90),p(95),p(99),max" /scripts/k6.js \
  2>&1 | tee "$OUT/k6-stdout.txt" || K6_EXIT=$?

wait "$RECORDER"
python3 "$HERE/summarize.py" "$OUT" "$DURATION_S"
exit "$K6_EXIT"
