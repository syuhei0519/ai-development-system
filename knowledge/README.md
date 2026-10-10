# Knowledge index

人間向け Markdown を正本とする。AI 用メタデータは検索・出典追跡の補助であり本文を置き換えない。知識の収集・選別・抽象化・管理は独立 Knowledge Agent が担当する。

| 技術領域 | Raw Findings（観測・出典） | Curated Knowledge（評価・一般化） |
| --- | --- | --- |
| orchestration | [raw index](raw/orchestration/README.md) | [curated index](curated/orchestration/README.md) |
| validation | [raw index](raw/validation/README.md) | [curated index](curated/validation/README.md) |

## ライフサイクル

1. 開発工程が任意の知識候補と根拠を渡す。Knowledge 専用入力には複数 Issue または Issue を持たない Raw Findings を出典と固定 revision 付きで同梱し、AC 原文は要求しない。Manager は非同期配送し、開発の終了条件にしない。
2. Knowledge Agent が公開安全性を確認して raw に観測事実と出典を保存する。非公開の原根拠は非公開の認可済み領域に残し、public repo には安全な情報のみを記す。
3. Knowledge Agent が重複・矛盾・汎用性を評価し、accepted / deferred / rejected と理由・日付を raw の判断欄に残す。採用する場合は [記事テンプレート](../templates/knowledge-article.md) で curated 記事を作る。
4. curated には適用条件・例外・重要判断・失敗・不採用案・出典を記す。観測からの推論はその旨を明示する。
5. 技術領域の索引とこの索引を更新する。新しい領域は raw と curated の双方に作る。
6. バージョン変更、反例、出典の失効、review_after 到来で再評価する。draft → active → deprecated/superseded を記録し、後継リンクと変更理由を残す。Git 履歴と raw の出典を保全する。

記事の追加が常に必要とは限らない。不採用の判断も残す。Issue/PR/repo の分割方法は固定しない。この初期構成に実運用由来の知識は含めない。

## 配送契約と実行範囲

[専用入力](../templates/knowledge-input.md) と [契約説明](../contracts/README.md) を使用する。根拠・出典不足は MISSING_INPUT とし、Issue AC がないだけで blocked にしない。後続は knowledge-context と記事実体の固定 revision・適用条件・例外・出典・状態を照合し、採否を記録する。知識で AC 原文や実測を置き換えない。

非同期収集・定期同期の実行基盤は Phase 1-3 の対象。このフェーズでは契約・手動配送可能な仕様・架空サンプル・検証のみを提供し、常駐処理やスケジューラーは実装・起動しない。
