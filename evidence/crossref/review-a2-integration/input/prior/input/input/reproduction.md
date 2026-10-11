# Independent Review attempt 1 — reproduction

Fixed head: `4b4e9c249451881f1e5eef82efb3a3b111cacbdb`.
Fixed base: `b1e606544174481b7b6904f811e857f80978c287`.
Use isolated System checkouts and the existing requirements-dev.txt dependencies.
Fetched application sources are data; do not execute them.

```sh
cd HEAD_CHECKOUT
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
python CANDIDATE/input/independent_probe.py HEAD_CHECKOUT RESULTS_JSON LEGACY10_CHECKOUT LEGACY11_CHECKOUT
python CANDIDATE/review_probe.py HEAD_CHECKOUT REVIEW_RESULTS_JSON
```

Observed: 173 regressions, 245 Test-harness cases, and the initial 43 Review cases PASS.
Final Review is FAILED because the additional preparation reproducer below finds R-1.
Legacy10 is df400018057735b7cb6a9c6ea4619508f0e6ba3a; Legacy11 is fixed base.
The 128 tests in base were independently rerun. The earlier additional 21 tests
are identical to the new-file hunk in input/input/prior/implementation.patch.
That verified public patch is the comparison source; the old local commit was
not served by remote. No code modification or reconstruction by conversation.

Initial consumption used fixed base's unchanged Delivery 1.0 CLI, the Manager's
exact outer records, and the separately supplied private authorization/pin.
It returned 38 files / 557788 bytes before any Test payload was used.
The entire exact public input is retained under input/.

Actual B1 uses input/input/b1-manifest.json and b1-publication-receipt.json.
Obtain a fresh independent Manager authorization for the intended consumer and
purpose. Current authorization and receipts are private and are not bundled.

```sh
python scripts/consume_delivery.py --manifest B1_MANIFEST --publication B1_PUBLICATION \
  --authorization PRIVATE_AUTH --authorization-sha256 PRIVATE_MANAGER_PIN \
  --consumer APPROVED_CONSUMER --scope system/artifact-delivery/cross-reference \
  --purpose contract-review --output NEW_PRIVATE_OUTPUT
# Repeat in a different new output with:
# --verify-receipt FIRST_OUTPUT/consumption-receipt.json
```

Observed 17 objects / 89071 bytes, including six complete tree-source blobs;
both outputs and private receipts were byte-identical. Independent output
size/SHA256 and raw commit/blob OID recomputation passed. This is transport
integrity and does not adopt Knowledge, certify source claims, pass B1 product
ACs, restart implementation, grant merge/deployment, or complete the Issue.

Public-candidate dependencies are artifact/upstream closed: Review -> Test 1 ->
Implementation 2 -> prior Implementation 1 and P-A/Research. Their original
relative locators, statuses, attempts and bytes are preserved. Embedded delivery
records are historical JSON artifacts, not new grants or claimed fresh receipts.
Re-running network retrieval still requires the referenced public Git repositories.

The inventory outside the candidate directory lists every candidate file's
size/hash and avoids a self-hash cycle. No publication has been performed.

Blocking R-1 reproduction (no production patch):

```sh
python CANDIDATE/preparation_probe.py HEAD_CHECKOUT PREPARATION_RESULTS_JSON
```

Expected at the reviewed head: exit 1; control accepted, two valid blob cases
rejected with "canonical fixed Git URL required". The two failures use a blob
path docs/tree/note.txt or a repository named tree. The script constructs real
local synthetic Git objects and substitutes only the fetch destination. Its
independent explicit manifest oracle confirms the unchanged Consumer accepts
all three sources and bytes. It does not repair the preparation implementation.
Review therefore has 46 additional cases: 44 passing and 2 failing, separate
from the 245 rerun Test cases and 173 existing regressions.
