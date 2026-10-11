# Issue Completion v1.0（複数 PR・repo）

PR の Merge Ready と Issue 全体の Completion は独立した契約。既存 Readiness v1.0 の
`aggregate_required` / `unknown` から achieved への禁止と Handoff v2.0 の意味を維持する。
この入口は Manager が取得した全必要構成・実体・現在観測を検査する offline CLI であり、
GitHub/API 操作、監視、署名、配備、Issue close は行わない。

## 入力と信頼

[assessment schema](issue-completion.schema.json) と [context schema](issue-completion-context.schema.json)
は Draft 2020-12、閉じた object。全必須 PR（同 repo 複数可）、依存 DAG、全 AC 原文、
必須 subcheck、配備先 environment/workload、全 source revision、設定 SHA-256、image digest、
観測・期限を列挙する。必要 PR 集合は非空、各結果集合は context と完全一致。
AC を短縮・分割せず subcheck の AND で評価する。最早検証段階より早い測定は不可。

context は Manager が独立した認可済み取得から確定する。`--context-sha256` はその raw bytes
への独立 pin。assessment 内の自己申告 hash、receipt、記事から pin や権限を得ない。
全必要 repo/PR の完全性、原文の正当性、承認・証跡の真実性は Manager が確認する。
`scope_revision` は同梱 scope source の SHA-256 と一致させる。

`required_scope` は全必要 member/deployment 集合を承認し `assess` のみを表す。
`product_operation` は actor・Issue・scope revision・対象・action・時刻を拘束する。
実 merge/deploy の actor とその時刻に承認があったかを照合する。必要な集合不足・撤回・期限切れは
ready にできない。`delivery` の publish/consume は製品操作の代わりにならない。
承認不要の操作を新設しない。GitHub checks/reviews/ruleset/queue、実 actor の権限は別途必要。
最小 v1 は保守的に scope decision 全件を現在も有効なものに限定する。

## 歴史的 PR ゲートと現在の実測

各 member は Readiness / context / PR Handoff の全 bytes を固定参照する。既存 validator を
**実 merge 時刻**で呼び、`evaluated_at <= gate_checked_at <= merged_at < expiry` を確認する。
現在期限切れの過去 Merge Ready は、その merge 時点で有効なら履歴として受理する。
PR の Issue、担当 AC 原文・集合、head/base/target/config/merge-group と現在の固定記録を照合する。
AC 追加後も過去の担当原文と scope が一致するものだけ履歴に使い、現在全 AC は別に実測する。

`merge_binding` の実体は head/base/検査 target と actual merge SHA・時刻・方式を対応付ける。
squash/rebase/queue でも head==merge SHA を要求しない。GitHub の merge 観測、結果 tree/commit 範囲、
検査対象からの対応を Manager が実証する。対応なし・旧 gate・未 merge は achieved 不可。

現在の証拠は `observed_at <= evaluated_at <= now < valid_until`。
premerge 証拠は元 PR subject を保持し、merge 後の日時へ書き換えない。
postmerge は全必要 merge 後、postdeploy は加えて対象配備後の測定を要求する。
集約証拠を全 merge vector と context digest に束縛し、postdeploy は全配備 vector も照合する。
配列順序は ID index で比較し、重複 ID は拒否する。

配備は期待/実測の全 source revisions、config digest、component image digest、環境、workload が
一致して初めて ready。タグや Synced/Healthy だけでは不可。source→build image→manifest→runtime
の provenance、multi-arch 対応、DB/volume/依存 service 状態は取得証拠で説明し Manager が確認する。
CLI 自身は image や live 環境へアクセスしない。設定 digest の算出範囲は証拠に記し Secret を含めない。

## 実体と証拠形式

BlobRef は `id, locator, sha256, size`。locator は **assessment ディレクトリを bundle root とする**
相対 path。root 外、`..`、remote URL、symlink、特殊ファイル、16 MiB 超は拒否する。
Handoff artifact の locator のみ従来どおり Handoff ディレクトリ基準。
歴史的 PR Handoff の Readiness locator にも集約入口で同じ通常ファイル・祖先検査を適用する。
同じ正当な実体を指す symlink、絶対 path、空要素、`.` / `..`、backslash も受理しない。
通常の入れ子ディレクトリ内の相対 locator は使用できる。既存 Readiness CLI 自体は変更しない。
同じ ref ID を異なる path/bytes に使わない。読み取った全ファイルを成功前に再読照合する。
ローカルの悪意ある writer が検査終了後に変更することまでは防がないので、配送時の pin を保全する。

証拠の source_ref は次の **JSON 実体**。observation は evidence の `source_ref` 以外の全フィールドと
型も含め一致する。任意の文章や receipt を measurement として使えない。これは自己署名や真実の証明ではなく、
取得元の記録と assessment の矛盾を防ぐ形式。Manager は認可された観測元との真正性も検査する。

```json
{"schema_version":"1.0","document_type":"issue_completion_observation","observation":{"...":"evidence excluding source_ref"}}
```

