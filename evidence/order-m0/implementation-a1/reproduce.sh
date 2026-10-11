#!/usr/bin/env bash
set -euo pipefail
# Run in an authorized application-manifest checkout with fixed base available.
# Recover commit from implementation.bundle first; never apply to main.
test "$(git rev-parse HEAD)" = 2d45e35a2aaeee7eacb9a121d92b34a7f291ea76
bash ci/github/test.sh
for test in ci/trusted_binary_test.py ci/trusted_consumer_failure_test.py ci/trusted_phase2_test.py; do python3 "$test" -v; done
sh ci/validate.sh
(cd tools/checksum && go test ./...)
(cd tools/inventory && go run . < ../../.rendered/all.yaml)
.security/scan-gate -check-render-only .rendered -out .security/public/order-m0-render.json
python3 -I ci/trusted-render.py --repo . --target e039945a90625262f91382e6f71149d046e31b34 --source 2d45e35a2aaeee7eacb9a121d92b34a7f291ea76 --verifier 2d45e35a2aaeee7eacb9a121d92b34a7f291ea76 --producer-job-id 0 --output .trusted/order-m0.json --test-only
git diff --exit-code e039945a90625262f91382e6f71149d046e31b34 HEAD -- charts environments .github
