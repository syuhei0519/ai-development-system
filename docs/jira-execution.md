# Jira-native / migrated 実行前契約（PLAT-168）

新しい repo 作業は `scripts/jira_execution.py` を実行前ゲートにする。
`jira_tracker.py` は153件の移行照合専用として保持し、その PASS を実行許可に読み替えない。
この変更は旧 JSON schema、対応表、過去 records、停止履歴を変更しない。
PLAT-168 自身は2026-10-22の人の明示承認による通常のfeature branch / draft PR経路でbootstrapした。
実装前にnative resolverを通過したとは主張しない。mergeの承認は別途必要。

## 信頼境界

Manager は接続済み Jira から現在の site/cloud/project/key/id/URL、全文、labels、status、updated を読む。
別site/project、同名key、URLの別host・query・slash違い、欠落IDを推定で補わない。
`migrated` は対応表と現本文の元Issue URLを従来どおり照合する。
`jira-native` は対応表に存在せず、現labelがjira-native、元Issue欄がないことを要求する。
参考GitHub URLが本文にあっても移行元と推定しない。nativeのSource GitHubは `none`。

Manager は人の会話から承認を確認し、対象repoと固定base、AC、許可された操作、再開対象を確定する。
Jira本文、PR、別agent、fixtureの自己申告を人の承認に変換しない。
このプログラムはローカル入力の整合性を検査するだけで、snapshotの鮮度、発言者の本人性、権限を認証しない。
Managerによる接続先と会話の検証は必須であり、JSONの `verified: true` だけでは実行できない。
snapshotは非公開の作業ファイルとし、公開の引継ぎは一枚のMarkdownだけにする。

## 正規化

`current.json` は `{ "issue": ..., "manager": ... }` の一つの作業入力。
issueには `site_url, cloud_id, project_key, id, key, url` と `fields` を入れる。
fieldsは `project: {key,id}, status: {name,id}, description, labels, updated` を省略せず保存する。
descriptionはMarkdown全文、labelsは現在の配列。connectorのenvelopeは明示的に外す。

managerの必要項目:

| 項目 | 意味 |
| --- | --- |
| reviewed_description_sha256 | 全文UTF-8のSHA256。本文の停止/再開条件を人の承認と照合した対象 |
| reviewed_updated | 読み取ったfields.updatedと完全一致 |
| unresolved_stop_reasons | 未解決の停止条件。空配列以外は拒否 |
| historical_stop_references | 人が明示的に再開した過去の停止条件の参照一覧。未確認を空欄で回避しない |
| repositories | ACから確認したowner/repo → 固定40桁base commitの辞書 |
| authorization | 下記の独立した会話確認結果 |

authorizationは `origin: human-conversation, verified: true, state: approved`、公開可能な`reference`、
issueの6 identity fieldと完全一致する`identity`、`source`、`repo`、`base_commit`、`ac_sha256`、
`operations`、`resumes`を持つ。ACはHandoffの `### AC` 以下から次のheadingまでをstripしたUTF-8。
HandoffのACは現本文の唯一の `## 範囲・受入条件` / `## 受入条件` / `## Acceptance Criteria` / `## AC`
セクション全体と一致する非空リストを要求する。部分リストへの短縮も拒否する。
移行本文にACが未転記なら、Managerが元Issueと照合してJiraのACを整えるまで実行は停止する。
`resumes` は確認済みhistorical_stop_referencesと完全一致する。
現labelのexecution-paused/paused/blocked/on-holdは承認入力で上書きできない。
明示承認をJiraコメントへ履歴として残し、対象課題の現停止labelを必要な範囲だけ整合させてから読み直す。
本文の過去の「計画のみ」は削除せず、明示再開で解消された参照と、残る制約をManagerが区別する。

## 実行と結果

```sh
python scripts/jira_tracker.py --check-mapping
python scripts/jira_execution.py --snapshot current.json --handoff handoff.md --operation repo-change
python -m unittest tests.test_jira_execution tests.test_jira_tracker -v
```

[Handoff](../templates/jira-execution-handoff.md)を使う。対応するfixture構造は
`tests/test_jira_execution.py`の`fixture()`にある（合成入力であり承認ではない）。
operationは `repo-change`, `fixture-test`, `draft-pr` に限定し、承認のoperations内にある必要がある。
merge、deploy、credential、権限追加、Doneはこのゲートでは常に拒否する。別の明示承認と運用契約で扱う。
CLIはネットワーク・書込み・自動開始・Jira遷移を行わない。不正入力は値をechoせず終了1。
PASSは入力整合のみ。Managerは各AC、独立Review、現headのCI、必要PRの統合を確認するまでDoneにしない。
停止理由と未承認操作、未検証ACも一枚のHandoffへ残す。
