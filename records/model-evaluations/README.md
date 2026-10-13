# Model routing evaluation records

This directory holds human-readable findings and proposals. It is not an
executable routing policy, a model enforcement mechanism, or a replacement for
the existing role definitions, workflow, contracts, defaults, and quality gates.

| Record | Status | Operational consequence |
| --- | --- | --- |
| [2026-10-13 findings and proposal](2026-10-13-model-routing-findings.md) | Step 1 UNVERIFIED; routing hypothesis UNVALIDATED | Steps 2 and 3 gated off; documentation-only delivery |

Records distinguish requested settings from independently observed runtime
settings. Request admission, model self-report, file integrity, and task
completion cannot establish actual runtime model or reasoning effort. Unknown
usage remains unknown; API prices cannot stand in for subscription usage.

Keep public records limited to safe summaries, synthetic probe labels, public
file integrity, and evaluation counts. Actual Cloud thread/turn/message IDs,
private task URLs, account/usage details, internal logs, credentials, and full
original task prompts belong outside this public directory.

Follow the existing [workflow](../../workflows/single-issue.md),
[handoff definitions](../../contracts/README.md), and
[delivery contract](../../contracts/artifact-delivery.md). Publishing a proposal
does not approve its operational use or permit implementation, merge, deployment,
new evaluations, or a reset of business attempt history.


## 2026-10-13 later authorization and consolidated status

The original bytes above are retained from PR10 head
`efa929fb82b11df46fba4215f51c4f101d6b6c99`; observations, Strict gates and results
are historical, not rewritten. PR11 is the single consolidation destination.
The original Step 1 remains UNVERIFIED: later authorization does not prove that
Strict runtime evidence, comparative quality or savings gates passed.

A separately authorized one-shot Best Effort pilot was admitted and completed
with `PINNED_ARTIFACT_UNAVAILABLE`. Its output contained no classification; the
deterministic validator rejected it. Observed model/effort/usage remain unknown.
Root cause beyond that reported error is unknown, not established model-quality
failure. Pilot launch budget is consumed **1/1** and evaluation count is **3/6**;
neither this consolidation nor new routing authorizes another pilot or benchmark.

The user later authorized a new Best Effort workflow trial for explicitly approved
new specialist dispatch decisions, separately from the consumed pilot. See
[workflow integration](../../workflows/workflow-model-routing.md): Manager stays
Dots; Research/Design and Review request Sol High; Implementation/Test/Knowledge
request Sol Medium; only separate routine read-only classification/extraction/
formatting consumers may request Luna Low. Standard uses wire `default`. Astra
is a manual candidate requiring exact scope/model/effort/budget approval, never
automatic. Authentication/input/delivery/network/environment/approval problems
are not escalation causes.

Best Effort can record unknown model/effort without blocking this approved new
trial; Strict opt-in still blocks unknowns. Qualified mismatches block/flag Manager
and never cause silent fallback. Human UI evidence needs actual execution binding
and provenance; selectors/settings and aggregate usage are not per-task proof.
Unknown usage stays null and no savings/comparison claim is made.

All Handoff/AC, independent Test/Review, current-head CI, Delivery, security,
approval, Readiness and business retry gates remain unchanged. Existing histories
and private pilot bytes stay untouched. No task, Astra, Knowledge or app execution
is launched by this workflow feature; paused backend Issue2 stays paused.
Independent Review of the updated PR11 head remains required. Manager may close
PR10 after its historical contents are verified remotely in PR11; implementation
does not close or merge PRs. No formal Issue-wide achieved/Handoff is invented.
