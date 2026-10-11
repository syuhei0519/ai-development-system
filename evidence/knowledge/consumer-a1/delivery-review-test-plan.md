# 次のAgent間配送で使うレビュー・テスト計画

作成結果: 検証済みdraft Knowledgeから12項目を設計した。**本書は計画であり、下記テストはすべて未実行**。今回完了した配送CLI2回と資料読取りの結果はdelivery-verification.json、限定的な採用判断はsemantic-review.mdに分離する。

## 入力、権限、実施順序

次回Managerは対象repo/固定head、選択Delivery版、準備helperの有無、全元資料・manifest/publication、独立Consumer認可pin、担当ACと試行予算を確定する。許可のないfixture作成・テストコード実行をこの計画から開始しない。今回の認可は資料検証と計画作成のみ。

順序は現在認可と版の確認（T07/T11）→全bytesと閉包（T06）→適用版での正常/異常/型境界（T01–T05）→fresh再取得と新出力利用（T08）→意味レビューと履歴（T09/T10）→Managerへの分離報告（T12）。途中で拒否された資料は利用しない。適用外項目は理由を記し、未実行をPASSにしない。

URLの例はsyntheticの形であり実在repoへの投稿指示ではない。`https://github.com/synthetic/source/blob/<固定40hex>/docs/note.txt`、同`docs/tree/note.txt`、repoを`synthetic/tree`にしたURLを用意する。commitは次回の承認済みfixtureの実際の固定値に置換する。準備URL機能がないDelivery1.1ではT01–T04は適用外。

## 検証項目

| ID | 項目 | 状態 |
| --- | --- | --- |
| T01 | 正常blob URLの名前衝突 | 未実行（計画のみ） |
| T02 | routeと実treeを区別 | 未実行（計画のみ） |
| T03 | 安全制約を残す異常URL対照 | 未実行（計画のみ） |
| T04 | 準備処理とConsumerの独立対照 | 未実行（計画のみ） |
| T05 | 未知Knowledge型の降格拒否 | 未実行（計画のみ） |
| T06 | 外側bindingと記事・source閉包 | 未実行（計画のみ） |
| T07 | 公開承認とConsumer承認を独立検査 | 未実行（計画のみ） |
| T08 | fresh receipt再検査後の実利用出力 | 未実行（計画のみ） |
| T09 | 配送gateの後に内容妥当性gate | 未実行（計画のみ） |
| T10 | 歴史・draft・現在headを分離 | 未実行（計画のみ） |
| T11 | 版と元bytesの保全 | 未実行（計画のみ） |
| T12 | 失敗時の利用停止と有限配送 | 未実行（計画のみ） |

## T01 正常blob URLの名前衝突

**適用条件:** 1.2等、固定blob URLを入力とする準備機能が次回対象にある場合。今回の1.1相対path専用配送にはそのまま実行しない。

**手順:** 同じ内容を持つ承認済み固定fixtureを、通常repo/docs/note.txt、通常repo/docs/tree/note.txt、repo名tree/docs/note.txtの3配置で用意する。各URLを準備処理へ渡し、その出力を正式Consumerへ渡す。fixture生成/実行は次回の明示権限下で行う。

**期待結果:** 3件ともblobとして準備受理しConsumerもPASS。routeがblobなのにrepo/path内treeだけでtree扱いしない。元URL・commit・raw bytesを保存する。

**保存する証拠:** 各ケースの固定fixture参照、準備exit/型、manifest digest、Consumer exit/新規出力照合を別々に記録。

**採用根拠:** K-VALIDATION-002「根拠と出典」L29–37 / K-VALIDATION-002「再利用手順・検証」L57–59。固定出典: S1, S2, S3。

**追加推論:** 同じ内容を用いた配置別fixtureとケース単位の結果欄はConsumerが具体化した設計。

## T02 routeと実treeを区別

**適用条件:** 選択済みの契約版が完全tree snapshotを明示的にサポートするときだけ。

**手順:** T01のblob対照と、owner/repo直後のrouteがtreeの固定tree対照を比較する。treeにnested/emptyディレクトリを含め、完全inventoryと全通常blobを照合する。1.1ではtreeを擬似blobに変換せず未対応として扱う。

**期待結果:** 対応版では実treeだけtree型、完全snapshotでPASS。欠落・余剰・型不正は拒否。tree未対応版の拒否を製品不具合と誤分類しない。

