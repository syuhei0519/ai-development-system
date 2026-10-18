# Knowledge Collection v1.0 — Phase 1-3 P-B

P-B provides mechanical collection and durable bookkeeping. The collector never launches
an Agent, calls an LLM, writes Git, creates a PR, generates semantic knowledge, registers a
schedule, or changes development readiness. Manager remains the single writer and performs
external actions only after the corresponding reservation has been persisted. P-C context
production/ack/periodic adapters and P-D real Knowledge/Consumer operation remain unimplemented.

## Contracts and authority

All new contracts are closed Draft 2020-12 objects, version 1.0:

- [KnowledgeEvent](knowledge-event.schema.json): public-safe or explicitly synthetic candidate,
  correction, or invalidation; producer role, observation kind, source and finding pins,
  timestamps, representation, optional Issue aliases, supersedes. No runtime identity field.
- [source registry](knowledge-source-registry.schema.json): all approved fixed inbox snapshots,
  typed artifact inventory and Delivery 1.3 Knowledge bindings. Each source ID and repository/path
  pair is unique; overlapping inbox prefixes are rejected. Source IDs remain stable on updates.
- [KnowledgeCollectionState](knowledge-collection-state.schema.json): **private_only**, writer/scope,
  predecessor digest, cursors, immutable original event digest, event state/history, stable batches,
  retry ledgers/pins, runtime observations, output digest, validated artifact set, committed pins,
  leases/backoff and full scan history.
- [record requests](knowledge-collection-record.schema.json): closed action-specific Manager inputs.
- [operation authorization](knowledge-collection-authorization.schema.json): private, independently
  supplied SHA256 pin, exact writer/scope/operation/request digest and expiration. Approval is
  external authority, never inferred from a receipt, event classification, replay, or public file.

`scan` and `reconcile` use the registry's **raw bytes** as the request. `record` uses the raw
closed action JSON. Manager confirms read/use permission and public safety for every fixed
snapshot and dependency before authorizing that request. Authorizing a scan does not authorize
a dispatch or a later record. Expired authorization cannot mutate state. The API is not a
signature system: trusted Manager code, current pins, local private storage and OS are the
trust boundary. Anyone controlling the independent CLI pins or private store can fabricate
observations; collection does not independently prove that an external Agent started.

The identity is SHA256 of UTF-8 JSON, sorted keys, compact separators, `ensure_ascii=False`,
plus LF, containing exactly `version="1.0", repository, commit, path, sha256, candidate_id,
event_kind`. The repository/path/hash come from `source_ref`; event ID is lowercase 64 hex.
Time, size, delivery attempt and runtime task identity do not enter this identity. Raw event
payloads are hashed without normalization. Same identity with any different payload bytes
(including a changed timestamp/whitespace) is a collision and quarantined. Corrections use a
new fixed source/candidate identity and `supersedes`; similar content is never deduplicated.

## Scan and reconciliation

`SnapshotSource` uses P-A's isolated HTTPS Git environment and raw blob reader. No checkout,
hooks, filters, submodule execution, arbitrary URLs or floating revisions are permitted. A
snapshot is a full 40-hex commit. All tree entries beneath the inbox prefix are enumerated,
including entries that must fail validation; only regular blobs are accepted. Expected event
path is `<inbox_path>/<event_id>.json`. UTF-8/strict JSON rejects duplicate keys, NaN and BOM.
Every ancestor through the inbox prefix must be a Git tree; symlink, gitlink and ordinary
blob ancestors are rejected before recursive enumeration. A genuinely missing prefix below
verified tree ancestors is an empty inbox and still participates in disappearance checks.

Every scan is a **full reconciliation**, even for a repeated commit. There is no ancestry,
diff, updated_at, notification-order or shallow-history optimization. Registry changes,
missing history, force pushes and old nonancestor cursors therefore follow exactly the same
complete path. Every declared source/dependency is read and size/SHA256 checked, and P-A
`verify_handoffs(..., '1.1', bindings)` verifies the entire typed dependency bundle before use.
Event references must exactly match that inventory. Handoff artifacts/upstream and Knowledge
source/article/retry dependencies remain subject to P-A local-path rules. Cross-reference
extensions are outside P-B; no URL reinterpretation or original-byte rewrite is performed.

