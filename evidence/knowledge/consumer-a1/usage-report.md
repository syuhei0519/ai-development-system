# 独立Consumer利用報告

今回のassignmentは完了。13 payload / 63991 bytes、固定records 2件、出典6実体を独立取得・照合し、draft2記事を意味レビューしたうえで、次回配送用の12検証項目と5件の不採用/保留判断を作成した。これは計画への実利用であり、提案テストの実行成功ではない。

## 状態の分離

| 対象 | 状態 | 根拠と限界 |
| --- | --- | --- |
| 入力Knowledgeの固定Git保存 | verified | payloadとrecordsを指定commitから取得。浮動mainやProducer workspaceを使わない。今回の成果物をGitへ保存/公開したという意味ではない。 |
| 配送完全性 | verified | 未変更正本Delivery1.1 Consumer CLIを2回実行、いずれもexit0。2回目はfresh Gitのreceipt再検査。context型、13件のsize/hash/UTF-8/JSON/schema/path/参照閉包、knowledge_bindings=[]を検査。 |
| 6出典の固定公開原資料との同一性 | verified | raw/evidence6コピーと元の固定Git source_alias先を全bytes照合。非公開原本は未検証。 |
| 意味評価 | verified（限定用途） | 主張・条件・例外・draft・時系列・更新条件・問いを読み、報告と事実と推論を分離。semantic-review.mdに根拠別判定。 |
| 検証済みKnowledgeの実利用 | verified（計画作成） | delivery-review-test-plan.mdのT01–T12へ具体的に採用。usage-map.jsonに全項目の段落/固定revision/採否/追加推論を対応付け。N01–N05で過大解釈を不採用/保留。 |
| 計画したテストの実行 | not_requested / not_executed | 今回は資料利用のみ認可。アプリ・過去テスト・reproducerは実行しない。 |
| 周期実行 | not_requested（延期） | 本task条件外。scheduler/自動context生成/常駐処理を実装・起動しない。 |
| 製品AC・Readiness・新PR7 head合格 | pending / unverified | 対象製品の実測・最新独立Test/Reviewはない。final_assessmentはManagerのみ。 |
| draft→active | not_requested | 記事/context/indexの元bytesを保持し、lifecycleを更新しない。 |
| 今回の新規成果物の公開/Push/PR/merge | not_requested / not_performed | ローカル候補のみ。安全候補の分類は公開許可を発行しない。 |

## KC対応

| AC | Review工程の判断 | 成果物 |
| --- | --- | --- |
| KC-1 | covered | delivery-verification.json、input全13件、非公開Consumer記録/認可/独立pin。利用開始はCLI検査後。 |
| KC-2 | covered | semantic-review.md、固定context/article/source、出典同一性記録。 |
| KC-3 | covered | delivery-review-test-plan.md、usage-map.json。各項目が判断・期待結果を持ち、要約だけに留めない。 |
| KC-4 | covered | この報告、handoff.json、reproduction.md。未実施と状態の分離。 |

coveredは今回担当したReview工程完了を示す。Issue全体の最終判定、製品の合格、過去のR-1修正合格ではない。

## 保存、承認、試行

Managerのtask-inputで明示された認可をUTF-8一行JSON+LFで非公開保存し、配送bundleと独立した入力bytesから算出したpinと照合した。認可対象consumer/scope/purpose/期限/表現区分を未変更CLIで検査した。認可の本人性は入力経路への信頼であって暗号学的署名ではない。

実行attempt=1。今回のConsumer配送は初回1回+fresh再検査1回で計2回、各上限3以内。過去工程のattempt/terminalは変更せず、scope変更による再開もしていない。基盤dispatch履歴を本Consumerが独立観測したとは主張しない。CLIや取得失敗の無限retryはない。

出力原本は非公開領域に保持。公開候補にはruntimeID、private original hash、認可、private pin、Consumption Receipt、内部生ログを含めない。公開済み入力13件は変換・再シリアライズせずそのまま同梱する。これらの過去公開安全性審査はProducer/Managerの報告と区別し、今回候補も内容を確認したが、新しい公開操作はしていない。

## 残件

次回のテスト実行には対象head/版/fixture/認可と担当をManagerが確定する必要がある。最新PR/merge/独立Test/Review状態、非公開原本、製品挙動は未確認。これらは今回の限定計画利用を阻害せず、アプリ開発もブロックしない。将来のKnowledge再評価では新しい固定証拠を別追加し、元のfailed/自己報告/draftを消さない。
