# synthetic sample: Test retry initial input

Every ID, revision and source here is fictional. This illustrates the complete initial bundle of a **new independent task**, not a message appended to the blocked task.

- Role: test. Attach `agents/test.md`, `contracts/handoff.schema.json`, `contracts/README.md`, and `workflows/single-issue.md` from the same checkout revision.
- Task: SYNTHETIC-TASK-TEST-002, attempt 2, scope: test-plan review of the fictional label design.
- Issue: SYNTHETIC-ISSUE-001 — synthetic sample: non-blank label contract.
- Authorized source placeholder: https://example.invalid/issues/SYNTHETIC-ISSUE-001#ac-1
- Mandatory AC original, SYNTHETIC-AC-1: **A label must contain at least one non-whitespace character.**
- AC completeness: fictional Manager supplied the sole AC original from the authorized source. This is an illustrative premise, not a real retrieval claim.
- Research upstream: SYNTHETIC-TASK-RESEARCH-001, attempt 1, dependency, SYNTHETIC-REVISION-1.
- Retry upstream: SYNTHETIC-TASK-TEST-001, attempt 1, retry_of, SYNTHETIC-REVISION-1.
- assignment.ac_ids: [SYNTHETIC-AC-1]. assignment.scope: test-plan review only. assignment.completion_criteria: compare all proposed cases to the assigned AC and record limitations.
- Deliverable: compare the proposed matrix to the AC and report scope and limitations. No implementation or product-test success may be claimed.
- Permission: read attached synthetic documents; write a local report and handoff. No GitHub writes or external AC lookup.
- Environment: existing authorized Cloud sandbox; no new credentials/services.
- Completion: all proposed cases evaluated against the supplied AC within plan-review scope; missing implementation execution explicitly noted.
- Return: Manager-readable attachments `test-plan-review.md` and `test.handoff.json`.

## Required attachments, retrieved by Manager before launch

- `research.handoff.json` (full JSON)
- `test.blocked.handoff.json` (full JSON)
- `design.md` (full document, including proposed cases)

All files are in this directory. In a real dispatch, the Manager must attach their actual bytes or copy their content into the initial input, replace placeholder revisions with verified immutable references, and ensure the new task can read them. Listing these paths alone does not constitute delivery.

## Correction and limitations

The prior fictional Test task was blocked because its initial input lacked the AC original. Manager re-dispatches the original above and the retrieved artifacts; Test does not recover it from design text or external lookup. Research completion covers design only. Unicode/runtime behavior and implementation acceptance remain unverified.
