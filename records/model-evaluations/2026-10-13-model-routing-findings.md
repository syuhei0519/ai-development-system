# Model Routing Optimization: findings and unvalidated proposal

Date: 2026-10-13. Repository: `syuhei0519/ai-development-system`.
Fixed source revision: `018973d2aceb672116cb3d8b80bc0f863a26d1d7`.

**Step 1 is UNVERIFIED. Steps 2 and 3 are gated off.** The owner required
operational application to stop when model enforcement cannot be verified,
allowing only proposals and verification results to be saved. This record is
that documentation-only fallback. It does not implement routing or establish
that any requested model or effort actually executed.

## Evidence and limits

The following probe observations were supplied by Manager after two independent
read-only Cloud probes. This documentation assignment did not repeat them or
perform a model evaluation. Probe A and Probe B are synthetic public labels;
the original prompts and runtime identifiers are not published.

The observed `cloud_threads.create` interface accepted `model`, `thinking`, and
`service_tier`. Both probes were admitted with identical prompts and the fixed
source revision. Both completed a raw-byte fetch and summary of
[`agents/manager.md`](https://github.com/syuhei0519/ai-development-system/blob/018973d2aceb672116cb3d8b80bc0f863a26d1d7/agents/manager.md).

| Synthetic label | Requested model | Requested effort (`thinking`) | Requested tier | Observed runtime model | Observed runtime effort |
| --- | --- | --- | --- | --- | --- |
| Probe A | `gpt-6.1-sol` | `medium` | Standard | unavailable / unverified | unavailable / unverified |
| Probe B | `gpt-6-luna` | `low` | Standard | unavailable / unverified | unavailable / unverified |

Both reported the same public file integrity:

- Byte length: `7822`.
- SHA-256: `ae76f99d4994f3af2cdf860c2321292435fd4f349cc62cbc39d1de89275d148b`.
- Git blob SHA: `5dc79007a5ee585dda0635dc9406f686922f3210`.

Manager independently verified the connector bytes and Git blob. The
documentation agent also checked the fixed Git blob's size and SHA-256 locally.
These checks establish public source-byte integrity only. They do not establish
runtime model selection, effort, relative quality, or efficiency.

The current read tool exposed outcomes/messages, without actual model, effort,
or usage. Manager found no supported mapping to per-turn runtime evidence for
these probes. Admission and model self-report are not execution evidence.
Tokens, allowance/credits, and exact runtime duration were unavailable. No
numerical usage or savings estimate is justified, and API prices must not
substitute for subscription usage.

Manager's interface inspection found that an omitted model follows the selected
desktop's saved model when applicable, otherwise the default child-task model,
then the first visible catalog model. Omitted effort follows matching desktop
saved effort or the model default. These are inspected request-resolution
rules, not verified execution metadata. Exact hosted defaults remain unknown.

In one probe, `/home/agent/.codex/config.toml` existed without `model`,
`model_reasoning_effort`, or `reasoning_effort` keys, and
`/workspace/.codex/config.toml` was absent. The other checked only the workspace
path. Those limited observations prove neither Cloud configuration enforcement
nor non-enforcement. No configuration was changed for this documentation task.

Evaluation budget used: **2 of 6**, with no retries and no Astra evaluation.
The remaining budget is unused, not authorization to proceed. There was no
Step 2 comparison, performance ranking, or established efficiency or quality
conclusion. Documentation validation is separate from that evaluation budget.

## Official documentation and applicability

The linked official pages were checked for this record on 2026-10-13:

- [Workspace model availability](https://learn.chatgpt.com/docs/enterprise/workspace-model-availability)
  states that Codex Cloud's default model cannot be changed. That default-model
  limitation is distinct from the inspected per-task request support; neither
  establishes which model executed these probes.
- [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
  describes prepared filesystems and saved task state.
  [Developer settings](https://learn.chatgpt.com/docs/developer-settings)
  describes app, CLI, and IDE settings and configuration files. Our reading of
  these pages does not establish saved-environment model/effort enforcement for
  these Cloud turns.
- [Codex App Server](https://learn.chatgpt.com/docs/app-server) documents
  `model/rerouted` and `thread/tokenUsage/updated` events on that surface.
  No supported mapping from those events to these Cloud probes was found.
  Their existence is not evidence that this Cloud read tool exposes them.
- [Pricing](https://learn.chatgpt.com/docs/pricing) and
  [Usage Insights](https://learn.chatgpt.com/docs/enterprise/usage-insights)
  provide usage context, not measured consumption for these probes. No private
  usage/account information or price-based consumption estimate is published.

## UNVALIDATED routing hypothesis

This table is a proposal for later verification. It is not an enabled policy,
an observed execution matrix, or an endorsement based on comparative results.
Sol below means `gpt-6.1-sol`; Luna means `gpt-6-luna`; Astra means `gpt-6-astra`.

| Work | Candidate request | Rationale to test |
| --- | --- | --- |
| Dots / Manager | Unchanged | Preserve current coordination and gate responsibilities |
| Research / Design and Review | Sol, High effort | Hypothesis for analysis and scrutiny of complex evidence |
| Implementation, Test, and Knowledge | Sol, Medium effort | Hypothesis for bounded execution of specified work |
| Routine classification | Luna, Low effort | Hypothesis for narrowly scoped classification with identical checks |
| Difficult design, debugging, or security work | Astra, manual approval candidate; effort to be explicitly approved | Consider only after evidence and authorization; no automatic escalation |

**Astra automatic escalation is disabled in the proposal.** No Astra request
was tested. Authentication, missing input, delivery, network, environment, and
approval failures are not escalation reasons. Resolve their actual causes and
return blockers through existing contracts. Harder work alone does not grant
model access, permission, a new evaluation, or additional business attempts.

The proposal must preserve all existing quality gates and deterministic
schema, hash, size, fixed Git revision, object typing, and full-byte verification
identically across candidate models. Model choice cannot relax AC completeness,
assignment boundaries, independent Test/Review, current-head CI, Readiness,
Issue Completion, publication safety, or separate Consumer-use authorization.

Business dispatch, execution, and delivery history stays append-only and
independent of model-evaluation accounting. Each business counter retains its
existing maximum of three and terminal state. Changing a model, effort, label,
scope wording, or failure category cannot reset history or bypass
`RETRY_LIMIT_REACHED`. This proposal does not reopen backend-app Issue 2.

## Proposed tracking and failure behavior

Any later, separately approved tracking design should distinguish:

| Information | Required interpretation |
| --- | --- |
| Requested model and effort | Explicit submitted settings, separate from actual execution |
| Observed model and effort | Supported actual runtime evidence, with unavailable values kept unknown |
| Evidence source and binding | Authorized source, fixed revision, and private execution binding; public summaries use synthetic labels |
| Usage and duration | Unknown unless measured on the applicable surface; never zero-filled or inferred from prices |
| Dispatch state/failure | Admission and start are separate; unknown start stops resend pending reconciliation |
| Execution state/failure | Confirmed started work and its outcome, separate from request admission |
| Delivery state/failure | Retrieval/publication/consumption checks, separate from execution success |
| Evaluation and business history | Separate budgets with immutable prior attempts and terminal states |

For operational routing, **fail closed on unknown or mismatched actual model or
effort**. Stop dependent comparison/application and report the missing evidence
or mismatch. Do not silently select a fallback, reinterpret an omitted value as
an observed default, or use task completion as a substitute for runtime proof.
This is proposed behavior; no enforcement code or schema extension is included.

## Staged rollout gates

1. **Step 1: runtime evidence.** Obtain a supported, authorized source of actual
   runtime model and effort bound to the relevant Cloud execution, including
   any rerouting. Reconcile requested versus observed settings and establish
   what can be verified. Until then, retain UNVERIFIED and stop.
2. **Step 2: matched tests.** Only after Step 1 and explicit authorization,
   perform matched tests within the remaining evaluation budget. Pin identical
   inputs, source revision, environment, tier, assignment, and scoring criteria;
   keep existing quality and deterministic checks identical. Require actual
   runtime evidence for each result. Unknown usage prevents savings claims;
   unknown/mismatched model or effort stops the comparison.
3. **Independent review.** Review the evidence, limits, public safety, proposed
   mapping, and unchanged contracts. Self-validation and CI do not substitute
   for this review. No new Review task is launched by this documentation work.
4. **Step 3: separate approved implementation.** Require a new implementation
   authorization and the existing readiness, Test/Review, CI, publication, and
   GitHub gates. Begin with a tiny read-only pilot that verifies runtime identity,
   preserves history, and stops on unknown/mismatch. Broader rollout requires
   pilot evidence and a further approved scope. No pilot is run here.

Documentation publication passes none of these operational gates. There is no
`config/model-routing.yaml`, routing application, default change, enforcement
implementation, new agent launch, OpenAI API call, credit purchase, merge, deployment,
Secrets/Rulesets change, or app-repository change in this assignment.

## Documentation validation and handoff

The fixed checkout contained no `AGENTS.md` or `.agents/skills` instructions.
The repository role definitions, workflow, contracts, README test instructions,
and `.github/workflows/validate.yml` govern the documentation handoff.
The owner's narrower documentation-only authorization controls this assignment.

Validation used Python 3.12 with the repository-pinned jsonschema dependency. All results
are implementation self-validation, not independent Test/Review or proof of
operational routing. Published content is a safe human-readable summary of
Manager-supplied findings, with locally checked public file integrity; it is
not the private probe evidence or a byte-identical copy of original prompts.

For Manager handoff, keep documentation assignment completion, GitHub remote
reflection, Draft PR, and same-head CI as separate states under the existing
[workflow](../../workflows/single-issue.md). Step 1 remains UNVERIFIED and Steps
2/3 remain blocked. Only Manager may make an Issue-wide final assessment.
No machine-readable handoff, readiness assessment, delivery receipt, new AC IDs,
or runtime identity is invented in this public Markdown-only change. Formal
downstream use still needs the existing fixed-byte delivery and independent
authorization checks; the public proposal grants no operational authority.

### Commands actually run

The following existing workflow checks all passed (exit 0):

```sh
python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
python scripts/validate_handoff.py examples/research-to-test/research.handoff.json examples/research-to-test/test.blocked.handoff.json examples/research-to-test/test.handoff.json examples/failed.handoff.json examples/partial-assignment.handoff.json
python scripts/validate_knowledge.py examples/knowledge/input.json examples/knowledge/handoff.json examples/knowledge/context.json examples/knowledge-delivery/input.json examples/knowledge-delivery/handoff.json examples/knowledge-delivery/context.json
python scripts/validate_readiness.py examples/readiness/pr-ready-issue-unverified.json --context examples/readiness/context.json --handoff examples/readiness/manager.handoff.json --at 2030-01-01T12:00:00Z
python scripts/validate_readiness.py examples/readiness/implementation-only.json --context examples/readiness/automatic-context.json --at 2030-01-01T12:00:00Z
python scripts/validate_readiness.py examples/readiness/postdeploy-achieved.json --context examples/readiness/context.json --at 2030-01-01T12:00:00Z
python scripts/validate_issue_completion.py examples/issue-completion/synthetic-achieved/completion.json --context examples/issue-completion/synthetic-achieved/context.json --context-sha256 951048815ca07294e13e6df297272e719e121d81a8e1c523c3958e4ba97742ac --handoff examples/issue-completion/synthetic-achieved/handoff.json --at 2030-01-03T12:00:00Z
python scripts/validate_issue_completion.py examples/issue-completion/synthetic-pending/completion.json --context examples/issue-completion/synthetic-pending/context.json --context-sha256 8943ce6030f4335adb8cfab5f7338670b2c45b3d24bd3114e92fab5c1cd8d5ff --handoff examples/issue-completion/synthetic-pending/handoff.json --at 2030-01-03T12:00:00Z
```

The README negative case behaved as expected (exit 1, missing completed evidence):

```sh
python scripts/validate_handoff.py examples/invalid-completed.handoff.json
```

`git diff --check` passed. A publication safety scan and manual content inspection
checked both Markdown files for private runtime IDs/URLs, account details,
credentials, internal logs, and original prompts. Only synthetic probe labels
and the supplied safe summaries are included. Scope inspection confirmed that
only Markdown under `records/model-evaluations/` was added and all existing
tracked contracts, code, workflows, tests, and defaults were unchanged.

Remote reflection, Draft PR state, and same-head CI are reported separately in
the publication handoff; these local checks do not certify those later states.
