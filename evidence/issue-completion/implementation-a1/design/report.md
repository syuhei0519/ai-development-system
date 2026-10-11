公開安全候補 / edited derivative / 未公開

実際の製品状態や実行結果を示さない技術設計案。公開前の独立安全性レビューと個別公開承認は未実施。正常ケースはsyntheticだけを想定する。

# 複数PR・複数repo Issue Completion集約契約：設計提案


## 1. 結論と比較

**採用推奨: 独立した Issue Completion v1.0 + current context + offline validator を追加し、Readiness v1.0/Handoff v2.0のschemaと既存判定を維持する。** PRのMerge Readyは引き続き各Readinessで判断する。複数PRの最終Issue achievedは、新契約を照合したManagerだけが発行する。aggregate_requiredをsingle_prへ書き換えない。

| 案 | 変更 | 評価 |
|---|---|---|
| A: 現行Readinessのaggregate_required禁止だけを解除 | 小さいコード差分だが単一subject/merged_at/deployed_atしかない | 不採用。依存PR、省略repo、異なる配備や古いheadの混合を検知できない |
| B: Readiness v2へsubject配列等を全面統合 | schema/CLI/Handoff pairing/既存fixtureの移行が必要 | 不採用。PR mergeとIssue完了の責務混在、既存利用者の破壊的変更が大きい |
| C: 独立Issue Completion契約を追加 | schema 2件、CLI 1件、tests/fixtures/docsを追加 | 採用。現行安全境界を維持し、明示的な集約入口だけを追加できる |
| D: Managerの文章だけで集約 | 実装差分なし | 不採用。機械的な完全性、expiry、参照/履歴照合がない |

「最小」は行数の最小ではなく、既存契約を緩めず不足する集約だけを追加する最小。新サービス、追加API、署名基盤、GitHub App、課金、PAT、Secret、Ruleset変更は不要。取得は既存の認可済み経路、検証はローカルJSON/bytes、実行判断はManagerに残す。

## 2. 現行コードで確認した制約

設計対象の既存契約を相対pathで示す。採用時は認可済みの固定revisionで再確認する。

- `agents/research-design.md`, `agents/manager.md`: 工程completedと製品AC合格は別。全AC metでも統合待ちはfinal_assessmentを省略。集約は後続依存。
- `contracts/readiness.md:59-65`, `scripts/validate_readiness.py:158-181`: integration passにはsingle_pr、実merge、全ACのintegration証跡が必要。aggregate_required/unknownでachieved不可。
- `scripts/validate_readiness.py:53-93`: assessment/contextのsubject・全AC原文・scope一致、全証跡の同じsubject、期限を検査。複数repoを単一subjectに詰められない。
- `scripts/validate_readiness.py:194-240`: --handoffはartifact_id、kind=other、実体path、初回raw bytes、再読bytes、sha256、Issue/AC/最終結果を照合する。
- `scripts/validate_handoff.py:67-80`: final_assessmentはACだけから全体outcomeを導出する。全AC met + 統合pending/failをfinal_assessmentへ表現することはできない。原ACを偽装せず中間finalを省略する既存運用を維持する。
- `contracts/artifact-delivery.md`: 原本/派生版、安全性/公開操作/Consumer利用承認、全bytes検査を分離。receipt authority_granted=false。独立pinをbundle自身から推論しない。履歴と試行上限は不変。
- `tests/test_readiness.py`, `tests/test_readiness_binding.py`: 単一PRから集約完了不可、対象/期限、GitHub review代替不可、queue、初回bytes差替えを既に回帰検証。
- `.github/workflows/validate.yml`: contents:read、unittest discover、delivery記録検査、Handoff/Knowledge/Readiness CLIのsynthetic replay。新テストを同じworkflowへ追加し、既存required check名/保護条件を変更しない。

## 3. 信頼境界と判定責任

