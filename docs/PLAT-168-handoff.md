# Handoff

## 目的
- Source: jira-native
- Jira Site: https://syuhei0519.atlassian.net
- Jira Cloud ID: 0e029d88-1812-4bd9-b5de-bdecfff6740b
- Jira Project: PLAT
- Jira ID: 10178
- Jira: PLAT-168
- Jira URL: https://syuhei0519.atlassian.net/browse/PLAT-168
- Source GitHub: none
- Target Repo: syuhei0519/ai-development-system
- Base Commit: e387d151ab4f406d372b2b4473d57f21539243fa
- Authorization: human approval 2026-10-22 PLAT-168-170 repo work

### AC
* ai-development-systemの現行resolver/Manager契約を確認し、migratedとjira-nativeの明示的なsource区分、Jira site/project/issue ID/key/URL、対象repo・固定base・ACの照合方法を定義する。
* 新規Jira課題は現Jiraのidentity・本文・停止/再開条件を検証し、旧GitHub Issueがないことを正常ケースとして扱う。移行課題では既存GitHub↔Jira対応の検証を保持する。
* 不明なsource区分、別site/project、誤ったkey/URL/id、AC欠落、停止中、必要承認なし、repo対象外をfail closedで拒否する。GitHub Issue番号を自動生成・推定しない。
* 一枚MarkdownのhandoffにJira identity、source区分、対象repo、AC/証跡、未承認操作、停止理由を含める。過去のschema/履歴を遡及変更せず、mergeだけでDoneにしない。
* native成功・migrated成功・identity不一致・停止維持・権限不足のfixture回帰が通り、運用文書と実装契約が一致する。

## やったこと
- feature branch: feat/plat-168-native-execution。人の明示承認による通常repo経路でbootstrap。
- 新規 scripts/jira_execution.py と単一Markdownテンプレート、Manager/workflow/運用文書、fixture回帰を追加。
- 既存153件対応表、旧resolver、旧schema、recordsは無変更。

## 観察結果
- AC Evidence: AC1 identity/source/repo/base/AC照合、AC2 native/migrated分岐、AC3拒否回帰、AC4単一Markdown、AC5対象17回帰と独立Reviewで確認。PR CI/統合はpending。
- Unapproved Operations: merge, deploy, credentials, permissions
- Stop Reason: none
- 独立Review初回の5指摘（operations型、未承認欄矛盾、AC部分一致、updated欠落、文書矛盾）を修正。再Reviewで対象17回帰成功、阻害指摘なし。
- 再現: python -m unittest discover -s tests -v; python scripts/jira_tracker.py --check-mapping; python scripts/validate_delivery_records.py; git diff --check。
- Windows全suiteはLinux前提の依存/パスで失敗。WSL Ubuntuの専用venvへ切替。初期版409回帰成功、修正版410回帰成功。153件照合、両Markdownテンプレート、旧delivery記録検証、diff checkも成功。
- Jiraは進行中。コメント10002で実行承認と履歴を記録し、対象のexecution-paused labelのみ解除。旧本文は保存。

## 学び
- checkerは入力整合性のみで、人の本人性やsnapshot鮮度を認証しない。Managerの接続済みJira・会話確認が必須。
- 実装/fixtureの停止条件は解消。PRはdraft、merge/auto-mergeは未承認。未統合なのでJira Doneではない。

