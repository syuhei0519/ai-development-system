#!/usr/bin/env bash
# Self-verification only. Requires prepared Go 1.27.1, Helm 4.2.4 and Docker.
# Invoke with fixed application-manifest checkout and a fresh output directory.
set -euo pipefail
repo=$(cd "$1" && pwd)
out=$2
mkdir -p "$out"
out=$(cd "$out" && pwd)
evidence=$(cd "$(dirname "$0")" && pwd)
cd "$repo"
test "$(git rev-parse HEAD)" = 82505fce911c1dbbe75fe8226a06665e582e1ff9
bash ci/github/test.sh
python3 ci/trusted_binary_test.py
python3 ci/trusted_consumer_failure_test.py
python3 ci/trusted_phase2_test.py
sh ci/validate.sh
(cd tools/checksum && go test ./...)
(cd tools/inventory && go build -o ../../.security/inventory .)
python3 "$evidence/reproduce.py" "$repo" "$out/probes.json"
python3 "$evidence/reproduce-render.py" "$repo" "$out/render-fixtures"
python3 "$evidence/compare-renders.py" "$repo" "$out/render-comparison.json"
python3 -I ci/trusted-render.py --repo "$repo" --target e039945a90625262f91382e6f71149d046e31b34 --source 82505fce911c1dbbe75fe8226a06665e582e1ff9 --verifier 82505fce911c1dbbe75fe8226a06665e582e1ff9 --producer-job-id 0 --test-only --output "$out/trusted-render.json"
