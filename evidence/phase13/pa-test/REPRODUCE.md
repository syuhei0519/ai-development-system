# Independent P-A Test reproduction

Public alias: knowledge-delivery-test-a1. Scope: system/phase1-3/P-A. Attempt: 1.
This package is a local publication candidate, not permission to publish or merge.

## Fixed dependencies

Repository: https://github.com/syuhei0519/ai-development-system
Head: 5345303db8c5208859ed741b98f119882de7a973
Base: df400018057735b7cb6a9c6ea4619508f0e6ba3a
Use detached fresh read-only checkouts; confirm both commits with git rev-parse HEAD.
Python 3.12 and jsonschema==4.26.0 are required; dependencies are specified by the fixed head's requirements-dev.txt.
Reproducers import only the supplied fixed checkout's scripts, not another Test task's files.
Product code must remain unchanged. All generated output belongs in new scratch directories.

In the commands below HEAD_DIR, BASE_DIR, EVIDENCE_DIR and TEST_DATA_DIR are operator-chosen local directories, not embedded environment paths.

```sh
cd "$HEAD_DIR"
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
cd "$BASE_DIR"
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q
python "$EVIDENCE_DIR/independent_cases.py" "$HEAD_DIR" independent-results-new.json
python "$EVIDENCE_DIR/verify_checkout.py" "$HEAD_DIR" "$BASE_DIR" checkout-results-new.json
```

Expected: head 128 methods, base 107 methods, independent 111/111, checkout 45/45.
Each independent result records expected/actual/detail and its case ID. Select the corresponding case() call in independent_cases.py for the mutation. The script regenerates all cases in one run; it does not accept a case-filter argument. In-memory rejection cases reseal outer pins to exercise semantic checks. inspect the result file's passed values; runner exit alone is not a pass assertion.
Some paired-document locator mutations fail first at input/output equality. The standalone-context variants reach path/dependency checks. Existing repository tests separately exercise synthetic Git symlink/gitlink modes and retry bindings.

## Fresh HTTPS Git and CLI probes

The fixed-head examples/knowledge-delivery/README.md is the source procedure.

```sh
python "$HEAD_DIR/scripts/prepare_knowledge_fixture.py" \
  --repository syuhei0519/ai-development-system \
  --commit 5345303db8c5208859ed741b98f119882de7a973 \
  --output "$TEST_DATA_DIR/fixture-prepared"
```

Manager must supply a current, independently authorized fixture-authorization.json in TEST_DATA_DIR, using the fixed-head authorization.template.json fields. Version is 1.1; consumer knowledge-delivery-test-a1; scope system/phase1-3/P-A; purpose contract-review; representation original. Pin the freshly prepared manifest and publication-receipt raw digests and the authorization's raw SHA-256 by a trusted channel. Do not reuse this package's receipt as authority. Private authorization bytes and trusted pin delivery remain outside the public package.

```sh
python "$HEAD_DIR/scripts/consume_delivery.py" \
  --manifest "$TEST_DATA_DIR/fixture-prepared/manifest.json" \
  --publication "$TEST_DATA_DIR/fixture-prepared/publication-receipt.json" \
  --authorization "$TEST_DATA_DIR/fixture-authorization.json" \
  --authorization-sha256 "$TRUSTED_AUTHORIZATION_SHA256" \
  --consumer knowledge-delivery-test-a1 --scope system/phase1-3/P-A \
  --purpose contract-review --output "$TEST_DATA_DIR/fixture-consumed"
```

Repeat the same command with a new output directory and --verify-receipt "$TEST_DATA_DIR/fixture-consumed/consumption-receipt.json". Expected: both exit 0, six original fixture files, authority_granted=false. Actual original consumption and separate recheck receipts were byte-identical; only one copy is retained here. New operator authorization produces a different authorization digest, so a future receipt need not equal this historical receipt.

```sh
python "$EVIDENCE_DIR/cli_probes.py" "$HEAD_DIR" "$TEST_DATA_DIR" cli-results-new.json
```

Expected: 6/6. Required inputs are fixture-prepared/{manifest.json,publication-receipt.json}, fixture-authorization.json and fixture-consumed/{consumption-receipt.json,artifacts/...}. They are produced above, not assumed to exist in another workspace. The probe checks consumer/purpose/pin failures, receipt false versus numeric zero, local symlink rejection, and fresh fetching despite corruption of a previous local output. It restores the old synthetic article afterward. It does not publish or write product code.

## Artifact closure and provenance

handoff.json binds all eleven Test artifacts by raw SHA-256 and binds upstream/handoff.json. That Implementation Handoff binds three artifacts and upstream/research/handoff.json; the Research Handoff binds four artifacts. Thus all nine upstream files are required by the current P-A relative-path profile. They are unchanged approved public bytes, not copies of private original inputs. test-report.json records their original fixed references and digests.

A URL-only upstream would pass some standalone shape checks but fail P-A delivery. Do not delete upstream, change status/attempt/assignment, or relabel missing dependencies to reduce this closure. Removing these nine snapshots requires a separately approved versioned cross-reference extension. The original sources remain pinned; no mutable main URL or undocumented private source is required.

No private original, authorization file, raw execution log, archive, runtime task identifier or conversation link is part of this package. Public aliases, public GitHub CI run IDs and non-secret receipt authorization digests are provenance, not credentials or grants. Review, current merge gates, B1 and P-B/C/D remain outside this result.
