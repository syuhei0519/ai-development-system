# Aggregate Issue Completion implementation report

Implementation scope: system/issue-completion/aggregate. Attempt 1. Implementation and assigned validation completed; independent Test/Review and Manager decisions remain separate.

Fixed base: df400018057735b7cb6a9c6ea4619508f0e6ba3a.
Fixed feature head: 591f896d30fde5630d49f99a4ea7544ff90f53a4.
Branch: feat/aggregate-issue-completion.
Draft PR: https://github.com/syuhei0519/ai-development-system/pull/5 (OPEN, draft=true, auto-merge disabled).
Remote feature head equals the fixed head. Main remained at the fixed base at final verification. No parallel branch was modified or integrated.

## Implementation and AC mapping

- AG-1: independent Issue Completion schema/context/CLI; unchanged Readiness v1 aggregate_required prohibition and Handoff v2 semantics. PR success never implies aggregate achieved.
- AG-2: closed schemas, strict JSON, independently pinned current context, exact required sets/AC originals/subchecks, dependencies, approval kinds/scopes/actors, actual merge result mapping, sources/config/image/environment/workload and time windows. Missing or contradictory evidence fails closed.
- AG-3: historical PR gates replay at actual merge time, current AC evidence remains currently valid. All required measured checks and integrations are needed. Only Manager final Handoff can assert achieved; no operation authority is granted.
- AG-4: pinned previous assessment, append-only events, head/set/deployment change events, current failure/rollback/revert handling. Previous not_achieved is conservatively retained until explicit revalidation and fresh successful measurements; expiration cannot erase failure.
- AG-5: separate Issue Handoff and PR Readiness pairing, same local identity/raw SHA-256 bindings and measurement-source correspondence; schemas, CLI, tests, samples, roles, template, docs and existing CI job updated. Legacy schema/validators unchanged.

## Technical choices within approved design

Added target/config/merge-group and operation actor fields to current snapshots to prevent comparison gaps. Verification/evidence include workload, method, expected result and producer. Structured source observation bytes must match evidence metadata; arbitrary text/receipt cannot substitute. The validator checks consistency, not the truth or independence of external observations. Manager verifies original scope completeness, provenance and live GitHub requirements.

All refs use the assessment directory as bundle root; Handoff locators retain Handoff-relative semantics. Historical scope approvals are conservatively required to remain valid in the current scope snapshot. A prior failure remains not_achieved even across a new configuration until repair/revalidation requirements pass. These conservative choices and limitations are documented in contracts/issue-completion.md.

## Boundaries and outstanding gates

No merge, auto-merge, application repository edit, deployment, Issue close, paid API, Secret or ruleset change. Independent Test/Review was not launched. This implementation's own validation is not independent Test/Review. Product Order3 AC and product Issue completion remain unverified; no product deployment approval or Issue 2 achievement is asserted.

The operational Handoff/report public-alias candidate is sealed separately and is not published or delivered through Git. Public feature code/docs/synthetic fixtures were authorized and pushed. Separate Manager delivery instructions are required for this candidate. No implementation blocker remains; independent review, later integration and merge decisions remain with Manager.
