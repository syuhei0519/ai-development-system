# Independent Test attempt3 — System PR8

Result: **completed for the assigned independent Test**, AC-S1–S5 covered at fixed head
`cdaad5a0d7437a9abc24481e4849b89a9e112401`. No new implementation defect found in the required cases.
Test1 F1/F2 are resolved on this head by fresh independent measurements. Historical Test1 failed and
Test2 system-failed/business-blocked records remain unchanged. No final_assessment or live Merge Ready is issued.

Public alias: readiness-prerequisite-test-a3; role test; attempt3;
scope ai-development-system#readiness-prerequisite-support.
The five original ACs and assignment in handoff.json are Manager-defined System acceptance criteria,
not backend-app product ACs or a retrieved GitHub Issue body.

## Fixed subject, governing inputs and independence

- Repository: syuhei0519/ai-development-system. Existing Draft PR: https://github.com/syuhei0519/ai-development-system/pull/8.
- Base/canonical System baseline: `0083151aa2f6b2aaf0e1db64ada3f196ed766e48`.
- Head/target: `cdaad5a0d7437a9abc24481e4849b89a9e112401`; tree `bd6db38a828be65062b7cf0bd8044765190b0cc1`.
- Historical failing head: `3f41a0470fd0b7a2199be0b947bb22284e993e2f`.
- Read the baseline workflow, contracts README, Handoff2 schema, Delivery1.2, Readiness1.0,
  IssueCompletion, input template and test role. No applicable AGENTS.md/SKILL.md was found in workspace
  ancestors or the target repository. Proposed Readiness1.1/IssueCompletion1.1 are test subjects, not the governing baseline.
- Used the Manager's explicit verification plan. No separate Research handoff or Knowledge context was supplied or assumed.
- Baseline consume_delivery.py succeeded with the independently supplied Manager authorization pin and
  fresh isolated Git: **90 artifacts, 71 structural slots, 1,928,316 payload bytes**. Manifest, publication and
  prior-Handoff size/hash pins match the input. Private authorization and Consumption Receipt are excluded.
  Typed upstream/retry closure was used only after success; no original bytes were LLM-reconstructed.
- All measurements below were newly executed in this task. Implementation's self-verification and Test2's
  recovered 309/280 results were not reused as independent results. No child Agent was launched.

## New independent execution

| Verification | Result | Evidence |
| --- | --- | --- |
| Baseline `python -m unittest discover -s tests -v` | 280 tests OK, exit0 | baseline-suite.txt |
| Head same full command | 309 tests OK, exit0 | head-suite.txt |
| Original independent_cases.py, unchanged | 237/237 expected, exit0 | execution-results.json |
| Original sample_checks.py, unchanged | 26 checks, no failures | execution-results.json |
| Original F1/F2 reproducers on old head | Both historical failures reproduced | execution-results.json |
| Original F1/F2 reproducers on new head | Preserved raw harness outcomes; interpretation below | execution-results.json |
| Published explicit v2 F1/F2 derivatives, unchanged | Aggregate control and preparation flow pass; invalid scope/FIFO rejected | execution-results.json |
| New additional_cases.py | 163/163: 116 behavioral, 28 schema, 19 compatibility-file checks | additional-results.json |
| Documented generated preparation example | synthetic ready/achieved | generated-example.txt |
| Current-head schema/document review and diff whitespace | Consistent; `git diff --check BASE HEAD` exit0 | this report / additional-results.json |

The head's 309 includes all 280 existing methods plus 29 additions; it includes the Readiness subset.
No subset count is added again. Every command executed against a detached fixed checkout. Implementation
worktrees remained clean; only test overlay, synthetic temporary data and the dedicated evidence branch were written.

Reproduce after verifying the delivery closure:

```sh
# Separate clean checkouts at BASE, HEAD and OLD as pinned above.
cd BASE
python -m unittest discover -s tests -v
cd HEAD
python -m unittest discover -s tests -v
python EVIDENCE/run_reproducers.py HEAD BASE OLD OUTPUT_DIR
python EVIDENCE/additional_cases.py HEAD BASE additional-results.json
python examples/issue-completion/preparation-example.py NEW_SYNTHETIC_DIR
```

