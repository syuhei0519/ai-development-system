# synthetic sample: readiness

すべて架空の repository、PR、SHA、人物、時刻、観測結果。実行実績ではない。2030年の固定時刻は再生用であり、現在のマージ許可には使わない。

| ファイル | 期待値 |
| --- | --- |
| pr-ready-issue-unverified.json + context.json | PASS。Merge Ready と Issue unverified が両立 |
| manager.handoff.json | 上記 readiness を artifact 参照する Handoff v2.0。Manager 最終判定は unverified |
| implementation-only.json + automatic-context.json | PASS。Implementation Ready、Deployment blocked、Merge blocked |
| postdeploy-achieved.json + context.json | PASS。マージ・配備イベント後の全 AC 実測でのみ achieved |
| invalid-premature-achieved.json + context.json | FAIL。未検証 AC を残した achieved |
| invalid-premerge-deferred.json + context.json | FAIL。premerge 不合格の延期 |

```bash
python scripts/validate_readiness.py examples/readiness/pr-ready-issue-unverified.json \
  --context examples/readiness/context.json \
  --handoff examples/readiness/manager.handoff.json --at 2030-01-01T12:00:00Z
python scripts/validate_readiness.py examples/readiness/implementation-only.json \
  --context examples/readiness/automatic-context.json --at 2030-01-01T12:00:00Z
python scripts/validate_readiness.py examples/readiness/postdeploy-achieved.json \
  --context examples/readiness/context.json --at 2030-01-01T12:00:00Z
python scripts/validate_handoff.py examples/readiness/manager.handoff.json
```

以下は **exit 1 が期待値**。通常CLIに --at を付けない場合は現在UTC時刻で検査する。

```bash
python scripts/validate_readiness.py examples/readiness/invalid-premature-achieved.json \
  --context examples/readiness/context.json --at 2030-01-01T12:00:00Z
python scripts/validate_readiness.py examples/readiness/invalid-premerge-deferred.json \
  --context examples/readiness/context.json --at 2030-01-01T12:00:00Z
```

`tests/test_readiness.py` はこれらに加え CI success + AI review fail、GitHub 必須 review 未充足、古い head/base/target/config/merge-group、期限切れ、独立性、依存未完、配備影響 automatic/unknown の fail-closed、queue、AC 原文と分類の context 不一致、全 AC 対応、CLI の終了コードと cwd 非依存を検査する。

形式が PASS でも真実性・独立性・実際のマージ可否は証明しない。架空の主張が構造上 PASS になるテストでこの境界も固定する。
