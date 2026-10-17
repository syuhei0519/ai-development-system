# Authorized Best Effort workflow trial — 2026-10-13

This later user authorization applies to **new explicitly authorized dispatch
decisions**, not the exhausted synthetic pilot, old probes, in-progress tasks,
paused backend Issue2 or automatic Knowledge launches. Historical Strict findings
remain unverified. The new trial permits unknown model/effort without treating
unknowns as execution evidence. Global rollout remains disabled; use this policy
only with an independently pinned per-dispatch approval. No task is launched by
this feature implementation. Evaluation count remains **3/6**, pilot **1/1**.

[Policy](../config/workflow-model-routing.yaml) revision `workflow-best-effort-v1`
is separate from the immutable pilot policy `bounded-read-only-v2`. Both use
strict JSON syntax within YAML filenames. Existing Handoff, Knowledge, Readiness,
Delivery and retry schemas stay unchanged. The separate private
`document_type=model_routing_record` never invents Issue AC or a formal Handoff.

| Role / explicitly bounded task | Requested model | Thinking | Service tier |
| --- | --- | --- | --- |
| Manager | Dots stays Manager; no child task | unchanged | no create arguments |
| Research/Design, Review | `gpt-6.1-sol` | `high` | `default` (Standard) |
| Implementation, Test, Knowledge | `gpt-6.1-sol` | `medium` | `default` (Standard) |
| Separate routine read-only classification, extraction or formatting consumer | `gpt-6-luna` | `low` | `default` (Standard) |
| Complex design/debug/security, exact manual approval only | `gpt-6-astra` | explicitly approved | `default` (Standard) |

Routine work uses `role=routine-consumer`, an explicitly approved bounded scope,
and one of the three routine task kinds. It must be read-only, with no app code,
security-sensitive content or live infrastructure. Do not label code fixes or
whole specialist roles as routine to get Luna. Ordinary specialist roles keep
Sol even when a task appears easy. `routine-consumer` is a routing classification,
not a new Handoff role. Manager must supply a compatible approved return contract
for auxiliary work; if an Issue/Knowledge gate applies, all existing required
inputs and its valid return role remain required. Missing contract/AC/input stays
blocked; a routing record never substitutes for that Handoff. Models and efforts are requested hypotheses;
there is no savings, comparison, benchmark or runtime enforcement claim.

Astra is a manual candidate, never automatic. Eligible roles are Research/Design,
Implementation, Test and Review. Approval must repeat exact model, effort, scope,
reason and budget; budget must fit existing remaining dispatch/execution limits.
Only `complex_design`, `complex_debug`, `complex_security` are valid reasons.
Authentication, missing input, artifact retrieval, network, environment and
approval problems are **not** model escalation causes. Solve/report those blockers
under existing contracts. No escalation creates another retry epoch or resets a
counter. Knowledge and routine consumers have no Astra route.

## Execution venue is independent of model routing

