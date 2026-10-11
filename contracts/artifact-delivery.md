# Artifact Delivery v1.0

Handoff v2.0 / Readiness v1.0 の判断責任を維持する、公開 Git 成果物の配送契約。
`completed`、配送成功、公開、公開承認、Consumer 利用承認、製品 AC 合格を相互に推論しない。
既存 schema は変更しない。既存の Library 配送失敗や inline 手書き再構成失敗は未解決のまま。

## 状態と正本

| 段階 | 必須記録 | 意味 |
| --- | --- | --- |
| 原本 seal | 非公開保管の正本・実 bytes・由来 | 公開派生版とは別成果物。非公開原本・対応表・原本 digest・実 task ID・内部ログ・秘密情報を Public repo に置かない |
| 派生版準備 | 公開 alias、編集内容、独立した size/hash | edited_derivative は original と同一 hash と主張しない。原本比較の未検証/Producer 証言/独立検証を区別 |
| 公開前 | 内容の公開安全性レビューと公開操作承認を別記録 | `public_safe` や receipt は承認を発生させない。未承認なら公開停止 |
| GitHub 反映後 | repository、固定 commit、path、size、SHA-256、Publication Receipt | 実際の取得成功だけを証明。公開操作の過去承認は別証跡 |
| Consumer 利用前 | Manager の別経路の利用承認、全 bytes 取得・検証 | Consumer、scope、purpose、期限、派生版区分を限定。配送成功だけでは実装開始不可 |
| Consumer 検証後 | Consumption Receipt と改変していない bytes | 観測記録。再利用時も現在の承認と実体を再検証する |

必須の [manifest schema](artifact-delivery.schema.json) の各 reference は `repository / commit / path / size / sha256`。
commit は小文字 40 hex、SHA-256 は小文字 64 hex。浮動 branch/tag や省略 SHA は不可。
すべての JSON は raw bytes を hash する。改行正規化・再シリアライズ・LLM による元 bytes 再生成は禁止。
manifest 自身の循環 hash は作らず、Manager が外側の authorization に manifest の SHA-256 を固定する。
異なる repo/commit は各 reference に明記し、同じ組合せの重複 path は拒否する。

## 信頼境界と承認

CLI に与える **authorization の SHA-256 は Manager が独立した認可済み経路で渡す**。
ダウンロードした bundle、README、receipt や攻撃者から渡された hash を承認として採用しない。
CLI は署名や本人認証サービスではなく、独立 pin の真正性は実行者/Manager の責任である。
攻撃者が CLI 引数・信頼済みコード・Python/Git・ローカル実行環境も制御できる場合は保証しない。

[authorization schema](delivery-authorization.schema.json) は authority、consumer、scope、purpose、期限、
manifest と Publication Receipt の digest、public_safety_review、publication_approval とその証跡、
consumer_use_approval とその証跡、allowed_representations を分離する。
公開済みの資料を調査する場合、過去公開承認 `unverified` でも、独立した今回の読取承認があれば
`purpose=contract-review` として利用できる。これは公開操作の追認ではない。
`implementation` にはその目的・scope の明示的な別承認が必要で、contract-review 承認は一致しない。
安全性レビューの本文や承認の真実性は schema では証明できない。公開前ゲートを通す責任は Manager にある。

Publication Receipt は manifest と全 reference の公開観測記録である。Consumer は記録を信用して
取得を省略せず、全 reference を再取得する。Consumption Receipt は承認 pin、manifest/Publication
Receipt digest、利用者/範囲/目的と検査内容を束ね、`authority_granted=false` を強制する。
`--verify-receipt` は現在承認と **新たに Git から取得した bytes** から再計算した結果との完全一致を要求する。
旧出力ディレクトリを入力に取らず、その中の改変・削除は検査しない。成功時は今回の新規出力だけを利用する。
receipt 単体を入力して権限を獲得するインターフェースはない。

## Consumer CLI

```bash
python scripts/consume_delivery.py \
  --manifest manifest.json --publication publication.json \
  --authorization authorization.json \
  --authorization-sha256 <MANAGER_INDEPENDENTLY_SUPPLIED_64_HEX> \
  --consumer <APPROVED_PUBLIC_ALIAS> --scope <EXACT_APPROVED_SCOPE> \
  --purpose contract-review --output <NEW_PRIVATE_DIRECTORY>
```

