# 現在の契約

通常の学習記録は [単一 Markdown](../templates/handoff.md)。JSON 検証が必要な場合だけ下表を使う。
新規タスクへの必須要件ではない。

| 契約 | 現行版 | schema |
| --- | --- | --- |
| Handoff | 2.0 | handoff.schema.json |
| Knowledge 入力・出力・参照、収集 | 1.0 | knowledge-*.schema.json |
| Artifact Delivery、Authorization、Publication、Consumption | 1.3 | artifact-delivery / delivery-authorization / publication-receipt / consumption-receipt.schema.json |
| Readiness と context | 1.1 | readiness / readiness-context.schema.json |
| Issue Completion と context | 1.1 | issue-completion / issue-completion-context.schema.json |

版は契約ごとに異なり、全JSONを同じ番号へ変更しない。
現行 CLI は Delivery 1.0–1.2、Readiness 1.0、Issue Completion 1.0 を拒否する。
旧 schema 14本を削除し、最新版は版接尾辞のないファイル名に統一した。
入力不備、未承認、参照の欠落・改変、未検証を成功とする記録は引き続き拒否する。

## 過去契約の再現

[変更前の固定履歴](https://github.com/syuhei0519/ai-development-system/tree/e1d2b4dcbe47483e1193206386f8d21810cc3fd7) で旧 CLI / schema / 記録を再現する。
旧版検証の現行サポートは終了。実データを新しい版へ書き換えて成功扱いにしない。
現行テスト用の架空データは明示的に作り直し、過去の実行結果とは区別する。
古い非公開の収集状態を再開する場合も、その状態を作った固定履歴を使う。

```sh
python scripts/validate_handoff.py templates/handoff.md
python scripts/validate_delivery_records.py
python -m unittest discover -s tests -v
```

形式検証は事実・達成・操作許可・レビューの成功を証明しない。
