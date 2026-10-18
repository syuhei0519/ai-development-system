# Issue Completion 1.1

現行は issue-completion.schema.json / issue-completion-context.schema.json。
必要な変更・配備・確認の集合を固定し、標準変更と準備変更を区別する。
統合前、測定不足、失敗、期限切れ、古い結果の再選択を達成として扱わない。
過去のReadiness参照と現在の固定contextを照合し、必要な全件の統合と測定を要求する。

再現例は examples/issue-completion の架空データ。実際の配備結果や操作許可を意味しない。
CLI は `--context` と独立の `--context-sha256`、必要なら `--handoff` を受け取る。

[旧版と当時の結果](https://github.com/syuhei0519/ai-development-system/blob/e1d2b4dcbe47483e1193206386f8d21810cc3fd7/contracts/issue-completion.md) は履歴から参照する。旧版検証の現行サポートは終了した。