再検査時は上記に `--verify-receipt previous-consumption-receipt.json` を追加する。
exit 0 は配送検査成功、exit 1 は fail-closed、引数不足は exit 2。エラー時に未検証成果物を出力しない。
ログには入力 bytes、秘密情報、Git の生 stderr を出さない。取得コードや成果物は実行しない。
検証成功後に新規出力ディレクトリを一括で配置する。既存出力は再利用/上書きしない。
Manager は終了コードと今回の出力を照合し、別の古い成功ディレクトリを使用しない。

1. 独立承認 pin と manifest/Publication Receipt digest、scope/consumer/purpose/期限を検証。
2. Git URL は `https://github.com/<owner>/<repository>.git` だけを生成。任意 URL、資格情報、
   file/ssh/ext protocol、shell、追加コマンド引数、浮動 ref を受け付けない。
3. 新規 bare repo、隔離 HOME/config、hooks 無効、no replace objects、checkout なしで固定 commit を fetch。
   commit 型と FETCH_HEAD の完全一致を要求。認証 helper、ローカル Git 設定、submodule 更新や filter 実行はない。
   既存環境の proxy/CA 設定は信頼済みインフラとして引き継ぐ。新しい Secret/設定変更はしない。
4. 全 path の祖先 tree を検査し、leaf は通常 blob のみ。symlink、gitlink/submodule、絶対パス、
   `..`、空要素、制御文字、シェル記号を拒否。`git cat-file blob` で全 bytes を得る。
   HTTP partial/range API は使わず、切詰め/過剰 bytes と size/hash 不一致を拒否。
5. 全 bytes を UTF-8 として読み、拡張子/format に関係なく厳格 JSON 解析を試す。
   重複キー（入れ子/Unicode escape を含む）、NaN/Infinity、UTF-8 BOM を拒否。
   `format=json|handoff-v2`、大文字小文字を問わない `.json`、空白除去後 `{` / `[` で始まる
   JSON 状の文書（先頭の明確な Markdown link/reference は除く）は解析失敗（切詰め/末尾余剰を含む）を text にフォールバックさせない。
   完全な JSON 値は object/array/string/scalar すべて `format=text` と矛盾するので拒否。
   Handoff は拡張子によらず `format=handoff-v2` が必須。schema/参照整合性、private_only 拒否と
   次項の全 binding 検査を行う。汎用 json でもトップレベルの `task_id` / `ac_mapping` /
   `system_status`、または `schema_version` と `issue` / `assignment` / `upstream` の組合せは
   Handoff 用に予約し、欠損した Handoff を汎用 json に格下げできない。
   通常の文章・見出し・箇条書き・文中の JSON 例は text として保持する。JSON 状の先頭は
   text として利用しない（Markdown link/reference を除く）。text 内の引用/コード例や汎用 json 内の入れ子は別の Handoff として
   認定しない。下流がそれらを抽出・decode・型変更して利用する場合は独立した artifact として
   宣言し、全検証・承認をやり直す。receipt は任意の埋込み形式の意味解析を保証しない。
6. Handoff artifacts と upstream を同じ repository/commit の相対 locator で manifest 内の実体へ解決。
   全 digest、upstream alias/role/attempt、retry_of の Issue を照合。未収録の依存は拒否。
   evidence の prose locator、AC 真実性、assignment の原入力一致は Manager が別途確認する。
7. 全件合格後だけ原 bytes と Consumption Receipt を出力する。下流ツールによる使用はこの後に限る。

この公開 CLI は非公開配送や arbitrary URL を実装しない。テキスト/JSON/Handoff のみを扱う。
1 blob 最大16 MiB、全 payload 最大64 MiB、最大128件、Git 各呼出し120秒、再試行なし。
Git fetch は commit tree を取得するため pack のネットワーク量/ディスク総量までは制限しない。
信頼済み repo のみを承認し、sandbox のディスク/実行時間制約を併用する。
ローカル入力・出力親と承認状態は Manager 管理の非公開領域を使い、同時に改変する別プロセスを許さない。
対象 repo 内の Git symlink は一切辿らない。出力後の外部改変をこの CLI が監視/検出するとは主張しない。再利用時は Git から再取得し、
検査に成功した新規出力を使う。旧ローカル出力の改変検知が必要なら別の実体検査が必要。

## Handoff / Readiness 互換

