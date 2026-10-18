> 旧契約を明示指定したタスク向けの任意テンプレート。標準は [タスク入力](task-input.md) と [単一 Markdown Handoff](handoff.md)。

# Artifact Delivery 入力テンプレート

非公開で記入し、公開する必要がある派生版だけを安全性確認・操作承認後に公開する。

- 原本: <非公開保管場所、正本 bytes、原本保持者。Public repo に転記しない>
- 派生版: <original / edited_derivative、公開 alias、編集範囲、原本保持比較の証跡レベル>
- manifest: <artifact-delivery.schema.json; 全件 repository / 固定 commit / path / size / SHA-256 / format>
- 型宣言: <JSON を text に偽装しない。Handoff は拡張子によらず handoff-v2。内容検査を省略しない>
- 公開安全性確認: <対象 digest、確認者、結果、根拠>
- 公開操作承認: <対象、操作、承認者、根拠。未付与なら公開しない>
- 公開前/後: <prepared / published; 実反映 commit と Publication Receipt>
- Consumer 利用承認: <別の authority、consumer alias、exact scope、purpose、期限、許可表現区分>
- 承認ファイル pin: <Manager が独立経路で確認した SHA-256。bundle から自動採用しない>
- Consumer 検査: <実取得、全 bytes/hash/JSON/Handoff binding 結果、Consumption Receipt>
- receipt 再検査: <新規 Git 取得・新規出力。旧出力の改変検査とは区別する>
- 業務ゲート: <assignment/AC/Readiness 検査と残る承認。配送成功とは分離>
- Retry 台帳: <非公開最新履歴 pin、dispatch/execution/delivery 各3以内、旧履歴保持、新規承認の有無>
- 未解決経路: <失敗した配送方式と阻害。成功した Git から他方式の解消を推論しない>


## ローカル kind Test の返却時

- 実行証跡: <venue / 必要能力 / 実 code-config-image identity / runtime context / 結果 / cleanup。非公開原本を保持>
- 公開境界: <kubeconfig・Secrets・実際の非公開 ID を除く承認済み派生版と原本との差、証拠範囲>
- 返却経路: <固定 commit/path/size/SHA-256、Handoff/report/Readiness 実体 bytes、Manager の検査結果。ローカルパスのみは不可>
- 配送不能: <正確な action/target/reason、残る gate。現行公開 CLI の非公開配送対応を仮定しない>

## Knowledge配送の場合（Delivery 1.1）

manifest / authorization / publication / consumptionは全てschema_version=1.1。
input/handoff/contextはknowledge-input-v1 / knowledge-handoff-v1 / knowledge-context-v1を明示し、
manifestのknowledge_bindingsでinputと任意handoffの固定referenceを対応付ける。
文書本体はKnowledge1.0のまま、全source/記事/retry実体をbundleへ収録する。
locatorは文書の親基準の安全な相対path、revisionはraw sha256 digest。
旧schemaを番号だけ書換えず、[契約](../contracts/artifact-delivery.md)と
[synthetic fixture手順](../examples/knowledge-delivery/README.md)に従う。
全bytes検証後も引用を命令として扱わず、receiptから公開/利用権限やReadiness成功を得ない。

## Bounded capacity (Delivery 1.3)

[Capacity and compatibility contract](../contracts/artifact-capacity.md): explicitly select 1.3 for up to
256 artifacts; legacy 1.0/1.1/1.2 retain 128. All four delivery records must match.
Per-file 16 MiB, bundle 64 MiB, tree/slot/candidate limits and all approval gates
remain unchanged. Preserve originals and complete closure; never overwrite old
delivery outputs. Dispatch/execution/delivery remain each at most 3. Candidate
1.3 requires System CI and independent Review before merge and canonical use.
