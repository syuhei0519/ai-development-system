---
id: "K-DELIVERY-001"
title: "配送検証の成功から、何を言えて何を言えないか"
domain: "validation"
status: "draft"
updated: "2026-10-11"
review_after: "修正headの独立Test/Review確定、契約版更新、反例発見、または2026-11-11"
tags: ["artifact-delivery", "承認", "固定出典"]
raw_sources: ["../../raw/validation/artifact-delivery-lessons.md"]
supersedes: []
superseded_by: []
publication: "public_safe"
---

# 配送検証の成功から、何を言えて何を言えないか

## 要点

ファイルが正しく届いたことと、その内容が正しいこと、利用してよいこと、製品が合格したことは別である。配送検証は固定revisionの実体が宣言どおり届き、指定された型・参照関係を満たしたことを示す。承認や製品合格まで推論を伸ばさない。

## 適用条件・範囲

固定Gitの成果物をAgent間で受け渡す場合に適用する。ここでの実例はDelivery 1.2の過去独立Test報告であり、本Knowledgeが読取り前に使用した外側配送はDelivery 1.0である。Knowledge本体契約は1.0。これらの版と責務を混同しない。

## 根拠と出典

[rawのKD-001とS1](../../raw/validation/artifact-delivery-lessons.md)は、旧headにおける独立Testが17 objects / 89071 bytesを正式CLIとfresh recheckで照合したと報告する。Knowledgeは報告ファイルの全bytesと固定SHAを照合した。内側のCLI実行・アプリ実行はしていない。
固定Git URLとSHA-256はrawのS1に明記し、[同一bytes](../../raw/validation/evidence/test-report.json)を保持する。公開派生版の検査であり、非公開原本との同一性は認定しない。

## 重要な判断と理由

配送結果は「どのrevisionの何を検査したか」と一緒に読む。fresh recheckは新規取得の照合であり、以前の出力ディレクトリを監視した証拠ではない。利用時には新規検証済み出力を選ぶ。

公開安全性、公開操作の承認、今回のConsumer利用承認はそれぞれ必要な根拠が異なる。receiptは観測記録であって権限の発行者ではない。S1はB1の過去公開承認をunverifiedとして残し、限定された読取り承認と区別している。外側配送の承認から内側資料の公開承認を逆算してはいけない。

## 例外・適用しない条件

size/hash一致は出典の真実性、記事の意味、アプリ動作、build、Readiness、IssueCompletionを証明しない。固定commitの存在からtreeや製品の正しさを推定しない。信頼済みCLIや実行環境、独立した承認経路が前提であり、単なるSHA共有がその真正性を証明するわけではない。

## 失敗・不採用案

「配送PASSなら製品AC合格」「公開済みなら利用可能」「receiptがあれば再取得不要」は不採用。S1の境界説明を越え、異なる判断責任を一つに畳んでしまうためである。旧headでは配送検証を通った後に独立Reviewが準備処理の不具合を指摘した（KD-002）。

## 再利用手順・検証

1. 対象revision、取得範囲、検査者、検査方法、自己検証か独立観測かを記す。
2. 現在のConsumer・scope・purpose・期限の承認を別に確認する。
3. 許可されたCLIで全実体を新規取得し、size/hash/type/schema/参照閉包を確認する。
4. 配送結果と内容評価を別欄に記録する。失敗は新規利用を止めるがKnowledge自体を開発gateにしない。

ここでの手順は再利用時の確認指針であり、この記事が実行許可を与えるものではない。

## 陳腐化・更新履歴

2026-10-11: 最初の実Knowledge整理としてdraft作成。Manager・独立確認前のactive認定はしない。契約版、認可経路、CLIの再検査仕様が変わったとき、反例が出たときに再評価する。後継記事はまだない。後続Consumerの実利用・周期実行は未検証。

## 理解を深めるための問い

- 同じbytesが届いても、内容が誤っている場合は誰が何を検査するか。
- 公開承認と今回の読取り承認が異なる状態のとき、何を主張できるか。
- fresh recheck後に古い出力を読んだら、どの保証を失うか。
