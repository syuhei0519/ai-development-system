# Bounded model routing: disabled rollout, one read-only pilot

Policy revision `bounded-read-only-v1` is a local deterministic planner/validator,
not an API client or scheduler. [Configuration](../config/model-routing.yaml) is
JSON syntax (a YAML subset), parsed with a strict JSON parser; arbitrary YAML,
custom tags, duplicate keys, nonfinite values, and additional request fields are
not accepted. The existing `jsonschema` dependency is sufficient. No agent role
files, standard model defaults, business attempt histories, or existing contracts
change. Global rollout and Astra automatic escalation are disabled. No Astra pilot.

Ordinary development retains **Strict** policy. This CLI offers no ordinary
Implementation/Test/Review route. The separately authorized **BestEffort** pilot
is explicitly opt-in: exactly one low-risk public synthetic classification task,
Luna Low (`model=gpt-6-luna`, `thinking=low`), Standard (`service_tier=standard`).
This requested route is an unvalidated hypothesis. There is no silent fallback,
retry, escalation, comparison experiment, or model-comparison claim.

Historical Draft PR10 remains **UNVERIFIED** and unchanged. Its findings do not
satisfy the original Strict gate. The new one-shot authorization is separate.
Observed model/effort/usage are currently unavailable in Dots Cloud read, despite
create accepting model/thinking; no AppServer mapping to savedCloudtasks has been
verified. The implementation agent's actual runtime is also unverified. Do not
re-investigate observation as part of this pilot. There is **no savings claim**
and **no runtime enforcement** claim.

## Request, evidence, and quality

The request separately records policy revision, pilot identifier, synthetic scope,
requested model/effort/tier and the exact Git artifact pin. A Manager-held approval
binds request and policy raw-byte SHA256 plus the reviewed checkout head. Both
independent Review and CI must pass at that same head before reservation. Their
`pass` fields are assertions checked for consistency, not evidence acquisition;
Manager must verify their actual provenance independently. A downloaded template,
receipt, or self-reported approval is not authorization. Templates deliberately
fail validation until Manager provides real approval privately.

The result receipt keeps observed model/effort and evidence separate. Unknown
fields must be explicit `null`; requests and consumer self-report never become
observations. Only separately verified platform observations may be recorded with
`source=platform_observation`. CLI does not authenticate that source label.
Manager must check its provenance. Self-report/request evidence is normalized to
null/unverified, including usage. Missing usage stays `null`, never zero-filled.
Authentically measured zero tokens may be recorded with platform evidence.
There is no telemetry plumbing, usage measurement, or account lookup.

| Observation | Strict | BestEffort pilot |
| --- | --- | --- |
| Matching model and effort, evidenced usage, confirmed admission, correct classification | Accept pilot result | Accept pilot result |
| Missing model, effort or usage, confirmed admission, correct classification | Block | Accept classification; unknown fields unverified |
| Known model or effort mismatch | Block | Block |
| Admission unknown/rejected, incorrect or malformed classification | Block | Block |

`quality_result` is deterministic classification quality, separate from
`runtime_evidence` (model/effort) and `usage_evidence`. Strict blocks unknown
usage as well as unknown model/effort; BestEffort may accept unknown usage. A BestEffort accepted result is not a Strict gate pass, savings
measurement, proof of runtime enforcement, or approval for normal development.
Unchanged Handoff, Delivery, Readiness, independent Test/Review, CI and Manager
business gates remain required wherever applicable. Local bytes/schema/hash/commit
checks run in code, never in an LLM. Result accuracy does not prove that the
consumer obeyed every instruction or retrieved the file; Manager checks execution
provenance separately.

## One launch and the local trust boundary

Manager uses one durable private reservation path for this entire pilot, across
request/approval/head changes. `plan` reads only and withholds `create_arguments`.
`reserve` exclusively creates a mode-0600 marker with `O_EXCL`, flushes/fsyncs it
and its directory, and only then emits exact create arguments. No dispatch occurs
in this CLI. Single-filesystem concurrent reservations at the same path permit
one winner. Symlink state files/parents are rejected. Existing, partial, or empty
markers are consumed; there is no reset, delete, or renewal command.

A crash after marker creation, lost stdout, failed dispatch, or unknown admission
must remain **consumed/pending reconciliation**, never trigger a second launch.
Result validation is read-only and never frees the slot, even on success. Manager
keeps the reservation hash independently and reconciles admission/results in the
private ledger. Confirmed admission and missing model observations are distinct.

This supports a trusted single Manager, Linux/POSIX local filesystem, fixed state
path, trusted checkout/Python/Git, independent approval pins, and no hostile
concurrent writer. It is not a cross-service enforcement guarantee: changing or
deleting the state, using another path/host, replaying emitted arguments directly,
or bypassing the CLI can violate the ceiling. No cross-service idempotency or
cloud duplicate suppression is claimed. Do not use a filesystem without reliable
exclusive creation/fsync, an ephemeral state directory, or separate paths per
invocation. Manager alone dispatches once and retains state across restarts.

Existing dispatch/execution/delivery counters and terminal histories remain
unchanged. Manager counts this conservatively against the existing total
evaluation ceiling: **2 used + at most one new pilot = 3/6**. No launch is performed
by implementation or its unit tests. Unit tests use disposable synthetic markers.
No permanent scheduler, extra OpenAI API, paid credits, deployment, merge,
auto-merge, permissions/Rulesets/Secrets changes, app repository edits, or paused
backend Issue2 restart is authorized by this addition.

## Supported scope and handoff limitations

The planner rejects every role except `classification-consumer`, every permission
set except pinned-file read and classification return, and every artifact except
the exact public synthetic file below. Writes, app code, secrets/security work,
live infrastructure, and normal Implementation/Test/Review operation are excluded.
The input must be the supplied fixed initial input; arbitrary extra prompts are
outside the supported trust boundary. Candidate booleans are artificial facts,
not real private/security findings or Knowledge adoption decisions.

[Manager instructions, initial input, commands and pins](../examples/model-routing/README.md)
provide the handoff for independent review and the later Manager pilot. The pilot
receipt is not an Issue/Knowledge Handoff or Delivery receipt. Existing Delivery
approval and full-byte checks are not replaced by this routing approval. Manager
must fulfill any applicable transport contract separately and preserve original
artifacts; routing validation adds no publication or consumer-use permission.

For this implementation delegation, a real GitHub Issue identity/source, verbatim
Issue AC and assigned AC IDs were not supplied. Handoff v2.0 `completed` requires
these, and the consumer's classification-only result also cannot satisfy Issue or
Knowledge Handoff. Report this actual limitation to Manager as
`MISSING_ACCEPTANCE_CRITERIA`; do not fabricate an Issue/AC/task ID, rewrite the
contract, or treat old synthetic Handoff fixtures passing as a newly validated
Handoff. Implementation tests are self-verification; independent Test/Review and
Manager readiness assessment remain pending.
