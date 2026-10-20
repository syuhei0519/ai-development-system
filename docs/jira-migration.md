# Jira への作業管理切替（step 4）

## 確認した実データ（2026-10-20）

接続済み Jira を読み取り、`PLAT` / Platform Engineering Lab / project ID `10001` が
company-managed (`classic`) の software project であることを確認した。別の `KAN` project と混同しない。
全167件を2ページで取得。元 Issue URL を本文に持つ153件と、新設 Epic 14件だった。
実 status は未着手135件、完了32件で、この作業では変更・再検証していない。
対応表は [config/jira-tracker.json](../config/jira-tracker.json)。取得した実 key と本文の
`元Issue URL` の1対1対応を保存し、移行案から採番を推測していない。
例: backend-app#36 → PLAT-3、frontend-app#6 → PLAT-5、ai-development-system#13 → PLAT-167。
新設 Epic 14件には単一の移行元がなく、この1対1 resolver では実装タスクとして選べない。
Epic の配下リンクを自動的な1対1対応や実装開始許可へ変換しない。

実 workflow は全 work type 共通で次の3状態。状態の存在と現在実行可能な transition は別である。

| ID | 実 status | 意味 |
| --- | --- | --- |
| 10005 | 未着手 | 候補・未開始。保留や停止の解除を意味しない |
| 10006 | 進行中 | 許可された作業中。Review / blocked / paused は別途明示 |
| 10007 | 完了 | 既存の観測値。今回のAC再検証済みという意味ではない |

ブラウザで開かれていた `PLAT board` (ID 2) を API でも確認。Scrum、filter ID `10001`、
JQL は `project = "PLAT" ORDER BY Rank ASC`。列は上記3状態に対応する。
UI の `PLAT Sprint 1` は0件、開始前の表示だった。Sprint を開始・編集していない。
取得できた保存 filter はこの1件。探索専用の Kanban board / 分離 filter は未確認であり、作成しない。
本文の `表示先案`、`状態案`、元 GitHub ラベル、移行ラベルは実 board / status / priority / sprint の設定ではない。

## 通常の開始と照合

1. Manager が Jira の現在の課題、AC、依存、status、labels、本文の保留・停止条件を読む。
   GitHub の元 Issue / PR は出典として読む。Issue closed や移行済み完了を今回の検証結果に置換しない。
2. 既存 key と元 URL を対応表で照合。両方が一致する既存課題を使う。
   不明・欠落・重複・矛盾・新設 Epic は該当作業を blocked にし、現在の Jira と出典を調べる。
   resolver 失敗で新規課題を作らず、GitHub 選定へ戻らない。対応表を更新する場合も独立に確認する。
3. ユーザーが許可したタスクだけを計画・委任する。Jira key / URL と Source GitHub を
   [単一 Markdown](../templates/handoff.md) の目的に含める。repo / PR / commit は GitHub identity を保持する。

`scripts/jira_tracker.py` はネットワークも書込処理も持たない。接続ツールの getJiraIssue 読取結果を
次の最小形式に明示的に正規化して、非公開の作業ファイル `current.json` に保存する。
connector の envelope は外す。description は Markdown、labels は実配列を渡す。推測で埋めない。

```json
{
  "key": "PLAT-3",
  "fields": {
    "project": {"key": "PLAT"},
    "status": {"id": "10005", "name": "未着手"},
    "description": "* **元Issue URL**: https://github.com/syuhei0519/backend-app/issues/36",
    "labels": ["migration-pilot-20261020"]
  }
}
```

これは形式例で、実タスクの現在の全文やラベル一覧を代用するものではない。
status ID / project が接続結果にない場合は省略可能。key・実 status 名・description・labels は必須。
同じ入力の再確認は同じ identity を返し、課題・ファイルを作成・更新しない。

```sh
python scripts/jira_tracker.py --check-mapping
python scripts/jira_tracker.py --key PLAT-3 --snapshot current.json --handoff handoff.md
# 元URLからも同一identityへ解決できる（旧Issueの選定・更新ではなく移行照合）
python scripts/jira_tracker.py --source-github-url https://github.com/syuhei0519/backend-app/issues/36 --snapshot current.json
```

