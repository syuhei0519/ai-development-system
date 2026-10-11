# Independent Review attempt1 — System PR8

Result: **completed; no blocking findings** for base `0083151aa2f6b2aaf0e1db64ada3f196ed766e48` → head `cdaad5a0d7437a9abc24481e4849b89a9e112401`, tree `bd6db38a828be65062b7cf0bd8044765190b0cc1`.
Role review, public alias readiness-prerequisite-review-a1, scope ai-development-system#readiness-prerequisite-support. This is an independent code/contract/evidence review, not GitHub required approval, live Readiness, product acceptance or permission to merge. No final_assessment is issued.

## Governing scope and provenance

Read the fixed baseline workflow, contract index, Handoff2 schema, Delivery1.2 and its parent contract, Readiness1.0, IssueCompletion1.0, task-input template and supplied review role. No AGENTS.md exists in the target baseline tree or workspace ancestors. Readiness1.1/IssueCompletion1.1 are proposed subjects of this review, not already adopted policy. No separate Research Handoff or Knowledge context was supplied or inferred. AC-S1–S5 are Manager-defined System conditions, preserved verbatim in Handoff; they are not a fetched GitHub Issue body or backend-app product ACs.

Canonical baseline consume_delivery.py freshly fetched and verified 112 artifacts / 95 structural slots / 2,540,030 bytes from isolated Git using the independently supplied bounded authorization. All raw size/hash/type/source/upstream/retry bindings passed. Input Handoff pin and fixed source head/tree match. No tree/candidate bindings are declared in this closure; their nonexistent coverage is not claimed. The Consumer output, not unverified downloaded prose, was used. Authorization and private Consumption Receipt are excluded from publication. Public derivative inspection does not establish equality with any unavailable private original.

Read Implementation1/2 design and reports, Test1 F1/F2, interrupted Test2, Test3 report/results/harness provenance, the complete 29-file baseline-to-head diff, current validators, all added regressions and sample changes. Compared new aggregate schemas in full against their retained 1.0 schemas: assessment differs only in explicit version identity; context adds typed required members. Reviewed original and derivative harness code. Test1 failed and Test2 blocked remain unchanged. Test3 completed is independent upstream evidence; the new executions below are separately observed Review evidence.

## Contract and code assessment

- **AC-S1:** readiness schema version branches preserve nonempty ordinary PR product scope in 1.0 and standard1.1. Only explicit preparation1.1 has empty product scope. Unknown/mixed versions and old Consumers reject new forms. Existing ordinary gates and original tests are retained.
- **AC-S2:** preparation context fixes nonempty conditions, related product ACs, artifacts and per-related-AC followup. Whole context/subject/config/preparation comparison, condition/result identity sets, raw bytes/size/digest/target revision and independent Test/Review producer/condition/artifact coverage are enforced. All original product outcomes remain separately pinned; any known product not_met blocks preparation merge. Product phase and deferral rules remain unchanged. Process completion cannot produce product met or Issue achieved. Nonblank text/pins alone cannot establish truth or authentication; Manager must verify real scope, independence and authorization.
- **AC-S3:** preparation is schema-limited to none + aggregate_required. Implementation, deployment and merge readiness stay distinct. CI, independent Test, AI Review, GitHub checks/reviews/ruleset/queue, authorization/dependencies and all freshness checks remain. Aggregate1.1 keeps preparation in required/current/result sets, merge permissions, historical gates, dependency ordering, merge binding and full merged vector. Only measurement_coverage targets the nonempty standard-member set. All required product subchecks and required deployments, source/config/image/environment/workload checks remain. Preparation cannot be a product verification target or achieve alone. Historical kind, related originals/phase and scope are checked; latest previous pin, failure latch and append-only history checks remain. Manager still owns completeness of the required set and scope changes not retained in old assessments.
- **AC-S4:** JSON schemas, CLI behavior, samples, roles, README, workflow and task template describe the same explicit boundary. Handoff2, Knowledge, Delivery and legacy IssueCompletion schema bytes are unchanged. Tests below pass. Source helper/fixture behavior is distinguished from real product observations.
- **AC-S5:** fixed Git source and verified upstream bytes are available; live metadata confirms the existing System feature branch feat/readiness-prerequisite-gate and open Draft PR8 at the assigned base/head. This review creates no PR. New output preserves upstream closure and uses only the dedicated evidence branch/prefix.

Useful code locations at the reviewed head: scripts/validate_readiness.py:59 (context binding), :160 (preparation), :232 (readiness derivation), :315 (CLI context pin); scripts/validate_issue_completion.py:188 (typed required set), :255 (historical preparation/artifact binding), :302 (full merge/deployment vectors), :415 (integration coverage), :439 (history), :534 (final reread); scripts/regular_file.py:17 (reader).

## F1/F2 and harness review

F1 is repaired by typed IssueCompletion1.1 membership rather than dropping preparation, assigning related ACs as product scope, or weakening standard1.0. The aggregate pins complete artifact refs in its independent context; each ref resolves to the historical Readiness parent plus original locator, with exact ID set/bytes/size/digest. Historical validation receives that materialized root; Bundle caches the artifact and rereads it before success. Subsequent standard measurements and all required integration remain necessary.