1. **Managerの現在context**は独立した認可済み取得から作る。assessmentの複写をcurrentと呼ばない。scopeの完全性、原文の出典、独立Test/Reviewの実体、取得経路の真正性はManagerが確認する。
2. **user approval / GitHub authority / delivery approval**は別。ユーザーの承認済みscopeは対象Issue・repo・操作・環境・有効条件を拘束する。GitHubのchecks/reviews/ruleset/queueと実actorの権限は別々に確認する。receipt、記事、Knowledge、schema passはこれらを生まない。
3. 新CLIは検査専用。merge/deploy/rollback/Issue close/reopenを呼ばない。操作直前の再取得はManagerの既存経路で実施する。新契約の合格でもGitHub保護やユーザーの個別禁止を迂回しない。
4. 集約判定の技術的readyとManagerの最終achievedを分ける。CLIは入力の整合性だけを判定し、主張の真実性・原文の完全性・live状態を証明しない。

## 4. 契約とJSON Schemaの具体仕様（実装対象、今回未実装）

追加ファイル案:
- `contracts/issue-completion.schema.json`
- `contracts/issue-completion-context.schema.json`
- `contracts/issue-completion.md`
- `scripts/validate_issue_completion.py`
- `tests/test_issue_completion.py`, `tests/test_issue_completion_binding.py`
- `examples/issue-completion/` 以下のsyntheticのみのfixtures

両schemaはDraft 2020-12、document_typeごとにschema_version const=1.0。全objectでadditionalProperties=false、全指定フィールドrequired。textはminLength=1かつJSON Schema pattern="\\S"、Git commitは小文字40hex、sha256は小文字64hex、RFC3339 timezone付きdate-timeをFormatCheckerで実検査。型boolを整数IDと同一視しない。JSONの重複キー、NaN/Infinity、BOM、余剰末尾を拒否するstrict readerを新入口で使用。既存Readiness/Handoff parserの挙動変更は今回の最小変更に含めない。

### 4.1 共通定義

以下はschemaへ機械的に展開する仕様表。`?T`はTまたはnull（フィールド省略ではない）。`T[]+`はminItems=1、ID参照配列はuniqueItems=true。nullは未確認を表し、合格条件では許さない。

| 型 | 必須propertiesと制約 |
|---|---|
| BlobRef | id:text, locator:text, sha256:64hex, size:integer>=1。実ファイルの全bytesを照合。artifact自身の自己hashを内部に置かない |
| Criterion | id:text,verbatim:text,source:text,verification_phase:premerge/postmerge/postdeploy。id/verbatim/sourceはHandoff原文と完全一致 |
| RequiredPR | member_id:text, repository:text, pr_number:?integer>=1, scope:text, ac_ids:text[]+, depends_on:text[], requirement_source:BlobRef。null PRは計画中のみ |
| RequiredDeployment | deployment_id:text, definition_state:unknown/defined, environment_id:text, workload_id:text, member_ids:text[]+, expected_sources:{repository,revision:40hex}[], expected_config_sha256:?64hex, image_requirement:required/none/unknown, expected_images:{component,digest:sha256-prefixed64hex}[], no_image_basis:?BlobRef。未確定ならunknown/null/空を保持しready不可。definedではsources非空/config非null、image requiredならimages非空、noneならno_image_basis必須 |
| Verification | verification_id:text, ac_id:text, phase:premerge/postmerge/postdeploy, member_ids:text[]+, deployment_ids:text[], environment_id:text, method:text, expected_result:text, owner:text, failure_action:text。同じACの複数必須subcheckを列挙可能 |
| ScopeDecision | scope_id:text, revision:64hex, status:approved/pending/revoked, authority:text, actor:text, decision_kind:required_scope/product_operation/delivery, scope:text, issue_id:text, member_ids:text[], deployment_ids:text[], allowed_actions:(assess/implement/merge/deploy/rollback/close_issue/publish/consume)[], evidence_refs:BlobRef[]+, observed_at,valid_until。文字列承認だけで操作可能としない |
| Proof | verdict:pass/fail/pending, evidence_ids:text[], reason:text。pass/failはminItems=1。not_applicableはこの型に設けない |
| Result | verification_id:text, outcome:met/not_met/unverified, evidence_ids:text[], reason:text。met/not_metはminItems=1 |
| ACResult | ac_id:text,outcome:met/not_met/unverified,verification_ids:text[]+,evidence_ids:text[]。必須subcheckの集合・結果から導出 |
| HistoryEvent | event_id:text,kind:head_changed/required_set_changed/config_changed/deployment_changed/expired/measurement_failed/rollback/revalidated/superseded,observed_at,affected_ids:text[]+,reason:text,evidence_refs:BlobRef[]。失敗/rollbackには実根拠必須 |

