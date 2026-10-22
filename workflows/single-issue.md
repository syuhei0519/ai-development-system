# Jira 開発タスクのワークフロー

## 仕事の正本と開始条件

仕事の選定・計画・進捗・完了は個人 Jira の `PLAT`、コード・PR・Review・CI・再現可能な知識は GitHub を正本とする。
GitHub Issues / Projects から新しい仕事を選定・更新・自動 Close しない。旧 Issue は読み取り専用の出典とする。
Jira identityとsource区分を [実行Handoff](../templates/jira-execution-handoff.md) に記す。
元GitHub Issue URLはmigratedだけで照合し、jira-nativeは明示的にnoneとする。
repo / branch / commit / PR の識別子は引き続き GitHub のものを使う。

Manager は [Jira 移行手順](../docs/jira-migration.md) に従い、既存課題・実 status・出典・停止条件を読み直す。
`migrated` は `config/jira-tracker.json` と `scripts/jira_tracker.py` の移行照合を保持する。
`jira-native` は対応表を経由せず現Jira identityを検証する。両者の実行開始は後述の
`scripts/jira_execution.py` で照合する。不明・欠落・重複・矛盾は blocked として解消し、
GitHub へのフォールバックや Jira の代替課題作成で埋めない。登録済み課題を再作成しない。
移行・候補選定・スプリントへの計画だけでは実装開始や停止タスクの再開を許可しない。

## ステータスの責任

Manager がユーザーの許可範囲で Jira の仕事を選び、計画・担当工程・進捗と完了根拠を管理する。
各担当は観測と未確認点を Handoff で返す。担当の `completed`、CI 成功、PR 作成だけで Jira を完了にしない。
実ワークフローは「未着手・進行中・完了」。Review / blocked / paused は独立した工程・保留理由として
Handoff と Jira の進捗記録へ明示する。存在しない status やラベルを仮定して自動遷移しない。
独立 Review、現 head の required CI、必要な PR の main 統合、全 AC の最終検証を Manager が確認してから完了を判断する。
未マージ PR は未統合、未検証 AC は未確認のまま。移行済みの「完了」も今回再検証した証拠とは扱わない。
この切替では Jira の status / board / sprint を変更しない。

開発は Sprint Goal と対象を合意した Scrum、探索・Spike は WIP を抑えた Kanban として運用する方針。
現ボードは PLAT 全体の Scrum で、探索専用 Kanban は未確認。本文の「表示先案」や `type:experiment` だけで
表示先を確定せず、別ボード／フィルターの整備は別途判断する。Release は sprint 完了と別の承認・CI・配備証跡で扱う。
学習 Topic / Session は開発完了と独立し、未開始・中断・未修了を開発のゲートにしない。

## 起動と責任分担

依頼で指定された repo、固定 revision、目的、必要な AC、禁止事項を渡す。
Research/Design → Implementation → Test → Review のうち必要な工程を使い、
Manager が独立 Review と現在の CI を確認してマージを判断する。
実装者の自己検証を独立 Test / Review と扱わない。

## 実行場所と必要能力

実装、Unit/build/static、対応 runtime の DB/API 検証、Helm rendering は Codex Cloud。
実 cluster が必要な検証は許可された既存 kind で行う。利用不能ならその検証だけ未確認とする。
追加 API・課金・Secrets/Ruleset の変更・main 直接 Push は行わない。
環境操作は対象、権限、復旧範囲が明示された場合に限る。

## 成果物と Handoff

標準の引継ぎは単一 Markdown。`templates/handoff.md` の
「目的・やったこと・観察結果・学び」に、repo / branch / commit、差分、
実行コマンドと結果、未確認点・阻害理由・次の担当を含める。
ログ、生成 JSON、render、試行ごとの出力は CI artifact に置く。
artifact の保存期限後も追試できるよう、再現手順と結論を Git Markdown に残す。
単一成果物に manifest / authorization / receipt / 独立 bytes pin を重ねる必要はない。

## マージ方針

feature branch と Draft PR を使い、独立 Review と required CI 後に Manager がマージする。
CI required check 名、security checks、安全拒否、通常の image digest と依存固定を維持する。
PR が未マージなら統合完了とせず、未検証の AC を成功にしない。

## 失敗と履歴

過去の失敗・未実施・未確認を成功に上書きしない。再試行時は変更理由と結果を短く追記する。
attempt 予算や配送台帳を通常の学習作業の必須入力にはしない。
過去の停止済みタスクを再開する許可は、この方針変更からは生じない。
旧版 JSON の再現には、その記録を作った固定 Git 履歴の CLI と schema を使う。現行 CLI へ再提出して成功扱いにしない。

## 互換性

既存 Handoff v2.0 の JSON schema / CLI とその回帰 fixture は互換用に保持する。
JSON 検証器は契約ごとの最新版のみを扱う。旧版は Git 履歴で再現する。標準の新規タスクには要求しない。
Markdown は `python scripts/validate_handoff.py templates/handoff.md` で構造確認できる。
新しい開発Handoffは [実行前契約](../docs/jira-execution.md) に従い、
`jira_execution.py --snapshot current.json --handoff handoff.md --operation repo-change`で照合する。
旧`jira_tracker.py`のPASSだけでは実行開始できない。snapshotは接続済みJiraの現在の読み取り結果と
Managerが独立して確認した人の承認から用意し、Gitに公開しない。
構造確認は事実・AC 達成・公開許可・独立レビューの証明にはならない。
非公開実行 ID、内部ログ、認証情報は公開しない。
