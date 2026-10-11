# Independent aggregate Issue Completion Test — attempt 1

Status: failed. Scope: system/issue-completion/aggregate; role: test; assigned AG-1 through AG-5. Two independently reproduced acceptance gaps require Implementation/Manager disposition. No implementation fix, push, PR comment, merge, deployment, product connection, additional API, Secret/permission/Ruleset change or other branch change was performed. This is a public-alias candidate, not a publication or product acceptance decision.

## Findings and reproduction

Reproduce from a clean checkout of head `591f896d30fde5630d49f99a4ea7544ff90f53a4` with its existing requirements-dev.txt dependencies installed:

```sh
python independent_cases.py SOURCE_CHECKOUT NEW_LOCAL_OUTPUT_DIRECTORY
```

The script copies only public synthetic examples into the output directory, runs the checkout's CLI from another working directory, and writes each mutated bundle and results.json. It does not import producer test helpers, modify source, or connect to a product environment. Results must be read: the script returns normally after recording expectation mismatches. All times, actors and product identities in these cases are synthetic. A fresh output directory is required.

### F-1: required subcheck removal lacks required-set history event

Case: `required_subcheck_removed_without_change_event`.

1. Start from the valid synthetic-achieved bundle and save the original completion as previous.json.
2. Pin its exact bytes in context.previous_assessment_sha256, history.previous_ref, and the separate CLI --previous-sha256 argument.
3. Remove runtime-persistence from required_verifications, current results/measurement, AC evidence mapping, integration coverage and final Handoff evidence. Preserve AC originals, member set and scope_revision. Append only a revalidated event, without required_set_changed.
4. Recompute the deliberately changed synthetic context/observation/Handoff bindings and invoke the CLI using the new independent test context pin and original previous pin.

Expected: exit 1 because a required subcheck set changed without its required_set_changed event. Actual: exit 0, `integration=ready; issue_completion=achieved`.

Location: scripts/validate_issue_completion.py:377 compares member IDs, AC originals and scope_revision but not previous/current verification IDs. The contract's history section requires corresponding events for scope/set changes. The previous assessment contains verification_results and can expose this removal.

Impact: incomplete change history can be accepted on a newly pinned context even with a correctly preserved latest previous assessment. This is a history-audit failure, not a demonstration of forging an independent Manager pin or bypassing current exact-set checks. A Manager still must review changed requirements. Blocking AG-4 finding; no product achieved result is inferred.

### F-2: PR Handoff symlink escapes the aggregate path policy

Case: `pr_handoff_symlink_locator`.

1. Start from the valid synthetic-achieved bundle.
2. Add pr-link.json as a symlink to app-readiness.json.
3. Change only app-handoff.json's Readiness artifact locator to pr-link.json; refresh that Handoff's outer BlobRef size/hash in completion and the completion digest in the final Handoff.
4. Leave the context and Readiness bytes unchanged and run the aggregate CLI.

Expected: exit 1 under the aggregate contract's local regular-file/no-symlink rule. Actual: exit 0, `integration=ready; issue_completion=achieved`.

Location: aggregate validator's historical Readiness/Handoff pair call (scripts/validate_issue_completion.py:209) delegates to unchanged scripts/validate_readiness.py:214, which resolves the symlink before comparing paths. Bundle.path's explicit symlink rejection is not applied to this PR Handoff locator. The independent blob_symlink case rejects as expected; final Issue Handoff path controls also reject.

Impact: inconsistent path enforcement between BlobRef/final Handoff and historical PR Handoff. This reproduction uses the same legitimate target bytes; it does not demonstrate acceptance of different measured content or secret exfiltration. Blocking AG-5 contract-boundary finding. Preserve legacy CLI compatibility when addressing the aggregate entry point.

## Validation and provenance

Fixed base/System canonical revision: `df400018057735b7cb6a9c6ea4619508f0e6ba3a`.
Fixed head/actual independent Test checkout: `591f896d30fde5630d49f99a4ea7544ff90f53a4`.
Head tree: `db71edff9993e107a1949910aa8dceb0f111b5cf`.
The head has the fixed base as its sole parent. This is the requested P-A-unintegrated head. No parallel branch was integrated or changed.

Read-only Git fetch of refs/pull/5/head matched the fixed head. refs/pull/5/merge was `fc49be189209d738b76679c7d68ca404c534463e`, with parents fixed base and fixed head, and the same tree as head. That synthetic Git merge ref is not proof of a real merge or of a CI runner checkout. Test execution used detached head, not that merge ref.

