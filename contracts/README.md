# 成果物の契約

新規の学習タスクは [単一 Markdown Handoff](../templates/handoff.md) が標準。
「目的・やったこと・観察結果・学び」に担当範囲、対象 commit、再現手順、結論、未確認点を含める。
CI artifact と PR 本文に実行結果をまとめ、Git には再現手順と結論の Markdown を残す。
通常の image digest、依存固定、真正性確認、security check の失敗拒否は維持する。

`python scripts/validate_handoff.py FILE.md` は4項目の存在を確認する。
JSON 入力には従来の [Handoff v2.0 schema](handoff.schema.json) と参照整合性検査を適用する。
形式の成功は事実、AC 達成、操作許可、独立レビューの成功を意味しない。

## 過去契約の再現

Readiness、Issue Completion、Artifact Delivery 1.0–1.3、Knowledge、routing の既存 schema / CLI と
実際の回帰 fixture は、指定済みの旧契約と過去の失敗を正確に検証するために保持する。
新規タスクへの必須要件ではない。互換検証用 schema の存在から wrapper / receipt の作成義務は生じない。
明示的な旧契約の再試行上限・停止履歴は保持し、この変更で再開・成功に書き換えない。
新しい証跡基盤や schema 版は追加しない。
