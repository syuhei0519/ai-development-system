---
name: cluster-diagnose
description: クラスタ platform-lab の障害や異常（Pod が Running でない、Application が Synced や Healthy でない、画面が開かない）を調べるときに使う。読み取りだけで調べ、事実、推定、次に確認することを分けて報告する。
argument-hint: "[症状、namespace、Application 名など]"
allowed-tools: Bash(make status) Bash(kubectl get *) Bash(kubectl describe *) Bash(kubectl logs *) Bash(kubectl top *) Bash(kubectl events *) Bash(argocd app get *) Bash(argocd app list *)
---

症状 $ARGUMENTS を、読み取りだけで調べます。変更操作（apply、delete、patch、scale、rollout、sync、restart）は 1 つも実行しません。

## 調べる順番

1. 全体: `make status`（なければ `kubectl get nodes` と `kubectl get pods -A | grep -v -E 'Running|Completed'`）
2. 異常な Pod: `kubectl describe pod <pod> -n <ns>` の Events と、各コンテナの State、Last State、Reason
3. イベント: `kubectl events -n <ns> --types=Warning`
4. 直前のログ: `kubectl logs <pod> -n <ns> --previous --tail=100`（再起動していなければ --previous なし）
5. Argo CD: `argocd app get <app> --core` の sync、health、直近の操作の結果
6. 資源: `kubectl top nodes`、`kubectl top pods -n <ns>`、`kubectl describe quota -n <ns>`

各段階で原因が絞れたら、残りは必要な分だけ読む。

## ログの要約

ログやイベントが長いときは、Agent ツールで model に haiku を指定した `platform-lab:platform-operator` に、エラーの行と時刻だけを要約させる。要約に Secret の値や IP が含まれていたら伏せる。

## 報告の書式

- **事実**: 実行したコマンドと、出力から読み取れること（Pod 名、Reason、終了コード、メッセージ）
- **推定**: 原因の候補を確からしい順に。それぞれ根拠になった事実を示す
- **次に確認すること**: 推定を確かめる読み取りのコマンド
- **直すなら**: 変更が要る場合は、変更する場所（Git のファイル）と案を示し、人の判断を待つ

ノード名、IP、Secret の値、内部パスは報告に書かない。
