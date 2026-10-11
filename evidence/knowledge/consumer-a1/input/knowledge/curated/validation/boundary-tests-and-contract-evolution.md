---
id: "K-VALIDATION-002"
title: "境界の正常系を試し、未知の型は契約で拡張する"
domain: "validation"
status: "draft"
updated: "2026-10-11"
review_after: "修正headの独立Test/Review確定、契約版更新、反例発見、または2026-11-11"
tags: ["境界テスト", "URL", "型", "外側binding"]
raw_sources: ["../../raw/validation/artifact-delivery-lessons.md"]
supersedes: []
superseded_by: []
publication: "public_safe"
---

# 境界の正常系を試し、未知の型は契約で拡張する

## 要点

回帰テストと独立Testが合格しても、未検査の正常入力で失敗することがある。異常入力を拒否するだけでなく、意味は同じで配置や名前が異なる正常入力を試す。未知のデータ型に出会ったときは既知の汎用型へ読み替えず、元bytesを保ったまま明示的な版付き契約を設計する。

## 適用条件・範囲

URL・型・依存関係を使って配送manifestを準備し、Consumerが検証する系に適用する。例はDelivery 1.2候補の準備処理とKnowledge候補profileである。これをすべてのURL形式に広げる一般パーサ仕様とはしない。

## 根拠と出典

[rawのKD-002/KD-003](../../raw/validation/artifact-delivery-lessons.md)に固定Git URLと全SHA-256をまとめた。S2/S3は旧headの独立Review報告とreproducer、S4/S5はImplementationの停止・拡張の自己報告、S6は修正自己報告である。各資料はraw/evidenceに元bytesのまま保存している。

S1は既存173テスト・独立245ケースのPASSを報告する。一方S2は同じ旧headで次の結果を報告する。

| 固定blob URLの配置 | 準備処理の報告結果 | 明示blob manifestによるConsumer対照 |
| --- | --- | --- |
| 通常repo、docs/note.txt | 受理 | PASS |
| 通常repo、docs/tree/note.txt | 誤って拒否 | PASS |
| repo名tree、docs/note.txt | 誤って拒否 | PASS |

これはURL全体の`/tree/`部分文字列を種別と誤認した正常系の失敗であり、不正入力の受理やコード実行が観測されたわけではない。reproducerは今回静的に読んだだけで、再実行していない。

## 重要な判断と理由

構造に意味がある値は、意味を持つ位置で分類する。今回の修正方向はowner/repository直後のrouteを読むことと、既存の完全一致・固定commit・安全path検査を維持することである。準備処理とConsumer双方を検査する。Consumerだけ正しくても、準備が正常入力を作れなければ利用経路は失敗する。

KD-003のS4では未知knowledge_candidates型が既存保護により停止した。S5では外側の厳密profileとproducer・candidate・sourceのbinding、treeの全snapshot検査を追加したと報告する。元文書に新fieldを足す代わりに、外側の版付き契約が元の文字列・revision・実体を結び付ける。これは実装の自己報告に基づく設計上の教訓であり、知識内容の真実性まで自動検証したという意味ではない。

## 例外・適用しない条件

全システムが同じ外側bindingを必要とするわけではない。適用には保全すべき元bytesと明示的な互換性境界があることが前提。新型profileを承認なく選んだり、通常の文章の意味まで機械検証できると扱ったりしない。tree sourceは追加設計課題として記録されているが、S4で実測された直接の停止原因は未知型である。入力の広い表現を二つの独立した実測失敗に膨らませない。

## 失敗・不採用案

- URL全体の部分文字列による種別推定：正常repo名やpathを誤判定するため不採用。
- 未知Knowledge型をjson/textへ降格：型の意味と参照検査を失うため不採用。
- 既存原文のlocator・status・attemptを書き換えて通す：元根拠と履歴を破壊するため不採用。
- treeを来歴リンクだけで済ませる：今回の要求では完全snapshotが必要なため不採用。ただし他用途すべてに完全tree取得を要求する一般則ではない。
- 旧headのTest合格を修正headへ転用：検査対象が変わるため不採用。

## 再利用手順・検証

正常対照、repo名の衝突、path名の衝突、実treeを区別し、準備→正式Consumerまで期待する型を照合する。拒否すべきURLも別に確かめる。未知型の場合は停止原因を保存し、必要なprofile・版・外側参照・実体閉包・承認範囲を先に定義する。内容の採用と機械的な配送を別判断にする。

## 陳腐化・更新履歴

2026-10-11: 最初の実Knowledge整理としてdraft作成。旧head `4b4e9c249451881f1e5eef82efb3a3b111cacbdb` のReviewはfailedのまま保存。修正head `520ef1e7a59662fe3e58d49d5510350ee08c3160` はS6で自己検証PASSと報告されるが、今回の根拠群では新たな独立合格を確認していない。Manager入力時点は独立Test/Review中・未merge。修正headの独立結果が確定したら固定出典を追記して再評価し、旧履歴は消さない。反例、契約更新でも再評価する。後継なし。active認定、後続Consumer実利用、周期実行はいずれも未検証。

## 理解を深めるための問い

- 既存テストの件数が多くても見落とす正常入力は、どの軸で探せるか。
- 準備処理とConsumerのどちらが失敗したかを分離する対照は何か。
- 型を汎用JSONへ下げると、どの保証が消えるか。
- 元bytesを守ることと、外側bindingが正しいことをそれぞれどう証明するか。
