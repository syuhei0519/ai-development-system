# PR #5 Independent Test attempt 2

Public alias candidate / edited derivative / unpublished. Role=test; scope=system/issue-completion/aggregate; AG-1–AG-5. **Assignment status: completed.** No new implementation defect or execution blocker was found in the assigned checks. This is independent contract implementation verification using synthetic data, not product AC acceptance or merge permission.

The fixed System configuration is `b1e606544174481b7b6904f811e857f80978c287`. The tested integrated head is `b6d446ceb072e3a6d137318175bb672155d9b206`; tree `1c7b003edd88407af2e8ae34524992f4d2b54324`. Its ordered parents are repaired head `2f1c1900aaacf85870742ee989357d9a2b20bfea` and the fixed System main. “Integration” here means main merged into the feature branch. PR #5 is still open and draft, and was not merged into main.

## Independent results

| Verification | Observed result |
| --- | --- |
| Fixed-head unit suite | 181/181 PASS, including 21 P-A Knowledge delivery methods |
| Fixed-main compatibility suite | 128/128 PASS |
| Unchanged prior independent CLI probes | 130/130 individual expected/actual checks PASS |
| Additional independent boundaries | 38/38 PASS, including four explicitly labelled known-limit observations |
| Legacy/P-A CLI and aggregate replay commands | 9/9 PASS |
| Original F-1/F-2 on pre-repair commit | Both original expected-reject probes reproduce unexpected exit 0 / achieved |
| F-1/F-2 on integrated head | Both exit 1; original expectations retained |
| Source preservation | 29 existing schema/validator/test files byte-identical to main; 18 P-A-specific files byte-identical to main; four repair files byte-identical to repaired head |
| Merged documentation/workflow | README, contracts README and workflow retain both P-A and aggregate additions; whitespace check PASS |

Local environment: Linux, Python 3.12.14, jsonschema 4.26.0. All commands, method-level results, boundary observations and revision comparisons are in `results.json`. Unit methods containing subtests are counted as methods, not inflated subcase totals. The unchanged independent script exits zero even if individual probes fail, so all 130 `passed` values and exact expected/actual results were checked. No test expectation or implementation source was edited.

## F-1 and F-2 repair assessment

F-1 is reproduced at `591f896d30fde5630d49f99a4ea7544ff90f53a4` by `required_subcheck_removed_without_change_event` in `upstream/independent_cases.py`: remove runtime-persistence from current context/results/evidence/all-AC bindings, preserve a pinned previous assessment, and append only revalidated. Expected exit 1; old actual exit 0, ready/achieved. Integrated actual exit 1. `scripts/validate_issue_completion.py:53` compares verification IDs, AC mappings and previously measured semantics; the history block requires a newly appended required_set_changed. Adding that event permits the otherwise consistent synthetic new scope. A method change without the event also rejects; an old matching event cannot cover a new change; harmless reordering remains accepted.

F-2 uses `pr_handoff_symlink_locator` from the same unchanged script. It points a historical PR Handoff Readiness artifact through a symlink to the same legitimate bytes. Old actual exit 0, integrated exit 1. The aggregate entry at `scripts/validate_issue_completion.py:249` now invokes the common local-file/digest/same-path check. Additional probes reject ancestor symlinks, FIFO, directory, missing files, alternate files with identical bytes, absolute/dot/parent/empty-component/backslash locators, and symlinks on assessment/context/final Handoff. A nested relative regular-file pair succeeds. Mutation of an already-read measurement just before final reread is rejected. This confirms path-policy repair, not a historical finding of different-content acceptance or leakage.

## AG-4 limitation and executable Manager responsibility

`contracts/issue-completion.md:93` and `verification_requirements_changed` explicitly state that previous-assessment v1 does not retain unmeasured verification definitions or failure_action. Independent tests confirm that changing failure_action without changing scope revision is accepted, and changing method/owner/expected_result on an unmeasured pending definition also remains a valid unverified record. These are **known-limit observations**, not evidence of complete automatic detection.

The documented Manager procedure is clear and executable: retain the approved scope original and previous context; compare the full definitions; update the scope original and its raw scope_revision for every semantic change; bind the updated revision in current context/decisions/evidence; append required_set_changed while preserving the old event prefix; use the independent current and latest-previous pins. For all four limit probes, updating scope_revision without that event rejects, and adding the event accepts the consistent record. Pending measurements remain unverified. Manager must independently substantiate new approvals and observations; refreshing synthetic bindings in a test is not a production evidence-acquisition procedure.

This bounded, explicit manual responsibility is consistent with AG-4 and does not block this contract implementation test. The validator alone cannot detect a Manager silently changing absent historical definitions while reusing scope_revision. Full automatic comparison requires the pinned prior context or a later contract extension. No complete-detection claim is made.

## Assigned requirement coverage

The unchanged verbatim AG requirements are in `requirements.md` and Handoff v2. These labels are design requirements, not product Issue IDs.

