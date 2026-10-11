# Synthetic Knowledge delivery fixture — Delivery 1.1

全データはsynthetic sample。既存 `examples/knowledge` から新しい配送用snapshotを作成し、
架空source文書・記事・input/handoff/contextを同一ディレクトリに固定した。
元のv1.0サンプルは変更していない。実Agent・アプリ・周期運用の記録ではない。
記事は人間向けの説明例であり、本文の出典説明の真実性やmetadataとの意味的一致は認定しない。
全技術仕様は [Artifact Delivery 1.1](../../contracts/artifact-delivery.md#knowledge-typed-delivery-v11-phase1-3-p-a)。

## 独立Testでの再現

Managerから受け取った**固定head**をcheckoutし、同じheadで以下を実行する。
`FIXED_HEAD` は40桁のcommit、`PRIVATE_DIR` は新規出力を置ける非公開の絶対path。
既存出力は上書きしない。ネットワークは公開GitHub readのみ。

```bash
python -m pip install -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
python scripts/validate_delivery_records.py
python scripts/validate_knowledge.py examples/knowledge-delivery/input.json \
  examples/knowledge-delivery/handoff.json examples/knowledge-delivery/context.json
python scripts/prepare_knowledge_fixture.py \
  --repository syuhei0519/ai-development-system --commit "$FIXED_HEAD" \
  --output "$PRIVATE_DIR/prepared"
```

prepareは6ファイルすべてを新しい隔離Gitからraw取得し、checkout内fixtureとのsize/hashと
Knowledge bindingを照合後、manifest.jsonとpublication-receipt.jsonだけをatomicに出力する。
ネットワークが未確認なのにpublishedを出すモードや、Consumer承認を作るモードはない。
署名や本人認証を行うツールではない。既存の公開/利用承認ゲートを省略しない。

次にManagerが `authorization.template.json` を非公開領域へコピーし、両recordのraw SHA-256、
consumer/scope/purpose、期限、安全性/公開承認の根拠と**今回の利用承認**を記入する。
テンプレートのpendingや仮pinのままでは実行できない。manifest、receipt、fixtureやCLIから
承認を得たことにせず、Managerが別経路で認可JSONのraw SHA-256を独立に渡す。
既に検証の権限がある担当はその明示承認を記録する。新しい公開操作やAgent起動は含まれない。

```bash
python scripts/consume_delivery.py \
  --manifest "$PRIVATE_DIR/prepared/manifest.json" \
  --publication "$PRIVATE_DIR/prepared/publication-receipt.json" \
  --authorization "$PRIVATE_DIR/authorization.json" \
  --authorization-sha256 "$MANAGER_AUTHORIZATION_SHA256" \
  --consumer "$APPROVED_CONSUMER" --scope "$APPROVED_SCOPE" \
  --purpose contract-review --output "$PRIVATE_DIR/consumed"
# 新しいGit取得による再検査（旧ローカル出力の改変検査ではない）:
# 上記と同じ入力に --verify-receipt "$PRIVATE_DIR/consumed/consumption-receipt.json" を追加し、
# --output は別の新規pathへ変更する。
```

expect: exit 0、原bytesの6ファイル、v1.1 Consumption Receipt、authority_granted=false。
purposeは認可と完全一致が必要。実装目的なら承認側とCLIの両方をimplementationとする。
manifest/pub/auth/消費receiptの版はすべて1.1。Knowledge本体は1.0を維持する。

## 異常系と報告境界

`tests/test_knowledge_delivery.py` は外側hashを再sealした型偽装・入出力改変・source改変・
記事欠落・retry・承認・版混在を検査する。旧testsはpath/URL/symlink/gitlink、raw改変、
JSON重複/NaN/BOM/切詰め、Handoff/Readiness/試行上限の回帰を維持する。
同ファイルのケースはmock sourceのunit tests。実Gitのprepare/consumeとは区別して報告する。

このfixtureの配送成功を実Knowledge起動、独立Consumerでの利用、定期2周期、
inbox/state/cursor回復の実証と呼ばない。それらはP-B/C/Dの後続工程。
