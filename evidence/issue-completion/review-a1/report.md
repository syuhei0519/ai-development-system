# Independent Review — System PR #5

Public alias candidate / edited derivative / unpublished. Role=review, attempt=1, scope=system/issue-completion/aggregate; assigned AG-1–AG-5. **Assignment completed; no blocking findings.** This reviews the design and contract implementation, not product Issue acceptance, merge readiness approval, or permission to publish or operate a product.

Fixed head: b6d446ceb072e3a6d137318175bb672155d9b206. Fixed canonical base: b1e606544174481b7b6904f811e857f80978c287. All 50 changed files are inventoried in source-inventory.json. Review covered both schemas, all validator paths, tests and synthetic samples, README, roles, workflow and task template; the verified design alternatives and Implementation/Test evidence were compared to the assigned verbatim AG text. The adopted separate aggregate schema/context/CLI preserves PR Readiness v1 and Handoff v2. Removing the old aggregate prohibition or embedding multiple subjects in the old PR schema would weaken or break existing contracts; the independent entry point is appropriate.

## Independently observed verification

| Check | Result |
| --- | --- |
| Unchanged fixed-main Consumer | 26 files / 564620 bytes; size/hash/type/schema/Handoff dependency and retry closure verified before use |
| Fixed-head unit methods | 181 PASS |
| Fixed-main unit methods | 128 PASS |
| Unchanged prior independent probes | 130/130 expected/actual checks PASS |
| Test attempt-2 boundary probes | 38/38 PASS, including four explicitly declared limitation observations |
| Preserved workflow CLI commands | 9/9 PASS |
| Original F1/F2, before repair | Both unexpectedly accept achieved (exit 0 versus original expected 1); historical failures reproduced |
| Original F1/F2, fixed integrated head | Both reject with exit 1 |
| Additional Review probes | 12/12 expected observations; includes one explicit v1 limitation, not a safety guarantee |
| Compatibility and source | All 29 existing schema/Python validator/test files byte-identical to main; diff whitespace check passes |

Independent results and case-level outcomes are in results.json. Environment: Linux, Python 3.12.14, jsonschema 4.26.0. Unit methods with subtests are counted as methods. The original independent script's exit 0 is insufficient: all individual booleans and expected/actual exits were inspected. Reproduction uses unchanged upstream scripts plus review_probes.py. No implementation or existing expectation was edited.

## Requirement assessment

| AG | Independent assessment and implementation locations |
| --- | --- |
| AG-1 | Covered. Aggregate required/unknown remains unverified in PR Readiness. Aggregate validator derives all gates at scripts/validate_issue_completion.py:380–445. Single merge, all-premerge-met alone, or incomplete integration cannot achieve. Honest pending records return exit 0 with blocked/unverified. |
| AG-2 | Covered. Closed schemas require member/repo/revision/approval/deployment vectors and observation times. Validator lines 154–357 checks complete sets, DAG, current subjects, actual merge mapping, config/image/source/environment/workload, expiry and structured raw evidence. Scope approval and operation approval are separate. Completeness and provenance truth still require independent Manager acquisition. |
| AG-3 | Covered. Lines 269–379 distinguish phase, merge/deploy chronology, full vectors, verification identity and all required subchecks; lines 449–475 require the completed Manager final Handoff and identical AC/measurement bytes for achieved. Original AC text and sources are preserved. Receipt/article substitution and delivery-as-operation authorization reject. |
| AG-4 | Covered within the explicit Manager trust boundary below. Lines 53–78 and 404–445 compare retained requirement identities/semantics, require newly appended events, keep the immutable prefix and failure latch, and distinguish unverified from failure/rollback/revert. Current evidence expiry rejects rather than reusing an old success. Full definition history is not fully machine checked. |
| AG-5 | Covered. Separate schemas/CLI, exit semantics, normal/negative synthetic cases, historical/final Handoff separation, regular-file/ancestor/raw-byte checks and legacy/P-A compatibility are concrete. The workflow retains contents:read and existing jobs/checks while adding aggregate replays. AI Review does not replace required GitHub review. User approval does not confer GitHub authority. |

These labels cover this Review responsibility only. Product operations, product measurements and product AC achievement are outside the assignment and remain unverified.

## F1 and F2

F1: the unchanged required_subcheck_removed_without_change_event reproducer removes runtime-persistence from current requirements, results, measurements and AC bindings while retaining a pinned previous assessment and adding only revalidated. Before repair it accepts ready/achieved; the fixed head rejects. The repair compares IDs, AC mapping and recorded measured semantics and requires a new required_set_changed event. Old events and reordered arrays are handled correctly. The 38 boundary probes check removal/addition semantics, old versus new events and scope-update controls.

F2: the unchanged pr_handoff_symlink_locator reproducer routes the historical PR Handoff Readiness locator through a symlink to the same legitimate bytes. Before repair it accepts; the fixed head rejects at the common Bundle.artifact path. The exact claim is path-policy repair, not proof of former different-content acceptance or disclosure. Leaf/ancestor links, alternate files, lexical aliases, FIFO/directory/missing paths reject; nested regular relative files succeed. Additional Review probes also reject a symlink at the assessment root, previous-assessment symlink and previous-byte mutation. Final reread detects covered-file changes; hostile writers after validation remain outside this local trust boundary.

## Required Manager procedure and residual risk