repository/環境名は単なるラベルでなくcurrent contextと完全一致させる。RequiredPRのAC対応は貢献範囲であり、1つのPRでAC全体をmetにする宣言ではない。非コードの必須repoもscope内のRequirementとして明記し、変更不要ならManagerの固定根拠付き判断を残す。

### 4.2 contextトップレベル（document_type=issue_completion_context）

必須fields:
`schema_version, context_id, issue, issue_integration_scope, scope_revision, scope_decisions, required_prs, required_deployments, required_verifications, current_members, current_deployments, observed_at, valid_until, source_refs, previous_assessment_sha256`。

- issue={id,source,title,acceptance_criteria:Criterion[]+}。issue_integration_scope=aggregate_required/unknown。scope_revisionはManagerが確定したscope文書bytesのSHA-256。unknownは受理可能だがready不可。required_prsは1件以上（同repo複数PRも可能）。同repo/pr_numberの重複禁止、member_idも一意。
- required_prsの全必要変更リストをManagerが完成させる。current_membersとのmember_id集合完全一致、required_deploymentsも同様。PR未作成・scope未確定はpendingとして保持する。PRの省略による空集合の全称合格を許さない。
- `required_verifications`は全ACを少なくとも1回参照する。verification_phaseより早い測定を完了証拠にできない。premerge ACを未実行のためpostdeployへ分類変更しない。premergeに加えて必要なpostmerge/postdeploy subcheckを追加できるが、原ACを差し替えない。
- `current_members`要素: member_id, state:unknown/open/merged/closed_unmerged/reverted, head_sha:?40hex, base_sha:?40hex, merge_sha:?40hex, merged_at:?time, observed_at,valid_until, evidence_refs:BlobRef[]。mergedにはmerge_sha/merged_atと取得根拠必須。revertedをmergedへ隠さない。
- `current_deployments`要素: deployment_id, state:unknown/pending/deployed/failed/rolled_back, sources:{repository,revision:40hex}[], config_sha256:?64hex, images:{component,digest}[], environment_id,workload_id, deployed_at:?time, observed_at,valid_until,evidence_refs:BlobRef[]。GitOps multi-sourceは全sourceを列挙する。
- previous_assessment_sha256は初回だけnull。以降はManagerの別管理の最新pinと一致。履歴の古い枝への巻戻しを許さない。
- scope_decisionsはdecision_kindでIssueの必要構成の確定判断、それぞれの製品操作承認、配送承認を区別する。deliveryのpublish/consumeは製品merge/deploy権限を代替せず、approvedなproduct_operationのactor/action/Issue/全対象member/deploymentが別に一致する必要がある。承認不要な操作を創設せず、今回の操作が対象scope/actor/action/environment/期限に含まれるか別途確認する。非公開承認実体を公開sampleへ入れない。

### 4.3 assessmentトップレベル（document_type=issue_completion_assessment）

必須fields:
`schema_version, artifact_id, assessor_role, evaluated_at, context_sha256, issue_id, acceptance_criteria, scope_revision, member_results, deployment_results, evidence, verification_results, ac_results, integration_readiness, issue_completion, reasons, history`。

- assessor_role const=manager。context_sha256は実体raw bytes。CLIの独立pinと一致する。
- `member_results`: member_id, readiness_ref:BlobRefまたはnull, readiness_context_ref:BlobRefまたはnull, readiness_handoff_ref:BlobRefまたはnull, gate_checked_at:?time, approved_head_sha:?40hex, actual_merge_sha:?40hex, merged_at:?time, merge_binding:Proof, historical_merge_gate:Proof。pendingでnullを許し、integration ready時は全必須PRの実体とbindingを必須にする。
- `deployment_results`: deployment_id, status:ready/blocked/failed/rolled_back, evidence_ids:text[], reason:text。構成はcontextのexpectedとactualを比較して導出。deployed_atだけでready不可。
- `integration_readiness`={status:ready/blocked, checks:{scope:Proof,required_merges:Proof,deployment:Proof,compatibility:Proof,measurement_coverage:Proof,current_evidence:Proof,authorizations:Proof}, evidence_ids:text[],reason:text}。全checks passかつ全AC metのときだけready。deployment対象ゼロでも適用なしと推測せず「必要配備なし」のscope根拠でpassを説明する。
- `issue_completion`: achieved/not_achieved/unverified。計算規則は第6節。
- `history`={previous_ref:?BlobRef,events:HistoryEvent[]}。初回はprevious_ref=null、events空でもよい。以降は前assessmentの全履歴を保持して追加する。変更のない単純再検査もrevalidatedイベントで記録可能。削除/変更/末尾切捨ては拒否。過去の成功・失敗は現在証跡配列に混ぜず履歴参照として保持する。

