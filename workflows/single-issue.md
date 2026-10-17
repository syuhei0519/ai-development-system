# 独立タスクで進める Issue ワークフロー

## 起動と責任分担

この手順は Dots 自身が Manager として実行する運用契約であり、自動実行エンジンや Dots API の実装ではない。Dots は `agents/manager.md` と契約・本ワークフローを使用し、専門工程ごとに役割定義と [Issue 工程入力](../templates/task-input.md)（Knowledge は [専用入力](../templates/knowledge-input.md)）を渡した独立タスクを起動する。既定は保存済み Codex Cloud とし、実 Kubernetes 必須の Test だけは下記の検証済みローカル PC 環境を指定する。別の Manager Cloud タスクは標準構成に含めず、6プロセスも常設しない。Dots に起動・回収能力がない環境では人間が操作を補助し、その制限を明示する。追加の OpenAI API、新規課金サービス、新規 PAT は不要。

標準依存関係は Research/Design → Implementation → Test → Review → Manager 最終ゲート。設計だけの検証では Research → Test も可能。独立した作業の並行実行は依存がないことを Manager が確認した場合のみ。Knowledge は各工程の候補から非同期に起動し、開発の必須依存にしない。

1. Manager は認可された Issue 原文・全必須 AC 原文・対象 repo/revision・実行権限・assignment.scope・担当 ac_ids・工程固有の completion_criteria を初回入力へ明示する。専門役割は担当外 AC を完了対象に含めない。Knowledge は Issue/AC ではなく収集・抽象化範囲と raw_findings を渡す。役割定義には Issue 固有情報を書き込まない。
2. 同じ論理工程（Issue + role + scope）ごとに最大3試行（初回 attempt=1、再実行2回）を割り当てる。scope を言い換えて試行上限を回避しない。新しい独立タスクには新しい task_id を与える。
3. upstream handoff の JSON だけでなく、成果物の**実体**と根拠を取得する。固定 Git commit と raw bytes の配送契約で後続が読める形で渡す。LLM に本文を再生成させない。元タスクのローカルパスや終了通知だけを渡さない。
4. タスクを起動し、非公開の進捗台帳に role/scope/task_id/attempt/upstream と基盤状態を記録する。タスク間の会話・ファイル・認証・環境が自動共有されるとは仮定しない。

## 実行場所と必要能力

Manager は各検証を AC/subcheck と必要能力に分け、最小限の関連検証を割り当てる。テスト名や E2E という名称だけで Kubernetes 必須にしない。

| 必要能力 / 作業 | 実行場所 |
| --- | --- |
| Research/Design、Implementation、Review、Knowledge、Unit、build/static checks | 保存済み Codex Cloud |
| 実 DB 統合、API レベルの複数サービス E2E（既存 runtime が対応する場合） | 保存済み Codex Cloud |
| Helm rendering / schema checks（cluster 不要） | 保存済み Codex Cloud |
| 実 deployment / Service DNS / Ingress / probes / Pod restart / PVC | ローカル PC の既存 kind |
| Argo sync、Rollouts/canary、cluster observability の実挙動 | ローカル PC の既存 kind |

Cloud の必要 runtime が使えなければその検証を環境阻害として記録する。通常作業をローカル PC へ自動 fallback したり、追加 API/課金サービスを導入して回避しない。API/DB の実測はその範囲の証拠であり、mock、compose、Helm rendering は実 cluster AC の合格を証明しない。

### ローカル kind Test の起動前ゲート

Dots が Manager のまま、Kubernetes Test を独立タスクとして `cloud_threads.create` で起動し、特定して検証済みのローカル環境を明示する。Cloud の既定環境や推測した環境 ID を選ばない。初回入力へ固定成果物と必要能力・venue・許可範囲を渡す。create 引数の具体的な環境指定は現在の tool schema に従い、対応手段がなければ blocked を返す。新 runner は作らない。

ローカルでの mutation 前に、Manager と Test は認可済み read-only 観測と承認根拠から次を確認する。

- 接続・認可済みの正しいローカル実行環境、既存 kind の正確な kube context / cluster（名称だけでなく接続先との一致）。
- 対象 namespace、既存リソースと今回所有するリソースの inventory、他作業・ユーザーデータとの境界。
- 承認された credentials / access scope、許可された具体的操作と対象。credentials 自体は入力へ転記しない。
- cleanup の明示境界（今回作成物の除去範囲、残す既存物、復旧責任）。既存 cluster の再作成・削除は行わず、ユーザー context を無断で変更しない。

