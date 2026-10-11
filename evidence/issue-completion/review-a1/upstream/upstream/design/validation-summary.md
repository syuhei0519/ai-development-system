# 検証要約

公開安全候補 / edited derivative / 未公開。内部ログ、ローカル絶対path、実行タスクID、認証情報を含まない要約。

## 既存基準

出典目録の固定System commitで既存の `python -m unittest discover -s tests -v` は107件成功した。これは既存契約の回帰結果であり、新集約契約の実装・製品AC・配備・GitHub merge可否の検証ではない。

## 配送候補

Handoff v2のschema/参照整合性を既存validatorで検査し、合格を確認した。公開候補Handoffの4つのartifact参照は同じディレクトリのreport.md、requirements.md、sources.md、validation-summary.mdだけを指す。各revisionは対象ファイルの全bytesのsha256。upstreamは空、最終Issue判定は含めない。

さらに既存ArtifactDeliveryのverify_handoffsをローカルの全候補bytesへ適用し、合格を確認した。Gitの公開先・commitには検査用のsynthetic値を与え、同じディレクトリ構造を別prefixへ移した場合を含む3配置で解決を確認した。必須ファイル欠落と1byte改変の負例は拒否された。この検査はGit fetch・公開・Publication Receipt・承認検査を実行したことを意味しない。

全文をProducerが点検し、実task/thread ID、非公開原本/hash、内部絶対path/log、私的リンク、認証値を候補に含めない。公開repoの固定source URLとhash、公開alias、技術要件、提案schema/CLI名は含む。publication=public_safeは候補の内容分類であり、独立公開安全性レビュー・公開操作承認・Consumer利用承認を発生させない。

## 限界と後続ゲート

新しい集約CLIは未実装。正常系はsyntheticテスト案であり、製品の測定成功を示さない。公開操作は未実施。公開後の実repo/commit/path/size/hashを持つmanifest、Publication Receipt、Managerの独立承認pin、Consumerによる固定Gitからの全bytes取得検査は後続で必要。implementation目的の利用scopeはcontract-reviewと区別する。

元bytesを正規化・再serializeして配送しない。公開前に候補が変われば、該当hashとHandoff bindingを更新し、全体を再点検する。今回の検証結果の正式な採否はManagerが別経路の検証記録と照合する。