### 4.4 evidence

必須fields:
`id, kind, phase, member_ids, deployment_ids, verification_ids, ac_ids, binding, observed_at, valid_until, producer, independent, result, source_ref, observation`。

- kind=scope/authorization/merge_binding/deployment/compatibility/ac_measurement/integration/rollback/failure。
- phase=premerge/postmerge/postdeploy。scope/authorization等の管理証跡にも観測段階を明記し、ac_measurementへ型の読み替えをしない。
- result=pass/fail/pending、source_ref=BlobRefでコマンド/チェック名・run ID、環境、測定条件、結果の実体を取得して照合。URLだけ、自己申告のみではready不可。失敗も実行した結果であり未測定とは異なる。
- bindingはoneOfの閉じたobject。premerge={type:pr,member_id,subject:既存Readiness subject,scope_revision}、postmerge/postdeploy={type:integration,context_sha256,scope_revision,merged_members:{member_id,merge_sha}[]+,deployments:{deployment_id,sources,config_sha256,images,environment_id,workload_id}[]}。
- active集約証跡は保守的に**全構成vector**へ束縛する。postmerge証跡のdeploymentsは空でもよいが、postdeployは該当必須配備を含む全current deployment vectorへ一致する。array順序はID順へ比較用index化し、duplicate key/IDは拒否する。hash計算のための再serializeは禁止。
- premerge測定は元PR subjectのまま。actual mergeへの対応をmerge_binding証跡で別途証明する。premerge測定をpostdeployとラベル変更したりSHA/時刻を書き換えて再利用しない。
- `ac_measurement`は明示されたverification_id/ac_id/phase/対象/環境/結果に一致するものだけ採用。CI/receipt/記事/rolloutの存在は業務測定の代用品にしない。

### 4.5 schemaと意味検証の分担

schema: 列挙、固定version、required、additionalProperties、型/format、非空、minItems、oneOf、pass/met時evidence minItems、merged/deployed時の条件付きnonnull。
CLI: ID一意性・完全集合、depends_onの未知参照/自己参照/循環拒否、参照先kind/phase、原文完全一致、scopeの包摂、subject/構成vector一致、時刻順、独立producer来歴の参照、期待outcome再計算、raw bytes/hash/path照合、履歴連続性。
Manager: 原文の完全性、全必要PR/repoの網羅、承認の真正性、GitHub保護の実状態、merge結果/画像来歴/実配備、観測結果の真実性、Test/Reviewの実際の独立性。CLIの限界を合格文言で隠さない。

## 5. PRから統合環境までの結合と時刻

### 5.1 PRゲートの過去証明

各PRのReadiness/context/Handoffをraw bytesで固定する。premerge gateの再検証は**当該merge時刻を検査時刻とする履歴検査**として行う。`evaluated_at <= gate_checked_at <= merged_at < policy/evidence valid_until`を要求し、旧CLIのvalidate(data,context,now=merged_at)を内部利用する。merge_readiness=readyを確認する。これはREPLAYであり、現在のmerge許可には決して使わない。

承認head == 最終PR head、target/merge-groupの必要check対象が一致し、そのゲートが実際のmerge直前にも有効だったことをManagerが確認する。base/設定/queueの変更に対して直前snapshotを取り直す。最後の有効window外でmergeされた場合は過去承認の合格を偽造せず、missing/invalid historical gateとして停止し、明示的な対応をManagerへ返す。

squash/rebase/merge queueではhead_sha==merge_shaとは限らない。merge_bindingはGitHubのPR/merge観測とGitの結果tree/コミット範囲・検査targetとの対応を記録する。異なるSHAが正しい場合も対応証拠がなければpending。予期しない差分・変更取り落とし・revertを不合格にする。単なる同名branch/tag/merge日時だけでは証明できない。

