# Artifact Delivery 1.3

現行の4記録はすべて schema_version=1.3 を使う。契約が異なる Handoff 2.0 / Knowledge 1.0 は変えない。
固定 Git bytes の digest・サイズ・参照、承認元・期限・用途、公開範囲を照合する。
配送成功は業務完了・公開許可・マージ許可を意味しない。

`consume_delivery.py` は未承認、不正 JSON、版不一致、欠落・改変・過剰な参照を拒否する。
単一ファイル16 MiB、合計64 MiB、最大256 artifacts。全構造参照を slot_bindings で束ね、
Knowledge input/output の対応と候補の固定 source tree も検査する。
`prepare_crossref_bundle.py --delivery-version 1.3` は現行記録の準備用で、実際の承認を生成しない。
通常の学習記録にはこの配送記録を要求しない。

[旧版と当時の結果](https://github.com/syuhei0519/ai-development-system/blob/e1d2b4dcbe47483e1193206386f8d21810cc3fd7/contracts/artifact-delivery.md) は履歴から参照する。旧版検証の現行サポートは終了した。
