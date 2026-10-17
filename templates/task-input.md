# 独立専門エージェント起動入力

Dots / Manager が専門役割の独立タスク（保存済み Codex Cloud が既定、実 Kubernetes Test のみ検証済みローカル PC）に渡す入力テンプレート。Manager 自身の Cloud 起動には使わない。Knowledge は [専用入力](knowledge-input.md) を使用する。山括弧の項目を埋め、未記入のまま起動しない。必須 AC 原文が取得できなければ不足を明示し blocked を要求する。実識別子や非公開資料は認可された非公開実行領域だけで扱う。

## Role / Contract

- role: <research-design | implementation | test | review>
- role_definition: <該当 agents/*.md の全文または取得済み添付>
- contract: <handoff.schema.json と contracts/README.md の取得済み添付>
- workflow: <single-issue.md の取得済み添付>

## Issue-specific Context

- Issue ID / title / authorized source: <識別子・題名・認可済み出典>
- 必須 AC 原文（省略・要約しない）: <AC ID ごとの原文と出典>
- AC の完全性確認: <全件取得済み / 欠落項目と MISSING_ACCEPTANCE_CRITERIA>
- task_id / attempt / logical scope: <独立 task・1〜3・再試行を通じ固定する責務>
- repo / base / target revision: <明示的な対象>
- assignment.scope / ac_ids / completion_criteria: <今回の担当範囲・担当 AC ID の明示的リスト・工程の完了条件>
- Mission / deliverables: <今回の責務と成果物>
- 許可操作・作業領域・禁止事項: <read/write/feature Push/Draft PR を個別指定>
- 環境・依存物・検証手順: <既存認可済みの環境>

## Execution Context（必要能力で選択）

- venue / required capabilities: <保存済み Codex Cloud / 検証済み local kind。AC/subcheck ごとの能力と選択理由。E2E 名だけで判定しない>
- runtime identity: <固定 code/config revision、実測 image digest（使用時）、DB/サービス構成、検証対象。未取得と該当なしを区別>
- local kind Test の場合: <`cloud_threads.create` に明示する検証済み接続・認可済み環境の非公開参照、正確な context/cluster、namespace、既存/owned inventory、承認 access scope/操作、cleanup 境界と復旧責任。秘密値を添付しない>
- unavailable / partial: <失敗操作・対象・理由・環境阻害の検証、独立して続ける Cloud 作業、残る gate と再開条件。予算・履歴は維持>
- return evidence: <venue/必要能力/実 identity/context/観測時刻/コマンド/結果/cleanup を既存 observation と固定 report artifact に記録。非公開原本と公開承認済み派生版を分離し Artifact Delivery で返す>

通常確認はまとめて行い、既存認可を再要求しない。mutation の safety floor 承認は省略しない。Cloud への既定割当・既存 runtime の対応範囲・offline 時の独立作業継続は [workflow](../workflows/single-issue.md#実行場所と必要能力) に従う。これは Handoff の新フィールドではなく初回入力の説明項目である。

## Explicit Handoff Bundle

- upstream: <role/task_id/attempt/relationship/handoff locator/revision>
- 取得済み handoff JSON: <本文または添付>
- 成果物の実体: <本文/添付/到達可能な固定参照と revision/digest>
- 根拠: <出典・確認結果・対象 revision>
- 採用判断、失敗、不採用案、制約、未確認点: <列挙>
- 再試行なら: <前回の阻害・修正内容・retry_of・前回 attempt +1>

前タスクの会話やローカルファイルの自動共有を仮定しない。必要な実体が未着なら blocked を返す。

## Optional Knowledge Context

必要な場合は [knowledge-context.schema.json](../contracts/knowledge-context.schema.json) に従う JSON と記事実体を初回入力に添付する。固定 revision、適用条件、例外、出典、lifecycle、再評価条件を確認し、採否を記録する。参照知識で AC 原文や実測根拠を代替しない。参照なしだけで開発を止めない。

## Return Contract

- 取得先: <Manager が handoff.json と成果物を取得する場所>
- handoff: schema_version=2.0、issue、assignment、role、task_id、attempt、upstream、system_status、status、summary、artifacts、evidence、ac_mapping、block_reasons、failure_reasons、knowledge_candidates、publication
- completed は assignment の工程完了。担当外・未検証を covered にしない。専門役割は final_assessment を出力しない。
- 基盤終了と業務判定を区別する。原文欠落は外部取得・推測で埋めない。
- 最大3試行。自己再起動せず Manager に修正内容を返す。
- Knowledge 候補は任意。公開前の安全性確認を別途行う。

## Readiness Context（該当する変更工程）

- Implementation Ready: <担当実装範囲、設計・実装許可・依存の根拠、未決設計とユーザー判断事項>
- Deployment Ready: <対象環境・rollback・配備許可・依存の状態。実装可否とは別評価>
- 対象: <repository、PR番号または未作成、head/base/target SHA、config revision、必要な merge-group SHA>
- AC: <全原文、最早検証段階、対象 PR の ac_ids、Manager による分類・scope 確認>
- 配備影響: <none / automatic / unknown と根拠。automatic/unknown の merge は Deployment Ready 必須>
- 現在の context: <readiness-context.schema.json に従う取得済み実体、保護設定・必須 checks/reviews/queue・取得時刻・期限>
- 証跡: <CI / 独立 Test / AI Review / GitHub 各保護条件 / 承認 / 依存を個別に取得。対象・時刻・期限・producer>
- postmerge/deploy 専用 AC: <unverified、前に検証できない理由・担当・環境・方法・失敗時対応・分類根拠>
- 配送: <Readiness v1.0 を Handoff v2.0 artifact として固定参照・実体添付し、両 CLI と --handoff 照合結果を返す>

該当しない工程は理由を記録し、架空の PR/証跡を作らない。Merge Ready は Issue Completion ではない。premerge の不合格・未実行・承認待ちを deferred にしない。未検証があれば自動 close を指定せず、Manager の全 AC 実測後の最終判定を待つ。


Issue Completionには全AC実測に加えて必要な統合完了が必要。全premerge ACがmetでも未マージならunverified。Readiness/contextのissue_integration_scopeで単一PRと集約待ちを分離し、複数PR・repo/範囲不明は単一PRからachievedにしない。複数PR・repoは独立[Issue Completion契約](../contracts/issue-completion.md)で全必要集合と固定証跡を検証する。全AC met・統合待ちの中間Handoffではfinal_assessmentを省略し、Readiness artifactで追跡する。

Readinessの配送にはartifact_id、Handoff基準のローカルlocator、実体bytesのsha256 digest revisionを使用する。`validate_readiness.py --handoff`は実体の読み取り・評価対象ファイルとの同一性・digestを照合する。旧DraftのReadinessは追加必須項目を確認して移行する。詳細と限界はReadiness契約を参照。

## Artifact Delivery Context

[配送テンプレート](artifact-delivery.md) の全 reference、原本/派生版区分、公開前後状態、
Publication Receipt、独立 pin の Consumer 利用承認、Consumption Receipt と検証済み実体を渡す。
未検証 bytes を利用しない。dispatch/execution/delivery の各予算、最新非公開台帳 pin、
旧 terminal と新承認 epoch の関係を明記する。最大3回は各予算に適用し、旧履歴をリセットしない。

## Aggregate Issue Completion Context

複数 PR/repo は [集約契約](../contracts/issue-completion.md) に従い、独立 context pin、全必須 PR/repo/AC 原文/subchecks、承認 scope、merge head/result 対応、配備 source/config/image/environment/workload、現在観測と期限、最新 previous pin と全履歴を初回入力に渡す。PR Readiness pair と最終 Issue Handoff pair は別実体で配送する。未実測は unverified、既知 failure/rollback は not_achieved を保持する。CLI 成功から操作権限を推論しない。

## 依存準備 PR の追加契約

[Readiness 1.1](../contracts/readiness.md#依存準備-prreadiness-11) の準備区分は Manager が固定 context で選択する。通常 PR の製品 AC ゲートは維持する。準備 PR はデプロイ影響 none・aggregate_required のみ。非空の工程条件、関連製品 AC、固定成果物、独立 Test/Review、後続検証責任を引き渡し、工程達成を製品 AC 達成や操作許可へ変換しない。起動入力には pr_kind、preparation 全体、独立 context pin、実体 bytes を含める。Implementation の自己検証は独立 Test/Review を代替しない。

Issue Completion 1.1 は準備 PR を型付き required メンバーとして保持する。
空の製品担当 ac_ids と関連 AC を分離し、歴史的 Readiness の親を成果物 root として
context の固定 BlobRef と照合する。全必要 merge 集合と後続 standard PR の全製品実測を要求し、
工程合格を製品達成へ変換しない。版互換・配送・検証手順は
[Issue Completion 契約](../contracts/issue-completion.md) と [合成例](../examples/issue-completion/README.md) を参照。


## Optional authorized model-routing trial context

For a new explicitly approved workflow-trial dispatch, include a separate private
[model routing record](../workflows/workflow-model-routing.md), not extra fields in
Handoff/Knowledge input JSON. This section cannot replace required inputs above.

- policy revision / independently pinned routing head: <workflow-best-effort-v1 / system checkout SHA; target task head and its CI remain separate>
- role / exact logical scope / private task reference / attempt: <same authorized assignment and unchanged retry ledger>
- dispatch decision: <new_task or explicit_redispatch; explicit approval; never change in-progress settings>
- mode / requested model / requested effort / requested tier: <BestEffort trial or Strict opt-in / role route / thinking / default=Standard>
- current business history and approval: <separate raw hashes, source/provenance, remaining existing budget; no reset>
- routine-only or manual Astra decision, if any: <explicit narrow scope and separate approval; Astra exact model/effort/budget/reason>
- observed model / effort / evidence sources and execution binding: <null/unverified until qualified platform or human-confirmed per-task UI evidence; selector/aggregate is insufficient>
- usage / observation history: <null if unknown; append-only private records with predecessor hash; no inferred zeros/savings>

No routing record grants AC completion, changes Handoff/Readiness/Delivery schemas,
relaxes security/approval/independent testing/review/current-head CI, or advances
an Issue. Role choice never grants access or additional attempts.