**保存する証拠:** 選択版、tree/blobの型、期待inventoryと実inventory、適用外理由。

**採用根拠:** K-VALIDATION-002「例外・適用しない条件」L45–47 / K-VALIDATION-002「失敗・不採用案」L51–55。固定出典: S4, S5。

**追加推論:** nested/emptyと欠落・余剰の具体例はS5報告を参考にした追加設計。全配送でtree取得を必須にはしない。

## T03 安全制約を残す異常URL対照

**適用条件:** URL準備機能を持つ選択契約版。許可されたlocal synthetic fixtureのみ。

**手順:** 正常対照に続き、浮動branch、短縮commit、query/fragment、別host、path traversal、曖昧routeを1要因ずつ加える。準備処理と独立manifestのConsumer経路を区別する。

**期待結果:** 規約外URLをfail-closedで拒否し、新しい検証済みbundleやreceiptを出さない。T01の正常受理を維持する。

**保存する証拠:** 変更した1要因、適用契約、期待拒否理由、exitと新規出力不存在。

**採用根拠:** K-VALIDATION-002「重要な判断と理由」L39–41 / K-VALIDATION-002「再利用手順・検証」L57–59。固定出典: S2, S6。

**追加推論:** 列挙した異常URL軸は本Consumerの追加テスト設計。記事に同じ全ケースの実測があるとは主張しない。

## T04 準備処理とConsumerの独立対照

**適用条件:** 準備helperとConsumerの両方が対象にある場合。

**手順:** T01各入力について、準備出力→Consumerという経路Pと、原bytes/固定参照から別担当が明示型manifestを組む経路Cを用意する。準備失敗時も元資料を書き換えず、Cの成功でPの失敗を上書きしない。

**期待結果:** P/C両経路に個別結果。P拒否かつC受理は準備機能の正常入力不具合としてfailed。Cのみ成功をend-to-end成功としない。

**保存する証拠:** 独立oracleの由来、同一元bytes比較、P準備/P消費/C消費の3結果。

**採用根拠:** K-VALIDATION-002「根拠と出典」L29–37 / K-VALIDATION-002「重要な判断と理由」L39–41。固定出典: S2, S3。

**追加推論:** 3結果を別欄にするレビュー表は本Consumerの具体化。oracleの作成も次回権限が必要。

## T05 未知Knowledge型の降格拒否

**適用条件:** 1.1 typed Knowledge配送。1.2候補profileは別契約としてのみ追加検査。

**手順:** 正常knowledge-context-v1を対照に、document_type=knowledge_unknown、型identity欠損、format=json/textへの変更を別々に試す。正しいmanifest/承認をfixture用に独立再sealした上で型検査へ到達させる。

**期待結果:** 正常contextのみ受理。未知型やidentity欠損をgeneric JSON/textに降格できない。元文書へのfield追加やstatus/attempt書換えで通さない。1.0に新型を番号変更だけで通さない。

**保存する証拠:** 元bytes保持、選択schema/format、型拒否が発生した段階。hash不一致だけで型拒否を検証したことにしない。

**採用根拠:** K-VALIDATION-002「要点」L17–19 / K-VALIDATION-002「重要な判断と理由」L43–43 / K-VALIDATION-002「失敗・不採用案」L52–53。固定出典: S4, S5。

**追加推論:** digest/承認をfixtureとして正しく作り直して型gateを分離する手順は追加推論。実運用認可の編集を許可するものではない。

## T06 外側bindingと記事・source閉包

**適用条件:** Delivery1.1。context-onlyとtyped input/handoff pairを別fixtureとして扱う。

**手順:** context-only正常系はknowledge_bindings=[]のまま全記事/sourceを同repo/commitの安全相対pathとdigestで収録する。1 source欠落・digest不一致・別commit同bytesへの差替えを1つずつ試す。別のpair系では入力/出力のassignment/raw_findings/knowledge_references/task_id/attempt/retry_of一致とbindingの重複・欠落を検査する。

**期待結果:** context-onlyで空bindingを正常受理し、記事/source欠落等は拒否。pair系は全構造と固定referenceが一致するときだけ受理。原Knowledge1.0本体を変更しない。

**保存する証拠:** 元文書digest、manifest外側digest、閉包一覧、pairの差分箇所と期待拒否。

**採用根拠:** K-VALIDATION-002「重要な判断と理由」L43–43 / K-VALIDATION-002「例外・適用しない条件」L45–47 / K-DELIVERY-001「再利用手順・検証」L46–49。固定出典: S4, S5。

