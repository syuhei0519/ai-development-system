<!-- learning-scope-20261017:start -->
## 最新の学習スコープ（2026-10-17）

**Priority: P0（計画上。Projectフィールドは未変更）**

元の3ACを最小API/モデル/保存契約として維持する。受付/状態取得、テストsink成功/失敗、同一要求の重複抑止、再起動後永続化を1つのAPI/DB fixtureで確認する。独立entrypointとlocal build可能な最小image入力・固定source/runbookを配備#22へ渡す。正式公開、外部送信、Kafka、全サービス横断の信頼性実装は前提にしない。

この節を、競合する旧Priority・Scope/AC・依存方針より優先する。記載しない既存AC/失敗gateは維持する。下記は過去の計画・証跡として保存し、PR・試行/失敗・承認履歴をリセットしない。今回の変更はIssue計画のみで、実装/検証/公開/配備/Closeやnative依存の更新を意味しない。
<!-- learning-scope-20261017:end -->

## Goal

[Notification/API] 独立APIと永続状態を実装する

<!-- manager-capability-reorg-20261012:start -->
## 再編後の管理情報（2026-10-12）

- Backlog key: `app-notification-api`
- Level: Execution
- Purpose: Execution
- Epic: microservices
- Priority: P1
- Quality Level: Standard（元の目的・ACの範囲のみ）
- Status: Backlog / paused（未Ready・開発停止）
- Feature親: [app-notification-service — syuhei0519/backend-app#9](https://github.com/syuhei0519/backend-app/issues/9)

### 担当Scope

通知受付/状態取得、テストsinkの成功/失敗、同一要求の重複抑止、再起動後も残る所有状態と独立entrypointを実装する。外部メール/SMS・Kafka・配備は含めない。

### Execution Acceptance Criteria

- [ ] テストsinkの成功/失敗をAPIから確認できる
- [ ] 同一要求を再送してもsinkに重複送出しない
- [ ] 再起動後も受付済み状態を取得できる

### 主Validation Layer

layer: 使い捨てAPI/DB Integration
procedure: 正常・拒否/失敗・同一要求再送・再起動と所有状態を同じfixtureで確認する。

## Hard Dependencies

GitHub Native blocked_byを正本とする。以下はその管理View。
- なし

## Soft Dependencies

- なし

## Unlocks

- [app-notification-release — syuhei0519/backend-app#42](https://github.com/syuhei0519/backend-app/issues/42)

### 利用可能な既存Capability / 完了済み履歴

- なし

### Ready判定で残る確認

- 明示的な開発再開指示待ち。環境・Credential・必要な判断/承認は未確認。依存ゼロはReadyを意味しない。
- 模擬結果/再送identity・永続化契約の固定
- 使い捨てDB/テストsink環境

依存なしはReadyを意味しない。環境・Credential・必須設計・承認を未確認のままReadyにしない。既存Project所属・フィールドは変更しない。新規IssueのProject所属は未確認。

### 実行制約・履歴継承

1つの主変更と1つの主Validation Layerに限定する。既存Security / CI / Release・独立Test / Review・承認ゲートを維持し、AC証明に必要な最小限だけ検証・記録する。全Featureの検証や新しいHardeningを後付けしない。非Blockingの改善はFollow-upへ分離する。修復ループが2回を超える、またはScopeが拡大した場合は停止してManagerへ戻し、必要なDefect分割を行う。

既存PR・証跡・attempt / retry_of・失敗・承認・残予算を継承する。Issue分割は履歴のリセットや新しい実行予算ではない。Implementation / Test / Review / Merge / Publish / DeployとIssue Closeは今回行わず、明示的な再開指示を待つ。

<!-- manager-capability-reorg-20261012:end -->

<!-- backlog-key: app-notification-api -->
