#!/usr/bin/env bash
# Independent Review reproduction. No application edits, registry/API writes or deployment.
set -euo pipefail
: "${BACKEND_CHECKOUT:?exact PR32 source}"
: "${M0_CHECKOUT:?fixed bc6adaed checkout}"
: "${M1_CHECKOUT:?fixed df8c8b5d checkout}"
: "${CONSUMED:?fresh canonical-consumed input bundle directory}"
: "${PRIVATE_OUTPUT:?new private writable directory}"
: "${REVIEW_OUTPUT:?directory containing adversarial.py}"
up="$CONSUMED/artifacts/syuhei0519/ai-development-system"
test2="$up/61571179b9ae25747244c889b34758a177d3c3e1/evidence/order-b2/test-e2-a2/reproduce.py"
impl2="$up/437cb5b76359a8743613529aa33f7a9dacb88e9c/evidence/order-b2/implementation-a2"
negative="$up/aa8e6e7622f015c74db9920b14d8a9be4f8b11a5/evidence/order-b2/test-a1/independent-negative.py"
mkdir -m 700 -p "$PRIVATE_OUTPUT"
cd "$BACKEND_CHECKOUT"
test "$(git rev-parse HEAD)" = dab0123f4fd459e12c1f64ff2305e5d28d8a41f5
test "$(git rev-parse HEAD^{tree})" = 8af1119fde6742666c4e4e43cec1aab15ab36ea7
PRIVATE_OUTPUT="$PRIVATE_OUTPUT/suites" bash "$impl2/reproduce.sh"
mkdir "$PRIVATE_OUTPUT/context" "$PRIVATE_OUTPUT/bin"
git archive HEAD | tar -x -C "$PRIVATE_OUTPUT/context"
(cd tools/oci-input; for name in github-oci-check oci-crane-check oci-runtime-export; do CGO_ENABLED=0 go build -o "$PRIVATE_OUTPUT/bin/$name" "./cmd/$name"; done)
(cd tools/scan-gate; CGO_ENABLED=0 go build -o "$PRIVATE_OUTPUT/bin/scan-gate" .)
(cd tools/release-record; CGO_ENABLED=0 go build -o "$PRIVATE_OUTPUT/bin/sbom-check" ./cmd/sbom-check)
# Only with the independently authorized bounded rootless-worker exception.
# Existing proxy/CA inputs remain private. A fresh worker is created per mode.
for mode in valid missing empty invalid nonexistent; do
 python "$test2" build "$PRIVATE_OUTPUT/$mode" "$PRIVATE_OUTPUT/context" "$mode"
done
ln -s "$M0_CHECKOUT" "$PRIVATE_OUTPUT/m0"
ln -s "$M1_CHECKOUT" "$PRIVATE_OUTPUT/m1"
python "$test2" source "$PRIVATE_OUTPUT"
for service in backend order; do
 python "$test2" chain "$service"
 python "$impl2/check-image.py" "$PRIVATE_OUTPUT/valid/$service.oci.tar" "$service" dab0123f4fd459e12c1f64ff2305e5d28d8a41f5
 python "$test2" image "$PRIVATE_OUTPUT" "$service"
 python "$test2" leak "$PRIVATE_OUTPUT" "$service"
 python "$test2" publish "$PRIVATE_OUTPUT" "$service" # mocks registry/API; real local validators
 done
python "$test2" matrix "$PRIVATE_OUTPUT"
python "$test2" consumer "$BACKEND_CHECKOUT" "$M0_CHECKOUT" "$M1_CHECKOUT"
for consumer in "$M0_CHECKOUT" "$M1_CHECKOUT"; do
 python "$negative" "$BACKEND_CHECKOUT" "$consumer"
 python "$consumer/ci/github/release_test.py"
done
python "$REVIEW_OUTPUT/adversarial.py" "$BACKEND_CHECKOUT"
# Expected on reviewed head: mixed scan accepted. This is a blocking review finding,
# not a passing security regression. Actual network operations remain mocked.
python "$REVIEW_OUTPUT/adversarial.py" "$BACKEND_CHECKOUT" --scan-swap "$PRIVATE_OUTPUT"
