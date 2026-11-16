---
name: gitops-change
description: Helm chart や gitops/ 配下（Argo CD が読む宣言）を変更するときに使う。描画と検証を通し、PR を作り、merge 後に同期と Healthy を確かめる。
argument-hint: "[chart または gitops のパス]"
allowed-tools: Bash(helm lint *) Bash(helm template *) Bash(kubeconform *) Bash(argocd app diff *) Bash(argocd app get *)
---

対象 $ARGUMENTS の変更を、次の順に確かめます。

## 1. 描画の検査

変更した chart と、それを使う values ごとに実行する。make lint や make template があれば、そちらを優先する。

```
helm lint <chart> -f <values>
helm template <release> <chart> -f <values> > /tmp/rendered.yaml
kubeconform -strict -summary -ignore-missing-schemas /tmp/rendered.yaml
```

- エラーがあれば直してからやり直す。警告は PR 本文に書く
- 描画結果のうち、変更で増えたり変わったりする資源（kind と name）を一覧にする

## 2. クラスタとの差分（クラスタがある場合）

context が kind-platform-lab のときだけ、対象の Application の差分を見る。

```
argocd app diff <app> --core --local <path>
```

クラスタがなければ「未確認（クラスタなし）」と書いて次へ進む。

## 3. PR

PR 本文の「どう確かめたか」に、1 の結果（lint と kubeconform の要約）と、2 の差分の要点を貼る。追加行が 400 を超えるなら分割を提案する。

## 4. merge の後

1. `argocd app get <app>` で、sync が Synced、health が Healthy、revision が merge した commit であることを確かめる
2. 収束しない場合は cluster-diagnose の手順で原因を調べる。sync や delete などの変更操作は人に依頼する

## やらないこと

- `kubectl apply` や `helm upgrade` での手動適用。配備経路は Git と Argo CD の 1 系統だけにする
