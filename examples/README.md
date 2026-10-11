# synthetic sample fixtures

全サンプルは架空データであり、実タスクの実績・識別子・出典ではない。`completed` や report 内の記述は契約表現の例であり、実際の開発・製品テスト成功を主張しない。example.invalid は取得先ではない。

Research→Test の例:

1. [Research handoff](research-to-test/research.handoff.json) は [設計](research-to-test/design.md) の担当範囲を completed とする。
2. [Test blocked](research-to-test/test.blocked.handoff.json) は AC 原文を渡し忘れた初回起動を表す。基盤は completed でも業務は blocked。
3. Manager が原文を補完した [再起動の初回入力](research-to-test/test.initial-input.md) と取得済み添付を新規タスクに渡す。
4. [Test retry handoff](research-to-test/test.handoff.json) は attempt=2 と retry_of を追跡し、[設計検証計画のレビュー](research-to-test/test-plan-review.md) に限定して completed とする。実装のテスト合格ではない。

[failed](failed.handoff.json) は業務失敗の正常な契約例で、[専用の架空の不完全な計画と失敗レビュー](failed-test-plan-review.md) を根拠とする。成功した Research→Test の計画・レポートとは別の例。[invalid-completed](invalid-completed.handoff.json) は根拠のない completed を意図的に拒否する異常例。

[一部担当の Issue handoff](partial-assignment.handoff.json) は AC-1 だけを担当し、AC-2 を not_assigned のまま工程 completed にする v2.0 の例。Manager の最終判定は含めない。

[Knowledge 入力](knowledge/input.json)・[handoff](knowledge/handoff.json)・[後続向け参照](knowledge/context.json) は複数の架空 Issue の raw findings を AC 原文なしで扱う専用 v1.0 の例。[記事](knowledge/curated-example.md) は架空の draft であり実運用知識ではない。

[Readiness の正常・異常例](readiness/README.md) は PR ready と Issue unverified の両立、実装のみ可能・配備 blocked、postdeploy 全 AC 実測、および不正な前倒し achieved / premerge defer を示す独立 v1.0 契約。固定時刻で再生し、現在のマージ許可と区別する。

配送の固定公開参照・synthetic 承認例・未承認拒否例は [delivery/](delivery/README.md) を参照。