`run_reproducers.py` requires the sibling reproducers directory. Its outputs and subprocess exit codes
are embedded in execution-results.json; named output_file/result_file values are command-local names.
The original scripts' hardcoded old `head` labels are preserved; the runner's checkout_revision records
the actual executed subject. The original sample script also hardcodes its old comparison refs; current-head
compatibility was separately checked in additional_cases.py and by reviewing the current diff.

## F1: preparation through aggregate completion

On the old head, the original standard aggregate control passes, standalone preparation with artifact root
passes, while empty product scope cannot enter aggregate completion. Missing root and related-as-product
scope also reject. This independently reproduces the original integration blocker.

On the new head, the original unmodified script still exits1 because it constructs an untyped 1.0
empty-scope aggregate and expects a missing artifact root/related-as-product substitution to pass.
Those inputs must remain rejected under the explicit versioned design. This harness exit is not a new defect.
The separately hashed published v2 derivative and new independent cases construct explicit 1.1 typed preparation.
They independently obtain synthetic **preparation ready → later standard product measurements → all required
merges and deployment → aggregate ready/achieved**. The preparation record retains every product AC and Issue
completion as unverified; the later product measurements, not process success, establish synthetic product outcomes.

Negative cases reject missing/unknown/duplicate artifact sets, wrong artifact root, digest/size/bytes,
historical kind/scope/version/original text/source/earliest phase mismatches, missing or tampered context pin,
preparation as a product verification target, preparation-only completion, missing current/required/result
members, unmerged preparation, wrong merge binding, incomplete full merge vector, missing merge/scope/deploy
permission, delivery approval substituted for product permission, missing/failed/wrong-stage/wrong-producer
measurements, wrong deployment source/config/image/environment/workload, and expired or failed historical gates.
All integration checks except product measurement_coverage retain the preparation member. The latter requires
the nonempty standard-member set. The final Bundle.finish reread independently detects a preparation artifact
changed after semantic validation. Nested materialization is covered by the new repository regression suite.

## F2: regular-file and bounded-read boundary

On the old head, a FIFO supplied with the matching55 bytes is incorrectly accepted. On the new head,
the original FIFO harness raises `reader did not open synthetic FIFO`; its writer assumes the defective
reader will open the FIFO. The v2 derivative and original237 writer-less FIFO case independently confirm
immediate exit1 on the corrected reader. Original and derivative scripts retain separate SHA-256 pins.

Fresh synthetic checks cover FIFO, Unix socket, directory, leaf symlink, ancestor symlink, replacement
between stat/open, replacement/growth/same-size mutation during read, ancestor replacement, root escape,
16MiB inclusive and +1 rejection, declared-size bounds and a never-EOF injected source bounded to limit+1.
Character device `/dev/null` was rejected by type before any data open; no device was created or read.
The successful target is Linux x86_64, Python3.12.14 with O_PATH and /proc/self/fd available.
Missing O_PATH and missing proc were separately simulated and failed closed. These are simulated unsupported
capability tests, not execution on another OS. An unsupported platform may raise an exception; no weaker
fallback or accepted artifact was observed. Native non-Linux support is outside this assignment.

No claim is made against a hostile writer after validation returns or an unresponsive filesystem/kernel.
Manager must retain the verified materialization and pins and revalidate after modification.

## Other acceptance boundaries

Original237 and the full repository regressions cover standard1.0/1.1 normal controls and empty-AC refusal,
old Consumers rejecting1.1, unknown versions/kinds/fields/types and duplicate identities; nonempty process
conditions/artifacts/related ACs/followup; missing/failed/unmeasured conditions; context condition/artifact/subject
mismatches; fixed artifact absence/unreadability/bytes/hash/revision and unsafe paths; Test/Review evidence
kind/subject/independence/producer/condition/artifact/AC binding; CI-only substitution; every merge gate;
automatic/unknown deployment effects, single_pr, known product not_met, unmerged achieved, false aggregate
integration, premerge deferral, stale policy/evidence and source/config change. Readiness/Handoff local identity,
artifact_id, kind, exact file, bytes and digest are exercised.

Nonblank scope prose, declared approval, a schema-valid source or a caller-supplied pin are not authentication
or proof of truth. The independently trusted Manager context and examination of real scope, approvals and
producer identity remain necessary. Process evidence may have empty product ac_ids because its required
binding is conditions and fixed artifacts; unknown AC claims reject. No product coverage is invented.

