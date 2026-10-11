#!/usr/bin/env bash
# Verification commands. No publish, PR, cluster or kind operations.
# Obtain and canonical-verify the fixed incoming bundle before using OLD_TEST.
set -euo pipefail
: "${BACKEND_CHECKOUT:?fresh fixed checkout required}"
: "${M0_CHECKOUT:?fresh fixed checkout required}"
: "${OLD_TEST:?canonical-consumed test-a1 artifact directory required}"
: "${PRIVATE_OUTPUT:?fresh private output directory required}"
test "$(git -C "$BACKEND_CHECKOUT" rev-parse HEAD)" = 65885af3fd648ce7010fa4a06470b273b995d418
test "$(git -C "$BACKEND_CHECKOUT" rev-parse HEAD^{tree})" = a041558ad61f96dfbae616bcd3e91ab5f6b4a3a3
test "$(git -C "$M0_CHECKOUT" rev-parse HEAD)" = bc6adaedcd645a4663c23284b977a3dd36c0796d
mkdir -m 700 -p "$PRIVATE_OUTPUT"
cd "$BACKEND_CHECKOUT"
go version # Measured version: go1.27.1 linux/amd64.
go mod verify
go test -json -count=1 ./... > "$PRIVATE_OUTPUT/unit.jsonl"
go vet ./...
go build ./...
ORDER_DISPOSABLE_TEST=1 go test -race -json -count=1 ./... > "$PRIVATE_OUTPUT/race.jsonl"
bash ci/github/test.sh > "$PRIVATE_OUTPUT/ci-suite.log" 2>&1
for module in tools/*/go.mod; do
 (cd "${module%/go.mod}"; go vet ./...; go test -race -count=1 ./...; go build ./...)
done
test -z "$(gofmt -l .)"
git diff --check 2d3b2feff46ddd8d7091e6b4b5e95355c9bf34d0 HEAD
python3 "$OLD_TEST/independent-negative.py" "$BACKEND_CHECKOUT" "$M0_CHECKOUT"
python3 -I "$M0_CHECKOUT/ci/github/release_test.py"
(cd tools/oci-input
 go build -o "$PRIVATE_OUTPUT/oci-runtime-export" ./cmd/oci-runtime-export
 go run "$OLD_TEST/transport-synthetic.go" "$PRIVATE_OUTPUT/oci-runtime-export")
# Image commands are separate because they require the explicitly authorized
# temporary BuildKit boundary and produce private operational logs:
# python3 reproduce-build.py NEW_PRIVATE_DIR CLEAN_FIXED_BACKEND application
# Copy synthetic-Dockerfile to a new scratch context as Dockerfile, then:
# python3 reproduce-build.py NEW_PRIVATE_PROBE_DIR SYNTHETIC_CONTEXT synthetic
# python3 check-oci-descriptors.py NEW_PRIVATE_PROBE_DIR/synthetic.oci.tar
# Do not replace the production Dockerfiles with the synthetic one.