通常の確認事項はまとめて確認し、既存の認可で満たされる事項を再承認要求しない。ただし safety floor の操作別承認、実 Rulesets / CI gates は保持し、包括的な実行場所の認可から破壊的操作の許可を推論しない。

ローカル PC offline / 接続不明 / 権限不足なら、必要な cluster 検証を **environment blocked** として正確な対象・失敗操作・理由・必要処置と共に返す。未起動を実行済みにせず、開始不明は照合まで再送停止。無期限 polling、予算リセット、自動再作成はしない。既存 dispatch/execution/delivery 台帳の分類と最大3回を維持する。依存のない Cloud 実装・API/DB 検証は継続し、混在 assignment は部分成果を保持して cluster 担当部分を未検証にする。必須 premerge cluster AC が blocked なら Merge Ready も blocked のまま。環境不足だけで postdeploy に付け替えない。

### 実行証跡と引き継ぎ

Handoff v2.0 の既存 `evidence.observation` と固定 `test-report` artifact に、実行 venue、必要能力、実行コマンド/結果/時刻/制約を記録する。runtime Test は実際の code commit、config revision/digest、実行 image digest（使用時）、DB/runtime の識別と構成を記録する。cluster Test は検証済み environment / context / cluster / namespace / workload と所有 inventory、mutation/cleanup の実施結果も非公開原本へ記録する。未使用項目は理由付きで該当なし、未取得は未検証とし、要求した設定を実観測に変換しない。

ローカル Test も [Artifact Delivery](../contracts/artifact-delivery.md) の固定 commit/path/size/SHA-256 と実体 bytes で Manager へ返す。ローカルパスや完了通知だけを返さず、再生成で補わない。原本は非公開に保全し、公開 Git には安全性確認・公開操作承認済みの派生版のみを置く。kubeconfig、Secrets、実際の非公開 environment/context/cluster/task ID は公開しない。配送不能は delivery blocked として残す。

Implementation Ready、Deployment Ready、Merge Readiness、Issue Completion は別判定のまま。変更ごとの mandatory full suite は追加せず、最小の関連検証を選び、同一対象・必要能力・有効期限と現行契約に適合する既存証跡は再利用する。schema/CLI は venue や cluster 実測の真実性を証明しない。Manager が原本・対象 identity・独立性を確認する。

## 終了通知後のゲート

通知の `completed` は基盤上の終了であり、業務完了ではない。Manager は毎回以下を実行して判定を記録する。

1. 通知と一致する task_id/attempt/対象 revision の handoff と全成果物を取得する。タスクが落ちて handoff がない場合は Manager が失敗観測を記録し、成功とみなさない。
2. Issue 工程は `python scripts/validate_handoff.py handoff.json`、Knowledge は `python scripts/validate_knowledge.py handoff.json` で形式・参照整合性を確認する。不正な handoff は `INVALID_HANDOFF` として依存後続を止める。
3. Issue 工程は assignment が起動時の割り当てと一致することを確認し、Issue の全必須 AC 原文と出典を認可済み入力に照合する。一部でも欠落・改変があれば blocked。schema は AC の完全性を証明しない。Knowledge では AC の代わりに入力 raw_findings の件数・ID・観測・出典・revision と assignment の一致を確認する。
4. artifact の実体、revision、根拠の内容、テストコマンドと実際の結果を読み、担当 ac_ids と assignment.completion_criteria を検査する。Knowledge は全入力 finding の根拠付き採否・保留判断を確認する。根拠が到達不能・不足なら blocked、既知の不合格や阻害指摘なら failed。
5. `status=completed` の自己申告と業務ゲートの両方を満たした場合だけ依存後続を起動する。Knowledge のゲートは開発の依存後続に適用しない。Research / Implementation / Test の `covered` はそれぞれの担当工程の完了であり、製品の最終 AC 合格ではない。担当外の AC は未検証のままでも工程を完了できるが、covered にしてはいけない。Manager だけが後で全 Issue AC の final_assessment を行う。
6. 合格した handoff、成果物実体、AC 原文、採用判断、未確認点、後続の責務を**後続の初回入力**に組み込む。後から前の会話を参照できることを前提にしない。

## 失敗・不足・再試行

