# Independent Test report — System PR 8

Result: **failed**, role test, public alias readiness-prerequisite-test-a1, attempt 1.
Manager-defined AC-S1–S5 are preserved verbatim in handoff.json. They are not backend-app product ACs or a retrieved GitHub Issue body. No final_assessment is issued.

## Subject and governing contract

Repository syuhei0519/ai-development-system; PR https://github.com/syuhei0519/ai-development-system/pull/8.
Baseline 0083151aa2f6b2aaf0e1db64ada3f196ed766e48; tested head/target 3f41a0470fd0b7a2199be0b947bb22284e993e2f; tree ee216bc39d2a2dbcfb4a0946e02d72ffd4d2b3c2. The head checkout is clean and no implementation files were edited.
Baseline workflow, contracts README, Handoff2, Delivery1.2, Readiness1.0, IssueCompletion, input template and test role were read. No applicable AGENTS.md was found in the workspace ancestors or target repository. PR-head Readiness1.1 is the test subject, not the governing System baseline. The Manager-provided mandatory test plan was used; no separate Research handoff or Knowledge context was supplied or assumed.

Input delivery: the baseline consume_delivery.py verified the independently supplied private authorization pin, all 30 typed artifacts and 29 structural slots from fresh isolated Git retrieval (exit 0). Input manifest/publication/Handoff raw size and SHA-256 matched the supplied pins. Target head commit/tree were also checked. No candidate/tree snapshots are declared in this input bundle; no nonexistent tree coverage is claimed. The private authorization and Consumption Receipt are excluded from public output. Verification of a published edited derivative is not direct inspection of a private original. Producer statements remain distinct from the results below.

## Executed results

| Command / scope | Independent result |
| --- | --- |
| Baseline: python -m unittest discover -s tests -v | 280 tests, OK; baseline-suite.txt |
| Fixed head: same command | 292 tests, OK; head-suite.txt |
| Fixed head Readiness subset | 55 tests, OK; readiness-suite.txt; subset of 292, not additional tests |
| independent_cases.py HEAD BASELINE OUTPUT | 237 cases, 236 expected, one FIFO timeout deviation; exit 1 |
| aggregate_reproducer.py HEAD OUTPUT | Existing aggregate control and standalone preparation gate succeed; three integration expectations fail; exit 1 |
| fifo_reproducer.py HEAD OUTPUT | Nonregular FIFO with matching bytes unexpectedly accepted; exit 1 |
| sample_checks.py HEAD OUTPUT | 26 documented sample / schema / compatibility / whitespace checks succeed |

Implementation's reported 292/55 were not reused as independent measurements. Tests above were executed in this task. Environment and reproducible overlay hashes are in test-config.json. pins.json binds head/base/target/test configuration and records a 24-hour fixed-measurement window from completion. Subject/configuration change or a new failure immediately invalidates applicability. These failed results are not a readiness approval.

## F1 — P1: preparation cannot enter the required aggregate completion path

Locations: contracts/issue-completion-context.schema.json:794–802; scripts/validate_issue_completion.py:246,260; scripts/validate_readiness.py:182–183. All locations refer to the fixed head.

Expected: a correctly measured preparation PR, with empty product pr_ac_ids, must be retained as a required merged dependency in aggregate completion without inventing product AC coverage or discarding that required PR. Subsequent product PR measurements and all current aggregate gates must still be mandatory.

Actual: the required_pr ac_ids schema requires minItems=1, so an empty preparation scope is unrepresentable. Using related product ACs instead does not solve the issue: the historical scope must exactly equal readiness.pr_ac_ids. Independently, aggregate validation calls validate_readiness without artifact_root; every preparation record has a nonempty fixed artifact set, so it rejects with `materialized artifact root required` even when all artifacts are present. The standalone validator accepts that same synthetic historical preparation record when the root is supplied.

Reproduce: run `python aggregate_reproducer.py HEAD_CHECKOUT aggregate-results.json`. The existing three-member standard aggregate control exits 0. A preparation replacement preserves all synthetic product originals and leaves them unverified in its historical record; subsequent members provide the aggregate product measurements. The empty-scope version exits 1; assigning related ACs also exits 1. The script changes only temporary synthetic fixtures. No source patch or gate bypass is used.

Impact: the documented preparation → later aggregate completion workflow is incomplete. Workaround by omitting a required preparation member or asserting product coverage would violate the contract and is not endorsed. This is a compatibility/integration failure, not evidence that aggregate fail-closed protection was relaxed. Owner: Implementation/Manager must define and implement the historical preparation mapping and bounded artifact delivery, retaining the existing aggregate protections, then request independent revalidation.

## F2 — P2: preparation artifact reader accepts or blocks on a FIFO

Location: scripts/validate_readiness.py:184–189, especially target.read_bytes at line 188.

Expected: a fixed artifact must be a readable ordinary file; a special file must be rejected without unbounded waiting. Size/hash checks must not require opening a FIFO/device as an ordinary artifact.

