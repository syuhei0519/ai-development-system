# Delivery 1.2: fixed cross references and immutable candidates

This explicitly versioned extension leaves Delivery 1.0/1.1 and Handoff 2.0,
Knowledge 1.0 and Readiness contracts unchanged. Old validators reject 1.2.
The previous partial 1.2 proposal was unreleased; it is not a released compatibility
profile. All four delivery record schemas dispatch on the exact version.

## References and structural bindings

Every artifact has an explicit `object_type`. `git-blob` requires repository,
40-hex commit, path, size and raw SHA-256. `git-commit-object` requires repository,
40-hex commit, size and raw SHA-256, and forbids path. Its artifact format must
also be `git-commit-object`. Commit payloads are checked against Git's object
header SHA-1 and retained under `git-commit-objects/REPO/COMMIT/commit.raw`.
Commit existence does not verify descendants, builds or product behavior.

`slot_bindings` binds each full owner reference, structural slot, original locator
and revision to exactly one full target reference and format. It is mandatory
for *every* Handoff artifact/upstream and Knowledge source/article/retry slot,
including relative locators. Missing, duplicate, extra and conflicting slots fail.
A structural slot is an artifact ID; an upstream role/task/attempt/relationship;
a finding/article ID plus source index; or a Knowledge retry identity.

Only generated canonical `https://github.com/OWNER/REPO/blob/COMMIT/PATH` and
`https://github.com/OWNER/REPO/commit/COMMIT` strings match. No URL is followed.
Blob revisions must be `sha256:RAW_HASH`; commit revisions must be the full OID.
Relative locators remain in the original owner repository/commit/directory.
Copies elsewhere cannot impersonate that original slot, even with equal bytes.
Every upstream document is retrieved and typed, with identity/attempt/retry Issue
checks. No original Handoff locator, status, scope, attempt or history is rewritten.

## knowledge-candidates-v1

The external artifact format selects `knowledge-candidates-v1.schema.json`.
The original JSON has **no schema_version**: it contains exactly `document_type`,
`publication_status`, `candidates`. The type must be `knowledge_candidates` and
status must remain `pending_manager_review`. This deliberately narrow profile
supports pending candidates only; it does not invent approval or adoption.
Each candidate requires exactly id/domain/summary/evidence/source/scope. IDs are
unique. Collections contain 1–128 candidates. ID/domain/source are at most 2048
characters; summary/evidence/scope at most 16384. All strings are nonblank.
Unknown/missing Knowledge identities and malformed JSON cannot be downgraded to
text, generic JSON, Handoff or Knowledge-input. The new formats are rejected by
legacy versions. Delivery 1.0's historical generic-JSON behavior is unchanged and
must never be presented as Knowledge validation.

`candidate_bindings` binds a full fixed owner reference, profile, full producer
Handoff reference, producer artifact ID, complete candidate-ID set, and one source
slot per ID. Each slot preserves the exact original source string and has one
explicit blob or tree target. The producer must declare the same IDs/domain and
raw_locator, and its knowledge artifact locator/revision must bind the owner.
The complete producer Handoff receives normal schema, identity, dependencies and
raw-byte checks. Missing, extra, duplicate, ambiguous and conflicting mappings
fail. Short producer summaries need not equal longer candidate summaries;
semantic correspondence, evidence truth and usefulness remain independent review.

Blob source targets must be separately listed artifacts with complete pins.
Canonical source URLs must match the explicit target, and all bytes, size/hash,
Git object OID/type and safe ancestry are verified. There is no fabricated source
revision field in the immutable candidate document.

## git-tree-snapshot-v1

A tree target contains `kind=tree` and a `snapshot`: profile, repository, commit,
path (directory), root tree OID, `trees` and `files`. Paths in the two lists are
relative to the directory, unique and lexicographically sorted. Every nested tree
has path/OID. Every regular file has path/mode/OID/size/SHA-256. The empty tree is
represented explicitly by its Git OID and empty lists. All path lengths, including
the directory prefix, must be at most 512 characters; snapshot names are restricted
to ASCII letters/digits/dot/underscore/hyphen and exclude dot/dotdot/.git.

The verifier obtains the fixed commit through isolated HTTPS Git, checks its raw
OID, parses its root tree, and walks normal tree ancestors. It reads complete raw
Git tree objects and verifies their type/size/OID before parsing every entry.
This avoids accepting truncated recursive listings as complete inventories.
Within the requested subtree every leaf must be 100644 or 100755; symlinks and
gitlinks fail. Only actual traversed ancestor edges must be directories. Missing
objects, duplicate names, malformed/truncated raw trees, inventory omissions,
extras, mode/OID/size/hash differences, nonregular objects and unsafe names fail.
All regular blob bytes are fetched and checked. Binary files are preserved as raw
source data and never executed or implicitly interpreted as typed documents.
Using a source-tree member later as Handoff/Knowledge requires separate explicit
artifact typing and full document validation.

Bounds per snapshot: 4096 total descendant entries, 1024 descendant trees,
1 MiB per raw tree, 4 MiB total raw ancestor/descendant tree metadata,
16 MiB per commit/blob. The combined bundle including all tree file bytes is
limited to 64 MiB. Exceeding limits fails; no truncation. Existing 128 explicit
artifact, 128 candidate-binding and 128 source-slot limits remain. Git calls have
120-second deadlines. Fetch pack network/disk totals remain environment bounded,
not byte-limited by this contract. Only trusted repositories should be authorized.

Tree members use the same `artifacts/REPO/COMMIT/PATH` output namespace as explicit
blobs. Overlapping references must have identical bytes. A tree snapshot is an
original representation and requires `original` in the separate authorization.
All output is staged privately and becomes usable only after *every* document,
source, dependency and authorization check passes. Tree/commit existence alone
certifies neither descendant content nor builds or product ACs.

## Records, permissions and retry history

Authorization still independently pins manifest/publication bytes, exact consumer,
scope, purpose, representations and expiry. Publication receipts pin the complete
manifest plus explicit artifacts; the manifest includes every candidate/tree pin.
Consumption receipts retain exact slot/candidate bindings and `authority_granted=false`.
Fresh receipt rechecks fetch everything again. They do not inspect old local output.
No source state, pending flag, successful hash, receipt or public availability grants
permission. Independent Test/Review, CI, B1 product acceptance, implementation restart,
Readiness and Issue Completion remain separate gates.

For an authorized retry with additional *assignment completion conditions*, retain
exact Issue/AC original bytes and the prior Handoff, increment attempt, and bind it
as retry_of. Put newly adopted conditions verbatim in assignment.completion_criteria
and keep a separate change record; do not fabricate new Issue ACs or rewrite the
prior issue to bypass equality. The Manager compares the assignment to its authorized
input, as in Handoff 2.0. Formal new Issue ACs would require a separately approved
contract transition; this extension does not weaken retry Issue equality.

See `examples/crossref-delivery/README.md` for reproducible preparation and validation.

## Bounded capacity (Delivery 1.3)

[Capacity and compatibility contract](artifact-capacity.md): explicitly select 1.3 for up to
256 artifacts; legacy 1.0/1.1/1.2 retain 128. All four delivery records must match.
Per-file 16 MiB, bundle 64 MiB, tree/slot/candidate limits and all approval gates
remain unchanged. Preserve originals and complete closure; never overwrite old
delivery outputs. Dispatch/execution/delivery remain each at most 3. Candidate
1.3 requires System CI and independent Review before merge and canonical use.
