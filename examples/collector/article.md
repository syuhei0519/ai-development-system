---
id: SYNTHETIC-ARTICLE-1
title: "synthetic sample: 空文字と空白のみのケースを分ける"
domain: validation
status: draft
updated: "2000-01-01"
review_after: "異なる runtime への適用前"
tags: [synthetic, test-plan]
raw_sources: [input.json]
supersedes: []
superseded_by: []
publication: synthetic_sample
---

# synthetic sample: 空文字と空白のみのケースを分ける

すべて架空の資料・判断であり、実行実績ではない。2件の架空の Issue の Raw Findings は [input.json](input.json) に固定 revision の出典付きで同梱する。

## 要点・適用条件

架空の2資料は、空文字と空白のみを別ケースとして扱う設計を示す。非空白文字を要求する文字列の検証計画では、両者を分けるという限定的な知識候補を抽出できる。製品テストの成功は示さない。

## 根拠・判断・例外

SYNTHETIC-RAW-1 と SYNTHETIC-RAW-2 の比較からの架空の推論。採用理由は2資料で同じ区別が現れるため。不採用案は長さだけの検査で、空白を通す可能性がある。実際の失敗は観測していない。Unicode と runtime 固有の動作は未検証であり、別途確認が必要。

## 陳腐化・更新

異なる runtime に適用する前に再検証する。現時点は draft。実運用記事としては採用しない。

## 理解を深めるための問い

- 長さだけの検査では、どの入力を誤って受理し得るか？
- 対象 runtime が変わると、どの前提を再検証すべきか？
