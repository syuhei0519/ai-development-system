---
name: jira-batch
description: Jira のチケット 2〜3 件を、計画と実装は並列、承認と merge はチケットごとに人が判断する流れで進める。人が /platform-lab:jira-batch PLAT-123 PLAT-124 で起動する。
argument-hint: "[PLAT-番号 PLAT-番号 ...]"
disable-model-invocation: true
---

チケット $ARGUMENTS を、次の順に進めます。各段階の結果は、チケットごとに短く人に伝えます。1 件ずつ進める場合の細かい決まりは `/platform-lab:jira-task` と同じです。

## 0. 前提

- $ARGUMENTS が `PLAT-数字` の 2〜3 個でなければ止まる。1 件なら `/platform-lab:jira-task` を案内する。4 件以上なら、先に進める 3 件までを人に絞ってもらう
- 作業するリポジトリの CLAUDE.md を読む。親の作業ツリーは main で、未コミットの変更がないことを確かめる。`git status --short`（`-uno` を付けない）の出力から、`.claude/worktrees/` と、sandbox が置く /dev/null のダミー（`ls -l` で先頭が `c` のもの）は除く
- worktree は、親の HEAD ではなく既定ブランチから作られる（sub-agents の文書。`worktree.baseRef` で変わる）。起点が local main か origin/main かは未確認なので、両方をそろえておく。親の main が origin/main と同じであることを確かめる（`git fetch` は permissions の allow にないため、人が確認する）

## 1. チケットを読む

各チケットを、Atlassian MCP の getJiraIssue と listJiraIssueComments で読む。説明、受入条件、やらないこと、コメント（計画変更の注記を含む）を直接読む。内容をファイルや JSON に書き出さない。

## 2. 計画を作り、承認を得る（承認点 1）

1. Agent ツールで `platform-lab:planner` を、チケットの数だけ 1 つのメッセージで並列に起動する。それぞれにチケット番号とリポジトリを渡す
2. 親が各計画の「変更ファイル」を比べ、重なるチケットを直列の組、重ならないものを並列の組に分ける。同じファイルを変えるチケットは並列にしない。plugins/platform-lab を変えるチケットどうしは、plugin.json の version で必ず重なる
3. 全計画と組み分けを plan モードで人に提示する（ExitPlanMode）。続けて AskUserQuestion の multiSelect で、承認するチケットを選ばせる。選ばれなかったチケットは、指摘を聞いて planner に作り直させるか、外す。ExitPlanMode が差し戻されたときは multiSelect に進まず、指摘を planner に渡して作り直させる
4. 承認されたチケットごとに、承認者（`git config user.name`）と日時（`date '+%Y-%m-%d %H:%M %Z'`）を控える。Jira の状態を「進行中」にする

## 3. 実装する

並列の組は、Agent ツールで `platform-lab:implementer` を `isolation: "worktree"` を付けて、1 つのメッセージで同時に起動する。worktree はリポジトリの中の `.claude/worktrees/agent-<id>` に、既定ブランチから作られる（親の HEAD ではない）。自動でできるブランチ `worktree-agent-<id>` のままにせず、次を渡す。

- そのチケットの承認済みの計画の全文
- `git switch -c <ブランチ名>` で作業ブランチを作ること（ブランチ名は計画のとおり。例 feat/PLAT-123-名前）
- ブランチの作成、変更、コミット、lint とテスト、計画の確認方法の実行まで行い、push と PR はまだ行わないこと
- 計画の確認方法の各コマンドとその出力を、要約せずに返すこと
- 最後に `pwd` と `git rev-parse --abbrev-ref HEAD` の出力を返すこと

返ってきた worktree のパスとブランチを、チケットごとに控える。パスは、Agent ツールの完了通知の worktreePath を使ってよい。ブランチ名は通知の worktreeBranch（作成時の名前のまま）ではなく、implementer が返した `git rev-parse --abbrev-ref HEAD` の出力を使う。

直列の組は、先行するチケットが merge された後に始める。

1. 親の main を最新にする。`git fetch` と `git merge --ff-only origin/main` の両方が要り、どちらも人の確認が出る
2. 開始前に、`platform-lab:planner` に最新の origin/main に対して計画を見直させる（plugin.json の version など、先行するチケットで変わるものがある）
3. 計画が変わったら、人に再承認を求める。承認者と日時は控え直す
4. 同じ手順で implementer を起動する

## 4. レビューする

