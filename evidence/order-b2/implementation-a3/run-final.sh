# Reviewed public edited derivative of completed Implementation self-verification; delivery-only preparation, no new measurement. Private originals retained; no private-original equivalence certification.
set -euo pipefail
: "${BACKEND_CHECKOUT:?fixed backend checkout required}"
: "${REPRO_ROOT:?private reproduction root required}"
: "${PRIVATE_OUTPUT:?private final measurement directory required}"
r="$REPRO_ROOT"
scripts="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for service in backend order; do
 python3 "$r/consumed-review/artifacts/syuhei0519/ai-development-system/437cb5b76359a8743613529aa33f7a9dacb88e9c/evidence/order-b2/implementation-a2/check-image.py" "$PRIVATE_OUTPUT/valid/$service.oci.tar" "$service" 24083aba485abd6b37bcbe71736fb543a847dcc6 > "$PRIVATE_OUTPUT/$service-independent-oci.json"
 python3 "$scripts/measure-final.py" chain "$service"
 python3 "$scripts/measure-final.py" image "$PRIVATE_OUTPUT" "$service"
 python3 "$scripts/measure-final.py" leak "$PRIVATE_OUTPUT" "$service"
 python3 "$scripts/measure-final.py" publish "$PRIVATE_OUTPUT" "$service"
done
python3 "$scripts/measure-final.py" matrix "$PRIVATE_OUTPUT"
python3 "$scripts/probe-final.py"
