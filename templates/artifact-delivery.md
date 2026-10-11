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
