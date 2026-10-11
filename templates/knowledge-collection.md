# Manager Knowledge collection input (P-B)

Use a Manager-owned private POSIX directory; never commit state, grants, runtime IDs or logs.
Collector performs no semantic curation or Agent launch. Acquire fresh authorization for each
mutation; the following are placeholders, not approval.

1. Read fixed registry JSON and every selected public source's approval. Supply registry raw bytes
   as the scan/reconcile request. Current authorization fields: schema_version=1.0,
   document_type=knowledge_collection_authorization, writer, scope, operation, request_sha256,
   valid_until (timezone), approval=approved, authority. Deliver the authorization SHA256 by an
   independent trusted channel. Do not copy a pin from an untrusted request/receipt.
2. Supply `--previous-sha256` from the latest private state pin, or `absent` for first scan.
   `--writer` and `--scope` must equal the established state owner/scope.
3. Prepare one record using [closed action schema](../contracts/knowledge-collection-record.schema.json).
   Obtain a new operation=record authorization pinned to those exact raw request bytes.
4. Input/output/evidence objects are exact files named by SHA256 in `--objects <private-dir>`;
   later records may reuse the durable store's objects. No original bytes are regenerated.
5. Reserve batch and dispatch intent durably before external Agent launch. A lost response,
   expired lease or dispatch_unknown requires Manager start/not-started evidence, never an
   automatic retry. After output receipt, resume delivery. Before Git changes record commit_pending;
   after uncertain Git outcome, fetch the fixed committed snapshot and acknowledge exact bytes.
6. For existing work supply reserve's `prior_ledger_sha256`; preserve exact scope and all history.
   For renewed terminal work supply the existing retry grant and independent pin, with old history,
   reason, new epoch/limits and relationship. A receipt is not a grant. No attempt exceeds three.
7. Keep private plans/history and public status counts separate. Knowledge failure does not change
   development gates. Record P-C/P-D, independent Test/Review, PR and merge as separate pending work.

```bash
python scripts/knowledge_collector.py scan \
  --store <PRIVATE_STORE> --previous-sha256 <PIN_OR_absent> \
  --writer <MANAGER> --scope <SCOPE> --request <REGISTRY> \
  --authorization <PRIVATE_AUTHORIZATION> --authorization-sha256 <INDEPENDENT_PIN>
python scripts/knowledge_collector.py record \
  --store <PRIVATE_STORE> --previous-sha256 <CURRENT_PIN> \
  --writer <MANAGER> --scope <SCOPE> --request <RECORD_JSON> \
  --authorization <PRIVATE_AUTHORIZATION> --authorization-sha256 <INDEPENDENT_PIN> \
  --objects <PRIVATE_INPUT_OUTPUT_OBSERVATIONS>
```

See [transition/recovery contract](../contracts/knowledge-collection.md). Never publish this
filled-in template, private snapshots, operational authorizations or Manager identity mappings.
