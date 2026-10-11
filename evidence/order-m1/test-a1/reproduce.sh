#!/usr/bin/env bash
# Synthetic M1 Test evidence. Run in a disposable checkout; never deploy these files.
set -euo pipefail
repo=${1:?fixed application-manifest checkout}; base=${2:?fixed base checkout}; evidence=${3:?evidence directory}
export GOTOOLCHAIN=local
cd "$repo"
test "$(git rev-parse HEAD)" = e0f79a61643d31a29de73ffc54bb6a31c320f0df
test "$(git -C "$base" rev-parse HEAD)" = bc6adaedcd645a4663c23284b977a3dd36c0796d
# Go 1.27.1 and Helm 4.2.4; fixed container digests are in .github/workflows/ci.yml.
# Provision writable GOCACHE/GOPATH and normal HTTPS trust/proxy routing for scanner containers.
bash ci/github/test.sh
sh ci/validate.sh
(cd tools/checksum && ../../.build/checksum-test -test.v)
for suite in ci/*_test.py; do
 case "$suite" in ci/namespace_boundary_test.py|ci/order_inventory_test.py) continue;; esac
 python3 "$suite" -v
done
SECURITY_RENDER_REQUIRED=true bash ci/github/source-scan.sh
# Expected nonzero: the independent adversarial expectations expose four gaps/limits.
python3 "$evidence/independent.py" "$repo" "$base" "$evidence"
