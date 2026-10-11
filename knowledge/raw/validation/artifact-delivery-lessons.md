# Raw Findings: 配送契約の初回実知見

- domain: validation / ai-development
- observed_at: 2026-10-11
- publication: public_safe（未公開候補。公開承認の代用ではない）
- 元の公開派生版を固定Gitから取得し、Delivery 1.0の未変更Consumer CLIで62件・720970 bytesを検証した後に読んだ。以下の6資料はその部分集合で、再シリアライズせず保存した。
- 本Knowledgeが直接観測したのは配送検査成功・出典digest一致・報告本文である。報告中の過去テスト実行を今回再現したわけではない。reproducerは読取りだけで実行していない。

## 観測事実と報告の区分

| Finding | 固定資料に書かれた内容 | 証拠の強さと限界 |
| --- | --- | --- |
| KD-001 | S1の独立Test報告は旧headに対する正式CLI・fresh recheckで17 objects / 89071 bytesの一致を報告。 | 独立Testによる過去観測の報告。Knowledge自身による実B1の再消費ではない。内側の非公開認可・原本は検査対象外。 |
| KD-002 | S2の独立Reviewは正常blob URLのrepo名treeまたはpath内treeで準備処理が失敗するR-1を報告。S3には正常対照と2つの境界ケース、明示blob manifestのConsumer対照がある。 | 旧headのReviewはfailed。reproducerの静的読取りは報告内容と整合するが、今回実行していない。 |
| KD-003 | S4のImplementation attempt 1は未知knowledge_candidates型でblocked。tree sourceの扱いも追加設計課題となった。S5のattempt 2は外側profile/bindingsと完全tree snapshotによる自己検証を報告。 | Producerの実装・自己検証報告。未知型をgeneric JSONに下げることと、元文書を書き換えることを採用していない。tree source自体が独立した実測停止原因だったとは断定しない。 |

## 時系列と未確認点

S4 blocked → S5 自己検証completed → S1 独立Test completed → S2 独立Review failed → S6 修正自己検証completed、の順序を保持する。
S1/S2の対象は `4b4e9c249451881f1e5eef82efb3a3b111cacbdb`。S6の修正headは `520ef1e7a59662fe3e58d49d5510350ee08c3160`。
S6にはroute位置からblob/treeを判定する修正と自己検証PASSがある。旧Review failedは消えない。修正headの最新独立合格はこの資料群から確認していない。Manager起動入力では独立Test/Review中・未mergeとされるが、ライブ状態の追加確認は本作業の対象外。

## Curated 判断（2026-10-11）

| Finding | 判断 | 理由 | 記事 |
| --- | --- | --- | --- |
| KD-001 | adopted | 配送完全性の具体的検証と、公開・利用・製品判定の境界が明示され再利用できる。 | [配送の成功をどう読むか](../../curated/validation/delivery-evidence-boundaries.md) |
| KD-002 | adopted | 同一旧headでTest合格とReview失敗が共存する具体例。準備処理とConsumerを分けた境界検査が有用。 | [境界と契約を検証する](../../curated/validation/boundary-tests-and-contract-evolution.md) |
| KD-003 | adopted | 不明型を止め、外側に厳密な契約を追加して履歴・元bytesを保全する判断を採用。tree停止の断定は採用しない。 | [境界と契約を検証する](../../curated/validation/boundary-tests-and-contract-evolution.md) |

KD-001とKD-002は同じ配送系を扱うが、前者は保証範囲、後者は検証網羅性を扱う。KD-003は型拡張の判断として統合する。TestとReviewの結果は検査範囲が異なり、矛盾を都合よく解消しない。採用はdraft記事化への採用でありactive認定ではない。入力3件の判断保留・不採用は0件だが、広すぎる解釈と不採用案は本文に残す。

## 固定出典

- S1: [test-report.json](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/input/input/test-report.json)
  - SHA-256: `af3a802497eb2007495e47be9088bbc5b1275382b892ecdd41b486fd58fd8613`
  - [同一bytesのローカル保存](evidence/test-report.json)
- S2: [review-report.json](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/input/review-report.json)
  - SHA-256: `ce2793c1454151c9c8c203f4c608048e41a89f3f15b33becb0f8ae61945c9b85`
  - [同一bytesのローカル保存](evidence/review-report.json)
- S3: [preparation_probe.py](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/input/preparation_probe.py)
  - SHA-256: `6c6fa0aa166ad1a112255ef7b731ec6b1564594f533794901fac7cb2d0fa177d`
  - [同一bytesのローカル保存](evidence/preparation_probe.py)
- S4: [implementation-blocked.json](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/input/input/input/prior/implementation-report.public.json)
  - SHA-256: `29d2ef67748681c07dd456e5a0618be91ede5a9f81feb331ff826ee63f258e03`
  - [同一bytesのローカル保存](evidence/implementation-blocked.json)
- S5: [implementation-completed.json](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/input/input/input/implementation-report.public.json)
  - SHA-256: `47e4461fc6006f65369304b4448715ebdd2bb76cb800156376f8fd5b93963e79`
  - [同一bytesのローカル保存](evidence/implementation-completed.json)
- S6: [implementation-repair.json](https://github.com/syuhei0519/ai-development-system/blob/72b729aabce1c6dd0877102e9af0194ea6055cba/evidence/crossref/implementation-a3/implementation-report.json)
  - SHA-256: `f9b4a9c13a145adad78a641991f454606501f755450ada6a5695dd1c2937f4ea`
  - [同一bytesのローカル保存](evidence/implementation-repair.json)
