# Implementation attempt 2 — System PR 8

Status: completed for the assigned implementation work; independent Test/Review pending.
Public alias: readiness-prerequisite-implementation-a2. Scope: ai-development-system#readiness-prerequisite-support.
No final_assessment or live Merge Ready is issued. Implementation1 completed and Test1 failed remain unchanged.

## Fixed subject and inputs

Repository: syuhei0519/ai-development-system. Existing Draft PR: https://github.com/syuhei0519/ai-development-system/pull/8.
Base: 0083151aa2f6b2aaf0e1db64ada3f196ed766e48.
Starting head: 3f41a0470fd0b7a2199be0b947bb22284e993e2f.
New head/target: cdaad5a0d7437a9abc24481e4849b89a9e112401.
Tree: bd6db38a828be65062b7cf0bd8044765190b0cc1.
Branch: feat/readiness-prerequisite-gate. One additional commit; no duplicate PR.

Baseline workflow, contracts README, Handoff2, Delivery1.2, Readiness1.0, Issue Completion,
input template and implementation role were read. No applicable AGENTS.md or repository SKILL.md
was found. The proposed Readiness1.1 is the subject, not an adopted governing baseline.
Manager-defined AC-S1–S5 and assignment were copied from the verified input, unchanged.
No Knowledge context or additional agent was used.

Baseline consume_delivery.py freshly fetched and verified the independently pinned Manager authorization,
46 artifacts, 46 structural slots and 778424 payload bytes from isolated Git (exit 0).
Input manifest and publication pins matched; the private authorization and Consumption Receipt are excluded.
The original Test1 report, reproducers and Implementation1 Handoff were consumed only after verification.
Public edited derivatives do not prove comparison with private originals.

## F1 repair and rationale

Issue Completion assessment/context 1.1 use explicitly versioned schemas. Version1.0 schemas are unchanged;
ordinary1.0 records remain supported and old Consumers reject1.1. Versions must match, including no unknown versions.
A 1.1 required member declares pr_kind and preparation. Standard requires nonempty product ac_ids and null preparation.
Preparation requires empty product ac_ids, nonempty related_ac_ids and a complete artifact_refs set.
Historical kind, empty scope, related IDs and their original text/source/earliest phase are checked.

Historical Readiness remains responsible for none + aggregate_required, process conditions, independent Test/Review,
fixed target revisions, followup responsibilities, product outcomes, freshness, permissions and all merge gates.
Each artifact_ref is pinned in the independently pinned aggregate context. Its safe bundle path must be the
historical Readiness file's parent plus the original artifact locator, and its bytes/size/SHA-256 must match.
The aggregate reader retains all these files for final rereading before success.

Preparation remains in every required/current/result collection, dependency graph, merge authorization,
merge binding and full merge vector. All integration checks retain the complete set except product
measurement_coverage, which requires the nonempty standard-member set and all product AC/subcheck measurements.
A preparation member cannot serve as a product measurement target. All required deployments and source/config/image/
environment/workload checks remain mandatory. Preparation alone cannot achieve Issue Completion.

Rejected: simply lowering minItems; copying related ACs into product scope; omitting the required preparation PR;
accepting missing artifact roots; asserting process success as product met; forcing all existing records to1.1.
These alternatives either weaken the scope boundary or break existing inputs unnecessarily.

## F2 repair and limits

A shared Linux regular-file reader traverses directories with descriptor-relative O_NOFOLLOW.
Before any data I/O, O_PATH pins an inode and fstat verifies the ordinary-file type and size.
Only a verified regular inode is reopened via the kernel descriptor link in /proc/self/fd.
Reads are bounded by the declared size and a hard16 MiB ceiling. The descriptor, original directory entry,
size, inode, mtime/ctime and ancestor identities are checked around the read.
FIFO/device/socket/directory/symlink, including symlink ancestors, are rejected. Replacement between stat/open,
during read, ancestor replacement, growth and same-size mutation have deterministic regressions.
Aggregate Bundle also uses this reader; digest checks and final all-file rechecks remain.

This requires Linux O_PATH and /proc/self/fd; unsupported platforms do not gain a weaker fallback.
It is not a sandbox against a hostile writer after validation or a timeout for an unresponsive filesystem/kernel.
Manager must preserve the verified materialization and pins and revalidate after any change.
Scope declarations, approval text and schema validity do not prove authorization or evidence truth.

