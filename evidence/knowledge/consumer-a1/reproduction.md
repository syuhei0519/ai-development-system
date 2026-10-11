# 取得と判断を再確認する手順

この手順は今回行った資料検証の記録であり、追加実行権限を付与しない。過去reproducer、アプリ、出典に書かれたテストは実行しない。認可とreceiptは非公開でManagerが保管し、Public候補に含めない。

1. 新規領域で正本repoのcommit `8afe6044857783dbf6d6ae7ac9459ae5e890a744` を取得する。contracts、scripts、agents/review.md、workflow、templatesを読み、正本bytesと同一のConsumer CLIを使う。既存workspaceへの依存は不要。
2. 固定records commit `e2f62afd30bd4334875902cc695fa8cbf753e16d` の `evidence/knowledge/milestone-a1/manifest.json`（7726 bytes、SHA256 `2be52b2ef14bd56882ea0d7f1a19c1a8411326c3e8103796f6003f7220cc6e34`）と `publication-receipt.json`（8549 bytes、SHA256 `fa2f4691d2d249493a85b2a684d0cc77f4d74ea1a5bfcbdaa7660e7628a56707`）を通常blobとして全bytes取得する。commit型/FETCH_HEAD/tree祖先/leaf型も確認する。
3. Managerの別経路から、現在有効なconsumer/scope/purposeを指定した認可と独立pinを受け取る。元pinやreceiptを新しいConsumerに転用しない。認可を編集して通すことはできない。
4. 次の未変更CLIを認可された非公開領域で実行する（パス/値は実際のManager入力に置換）。

```bash
python CANONICAL/scripts/consume_delivery.py \
  --manifest PRIVATE/manifest.json \
  --publication PRIVATE/publication-receipt.json \
  --authorization PRIVATE/authorization.json \
  --authorization-sha256 MANAGER_INDEPENDENT_PIN \
  --consumer APPROVED_CONSUMER --scope EXACT_SCOPE \
  --purpose contract-review --output PRIVATE/NEW_OUTPUT_1
```

期待はexit0と検証済み13件63991 bytes。contextはknowledge-context-v1、Deliveryは1.1、本体Knowledgeは1.0、knowledge_bindings=[]。全記事と6 source実体が閉包に含まれる。再検査は同じ引数に `--verify-receipt PRIVATE/NEW_OUTPUT_1/consumption-receipt.json` を足し、出力を未存在のNEW_OUTPUT_2に変える。**検査成功後はNEW_OUTPUT_2のみを利用する**。

5. 初回とfreshの13件をそれぞれ全bytes読取り、manifestのsize/hashと照合し、初回==freshを別途確認する。CLIのreceipt再検査自体が旧出力を検査したと扱わない。今回この追加比較も全件一致した。
6. manifestの6 source_aliasに記載された固定Git `72b729aabce1c6dd0877102e9af0194ea6055cba` を新規取得し、raw/evidence6件と全bytes比較する。全元path/size/SHA256はdelivery-verification.jsonのsource_origin_comparisonsに収録。通常blob祖先と型を検査してから読む。私的なオリジナルへの追加アクセスはしない。
7. semantic-review.mdの各主張を新出力側のcontext、両記事、raw記事、6出典本文に照合する。記事の見出しと固定行番号、JSON pointer、S3の静的構造で追跡する。過去報告は報告として保持する。
8. usage-map.jsonのT01–T12がdelivery-review-test-plan.mdの項目と一致し、N01–N05の採否理由、固定記事id/revision、draft/更新条件がcontextと一致することを確認する。全提案テストはnot_executedである。
9. 正本 `scripts/validate_handoff.py handoff.json` と `scripts/validate_knowledge.py input/context.candidate.json` で形式・参照整合性を確認する。handoffの全artifact実体のsize/hashを配送inventoryと照合する。schema合格だけをKC業務判定にしない。

## 最小配送閉包

根はhandoff.json。そこから7件の新規報告（assignment、配送観測、意味レビュー、計画、利用対応表、利用報告、この手順）とinput全13件を参照する。入力は今回のmanifest全体を再取得・確認できるよう13件をそのまま保持する。contextの必須意味依存は2記事+6出典、さらにraw記事と索引3件を含め、原13件を削らない。

候補inventoryは循環digestを避けるためbundle外のsidecar。全候補のpath/size/SHA256/formatと、handoffからの最小配送集合を列挙する。inventory自身を自己参照しない。Managerは候補の公開安全性/公開操作承認と新Consumer利用承認を別に確定するまで公開しない。非公開認可/pin/receipt/生ログ/原本Handoffは閉包外。
