# Readiness v1.0 / v1.1 と Issue Completion

[readiness.schema.json](readiness.schema.json) は PR ごとの判定記録、[readiness-context.schema.json](readiness-context.schema.json) は Manager が取得した現在の対象・AC・保護設定の照合用スナップショット。Issue handoff v2.0 と Knowledge v1.0 は変更しない。readiness は独立した v1.0 の artifact として locator・固定 revision/digest を handoff に記録し、実体を配送する。単に handoff のバージョンを置き換えない。

## 四つの判定

| 判定 | 必須条件 | 他の判定との関係 |
| --- | --- | --- |
| Implementation Ready | 担当範囲の設計、実装許可、実装依存の合格 | 配備環境がなくても実装可能な範囲を進められる |
| Deployment Ready | 配備環境、rollback/失敗時対応、配備許可、配備依存の合格 | Implementation Ready と独立。配備操作の許可を新たに与えない |
| Merge Ready | Implementation Ready、PR 内の premerge AC 実測合格、下記すべての merge checks、postmerge/deploy AC の追跡 | 配備影響 automatic / unknown なら Deployment Ready も必須。Issue achieved は要求しない |
| Issue Completion | 全 Issue AC の実測結果を Manager が確認 | 全件 met かつ必要な統合完了のときだけ achieved。AC/統合の失敗は not_achieved、残りは unverified |

`*_readiness.status` は ready / blocked。checks の verdict は pass / fail / pending / not_applicable。blocked な記録も正常な契約であり、CLI exit 0 は ready を意味しない。各 checks.dependencies は当該工程で必要な依存物・前工程の固定成果物・未完依存を列挙した証跡を参照する。依存がない場合も確認根拠を残す。依存の欠落を pass にしてはいけない。

未決 API/DB 設計は Research が選択肢・比較軸・推奨・根拠・不確実性を提示し、技術的に決められる部分とユーザー判断/承認が必要な部分を区別する。必須設計や承認が未解決の範囲は Implementation Ready にしない。Manager が依存しない実装範囲と assignment を明示すれば、その範囲は進められる。配備環境未準備だけで実装可能な作業全体を停止しない。

## PR と現在の証跡

`subject` は repository、pr_number、head_sha、base_sha、target_revision、config_revision、merge_group_sha を持つ。SHA は40桁の固定値。PR 未作成の計画時のみ pr_number=null を許すが Merge Ready にはできない。target_revision は検証した実際の commit（head、合成 merge commit、merge-group 等）。config_revision は判定に影響する CI・Ruleset・承認条件・環境設定の固定版またはダイジェスト。変更された設定を同じ識別子で使わない。

各 evidence は対象 subject、observed_at、valid_until、locator、observation、producer、independent、ac_ids を持つ。観測内容には対象変更、実行コマンド/チェック名・run ID、結果、検証環境、依存物と制約を記す。`kind` は証跡の用途を区別し、CI/AI review の証跡を GitHub required review の代用品にはできない。独立 Test/AI Review は実装者と異なる producer と独立性の確認が必要。ID の違いだけでは実際の独立性を証明できないため Manager が起動・成果物来歴を照合する。

merge checks は **ci / independent_test / ai_review / github_checks / github_reviews / github_ruleset / github_queue / authorization / dependencies** を個別に記録する。CI 成功だけで独立 Test や Review を合格にしない。GitHub required checks、required reviews、Ruleset と queue はそれぞれ実設定と実状態を認可済み経路で確認する。適用不要な checks/reviews/queue のみ not_applicable を許し、現在の github_requirements=false と根拠が必要。CI、独立 Test、AI Review、Ruleset、許可、依存を省略できない。AI Review 合格を GitHub の必須承認に自動置換しない。

queue 必須時は merge_group_sha が必要。queue 投入前は blocked の記録となり、投入をマージ可能性と同一視しない。GitHub が発行した merge-group と必要な対象 revision の checks を回収して再評価する。本 CLI は queue 投入・マージ・設定変更を実行しない。保護ルールを無効化・変更・管理者権限で迂回しない。

Manager は評価時と実行直前に current context を取得し、head/base/target/config/merge-group、PR 対象、AC 原文・分類・スコープ、配備影響を照合する。更新・期限切れがあれば古い ready を失効し、該当検証と Test/Review を再実行して新しい記録を作る。既存証跡の SHA や日時の書き換えで更新しない。本 v1.0 は保守的に記録内の全証跡を同じ current subject と照合する。異なる revision の履歴は以前の記録に保持し、新しい評価へ無条件転用しない。

policy_observed_at / policy_valid_until と各証跡の期限を必須とし、`observed_at <= evaluated_at <= 検査時刻 < valid_until` を検査する。期限の妥当な長さは Manager が変更頻度と実際の保護条件から決める。CLI はその妥当性や現在時刻以降の変更を保証しない。外部取得とマージの間の競合は GitHub の実保護設定・queue と実行直前の再確認で扱う。