## Executed self-verification

| Measurement | Result |
| --- | --- |
| Original Test1 aggregate reproducer on starting head | Existing standard control passes; preparation path fails as reported |
| Original Test1 FIFO reproducer on starting head | Matching55-byte pipe accepted: reproduced F2 |
| Original independent_cases.py on starting head | 236/237; writer-less FIFO timeout reproduced |
| Final python -m unittest discover -s tests -v | 309 tests OK: prior292 plus17 regressions |
| Original independent_cases.py on final source | 237/237 expected, including prompt FIFO rejection |
| Original sample_checks.py on final source | 26 checks, no failures |
| Edited aggregate_reproducer_v2.py | Standard control, direct preparation, typed1.1 preparation→product→integration pass; missing root and related-as-product rejected |
| Edited fifo_reproducer_v2.py | Immediate exit1, no reader-side FIFO open required |
| New generated preparation example | ready/achieved synthetic replay with separate product measurements and all required merges/deployment |
| All contract schemas / delivery records / git diff --check | Pass |

Original reproducers were rerun unchanged after repair, and those results remain separate.
The original aggregate script still returns1: it constructs untyped1.0 empty-scope input, omits the root in a direct
call, and expects related-as-product scope to pass. Accepting these would violate the requested boundary.
The original FIFO harness raises 'reader did not open synthetic FIFO' after the repaired reader exits early;
it assumed the faulty reader would open the pipe. fifo-original-after.txt retains that outcome with a public path alias.
The small edited derivatives support the new explicit input format and early fail-closed behavior. Original input bytes
remain in the fixed upstream closure; no upstream report/status was changed.

Test1 scripts hardcode their old head in emitted JSON. The after-run subject is the checkout argument pinned in
revision.json, not that stale label. This limitation is disclosed rather than rewriting original script output.
All after runs here are Implementation self-verification, even when executing code authored by independent Test1.
The previous independent failure is not converted into a passing independent result.

New regressions cover valid1.1 standard/legacy compatibility, complete preparation flow, nested materialization,
missing/duplicate/wrong artifact sets and root/digest/size, unknown/changed related originals, kind/version/scope mismatch,
preparation-only completion, missing/unmerged required members, false product target/stage, missing or failed measurement,
failed deployment, expiry, Ruleset failure and none restriction. Existing historical/failure/approval tests remain.

Reproduce from the fixed feature commit:

```sh
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
python examples/issue-completion/preparation-example.py /tmp/fresh-synthetic-preparation
python aggregate_reproducer_v2.py CHECKOUT aggregate-after.json
python fifo_reproducer_v2.py CHECKOUT fifo-after.json
# Obtain the original scripts through the verified upstream closure:
python independent_cases.py CHECKOUT BASELINE_CHECKOUT independent-after.json
python sample_checks.py CHECKOUT sample-results.json
```

## Delivery and remaining gates

Feature push is verified; PR8 is open, Draft and unmerged at the fixed base/new head.
GitHub pull_request CI run38130204297 succeeded for the queried new head. Only metadata was requested;
no forbidden raw logs were requested, retried or obtained. CI is distinct from independent Test/Review and live policy checks.
Manager must freshly confirm mutable PR/CI/Ruleset/check/review/queue/actor conditions before any future action.
Measurements bind this head/tree/config; source/config changes or new failures invalidate their applicability.

Public contents were inspected: source changes, synthetic tests/results, public Git/CI metadata and fixed upstream
public references only. Private authorizations, private originals/hashes, runtime identifiers, conversations,
internal operational logs and secrets are excluded. Publication uses the existing owner authorization for this
System evidence branch. A Publication Receipt is transport evidence, not Consumer authorization.
Manager must issue a separate bounded Consumer authorization and freshly run baseline consume_delivery.py before use.

Attempt2 retains Implementation1 retry_of and Test1 dependency. Dispatch/execution/delivery maxima remain3,
with no counter reset, self-retry or agent launch. No other repository, product Issue, deployment, merge, auto-merge,
main push, Secrets, environment/permission/Ruleset change, Knowledge schedule or additional OpenAI API was performed.
New-head independent Test and Review remain pending; final Issue judgment belongs to Manager.