### 5.2 現在の完了証拠

過去のmerge gateの期限が今切れていても「その時刻のゲートが有効だった」という履歴事実は消さない。一方、**現在achievedに採用するAC測定・integration・配備・scope/current context証跡は今も有効でなければならない**。premerge測定も現在AC結果へ用いるなら今の有効期限と対象対応を検査する。期限切れなら新しい適切な測定を実行して別証跡を作る。過去ゲートの延命のためにSHA/日時を上書きしない。

active証跡とcontextは `observed_at <= evaluated_at <= now < valid_until`。境界のnow==valid_untilは失効。future時刻も拒否。postmerge測定は関係する全必須mergeのmax(merged_at)以降、postdeploy測定はさらに全対象配備のmax(deployed_at)以降。最小実装では全必要merge/全対象配備を待って全体integrationを測る。

imageのタグ一致では不十分。build provenance/source→image digest、manifest/GitOps source revision→期待digest、実workload→観測digestをつなぐ。multi-arch index digestとruntime platform digestの差は固定provenanceで対応を証明する。CLIはネットワークから勝手にimage取得せず、既存取得証跡を照合する。Synced/Healthyだけで誤image・誤環境を合格にしない。

環境bindingには環境ID、workload、全source revisions、設定digest、componentごとのimage digestを含める。設定digestは対象範囲・算出法を明示しSecrets値を含めない。DB/永続volume/依存serviceなど、AC結果に影響する構成の識別/状態もsource証跡の観測に記録し、必要ならcontextの明示的な構成要素として追加する。省略で合格させない。

## 6. 完了導出・失効・失敗

処理順:
1. 読取/strict JSON/schema/実体binding失敗 → exit 1、現在の有効assessmentとして消費不可。過去の成功へfallbackしない。
2. trusted current contextと全scope/AC/必須集合を照合。不足を「必要なし」にしない。正直なpending記録は有効だがready/achieved不可。
3. PR履歴ゲート・merge binding・配備・実測を検査。required_verificationsの全件を一度ずつ結果に含める。
4. ACごとに、必須subcheckにnot_metがあればnot_met、未測ならunverified、全件metのみmet。AC原文を分割/短縮せず、subcheckでANDを表す。
5. 現構成で確認されたAC不合格、必須mergeのrevert、配備失敗/rollback、integration不合格が残ればissue_completion=not_achieved。全AC met・全必須merge・全必須配備・全統合checks pass・scope承認一致・有効証跡が揃う場合だけachieved。それ以外はunverified。integration_readinessは失敗時も不足時もblocked、reasonsで区別する。
6. Managerが原文/実体/業務根拠を最終確認し、achievedをHandoff final_assessmentへ記す。CLI exit 0だけでは不可。

既知の失敗を証跡期限切れだけでunverifiedへ戻さない。失敗観測はhistoryへ残し、同じ失敗の修正と再実測でのみ解決する。rollbackで旧成功構成に戻った場合も自動achievedにしない。新revisionのcurrent contextと再測定が必要。過去の失敗が別構成に属する場合はその構成を明記し、新構成の現状態をunverifiedから再評価する。

再評価trigger: PR head/base/target/merge-group/config変更、新必須PR/repo/AC/subcheck追加、scope/承認の変更・撤回、配備source revision/設定/image/環境変更、証跡/ポリシー失効、failure/rollback/revert。旧assessmentとeventsを保持し、新context+新assessmentを作る。新PR追加ではrequired集合が変わるため旧証跡の全体bindingを再利用不可。今回はイベント駆動監視を実装しない。Managerは判定時・実行直前・変化通知時に再取得する。継続監視自動化は別scope。

## 7. CLIとHandoff互換

提案CLI（まだ存在しない）:

```text
python scripts/validate_issue_completion.py completion.json \
  --context current-completion-context.json \
  --context-sha256 <MANAGER_INDEPENDENT_PIN> \
  --handoff manager-completion.handoff.json
# 2回目以降:
# --previous previous-completion.json --previous-sha256 <MANAGER_LATEST_PIN>
# synthetic replayのみ:
# --at 2030-01-01T12:00:00Z
```