A network/read/partial blob/hash failure aborts the entire scan transaction: no event/cursor
change. Complete but malformed events or events lacking an inventory reference are individually
quarantined, with original bytes retained; valid events remain processable. An already recorded
event that disappears from **any previously observed source** or changes payload is quarantined,
even when another inbox still supplies the same event bytes. Historical source membership is
retained, including sources removed from the registry. The scan is marked `quarantined`,
and cursors do not advance. Terminal/retry history and original bytes remain intact. A clean
scan advances every source cursor together with event registration. Cursor means enumerated,
not processed successfully. A poisoned event can coexist with a successful enumeration.

Resource limits: 1024 event files/source, 128 sources, 128 dependencies, 16 MiB/blob,
64 MiB total scan/bundle payload; inherited 120 second Git command timeout. No implicit retries.
Git pack transfer size and tree listing size are not bounded by blob limits; only trusted,
authorized repositories and a bounded execution environment should be used. State must fit
16 MiB for subsequent reading; archive growth needs Manager capacity planning. No automatic
history deletion, compaction, private-store backup or remote-storage provisioning is included.

## Durable transaction and recovery

Private POSIX local storage uses directory mode 0700 and files 0600. The parent is Manager
controlled; NFS/distributed locks and adversarial local writers are unsupported. The stable
`writer.lock` uses nonblocking `flock`, so overlap is rejected. Under the lock the writer and
scope must match, and `--previous-sha256` must match exact current `state.json` bytes. Use
`absent` only for first initialization. Retain the latest successful digest outside this store;
a digest supplied by an old snapshot cannot replace the current file. Whole-store rollback
by its owner is detectable only against that independently retained latest pin.

Transaction order: verify all reads → content-addressed raw objects + previous state, fsync →
complete candidate in `staging/`, fsync → immutable `snapshots/<digest>`, fsync → atomic replace
`state.json`, directory fsync. Scan/event/cursor updates share this one commit point. No raw
history is overwritten. After failure, staging/snapshots are retained for inspection and never
automatically promoted. Before state replacement, repeat the authorized operation against the
old pin; after replacement, reload/verify the new state and update the Manager pin. Never blindly
repeat an external dispatch when a CLI result was lost. `plan`/`replay` do not recover or mutate
staging. Power-loss guarantees depend on the filesystem honoring fsync and atomic rename.

Objects, staged states and snapshots are first written and fsynced inside a fresh private
temporary directory on the same filesystem. A hard link publishes the complete file at its
digest name without overwriting an existing name, then the destination directory is fsynced.
An existing final file must contain exactly the expected bytes and is never replaced. A killed
writer may leave `.pending-*` directories; retries ignore these incomplete files and use fresh
temporary paths. They are not automatically promoted or garbage-collected. This also covers
crashes inside the raw write, before the transaction crash hooks. Corrupted final files already
created by an older writer remain fail-closed and require explicit Manager repair; retry does
not silently overwrite historical evidence. No schema or retry-budget migration is required.

## Batch, transition and retry protocol

`reserve` seals a nonempty explicit set of verified event IDs and a Knowledge v1 input digest.
Raw-finding IDs must exactly equal those event IDs, and each finding must preserve all its
event source digests. Batch ID = SHA256 of sorted event-ID JSON + LF. Each event is claimed only
once; regrouping, input changes and new batches cannot reset that event's ledger. The raw input
is retained in objects. A lease is informational; expiry never releases the claim or restarts an
Agent. Backoff is enforced at dispatch and delivery reservation.

