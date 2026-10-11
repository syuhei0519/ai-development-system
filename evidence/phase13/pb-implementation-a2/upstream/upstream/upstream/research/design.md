# System Phase1-3 design assignment — Knowledge Agent 実装・検証計画

公開安全候補の編集派生版 / public_safe分類候補・未公開・公開承認待ち。作成日 2026-10-11。設計担当による read-only 調査の完了報告。実装・配備・運用完了報告ではない。

## 1. 結論と範囲

Phase1-3 は「Phase1 の第3工程 Knowledge Agent 実装」であり、Phase1〜3 全体ではない。Manager の工程管理と、独立 Knowledge Agent の選別・抽象化・記事管理を分離する。推奨は、既存 Git を確定した bytes と履歴の正本にし、Manager が節目と定期確認で取得・配送・独立 Codex Cloud 起動を担当する方式。Knowledge の失敗や遅延を開発のゲートにしない。常設6 Agent、追加 OpenAI API、PAT、新課金サービスは不要とする。

既存契約を実運用につなぐため、最優先は Knowledge v1 の配送型対応、次に source 固定と永続 inbox/state、次に同期 context/利用 acknowledgement、最後に周期をまたぐ運用実証。単なる文章追加や手動1回の実演では完了にしない。

設計対象は System Phase1-3 design assignment の明示的工程要件。backend Issue2 の AC は未提供であり流用しない。B1 再開、Order アプリ設計、Issue2 AC 合格、追加API、Secret・権限・Ruleset変更、実配備、コード変更、commit/push/PR/merge、他Agent起動は実施していない。

相談確認で渡された要求は、①Managerと別責務、開発と非同期 ②定期的同期、TaskAの知見を後続TaskBで活用 ③Issue横断の役割から設計判断/調査/失敗/テスト観点抽出 ④人間が理解して学べる文書。毎日1回・専用 Knowledge Dot は確定要件ではない。周期は下記の推奨であり、既存契約や利用枠の変更許可を意味しない。

## 2. 固定した情報源と実測

正本 repository は syuhei0519/ai-development-system、調査 commit は df400018057735b7cb6a9c6ea4619508f0e6ba3a（PR3配送契約の merge commit）。浮動 main の後続変更は判断に混ぜていない。各ファイルの blob、size、SHA-256 は source-inventory.json に固定した。

|根拠|確認した内容|
|---|---|
|[agents/research-design.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/agents/research-design.md)|設計・検証案、工程完了と製品合格の分離|
|[agents/knowledge.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/agents/knowledge.md)|Knowledgeの独立責務、全finding判断、非ブロッキング、3試行|
|[agents/manager.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/agents/manager.md)、[workflow](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/workflows/single-issue.md)|DotsがManager、独立Cloud、会話・環境の共有を仮定しない|
|[Knowledge契約](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/README.md)、input/handoff/context schema|AC不要、複数Issue、固定出典、採用・保留・不採用|
|[Artifact Delivery](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/artifact-delivery.md)|公開原本/派生版、承認pin、全bytes検査、別retry予算|
|[Readiness](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/readiness.md)|Implementation/Deployment/Merge/Issue Completion分離、集約未実装|
|[記事テンプレート](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/templates/knowledge-article.md)、raw/input template、knowledge索引|人間向けMarkdown正本、適用条件・例外・失敗・問い・更新履歴|
|[配送実経験の公開記録](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/records/artifact-delivery/correction-20261011.json)|Git配送観測、Producer証言と独立原本照合の区別、未解決Library/inline失敗、B1 terminal保全|

実測: 固定checkoutで `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q` は107 tests / OK / exit 0。これは本Researchによる baseline確認であり、将来変更の独立Test/Review・CIではない。

追加の最小再現: examples/knowledge/{input,handoff,context}.json を validate_knowledge.validate と consume_delivery.verify_handoffs(format=json) に渡した。3件ともKnowledge schema検査は合格。input/handoff は `Handoff must be typed handoff-v2` で拒否、context は配送型検査を通る。ネットワーク配送全体の成功を主張する実験ではなく、既存関数の型分岐を確認したもの。

