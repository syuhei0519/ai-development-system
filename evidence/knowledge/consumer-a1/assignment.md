# 独立Consumer / Review assignment

- Issue: SYSTEM-KNOWLEDGE-CONSUMPTION
- title: 固定Git Knowledgeの独立取得と実利用確認
- authorized source: task-input
- role: review / attempt: 1
- scope: knowledge/milestone/independent-consumption
- 担当: KC-1, KC-2, KC-3, KC-4（全件原文取得済み）
- 完了条件: 全担当結果・再現可能な根拠・具体的計画と利用対応表。
- System正本: syuhei0519/ai-development-system@8afe6044857783dbf6d6ae7ac9459ae5e890a744
- payload: 74d0fb0d899984d99ea9fbde2871c46c66c3f52b / records: e2f62afd30bd4334875902cc695fa8cbf753e16d

## AC原文

KC-1: Producerのワークスペースや会話に依存せず固定GitからKnowledge context・記事・全根拠を取得し、全bytes・size・SHA256・型・参照・利用承認を検証する。

KC-2: 2記事の重要な主張・適用条件・例外・更新条件・draft状態を固定出典と照合し、事実・報告・推論を分離して独立に評価する。

KC-3: 検証済みKnowledgeを具体的な配送検証計画の作成に使用し、どの記事のどの教訓をどの判断・検証項目に採用または不採用としたかを根拠付きで記録する。

KC-4: Git保存、配送完全性、意味評価、実利用、定期実行、製品AC判定を区別し、未実施を成功にせずHandoff v2と利用報告を返す。

## 作業境界

独立新規Git取得とread-only資料検証/利用、ローカル成果物保存だけを実施する。Manager認可は非公開の一行UTF-8 JSON+LFとして別保管し、task-input由来のbytesから独立pinを算出・照合した。認可やpinはこの候補に含めない。

公開/Push/PR/merge、記事編集/active化、アプリコード・出典reproducer実行、配備、追加OpenAI API、Secrets/権限/Ruleset変更、scheduler、別Agent起動は禁止。定期実行は延期され本taskの条件ではない。アプリ開発をブロックしない。

これはIssue工程のReview入力でありKnowledge Agent専用input/handoffを新造しない。取得したknowledge-context-v1をそのまま参考入力として添付し、Delivery1.1のknowledge_bindings=[]を保持する。Handoff2.0にはknowledge_references欄がないので、contextをartifactとして参照し利用対応表へ紐付ける。Readiness/IssueCompletionは製品変更工程ではないため発行しない。