| Record action | Required state / effect |
| --- | --- |
| reserve | verified → reserved; immutable membership and initial retry ledger |
| dispatch | reserved → dispatching; reserve dispatch and check execution budget **before** external launch |
| dispatch_unknown | dispatching → dispatch_unknown; retains pending dispatch reservation |
| started | dispatching/dispatch_unknown → started; pinned observation + runtime ID, dispatch success, reserve execution |
| dispatch_failed | same source states → reserved; pinned proof of **not started**, dispatch failure |
| execution_failed | started → reserved; matching runtime observation, execution failure |
| prepare_retry | reserved only; fresh P-A typed bundle for next input, same assignment/findings/context, prior attempt binding |
| output_received | started → output_received; matching runtime, durable output bytes, execution success |
| delivery_start | output_received; persist a delivery reservation before fetch/validation |
| delivery_failed | pending delivery → output_received; consume attempt, preserve output and optional backoff |
| validated | pending delivery → validated; re-fetch complete typed bundle, exact sealed input/output, completed Knowledge handoff |
| commit_pending | validated → commit_pending **before** external Git work |
| committed | commit_pending → committed; freshly verify exact bytes in one fixed output snapshot |
| context_available | committed → context_available; records an already validated, committed context (does not generate or sync it) |
| blocked | reserved/validated → blocked with pinned evidence; no automatic release or retry |
| renew | terminal only; existing retry validator requires separately pinned explicit grant and empty new epoch |

`pending` and `verified` are separately recorded during scan; poison/history anomalies use
`quarantined`. Blocked/quarantined states are intentionally not automatically reset. Manager
can correct source evidence through a new superseding event; it must preserve its relationship
to the old failed work rather than relabeling identical work to obtain a fresh budget.

The existing append-only retry validator owns dispatch/execution/delivery budgets (each at most
3 including success). A persisted pending reservation cannot be reserved again after a crash.
A result consumes that reservation once. Failure on the last allowed attempt preserves
`RETRY_LIMIT_REACHED` and moves to terminal. Even a fully used successful counter cannot be
used a fourth time. Original scope/history/limits are not rewritten. `prior_ledger_sha256` on
reserve imports an independently pinned existing ledger with the exact batch scope; terminal
imports remain terminal. Manager must map previous logical work before initial ingestion.

After an execution failure, dispatch rejects stale input attempts. `prepare_retry` verifies a
complete Delivery 1.3 bundle including the new input and its typed prior handoff dependencies;
the new task identity and next attempt are required. After an explicitly authorized new epoch,
a new attempt-1 input is allowed while old epochs remain. `renew` uses the existing grant shape
and separate `--grant-sha256`; ordinary record authorization alone cannot renew. It cannot discard
an acquired output: renewal resumes delivery if output exists. Receipt/replay cannot supply a grant.

Output-received crash: recover the same raw output and resume its delivery reservation; do not
launch Knowledge again. Git-commit-before-state crash: record `committed` with fixed repository,
commit, paths, sizes and hashes for **all** validated bundle bytes, and fetch them again. This
acknowledges exact bytes only, not merge approval, article quality, readiness or operational use.
The CLI neither creates nor retries a commit. Manager reconciles external Git outcomes first.

## CLI and public/private boundary

See [synthetic reproduction](../examples/collector/README.md) and
[Manager input template](../templates/knowledge-collection.md). `plan` and `replay` are the same
read-only deterministic calculation against an exact state digest. They do not confer authority,
reserve a batch, use a past authorization, or read live sources. Private plan output can be saved
with `--private-plan`; state remains unchanged. Suggestions require current authorization and
all record preconditions, including budgets, retry-input replacement and backoff, before action.

`scan`, `reconcile`, `record` require independently pinned current authorization and CAS. Public
stdout contains only closed status counts, `authority_granted=false`, and
`development_gate_changed=false`; stderr is a fixed error message. No request, runtime ID,
source content/path, authorization, private digest or internal exception is emitted. Exit 0
means the bookkeeping transaction succeeded, including individual quarantines; exit 1 means
rejection, exit 2 argument error. Inspect counts and private state, never infer all events passed
from exit 0. These are **Knowledge-only** results; do not add the collector to a development gate.