## AC、延期、配備

全 Issue AC の原文と出典を acceptance_criteria に保持し、Manager が PR に必要な pr_ac_ids を確定する。複数 PR の Issue では担当外 AC が未検証でも対象 PR を評価できるが、全 Issue AC は ac_results に一度ずつ記録する。PR に必要な AC を外す変更は Manager の明示的判断と current context の更新が必要。CLI は原文の完全性やスコープ選定の正しさを推測しない。

verification_phase は達成を検証できる最も早い段階（premerge / postmerge / postdeploy）。未実行・環境未準備・承認待ち・不合格を理由に premerge を postdeploy に付け替えてはいけない。Manager は分類を原文・Research の検証設計・独立 Test/Review に照合する。

postmerge / postdeploy にしか確認できない AC を残して Merge Ready にするには、outcome=unverified と deferred が必要。deferred は **reason（前に検証できない理由）、owner、environment、method、failure_action、evidence_ids（分類根拠）** をすべて持つ。既知の not_met を unverified に戻して隠さない。premerge AC の deferred は常に拒否し、premerge の不合格・未実行・未承認はマージを止める。deferred は合格でも免除でもない。

GitOps 自動同期、workflow 配備、マージ起点の配備を調査し deployment_effect を none / automatic / unknown で記録する。none にも明示的根拠が必要。automatic または unknown は Deployment Ready 必須という fail-closed 判定。Deployment Ready の environment は対象環境・アクセス・設定・必要データ・検証手段、rollback は検知・復旧手順と担当を含む。証跡がない場合は pending として blocked を返す。

postmerge の実測結果には merged_at、postdeploy には merged_at と deployed_at が必要。観測は必要イベント以降でなければ met / not_met にできない。全 AC の実測を得て初めて Issue achieved を記録し、Manager の handoff.final_assessment と照合する。マージしただけでは Issue を閉じない。未検証を残した PR では `Closes/Fixes/Resolves` 等の自動 close 指示を使わず、通常の関連リンクと未検証 AC・検証責任を記す。失敗時は Issue を未完了として復旧・修正・再検証へ戻す。

## CLI と限界

```bash
python scripts/validate_readiness.py readiness.json --context current-context.json
python scripts/validate_readiness.py readiness.json --context current-context.json --handoff handoff.json
```

CLI は JSON Schema、参照、対象一致、時刻、状態整合性と AC 実測の記録条件を検証する。exit 0 は記録として整合、exit 1 は不正/取得失敗、引数不備は exit 2。blocked の正常記録も exit 0 なので、Manager は各 status を必ず読む。Handoff を併用する場合は `--handoff` で原文・Issue・最終判定の一致を必ず検査する。v2.0 単体 CLI は後方互換のままで、readiness を自動発見しない。

`--at` は明示時刻で架空例や過去記録を再生するオプション。出力は REPLAY と表示し、現在のマージ許可に使わない。通常の評価は現在UTC時刻を使う。context は Manager が別途取得した現状であり、古い assessment を複写して current と称してはいけない。

**schema/CLI は証拠の真偽、原文の完全性、実際の独立性、live GitHub のマージ可否、実際の配備や権限を証明しない。** readiness=ready は操作権限を付与せず、ユーザーの明示的許可と GitHub の実保護条件が別途必要。証跡取得不能・設定不明・期限切れは再確認まで進めない。

## Issue全体の統合とPhase 1-2の境界

`issue_integration_scope` を assessment と current context に必須化する。Manager は Issue の全必要変更を確認し、`single_pr`（必要な統合がこの1 PRのみ）、`aggregate_required`（複数PR・複数repo等）、`unknown` を確定する。PRのpr_ac_idsとは別のIssue全体条件であり、scopeの縮小を推測してはいけない。

全premerge ACがmetでも、merged_at=nullならissue_completion=unverified。single_prでもマージ済みだけでは不足し、`issue_integration` のpassと `kind=issue_integration` の証跡が必要。証跡は全Issue ACを対象とし、現在のsubjectと一致し、マージ以後の観測であること。実際のマージ結果と必要な統合完了をManagerが確認する。全AC metと統合passが揃って初めてachievedになる。統合pendingでもPRのMerge Readyは妨げない。

複数PR・複数repoの依存一覧、各マージrevision、統合環境と全体検証は独立[Issue Completion v1.0](issue-completion.md)で集約する。本CLIでaggregate_required/unknownを統合passやachievedにすることはできない。Managerは依存を明記し、本PR契約ではunverifiedを保持し、別のIssue Completion CLIと最終Issue Handoffで全体を判定する。単一PRのマージから全体達成を推論しない。

Handoff v2.0の既存schema/CLIは変更しない。全AC metでも統合がpending/failの中間報告は、`final_assessment`を省略し、Readiness artifactでpendingはissue_completion=unverified、failはnot_achievedとして追跡する（ACの実測をunverifiedへ偽装しない）。最終achievedの発行は統合完了後だけ。集約待ちも同様に最終判定を保留する。

