# AI Development System

学習用の開発を、目的・変更・観察・学びが追える短い記録で進めます。

- [ワークフロー](workflows/single-issue.md)
- [タスク入力](templates/task-input.md) / [Handoff](templates/handoff.md)
- [役割](agents/) / [契約と互換性](contracts/README.md)
- [既存 Issue / PR の変換ルール](docs/learning-workflow.md)

ログと生成証跡は CI artifact と PR にまとめ、Git には再現手順と結論の Markdown を残します。
artifact の失効後も対象 commit と手順から追試できるようにします。
独立 Review、required CI、security checks、image digest と依存固定は維持します。
過去の失敗・停止・未実施記録は Git 履歴と互換テストで保持します。
追加 OpenAI API・課金サービス・Secrets/Ruleset 変更・main 直接 Push は行いません。

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_handoff.py templates/handoff.md
python -m unittest discover -s tests -v
```

旧 JSON 契約と回帰 fixture は明示指定された既存タスクの互換検証に残しています。
新規タスクに旧版の schema や多重の receipt を組み合わせる必要はありません。
