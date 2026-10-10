# Handoff contract v1.0

`handoff.schema.json` は JSON Schema Draft 2020-12。追加フィールドを拒否し、すべての文字列は空白だけの値を拒否する。`issue` は必須 AC 原文と取得元を保持し、`role` と Issue 固有情報を分離する。`task_id` は独立実行の識別子、`attempt` は同じ論理工程の試行回数（1〜3）。実際の識別子は非公開の実行領域に置く。

- `system_status`: 実行基盤の終了状態。`completed` は業務成功を意味しない。終了通知の状態を Manager が照合する。
- `status`: 役割の業務判定 `completed` / `blocked` / `failed`。completed には成果物・根拠・AC 対応が必要。blocked には修正可能な阻害理由と必要な処置、failed には失敗理由が必要。
- `ac_mapping.disposition=covered`: **その役割に割り当てた責務**について AC を扱ったという主張。Research の設計済みは実装済み・テスト合格ではない。`scope` に確認した範囲と限界を記す。最終 AC 充足は Manager の業務検査で判定する。
- `artifacts`: locator と revision で内容を特定する。ローカルパスだけでは別タスクに届かない。Manager は実体を取得し、後続が読める形でコピー・添付する。変更可能な URL の場合も immutable revision / digest を別途記録する。
- `evidence`: 主張、根拠となる成果物 ID、根拠の場所、観測内容。テストはコマンド、対象 revision、結果、環境上の制約を観測内容に含める。
- `upstream`: 依存する handoff と再試行元を追跡。再試行には直前の同一 role・同一 Issue の task、attempt と `retry_of` を記録し、Manager が前回 +1 を検査する。
- `knowledge_candidates`: Knowledge Agent 用の任意の候補配列。空でも開発を進められる。公開可否の自己申告は公開許可にはならない。
- `publication`: synthetic_sample は架空の例、public_safe は公開前レビュー済み、private_only は公開不可。値だけで機密検査を代替しない。

## 検証の境界

`python scripts/validate_handoff.py FILE...` はスキーマ形式とローカル参照整合性（ID の重複・存在、completed の全 AC 対応、retry の直前試行）を検査する。参照整合性は JSON Schema の追加検査であり、真実性の検証ではない。出典の到達性・内容、AC 原文の完全性、成果物の品質、実際のテスト成功、権限、GitHub 反映、公開安全性は [Manager の業務ゲート](../workflows/single-issue.md) で別途検査する。

AC 原文が一つでも欠落していれば、既知の AC を保持したまま `MISSING_ACCEPTANCE_CRITERIA` で blocked とする。すべて不明なら `acceptance_criteria: []` とする。空の原文や推測した原文で穴埋めしない。部分欠落は形式検査では検出できないため入力との照合が必要。

`$id` の example.invalid は識別用のプレースホルダーであり、ネットワーク取得は不要。契約変更時は schema_version とサンプル・テストを同時に見直す。