## Readiness成果物の実体照合

assessmentの`artifact_id`に一致するHandoff artifactsの1件を要求する。kind=other、locatorは配送されたローカルReadiness JSON（相対パスはHandoffファイルのディレクトリ基準）、revisionは`sha256:<実ファイル全bytesの64桁hex digest>`とする。`--handoff`はlocatorの存在・読み取り、CLIが評価したファイルとの同一パス、初回raw bytesからのparse・schema/意味検証、初回bytesのSHA-256、参照先を再読込したbytesとの完全一致を検査する。欠落、別ファイル、改変、読み取り不能、digest不一致はexit 1。URLを自己申告しただけでは成功せず、認可済み経路で事前に実体を配送する。コピー配送時はコピーした実体へlocatorを設定し、元の固定digestを保持する。

digestはJSONを整形し直して計算するのではなく、そのままのファイルbytesから計算する。参照ID・locator・digestも含む配送元Handoffの真正性はManagerが別途確認する。実体と参照を一緒に偽装した場合の真偽や署名認証まで保証するものではない。

今回のDraft内改訂ではReadiness v1.0の必須項目を追加する。旧DraftのReadiness/contextはそのまま受理せず、Managerが統合scope・状態・証跡を確認して追加し、artifact_idと実体digestを配送する。バージョンは未リリースのv1.0を維持し、Handoff v2.0 / Knowledge v1.0の互換性は維持する。

## 依存準備 PR（Readiness 1.1）

通常 PR の 1.0 形式と必須 AC 条件を維持する。1.1 は assessment と Manager context の両方に
`pr_kind=standard|preparation` と `preparation` を必須とする。standard は preparation=null、
pr_ac_ids は非空。preparation だけ pr_ac_ids=[] とし、deployment_effect=none、
issue_integration_scope=aggregate_required に限定する。単なる AC 集合の縮小ではない。
旧 1.0 Consumer は 1.1 と追加フィールドを拒否するため、黙って通常 PR と解釈しない。

Manager は準備のみという scope_reason、非空 related_ac_ids、製品 AC と異なる ID の非空
conditions（原文、method、expected_result）、固定 artifacts、followup、全製品 product_outcomes を確定する。
同じ preparation 全体を assessment に記録し、配列順も含め context と完全一致させる。
followup は各関連 AC に owner/environment/method/dependencies/failure_action を必須とする。
依存がないという判断も dependencies に明記する。工程条件を acceptance_criteria に登録しない。

preparation_results は各条件を一度ずつ測定し、met だけを Merge Ready の候補とする。
preparation_measurement の evidence は condition_ids と全 artifact_ids を参照する。
独立 Test と AI Review も全条件・全固定成果物を同じフィールドで対象にする。
既存の producer/independent/subject/期限検査と全 merge checks を維持する。
artifact は id、assessment 基準のローカル locator、target_revision と等しい40桁 revision、
size_bytes、raw sha256 を持ち、CLI は全 bytes を読み照合する。証跡本文の真実性や実際の独立性は
Manager が固定成果物・起動来歴と照合する。schema の pass はその代替ではない。

全製品 AC の原文・最早段階・実測状態は保持する。product_outcomes は Manager の既知状態を
全件固定し、ac_results との差を拒否する。保守的な境界として、関連外を含む一つでも既知の
not_met があれば準備 PR の merge は blocked。既知失敗を unverified に戻さない。
準備のみの PR が未実装の製品 premerge AC を unverified のまま残すことは延期ではない。
その製品を実装する通常 PR の premerge ゲートは引き続き必須であり、deferred や段階変更で逃がさない。
Manager は既存 PR を準備へ分類し直して失敗・未承認・未実行の通常ゲートを回避してはならない。
準備のマージは Issue 達成を示さず、全製品実測と全必要統合を独立 Issue Completion で確認する。

1.1 CLI は認可済み別経路で Manager が固定した `--context-sha256` を必須とする。
ダウンロードした receipt や assessment 自身の hash はこの信頼の起点にならない。
認証・署名サービスではなく、正しい独立 pin と最新状態の取得は Manager の責任。
新形式も操作権限や Consumer 利用承認を与えない。Handoff 2.0 / Knowledge 1.0 / Delivery 1.2 は変更しない。

```sh
python scripts/validate_readiness.py readiness.json --context current-context.json \
  --context-sha256 MANAGER_INDEPENDENT_CONTEXT_PIN --handoff handoff.json
```

### 証跡期限の選択

固定コードに対する測定と可変 GitHub policy の観測は別の寿命を持つ。Manager は測定対象と
保護条件の変化頻度に応じて各 evidence.valid_until と policy_valid_until を選ぶ。
固定コードだから無期限とはしない。全証跡について既存の時刻不等式を維持し、subject/config の
変更は期限内でも即失効する。旧期限を書き換えず、新たな確認と新記録を作る。
1.1 は期限検査を緩和しない。
