#!/usr/bin/env bash
# Independent Test3 reproduction; synthetic fixtures only, no deployment.
# args: fixed application checkout, canonical verified input directory, new output directory
set -euo pipefail
repo=$(realpath "$1")
verified=$(realpath "$2")
out=$(realpath -m "$3")
here=$(dirname "$(realpath "$0")")
test "$(git -C "$repo" rev-parse HEAD)" = e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4
mkdir -p "$out"
impl="$verified/artifacts/syuhei0519/ai-development-system/b231aa38653333bd86f293a13458f4bf955970f3/evidence/order-m0/implementation-e2-a1"
prior="$verified/artifacts/syuhei0519/ai-development-system/9977949f20d2d1f129d28a152c7a6dc056914228/evidence/order-m0/test-a2"
cd "$repo"
bash ci/github/test.sh
python3 ci/trusted_binary_test.py
python3 ci/trusted_consumer_failure_test.py
python3 ci/trusted_phase2_test.py
sh ci/validate.sh
(cd tools/checksum && go test ./...)
(cd tools/inventory && go build -o ../../.security/inventory .)
.security/scan-gate -check-render-only .rendered -out "$out/live-scan.json"
python3 "$impl/reproduce.py" "$repo" "$out/f1.json"
python3 "$prior/security-boundaries.py" "$repo" "$out/security.json"
python3 "$impl/f2-trusted.py" "$repo" "$out/f2"
python3 "$impl/reproduce-render.py" "$repo" "$out/render-fixtures"
python3 "$impl/fixed-render-comparison.py" "$repo" "$out/render-comparison.json"
python3 "$here/independent-probes.py" "$repo" "$out/independent-probes.json"
python3 -I ci/trusted-render.py --repo "$repo" --target e039945a90625262f91382e6f71149d046e31b34 --source e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4 --verifier e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4 --producer-job-id 0 --test-only --output "$out/baseline-render.json"