F2 uses no-follow descriptor-relative ancestor traversal and O_PATH to pin/type-check the leaf before any data open. It reopens the verified regular inode through Linux /proc/self/fd, limits reads to declared bound+1 and hard16 MiB, and checks inode/mode/size/mtime/ctime plus original leaf/ancestor identity. FIFO/device/socket/directory/symlink, growth/replacement/same-size mutation and unsafe locators reject in exercised cases. Missing Linux capabilities fail closed; no new OS support is requested.

The original aggregate reproducer still exits1 on new head because it constructs old untyped empty-scope input and expects missing-root/related-as-product substitutions to pass. Keeping those inputs rejected is correct. The explicit v2 derivative adds typed1.1/artifact mapping and removes preparation from product measurement targets while retaining all merged dependencies. Its missing-root and related-as-scope expectations correctly reject. The original FIFO writer expects a reader to open the pipe and raises when the fixed reader exits first; v2 allows that early rejection without weakening the nonzero validator requirement. Original raw outcomes remain retained, separately from v2 results.

Test3's first overlay correction only renames a colliding synthetic directory. Its second correction replaces actual source/image arrays instead of mutating shared expected/actual fixture objects. The intended mismatch and rejection expectation are unchanged; the corrected tests create a real mismatch. No product defect was discarded, and intermediate variants/results remain in upstream provenance.

## Fresh Review executions

See measurements.json for commands, raw synthetic outputs, actual checkout revisions, script hashes and result rows.

| Execution | Observed result |
| --- | --- |
| Baseline full unittest discovery | 280, OK |
| Head full unittest discovery | 309, OK |
| Unchanged original independent overlay | 237/237, exit0 |
| Unchanged sample overlay | 26 checks, no failures, exit0 |
| Original F1/F2 on old head | Both failures reproduced, exit1 |
| Original F1/F2 on new head | Expected obsolete-harness outcomes retained, exit1 |
| Published v2 F1/F2 on new head | Both exit0; typed path succeeds and unsafe inputs reject |
| Unchanged Test3 additional overlay | 163/163, exit0 (116 behavioral / 28 schema / 19 byte-compatibility checks) |
| Generated preparation aggregate example | ready/achieved synthetic replay only |
| Full diff whitespace and exact tree | Passed / matched |

The full 309 includes all 280 baseline methods plus 29 added methods; subsets are not added again. Original overlay output hardcodes old head labels and the sample script hardcodes old comparison refs; actual checkout revisions in the runner and current-head byte/diff checks control interpretation. The first Review runner invocation failed because its output directory was absent, before saving its first child result. That harness setup failure is disclosed; creating the directory and executing the same unchanged runner was within this one Review attempt, not a task restart, implementation fix or history rewrite.

## Operational scope, limits and remaining gates

The entire diff is contract/validator/test/example/documentation work. It does not change app charts/workload values, deployment configuration or existing GitHub workflows, and introduces no external deployment, permissions, Secret/Ruleset/Environment changes, scheduled job, Agent launcher or extra OpenAI API. This is a code-diff observation, not verification that every external integration setting is absent. Owner/Manager confirmation of external deployment wiring remains separate.

Authoritative public CI metadata reports run38130204297, pull_request event, workflow .github/workflows/validate.yml, exact head cdaad5a..., completed/success. No forbidden raw logs were requested, retried or fetched; historical checkout contents and per-step logs are not certified. Fresh independent fixed-head execution is a different proof. GitHub PR/CI observations have five-minute windows in measurements.json. Manager must reacquire mutable PR/CI/protection/review/queue/actor facts immediately before any action. Manager's earlier policy observations are not represented as this Review's live measurements; absence of configured protection is not treated as a bypass.

Finite synthetic tests do not prove all interleavings or evidence truth. O_PATH/proc require trusted Linux/kernel facilities; no guarantee covers a stalled filesystem/kernel or hostile writers after validation returns. Pin and retain materialization; revalidate after change. Standalone legacy JSON entrypoints were not generally redesigned; the bounded reader addresses fixed preparation artifacts and aggregate files. CLI success is record consistency and cannot authenticate a caller-supplied pin, independently establish producer identity, grant consumer use, or replace required GitHub approvals.

pins.json gives this fixed review's completion time and 24-hour expiry. Head/base/relevant configuration changes or a new failing result invalidate it immediately. No timestamp rewrite renews prior evidence. All System conditions are assessed at their earliest premerge review/test stage; no artificial postdeploy deferral is used. This result cannot by itself authorize SystemPR8 or M0PR18 merge, backend-app product success, deployment, or final Issue completion. Formal Readiness construction remains Manager work after this review.

## Delivery and safety

Handoff2 upstream is Test3 attempt3 and Implementation2 attempt2, both dependency; no retry_of. Dispatch/execution/delivery budgets remain at most3 and all earlier histories/terminal states remain intact. No other Agent or self-task retry was launched. No implementation edit, main push, merge/auto-merge, PR review/comment, Issue edit or deployment occurred.

Publication is covered by the standing owner authorization for System evidence after safety review. Only report, compact synthetic measurements, fixed pins, public alias Handoff and public transport observations are included. Private authorization, private receipt/original/hash, runtime identifiers, conversations, credentials and internal operational logs are excluded. Existing upstream documents are reused byte-for-byte at their original fixed references. Publication Receipt and fresh typed-closure observation grant no new Consumer authority; Manager must supply its own bounded approval and canonical fresh consumption before downstream use.