Handoff2, Knowledge1, Delivery1.2 schema/validator bytes and the IssueCompletion1.0 schema files remain
unchanged from baseline (individual byte checks recorded). Aggregate CLI changes are intentional and tested.
Readiness/IssueCompletion documentation, samples, role additions, README and task/workflow templates consistently
describe explicit preparation, none/aggregate_required, related versus assigned ACs, independent evidence,
fixed artifact delivery and later product/integration responsibility. Schema validity alone is not the Test result.

## Test overlay corrections, preserved separately

The first additional overlay invocation stopped on a temporary name collision (`ancestor` symlink versus
mutation directory). It did not emit a complete result and is not counted as completed testing. After that
test-only correction, 161/163 passed; two apparent deviations were investigated. The fixture shares Python
objects for expected/current sources and images. In-place mutation changed both, making those synthetic
inputs internally consistent. The final overlay replaces only actual lists, leaving independently expected
values intact; both intended mismatches reject and final163/163 passes. Prior script bytes, hashes, traceback
and intermediate results are retained in harness-provenance.json. No implementation changed and no product
failure was discarded. This is one task attempt3; no task restart, new execution budget or Agent dispatch occurred.

## AC-specific Test disposition

| AC | Disposition | Evidence and boundary |
| --- | --- | --- |
| AC-S1 | covered | Original237, baseline/head regressions, standard controls and old Consumer rejection preserve the ordinary gate. |
| AC-S2 | covered | Process/independent-proof/product-state checks plus independent F1/F2 repair verification and aggregate negatives. Test1 not_met is resolved only for this fixed new head. |
| AC-S3 | covered | none/aggregate restriction, all gate/permission/freshness/dependency/failure and aggregate-vector/deployment protections tested. No live operational permission certified. |
| AC-S4 | covered | Fresh280/309, original237, samples26, additional163, current schema/compatibility/docs review and generated example succeed. Test1 not_met is resolved for this head. |
| AC-S5 | covered | Input full typed Git closure, fixed head/tree, existing Draft PR8 on feat/readiness-prerequisite-gate and output's fixed Git delivery. No duplicate PR created. |

These are Test responsibilities, not Manager's final product or Issue AC judgment.

## CI, expiry and remaining gates

Fresh metadata confirms PR8 open, Draft, unmerged, auto_merge=null at the fixed head/base. Independently queried
CI run38130204297 is completed/success, event=pull_request, head=cdaad5a..., workflow=.github/workflows/validate.yml.
No forbidden raw log request/retry/alternate path was made. Metadata success is not a claim to have inspected raw CI logs.

pins.json records fixed subject/config completion and the Manager-specified24-hour expiry. Any change or new
failure invalidates it immediately. GitHub snapshots have separate five-minute windows in github-observations.json;
expired observations are not renewed by editing dates. Manager must freshly acquire mutable PR/CI/policy state,
required checks/reviews/Ruleset/queue, actor permission, any required merge-group and independent Review before action.
No real product measurement, deployment, merge, live MergeReady or final Issue completion is claimed.

## Delivery and retained history

Only evidence/readiness-prerequisite-test-a3 and evidence/readiness-prerequisite/test-a3/ are used for new public
output. Prior Handoffs/artifacts remain at original fixed references and raw bytes in the typed closure.
retry_of is readiness-prerequisite-test-a2 attempt2; dependency is readiness-prerequisite-implementation-a2 attempt2.
All dispatch/execution/delivery limits remain3. This is the last execution in the existing budget; other histories,
budgets and terminal states are unchanged. No self-retry, Agent launch, source fix, main push, merge/auto-merge,
Issue edit, deployment, secret/permission/Ruleset/environment change, Knowledge scheduling or extra OpenAI API occurred.

Public content was inspected as synthetic tests/results, reports, public Git/CI metadata and fixed public inputs.
Private authorization/receipts, private originals or their hashes, runtime identifiers, conversations, secrets and
internal raw logs are excluded. The standing owner permission covers publication after safety review. Published
derivative inspection does not prove comparison with private originals; upstream Producer testimony stays distinct.

Publication Receipt and fresh typed closure observations are transport evidence, not a new Consumer authorization.
Manager must supply separate bounded Consumer approval and run baseline consume_delivery.py before downstream use.
