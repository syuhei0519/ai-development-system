#!/usr/bin/env bash
# Synthetic-only independent M0 tests; operate in an isolated fixed checkout.
# Caller supplies checkout, prepared Go/Helm/Docker, and output directory.
set -u
here=$(dirname "$(realpath "$0")")
repo=$(realpath "$1")
out=$(realpath -m "$2")
mkdir -p "$out"
cd "$repo"
test "$(git rev-parse HEAD)" = 2d45e35a2aaeee7eacb9a121d92b34a7f291ea76 || exit 2
bash ci/github/test.sh || exit 2
python3 ci/trusted_binary_test.py || exit 2
python3 ci/trusted_consumer_failure_test.py || exit 2
python3 ci/trusted_phase2_test.py || exit 2
sh ci/validate.sh || exit 2
(cd tools/checksum && go test ./...) || exit 2
(cd tools/inventory && go build -o ../../.security/inventory .) || exit 2
.security/scan-gate -check-render-only .rendered -out "$out/live-render-scan.json" || exit 2
python3 "$here/reproduce.py" "$repo" "$out/independent-results.json"
a=$?
python3 "$here/reproduce-render.py" "$repo" "$out/render-fixtures"
b=$?
# Fixed head currently fails expected rejection of container security overrides.
test "$a" -eq 0 && test "$b" -eq 0
