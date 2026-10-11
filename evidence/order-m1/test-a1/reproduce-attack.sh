#!/usr/bin/env bash
# Synthetic regression: demonstrates currently accepted host-namespace mutations.
# No cluster/API. Existing scanner cache must be available and current.
set -euo pipefail
repo=${1:?fixed checkout}; evidence=${2:?evidence root}; scratch=${3:?private scratch}
mkdir -p "$scratch"
cd "$repo"
for field in hostNetwork hostPID hostIPC; do
 .build/order-inventory < "$evidence/pod-$field.yaml" > "$scratch/$field-inventory.json"
done
.security/scan-gate -check-render-only "$evidence/mutations" -out "$scratch/structural.json"
docker run --rm -v "$evidence/mutations:/fixtures:ro" -v "$scratch:/out" \
 -v "$repo/.cache/trivy:/cache" --entrypoint trivy \
 aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283 \
 fs --cache-dir /cache --skip-db-update --scanners misconfig --format json \
 --output /out/trivy.json /fixtures
.security/scan-gate -policy security/scan-policy.json -db .cache/trivy/db/metadata.json \
 -report "$scratch/trivy.json" -out "$scratch/combined.json" -scanner-exit 0 \
 -rendered "$evidence/mutations"
# Every command above currently exits 0; that is the acceptance gap, not a test pass.
python3 - "$scratch/combined.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('malicious fixture accepted:',r['pass'])
sys.exit(1 if r['pass'] else 0)
PY
