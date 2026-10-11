# 配送サンプルと固定公開根拠

`synthetic.manifest.json` は公開 synthetic 7件、`research-public.manifest.json` は編集済み公開派生版9件の
固定 commit/path/size/SHA-256 を外側契約で列挙する。元の immutable 成果物をコピー・改変しない。
後者の非公開原本・実識別子・対応表・原本 digest はここにない。
Publication Receipt と後日の訂正記録は [records](../../records/artifact-delivery/) にある。

`synthetic.authorization.json` は **synthetic sample**。記載された approved は実運用の承認ではない。
実行者が別途このデモの利用を承認して pin を渡した場合だけ利用する。
`invalid-unapproved.authorization.json` は正しく pin しても Consumer 利用 pending のため必ず拒否。
既存公開 Research 用の実装利用承認はサンプルから生成しない。

```bash
python -m unittest discover -s tests -v
```

ネットワーク不要のテストは一時 Git repo に通常 blob / symlink / submodule を作り、実 Git 読取りを検証する。
公開 Git 取得を再現するには [CLI 手順](../../contracts/artifact-delivery.md#consumer-cli) に
synthetic manifest、対応 Publication Receipt、独立承認した authorization とその pin を指定する。
出力先は repo 外の新規 private directory にする。取得した verify.py 等を実行しない。

異常系は改変/切詰め/size/hash/commit、未存在 commit、未承認/期限/範囲、receipt 改変、取得不能、
重複 JSON key、Handoff binding、注入 path/URL/ref、symlink/submodule、予算上限と履歴改変を扱う。
CI はユニット/一時ローカル Git 検証を行い、外部ネットワークの可用性や承認の真正性を証明しない。

`retry-initial.json` → `retry-dispatch-failed.json` は初回 dispatch 失敗の正常な追記例。
`retry-exhausted.json` → `invalid-retry-reset.json` は過去3回を消す異常例で拒否必須。
いずれも synthetic sample の架空 alias だけを使用する。