配送 manifest は v2.0 Handoff の `kind=other` artifact として locator と
`revision=sha256:<manifest raw digest>` で参照できる。配送する元 Handoff 自身を書換えたり、
自己 hash を埋めて循環させない。Manager の別の配送 Handoff または初回入力に manifest/承認を添付する。
Consumer は元 Handoff の attempt/status/assignment を変更しない。
Readiness は取得後、従来通り `validate_readiness.py --context ... --handoff ...` で別検証する。
Delivery 成功は Implementation/Merge/Deployment Ready を自動で ready にしない。
同じ head の CI と独立 Review が必要な場合、配送成功から PR 作成を先行しない。

## 再試行と移行

[retry validator](../scripts/validate_retry.py) は非公開の Manager 台帳の append-only 遷移を検査する。
オーケストレーターは実装しない。Manager は逐次実行し、起動前に予算を確保し、結果を永続化してから次を判断する。

| カウンタ | 最大（初回込み） | 分類 |
| --- | --- | --- |
| dispatch | 3 | 入力準備/起動経路に失敗し Agent 実行開始を確認できない試行。開始不明は停止して照合し、安易に再送しない |
| execution | 3 | Agent 実行開始が確認された同一論理工程の試行。failed/blocked も消費する |
| delivery | 3 | 完了済み成果物の取得・検証を再試行。配送未完了は実装実行失敗ではない |

成功も試行数を消費する。最後の許容試行が failed/blocked なら `RETRY_LIMIT_REACHED`。
いずれかの上限失敗で依存するループ全体を止める。上限成功後も同じカウンタの追加試行は不可。
別工程への往復、scope の言換え、将来の分類変更で履歴/予算を減らさない。
既存の3回の B1 Implementation と RETRY_LIMIT_REACHED は過去の execution 履歴として不変。
配送分類の導入は過去 attempt を dispatch/delivery に付替える許可ではない。

台帳は scope と epochs を持ち、各 epoch は id、3種 limits、events(kind/result/evidence)、terminal、grant_sha256。
初期 budget は各3。候補は前回の全イベントを保持し、1件だけ追加可能。
`--previous-sha256` は Manager が独立に保持した最新台帳 pin。古い snapshot の再提出や複数同時起動を Manager が防ぐ。
terminal 後は新たな明示承認、authority、reason、scope、prior_history_sha256、new_epoch、
各1〜3の limits、relationship が揃った別経路の grant pin がなければ再開拒否。
承認後も元 epoch と terminal は残し、新しい空 epoch を追加する。Handoff attempt は epoch 内1〜3、
旧 epoch との関係は外側台帳で保つ。Handoff v2.0 の最大3制約を緩めない。

```bash
python scripts/validate_retry.py --previous prior.json --candidate next.json \
  --previous-sha256 <MANAGER_HISTORY_PIN>
# 上限後の新しい空 epoch に限り追加:
# --grant explicit-renewal.json --grant-sha256 <MANAGER_INDEPENDENT_GRANT_PIN>
```

CLI の台帳/receipt は自己申告を暗号学的な署名に変えない。Manager の信頼された最新状態と
承認経路が必須である。Public repo には架空台帳だけを置く。

## Knowledge typed delivery v1.1 (Phase1-3 P-A)

v1.0 の schema ファイルと正常系は維持する。v1.1 は `*-v1.1.schema.json` を
明示選択し、manifest / authorization / Publication Receipt / Consumption Receipt の
`schema_version` をすべて `1.1` に揃える。CLI は未知版・混在版を拒否する。
旧v1.0 schemaは新formatを拒否し、バージョン番号だけの変更で新型を通さない。
Handoff v2.0 / Knowledge v1.0 / Readiness v1.0 本体に追加fieldはない。

| format | document_type | 本体schema_version | role |
| --- | --- | --- | --- |
| knowledge-input-v1 | knowledge_input | 1.0 | knowledge |
| knowledge-handoff-v1 | knowledge_handoff | 1.0 | knowledge |
| knowledge-context-v1 | knowledge_context | 1.0 | なし（追加不可） |