**追加推論:** 具体的1.1規則は固定正本contracts/artifact-delivery.md「外側binding」に基づく追加設計。記事の1.2 candidate bindingを同一仕様とみなしていない。

## T07 公開承認とConsumer承認を独立検査

**適用条件:** 全配送。現在のManager認可・独立pinが必要。

**手順:** 安全性レビュー、過去公開操作承認、今回Consumer承認を別欄にする。consumer/scope/purpose/期限/representation、manifest/publication digestの一致を検査する。local fixtureでは公開承認unverified+限定contract-review承認と、利用未承認/期限切れを対照にする。

**期待結果:** 契約が許す限定読取りは過去公開承認の追認なしに扱える。利用未承認/不一致/期限切れは拒否。receiptのauthority_granted=falseを確認し実装・merge権限を推論しない。

**保存する証拠:** 認可原本とpinは非公開。公開候補には状態・観測範囲のみ。内側資料の過去承認を外側から逆算しない。

**採用根拠:** K-DELIVERY-001「重要な判断と理由」L34–34 / K-DELIVERY-001「例外・適用しない条件」L38–38 / K-DELIVERY-001「再利用手順・検証」L46–51。固定出典: S1, S4。

**追加推論:** 承認状態のfixture対照は追加設計。実承認の真正性はManagerの別経路に依存し、自己発行しない。

## T08 fresh receipt再検査後の実利用出力

**適用条件:** 初回CLI成功後に現在の認可が有効で再利用する場合。

**手順:** 初回receiptを非公開保存し、--verify-receipt付きで新規Git取得・別の新規出力へ再検査する。次の意味レビュー/計画作成が参照する実体を新出力から選び、利用locatorとdigestを記録する。必要なら旧出力と新出力を別途全bytes比較する。

**期待結果:** 再検査成功は新取得bytesとreceiptの一致のみ。利用出力が新規出力と一致し、旧出力の改変検知をreceiptに帰属させない。承認失効・再検査失敗ならその新規利用を停止。

**保存する証拠:** 2回のexit、新規出力、非公開receipt、利用したファイルdigest。旧新比較は別証拠欄。

**採用根拠:** K-DELIVERY-001「重要な判断と理由」L32–32 / K-DELIVERY-001「理解を深めるための問い」L59–61。固定出典: S2。

**追加推論:** 利用出力のlocatorをレビュー成果物に記録する手順を追加。このtaskでは実際に2回目出力を読んで計画を作成した。

## T09 配送gateの後に内容妥当性gate

**適用条件:** 助言を判断へ採用するすべてのKnowledge消費。

**手順:** 型/bytes合格とは別に2記事の重要主張を元sourceへ対応させ、事実/報告/推論、適用条件・例外・draft・問い・更新条件を読む。誤った内容を含むがbytes自体は正しいsynthetic文書を意味gateの負対照とする。

**期待結果:** 配送PASSでも意味不整合は採用保留/不採用。限定参考利用には教訓→判断→具体検証項目の対応と根拠が必要。単に要約しただけを実利用成功にしない。

**保存する証拠:** 主張対応表、採否理由、計画の項目ID。製品ACの実測結果は別gateのまま。

**採用根拠:** K-DELIVERY-001「要点」L19–19 / K-DELIVERY-001「例外・適用しない条件」L38–38 / K-DELIVERY-001「理解を深めるための問い」L59–61 / K-VALIDATION-002「再利用手順・検証」L59–59。固定出典: S1, S2, S5。

**追加推論:** 意味誤りを持つsynthetic負対照と利用対応表の構造は本Consumerの追加設計。

## T10 歴史・draft・現在headを分離

**適用条件:** 過去報告または修正headに関するKnowledgeを参照するとき。

**手順:** S4 blocked→S5自己検証→S1独立Test→S2独立Review failed→S6修正自己検証の順を保持。対象head/観測者/時点を並べ、現head判定が必要なら別途固定された独立Test/Review証拠を要求する。

**期待結果:** 旧failedと自己検証を消さず、現在状態は根拠がなければunverified。draftのまま限定採用し、修正独立結果/版変更/反例/2026-11-11で再評価。周期運用やactive化の達成にしない。

**保存する証拠:** head別状態表、出典revision、更新trigger、保留理由。

