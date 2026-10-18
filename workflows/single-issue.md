# 学習用の Issue ワークフロー

## 起動と責任分担

依頼で指定された repo、固定 revision、目的、必要な AC、禁止事項を渡す。
Research/Design → Implementation → Test → Review のうち必要な工程を使い、
Manager が独立 Review と現在の CI を確認してマージを判断する。
実装者の自己検証を独立 Test / Review と扱わない。

## 実行場所と必要能力

実装、Unit/build/static、対応 runtime の DB/API 検証、Helm rendering は Codex Cloud。
実 cluster が必要な検証は許可された既存 kind で行う。利用不能ならその検証だけ未確認とする。
追加 API・課金・Secrets/Ruleset の変更・main 直接 Push は行わない。
環境操作は対象、権限、復旧範囲が明示された場合に限る。

## 成果物と Handoff

標準の引継ぎは単一 Markdown。`templates/handoff.md` の
「目的・やったこと・観察結果・学び」に、repo / branch / commit、差分、
実行コマンドと結果、未確認点・阻害理由・次の担当を含める。
ログ、生成 JSON、render、試行ごとの出力は CI artifact に置く。
artifact の保存期限後も追試できるよう、再現手順と結論を Git Markdown に残す。
単一成果物に manifest / authorization / receipt / 独立 bytes pin を重ねる必要はない。

## マージ方針

feature branch と Draft PR を使い、独立 Review と required CI 後に Manager がマージする。
CI required check 名、security checks、安全拒否、通常の image digest と依存固定を維持する。
PR が未マージなら統合完了とせず、未検証の AC を成功にしない。

## 失敗と履歴

過去の失敗・未実施・未確認を成功に上書きしない。再試行時は変更理由と結果を短く追記する。
attempt 予算や配送台帳を通常の学習作業の必須入力にはしない。
過去の停止済みタスクを再開する許可は、この方針変更からは生じない。
古い JSON 契約を明示指定した既存タスクには、その固定契約と履歴を使う。

## 互換性

既存 Handoff v2.0 の JSON schema / CLI とその回帰 fixture は互換用に保持する。
Readiness / Delivery / routing 等の旧検証器は過去契約の再現用で、標準の新規タスクには要求しない。
Markdown は `python scripts/validate_handoff.py templates/handoff.md` で構造確認できる。
構造確認は事実・AC 達成・公開許可・独立レビューの証明にはならない。
非公開実行 ID、内部ログ、認証情報は公開しない。
