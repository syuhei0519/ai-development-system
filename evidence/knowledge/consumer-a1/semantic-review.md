# 固定Knowledgeの独立意味レビュー

判定: 2記事を **draftの検証計画用参考として条件付き採用**。この限定用途を阻害する出典との不整合は認めなかった。現在の製品合格・PR #7の新head合格・active化には採用しない。

レビュー対象は `syuhei0519/ai-development-system@74d0fb0d899984d99ea9fbde2871c46c66c3f52b`。未変更正本 `8afe6044857783dbf6d6ae7ac9459ae5e890a744` のDelivery 1.1 CLIによる初回とfresh receipt再検査に成功した後、**2回目の新規出力**から読んだ。Producerのworkspace・会話・非公開原本は参照していない。6つの公開出典コピーについては元の固定Git `72b729aabce1c6dd0877102e9af0194ea6055cba` から別途全bytesを取得し同一性を確認した。

## 固定参照と証拠の区分

- A = K-DELIVERY-001: [配送の保証境界](https://github.com/syuhei0519/ai-development-system/blob/74d0fb0d899984d99ea9fbde2871c46c66c3f52b/knowledge/curated/validation/delivery-evidence-boundaries.md)、SHA256 `efde077ec14efb1991c1393f637be020f036f5e048f888eca75976156aea66f8`。
- B = K-VALIDATION-002: [境界と契約拡張](https://github.com/syuhei0519/ai-development-system/blob/74d0fb0d899984d99ea9fbde2871c46c66c3f52b/knowledge/curated/validation/boundary-tests-and-contract-evolution.md)、SHA256 `b6784558c0a6131fa0e9f68b89f7861bc63a135076cc5004c446223b8f79d1bd`。
- C = [context.candidate.json](input/context.candidate.json)、SHA256 `6e19b98691eb3c5e4c780e65fe2a592e4f20c26181b3ffbc5d6d0c24b6be04b5`。2 referencesのid・digest・適用条件・例外・draft・更新条件を本文と照合。
- R = [raw記事](input/knowledge/raw/validation/artifact-delivery-lessons.md)。S1〜S6の完全なURL・digestはRと[配送検証記録](delivery-verification.json)に保存。
- S1 = test-report.json、S2 = review-report.json、S3 = preparation_probe.py、S4 = implementation-blocked.json、S5 = implementation-completed.json、S6 = implementation-repair.json。いずれも [input/knowledge/raw/validation/evidence](input/knowledge/raw/validation/evidence) の公開派生資料。

**独立観測事実**は今回の固定Git取得、13件63991 bytesとrecordsの照合、6公開出典との同一性、実際に読んだ記載、計画と対応表の作成である。S1〜S6に書かれた過去の実行結果は**固定報告**であり、今回再実行した事実ではない。計画上の一般化と追加ケースは**推論**として分離する。S3は静的読取りのみ。

## 主張ごとの照合

| 対象箇所 | 固定出典の箇所 | 評価と利用条件 |
| --- | --- | --- |
| A L19,27–28: 配送完全性と内容・製品合格の分離、17 objects / 89071 bytes | S1 `/summary`, `/requirements/5`, `/boundaries` | 数量・CLI/fresh recheckはS1の報告と一致。非公開原本との同一性やアプリ実行は認定しないと明示され、出典より強くない。Aが報告を読んだ事実はProducerの記述であり、本Consumerによる過去実行再現ではない。 |
| A L23: Delivery 1.2の実例、Producer外側1.0、Knowledge1.0 | S1 `/summary`, `/boundaries`、R冒頭 | 1.2実例はS1、Producer外側1.0はRの自己報告。今回の外側は**1.1**であり、この記事の1.0を今回へ転記しない。Cの適用条件は歴史的1.0/1.2を要約しており、現行CLI仕様の列挙ではない。 |
| A L32: fresh再検査後は新規出力を利用 | S2 `/residual_risks/3`、固定正本配送契約のConsumer CLI | 一致。receipt再検査自体は旧出力を調べない。今回は別途bytes比較も行ったので、旧・新の一致についてはその追加観測だけを根拠とする。 |
| A L34: 公開安全性・公開承認・Consumer承認の分離 | S1 `/boundaries/2`、S4 `/blocker/authority_boundary` | 内側B1の過去公開承認unverifiedを保持。今回のManager明示承認を内側B1の追認にしない。公開安全性の過去審査はManager/Producerの報告であって、CLIの証明ではない。 |
| A L38,42,46–51: size/hashやreceiptを業務成功・権限へ拡張しない | S1 `/boundaries`, S2 `/gate_states`, `/residual_risks` | 支持される設計上の教訓。手順は助言で実行権限ではない。今回の計画でも内容gateと製品gateを独立させる。 |
| B L29–37: 173/245 PASSと正常URL2ケースの準備失敗、Consumer対照PASS | S1 `/summary`、S2 `/findings/0/reproduction`, `/actual`, `/impact`、S3 `scenarios` と明示manifest oracle | 数値・通常repo/path・repo名tree・path内treeの表が一致。S3の静的構造が対照の意図を支持するが実行結果を新たに証明しない。S2は不正受理/コード実行を観測していないと明示し、記事も同じ限界を守る。 |
| B L41: route位置による分類と安全検査維持 | S2 `/findings/0/fix_conditions`、S6 `/finding/repair` | S2の修正要求・S6の自己報告に一致。原因分析として採用するが、現在のコードに修正が有効であるとの判定には使わない。 |
| B L43,47: 未知型停止、外側profile/binding、treeの位置付け | S4 `/blocker/diagnosis`, `/operational_result`, `/additional_design_question`、S5 `/implementation`, `/supplemental_conditions` | S4直接停止原因は未知knowledge_candidates型。treeは追加設計課題であり独立した実測停止としない。S5の設計/自己検証報告としての記述は適切。本文全体の真実性は機械検査対象外。 |
| B L51–55: 降格・元文書編集・旧head合格転用の不採用 | S4 `/concrete_design`, `/blocker`、S5 `/implementation`, `/history`、S2 `/findings/0/fix_conditions` | 根拠がある。ただし1.2 candidate profileを1.1 knowledge-contextへ持ち込まない。今回context-onlyの外側knowledge_bindings=[]は正当で、input/handoff pairを架空に追加しない。 |
| B L63: 旧Review failed→修正自己検証PASS、未確定状態 | S2 `/status`, `/head`、S6 `/head`, `/independent_review`, `/coverage/8`、R「時系列と未確認点」 | 旧head `4b4e9c249451881f1e5eef82efb3a3b111cacbdb` のfailedを保持。修正head `520ef1e7a59662fe3e58d49d5510350ee08c3160` は自己報告のみ。初回入力時点の独立Test/Review中・未mergeはRに残されたManager報告であり6出典から現在状態を独立確認できない。現時点未mergeともmerge済みとも断定しない。 |

## 適用条件、例外、更新条件、問い

両記事のfront matterとCはid/digest/draft/review_triggerが一致する。Aは固定Gitでの配送保証の境界、BはURL準備経路と型・依存閉包の設計へ限定する。Bの完全tree要件は1.2の当該要求に限定され、一般的な全配送へ拡張しない。現在1.1のcontext-only配送にtree型の受理を期待しない。

C・索引・本文の「未公開」「後続Consumer実利用未検証」は作成時点のスナップショットである。固定recordsと今回取得はGitでの存在を示すが、元記事を編集して状態を更新しない。今回新たに証明するのはこの計画への限定実利用のみ。周期実行、active認定、最新独立Test/Reviewは未検証のまま。

再評価条件は修正headの独立結果確定、契約/認可経路/CLI再検査仕様変更、反例、または2026-11-11。現在状態が必要な主張は新たな固定証跡が揃うまで保留する。

Aの問いに対して、内容誤りは意味ReviewとManagerの別gateで扱い（T09）、承認状態は別欄で追跡し（T07）、fresh後は新出力の利用locatorを記録する（T08）。Bの問いに対して、名前とrouteを独立の軸にする（T01–T03）、準備経路と独立manifestを別対照にする（T04）、未知型で失う保証を検査する（T05）、原bytesと外側参照の照合を別assertionにする（T06）。これは本Consumerの具体化であり、記事が既にこの計画を実行したという意味ではない。

## 残る限界

原private資料、元実行ログ、現在PR/CI/merge状態は取得しない。報告内のテスト結果の真実性を再実測していない。固定6出典は全件読み比べたが、そのproseが挙げる全テストファイルやアプリ依存を再帰実行・再帰配送していない。CLIが保証するtyped context閉包と、本文リンクの意味評価を混同しない。阻害指摘なしは今回の**限定的知識利用**についてであり、旧Reviewの阻害R-1を解消する判断ではない。
