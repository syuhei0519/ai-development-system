# Synthetic cross-reference / candidate / tree reproduction

All files under `sources/` are synthetic transport data. Do not execute them.
No production result, operational Knowledge adoption or B1 acceptance is asserted.

1. Select an already-published fixed System commit containing `sources/`.
2. Generate a synthetic immutable producer and candidates:

   ```sh
   python scripts/prepare_crossref_fixture.py --repository OWNER/REPO \
     --source-commit FULL_40_HEX --output /tmp/synthetic-crossref
   ```

3. With the applicable feature-publication authority, commit those exact synthetic
   files into a fixture subdirectory. The source commit stays fixed. This two-commit
   structure avoids self-hash cycles. Do not commit authorization files.
4. From the fixture's **new** fixed commit, prepare records in a private directory:

   ```sh
   python scripts/prepare_crossref_bundle.py --repository OWNER/REPO \
     --commit FIXTURE_40_HEX --handoff-path FIXTURE_DIRECTORY/handoff.json \
     --handoff-sha256 RAW_HANDOFF_SHA256 --output /tmp/crossref-records
   ```

   Preparation retrieves complete bytes and records the blob/commit/tree pins.
   It creates no authorization or verified Consumer output and is not formal
   delivery success. The helper supports Handoff dependencies and this candidate
   profile; it is not a universal Knowledge-input/context manifest builder.
   Candidate source kind is the `blob` or `tree` route segment immediately after
   owner/repository. Those words in an owner, repository or nested path do not
   change the kind. Fixed OID, canonical URL and safe path checks still apply;
   unknown routes, query strings and encoded paths are rejected.
5. Obtain a separate current Manager authorization with version `1.2`, manifest
   and publication raw pins, exact consumer/scope/purpose/expiry and `original`
   representation allowed. Supply its independent pin directly to the CLI:

   ```sh
   python scripts/consume_delivery.py \
     --manifest /tmp/crossref-records/manifest.json \
     --publication /tmp/crossref-records/publication-receipt.json \
     --authorization /PRIVATE/manager-authorization.json \
     --authorization-sha256 MANAGER_INDEPENDENT_PIN \
     --consumer APPROVED_CONSUMER --scope APPROVED_SCOPE --purpose implementation \
     --output /PRIVATE/new-verified-output
   ```

6. Re-run with another fresh output and `--verify-receipt` pointing at the prior
   receipt. This re-fetches sources, including every tree blob. It does not inspect
   the old output directory. Approval and source truth remain separate gates.

Offline regression (no external network, synthetic local Git object fixtures):

```sh
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
```

Tests retain the original 128 plus previous-attempt 21 methods, and add candidate
profile/producer/source/approval/type and complete-tree negative cases. Real B1
verification requires its own Manager authorization; synthetic success cannot
replace it. No application build, tests or deployment are part of these commands.

## Bounded capacity (Delivery 1.3)

[Capacity and compatibility contract](../../contracts/artifact-capacity.md): explicitly select 1.3 for up to
256 artifacts; legacy 1.0/1.1/1.2 retain 128. All four delivery records must match.
Per-file 16 MiB, bundle 64 MiB, tree/slot/candidate limits and all approval gates
remain unchanged. Preserve originals and complete closure; never overwrite old
delivery outputs. Dispatch/execution/delivery remain each at most 3. Candidate
1.3 requires System CI and independent Review before merge and canonical use.
