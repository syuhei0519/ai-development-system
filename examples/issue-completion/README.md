# Issue Completion samples

全て synthetic sample。2030 年の架空 repo/PR/actor/観測を使い、製品 AC や実配備を表さない。

- `synthetic-achieved`: 3 repo/3 PR、head と異なる squash merge 結果、merge 時点で有効（現在は失効）の PR gates、現在有効な全必須 subcheck、配備と統合、別の最終 Manager Handoff。
- `synthetic-pending`: 未 merge・未配備・全 AC unverified。CLI exit 0 は正直な記録の整合だけ。

実製品 Order3 の AC は未実測で **unverified**。この例に製品原文の推測や met の代入はしない。製品原文・現在環境・測定結果は Manager の認可済み初回入力で別に取得する。

以下の pin は synthetic replay 専用。実際の context pin は Manager の独立経路から取得し、bundle 自身の hash を権限としない。

```sh
python scripts/validate_issue_completion.py examples/issue-completion/synthetic-achieved/completion.json --context examples/issue-completion/synthetic-achieved/context.json --context-sha256 951048815ca07294e13e6df297272e719e121d81a8e1c523c3958e4ba97742ac --handoff examples/issue-completion/synthetic-achieved/handoff.json --at 2030-01-03T12:00:00Z
```

```sh
python scripts/validate_issue_completion.py examples/issue-completion/synthetic-pending/completion.json --context examples/issue-completion/synthetic-pending/context.json --context-sha256 8943ce6030f4335adb8cfab5f7338670b2c45b3d24bd3114e92fab5c1cd8d5ff --handoff examples/issue-completion/synthetic-pending/handoff.json --at 2030-01-03T12:00:00Z
```

再生成は `tests/completion_fixture.py` の build（テスト専用）。実体、全 hash、Handoff binding、CI の固定 pin を一緒に更新する。構造化 observation は元観測の真実性を保証しない。公開前に全 bytes を安全点検する。

## Preparation → standard product measurements → integration (1.1)

`tests/preparation_completion_fixture.py` は synthetic-achieved の準備依存版を生成する。
準備の製品結果は unverified のまま、後続通常 PR が全製品実測を提供する。
全3メンバーの merge、デプロイ、統合証跡は維持する。以下は合成 replay 専用。

```sh
python examples/issue-completion/preparation-example.py /tmp/synthetic-preparation
```

生成した context pin は合成例にのみ使用する。実運用の認可や独立 Manager pin の代用ではない。
後方互換の通常 aggregate control と異常系は `test_issue_completion*.py`、
新しい型・scope・root・測定と統合の異常系は `test_preparation_completion.py` を参照。