Actual: resolve/containment is checked but regular-file type is not. A FIFO inside the assessment root with no writer stalls until the independent test kills the subprocess after two seconds. When a synthetic writer supplies the exact expected 55 bytes, the CLI returns exit 0 (PASS REPLAY), accepting a pipe as the fixed artifact. No real file, device, credential or external service is involved.

Reproduce: `python independent_cases.py HEAD_CHECKOUT BASELINE_CHECKOUT independent-results.json` contains artifact_FIFO_fail_closed; `python fifo_reproducer.py HEAD_CHECKOUT fifo-results.json` supplies the matching bytes. Both scripts terminate their child processes and keep implementation files untouched.

Impact: malformed local materialization can hang verification, and special-file input is treated as a fixed artifact. This does not demonstrate a live GitHub authorization bypass. Canonical Git delivery already rejects special files; the Readiness CLI also accepts independently materialized local artifacts, which is the tested boundary. Owner: Implementation should enforce ordinary-file/bounded-read rules while preserving size, raw hash, target and root checks; independent retest required.

## AC responsibility mapping

| Assigned AC | Test disposition | Evidence / limit |
| --- | --- | --- |
| AC-S1 | covered | Standard1.0/1.1 normal pass and empty scope rejection; baseline circular obstruction reproduced; old consumer rejects1.1. |
| AC-S2 | not_met | Required conditions, related ACs, product-state preservation and independent proof bindings pass; fixed artifact boundary fails F2; later aggregate path fails F1. |
| AC-S3 | covered | none/aggregate restriction and existing gate, freshness, subject/configuration, queue and failure-preservation regressions pass. No live policy/permission certification; aggregate rejection remains fail-closed. |
| AC-S4 | not_met | All repository tests and documented samples pass, but independent F1/F2 show missing integration and abnormal-file regressions. |
| AC-S5 | covered | Exact head/tree, fixed published implementation evidence and Draft PR8 on feat/readiness-prerequisite-gate verified; output delivered on separate evidence branch. No duplicate PR created. |

Coverage includes unknown versions/kinds/fields/types, duplicate IDs, missing/empty conditions and responsibilities, unknown related ACs, context mismatches, missing/tampered independent context pin, artifact absence/different bytes/size/digest/revision/unreadable directory or file/external path, Test/Review kind/subject/producer/independence/condition/artifact/unknown AC binding, CI-only substitution, all mandatory merge checks, automatic/unknown effects, single_pr, known product not_met, premature achieved, fake aggregate integration, premerge deferral and expiration. Handoff-to-Readiness identity, file, bytes and digest were exercised. Existing compatibility source files are unchanged and their baseline/head regressions pass.

A nonblank scope_reason or structurally valid permission claim is not proof of authorization. Independently trusted context and Manager examination of real scope/approvals remain required; the schema cannot determine truth. Process Test/Review ac_ids may be empty because its mandatory coverage is condition_ids and artifact_ids; unknown product AC IDs are rejected. No product AC met is inferred from process evidence. These intentional trust boundaries are not represented as cryptographic authorization checks.

## GitHub, freshness and unfinished gates

Independent public GitHub metadata observed PR8 open, draft=true, merged=false, fixed base/head, and null auto_merge. CI pull_request run 38128623164 and push run 38128597052 both completed successfully on the fixed head using .github/workflows/validate.yml. github-observations.json preserves observation times and separate five-minute metadata windows. Manager must freshly retrieve mutable PR/CI/policy state before execution; expired snapshots are not renewed by rewriting their dates.

Known rawlogsForbidden was respected: no raw log request, retry or alternate retrieval was attempted. CI metadata success does not certify per-step raw logs. GitHub required checks/reviews/ruleset/queue, actor authority, independent Review and real merge-group target were not certified here. No actual readiness assessment is fabricated without those inputs; the synthetic Readiness/Handoff pairing tests are not live MergeReady. Product integration/deploy behavior remains unverified. Issue final judgment belongs solely to Manager.

## Delivery and safety

Public output contains test reports, synthetic reproducers/results, public Git/CI metadata and pinned public source references. Private authorization, private receipts/original hashes, runtime task identifiers, private conversations, secrets and internal operational raw logs are excluded. Public alias Handoff is marked as an edited derivative in the delivery manifest; public-original comparison is not claimed. Original upstream bytes and Handoff identity/status/attempt/scope remain unchanged through fixed URL closure.

Execution attempt1 has no retry_of. Dispatch/execution/delivery each have maximum3; no self-retry, Agent launch, historical counter reset or other task budget changes occurred. No app/System implementation edits, main push, merge, auto-merge, Issue edits, deploy, secret/policy/environment changes or extra OpenAI APIs were performed.

Publication is within the standing explicit authorization for this dedicated System evidence branch after content review. Publication Receipt and fresh typed closure are transport observations, not new Consumer authorization. Manager must issue an independent bounded Consumer authorization and run baseline consume_delivery.py before downstream use. Do not advance on CI or schema success while F1/F2 remain unresolved.
