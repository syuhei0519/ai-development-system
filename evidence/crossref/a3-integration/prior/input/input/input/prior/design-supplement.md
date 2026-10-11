# Manager design supplement for the next independent assignment

This is a later Manager design decision recorded during delivery preparation.
The original X-1 through X-6 remain unchanged in assignment-requirements.json.
Attempt 1 remains blocked. This document does not start attempt 2, implement code,
authorize publication, authorize application execution, or approve a merge.

## Adopted design

Manager adopts the explicit knowledge-candidates-v1 profile, outer candidate_bindings,
full raw-byte blob source verification, and complete tree-source snapshot verification.
Provenance-only treatment is not accepted. Candidate meaning and source truthfulness
remain independent review gates; delivery success is not knowledge adoption or B1 acceptance.

Keep immutable candidate bytes unchanged. Do not add schema_version, task_id, attempt,
revision or authority to the original document. Preserve publication_status=pending_manager_review;
it is not public-operation approval, consumer-use approval or an adoption decision.
The profile version is selected externally by the typed delivery record.

The explicit profile must require exact document_type=knowledge_candidates; the existing
top-level fields document_type/publication_status/candidates; and candidate fields
id/domain/summary/evidence/source/scope. Define strict required fields, types, bounded
collections/strings, unique candidate IDs and additionalProperties=false.
Maintain unknown Knowledge rejection in generic JSON, text, Handoff and Knowledge-input
paths. Legacy Delivery 1.0/1.1 schemas and successful behavior remain unchanged and reject
the new format. Extend all delivery record schemas and version dispatch consistently.
This is an addition to the unreleased 1.2 design, not a retroactive reinterpretation of 1.0.

Outer candidate_bindings have an explicit profile version, the complete fixed owner-document
reference, producer Handoff reference, producer artifact ID, candidate-ID correspondence,
and exact original source string plus typed source target for each structural slot.
Validate the producer Handoff bytes/type/identity, artifact and raw_locator linkage, and
complete one-to-one candidate identity correspondence. Reject missing, extra, duplicate,
ambiguous or conflicting bindings. Do not require equality between deliberately different
short producer summaries and longer candidate summaries; semantic correspondence remains review.
Do not invent an original revision field: fixed commit is parsed from the source URL,
and raw size/hash pins live explicitly in the outer binding.

Blob source: match canonical GitHub fixed blob URL to repository/full commit/path.
Fetch through isolated HTTPS Git and validate all raw bytes, size/hash, object type
and safe tree ancestry. No arbitrary URL traversal, floating refs, redirects, symlinks,
gitlinks, filters, checkout or execution of the fetched application code.

Tree source: define a versioned complete snapshot contract for the canonical fixed tree URL,
repository/full commit/directory. Resolve the directory through normal tree ancestors.
Enumerate the entire subtree, including nested tree edges needed to prove ancestry,
and require every non-directory leaf to be a regular blob (100644 or 100755).
Match the complete file/path/mode/OID set without omissions, extras or duplicates.
Bind and retrieve every regular blob with exact raw size/SHA-256 and Git blob OID checks.
Reject symlink/gitlink leaves or ancestors, non-tree directory edges, path ambiguity,
missing objects, excess resource bounds and partial enumeration. Do not silently truncate.
Empty directories are not Git entries; an empty Git tree must be handled explicitly.
Tree/commit existence alone does not verify descendant files, build results or product ACs.
The detailed schema and resource ceilings must be pinned in the next approved assignment.

The two existing B1 source forms are:
- blob: https://github.com/syuhei0519/backend-app/blob/7b54f55cf1a652ee127528877b3bb9034b75b311/internal/ordertest/disposable.go
- tree: https://github.com/syuhei0519/backend-app/tree/7b54f55cf1a652ee127528877b3bb9034b75b311/internal/store/orderpostgres

Authorization remains a separate private Manager record with independent pin,
consumer/scope/purpose/expiry and exact manifest/publication bindings.
Receipts grant no authority. Do not emit usable output before every required dependency passes.
Original Handoff role/status/attempt/retry and historical terminal states are immutable.

## Proposed additional ACs for the next assignment

These are proposed next-assignment additions, not retroactive attempt 1 coverage.

- X-7: 厳格な knowledge-candidates-v1 profile と版付き外側 candidate_bindings を実装する。原文書にschema_version等を追加せず、document_type・必要field・型・余剰field禁止・候補ID一意性を検証する。producer Handoff固定実体・artifact ID・raw_locator・候補ID集合・原source文字列とtyped targetを一意結合し、欠落/余剰/重複/曖昧/競合を拒否する。pending_manager_reviewを承認へ読み替えず、未知Knowledge型の降格拒否を維持する。blob sourceの全bytes・size/hash・固定URL/OID/pathを検証し、provenance-onlyへ緩和しない。
- X-8: 固定tree sourceの版付き完全snapshotを検証する。固定repo/full commit/directoryとcanonical tree URLを照合し、対象祖先および配下treeを完全列挙する。全通常blobのpath/mode/OID/size/SHA-256と実体を照合し、欠落/余剰/重複/改変/不正祖先/symlink/gitlink/非通常object/部分列挙を拒否する。tree/commit objectの存在だけで配下内容やbuild/製品ACを認定せず、件数/bytes上限超過時は切り詰めずfail closedとする。
- X-9: 実B1公開Handoffとknowledge_candidates原bytesを変更せず、固定code commit・Research依存・候補producer binding・blob source・tree配下の全必要実体をCLI実取得で検証する。旧128testsを含む現149testsを維持し、新旧validatorで版・型・URL/OID/path/mode/size/hash・candidate集合・producer・承認・依存欠落・private_only・symlink/gitlink・JSON偽装・retryidentity・再取得の正常/否定系を検証する。System自己検証、独立Test/Review、B1製品AC、実装再開、IssueCompletionを分離して報告する。

## Delivery and assignment boundaries

This supplement and the blocked report travel as ordinary Delivery 1.0 text/JSON artifacts.
They do not smuggle a B1 Handoff into a generic document or certify embedded code, references,
new schemas, or the historical B1 attempt. The saved patch is plain-text source evidence,
not an executed implementation or new-format Consumer success.

For the next task, Manager must fix the target revision, P-A dependency state, approved scope,
X-1 through X-9 assignment, implementation authority, independent consumer pin and retry history.
P-A merge and Manager dependency confirmation remain prerequisites to PR creation.
No task starts from this preparation alone. No authorization JSON is part of this public bundle.