The previous v1 assessment does not store all unmeasured verification definitions or failure_action. contracts/issue-completion.md:81–99 explicitly assigns their changes to the Manager's scope-original/scope_revision/history procedure; the full old definitions cannot be reconstructed from that assessment. This is a material operational constraint, not complete automatic change detection.

Review adds a stronger observation than the pending-only case: a pinned previous pending assessment can be followed by a fully measured achieved assessment with a changed formerly unmeasured method while reusing the old scope revision. The validator accepts because that old method was never stored. This deliberately violates the Manager scope-update duty; it is a **known-limit observation**, not an approved way to operate. All current synthetic measurements and other gates are still supplied. Removing a required measurement from the otherwise updated case rejects.

The required procedure is executable: retain the prior approved scope original and full current-context snapshot with independent pins; compare the complete required PR/deployment/verification definitions, including unmeasured fields and failure_action; obtain the appropriate scope approval for semantic changes; update scope original/raw scope_revision and current decisions/evidence bindings; append the corresponding required_set_changed event without changing the old prefix; supply the latest previous-assessment pin; reacquire all required current measurements. The probes confirm a scope bump without its event rejects, and complete scope/event/measurement updates accept. A receipt, newly computed self-pin, or written event alone cannot substitute for those independent acquisitions.

I find this compatible with AG-4 for the specified offline contract plus mandatory Manager procedure: AG-4 does not require autonomous monitoring or complete historic-definition reconstruction, and the contract does not waive re-evaluation or any current measurement gate. It would be unsafe to deploy this CLI as an autonomous final-decision engine or to claim that it detects every silent semantic change. If the prior approved full definitions/latest pins cannot be established, the Manager must stop rather than accept this known blind spot. A future separately scoped contract may carry the prior context/full definitions for machine comparison.

Other residual boundaries: Manager verifies necessary-set completeness, original AC authority, actor approvals, historical merge tree/provenance, real environment state, measurement truth and real Test/Review independence. Generic scope/evidence files are not signatures. The validator is conservative about expired active approvals and unresolved failures. GitHub required checks/reviews/ruleset/queue and operation-time user authorization remain independent mandatory gates.

## CI and Git observation

Read-only GitHub run/job metadata and connector job logs were independently obtained. The CLI log route returned Forbidden; connector retrieval succeeded. This does not repair or validate the CLI route. Raw logs are private.

- Push run https://github.com/syuhei0519/ai-development-system/actions/runs/38111782731: success, actual checkout b6d446ceb072e3a6d137318175bb672155d9b206, 181 tests / OK, achieved and pending replay passed.
- PR run https://github.com/syuhei0519/ai-development-system/actions/runs/38111785804: success, actual checkout d3746526b52e0ed50e6e3a52f45b2ffc476bdd8f, 181 tests / OK, both replays passed. API head alone was not used to infer checkout.
- Independently fetched test-merge parents are fixed main then fixed head. Its tree and the fixed-head tree are both 1c7b003edd88407af2e8ae34524992f4d2b54324. Fixed base tree is 10a4b8ccf7a8d10d991bef2cbe714afc35709b48.
- PR #5 was independently observed open/draft with the exact assigned head/base. There was no merge into main. CI success is not a required GitHub review or authority to merge.

## Handoff, preservation and safety

Review is PUBLIC-AGGREGATE-REVIEW-001, attempt 1. Test attempt 2 and Implementation attempt 2 are dependencies, not Review retries. Their unchanged Handoffs preserve their original retry_of chains, including failed Test attempt 1 and its F1/F2 evidence. The 26 verified public input files are copied byte-for-byte beneath upstream/; no old report, input, result, status or expectation is rewritten. Root AG requirements are unchanged.

The private incoming authorization was saved as the supplied one-line UTF-8 JSON plus LF, independently pinned and made read-only. A fresh Consumption Receipt and all raw logs/metadata remain private, separate from this candidate. No private authorization/pin/receipt/original hash/runtime task identifier is included here. Upstream private originals were not supplied, so no direct comparison to those originals is claimed. Source-thread identity is not substituted for a runtime task ID. This candidate has public aliases only; its inventory and closure verification do not constitute publication or Consumer-use approval.

The additional-probe setup initially omitted the existing head_changed event when transitioning a pending record's null approved heads to fixed merged heads. That fixture correctly rejected; the fixture was corrected to retain that unrelated mandatory event before isolating the unmeasured-definition comparison. Original and final probe results are retained privately and the setup observation is recorded in results.json. This was probe construction within Review attempt 1, not an implementation repair or retry reset.

Reproduce: `python reproduce.py HEAD_CHECKOUT NEW_OUTPUT --base BASE_CHECKOUT --before BEFORE_REPAIR_CHECKOUT`. It verifies exact checkouts, runs the preserved upstream reproduction and the Review probes, and emits local logs/results. Network CI observation is a separate read-only step. Source code is obtained from the fixed Git revisions; the candidate includes all Handoff artifact/upstream dependencies with exact raw-byte inventory.

Assignment: completed. Blocking findings: none. Input use and independent verification: verified. Product Issue achievement: unverified. Candidate publication: pending/not performed. Push/PR edits/comments/merge/deploy/application execution/extra API/Secrets/permission/Ruleset changes/additional agents: forbidden and not performed. No further task is launched; return to Manager and stop.