| Requirement | Independent coverage and boundary |
| --- | --- |
| AG-1 | PR MergeReady remains separate from aggregate completion. Legacy all-premerge-met/unmerged and aggregate-required false achievement reject; honest integration pending remains unverified. Positive aggregate achievement requires the complete synthetic gates. |
| AG-2 | Required PR/repo/verification/deployment sets, duplicate/missing entries, multiple PRs per repo, DAG, current head/base/target/config/merge SHA/queue, authorization actor/scope/action, source/image/config/environment/workload, observation/expiry, measurement and raw-byte binding checks covered by 181 + 130 + additional probes. Missing merge/deployment/measurement never becomes achieved. |
| AG-3 | Premerge versus postmerge/postdeploy timing, original AC text, every required subcheck, integration readiness and Manager-only final Handoff verified. Receipt/Knowledge substitutions and AI-review substitution for GitHub review reject. Synthetic achieved is not unmeasured product achievement. |
| AG-4 | Head/required-set/deployment/expiry changes, immutable history prefix/latest previous pins, failure latch, rollback/revert/failed/unverified results covered. F-1 repaired within the explicit previous-v1 limitation and Manager procedure above. |
| AG-5 | Closed JSON schemas, positive/negative CLI replay, byte/path binding, Handoff v2/Readiness v1 unchanged semantics, Delivery v1/v1.1/P-A compatibility, adopted independent aggregate design and operational boundaries verified. User approval, CI, independent Test, AI review and GitHub checks/reviews/ruleset/queue remain separate gates. |

## CI revision and tree verification

Both GitHub run/job metadata and job logs were independently obtained through existing read-only authorization. The initial CLI log download route returned Forbidden; the separate GitHub connector successfully returned complete job logs. That does not imply the CLI route was repaired. Raw logs are retained privately and excluded from this candidate.

- Push [38111782731](https://github.com/syuhei0519/ai-development-system/actions/runs/38111782731): completed/success; checkout log identifies `b6d446ceb072e3a6d137318175bb672155d9b206`; log reports 181 tests and OK.
- PR [38111785804](https://github.com/syuhei0519/ai-development-system/actions/runs/38111785804): completed/success; API head is the same feature SHA, but actual checkout log identifies synthetic merge commit `d3746526b52e0ed50e6e3a52f45b2ffc476bdd8f`; log reports 181 tests and OK. The independently fetched commit has parents main + feature and the same `1c7b003edd88407af2e8ae34524992f4d2b54324` tree as the tested head.

Both logs include Knowledge fixture validation and achieved/pending aggregate replay success. These observations are for the integrated tree, not results borrowed from repaired-only head `2f1c1900...`. CI success is not GitHub merge authorization or independent Review.

## Input, retry, output and safety

Before using upstream content, an isolated checkout of the unchanged fixed-main Consumer CLI fetched and verified all 20 artifacts / 410453 bytes from payload commit `759c81c06da504a5c9834aa25875cd381e76d267`. The manifest and Publication Receipt came from fixed records commit `bd8e7ef37ff1b62447b79fecdf05d05af6018b06`. Sizes/digests matched the independent Manager pins; typed Handoff/JSON checks, artifact/upstream closure, retry identity and publication/use authorization were verified. AG originals were then matched exactly to the assigned text. A new Consumption Receipt and the supplied one-line authorization/pin are held privately. Neither grants product authority.

This Handoff is PUBLIC-AGGREGATE-TEST-002, role test, attempt 2. Its retry_of is exactly PUBLIC-AGGREGATE-TEST-001 in `upstream/test.handoff.json`, whose original failed status/attempt/bytes are unchanged. Implementation attempt 2 is a dependency, not the Test retry. All 20 input files are carried unchanged under `upstream/`; relative closure is intact. Original failed Test and Implementation histories are not reset or reclassified. This task used one incoming delivery verification and no dispatch of another agent or outgoing publication; all prescribed maxima remain 3. The global private dispatch ledger was not supplied and is not fabricated.

The candidate contains only public aliases, technical reports, synthetic test code/results, original AG text and unchanged approved public upstream bytes. Authorization files, private pins/receipt/original hashes, actual task/thread identifiers, internal logs and runtime worker identifiers are excluded. Full-byte UTF-8/JSON inspection and sensitive-pattern scan were performed; upstream private originals were not supplied, so comparison to those originals is not claimed. The inventory lists each payload's size/SHA-256/type and the validated dependency closure. This is an unpublished local candidate, not a Publication Receipt or new Consumer approval.

## Reproduction and remaining gates

After obtaining the candidate bytes and fixed source checkouts through an authorized path, run `python reproduce.py HEAD_CHECKOUT NEW_OUTPUT_DIRECTORY --base BASE_CHECKOUT --before BEFORE_REPAIR_CHECKOUT`. It checks the exact source commits, runs 181 head methods, 128 base methods, unchanged 130 independent probes, 38 extra probes, nine CLI invocations and the two original pre-repair reproductions. `results.json` records the performed commands; network/CI observation is a separate read-only step.

Implementation verification: verified. Independent Test assignment: completed. GitHub remote head and CI: verified at observation time. Independent Review and Manager final product assessment: pending. Product AC/Issue achievement: unverified. Publication, push, PR mutation, merge, deployment, app changes, API/Secret/Ruleset changes and additional agents: not requested/forbidden and not performed. No remaining blocker within the assigned independent Test scope. Return this candidate and private original evidence to Manager; do not infer permission for a subsequent operation.