The [capability-based venue policy](single-issue.md#実行場所と必要能力) selects saved Codex Cloud by default and the specifically verified local PC environment only for actual kind cluster Test behavior. Dots remains Manager; local Kubernetes Test uses `cloud_threads.create` with that verified environment explicitly selected. The planner's model/thinking/service_tier output does not select or authorize an environment. Manager supplies the venue through the current tool schema after the existing access, target and mutation gates. Local offline/access failure is environment blocked, never a model fallback/escalation cause. Role model routes, BestEffort/Strict observation rules, approvals and all existing budgets/history remain unchanged.

## Manager's existing dispatch sequence

1. Retain the normal AC/assignment, permissions, upstream bytes, independent
   testing/review, current-head CI, Delivery and Readiness gates. Confirm the task
   is new and authorized; for an old logical scope use a new explicit redispatch
   decision against the latest unchanged business history. Never change settings
   of an in-progress task. Routing head is the pinned system checkout; app/task
   target head and its CI remain separate requirements in the task input.
2. Prepare a private routing request and approval using the
   [synthetic instructions](../examples/workflow-model-routing/README.md). Bind
   request/policy raw hashes, exact routing head and independently held current
   business retry ledger hash. Manager selects the stable logical scope and
   verifies approval provenance. This is not authorization to execute any app
   work; the current delegation leaves all app/Knowledge launches off.
3. Run the read-only planner. `BestEffort` is the trial default (explicit in input);
   `Strict` is an explicit opt-in. Planner checks approved route/scope, current
   business budget, attempt, ledger terminal state and callable create arguments.
   Only routing eligibility is evaluated: `quality_gate=not_assessed` always.
4. Manager inspects the route and all ordinary quality/approval gates, durably
   reserves dispatch intent in the **existing private progress/retry records**
   before any create, then submits emitted model/thinking/service_tier with the
   complete task input. No new reservation mechanism or runner is provided here.
   `dispatch_reserved=false` means the planner itself has reserved nothing.
   Unknown admission stops resend pending reconciliation. Existing counters,
   previous ledger pins and bounded renewal rules remain authoritative.
5. Preserve requested settings and the original approved routing record privately.
   After actual execution, append source-qualified observations with `observe`.
   Use the original approved request/history snapshot for that record; this does
   not reauthorize dispatch using an old snapshot. Each successor references the
   previous raw hash and retains all observation history. Before any later task,
   obtain a new dispatch decision and current business history pin.
6. Keep routing evidence separate from Handoff/business quality completion.
   Unknown runtime can proceed only in BestEffort, never as verified. Known
   mismatch blocks/flags Manager, with no fallback or automatic retry. A mismatch
   in history stays blocked even if a later matching observation is appended.

The planner is not an orchestrator, API client, scheduler, model probe or remote
runner. It never mutates the supplied ledgers or records. It emits JSON to stdout;
Manager persists records privately and verifies actual quality/approval/dispatch
state. It does not authenticate approval labels, UI screenshots or user identity.
Independent pins, trustworthy classification of scopes, live gates, latest state,
single Manager coordination and durable persistence are the trust boundary.
There is no global/cross-service duplicate suppression guarantee. Do not reuse
one record's create arguments for another task or execute from a blocked result.

## Observation sources and gates

Each append records nullable observed model/effort, their evidence, and separately
nullable usage. Evidence contains `source`, `binding`, `task_reference`,
`provenance` (include locator/observation time/context) and `confirmed_by`.
Source-qualified observations require `platform_metadata` or
`human_confirmed_ui`, binding `execution_task`, the exact private task reference,
and nonempty provenance/confirmer. Human UI confirmation is not invented server
metadata. Manager must verify that the evidence shows that execution, including
rerouting; code checks consistency and cannot prove that the UI claim is true.

UI selectors/settings, aggregate UI usage, request values and model self-report
are retained as unverified claims in `observation_history`. They are never copied
into observed model/effort or measured usage. A user's statement that usage/model
is visible in UI is not evidence binding a particular execution. Missing values
remain null; unknown usage is never zero-filled or inferred from pricing. Genuine
measured zeros require qualified per-task evidence. Observation history is bounded
to 32 entries and local JSON inputs to 64 KiB; no telemetry is collected.

BestEffort with unknowns returns `allowed_unverified`; matching model/effort may
return `allowed_verified` while `usage_status=unverified` remains separate. Strict
blocks missing qualified model, effort **or usage**. Known mismatch blocks both
modes. Manager emits no Cloud arguments. Schema/approval/budget errors block.
Exit 0 means routing consistency/eligibility, not task execution or quality pass;
exit 1 is blocked; exit 2 is an argument error. No ordinary gate is relaxed.

## Historical pilot remains consumed

The one-shot pilot completed with `PINNED_ARTIFACT_UNAVAILABLE`; deterministic
validation rejected its non-classification output. Admission was confirmed,
observed model/effort/usage remain unavailable. Root cause beyond that reported
error is unknown; it is not established model-quality failure or an escalation
reason. The original marker remains consumed at one launch. Private approval,
reservation, receipt and result bytes are untouched; no new budget is inferred.
Old `model_routing.py` and its policy/pins remain unchanged for historical replay,
not authorization to reserve again. The workflow planner rejects the old pilot ID
and scope and cannot consume its state as a business retry ledger.

PR10's two Markdown records are retained byte-for-byte as historical prefixes in
PR11, with dated later status sections. Their original Strict gates, observations
and validation results are not rewritten. Manager may close PR10 only after remote
retention verification; this implementation closes or merges neither PR.