--handoffを必須として正式集約入口を1つにする。--at時はREPLAYを明示し、現在の完了/操作判断へ使わない。contextとpreviousのpinは別経路でManagerから取得し、bundle内hashを権威にしない。--previousの省略可否はcontext.previous_assessment_sha256で決める。履歴の初回偽装をManagerの最新台帳pinで防ぐ。

exit 0=記録整合（blocked/unverified/not_achievedも含む）、1=不正/読取不能/期限切れのactive証跡/矛盾、2=引数不備。出力はmode、integration status、issue_completion、理由を明示し、権限付与なしと表示。期限切れ証跡を現在のactive入力に残したままvalidとはしない。失効後の新pending記録では旧証跡をhistoryに移す。

Handoff v2.0を変更しない。completionをkind=other、id=artifact_id、locator=配送されたlocal JSON、revision=sha256:<raw digest>で参照する。全参照実体を先に取得し、初回bytesからparse・validate・hash、再読一致を検査する。remote locatorを勝手にfetchしない。refはbundle root内の通常ファイルに限定し、symlink/escape/別ファイル/同内容別pathを拒否。size/hash改変や読み取り中変更もexit 1。

- **PR専用Handoff**は従来Readinessとpairingし、aggregate_requiredのissue_completion=unverifiedを維持する。
- **Issue最終Handoff**は独立completionとpairingする。集約achieved Handoffを各PR Readinessの--handoffへ渡すと現行コードは正しく矛盾を拒否するため、同じHandoffへ混ぜない。
- final_assessmentがあるときはrole=manager、全原AC/結果/根拠がcompletionと一致必須。根拠は同一実体へのmappingを照合する。最終achieved発行時はfinal_assessment必須でstatus=completed。
- 全AC met + integration pending/failではfinal_assessmentを省略しcompletionでunverified/not_achievedを追跡する。Handoff v2のACのみの導出規則に合わせてACを改ざんしない。
- PR Readinessが全体の旧AC listを持つ場合、AC追加後は合格をそのまま流用しない。歴史的ゲートとして保存し、現在の全AC/subcheck集合について不足する検証を追加する。PRの過去scopeと新しいIssue scopeの明示対応が必要。

ArtifactDeliveryは変更しない。公開Git経由なら事前の別承認・全bytes取得・receipt検査後、新CLIで業務結合を別検証する。新契約の汎用JSON配送は意味検証を省略する許可ではない。非公開ローカル配送もbytesを取得してhashを照合し、元Handoffを再生成しない。dispatch/execution/delivery各3回と旧terminal履歴は変更しない。

## 8. 実装・Test・Reviewへの作業単位

1. Implementation: 上記schema 2件とdoc、strict読取/参照結合/導出/履歴CLIを追加。旧schema/validatorを変更しない。既存Readinessのhistorical validateを利用する際、CLI引数ではなく固定nowで関数を呼ぶ。Handoffの既存validateを先に呼び、新completion pairingを独立実装。
2. Test: 第9節のsynthetic fixtureと変異テスト。手元にないlive権限/配備を捏造しない。独立Testに全artifact bytesと固定headを配送する。
3. Review: 全必要集合の省略、権限混同、時間窓、TOCTOU、squash/queue mapping、2種類Handoff、履歴巻戻し、JSON parser境界を重点確認。
4. Docs/CI: agents/manager.md・research-design.md・contracts/README.md・readiness.md・workflows/single-issue.mdで「後続未実装」を新契約への入口に更新。既存Readiness自身のaggregate禁止は残す。workflowの既存unittest discoverへ新testsを含め、synthetic completion CLI replayを追加。readiness/delivery/retry/knowledge回帰を全維持。
5. Manager: ユーザーの承認範囲内で、実装・独立検証・GitHub必須ゲートが揃った新headだけ次工程へ。今回の設計completedはこの実装/merge許可ではない。

Implementation Ready: 本設計の採用、scope/subcheck設計の確定、実装担当への既存権限、必要入力bytesが揃えば契約実装を開始できる。製品配備環境は契約実装開始の前提にしない。
Deployment Ready: 製品の環境・アクセス・rollback・データ・実測手段・操作承認を別に揃える。schema実装/テスト成功で配備可能とはしない。

