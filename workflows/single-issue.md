# 独立タスクで進める Issue ワークフロー

## 起動と責任分担

この手順は Manager が Dots / 既存 Codex Cloud から実行する運用契約であり、自動実行エンジンや Dots API の実装ではない。6プロセスを常設しない。各工程で役割定義と [起動入力](../templates/task-input.md) を渡した独立 Cloud タスクを起動する。追加の OpenAI API、新規課金サービス、新規 PAT は不要。

標準依存関係は Research/Design → Implementation → Test → Review → Manager 最終ゲート。設計だけの検証では Research → Test も可能。独立した作業の並行実行は依存がないことを Manager が確認した場合のみ。Knowledge は各工程の候補から非同期に起動し、開発の必須依存にしない。

1. Manager は認可された Issue 原文・全必須 AC 原文・対象 repo/revision・実行権限・工程固有の完了条件を初回入力へ明示する。役割定義には Issue 固有情報を書き込まない。
2. 同じ論理工程（Issue + role + scope）ごとに最大3試行（初回 attempt=1、再実行2回）を割り当てる。scope を言い換えて試行上限を回避しない。新しい独立タスクには新しい task_id を与える。
3. upstream handoff の JSON だけでなく、成果物の**実体**と根拠を取得する。固定 revision/digest、添付、本文コピーなど、後続が読める形で渡す。元タスクのローカルパスや終了通知だけを渡さない。
4. タスクを起動し、非公開の進捗台帳に role/scope/task_id/attempt/upstream と基盤状態を記録する。タスク間の会話・ファイル・認証・環境が自動共有されるとは仮定しない。

## 終了通知後のゲート

通知の `completed` は基盤上の終了であり、業務完了ではない。Manager は毎回以下を実行して判定を記録する。

1. 通知と一致する task_id/attempt/対象 revision の handoff と全成果物を取得する。タスクが落ちて handoff がない場合は Manager が失敗観測を記録し、成功とみなさない。
2. `python scripts/validate_handoff.py handoff.json` で形式・参照整合性を確認する。不正な handoff は `INVALID_HANDOFF` として依存後続を止める。
3. Issue の全必須 AC 原文と出典を認可済み入力に照合する。一部でも欠落・改変があれば blocked。schema は AC の完全性を証明しない。
4. artifact の実体、revision、根拠の内容、テストコマンドと実際の結果を読み、各 AC の担当範囲と役割固有の Completion Criteria を検査する。根拠が到達不能・不足なら blocked、既知の不合格や阻害指摘なら failed。
5. `status=completed` の自己申告と業務ゲートの両方を満たした場合だけ依存後続を起動する。Research の `covered` は設計範囲の完了であり、最終 AC 合格ではない。
6. 合格した handoff、成果物実体、AC 原文、採用判断、未確認点、後続の責務を**後続の初回入力**に組み込む。後から前の会話を参照できることを前提にしない。

## 失敗・不足・再試行

| 状況 | Manager の処置 |
| --- | --- |
| 必須 AC 原文が一つでも欠落 | `MISSING_ACCEPTANCE_CRITERIA` で blocked。役割側は外部取得・推測しない。Manager が既存の認可済み情報源から原文を補完し、出典付きの修正入力を作る。認可がない/取得不能なら人間に不足を報告して停止する。 |
| 修正可能な入力・成果物の不足 | 依存後続を停止し、修正点と責務を明記した新しい独立タスクを起動する。 |
| テスト不合格・レビュー阻害指摘 | Implementation 等の責任工程へ戻し、修正 revision に対して必要な Test/Review を再実行する。古い revision の合格を転用しない。 |
| 基盤失敗・handoff 不在 | 部分成果物を回収し Manager が失敗記録を作る。存在しない成果物・テスト結果を埋めない。 |
| 権限・接続不足 | 設定や Secrets、永続アクセスを変更せず阻害を報告する。別経路を使う場合も既存認可の範囲に限定する。 |
| attempt=3 でも未完了 | `RETRY_LIMIT_REACHED` を記録して停止し、人間に残件を返す。自動で回数をリセットしない。 |
| Knowledge の遅延・失敗 | Knowledge の状態と再試行を別管理し、開発は止めない。 |

再試行の `upstream` には直前の同一 role・同一 Issue の handoff を `retry_of` として含め、attempt は前回 +1 とする。他工程の依存は `dependency` として保持する。基盤失敗時の handoff は Manager が観測根拠付きで代行記録し、summary に代行であることを明示する。前回内容を上書きしない。工程をまたぐ修正ループも同じ論理工程の回数を消費し、いずれかが上限に達したら依存する開発ループを停止する。

## 開発完了と配送の別判定

最終報告では下記の状態を個別に `verified / failed / blocked / not_requested / pending` と根拠付きで記す。前の段階の成功を次の段階の成功としない。

| 検査対象 | 根拠 |
| --- | --- |
| 実装完了 | 対象 commit/差分、全 AC の最終対応、Test/Review の業務ゲート |
| GitHub remote 反映 | feature branch の remote head SHA とローカル SHA の一致 |
| Draft PR | PR URL、base/head、head SHA、draft=true を認可済み経路で取得 |
| CI | 同一 head SHA のチェック/run の結果。queued/in_progress は pending、未実行は未確認、CI がない場合は明示して成功としない |

CLI Git と GitHub 連携は別経路。GitHub 連携の成功は CLI の認証・ネットワーク障害解消を証明せず、その逆も同じ。失敗した経路と成功した経路を個別に報告する。main への直接 Push、merge、auto-merge はこの運用では行わない。

## Knowledge と変更単位

Manager は候補の配送と進捗のみ管理し、Knowledge Agent が raw の保全、抽象化、採否、記事更新を担当する。知識用 Issue/PR を分けることも開発差分に含めることも可能であり、1 Issue=1 PR や repo ごとの分割を絶対条件にしない。権限とレビュー可能性に応じて変更単位を選ぶ。

公開前には内容を読み、実際の非公開 task/thread/message ID、私的会話、個人情報、内部メモ、認証情報、運用ログを除外する。公開サンプルは架空の識別子・プレースホルダーのみとし `synthetic sample` を明記する。知識候補やメタデータの public_safe 自己申告だけで公開を承認しない。
