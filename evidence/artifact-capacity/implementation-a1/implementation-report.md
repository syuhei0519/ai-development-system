# Bounded Artifact Delivery Capacity — Implementation attempt 1

Issue: ai-development-system/artifact-capacity. Assignment: system-artifact-capacity.
Implementation epoch 1 attempt 1. Dispatch/execution/delivery budgets remain 3 each.
This independent System contract change does not relabel or reset any application
attempt, B2 history, terminal state or past delivery.

Base: `4693887fa79c2b4a291c555b8bd27b6903eb4199`. Exact implementation head: `4e38376404d9486daae93829735f11166a01e062`.
Draft PR: https://github.com/syuhei0519/ai-development-system/pull/9
Feature branch: feat/bounded-artifact-capacity. Draft/open and base/head were
read back from GitHub. No merge/auto-merge performed. Both push and PR CI succeeded on the exact head (see ci-observation.json).
Independent Test/Review
remains pending. Issue final_assessment and Merge Ready are not claimed.

## Change and reason

Delivery 1.3 adds an explicit finite 256-artifact bound in manifest/publication/
consumption schemas with matching authorization version selection. The Consumer
and preparation CLI select the same bound; preparation defaults to 1.2 and accepts
`--delivery-version 1.3` explicitly. Four separate schema files retain the existing
self-contained versioned schema convention. Regressions assert their exact delta.

In-place modification of released 1.2 was rejected because old/new validators
would disagree on the same labelled document. Legacy 1.0/1.1/1.2 retain 128 and
remain accepted by the updated Consumer. Old Consumers reject 1.3. Never relabel
historical records; new records need new independent authorization pins. Original
artifact bytes, immutable references and complete closure are preserved.

All other fail-closed limits remain: 16 MiB/file, 64 MiB total including tree
members, 4096 structural slots, 128 Knowledge/candidate bindings and candidate
source/ID counts, 4096 tree entries, 1024 descendant trees, raw tree and safe path
bounds, regular object types, full fixed commit/SHA/size, strict JSON/Handoff,
representation and separate publication/Consumer approvals. Retry policy unchanged.

## AC mapping (Implementation scope)

- AC-C1: offline fixture consumes legacy 128 with existing prior/current Handoffs
  and commit object, preserves all bytes, adds a dependent Handoff at 129, and
  consumes 256 through normal Consumer/receipt/output logic. No B2 payload copied
  or executed. Fixed blocker manifest metadata alone was inspected and pinned.
- AC-C2: opt-in 1.3 comparison and exact schema-delta test; unchanged byte/tree/
  slot/type/auth defenses and legacy profiles. See candidate-profile.json.
- AC-C3: full 356 tests passed in 92.409 seconds, including 47 new-version cases;
  eight additional CI commands passed. See test-results.json for measured commands,
  boundary cases and limitations. Synthetic transport is network-independent.
- AC-C4: README, contract index, original delivery/cross-reference contracts,
  new capacity contract, template, example instructions and workflow wording now
  describe finite capacity/compatibility/operations. CI automatically discovers
  the new tests and checks all 1.3 schemas. Old delivered evidence is untouched.

## Handoff and operating boundaries

The implementation code is in the feature commit and complete implementation.patch;
four candidate schema byte copies are also included for review. Candidate schemas
are data, not a trust-root update. The small evidence bundle uses known canonical
Delivery 1.2 at the fixed base. New output directories are required for preparation
and postpush fresh validation. Authorization bytes and real runtime identities
remain private; public task identifiers are purpose-made aliases, not runtime IDs.
Original/derived representations, public safety, publication authorization and
Consumer-use authorization remain separate. Manager must independently authorize
subsequent Consumers; a Producer self-check receipt cannot do so.

The role, workflow, Handoff2.0, Readiness1.1 and Delivery1.2 canonical instructions
were read. No AGENTS.md or SKILL.md exists in the target checkout; workspace ancestor
AGENTS and the available local .agents directory supplied no additional files.
Changes are confined to this System repository's 18 files. No backend-app,
application-manifest or platform-gitops code, API, billing, Secret, permission or
Ruleset change occurred. Deployment effect is none: the only GitHub workflow runs
contract/test validation, with contents:read, and has no deployment job.

## Risks and remaining gates

1. Consumers must intentionally upgrade to approved 1.3; old 1.2 rejects 129+.
2. 256 entries still do not guarantee fitting byte or slot bounds. Exceeding any
   bound must fail and return to Manager without deleting closure or history.
3. Schema copies add maintenance surface; exact-delta/limit agreement regressions
   constrain unintended divergence.
4. Git fetch pack totals remain environment-bounded as before; this work changes
   neither network/disk enforcement nor source truth/authorization authenticity.
5. Independent Test/Review, same-head CI result and Manager's final readiness/
   integration assessment remain separate. Implementation self-tests do not grant
   merge, application restart, deployment or product acceptance.