ユーザー/Managerによる確定事項: 全必要PR/repoの完全リスト、対象環境と必須実測範囲、期限長、scope変更/縮小の判断、実際の操作承認。技術推奨だけで決められる事項: 独立契約、保守的vector binding、既存schema維持、strict JSON/bytes検査。新たな権限要求は今回行っていない。

## 9. 正常・異常テストの具体表

すべての正常系はsynthetic。`example.invalid`、`example/app`等の架空repo、固定架空SHA、2030年の明示replay時刻を用いる。実IssueのAC合格fixtureは作らない。

| ID | 条件/変異 | 期待 |
|---|---|---|
| P01 | 3架空repo/3PRが各ready、merge済み、正しいdigest/configが同一環境へ配備、全subcheck実測・全AC met、統合pass、Manager final一致 | exit0 / ready / achieved / REPLAY |
| P02 | 同repo複数PR、merge/squash/rebase/queue各方式と明示的binding | 対応が証明された方式だけP01と同じ |
| P03 | 正直なPR未作成/未merge/未配備/未測定 | exit0 / blocked / unverified、final achievedなし |
| P04 | 全premerge AC met、全PR merge済み、integration測定pending | exit0 / blocked / unverified、final省略 |
| P05 | 全AC metだがintegration fail、またはrollback | exit0 / blocked / not_achieved、v2 final省略 |
| P06 | 過去ゲートはmerge時点有効、今は期限切れ。現在AC/integration証跡は新規有効 | 歴史と現在を分離して受理 |
| P07 | 失敗→修正/新構成→再測定、過去failureとrollbackをhistoryに保持 | 新構成の条件が揃うまでachieved不可 |
| N01 | 1PRだけmerge、残り省略/未merge、全premerge metだけでachieved | 集合欠落または不正achievedでexit1 |
| N02 | 必須repo/PR/verification/deploymentの削除・重複、unknown scopeをready | exit1 |
| N03 | head/base/target/config/merge-group変更、旧Review/CI、未対応merge SHA | exit1または新pendingとしてblocked。古いready無効 |
| N04 | PR headをactual merge SHAに無条件同一視、squash対応なし | binding pending、achievedならexit1 |
| N05 | user approvalだけでgithub_reviews/checks/ruleset/queueをpass、AI Review代替 | 既存Readiness検査/Managerゲートで拒否 |
| N06 | scope縮小、新必須PR追加、承認期限切れ/撤回、contextを旧copy | pin/集合/時刻で拒否。context真偽はManagerでも検査 |
| N07 | image tagのみ、別digest/別環境/別workload、multi-source片方省略、Syncedだけ | deployment不足/不一致、achieved不可 |
| N08 | premerge試験をpostdeployとして流用、観測がmerge/deploy前、架空event時刻 | exit1 |
| N09 | AC原文1文字/句読点/出典変更、AC抜け/重複、subcheck1件未測 | 原文/集合不一致exit1、正直な未測はunverified |
| N10 | evidence kind違い、他AC/verification/producer、receiptをmeasurementへ | exit1、独立性の実体はManagerも拒否 |
| N11 | now==expiry、future観測、context失効、過去gateがmerge時点でも失効 | exit1。新pending記録に作り直す |
| N12 | 配備revision/image/configが後から変化、rollbackを黙って削除 | vector/history不一致exit1 |
| N13 | partial read、改行1byte追加、digest/size差、初回read後swap、同内容別path、symlink | exit1、成功出力を消費不可 |
| N14 | JSON重複キー/escaped重複/BOM/NaN、pr_number=true、余剰field | exit1 |
| N15 | handoff role非Manager、誤artifact_id、異Issue/原文/結果、全met統合pendingなのにfinal achieved | exit1 |
| N16 | 最新previous pin違い、履歴切捨て、初回偽装、失敗をunverifiedへ書換え | exit1/Manager最新台帳で停止 |
| N17 | 引数不足、読取不能、異cwd、remote locator、再利用旧成功dir | 2/1/正しいrelativeなら0/1/拒否 |
| N18 | 同じcontextを許可としてreceipt単体/記事から操作しようとする | authority付与なし。CLIは操作APIを持たない |

各異常テストでは「不正achieved拒否」と「正直なblocked記録は許容」を別に確認する。CLIがexit0を返すだけのテストにしない。既存readinessのaggregate禁止テストを削除せず、新集約入口だけでsynthetic achieved可能にする。