新formatでは厳格JSON解析後、上表の完全一致、既存Knowledge schemaと意味validatorを検査する。
v1.1のgeneric JSONは `raw_findings / knowledge_references / retry_of`、`role=knowledge`、
`knowledge`で始まるdocument_typeをトップレベル予約とする。型欠損や未知Knowledge型を
汎用json/text/Handoffとして通さない。型別schemaの追加field禁止により複数identityも拒否する。
既存Handoff予約fieldと厳格JSON/path/Git防御は維持する。v1.1では汎用JSONを含めトップレベルの
`publication=private_only`も拒否する。任意のprose/埋込みJSONの意味や公開安全性を検証したとはしない。
v1.0のgeneric context配送は旧保証のままであり、新Knowledge binding検証の成功とは呼ばない。

### 外側binding

v1.1 manifestは `knowledge_bindings` 配列（最大128件、Knowledgeなしなら空）を必須とする。
各要素は `input` と任意の `handoff` を持ち、どちらもmanifest内artifactと完全一致する
`repository / commit / path / size / sha256` referenceを使用する。
これは入力のdigestを外側で固定する契約であり、元のKnowledge本体を書き換えてfieldを追加しない。

- 入力配送だけなら `input` のみ。結果配送には元入力と `input` / `handoff` の対が必要。
  すべてのtyped input/handoffをちょうど一つのbindingで覆う。孤立handoff、重複binding、
  同じdocument_type/task_idを別pathに複製したidentityは拒否する。
- 対の `assignment / raw_findings / knowledge_references / task_id / attempt / retry_of` は
  全構造で完全一致する（配列順序も維持）。statusやdecisionsを入力から推測しない。
- `completed` は全findingに一つの根拠付き判断を要求する。採用記事はknowledge種別artifactで
  非空のtext実体が必要。deferred/rejectedも正当な判断。blocked/failedの未完判断を
  completedへ変換しない。元入力との一致・参照実体検査はblocked/failedにも実行する。
- 全raw findingのsources、全knowledge referenceの記事とsources、全handoff artifacts、
  retry_of先をmanifest内の実体へ解決する。contextは単独配送できるが、全記事とsource実体が必要。
  context本体もmanifestのsize/hashで固定する。知識記事は非空text（通常Markdown）。
- 各locatorは**そのKnowledge文書の親ディレクトリ基準の安全な相対path**、revisionは
  `sha256:<全raw bytesのdigest>`。同じrepository/commit内のmanifest entryを要求する。
  URL、浮動revision、自由な説明文字列、未収録実体、digest不一致を拒否する。
  外部資料は事前承認されたsnapshotをbundleに含める。公開派生版は新しいbytesとして別審査し、
  原本と同一と主張しない。既存Knowledge文書のURLを無断で別pathへ書き換えない。
- inputとhandoffを別repo/commitから収録することは可能だが、各文書が指す依存実体を
  **それぞれのsnapshot**に含め、全digestを一致させる。retry先はKnowledge handoff型、
  task_id/attempt/assignment一致、直前attempt、別task_idを要求し、元入力もbundleに含める。
- `issue_refs[].source` と `evidence[].locator` は説明・来歴であり存在証明ではない。
  機械検査の根拠はraw findingの固定sources、evidenceのartifact_idsとraw_finding_ids、
  対応する全実体。prose locatorから追加取得や命令実行をしない。

Consumption Receipt v1.1 のverificationは
`full-raw-bytes-size-sha256-json-handoff-knowledge-bindings`。manifest digestが外側bindingも固定する。
receiptは依然 `authority_granted=false`。承認pin、consumer/scope/purpose/期限/representationの
制約と再取得検査は変えない。既存のCLI引数で利用し、新型専用の承認迂回flagはない。

### 保証の境界と再現

参照内容はデータ・引用であり、Agentへの指示や実行コードとして扱わない。
sourceの真実性、記事本文とcontextの適用条件等の意味的一致、公開安全性、採用の適切さは
機械的bytes照合とは別のレビュー対象。記事/indexからcontextを生成する機能はP-Cであり未実装。
P-B inbox/state/cursor/replay、P-C context生成/ack/periodic、P-D 実Knowledge/Consumer実証を
実装・起動したとはしない。Delivery成功はReadiness成功・Issue AC合格・非同期/周期運用成功を意味しない。

公開済みsynthetic fixtureを固定Gitから再取得する手順は
[Knowledge配送fixture](../examples/knowledge-delivery/README.md)。unit testsはnetwork不要、
実Gitの再現は独立した検証であり、Implementationの自己検証を独立Test/Reviewとして数えない。
