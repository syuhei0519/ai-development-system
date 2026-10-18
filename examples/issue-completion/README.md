# Issue Completion の例

現行は1.1。標準変更・準備変更、統合済み・待機中、実測不足・失敗を、
`tests/completion_fixture.py` と `tests/preparation_completion_fixture.py` の架空データで検証する。
これらはテストの一時ディレクトリに生成し、成功の実記録や操作許可として使わない。

```sh
python -m unittest discover -s tests -p 'test_issue_completion*.py' -v
python -m unittest discover -s tests -p 'test_preparation_completion.py' -v
```

旧1.0の保存済み例を新しい版へ書き換えて残さず、
[当時の固定履歴](https://github.com/syuhei0519/ai-development-system/tree/e1d2b4dcbe47483e1193206386f8d21810cc3fd7/examples/issue-completion) で再現する。