この検証は対応と形式の整合性だけを見る。snapshot の鮮度・真正性、AC 達成、開始権限、独立 Review は
Manager が接続済み正本と証跡を確認する。PASS から開始・完了・status 更新を実行しない。
現在状態が未知、接続不可、書込結果が不確かなら停止して読戻し・照合する。

## 状態と完了の所有者

仕事の選定・計画・進捗・完了は Jira で Manager が責任を持つ。各担当は結果と未確認点を Handoff で報告する。
進行中の Review と停止理由は Jira の進捗記録および Handoff に明示し、架空の Review / Blocked status を要求しない。
別途許可された将来の状態更新では、現在値とその課題で可能な transition を読んでから必要な差分だけ行う。
既に目標状態なら no-op。不確かな結果を再送せず、key を使って先に照合する。
この変更は自動同期クライアント・自動遷移・通知・旧 Issue の Close / 本文更新を実装しない。

完了は、担当工程の終了、PR の統合、全 AC の最終確認を分ける。
Manager は独立 Review、現在 head の required CI、必要 PR の main 統合と固定 revision、
各 AC の根拠・実行結果を確認する。未マージは未統合、未確認は未確認のまま残す。
移行済みの完了状態、自己検証、学習 Session 完了だけを新たな完了根拠にしない。
Release / deploy は Sprint 完了とは別の許可・CI・証跡が必要で、Sprint 終了で自動発行しない。

開発は Sprint Goal と選定対象を合意した Scrum、探索・Spike は WIP を制限する Kanban が方針。
現ボードは全 PLAT を表示するため、専用表示先は今後別途確認する。移行案ラベルから勝手に振り分けない。
初回 Sprint の目標・対象・開始、停止タスクの再開はこの tracker 切替に含まれない。

学習 Topic / Session は独立する。`personal-learning-system` の汎用 source URL は Jira URL を既存の
`kind=issue` として保持でき、元 GitHub Issue / PR と実装 commit を併記する。UUID や過去 Session を再採番しない。
学習未開始・中断・未修了を開発完了のゲートにしない。

## 互換性と有効化

検証: Windows の接続PC上の WSL Ubuntu と作業用 venv で、既存393件＋追加8件の
`python -m unittest discover -s tests -v` 全401件成功。
`jira_tracker.py --check-mapping`、実際の read-only PLAT-3 snapshot の照合、
`validate_handoff.py templates/handoff.md`、`validate_delivery_records.py`、`git diff --check` も成功。
テスト用 venv を activate して、既存テストが起動する `python3` にも依存を渡した。
新テストは対応表の一意性・再実行の同一結果・欠落/重複/不一致/未知状態の拒否・Handoff照合を確認する。
Jira書込・状態遷移・学習Session実行はテストしていない。独立ReviewとGitHub現head CIはPRで別途確認する。

既存 JSON schema・旧 CLI・fixture・過去 records は変更していない。明示的な旧契約の検証用であり、
Jira への入力アダプターや現在の完了・操作許可として利用しない。GitHub Issue の自動 Close keyword を新規PRへ書かない。
実行スクリプト・CI に GitHub Issue / Projects 更新クライアントは存在せず、残る `close_issue` は旧契約の許可分類である。
現在の文書にあった旧 Issue 更新指示を外し、新規 Issue テンプレートを Jira への案内に切り替えた。

関連4repoは tracker コマンド・CI の該当参照を確認。残る Issue 記述は過去の受入・handoff・再構築記録であり変更しない。
`personal-learning-system` は汎用 URL のためモデル・schema の変更は不要。学習入口の参照先だけを補足する。
着手時の ai-development-system は main `42521c0`、open PR なし、Jira 用の既存 branch なしを確認した。

有効化はこのPRの現head CIと独立Reviewを確認後、Managerが別途mergeを判断する。
その後、実際に使う Manager / ChatGPT Project の指示が新しい定義を参照することを確認する。
board 分離、workflow の追加状態、外部のGitHub Projects自動化がある場合の停止確認は別途必要。
それらをこのPRが設定済み・停止済みと主張しない。旧 Issue の一括変更や追加 import は行わない。