| 状況 | Manager の処置 |
| --- | --- |
| 必須 AC 原文が一つでも欠落 | Issue 工程は `MISSING_ACCEPTANCE_CRITERIA` で blocked。専門役割側は外部取得・推測しない。Dots / Manager が既存の認可済み情報源から原文を補完し、出典付きの修正入力を作る。認可がない/取得不能なら人間に不足を報告して停止する。 |
| 修正可能な入力・成果物の不足 | 依存後続を停止し、配送だけの不足なら delivery の有限再取得を行い、実行の修正が必要なときだけ実行予算内で新しい独立タスクを起動する。 |
| テスト不合格・レビュー阻害指摘 | Implementation 等の責任工程へ戻し、修正 revision に対して必要な Test/Review を再実行する。古い revision の合格を転用しない。 |
| 基盤失敗・handoff 不在 | 部分成果物を回収し Manager が失敗記録を作る。存在しない成果物・テスト結果を埋めない。 |
| 権限・接続不足 | 設定や Secrets、永続アクセスを変更せず阻害を報告する。別経路を使う場合も既存認可の範囲に限定する。 |
| attempt=3 でも未完了 | `RETRY_LIMIT_REACHED` を記録して停止し、人間に残件を返す。自動で回数をリセットしない。 |
| Knowledge の根拠不足・遅延・失敗 | 原根拠欠落は MISSING_INPUT。Issue/AC 不在だけでは blocked にしない。Knowledge の状態と再試行を別管理し、開発は止めない。 |

Issue 工程の再試行の `upstream` には直前の同一 role・同一 Issue の handoff を `retry_of` として含め、attempt は前回 +1 とする。他工程の依存は `dependency` として保持する。基盤失敗時の handoff は Manager が観測根拠付きで代行記録し、summary に代行であることを明示する。前回内容を上書きしない。Knowledge は専用契約の retry_of で同じ知識処理範囲の直前試行を追跡する。工程をまたぐ修正ループも同じ論理工程の回数を消費し、いずれかが上限に達したら依存する開発ループを停止する。

## 開発完了と配送の別判定

最終報告では下記の状態を個別に `verified / failed / blocked / not_requested / pending` と根拠付きで記す。前の段階の成功を次の段階の成功としない。

| 検査対象 | 根拠 |
| --- | --- |
| 実装完了 | 対象 commit/差分、各 assignment の工程完了、Test/Review の業務ゲート。これだけで Issue 全体を合格としない |
| Issue 全体の最終達成 | Manager の final_assessment と全必須 AC の実測根拠。未検証があれば achieved にしない |
| GitHub remote 反映 | feature branch の remote head SHA とローカル SHA の一致 |
| Draft PR | PR URL、base/head、head SHA、draft=true を認可済み経路で取得 |
| CI | 同一 head SHA のチェック/run の結果。queued/in_progress は pending、未実行は未確認、CI がない場合は明示して成功としない |

CLI Git と GitHub 連携は別経路。GitHub 連携の成功は CLI の認証・ネットワーク障害解消を証明せず、その逆も同じ。失敗した経路と成功した経路を個別に報告する。main への直接 Push は行わない。現在の Phase 1-1 作業の merge / auto-merge 禁止と、将来の権限は次節で分けて扱う。

## マージ方針

現在の Phase 1-1 作業では Draft PR を維持し、merge と auto-merge の有効化を行わない。Ruleset・ブランチ保護・アカウント設定の変更も行わない。

ユーザーが許可した将来方針として、**Phase 1-2 以降は品質ゲート通過後に AI がマージできる**。Manager または明示的に割り当てられた実装担当が、既存の認可済み GitHub 経路で実行する。これは本作業での即時実行許可ではない。

マージ前には対象 PR の [Merge Readiness v1.0](../contracts/readiness.md) を判定する。Issue 全体の achieved はマージ前の必須条件にしない。最新 head/base/対象 revision/設定/必要な merge-group の証跡、独立 Test、AI Review、CI、GitHub 必須 checks・review・Ruleset・queue、依存関係、ユーザー許可を個別に照合する。Implementation Ready と Deployment Ready は独立評価し、自動配備または配備影響不明の場合は Deployment Ready も要求する。GitHub の必須 checks/review/Ruleset/ブランチ保護を AI が無効化・書き換え・管理者権限で迂回してはならない。必須条件の失敗・未実行・未承認、head/base/設定/対象 revision 更新、証跡期限切れがあれば停止して必要な再検証を行う。auto-merge を使う将来運用でも同じ条件を適用し、今回の PR では有効化しない。

