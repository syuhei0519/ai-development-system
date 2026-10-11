#!/usr/bin/env bash
# Implementation self-verification; prepared Cloud Go 1.27.1, Helm 4.2.4, Docker.
# Arguments: fixed application checkout, output directory, verified Test2 directory.
# Obtain Test2 via canonical Delivery 1.2 with independent Manager approval first.
set -euo pipefail
here=$(dirname "$(realpath "$0")")
repo=$(realpath "$1")
out=$(realpath -m "$2")
upstream=$(realpath "$3")
mkdir -p "$out"
cd "$repo"
test "$(git rev-parse HEAD)" = e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4
bash ci/github/test.sh
python3 ci/trusted_binary_test.py
python3 ci/trusted_consumer_failure_test.py
python3 ci/trusted_phase2_test.py
sh ci/validate.sh
(cd tools/checksum && go test ./...)
(cd tools/inventory && go build -o ../../.security/inventory .)
.security/scan-gate -check-render-only .rendered -out "$out/live-scan.json"
python3 "$here/reproduce.py" "$repo" "$out/after-f1.json"
python3 "$upstream/security-boundaries.py" "$repo" "$out/after-security.json"
python3 "$here/f2-trusted.py" "$repo" "$out/f2-render"
python3 "$here/reproduce-render.py" "$repo" "$out/render-fixtures"
python3 "$here/fixed-render-comparison.py" "$repo" "$out/render-comparison.json"