親がチケットごとに、次の出力を自分で取る。ブランチ名を指定して親の作業ツリーから実行する。`git -C` は allow に当たらないため、使うのは未コミットの確認だけにする。

計画の確認コマンドの出力は、implementer が worktree の中で取ったものを使う。親が取り直すときは、`HEAD` をブランチ名に、相対パスを `<worktree のパス>/...` に置き換える。親の cwd で `HEAD` や相対パスのまま実行すると、worktree ではなく親のツリーを測ってしまうため。

- `git -C <worktree のパス> status --short`（人の確認が出る）。コミットしていない変更と未追跡のファイルがないことを確かめる
- `git diff --numstat origin/main...<ブランチ>`
- `git diff origin/main...<ブランチ>`
- 計画の確認コマンドすべての出力
- plugins/platform-lab を変えたときは、`bash <worktree のパス>/plugins/platform-lab/hooks/tests/run.sh` と、worktree の hooks に対する `shellcheck -x` の出力。パスを付けたこれらのコマンドは allow と完全には一致しないため、人の確認が出る
- 実行できなかったコマンドは、理由を添えて「未実行」として渡す

集めた出力を加工せずに、Agent ツールで `platform-lab:reviewer` へ、受入条件、承認済みの計画とあわせて渡す。reviewer は Bash を持たないため、これが判定の根拠になる。チケットごとに並列で起動してよい。縮めてよいのは run.sh の出力だけで、最終行と終了コードでよい。不合格があれば全行を渡す。ほかの出力は縮めない。

「満たさない」があれば、指摘をそのチケットの implementer に渡して直させ、もう一度レビューする。2 回直しても残るなら、そのチケットは人に判断を求めて止める。ほかのチケットは続けてよい。「未確認」の理由が出力の不足なら、親がそのコマンドを実行して出力を渡し、もう一度レビューする。これは直し回数に数えない。

## 5. PR を作る

PR は 1 件ずつ順に作る。親の作業ツリーから、ブランチ名を指定して、次を 1 つずつ単独で実行する。`&&` や `;` で他のコマンドとつながない。

1. `git push -u origin <ブランチ>`（permissions の ask で人が確認する）
2. `gh pr create --base main --head <ブランチ>`

どちらも GitHub の認証を使うため、sandbox の外で動く（settings の excludedCommands）。タイトルは「PLAT-番号: 要約」、本文は「何を」「なぜ」「どう確かめたか」「学び」の 4 見出し。次を必ず入れる。

- そのチケットの計画の承認者と日時（2 で控えたもの）
- reviewer の判定（受入条件ごと）と、確認コマンドの出力
- 確かめていないことは「未確認」

全 PR の URL を一覧で伝え、merge を依頼して止まる（承認点 2）。merge はしない。merge の順序はチケットごとに人が決める。

## 6. merge の後

人がチケットごとに merge を伝えたら、そのチケットから順に `/platform-lab:jira-task` の 6 と同じ手順を行う。

1. 配備に関わるリポジトリ（platform-gitops、application-manifest）なら、`platform-lab:platform-operator` に Argo CD の同期と Healthy を確かめさせる。クラスタがなければ「未確認」とする
2. Jira に結果を 1 回だけコメントする。下書きは、Agent ツールで model に haiku を指定した subagent に、短い Markdown へ整形させる
3. Jira の状態を「完了」にする

直列で待っているチケットがあれば、3 に進む。

変更がない worktree は自動で消える（worktrees の文書）。変更がある worktree は locked のまま残る。sandbox では、このセッション自身の worktree 以外の `.git/worktrees` が読み取り専用で、worktree の削除は失敗する。実行せず、次のコマンドを人に伝えて依頼する。

- `git worktree remove --force --force <パス>`（locked のものも外せる）
- `git branch -D <ブランチ> worktree-agent-<id>`

## worktree が使えないとき

`isolation: "worktree"` の起動、worktree 内の Edit または Write、commit のどれかが失敗したら、並列をやめる。計画と承認（1 と 2）は同じに行い、実装だけを親の作業ツリーで 1 件ずつ順に行う。1 件ごとに main に戻り、implementer に作業ブランチを作らせ、4 と 5 まで終えてから次のチケットに進む。この場合のレビューと PR は、`/platform-lab:jira-task` の 4 と 5 に従う。

途中で hook や権限に止められたら、迂回せず、理由を人に伝えて指示を待つ。