## Readiness と Issue Completion の運用

1. Research は Implementation Ready と Deployment Ready の条件、未決設計の比較・推奨・根拠、ユーザー判断/承認が必要な箇所を分離する。Manager は環境未準備だけで実装可能な範囲を一律停止せず、必要な設計・許可・依存が揃った assignment を確定する。
2. Manager は全 AC 原文、最早検証段階、対象 PR の AC、配備影響と現状の保護設定を current context に確定する。premerge で達成可能な必須条件の不合格・未実行・承認待ちを deferred に逃がさない。
3. Implementation の固定成果物を独立 Test/Review に渡す。CI、独立 Test、AI Review、GitHub 必須条件を別証跡として取得し、[readiness CLI](../scripts/validate_readiness.py) を現在の context と実行する。handoff と一緒に配送するときは `--handoff` も指定する。形式検査の成功と ready と実行許可を区別する。
4. 本当にマージ・配備後にしか確認できない AC は理由・担当・環境・検証方法・失敗時対応・分類根拠を記録し unverified のまま保持する。GitOps 等のマージによる配備がある/影響不明なら Deployment Ready を追加必須条件とする。
5. 許可されたマージ操作の直前に現状と期限を再確認する。更新で ready を失効させ再検証する。今回の作業に与えられた PR/merge/auto-merge 禁止をこの将来手順で上書きしない。
6. PR ready やマージ成功では Issue を完了扱いにしない。未検証が残る PR に自動 close キーワードを使わない。マージ・配備後の実測を回収し、Manager だけが全 Issue AC を final_assessment で判定する。全 AC 実測 met と必要な統合・配備完了が揃った場合のみ achieved。複数 PR/repo は [集約 CLI](../contracts/issue-completion.md) の独立 context pin、全必要集合、現在証跡、最新履歴 pin と最終 Issue Handoff を照合する。失敗・未確認は未完了で追跡する。

## Knowledge と変更単位

Manager は候補の配送と進捗のみ管理し、取得済み根拠を Knowledge 専用入力として明示的に渡す。Knowledge Agent が raw の保全、抽象化、採否、記事更新を担当する。知識用 Issue/PR を分けることも開発差分に含めることも可能であり、1 Issue=1 PR や repo ごとの分割を絶対条件にしない。権限とレビュー可能性に応じて変更単位を選ぶ。

公開前には内容を読み、実際の非公開 task/thread/message ID、私的会話、個人情報、内部メモ、認証情報、運用ログを除外する。公開サンプルは架空の識別子・プレースホルダーのみとし `synthetic sample` を明記する。知識候補やメタデータの public_safe 自己申告だけで公開を承認しない。

Phase 1-3 P-B では [collector](../contracts/knowledge-collection.md) の scan/reconcile を節目に実行し、全件検証後に inbox/event/cursor を一括保存する。Manager は最新 state pin と別経路認可を保持し、plan を確認して reserve/dispatch intent を永続化してから独立 Knowledge を起動する。開始不明は照合まで停止し、取得済み output は delivery から再開する。Git 確定後の中断は固定 commit の全 bytes 照合で追認する。collector 自身は Agent を起動せず、schedule 登録・有効化、P-C context/ack と P-D 実運用実証は含まない。後続役割への知識配送は knowledge-context と取得済み記事実体を初回入力に渡し、固定 revision・適用条件・例外・出典・状態を確認する。


Issue Completionには全AC実測に加えて必要な統合完了が必要。全premerge ACがmetでも未マージならunverified。Readiness/contextのissue_integration_scopeで単一PRと集約待ちを分離し、複数PR・repo/範囲不明は単一PRからachievedにしない。複数PR・repoは独立[Issue Completion契約](../contracts/issue-completion.md)で全必要集合と固定証跡を検証する。全AC met・統合待ちの中間Handoffではfinal_assessmentを省略し、Readiness artifactで追跡する。

Readinessの配送にはartifact_id、Handoff基準のローカルlocator、実体bytesのsha256 digest revisionを使用する。`validate_readiness.py --handoff`は実体の読み取り・評価対象ファイルとの同一性・digestを照合する。旧DraftのReadinessは追加必須項目を確認して移行する。詳細と限界はReadiness契約を参照。

## Artifact Delivery と試行分類

