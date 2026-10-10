# 独立専門エージェント起動入力

Dots / Manager が専門役割の独立 Codex Cloud タスクに渡す入力テンプレート。Manager 自身の Cloud 起動には使わない。山括弧の項目を埋め、未記入のまま起動しない。必須 AC 原文が取得できなければ不足を明示し blocked を要求する。実識別子や非公開資料は認可された非公開実行領域だけで扱う。

## Role / Contract

- role: <research-design | implementation | test | review | knowledge>
- role_definition: <該当 agents/*.md の全文または取得済み添付>
- contract: <handoff.schema.json と contracts/README.md の取得済み添付>
- workflow: <single-issue.md の取得済み添付>

## Issue-specific Context

- Issue ID / title / authorized source: <識別子・題名・認可済み出典>
- 必須 AC 原文（省略・要約しない）: <AC ID ごとの原文と出典>
- AC の完全性確認: <全件取得済み / 欠落項目と MISSING_ACCEPTANCE_CRITERIA>
- task_id / attempt / logical scope: <独立 task・1〜3・再試行を通じ固定する責務>
- repo / base / target revision: <明示的な対象>
- Mission / deliverables / role-specific completion criteria: <今回の担当範囲>
- 許可操作・作業領域・禁止事項: <read/write/feature Push/Draft PR を個別指定>
- 環境・依存物・検証手順: <既存認可済みの環境>

## Explicit Handoff Bundle

- upstream: <role/task_id/attempt/relationship/handoff locator/revision>
- 取得済み handoff JSON: <本文または添付>
- 成果物の実体: <本文/添付/到達可能な固定参照と revision/digest>
- 根拠: <出典・確認結果・対象 revision>
- 採用判断、失敗、不採用案、制約、未確認点: <列挙>
- 再試行なら: <前回の阻害・修正内容・retry_of・前回 attempt +1>

前タスクの会話やローカルファイルの自動共有を仮定しない。必要な実体が未着なら blocked を返す。

## Return Contract

- 取得先: <Manager が handoff.json と成果物を取得する場所>
- handoff: schema_version=1.0、issue、role、task_id、attempt、upstream、system_status、status、summary、artifacts、evidence、ac_mapping、block_reasons、failure_reasons、knowledge_candidates、publication
- 基盤終了と業務判定を区別する。原文欠落は外部取得・推測で埋めない。
- 最大3試行。自己再起動せず Manager に修正内容を返す。
- Knowledge 候補は任意。公開前の安全性確認を別途行う。
