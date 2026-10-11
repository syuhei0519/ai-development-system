# Contracts: Issue v2.0 / Knowledge v1.0 / Readiness v1.0 / Issue Completion v1.0

JSON Schema Draft 2020-12 を使用する。追加フィールド、空文字・空白のみの文字列、型不正を拒否する。schema の `$id` にある example.invalid は識別用プレースホルダーであり、ネットワーク取得は不要。

## Issue task handoff v2.0

[handoff.schema.json](handoff.schema.json) は manager / research-design / implementation / test / review 用。Knowledge は後述の専用契約を使う。

- `issue`: Issue 原文の出典と必須 AC の原文。Manager が原文の完全性を確認する。
- `assignment.scope`, `assignment.ac_ids`, `assignment.completion_criteria`: Manager が起動前に確定する担当範囲、担当 AC、工程の完了条件。エージェントが完了しやすいよう勝手に縮小しない。担当範囲を変更する場合は Manager が判断と新しい初回入力を記録する。
- `task_id`, `attempt`, `upstream`: 独立実行、同一論理工程の試行回数（初回込み1〜3）、依存と retry_of。再試行は同一 role・Issue・論理工程の直前試行 +1。実識別子は非公開領域だけで扱う。
- `system_status`: 実行基盤の終了状態。`completed` は業務成功を意味しない。
- `status`: **今回の assignment の工程完了**。completed は全担当 AC の工程上の責務が完了し、根拠と成果物がある状態。Issue 全体の AC 合格ではない。blocked には理由と必要な処置、failed には失敗理由が必要。
- `ac_mapping.disposition`: `covered` は担当 AC に対する役割の責務の完了、`unverified` は未検証、`not_met` は担当工程の不合格、`not_assigned` は担当外。担当外を covered としない。担当 AC が未検証・不合格・未記載なら completed にできない。担当外 AC は省略または正直な状態で記録し、未検証や担当外が残っていても今回の工程は completed にできる。
- `ac_mapping.scope`: 実際に確認した範囲と限界。Research の設計済み、Implementation の実装済み、Test の担当検証済みはいずれも製品全体の最終合格ではない。
- `final_assessment`: **Manager のみ**が記録できる Issue 全体の最終 AC 判定。全 Issue AC を重複なく列挙し、各 `met / not_met / unverified` と根拠を記録する。v2.0のAC判定内では全件 met なら achieved、1件でも not_met なら not_achieved、残りは unverified。ただしReadiness運用で全AC metでも統合未完了の場合は、最終判定自体を保留しfinal_assessmentを省略する。未検証を met にしない。Manager の判定作業が completed でも、最終判定が unverified / not_achieved なら Issue は完了していない。
- `artifacts` / `evidence`: 成果物の locator・固定 revision、主張・根拠・観測内容。テストはコマンド、対象 revision、結果、環境の制約を観測内容に含める。別タスクにローカルパスだけを渡さず実体を取得・配送する。
- `knowledge_candidates`: 任意の知識候補。空でも開発を進められる。Knowledge 起動時は根拠を取得して専用入力に変換する。Issue handoff をそのまま Knowledge 入力とはしない。
- `publication`: synthetic_sample / public_safe / private_only。自己申告は公開許可の代用にならない。

AC 原文が欠落していれば `MISSING_ACCEPTANCE_CRITERIA` で blocked。既知の原文と既知の担当 AC ID は保持し、全原文不明なら `acceptance_criteria: []` とする。専門役割は外部取得・推測しない。Manager が認可済み情報源から補完する。欠落 blocked の場合だけ、原文未着の担当 ID が Issue 内に未登録でも報告を受け付ける。schema は原文の完全性を証明しない。

`python scripts/validate_handoff.py FILE...` は schema とローカル参照整合性（担当 AC、重複、全担当の covered、最終判定の全 Issue AC 対応、retry）を検査する。Manager が assignment と元の起動入力の一致、同一論理工程の追跡を別途照合する。

## Knowledge 専用契約 v1.0

- [knowledge-input.schema.json](knowledge-input.schema.json): `document_type=knowledge_input`。assignment は収集・比較・抽象化の範囲と完了条件。`raw_findings` は1件以上で、各件に観測、技術領域、出典 locator と固定 revision が必要。`issue_refs` は0件以上でよく、複数 Issue を横断できる。単一 Issue も AC 原文も要求しない。
- [knowledge-handoff.schema.json](knowledge-handoff.schema.json): `document_type=knowledge_handoff`。取得した raw_findings のスナップショット、成果物、raw_finding_ids まで遡れる根拠、採用/保留/不採用（adopted/deferred/rejected）判断と理由を返す。completed には全入力 finding の根拠付き判断が必要。採用には knowledge 種別の記事成果物が必要。保留・不採用でも判断作業は完了できる。
- 入力・出力の raw_findings の実体、ID、出典、revision と assignment は起動入力に照合する。都合の悪い入力の削除や改変による完了を認めない。CLI の単体ファイル検査はこの配送前後の同一性を証明しない。
- 根拠不足は `MISSING_INPUT` で blocked。AC がないことは阻害理由にしない。空の原根拠で completed を主張したり、出典のない finding を入力したりすると検証が失敗する。
- task_id / attempt / retry_of は独立した Knowledge 工程で追跡し、初回込み最大3試行。失敗・遅延は依存する開発工程を止めない。

