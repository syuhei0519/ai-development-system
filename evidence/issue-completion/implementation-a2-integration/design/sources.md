# 設計出典

公開安全候補 / edited derivative / 未公開。

設計の基準は公開Systemリポジトリ `syuhei0519/ai-development-system` の固定commit `df400018057735b7cb6a9c6ea4619508f0e6ba3a`。以下のURLは公開コードの固定参照であり、私的会話・実行タスク・非公開成果物へのリンクではない。記載hashは公開ソースファイルの全bytesであり、非公開設計原本のhashではない。

このファイルは出典目録。Systemソースそのものは配送bundleへ複製していない。Implementation開始時に、Managerが認可した固定System snapshotを別入力として取得・検査する。bundleのHandoff artifact参照は同梱ファイルだけで完結するが、開発環境やコード依存全体が同梱されているとは主張しない。

| 固定出典 | bytes | SHA-256 |
|---|---:|---|
| [agents/research-design.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/agents/research-design.md) | 4380 | `c62194fe3064a1d36e9292dbf3c3d635db141e340c3c156e4eb668586474d055` |
| [agents/manager.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/agents/manager.md) | 5895 | `73c7af44c4d85f416e728915f85dca31eb273d6728d5bab2ecd4f67dd1ae5acb` |
| [contracts/README.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/README.md) | 10257 | `005e74d6ae1103e1e3c8d543a87ce4f73592040efb2ea8b34088278b2fa7181d` |
| [contracts/readiness.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/readiness.md) | 12727 | `fbecc481811a7b57d70463d37fff65362e6f8c83b21d6490baef9e24dc6717d3` |
| [contracts/readiness.schema.json](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/readiness.schema.json) | 12251 | `bfb1589b2cc0fce39b9b098dc72265796aa79053dd6c3f3131d28aa43d341693` |
| [contracts/readiness-context.schema.json](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/readiness-context.schema.json) | 4425 | `e10a8069441a17b447819b0bec9cb145b7a7f91f8d758a6f3dbdcc44361a2f4d` |
| [contracts/handoff.schema.json](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/handoff.schema.json) | 15093 | `3df669f230c3f1d65ddaaa9e7de5f713f70b9e8440512403f6ea309eb70b3ae1` |
| [contracts/artifact-delivery.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/artifact-delivery.md) | 12526 | `6f65c19c74aea4483f900ce045a6648357c754c1977cd38338839fbb1457ef22` |
| [contracts/artifact-delivery.schema.json](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/contracts/artifact-delivery.schema.json) | 2490 | `480ba09256cb5b947d8b2df380a12a7ab9ff5fd3c777653e056eacb2541b655c` |
| [scripts/validate_readiness.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/scripts/validate_readiness.py) | 13968 | `73ecbcacf1adcadda7200666d123079dd58adb1a7dfd63ba3aadccef86757080` |
| [scripts/validate_handoff.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/scripts/validate_handoff.py) | 5107 | `c78e917498087cf9bf230ac644135d3dd3aacfe6ff68e294dfe3bc563bfbe221` |
| [scripts/consume_delivery.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/scripts/consume_delivery.py) | 13843 | `62df142aa83c5216aae6151f2d21ffffe4bd8aa9db68dd1144502505cce8fcad` |
| [tests/test_readiness.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/tests/test_readiness.py) | 13525 | `252aa1c0c6be2fb772937d06664a013d72a250121116adb30aa2e1bc42adc2a5` |
| [tests/test_readiness_binding.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/tests/test_readiness_binding.py) | 9298 | `332902e861e6000171a902e82df81298ace45c1423ade92c4048af913384fb9b` |
| [tests/test_delivery.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/tests/test_delivery.py) | 13631 | `d877fb3b0f44141e6533d30b1d366e2f142b82a016bccb2d93ccaacca3f1a4a4` |
| [tests/test_delivery_content.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/tests/test_delivery_content.py) | 8418 | `2f1c7d313c542877fa32fdb0a4520c0328452ae56f275f1a7dc6a5fa474f1092` |
| [tests/test_retry.py](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/tests/test_retry.py) | 4503 | `ae9ddf65df67dcfe10ca18fe04c0fefe7b0de3661d1c0d94dd0246650d0964df` |
| [.github/workflows/validate.yml](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/.github/workflows/validate.yml) | 1860 | `8e26b2496c01354a754b950382d2a55f0843552023c93643d0d53eb6ca6fe67c` |
| [workflows/single-issue.md](https://github.com/syuhei0519/ai-development-system/blob/df400018057735b7cb6a9c6ea4619508f0e6ba3a/workflows/single-issue.md) | 15288 | `f3bbeeb49ff537cd1058f9d9b71e1af1a87a5c68e2491aebde7d5743049ffec6` |

## 適用上の区別

Readinessのaggregate_required禁止は現行仕様。新しいIssue Completion schema/CLI/fixturesは設計提案であり、上記commitに実装済みではない。新仕様の意味検証・実装・独立Test/Reviewは後続工程で必要になる。
