#!/usr/bin/env bash
# Synthetic sample and fixed-head verification. No publish, PR, cluster or kind.
set -euo pipefail
: "${BACKEND_CHECKOUT:?fresh fixed backend checkout required}"
: "${M0_CHECKOUT:?fresh fixed M0 checkout required}"
: "${TEST_ARTIFACTS:?directory containing this delivery required}"
test "$(git -C "$BACKEND_CHECKOUT" rev-parse HEAD)" = 65885af3fd648ce7010fa4a06470b273b995d418
test "$(git -C "$M0_CHECKOUT" rev-parse HEAD)" = bc6adaedcd645a4663c23284b977a3dd36c0796d
cd "$BACKEND_CHECKOUT"
go version # Expected Go1.27.1; activate the authorized environment first.
go mod verify
go test -count=1 ./...
go vet ./...
go build ./...
bash ci/github/test.sh
# Requires pinned PostgreSQL already present; creates only fresh disposable DBs.
ORDER_DISPOSABLE_TEST=1 go test -race -count=1 ./...
for module in tools/*/go.mod; do
 (cd "${module%/go.mod}"; go vet ./...; go test -race -count=1 ./...; go build ./...)
done
python3 "$TEST_ARTIFACTS/independent-negative.py" "$BACKEND_CHECKOUT" "$M0_CHECKOUT"
(cd "$M0_CHECKOUT"; python3 -I ci/github/release_test.py)
bin=$(mktemp -d)
trap 'rm -rf "$bin"' EXIT
(cd tools/oci-input; go build -o "$bin/oci-runtime-export" ./cmd/oci-runtime-export; go run "$TEST_ARTIFACTS/transport-synthetic.go" "$bin/oci-runtime-export")
# Required production OCI validation remains blocked in the measured environment.
# Use unchanged ci/github/oci.sh for each service in separate fresh workspaces,
# with fixed GitHub identity, compiled validators and a fresh source scan/binding.
# Do not invoke release.py publish against GHCR; use mocked tests only.