原因は scripts/consume_delivery.py:155–165 の reserved identity 判定であり、Knowledge input/handoff の task_id/assignment/system_status が Handoff v2 の予約項目と衝突する。format=handoff-v2 へ偽装すると v2 schema が不一致となる。text偽装・埋込み・識別子削除で回避してはいけない。

固定repoに AGENTS.md/.agents/skills はなく、選択環境のskills領域 にも参照可能なskillはなかった。別アプリrepoの設定やACは調査対象にしなかった。

## 3. 現行実装と未実装境界

|領域|存在するもの|今回の実装候補・不足|
|---|---|---|
|Knowledge v1|input/handoff/context schema、validate_knowledge.py、架空サンプル、15件のKnowledge unittestメソッド|原入力との比較、記事bytes/context metadataとの一致、immutable sourceの実在確認は単体CLIでは保証しない|
|記事管理|raw/curated索引、採否・lifecycle・review_after・問いを含むテンプレート|実運用記事なし。重複・矛盾台帳、実体索引整合、stale検出は未実装|
|配送|Git全bytes、size/hash、承認pin、Handoffv2 bindings、Publication/Consumption receipt|Knowledge型配送不可。Knowledge型を明示した検証・binding追加が必要|
|retry|dispatch/execution/delivery各最大3、履歴pin、更新validator|inbox処理と連携する実行器、lease、開始不明照合は運用/実装が必要|
|非同期|責務分離と開発非依存という運用契約|event/inbox/cursor/replay/定期実行/遅延可視化なし|
|Actions|validate.yml: feature push・pull_request、contents:read、契約/107テスト等|schedule/workflow_dispatch/収集jobなし。Agent起動APIの実装もない|
|後続利用|knowledge-contextと記事実体を初回入力に渡す契約|context生成、stale確認、consumer採否・実利用証拠の機械照合なし|

Knowledge schemaのrevisionは非空文字列の制約であり、40桁Git SHAや実体digestを証明しない。現行validate_knowledge.pyはjson.loadsによる単体形状/参照検査で、配送CLIの厳格JSON解析と同じ保証ではない。新しい公開inbox入口は厳格解析を使う。

## 4. 実行方式の比較・採否

|方式|実現するもの|制約/採否|
|---|---|---|
|A. Managerの節目＋定期チェック、独立Cloud、Git確定|Managerが取得・入出力作成・dispatch・回収。Knowledgeが非同期に解釈し、PR経由で確定。後続TaskBへpin配送|最小構成として推奨。スケジュール実行内でCloud委任・回収できるかは実機検証が必要。通常チャットで委任できても定期runで同じとは断定しない|
|B. GitHub Actions schedule/dispatchで機械的sweep、Managerが結果を読む|許可済みpublic Git inboxを固定SHAで全件照合し、due/failureレポートを出す。追加OpenAI API不要|補助として採用可能。LLMによるcuration/Cloud起動はActionsへ持ち込まない。Actions単独では要件のAgent実行を完結しない|
|C. 専用Knowledge Dotのnative schedule|既存契約のKnowledge roleで定期curationできる可能性|確定要件ではない。利用枠・永続source読取・同じ配送検査・Manager回収が実証される場合の将来代替。現段階の必須にしない|
|D. shell cron/常駐worker/独自queue service|自動ポーリング|新常設環境・運用責任・権限を必要とするため不採用|
|E. Actionsから架空のCloud起動API/新OpenAI API|無人Agent起動を想定|根拠なし/追加API禁止に抵触。不採用|
|F. Managerが候補の要約・記事化まで実施|起動回数を減らせる|責務分離要件に反する。不採用|
|G. 手動1回の配送のみ|happy path確認|開発用smokeには有効、定期運用完了の証拠として不採用|

推奨運用周期は「各専門工程のhandoff回収時にenqueue、次のTask起動前に最新の検証済みcontextを確認、24時間程度の定期sweepで未処理・失効を補完」。24時間は初期推奨で、毎日固定実行の確定要件ではない。候補量・実行枠で調整し、空batchはAgentを起動せずno-op記録にする。無制限な頻度増加や追加課金を前提にしない。