`ac_measurement` は verification_id、AC、phase、対象、環境/workload、method、expected_result、
producer=verification.owner、result が一致する必要がある。CI/Knowledge/receipt はこの実測の代わりにならない。
JSON は UTF-8、重複キー（escape 含む）・NaN/Infinity・BOM・余剰末尾・未知フィールドを拒否する。
sha256 は常に raw bytes。比較用 JSON 正規化を配送 hash の計算に使わない。

## 導出と履歴

全必須 subcheck の一つでも not_met なら AC=not_met、未測定が残れば unverified、全て met のみ met。
全 AC met、全 merge/配備/承認、統合チェック全 pass の後だけ ready / achieved。
既知の AC/integration failure、revert、rollback、配備 failed は blocked / not_achieved。
正直な不足は blocked / unverified。証拠不整合や active expiry は exit 1 であり、有効な保留記録ではない。

head/base/target/config/queue、scope/必須 PR/repo/AC/subcheck、deployment revision/env/workload/image、
承認、期限、rollback/revert が変わったら新 context で再評価する。自動監視は実装しない。
失効証拠は active 集合から外し、旧 assessment を raw のまま履歴へ保持する。
2 回目以降は `history.previous_ref`、context の `previous_assessment_sha256`、Manager 最新台帳の
`--previous-sha256` と実ファイルが一致する必要がある。古い枝への復帰や初回偽装は Manager の最新 pin 管理でも防ぐ。
全履歴 events は prefix を変更せず追加する。scope/集合/head/配備変更には対応 event を残す。
必須 subcheck の追加・削除・ID変更・AC対応変更は、前回 assessment の
verification_results / ac_results と比較し、新規 `required_set_changed` event を要求する。
前回の ac_measurement に記録された phase・対象member/deployment・環境/workload・method・
expected_result・producer(owner) と現 required_verifications の差も同様に扱う。
配列の並べ替え、測定結果・時刻・証拠IDの更新だけは必須集合変更にしない。
v1 assessment は未測定の定義全文や failure_action を保持していないため、そこから過去の値を
復元したとは扱わない。Manager はこれらの変更も scope 原本と scope_revision に反映し、
対応 event を残す。全定義の機械的な過去比較には別途 pin された旧 context が必要である。
失敗/rollback/revert は証拠付き event が必要。

v1 は保守的に前回 not_achieved を保持し、単なる期限切れや pending 化で unverified へ消さない。
解除には全 ready 条件、新しい現在 AC/integration 実測、証拠付き revalidated event が必要。
異構成へ移ってもその条件が揃うまで not_achieved を保持する。これは失敗の消失を避ける最小実装の判断。
旧成功・失敗は履歴に残り、過去証拠を現在の証拠に混ぜない。dispatch/execution/delivery 各最大 3 と
旧 terminal 履歴の扱いは Artifact Delivery のまま。

## CLI と二種類の Handoff

```sh
python scripts/validate_issue_completion.py bundle/completion.json \
  --context bundle/context.json --context-sha256 "$MANAGER_CONTEXT_PIN" \
  --handoff bundle/handoff.json
# 2 回目以降には両方追加:
# --previous bundle/previous.json --previous-sha256 "$MANAGER_LATEST_PIN"
# synthetic/historical replay のみ: --at 2030-01-03T12:00:00Z
```

exit 0 は記録整合のみ（blocked/not_achieved も含む）。1 は不正/欠落/失効、2 は引数不備。
REPLAY は現在の完了や操作許可を意味しない。CLI は権限を付与しない。

PR Readiness pair と最終 Issue Completion pair を分離する。必須 `--handoff` は Manager の Handoff v2。
completion の artifact_id / kind=other / 同一 local path / 初回 raw bytes / SHA-256 を確認する。
最終 AC evidence は completion と Handoff が同一 source 実体へ結合しているかも確認する。
achieved には completed Manager Handoff の final_assessment が必須。
全 AC met + integration pending/fail は既存 v2 の AC だけからの導出と両立しないため final を省略する。
AC を unverified に改ざんしない。各 PR の Readiness に Issue 最終 Handoff を混ぜない。

公開配送には別途 Artifact Delivery を実施する。一般 JSON として配送できても本 CLI の意味検証は省略不可。
検査合格だけで実操作せず、Manager の最終原文・実体・独立 Test/Review・GitHub 必須ゲートを通す。

## 採用判断と検証

独立 schema/context/CLI の追加に限定し、既存 v1/v2 の schema・validator を変更しない。
設計案から具体化した追加項目は current member の target/config/merge-group と実 actor、verification/evidence の
workload/method/expected_result、明示的 merge mapping、構造化 source observation。いずれも比較対象の欠落を避けるため。
新サービス、課金 API、Secret/Ruleset 変更は不要。

[synthetic samples](../examples/issue-completion/README.md)、`tests/test_issue_completion*.py` は
3 repo、同 repo 複数 PR、squash/rebase/queue、過去期限切れ gate、現在実測、欠落/重複、scope/pin/expiry、
source fake、path/bytes、履歴、失敗と Handoff 境界を検証する。全既存回帰も維持する。
実製品の Order3 AC は未実測のため unverified。schema 実装・synthetic 成功を製品 Issue 達成や配備許可にしない。
