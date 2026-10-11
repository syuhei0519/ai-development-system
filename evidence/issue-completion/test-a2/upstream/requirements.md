# Issue Completion集約契約の設計要件

公開安全候補 / edited derivative / 未公開。ここでのAG番号は設計要件の公開ラベルであり、製品Issueや実行IDではない。以下の技術要件を設計の判定基準とする。製品ACの合格を表さない。

## AG-1

PR単位MergeReadinessとIssue全体Completion分離、単一PRmerge/全premergeACmetだけでachievedにしない。

## AG-2

必要なPR/repo/mergeSHA/承認済みscope/構成・image digest/実測環境/時刻/証跡期限を集約し、欠落・旧head・未merge・未配備・scope不足・証跡不一致はfailclosed。

## AG-3

postmerge/postdeployの実測とpremerge試験を区別、全AC原文一致/全体integrationready/全必須実測metの後だけManagerがachieved。製品操作権限をreceipt/記事から推論しない。

## AG-4

head変更/新必須PR/配備revision変更/失効時の再評価、rollback/失敗/未検証を記録。

## AG-5

Handoffv2/Readinessv1互換、JSONschema/CLI/正常異常テスト/採用案と境界を具体化。既存GitHub必須check/review/rulesetは迂回禁止。UserapprovalとGitHubauthorityは別。

## 担当範囲と完了条件

Research/Design工程として、既存の役割・Readiness v1・Handoff v2・ArtifactDelivery・CLI・tests・workflowを確認し、変更案を比較して推奨を示す。JSON Schemaの必須フィールド・意味検証・CLI・正常異常テスト・互換性・権限境界を具体化する。コード実装・製品実測・公開操作はこの成果物の完了範囲に含めない。

正常テスト計画はsyntheticだけを用いる。実製品の未測定結果をmetに置き換えない。Implementationは別途与えられた正本AC、固定対象revision、承認scopeを使用し、公開派生版から権限や未収録の製品要件を補完しない。
