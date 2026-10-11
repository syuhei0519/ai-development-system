# System capacity Implementation a1 delivery

Payload commit: `750b3771009488834e2bc2aca91c64923af158fd`.
Implementation head: `4e38376404d9486daae93829735f11166a01e062`.
Draft PR: https://github.com/syuhei0519/ai-development-system/pull/9
Canonical transport validator: `4693887fa79c2b4a291c555b8bd27b6903eb4199`.

This manifest is Delivery 1.2: 12 explicit artifacts, 11 structural slots,
200381 payload bytes. It includes Handoff 2.0, report, full patch, test/CI/blocker
observations, candidate-profile, four candidate schema byte copies and the raw
implementation commit. The candidate schema copies are generic JSON data for
review; they never replace the known transport validator or its schema files.

- manifest SHA-256: `abf93cf8c6aa1d1312955817f03e4426d0566cb152e2de7ba223a1688266d536`
- publication receipt SHA-256: `e27bb916b290eb998e643de8ad2e70bea202a747ddbf92299436ef4f52bec5ab`

Acquire these exact records from the fixed records commit reported by the producer.
Manager must verify their pins through the authorized handoff and supply separate
current authorization (consumer, system-artifact-capacity scope, purpose, expiry,
representations and both record pins). Public availability and receipts do not
authorize downstream use. Keep authorization bytes and the authorization pin private.

With the known canonical checkout and independently pinned authorization:

```sh
python scripts/consume_delivery.py --manifest manifest.json \
  --publication publication-receipt.json --authorization PRIVATE_AUTHORIZATION.json \
  --authorization-sha256 MANAGER_INDEPENDENT_PIN \
  --consumer APPROVED_PUBLIC_ALIAS --scope system-artifact-capacity \
  --purpose contract-review --output NEW_PRIVATE_DIRECTORY
```

For a receipt recheck, use `--verify-receipt PRIVATE_PREVIOUS_RECEIPT.json` and a
second new output directory. It re-fetches Git bytes and does not inspect an old
output. Preserve original records, payload bytes and existing delivery outputs.
Producer's postpush result is reported separately without private authorization
material. Its self-verification is not independent Test/Review, Manager acceptance,
merge permission or a reset of dispatch/execution/delivery (each remains 3).
