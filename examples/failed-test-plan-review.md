# synthetic sample: failed Test plan review

This is a self-contained fictional alternative plan and its fictional review. It is separate from the successful Research→Test example. All IDs and revisions are placeholders; no product code or actual test execution is represented.

## Supplied AC original

SYNTHETIC-AC-1: “A label must contain at least one non-whitespace character.”

Source placeholder: https://example.invalid/issues/SYNTHETIC-ISSUE-001#ac-1

## Incomplete alternative plan

| Input | Proposed expectation |
| --- | --- |
| `""` | reject |
| `"a"` | accept |

## Fictional review finding

The plan omits whitespace-only input such as `" "` or `"\t\n"`. It therefore cannot distinguish the required non-whitespace rule from an incorrect length-only rule. The assigned plan-review completion criterion is coverage of the supplied AC, so the fictional business outcome is `failed` and the AC mapping is `not_met`.

Required correction: add explicit whitespace-only rejection cases and re-review the revised plan. This is a fictional documentary finding, not an observed product-test failure. Product behavior and CI remain unverified.
