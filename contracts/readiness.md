# Readiness 1.1

現行は readiness.schema.json / readiness-context.schema.json。
通常の変更は pr_kind=standard、preparation=null とし、製品の確認条件を省略しない。
準備だけの変更は pr_kind=preparation とし、工程の成果を製品の達成へ読み替えない。

CLI は対象commit・実体・独立context digest・期限と検証根拠を照合する。
Handoffと組み合わせる場合は `--handoff` も指定し、読み取り後のbytes変更を拒否する。
`--context-sha256` は提供元と別に確認した context bytes の SHA-256 を渡す。
マージ前の合格だけでは統合や実配備の完了にならない。

[旧版と当時の結果](https://github.com/syuhei0519/ai-development-system/blob/e1d2b4dcbe47483e1193206386f8d21810cc3fd7/contracts/readiness.md) は履歴から参照する。旧版検証の現行サポートは終了した。