**採用根拠:** K-VALIDATION-002「陳腐化・更新履歴」L61–63 / K-VALIDATION-002「失敗・不採用案」L55–55 / K-DELIVERY-001「陳腐化・更新履歴」L53–55。固定出典: S1, S2, S4, S5, S6。

**追加推論:** 最新証拠がなければ現在状態判断を保留する運用は本Consumerの適用判断。

## T11 版と元bytesの保全

**適用条件:** 配送契約やprofileを更新する場合。

**手順:** 元context/article/source bytesを先にsealし、追加規則は版付き外側recordへ記録する。4配送recordの版一致、選択版schema、型identityと旧版互換条件を確認する。許可されない未知版や混在版を負対照にする。

**期待結果:** 元locator/status/attempt/digestは不変。Knowledge1.0/外側Delivery1.1/歴史的Delivery1.2を混同しない。新型受理には正式契約と明示認可が必要。

**保存する証拠:** 変更前後bytes比較、版の一覧、契約固定revision、schema判定。

**採用根拠:** K-DELIVERY-001「適用条件・範囲」L21–23 / K-VALIDATION-002「重要な判断と理由」L43–43 / K-VALIDATION-002「失敗・不採用案」L52–55。固定出典: S4, S5。

**追加推論:** 4配送recordの版一致等は正本1.1契約からの具体化。

## T12 失敗時の利用停止と有限配送

**適用条件:** 全配送。Managerが次回の予算を明示していること。

**手順:** 利用前に参照欠落/不一致を見つけたら新規利用を停止し、部分結果を保存。dispatch/execution/deliveryを別カウンタで記録し各最大3、失敗理由と必要処置をManagerへ返す。Knowledge待ちだけではアプリ開発を停止しない。

**期待結果:** failed/blockedを成功に変換せず、古い成功出力で代替しない。上限をscope変更等でリセットしない。計画作成と実行結果は別状態。

**保存する証拠:** 失敗段階、出力有無、予算消費、引継ぎの未確認点。

**採用根拠:** K-DELIVERY-001「再利用手順・検証」L46–51 / K-VALIDATION-002「失敗・不採用案」L53–55。固定出典: S4, S6。

**追加推論:** 3種類の最大3回管理はユーザーassignmentと固定workflowによる追加運用条件。記事だけから予算や実行許可を導かない。

## 固定出典と不採用判断

全記事の固定revisionは `74d0fb0d899984d99ea9fbde2871c46c66c3f52b`。A/K-DELIVERY-001は `knowledge/curated/validation/delivery-evidence-boundaries.md`（SHA256 `efde077ec14efb1991c1393f637be020f036f5e048f888eca75976156aea66f8`）、B/K-VALIDATION-002は `knowledge/curated/validation/boundary-tests-and-contract-evolution.md`（SHA256 `b6784558c0a6131fa0e9f68b89f7861bc63a135076cc5004c446223b8f79d1bd`）。段落は上記見出しと固定bytesの行番号で特定する。機械可読の全対応と6出典のdigestは[usage-map.json](usage-map.json)。

- N01 rejected: 配送PASSを製品AC/Readiness/新PR7 headの合格として使う。全bytesは内容・製品挙動を証明しない。今回アプリTestも新head独立Testも実行していない。
- N02 rejected: 1.2 candidate/tree bindingを1.1 context-onlyにそのまま追加する。契約版と対象型が異なる。今回のknowledge_bindings=[]と全source閉包を維持。
- N03 deferred: 修正headの最新独立合格・現在merge状態・draftのactive昇格。固定6出典には新しい独立合格がなく、初回時点のManager報告は現在状態証明ではない。新しい固定証拠と権限が必要。
- N04 rejected: 過去のtree sourceが未知型と別の実測停止原因だったと断定する。S4は未知型で止まった報告。treeは追加設計課題としてしか支持されない。
- N05 deferred: 周期実行・自動context生成・一般的な運用成功。今回の任務外で延期。独立計画への手動限定利用はその代替証拠にならない。

## 次回の返却様式

各項目に対象固定head、担当、適用/適用外理由、入力参照、実測exit/観測、期待との差、証拠参照を埋める。未実行はnot_executed、資料/権限不足はblocked、既知の不合格はfailed。配送、内容評価、実際の採用、製品AC、Readiness、周期実行を独立欄にする。新しいheadへ古いPASSを転用しない。

この成果物の利用は計画作成として完了しているが、計画の実行・製品AC判定・新PR7 headの合格・アプリ配備・周期運用・記事active化は認定しない。
