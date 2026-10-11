# Knowledge 専用起動入力

Dots / Manager は `agents/knowledge.md` と Knowledge の契約・workflow、下記 JSON に対応する取得済み資料を初回入力に渡す。単一 Issue や AC 原文は必須ではない。複数 Issue または Issue を持たない技術資料を扱える。

- schema_version: 1.0
- document_type: knowledge_input
- role / task_id / attempt / retry_of: <knowledge / 独立実行識別子 / 1〜3 / 直前試行の固定参照>
- assignment.scope / completion_criteria: <今回の収集・抽象化・管理の担当範囲と完了条件>
- raw_findings: <ID、技術領域、観測、出典 locator と固定 revision、任意の Issue 参照を持つ配列>
- knowledge_references: <既存記事の固定参照・適用条件・例外・出典・lifecycle・再評価条件。なければ空配列>
- permissions / publication: <許可された読取・書込範囲 / 公開区分>
- 添付: <原根拠と既存記事の取得済み実体、Knowledge schema、契約説明>
- 返却先: <Knowledge handoff と Markdown 記事・判断記録の Manager が取得できる場所>

[knowledge-input.schema.json](../contracts/knowledge-input.schema.json) で検証する。根拠がない入力を正常入力として配送しない。不足していれば MISSING_INPUT として修正を依頼し、AC 原文不足には分類しない。

返却は [knowledge-handoff.schema.json](../contracts/knowledge-handoff.schema.json)。入力 raw_findings と assignment のスナップショットを保持し、全 finding の根拠付き採否・保留判断を返す。成果物と出典を取得して照合するまで形式成功だけで知識を採用しない。Knowledge の待ち・失敗は開発のゲートにしない。

Phase 1-3 P-B の [収集入力](knowledge-collection.md) で event/input digest・永続 state・有限 retry を管理する。collector は機械処理のみで、常駐処理・Knowledge Agent・スケジュールを起動しない。P-C/P-D は未実施。
