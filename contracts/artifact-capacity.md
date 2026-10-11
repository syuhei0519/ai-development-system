# Delivery 1.3: bounded artifact capacity

Delivery 1.3 increases only the explicit `artifacts` array limit from 128 to 256.
The manifest, publication receipt and consumption receipt share that limit;
authorization selects the same version. All four records must use `schema_version=1.3`.
The Consumer and preparation CLI reject unknown/mixed versions. Handoff 2.0,
Readiness 1.1, Knowledge contracts and retry histories are unchanged.

## Compatibility decision

Changing the released 1.2 maxItems in place would make a document labelled 1.2
pass a new validator and fail an old one. Instead, four separately named
`*-v1.3.schema.json` files provide explicit opt-in. Their only differences from
1.2 are schema identity/version and the three artifact-array maxima. Legacy
1.0/1.1/1.2 schemas and validation semantics retain 128. Old Consumers reject 1.3;
new Consumers still accept valid old records. Do not relabel old records or
rewrite their payloads. Preserve old manifest/receipts and produce new records
with independent authorization pins. Existing original artifact bytes and their
references remain unchanged when adding subsequent evidence.

## Bounds and unchanged gates

- 256 explicit artifacts in 1.3; 128 in legacy versions.
- Each commit/blob remains at most 16 MiB; the combined bundle including tree
  members remains at most 64 MiB. More entries do not provide more byte budget.
- Structural slot bindings remain at most 4096. Knowledge bindings, candidate
  bindings, candidate IDs and per-candidate source slots retain their existing
  128 limits. Candidate document string/count limits remain unchanged.
- Tree limits remain 4096 descendant entries, 1024 descendant trees, 1 MiB per
  raw tree and 4 MiB tree metadata. Existing safe paths (512 characters), depth
  implied by safe paths, raw-object bounds and regular-object checks remain.
- All dependencies of every Handoff/Knowledge document must be explicit and
  completely bound. Never delete originals, past history, slots or closure to fit.
- Fixed commits, SHA/size, object/format typing, strict JSON, immutable candidate
  profiles, representation approval and original/derivative separation remain.
- Public safety review, publication approval and separate Consumer authorization
  remain distinct. Receipts grant no authority; rechecks fetch all bytes freshly
  into a new output directory. Existing delivery outputs must not be overwritten.
- Dispatch/execution/delivery each remain at most 3. New capacity does not reset
  counters, relabel attempts or reopen terminal histories.

If the finite count, byte or structural bound is exceeded, stop and return the
blocker to Manager. Do not truncate, omit dependencies, automatically retry,
split a required closure across unverifiable bundles, or weaken any bound.

## Operation and verification

Use `prepare_crossref_bundle.py --delivery-version 1.3` for new larger records;
its default remains 1.2. Obtain matching separate authorization and use the normal
`consume_delivery.py` arguments. The normal schema-record CI checks all versions,
and unittest discovery includes `tests/test_artifact_capacity.py`.

```sh
python -m unittest discover -s tests -p test_artifact_capacity.py -v
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
```

The offline tests preserve a 128-artifact legacy bundle and add a dependent
Handoff at 129, then grow to 256. They reject 257, byte overflow, missing closure,
duplicates, tampering, type confusion, approval mismatches and mixed records.
They also replay the existing cross-reference, candidate and tree attacks in 1.3.
Synthetic success is implementation self-verification, not independent Test/Review
or product acceptance. Until this System PR passes CI and independent Review and
is merged through the existing gates, 1.3 is a candidate, not a trusted canonical
profile. Transport this change in a small legacy bundle using the fixed known
validator; candidate schemas are review data, never the transport trust root.