- Base existing suite: `python -m unittest discover -s tests -v` — 107 passed.
- Fixed head existing suite: the same command — 152 passed (107 existing plus 45 new methods).
- Existing Handoff, Readiness, Knowledge, Delivery and Retry validators/schemas and existing tests inspected were byte-identical between base and head. All six legacy workflow CLI invocations passed: delivery record consistency, Handoff examples, Knowledge examples and three Readiness examples.
- Independent suite: 130 cases, 128 expectations met, 2 unexpected accepts. CLI mutations and exact expected/actual outputs are in independent-results.json. Two expectation mismatches are the findings above. Covered controls include normal aggregate achieved, honest unverified/not_achieved, single-PR all-premerge-met/unmerged, aggregate_required legacy rejection, missing/extra/duplicate sets, stale revisions, merge methods, historical gates, authorization actor/scope/action/expiry, independent context/previous pins, source/config/image/environment/workload, source substitution, measurement phase/freshness, failed integration and rollback/revert concealment, old measurements after failure, append-only history, strict JSON, bytes/path binding and both Handoff boundaries.
- No AG acceptance is inferred from producer tests alone. The independent suite uses its own mutation and CLI orchestration code, while deliberately reusing public synthetic example bytes as input.
- One expanded local harness run stopped because of a test-helper callback typo. The reproduction helper was corrected locally and rerun in a fresh output directory. This was a Test harness error, not a product failure or a new logical execution attempt.

CI is separate: implementation validation-summary.md reports successful push and PR runs at https://github.com/syuhei0519/ai-development-system/actions/runs/38108769215 and https://github.com/syuhei0519/ai-development-system/actions/runs/38108785285. This Test did not independently retrieve GitHub run status/logs; those remain producer-reported CI evidence, not independent CI verification. Local workflow reproduction does not assert remote CI success or live GitHub authority.

## Assigned requirement disposition

| Requirement | Independent Test disposition | Evidence/limits |
|---|---|---|
| AG-1 | covered | MergeReady/unverified separation, single-PR unmerged/all premerge met, legacy aggregate_required prohibition, valid synthetic aggregate achieved |
| AG-2 | covered | Exact required sets, old revisions, authorization, configuration/source/image/environment/workload, timing and source/binding negative controls; context truth/completeness remains Manager responsibility; F-2 is tracked under AG-5 |
| AG-3 | covered | Phase/event separation, all current subchecks, Manager final and original AC binding, no receipt/Knowledge authority; synthetic measurements only |
| AG-4 | not_met | F-1; expiry/failure/rollback/revert/previous pin controls otherwise passed |
| AG-5 | not_met | F-2; 152 existing tests and old contract/CLI compatibility otherwise reproduced |

Original AG texts are preserved verbatim in requirements.md and handoff.json. Assignment scope and all five IDs match the Manager input. Implementation's assignment was verified separately and not copied as Test completion criteria. Final product IssueCompletion and Order product AC are outside this assignment and remain unverified. Test emits no final_assessment. Manager must return findings to Implementation, obtain a fixed revision and required independent Test/Review evidence, and decide the final gate. No merge authority is granted.

## Delivery and public-candidate boundary

Incoming nine files were consumed only after unmodified base consume_delivery.py verified the independently supplied authorization, manifest/publication digests, fixed Git payload bytes, strict content typing, Handoff v2 and all artifact/upstream bindings. All 19 design source inventory entries also matched fixed base bytes. ConsumptionReceipt original and authorization original/pin are held privately. verification-summary.md is a separate safe summary and is explicitly not a Receipt.

The public candidate consists of this alias Test Handoff/report, independent synthetic code/results, verification summary, and nine already-public upstream files copied unchanged. The implementation Handoff filename is disambiguated as implementation.handoff.json without changing its bytes; its relative artifacts and design dependency still resolve. Public upstream hashes/revisions are retained. Private authorization bytes/pin, private original hashes, actual runtime task/thread identifiers and raw internal logs are excluded. Public upstream notices saying 'unpublished' are preserved as historical bytes and are not current Test publication claims.

No private upstream original was available for comparison; only the pinned public derivative bytes were independently checked. Producer safety statements are not substituted for independent raw-byte checks. New Test materials use public aliases from inception and summarize private execution observations; raw logs are not publication candidates. Publication is pending Manager safety review and explicit publication authorization. No manifest/Publication Receipt claiming a Test upload is produced.
