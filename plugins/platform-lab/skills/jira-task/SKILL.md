---
name: jira-task
description: Jira のチケット 1 件を、計画、人の承認、実装、レビュー、PR、Jira コメント 1 回まで 1 つの流れで進める。人が /platform-lab:jira-task PLAT-123 で起動する。
argument-hint: "[PLAT-番号]"
disable-model-invocation: true
---

チケット $ARGUMENTS を、次の順に進めます。各段階の結果は短く人に伝えます。

## 0. 前提

- $ARGUMENTS が `PLAT-数字` でなければ、チケット番号を人に聞いて止まる
- 作業するリポジトリの CLAUDE.md を読む。現在のブランチが main で、未コミットの変更がないことを確かめる

## 1. チケットを読む

Atlassian MCP の getJiraIssue と listJiraIssueComments で、説明、受入条件、やらないこと、コメント（計画変更の注記を含む）を直接読む。内容をファイルや JSON に書き出さない。

## 2. 計画を作り、承認を得る（承認点 1）

1. Agent ツールで `platform-lab:planner` に、チケット番号とリポジトリを渡して計画を作らせる
2. 計画を plan モードで人に提示する（ExitPlanMode）。承認されなければ、指摘を planner に渡して作り直す
3. 承認されたら、承認者（`git config user.name`）と日時（`date '+%Y-%m-%d %H:%M %Z'`）を控える。Jira の状態を「進行中」にする

## 3. 実装する

Agent ツールで `platform-lab:implementer` に、承認済みの計画の全文を渡す。ブランチの作成、変更、lint とテスト、計画の確認方法の実行まで行わせ、PR はまだ作らせない。

## 4. レビューする

1. Agent ツールで `platform-lab:reviewer` に、受入条件、承認済みの計画、`git diff origin/main...HEAD` の対象ファイルを渡す
2. 「満たさない」があれば、指摘を implementer に渡して直させ、もう一度レビューする。2 回直しても残るなら、人に判断を求めて止まる

## 5. PR を作る

implementer に PR を作らせる。タイトルは「$ARGUMENTS: 要約」、本文は「何を」「なぜ」「どう確かめたか」「学び」の 4 見出し。次を必ず入れる。

- 計画の承認者と日時（2 で控えたもの）
- reviewer の判定（受入条件ごと）と、確認コマンドの出力
- 確かめていないことは「未確認」

PR の URL を人に伝え、merge を依頼して止まる（承認点 2）。merge はしない。

## 6. merge の後

人が merge を伝えたら再開する。

1. 配備に関わるリポジトリ（platform-gitops、application-manifest）なら、Agent ツールで `platform-lab:platform-operator` に Argo CD の同期と Healthy を確かめさせる。クラスタがなければ「未確認」とする
2. Jira に結果を 1 回だけコメントする。下書き（PR の URL、受入条件ごとの結果、未確認の項目）は、Agent ツールで model に haiku を指定した subagent に、短い Markdown へ整形させる
3. Jira の状態を「完了」にする

途中で hook や権限に止められたら、迂回せず、理由を人に伝えて指示を待つ。
