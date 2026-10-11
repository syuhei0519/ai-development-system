#!/usr/bin/env bash
# Self-verification commands. No external publish, dispatch, cluster or merge.
set -euo pipefail
: "${BACKEND_CHECKOUT:?fresh fixed source required}"
: "${PRIVATE_OUTPUT:?private output required}"
cd "$BACKEND_CHECKOUT"
test "$(git rev-parse HEAD)" = dab0123f4fd459e12c1f64ff2305e5d28d8a41f5
test "$(git rev-parse HEAD^{tree})" = 8af1119fde6742666c4e4e43cec1aab15ab36ea7
mkdir -m 700 -p "$PRIVATE_OUTPUT"
go version
go mod verify
go test -json -count=1 ./... > "$PRIVATE_OUTPUT/unit.jsonl"
go vet ./...
go build ./...
ORDER_DISPOSABLE_TEST=1 go test -race -json -count=1 ./... > "$PRIVATE_OUTPUT/race.jsonl"
bash ci/github/test.sh
for module in tools/*/go.mod; do
 (cd "${module%/go.mod}"; go vet ./...; go test -race -count=1 ./...; go build ./...)
done
test -z "$(gofmt -l .)"
git diff --check 2d3b2feff46ddd8d7091e6b4b5e95355c9bf34d0 HEAD
# Use a separate pristine git archive context for Docker builds: Go's build
# command may leave executable outputs in a test checkout. Never export these.
mkdir "$PRIVATE_OUTPUT/context"
git archive HEAD | tar -x -C "$PRIVATE_OUTPUT/context"
# After reviewing the explicit two-option temporary rootless authorization:
# python reproduce-build.py "$PRIVATE_OUTPUT/valid" "$PRIVATE_OUTPUT/context" valid
# python reproduce-build.py "$PRIVATE_OUTPUT/missing" "$PRIVATE_OUTPUT/context" missing
# python reproduce-build.py "$PRIVATE_OUTPUT/invalid" "$PRIVATE_OUTPUT/context" invalid
# python check-image.py "$PRIVATE_OUTPUT/valid/backend.oci.tar" backend "$(git rev-parse HEAD)"
# python check-image.py "$PRIVATE_OUTPUT/valid/order.oci.tar" order "$(git rev-parse HEAD)"
# Build the exact validators under PRIVATE_OUTPUT/bin:
# tools/oci-input: github-oci-check, oci-crane-check, oci-runtime-export
# tools/release-record: sbom-check; tools/scan-gate: scan-gate (CGO_ENABLED=0)
# python verify-chain.py backend
# python verify-chain.py order
# Each verifier reads the exported original tar, never rebuilds an image.
# Fixed upstream independent-negative.py/transport-synthetic.go can be rerun
# as self-verification after their separate canonical input delivery succeeds.
