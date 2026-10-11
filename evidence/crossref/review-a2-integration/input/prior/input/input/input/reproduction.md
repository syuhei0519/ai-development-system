# Independent Test attempt 1 — reproduction

Target: `syuhei0519/ai-development-system` at
`4b4e9c249451881f1e5eef82efb3a3b111cacbdb`.
Original base: `5345303db8c5208859ed741b98f119882de7a973`.
Initial Delivery 1.0 consumer: `df400018057735b7cb6a9c6ea4619508f0e6ba3a`.

Use isolated System checkouts. Do not execute fetched application source.
No production files need modification. Python and dependencies from the fixed
`requirements-dev.txt` are required.

```sh
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
python PATH_TO_CANDIDATE/independent_probe.py HEAD_CHECKOUT RESULTS_JSON LEGACY10_CHECKOUT LEGACY11_CHECKOUT
```

Expected: 173 existing tests pass; 245 independent checks pass. Four deliberate
CLI failure probes print the generic rejection message while the harness verifies
exit 1, absent output directory and absent consumption receipt. These messages
are expected negative-test observations. `independent-results.json` records every
case and expected/actual result. The harness imports only production modules,
builds separate synthetic documents, and repins adversarial outer records.
Its local synthetic Git transport substitution never changes the production CLI.

For the real B1 delivery, first obtain a **new**, separately delivered Manager
authorization and independent pin for the exact consumer, scope, purpose and
record hashes. Prior authorization and receipts are not reusable grants.
Use immutable `input/b1-manifest.json` and `input/b1-publication-receipt.json`:

```sh
python scripts/consume_delivery.py \
  --manifest PATH_TO_CANDIDATE/input/b1-manifest.json \
  --publication PATH_TO_CANDIDATE/input/b1-publication-receipt.json \
  --authorization PRIVATE_AUTHORIZATION \
  --authorization-sha256 MANAGER_INDEPENDENT_PIN \
  --consumer APPROVED_CONSUMER \
  --scope system/artifact-delivery/cross-reference \
  --purpose contract-review --output NEW_PRIVATE_OUTPUT
```

Run again with a different new private output path and
`--verify-receipt FIRST_OUTPUT/consumption-receipt.json`. Recheck fetches current
fixed Git bytes; it does not inspect mutations in an old output directory.
The independently observed result was 17 unique objects / 89071 raw bytes,
including the Research retry dependencies, one raw commit object, one candidate
blob source and all six tree-source files. Both outputs were byte-identical.
Full receipts and both Manager authorization records remain private.
`delivery-observation.json` is a separate edited observation, **not** a receipt.

The initial 33-file outer bundle was consumed using the unchanged 1.0 consumer
before any report or dependency was used. Transport of nested 1.2 record JSON by
the 1.0 CLI is not evidence of B1 1.2 success. The successful real B1 runs above
are separate observations.

The 27 files under `input/` are the exact transitive artifact/upstream closure of
the public Implementation Handoff. No dependency locator was rewritten in them.
Their own prior status, attempt, claims and pending wording remain historical.
The Test Handoff is new, role=test, attempt=1. Original Issue/X-1–X-6 text is
unchanged; X-7–X-9 remain additional completion criteria with adoption evidence.

After the original-base tests, new main
`b1e606544174481b7b6904f811e857f80978c287` was independently fetched. It has the
same tree as the original base, which is its second parent. PR #7 test-merge
`fe410be606c9b22bd466c78b10728fff3e4723b6` has parents new main and fixed head,
and the same tree as fixed head. The PR CI job log independently confirms that
checkout SHA and 173 tests. This later applicability observation does not rewrite
the base of the original independent tests. CI remains separate from Test.

The candidate is local and unpublished. Manager must review safety and authorize
any publication or downstream use. No Review, merge readiness, B1 product AC,
Knowledge adoption, application execution or IssueCompletion is certified here.
