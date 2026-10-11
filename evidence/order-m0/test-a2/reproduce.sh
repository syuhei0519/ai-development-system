#!/usr/bin/env bash
# Independent M0 Test2; fixed checkout, prepared Go/Helm/Docker and output directory.
# No deployment. Expected current result: failure on F-2, retaining all results.
set -u
here=$(dirname "$(realpath "$0")")
repo=$(realpath "$1")
out=$(realpath -m "$2")
mkdir -p "$out"
cd "$repo"
test "$(git rev-parse HEAD)" = 82505fce911c1dbbe75fe8226a06665e582e1ff9 || exit 2
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
python3 "$here/security-boundaries.py" "$repo" "$out/security-boundaries.json"
b=$?
python3 "$here/reproduce-render.py" "$repo" "$out/render-fixtures"
c=$?
python3 "$here/f2-trusted.py" "$repo" "$out/f2-render"
d=$?
python3 "$here/fixed-render-comparison.py" "$repo" "$out/render-comparison.json"
e=$?
test "$a" -eq 0 && test "$b" -eq 0 && test "$c" -eq 0 && test "$d" -eq 0 && test "$e" -eq 0
