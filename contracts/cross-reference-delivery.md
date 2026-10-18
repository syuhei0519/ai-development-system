# Delivery 1.3 の参照

Handoff / Knowledge の各構造参照は、所有JSON・slot・元locator/revision・対象を一意に結ぶ。
URLを追跡して任意の内容を採用せず、列挙された固定 Git blob / commit / tree と照合する。
Git commit object は raw SHA-256 と Git OID を区別する。欠落、重複、誤型、余分な slot を拒否する。
候補の source snapshot と全tree bytes を保持し、承認を候補自身から導かない。

[旧版と当時の結果](https://github.com/syuhei0519/ai-development-system/blob/e1d2b4dcbe47483e1193206386f8d21810cc3fd7/contracts/cross-reference-delivery.md) は履歴から参照する。旧版検証の現行サポートは終了した。