[配送契約](../contracts/artifact-delivery.md) の公開前安全性確認/公開承認、反映後 Publication Receipt、
別の Consumer 利用承認、Consumer CLI 全件検査と Consumption Receipt を工程ゲートへ追加する。
元の bytes を手書き再構成しない。Public repo に非公開原本・実識別子・内部ログ・秘密情報は置かない。
公開派生版の利用には original と別の利用範囲の承認が必要。公開済みは承認済みを意味しない。

従来の同一論理工程の実行上限3回を維持し、dispatch 最大3回、execution 最大3回、delivery 最大3回を
別カウンタで管理する。Agent 開始確認後の失敗と開始前の dispatch failure を区別し、
配送未完了は delivery failure として扱う。開始不明は照合まで再送を止める。
いずれかの最終許容試行が未完了なら RETRY_LIMIT_REACHED で依存ループ停止。
過去の B1 Implementation 3回と terminal 状態は不変。分類変更・scope の言換えでリセットしない。
再開には新たな明示承認、理由、各1〜3の新予算、scope、過去履歴 pin と関係がすべて必要。
[retry CLI](../scripts/validate_retry.py) で新 epoch と旧履歴の完全保持を検査する。
配送成功は Readiness や製品実装再開許可にならない。ユーザーが同一 head の独立 Review と CI を
PR 前に要求した場合、その確認と後続指示まで PR を作成しない。

Consumer は format/拡張子だけで内容検査を省略しない。再利用では全 bytes を新規取得・再検査した出力を使い、`--verify-receipt` が旧出力の改変を検査したとは扱わない。

## 依存準備 PR の追加契約

[Readiness 1.1](../contracts/readiness.md#依存準備-prreadiness-11) の準備区分は Manager が固定 context で選択する。通常 PR の製品 AC ゲートは維持する。準備 PR はデプロイ影響 none・aggregate_required のみ。非空の工程条件、関連製品 AC、固定成果物、独立 Test/Review、後続検証責任を引き渡し、工程達成を製品 AC 達成や操作許可へ変換しない。起動入力には pr_kind、preparation 全体、独立 context pin、実体 bytes を含める。Implementation の自己検証は独立 Test/Review を代替しない。

Issue Completion 1.1 は準備 PR を型付き required メンバーとして保持する。
空の製品担当 ac_ids と関連 AC を分離し、歴史的 Readiness の親を成果物 root として
context の固定 BlobRef と照合する。全必要 merge 集合と後続 standard PR の全製品実測を要求し、
工程合格を製品達成へ変換しない。版互換・配送・検証手順は
[Issue Completion 契約](../contracts/issue-completion.md) と [合成例](../examples/issue-completion/README.md) を参照。

## Bounded capacity (Delivery 1.3)

[Capacity and compatibility contract](../contracts/artifact-capacity.md): explicitly select 1.3 for up to
256 artifacts; legacy 1.0/1.1/1.2 retain 128. All four delivery records must match.
Per-file 16 MiB, bundle 64 MiB, tree/slot/candidate limits and all approval gates
remain unchanged. Preserve originals and complete closure; never overwrite old
delivery outputs. Dispatch/execution/delivery remain each at most 3. Candidate
1.3 requires System CI and independent Review before merge and canonical use.


## Model routing for explicitly approved new dispatches (2026-10-13)

Insert the [Best Effort routing workflow](workflow-model-routing.md) between
complete authorized task-input preparation and Manager's existing dispatch-intent
reservation/create step. Manager stays Dots. Research/Design and Review request
gpt-6.1-sol high; Implementation/Test/Knowledge request gpt-6.1-sol medium;
service_tier=default explicitly selects Standard. Only a separately bounded routine
read-only consumer may request Luna low. Astra requires a manual exact
scope/model/effort/budget approval and never repairs access/input/transport errors.

Use a separate private routing record with role/scope, policy revision, requested
settings, task reference, source-qualified observations and null unknown usage.
BestEffort runtime unknowns do not block this new authorized trial; Strict opt-in
does, and qualified mismatch blocks/flags Manager without fallback. UI settings
and aggregate usage cannot establish actual per-task execution. All existing
AC/Handoff, independent Test/Review, current-head CI, Delivery, security, approval,
Readiness and retry gates above remain unchanged. Routing eligibility is not
quality pass or dispatch reservation. Preserve latest budget pins and histories;
old scope redispatch needs a new explicit decision, not an in-progress setting edit.
The historical pilot is consumed 1/1 with PINNED_ARTIFACT_UNAVAILABLE, cause unknown;
evaluation count remains 3/6. This feature starts no task or paused backend work.
