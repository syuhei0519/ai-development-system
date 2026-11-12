# ai-development-system

## 目的

Platform Lab の開発を Claude Code で安全に進めるためのプラグイン `platform-lab` を配布する。
柵（hooks、permissions、sandbox、ruleset、CI）を文書ではなく仕組みで持つことを最優先にする。

## 構成

```
.claude-plugin/marketplace.json   マーケットプレイス（このリポジトリ）
plugins/platform-lab/             プラグイン本体
  .claude-plugin/plugin.json
  agents/                         planner、implementer、reviewer、platform-operator、tutor
  hooks/                          hooks.json、guard-*.sh、post-edit-lint.sh、tests/（cases.tsv、run.sh、fixtures/）
templates/                        各 repo へ配るひな形（P3-01 以降で追加）
```

旧 Codex 期の資産（agents/、config/、contracts/、examples/、scripts/、tests/、workflows/、
knowledge/、records/）は作業パッケージ P3-08 で削除するまで並存させる。新しい変更は加えない。
保存点はタグ `archive/codex-2026-11`。

## コマンド

```sh
bash plugins/platform-lab/hooks/tests/run.sh            # hook の試験
shellcheck -x plugins/platform-lab/hooks/*.sh           # 静的検査
claude plugin marketplace add ./ && claude plugin install platform-lab@ai-development-system
```

## 変更の流れ

1. Jira のチケット（PLAT-xxx）を読み、計画を出して承認を得る
2. ブランチ feat/PLAT-xxx-名前 を作る
3. 変更し、hook の試験と shellcheck を通す。hook の判定を変えたら cases.tsv に 1 行以上足す
4. PR を作る（タイトル「PLAT-xxx: 要約」、追加 400 行以内、本文は 何を／なぜ／どう確かめたか／学び）
5. 人が merge する

## hook を書くときの約束

- bash と jq だけで書く。jq がない環境では拒否（終了コード 2）に倒す
- 拒否の文は「何が、なぜ止まったか、代わりにどうするか」を 1〜2 行で書く
- hook は文字列の照合なので迂回できる。確実に止めたいものは sandbox と専用 kubeconfig で塞ぐ
- Claude Code の設定書式は公式ドキュメント（hooks、plugins、sub-agents）で確かめてから書く

## 守ること

- 確かめていないことは「未確認」と書く
- 証跡、受入記録、実機のスナップショットを Git に入れない
- hook や権限で止められたら、迂回せず、理由を伝えて人に確認する