ChatGPTの現行公式説明では定期タスク、接続ツール、保存prompt、webでlocal folderを保持しない制約が説明されている。これは特定のManager scheduled runから独立Cloudを起動できる保証ではない。既存能力をreadonlyで確認し、短い能力実験でdispatch/回収まで確かめる。使えなければ、定期通知を受けたManager/人間補助による実行を明示し、自律実行達成とは呼ばない。[公式説明](https://learn.chatgpt.com/docs/automations)

Actionsのscheduleはdefault branch上で動き、負荷による遅延/欠落があり得る。したがって正確な時刻や各通知を配送保証として扱わず、次のsweepで全未処理を再照合する。正本はGit/管理台帳であり、期限付きActions artifactだけにcursorを置かない。[GitHub公式](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

本調査はscheduler登録もworkflow変更も行わない。設定追加/有効化・課金枠・永続保管先・必要権限はManagerが既存認可の範囲を確認する。権限拡張や有料代替を自動選択しない。

## 5. 責務と処理の流れ

1. Research/Implementation/Test/Review の工程終了時、通常handoffとoptional knowledge_candidatesをManagerが回収。候補が空でも開発を継続する。失敗/blocked工程の観測も採取対象とし、成功工程だけに偏らせない。
2. Managerの収集器は候補が指すevidence_idsと原artifact実体を取得・検証し、Raw Findingへの機械的対応と出典pinを作る。選別・一般化はしない。候補summaryだけを根拠の代用品にしない。
3. 認可済み非公開原本を保全し、安全な派生版を別bytesとして作成・審査。public側には公開alias、公開版のsize/hash、固定出典だけを置く。原本digest/実task ID/私的会話リンク/内部ログ/対応表は置かない。
4. 安全性と公開操作承認を通ったpublic event/根拠をGitで確定。通知はwake-upであり、取得するsource SHAを必ず固定する。原根拠不足/不許可はknowledge quarantineへ記録し、開発は進行する。
5. Managerがdue batchをclaimし、Knowledge v1 inputと実体、既存記事context、roles/contracts、権限と返却先を独立Cloud初回入力へ配送。開発側の次工程は待たない。
6. Knowledge Agentがraw保全・重複/矛盾評価・採否・記事/index差分・専用handoffを返す。Managerは再要約せず、原入力/出力一致と全実体・判断を照合する。
7. 独立Test/ReviewとCIを経た記事・indexをGitに確定。Managerがpublic pin/利用承認/receiptを作る。Gitはbytes/history/merge整合を担い、Agentの起動、業務採用、公開許可を決定しない。
8. 後続TaskBへ固定knowledge-context、取得済み記事、状態確認時点、実体receiptを渡す。Consumerが適用判断と利用箇所/未採用理由を返す。新記事が未readyなら既存の検証済み知識か知識なしで続行する。

Source原本が一時Cloud領域しかない場合は「seal済み」と「永続保存済み」を区別する。既存の認可済み非公開保管先をManagerが確認できないならprivate収集の運用はblockedとし、public/synthetic経路の実装と検証を続ける。Libraryの過去配送失敗が解決済みとは仮定しない。

## 6. 提案する外側契約とCLI責務

以下は新設計であり現行CLI名/fieldの存在を主張しない。Knowledge v1/Handoff v2/Readiness v1の業務意味を維持し、追加fieldを既存additionalProperties=falseへ押し込まない。

### 6.1 KnowledgeEvent v1 / 永続inbox

公開安全なeventは `schema_version, document_type, event_id, event_kind, source_ref, candidate_id, producer_role, observation_kind, finding_refs, occurred_at, collected_at, representation, classification` を持つ。source_refはrepository/40hex commit/path/size/sha256、finding_refsも実体へのpin。observation_kindはdecision/research/failure/test_observation等であり、内容を推論したことが分かる場合は明示する。Issue参照は0件以上で可。実task IDは非公開台帳だけに置く。

event_idはversion付きcanonical identity（repo, commit, source path, source bytes sha256, candidate_id, event_kind）からSHA-256で生成。時刻、配送attempt、runtime task IDをキーに含めない。正規化対象はidentity JSONのみ、原根拠bytesは正規化しない。同じidentityに異なるpayload digestはcollision/tamperとして隔離。訂正は新eventとsupersedes関係で表す。内容が似ているだけでtransport dedupしない。

初期public inboxは許可済みrepoの限定pathにappend-onlyのeventファイルとして置く提案。例: knowledge/inbox/events/<event-id>.json。Knowledge本文/indexとは分ける。private inboxは既存認可済み非公開保管先のみ。read-only Actionsがinboxへ直接pushする設計にはしない。Managerが許可されたGit確定経路を使用する。

### 6.2 KnowledgeCollectionState v1 / cursor / crash recovery

Manager台帳はsource registry pin、sourceごとのlast_scanned_commit、event digest一覧、各event処理状態、scan/run履歴、batch/input digest、retry台帳pin、committed_output_pinを保持する。公開用は安全な観測レポートだけ。状態更新は一つのManager writerに限定し、前state digestをcompare-and-swapで照合してatomic replace。複数writer対応は初期実装に入れない。leaseは二重起動防止の補助であり、期限切れだけでAgent再起動しない。

スキャン開始時点Sのtree/inboxを最後まで列挙→全件source検証→durable stage→event登録とscan cursor更新を一つのstate transactionにする。cursorは「ここまで列挙済み」であり「全て処理成功」ではない。eventごとのpending/blocked/terminalを残す。途中の読み取り失敗ではcursorを進めない。API paginationを使うadapterでは全page終了と安定source pinが必要。updated_atだけやwebhook配達順だけに依存しない。

履歴欠落・force push・旧cursor非ancestor・registry変更時はfull reconciliation。過去のterminalやsource digestを消さず比較する。毎回全inbox照合を最初の実装とし、小規模では単純さを優先する。diff最適化は後続。source欠落は消えたeventを成功扱いにせずquarantineへ。

状態: pending → verified → reserved → dispatching → started → output_received → validated → commit_pending → committed → context_available。根拠不足はquarantined/blocked、開始不明はdispatch_unknown、上限失敗はterminal。curation判断のdeferred/rejectedと処理失敗は別フィールド。validatedでもGit確定まではcompleted processingとしてcursorから除外しない。

crash後はinput digest+batch ID+Managerの実task対応を照合し、開始/未開始/終了不明を確定する。取得済みoutputがあればdeliveryから再開しKnowledgeを再実行しない。Git確定済みでstate未更新なら固定commitを検証してackを修復。二重commit/再dispatchを防ぐ。

### 6.3 Batch / replay / retry

batchは明示的event ID集合とinput digestでsealする。schema上raw_findingsは1件以上必要なので空batchはKnowledge入力を作らない。batch途中の新eventは次回へ回す。batch IDとイベント集合を変更して既存失敗を初回扱いにしない。

replayは固定source/state snapshotから同じplanを再構成するread-only処理。過去承認の期限切れを現在の利用許可にしない。再度のsemantic curationは同じ論理工程なら同じretry budget、新しい反例/更新イベントなら過去判断との関係と新assignment理由をManagerが記録する。

既存validate_retry.pyへdispatch/execution/deliveryの結果をappendし、各初回込み最大3。開始不明はreconcileまで停止。delay/backoffはManagerのnext_eligible_atとして保持し、Agentが自分を再帰起動しない。定期sweepでterminalを自動初期化しない。B1の3回とRETRY_LIMIT_REACHEDはこの基盤の完成によって解除されない。

### 6.4 Knowledge v1の配送型とbinding

推奨はArtifact Deliveryの明示的 minor version拡張（例v1.1）として `knowledge-input-v1 / knowledge-handoff-v1 / knowledge-context-v1` を追加し、旧v1.0を旧ルールのまま受理するversion dispatch。manifest/publication/consumptionの複製reference定義とverification表現を一緒に更新する。Handoff v2/Knowledge v1本体の意味は変更しない。旧validatorが新型を静かに通さずfail-closedする状態を維持する。

新しいformatはdocument_type/schema_version/roleを完全一致で検査し、専用schema+意味validatorを使う。Knowledge風JSONがgeneric json/text/Handoffへ降格する経路を拒否する。予約field検査を単純削除してHandoff偽装を許してはいけない。未知型、欠損型、複数identity、private_onlyは拒否。

外側Knowledge bundle bindingはinput reference digest、handoff reference、raw/source/artifact/context参照の実体manifest entriesを束ねる。inputとhandoffのassignment/raw_findings/knowledge_references/task_id/attempt/retry_ofを照合。結果statusや決定欄以外の入力改変を拒否。すべての原入力findingに一つの根拠付きdecisionを要求し、adoptedのarticleがknowledge種別かつ実在bytesであることを検査する。

sourceは既存公開Git sourceの固定commit/path/digestか、非公開側の認可済みbytes snapshotに限定して初期実装する。任意Web URLの自動取得は入れない。Knowledge v1の自由locator文字列だけをhash一致の代用にしない。外部根拠snapshotを公開するときも安全性・公開許可が必要。ソースの真実性/一般化/原本対派生版の同等性は機械検査とは別の独立レビュー。

### 6.5 KnowledgeSync / Consumer acknowledgement v1

別artifactとして `consumer_alias, assignment_ref, context_ref, delivery_receipt_ref, knowledge_snapshot_commit, lifecycle_snapshot_ref, observed_at, references[]` を持つackを提案。各referenceにarticle ID/revision/digest、read確認、adopted/adapted/not_used/deferred、適用理由、条件/例外確認、consumer成果物の具体的利用箇所または非採用理由を記録。自己申告「読んだ」だけで利用実証にしない。

context生成は同一knowledge snapshotのindexと記事実体から行い、ID/revision/lifecycle/applicability/exceptions/sources/review_triggerを照合する。現行schemaには対象consumer情報がないため外側sync recordで束ねる。Consumer初回入力にindexだけ渡さず記事全文とcontextを添付。Handoffのkind=other artifactとしてackを参照でき、final_assessmentは追加しない。

新規タスク開始時にlatest policy/lifecycleを確認し、選ぶ記事のSHAは固定。開始後に新revisionが出てもsilent hot swapせず次の同期で新contextを生成する。criticalな反例/失効が判明したときはManagerが該当consumerへ追補を判断する。古いsnapshotしか読めないならfreshとは主張せず、non-useか条件付き採用理由を残す。

## 7. 知識の品質・原本・陳腐化

Raw Findingsは観測と固定出典を保全する。正誤訂正は履歴/追補で残し、失敗や不採用を削除しない。採否はraw判断欄に追記するが、原観測のsnapshotとdigestは不変。異なるIssueの同じ現象はraw IDを保ったまま一つのcurated記事へまとめる。

transport dedupは同一source identityだけ。semantic dedupはKnowledgeが根拠を比較して判断し、duplicate_of/related_toを外側decision recordへ残す。矛盾は多数決で潰さず、環境/version/前提/観測日で説明できるか調べる。説明不能ならdeferredと必要な追加観測を記す。重複も入力findingごとのdecision coverageから除外しない。

機械的enumは既存のadopted/deferred/rejectedを使用。rawテンプレート/READMEのacceptedは「記事として採用」の表記差なのでadoptedへ統一する更新を推奨。意味の新設や過去原本の書換えはしない。

記事は要点→適用条件→例外→根拠と事実/推論→重要判断と比較→失敗/不採用→再利用手順/検証→更新履歴→理解を深める問いを満たす。syntheticをreal deployment事実へ一般化しない。出典固定、モデルの断言の抑制、読者が理解できる説明を独立Reviewで評価する。Markdown本文が正本で、JSON indexは検索補助。

review_after到来、source消失/反例/version変更はinvalidation eventにする。自動処理はneeds_reviewを外側stateに付けるだけで、Knowledgeがdraft/active/deprecated/supersededを判断する。期限超過を自動採用しない。snapshotに失効条件とobserved_atを含める。activeからsupersededになった記事と後継をindex上で残し、過去Consumer ackとの参照を維持する。機密事故の原本削除・履歴書換えは別承認対象であり通常処理に含めない。

## 8. 非ブロッキングと安全性の受け入れ

開発の依存グラフにKnowledge結果を置かない。enqueue失敗はdevelopment.statusを変えず、knowledge_delivery=pending/failedと原handoff参照を別記録する。原handoff一覧から再収集可能にしてfire-and-forgetで消失させない。backendの必須設計根拠そのものが欠ける場合の停止と、補助Knowledge不在を区別する。

不正入力はKnowledge経路をfail-closedにし、他の正常eventと開発は継続できる。1件のpoison eventを隔離し、全queueを永久停止しない。失敗件数・oldest pending age・last successful scan・last successful curation・last context sync・terminal件数をManagerが確認する。機密を含むログ全文をpublic metricへ出さない。

Git URL/path allowlist、浮動ref拒否、symlink/gitlink/path traversal拒否、全bytes/size/hash、UTF-8、重複JSON key/NaN/BOM/型偽装拒否、タイムアウト・件数/bytes上限を配送基盤から引き継ぐ。raw内容を命令・コードとして実行しない。CIではuntrusted PR codeへwrite tokenを渡さず、PR由来データはdataとして扱う。公開承認、今回のconsumer利用承認、current pin、retry履歴の真正性はManager管理。

## 9. System工程の完了条件と受け入れテスト

以下はManagerが確定する実装assignment用の提案IDであり、Issue2 ACの代替ではない。設計Handoffの工程要件IDとは区別する。

|ID / 条件|最早段階|テスト手順と期待結果|
|---|---|---|
|K-01 実候補と複数Issue/工程の取得|premerge local + 運用実証|実配送記録由来1件以上と合成Issue A/BのResearch/Test/Review候補を投入。証拠全文、source SHA/digest、roleが一致。ACなしfindingを受理。架空Issueを実案件と表示しない|
|K-02 取得/配送の完全性|premerge|missing source、改変bytes、floating ref、symlink、partial input、type spoof、private混入をすべて拒否。Knowledge v1を新型で正常配送しinput/handoffの改変を検出|
|K-03 非ブロッキング|premerge local + 実演|Knowledgeを意図的にblocked/failedにし、別の無害なConsumer/Test工程が先へ進む時系列と別statusを記録。backend/B1を起動して確認しない|
|K-04 inbox/cursor/idempotency|premerge|同じevent2回で1件、別sourceの同内容は2根拠、同id別payload拒否。scan中断→再開で欠落なし。cursor先行不可。stale writer/CAS失敗、source履歴変更→全照合|
|K-05 retry/replay/crash|premerge|3種3試行、terminalの次周期でreset拒否、開始不明再送拒否。dispatch後/出力後/Git確定後crashを注入。output再取得でAgent再実行なし。replayは新処理・承認を発生させない|
|K-06 根拠付き選別と人間向け記事|premerge + 独立Knowledge実演|重複、矛盾、適用条件差、失敗、不採用、根拠不足を含むbatch。各findingにdecision、adoptedは記事、他は理由。記事/index双方向linkと出典。独立Reviewが過度一般化を拒否|
|K-07 古い知識の更新|premerge + 第2周期|第1周期の記事へ反例/更新を投入。old raw維持、記事revision更新/失効、index後継、contextに変更理由。期限到来をREPLAY時計で機能検査し、live確認と区別|
|K-08 TaskA→独立TaskB利用|premerge fixture + 運用実演|別Cloud Consumerへ固定context/全文を配送。ackとConsumer test-plan/designの実利用箇所を独立Testが読み、適用条件を引用した追加テスト等の成果を確認。採否理由だけでは「利用」実証不足|
|K-09 定期同期経路|post-activation|同一登録scheduleの異なる2 due window以上でrun ID/設定pin/時刻/scan範囲/差分/結果を取得。2回目に新findingまたは失効を反映しConsumerへ新context。手動Run now2回やmock clockだけは不十分|
|K-10 回復と空周期|premerge fixture + 運用観測|空queueのno-op、1周期欠落後catch-up、1 poison event隔離、overlap run拒否を確認。定期失敗はKnowledgeだけに限定しpendingを残す|
|K-11 権限と互換性|premerge|追加API/Secret/PATなし。旧Handoffv2/Knowledgev1/Deliveryv1サンプルと既存107tests維持。receiptから権限を作らない。read-only jobが記事commit/Agent起動しない|

K-09は本質的にschedule有効化後の実測でありpost-activationに分類する。他のpremergeで可能なテストを「運用がない」理由で後送りしない。周期実証がまだならimplemented/testedとoperationally demonstratedを分けて未完を表示。スケジュールがAgent起動まで対応しない場合はassisted periodic operationの実証範囲を明示し、完全自律運用は未検証とする。

具体的合成matrix: A/Researchが固定revision必須を観測、A/Testが同事象を重複観測、B/Reviewが「receiptで旧ローカル改変も検出する」という誤解への反例、B/Testがそれを検証、C/Researchが別runtimeでの適用限界、孤立sourceなし候補はquarantine。public fixture内の実識別子は全てsynthetic alias。実記録とfixtureを混ぜてreal multi-issue rolloutを主張しない。

## 10. PR分割とmerge依存順序

PR番号は未採番。以下のP-A〜P-Dは設計上の別名であり実PRではない。

|単位|差分と優先順位|依存/完了条件|
|---|---|---|
|P-A Knowledge配送と照合契約（P0）|明示format/version dispatch、Knowledge bundle input-output binding、strict入口、契約・CLI・負例・互換検証|PR3固定baselineから開始。既存v1.0保持と型偽装拒否。独立Test→Review→CI/保護→merge|
|P-B 非同期収集/inbox/state（P0）|event/state schema、scan/plan/record/reconcile/replayの小CLI、CAS/atomic保存、retry連携、source registry、synthetic fixtures|P-Aの検証済みbytesを利用。collector自身はAgent起動しない。cursor/失敗注入/3試行の独立検証後merge|
|P-C 同期context/ackと運用手順（P1）|記事/index整合、lifecycle/stale、context生成/ack検証、Manager手順、periodic adapter（既存scheduleまたはreadonly Actions）|P-B/P-Aが必要。無権限で登録はしない。schedule planと実活性化を分離。過去の未実装境界を段階別に更新|
|P-D 実Knowledge成果と利用証跡（P1）|Managerが独立Knowledgeを起動し、実候補+synthetic batchからraw/curated/index。別Consumerの利用実証と第2周期更新の安全な証跡|P-C後。記事内容を独立Test/Review。運用結果は正直に未実測を残す。記事改訂が続く場合は追加PR可|

schema/docだけ先行mergeして「完了」と言わない。P-D実証が検証対象コードの修正を要求したら対応PRへ戻り、新headでTest/Review/CIを再実行する。周期実証の待ち時間中も開発は継続する。

各PRはImplementationの固定head成果物を独立Testへ、その結果と差分を独立Reviewへ渡す。Testは配送改変・crash・権限・同期利用を実行して証拠を返し、Reviewは設計整合・安全性・役割独立・一般化・未検証表示を確認。Research自身のbaseline成功やImplementationの自己テストを独立Testに数えない。Managerが証跡の同一head/base/config/target/期限/必要merge-groupとGitHub必須checks/review/Ruleset/queue/許可を個別確認する。

Merge ReadyはPR単位、Issue Completionは全体。複数PR/repo IssueCompletion集約契約は未実装でありPhase1-2完走依存として識別するだけ。本設計で作らない。aggregate_required/unknownを単一PRのachievedにしない。必要ならManagerは全体final_assessmentを省略しReadinessでunverifiedを維持する。Knowledge運用の達成証拠を記録することとIssue2/Order全体achievedは別である。

## 11. 実証の実行手順と後続への入力

Managerは次を順に委任する。本Researchは起動しない。

1. 設計Test/Review: このreport、Handoffv2、固定source inventory、baseline観測を取得。P-Aの型衝突とP-Bのcrashモデル、K-09の実機可能性を検証する。codeは変更しない。
2. Implementation: P-Aから開始。許可範囲はsystem repoのみ。既存backend/frontend/gitopsを触らず、実装後に独立Test/Reviewへ固定bytesを配送する。
3. TaskA: 配送基盤の公開記録を根拠として、Producer証言と独立検証、receiptの保証範囲、dispatch/delivery/execution分類の実Candidatesを抽出する。記録に書かれた主張と独立再現を区別する。合成複数Issue/工程の候補も別ラベルで追加。
4. 独立Knowledge K1: 全原根拠と既存contextを添付したKnowledge v1入力を渡す。採否/矛盾/失敗/適用条件/問いを含む記事とindexを返す。Managerは編集を代行しない。
5. CONSUMER-B（無害な後続専門タスクであり、過去のbackend B1とは無関係）: 「配送fixtureのテスト計画を作る」独立Test/Researchタスク。記事を固定SHAで読み、receipt再検査が旧出力改変を保証しない点を受入ケースに反映。ackと具体的test-plan箇所を提出。アプリ実装を再開しない。
6. 次の実schedule周期までに新反例/適用条件差をinboxへ投入。K2で既存記事を更新、CONSUMER-Cへ新context配送。K1とK2のrevision差・両ack・実周期証跡を記録。空周期/失敗回復も確認。
7. ManagerはK-01〜K-11を証跡で判定し、未完点・assisted/automaticの範囲・実運用sourceとsynthetic範囲を報告する。

Consumerの初回入力はassignment、対象revision、役割、提供された工程要件、固定knowledge-context、記事全文、delivery receipt、別経路承認pin、最新lifecycle確認時点、返却ack仕様を含む。過去会話やKnowledge Agentの環境が見えると仮定しない。

## 12. 更新すべき現行ドキュメント

ファイル名は root Knowledge.md ではなく agents/knowledge.md と knowledge/README.md が存在する。

|場所（固定SHAの位置）|変更方針|
|---|---|
|agents/knowledge.md Execution Boundary L36|「Phase1-1では未実装」を履歴として保ち、Phase1-3で実装したcollector/syncと未検証scheduler能力を具体的に分ける|
|agents/knowledge.md Readiness L40|「非同期基盤の実装・起動対象外という境界を維持」を現行段階に合わせ更新。Readiness/Issue Completion責務なしは維持|
|agents/knowledge.md Permissions|Phase1-1時点のmerge禁止の歴史表現と、今のManager経由の許可範囲を分ける。Knowledgeが独自mergeする権限は足さない|
|knowledge/README.md L25、contracts/README.md L41、templates/knowledge-input.md L19、README.md L93|手動仕様のみという説明を、実装済みCLI/運用手順/実証状況/制限へのリンクに更新|
|workflows/single-issue.md Knowledgeと変更単位|enqueue→定期reconcile→独立Knowledge→承認/PR→context/ackを追加。開発非依存を維持|
|agents/manager.md|候補選別を代行せず、source取得/台帳/周期/dispatch不明照合と別retryを管理する手順追加|
|templates/raw-finding.md、knowledge/README.md|accepted/adopted表記差の統一、raw観測とdecision追記の分離、公開派生版出典と私的原本の区別|
|contracts/artifact-delivery.md・関連schema/receipt/CLI|Knowledge型対応のversion/互換性/全実体bindingと保証範囲を追加|
|knowledge/*/*/README.md|実記事追加後だけ「記事なし」を更新。fixtureだけで実運用記事ありとしない|
|agents各Consumerとtask-input template|context/記事read・適用判断ack、stale時non-useを追加。AC原文や実測の代替禁止を維持|

更新時に「常設処理なし」を「自律scheduler稼働済み」へ一括置換しない。実装、登録、有効化、定期run観測、Knowledge完了、Consumer利用を別状態で示す。

## 13. 依存・残る判断・完了判定

今すぐ独立して進められるのはP-A/P-B、P-Cの純粋validatorと運用定義、public/synthetic source設計、独立Test/Review。Phase1-2 Order未完了はこれらを止めない。実配送記録の調査可能範囲も使える。OrderのAC、DB/Secrets/deploy、B1試行上限解除を必要としない。

運用実証前にManagerが確認するもの: scheduled run内の既存Cloud委任/回収能力、既存認可済みprivate state/source保存先、選択sourceのread可否と公開安全性、既存利用枠での周期、Git/Actions workflow有効化範囲、Consumer別利用承認。新Secret/権限/cost/実配備が必要なら該当操作だけ止める。人間に一般技術選択を丸投げせず、方式A・24h程度sweep・single writer・全件照合・typed deliveryを推奨値としてManagerが入力へ確定できる。

この設計assignmentは完了。Knowledge実装・実Agentによるcuration・TaskB利用・scheduler登録/周期運用・新CI/独立Test/Review・PR/merge・IssueCompletionはいずれも本タスクで実行していない。reportとhandoffの保存だけで公開承認・配送成功・実装再開許可は生じない。

## 派生版の状態

本書は設計原本から私的入力来歴と内部の保存場所を除去した編集派生版。独立内容安全性review・公開操作承認・今回のConsumer利用承認は未取得。原本と同じbytesではない。原本との比較はProducerによる確認であり独立原本照合ではない。原本のdigest、私的会話リンク、実task識別子、内部ログは含めない。配送はManagerの次指示待ち。