`python scripts/validate_knowledge.py FILE...` は document_type に応じた専用 schema と参照整合性を検査する。出典の真実性、公開安全性、一般化の妥当性は Knowledge Agent が別途確認する。採用を自動決定しない。

## 後続エージェントが知識を参照する入力

[knowledge-context.schema.json](knowledge-context.schema.json) の `document_type=knowledge_context` を、取得済み記事実体とともに起動入力へ添付する。各参照に ID、locator、固定 revision、適用条件、例外、出典とその revision、lifecycle、再評価条件を含める。参照が不要なら添付自体を省略できる。ある場合は上記 CLI で検証する。

Manager が参照を取得・配送し、担当エージェントが対象環境への適用可能性を確認する。draft / deprecated / superseded は無条件採用せず、採否と理由を記録する。参照知識は助言であり、Issue の AC 原文や実測根拠を置き換えない。利用可能な知識がないことだけでは開発を止めない。

Knowledge の非同期収集・定期同期を動かす実行基盤、スケジューラー、自動トリガーは **Phase 1-3** の対象。本フェーズは契約と手動配送可能な仕様・サンプル・検証のみであり、これらの基盤を実装・起動しない。

## 移行と互換性

Issue handoff v1.0 → v2.0 は破壊的変更。v1.0 を黙って受け付けず、Manager が元の割り当てに基づいて assignment を明示し、担当外の covered を削除または正しい状態に変更する。バージョン番号だけの書き換えや推測での担当決定は不可。既存公開サンプルはすべて架空の割り当てを明示して移行済み。

Knowledge は Issue 契約の role=knowledge を廃止し、独立した v1.0 の入出力・参照契約へ移行する。必須 AC 原文の要件を引き継がず、実際の raw evidence と固定出典を引き継ぐ。過去の実行成果物は上書きせず元のバージョンで保管する。更新時は schema・CLI・テスト・サンプル・文書を同時に見直す。

すべての形式検査は、根拠の真実性・AC 充足・公開可否・GitHub 反映・CI 成功の証明とは別。[業務ゲート](../workflows/single-issue.md) を省略しない。

## Readiness と Issue Completion

[Readiness v1.0](readiness.md) は3種 readiness と全 AC の実測状態を分離する独立契約。PR 単位の Merge Ready に Issue achieved を要求しない。`readiness.schema.json` と `readiness-context.schema.json` を `validate_readiness.py` で照合し、handoff との配送には `--handoff` も使う。既存 handoff v2.0 の artifacts から固定参照し、既存 final_assessment の全 AC 実測による厳格な Manager 判定を維持する。Knowledge 契約と収集基盤には変更を加えない。


Issue Completionには全AC実測に加えて必要な統合完了が必要。全premerge ACがmetでも未マージならunverified。Readiness/contextのissue_integration_scopeで単一PRと集約待ちを分離し、複数PR・repo/範囲不明は単一PRからachievedにしない。複数PR・repoは独立[Issue Completion契約](issue-completion.md)で全必要集合と固定証跡を検証する。全AC met・統合待ちの中間Handoffではfinal_assessmentを省略し、Readiness artifactで追跡する。

Readinessの配送にはartifact_id、Handoff基準のローカルlocator、実体bytesのsha256 digest revisionを使用する。`validate_readiness.py --handoff`は実体の読み取り・評価対象ファイルとの同一性・digestを照合する。旧DraftのReadinessは追加必須項目を確認して移行する。詳細と限界はReadiness契約を参照。

## Artifact Delivery v1.0

[配送契約](artifact-delivery.md) と外側 manifest / authorization / publication-receipt / consumption-receipt
schema を追加する。Handoff v2.0 と Readiness v1.0 の schema・判定責任は維持する。
Public Git 原本と edited derivative を区別し、配送成功・公開済み状態・公開承認・利用承認は別判定。
Git 配送で手書きの再構成をしない。独立 pin の承認と全 bytes の Consumer 検査が揃うまで利用しない。
再試行分類の変更で旧 attempt を減らさず、各3回の別予算と上限後の承認は配送契約に従う。


## Artifact Delivery v1.1 — Knowledge実体照合

[配送契約](artifact-delivery.md#knowledge-typed-delivery-v11-phase1-3-p-a) の明示的minor版は
Knowledge input/handoff/contextのtyped配送、原入力一致、source/記事/contextの固定bytes検査を追加する。
本体のKnowledge1.0・Handoff2.0・Readiness1.0とDelivery1.0の正常系は維持する。
版別schemaは `*-v1.1.schema.json`、CLIは4種配送recordの版一致を要求する。
公開synthetic fixtureと固定Git再現手順は [examples/knowledge-delivery](../examples/knowledge-delivery/README.md)。
非同期収集・context生成・ack・周期実行・実Agent利用実証は後続P-B/C/Dであり未実装。
